"""Standalone camera or offline replay, using exactly the same controller as ROS 2.

From the ROS package directory:
python -m face_vision.live_lamp --replay examples/observations.jsonl --plot
python -m face_vision.live_lamp --model-path /path/face_landmarker.task --preview
"""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import queue
import sys
import threading
import time
import uuid
from .lamp_controller import LampController


class CameraWorker(threading.Thread):
    def __init__(self, model_path, camera_index=0):
        super().__init__(daemon=True)
        self.model_path, self.camera_index = model_path, camera_index
        self.frames = queue.Queue(maxsize=1)
        self.stop_event = threading.Event()

    def put_latest(self, item):
        try:
            self.frames.get_nowait()
        except queue.Empty:
            pass
        self.frames.put_nowait(item)

    def run(self):
        cap = detector = None
        try:
            # Replay / tests never import or require these optional dependencies.
            from .vision_core import (cv2, mp, np, mp_python, vision, classify_expression)
            opts = vision.FaceLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=str(self.model_path)),
                running_mode=vision.RunningMode.VIDEO, num_faces=1,
                output_face_blendshapes=True, min_face_detection_confidence=.5,
                min_face_presence_confidence=.5, min_tracking_confidence=.5)
            detector = vision.FaceLandmarker.create_from_options(opts)
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_V4L2 if sys.platform.startswith('linux') else cv2.CAP_ANY)
            if not cap.isOpened():
                raise RuntimeError(f'Cannot open camera {self.camera_index}')
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            origin, last_ms, seq, stream = time.monotonic(), -1, 0, uuid.uuid4().hex
            while not self.stop_event.is_set():
                captured = time.monotonic()  # approximate read boundary, not exposure timestamp
                ok, frame = cap.read()
                emotion, strength, detected = 'unknown', 0.0, False
                if ok:
                    image = mp.Image(image_format=mp.ImageFormat.SRGB,
                                     data=np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
                    ms = max(last_ms + 1, int((captured - origin) * 1000))
                    last_ms = ms
                    result = detector.detect_for_video(image, ms)
                    detected = bool(result.face_landmarks)
                    if detected:
                        blends = result.face_blendshapes[0] if result.face_blendshapes else []
                        emotion, strength = classify_expression(blends)
                obs = {'schema': 1, 'stream_id': stream, 'seq': seq, 'detected': detected,
                       'emotion': emotion, 'strength': strength}
                seq += 1
                self.put_latest((obs, captured, frame if ok else None, None))
                self.stop_event.wait(1.0 / 15.0)
        except Exception as error:
            self.put_latest((None, time.monotonic(), None, str(error)))
        finally:
            if cap is not None:
                cap.release()
            if detector is not None:
                detector.close()


def write_csv(samples, output):
    fields = ['time_s', 'input_emotion', 'input_strength', 'mode', 'status',
              'H_happy', 'H_sad', 'H_curious', 'phi_rad', 'o1', 'o2',
              'J1_deg', 'J2_deg', 'J3_deg', 'J4_deg', 'color', 'brightness']
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        for s in samples:
            writer.writerow([s['t'], s['input_emotion'], s['input_strength'], s['mode'],
                             s['input_status'], *[s['hormones'][k] for k in ('Happy', 'Sad', 'Confused')],
                             s['phi'], s['o1'], s['o2'], *s['q_deg'],
                             s['light']['color'], s['light']['brightness']])


def plot_samples(samples, filename, source_label='Replay fixture, not camera or servo measurements'):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    ts = [s['t'] for s in samples]
    fig, ax = plt.subplots(4, 1, figsize=(13, 11), sharex=True)
    modes = {'Neutral': 0, 'Happy': 1, 'Sad': 2, 'Confused': 3}
    ax[0].step(ts, [modes[s['mode']] for s in samples], where='post')
    ax[0].set(yticks=list(modes.values()), yticklabels=list(modes), ylabel='Accepted mode')
    for key, label in [('Happy', 'H_happy'), ('Sad', 'H_sad'), ('Confused', 'H_curious')]:
        ax[1].plot(ts, [s['hormones'][key] for s in samples], label=label)
    ax[1].set(ylabel='Hormone level', ylim=(-.03, 1.03))
    ax[1].legend()
    for j in range(4):
        ax[2].plot(ts, [s['q_deg'][j] for s in samples], label=f'J{j+1}')
    ax[2].set(ylabel='Command (degrees)')
    ax[2].legend(ncol=4)
    ax[3].plot(ts, [s['light']['brightness'] for s in samples], color='#a58a00')
    ax[3].set(ylabel='Brightness', xlabel='Time (s)', ylim=(0, 1.05))
    for a in ax:
        a.grid(alpha=.25)
    fig.suptitle('Face expression -> hormone memory -> CPG / lamp commands\n' + source_label)
    fig.tight_layout(rect=[0, 0, 1, .94])
    fig.savefig(filename, dpi=160)
    plt.close(fig)


def replay(path, duration=45.0):
    events = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    previous = -1.0
    for event in events:
        t = event.get('time_s')
        if type(t) not in (int, float) or not math.isfinite(t) or t < 0 or t < previous:
            raise ValueError('Replay time_s must be finite, nonnegative and sorted')
        previous = t
    controller, index, samples = LampController(), 0, []
    for step in range(round(duration / controller.dt) + 1):
        now = round(step * controller.dt, 8)
        # Process timer first: a newly received frame must not affect past integration ticks.
        sample = controller.step(now)
        while index < len(events) and events[index]['time_s'] <= now + 1e-9:
            controller.observe(events[index], now)
            index += 1
        samples.append(sample)
    return samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--replay', type=Path)
    inputs.add_argument('--model-path', type=Path)
    parser.add_argument('--camera-index', type=int, default=0)
    parser.add_argument('--duration', type=float, default=45.0)
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--plot', action='store_true')
    parser.add_argument('--output', type=Path, default=Path('results/face_lamp.csv'))
    args = parser.parse_args()
    os.environ.setdefault('MPLCONFIGDIR', str(args.output.resolve().parent / '.matplotlib'))
    if not math.isfinite(args.duration) or args.duration <= 0:
        parser.error('--duration must be positive and finite')
    if args.replay:
        samples = replay(args.replay, args.duration)
    else:
        if not args.model_path.is_file():
            parser.error('face_landmarker.task model file does not exist')
        controller = LampController(start_time=time.monotonic())
        worker = CameraWorker(args.model_path, args.camera_index)
        samples, last_frame = [], None
        worker.start()
        next_tick, next_print = time.monotonic(), time.monotonic()
        try:
            while time.monotonic() - controller.origin <= args.duration:
                now = time.monotonic()
                sample = controller.step(now)
                try:
                    obs, captured, frame, error = worker.frames.get_nowait()
                    if error:
                        raise RuntimeError(error)
                    if now - captured > controller.gate.timeout_s:
                        controller.gate.invalidate('camera_processing_timeout')
                    else:
                        controller.observe(obs, now)
                    if frame is not None:
                        last_frame = frame
                except queue.Empty:
                    pass
                samples.append(sample)
                if now >= next_print:
                    print(f"{sample['t']:6.2f}s {sample['mode']:8} H={sample['hormones']} q={sample['q_deg']}")
                    next_print = now + 1
                if args.preview and last_frame is not None:
                    import cv2
                    image = last_frame.copy()
                    cv2.putText(image, f"{sample['input_emotion']} -> {sample['mode']} | {sample['input_status']}",
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 0), 2)
                    h = sample['hormones']
                    cv2.putText(image, f"H happy={h['Happy']:.2f} sad={h['Sad']:.2f} curious={h['Confused']:.2f}",
                                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 255, 255), 2)
                    cv2.putText(image, 'J1-J4 deg: ' + ', '.join(f'{q:.1f}' for q in sample['q_deg']),
                                (10, 90), cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 255, 255), 2)
                    cv2.imshow('Face -> hormone -> CPG (q to stop)', image)
                    if cv2.waitKey(1) & 0xff == ord('q'):
                        break
                next_tick += controller.dt
                if next_tick < time.monotonic():
                    next_tick = time.monotonic()
                time.sleep(max(0, next_tick - time.monotonic()))
        except KeyboardInterrupt:
            pass
        finally:
            worker.stop_event.set()
            worker.join(timeout=2)
            if args.preview:
                try:
                    import cv2
                    cv2.destroyAllWindows()
                except ImportError:
                    pass
            if samples:
                write_csv(samples, args.output)
    write_csv(samples, args.output)
    if args.plot:
        label = ('Replay fixture, not camera or servo measurements' if args.replay
                 else 'Live camera input / simulated lamp commands; no servo measurements')
        plot_samples(samples, args.output.with_suffix('.png'), label)
    print(f'Saved {len(samples)} command samples to {args.output.resolve()}')


if __name__ == '__main__':
    main()
