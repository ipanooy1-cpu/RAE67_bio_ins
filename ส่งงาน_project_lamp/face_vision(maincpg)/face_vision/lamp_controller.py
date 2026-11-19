"""Camera expression -> debounced mode -> persistent hormone / SO(2) CPG.

No ROS, camera or motor dependencies here. Outputs are proposed simulation commands.
"""
import math
from . import lamp_model as model

EXPRESSION_MAP = {
    'happy': 'Happy', 'sad': 'Sad', 'neutral': 'Neutral',
    'angry': 'Confused', 'surprised': 'Confused',
}


class ExpressionGate:
    def __init__(self, min_strength=.35, stable_s=.30, timeout_s=.50, min_samples=3):
        if not (0 <= min_strength <= 1 and 0 <= stable_s < timeout_s
                and min_samples >= 1):
            raise ValueError('Invalid expression gate settings')
        self.min_strength, self.stable_s = min_strength, stable_s
        self.timeout_s, self.min_samples = timeout_s, min_samples
        self.last_received = None
        self.last_seq = -1
        self.stream_id = None
        self.candidate = None
        self.candidate_since = 0.0
        self.count = 0
        self.mode = 'Neutral'
        self.reason = 'no_observation'
        self.raw_emotion = 'unknown'
        self.strength = 0.0

    def invalidate(self, reason):
        self.mode = 'Neutral'
        self.candidate = None
        self.count = 0
        self.reason = reason

    def push(self, observation, now):
        """now is a local monotonic RECEIVE time, never a ROS/source clock."""
        if not isinstance(observation, dict) or not math.isfinite(now):
            self.invalidate('invalid_observation')
            return False
        stream, seq = observation.get('stream_id'), observation.get('seq')
        score = observation.get('strength')
        if (observation.get('schema') != 1 or not isinstance(stream, str) or not stream
                or type(seq) is not int or seq < 0
                or type(observation.get('detected')) is not bool
                or type(score) not in (int, float) or not math.isfinite(score)
                or not 0 <= score <= 1):
            self.invalidate('invalid_observation')
            return False
        if stream == self.stream_id and seq <= self.last_seq:
            # Duplicated messages must not refresh the receipt watchdog.
            return False
        if self.last_received is not None and now < self.last_received:
            self.invalidate('invalid_receive_time')
            return False
        if stream != self.stream_id:
            self.invalidate('source_restart')
            self.last_seq = -1
        elif self.last_received is not None and now - self.last_received > self.timeout_s:
            self.invalidate('input_timeout')
        self.stream_id, self.last_seq, self.last_received = stream, seq, now
        raw = observation.get('emotion')
        self.raw_emotion = raw if isinstance(raw, str) else 'unknown'
        self.strength = score
        if not observation['detected']:
            self.invalidate('no_face')
            return True
        if not isinstance(self.raw_emotion, str) or self.raw_emotion not in EXPRESSION_MAP:
            self.invalidate('unknown_expression')
            return True
        if score < self.min_strength:
            self.invalidate('weak_expression')
            return True
        mapped = EXPRESSION_MAP[self.raw_emotion]
        if mapped != self.candidate:
            self.candidate, self.candidate_since, self.count = mapped, now, 1
        else:
            self.count += 1
        if self.count >= self.min_samples and now - self.candidate_since >= self.stable_s - 1e-9:
            self.mode, self.reason = mapped, 'accepted'
        else:
            self.reason = 'waiting_stable_expression'
        return True

    def current(self, now):
        if self.last_received is None or now - self.last_received > self.timeout_s:
            self.invalidate('input_timeout' if self.last_received is not None else 'no_observation')
        return self.mode


class LampController:
    def __init__(self, *, min_strength=.35, stable_s=.30, timeout_s=.50,
                 max_speed_deg_s=20.0, start_time=0.0):
        if not math.isfinite(start_time) or not math.isfinite(max_speed_deg_s) or max_speed_deg_s <= 0:
            raise ValueError('Invalid controller settings')
        self.gate = ExpressionGate(min_strength, stable_s, timeout_s)
        self.max_speed = max_speed_deg_s
        self.dt = model.DT
        self.time = start_time
        self.origin = start_time
        self.mode = 'Neutral'
        self.onset = {name: start_time for name in model.PRESETS}
        self.hormones = {name: 0.0 for name in model.HORMONE_SETTINGS}
        self.o1, self.o2 = .10, 0.0
        for _ in range(model.WARMUP_STEPS):
            self.o1, self.o2 = model.so2_step(self.o1, self.o2, 1.10, .20)
        self.q = [90.0] * 4
        self.centers = self.q.copy()
        self.sad_start = 90.0
        self.light = {'color': '#ffffff', 'brightness': .6}
        self.phi = .20
        self.scheduler_fault = False

    def observe(self, observation, received_at):
        # Integrate preceding time with the OLD input before applying this frame.
        self.step(received_at)
        return self.gate.push(observation, received_at)

    def _tick(self, now):
        next_mode = self.gate.current(now)
        if next_mode != self.mode:
            self.mode = next_mode
            self.onset[self.mode] = now
            if self.mode == 'Sad':
                self.sad_start = self.q[3]
        # This state is updated continuously; never re-initialize it per frame.
        self.hormones = model.hormone_step(self.hormones, self.mode, self.dt)
        elapsed = {name: max(0.0, now - self.onset[name]) for name in model.PRESETS}
        params = model.hormone_parameters(self.hormones, elapsed)
        self.phi, self.light = params['phi'], params['light']
        self.o1, self.o2 = model.so2_step(self.o1, self.o2, 1.10, self.phi)
        self.centers = params['centers']
        fade = None
        if self.mode == 'Sad':
            poses = [(t, a.copy()) for t, a in model.PRESETS['Sad']['poses']]
            # Preserve downward progress even if live Sad begins at 90 rather than
            # the offline preset's 105 degrees; do not first raise the head to 100.
            for _, angles in poses:
                progress = (105.0 - angles[3]) / 45.0
                angles[3] = self.sad_start + (60.0 - self.sad_start) * progress
            self.centers[3] = model.pose_at_time(elapsed['Sad'], poses)[3]
            fade = tuple(self.onset['Sad'] - self.origin + t for t in (5.0, 10.0))
        target = model.decode_angles(self.o1, self.o2, self.centers,
                                     params['gains'], now - self.origin, fade)
        max_delta = self.max_speed * self.dt
        # Extra rate limit: noisy mode changes cannot jump the angle command.
        self.q = [model.clamp(old + model.clamp(new - old, -max_delta, max_delta), low, high)
                  for old, new, (low, high) in zip(self.q, target, model.JOINT_LIMITS)]

    def step(self, now):
        if not math.isfinite(now) or now < self.time - 1e-9:
            raise ValueError('Controller clock must be finite and monotonic')
        count = int((now - self.time + 1e-9) / self.dt)
        if count > 5:
            # Never fast-forward a moving trajectory after a blocked callback.
            self.scheduler_fault = True
            self.gate.invalidate('scheduler_overrun')
            self.time = now
            return self.snapshot()
        self.scheduler_fault = False
        for _ in range(count):
            self.time = round(self.time + self.dt, 9)
            self._tick(self.time)
        return self.snapshot()

    def snapshot(self):
        return {'t': round(self.time - self.origin, 6), 'mode': self.mode,
                'input_emotion': self.gate.raw_emotion, 'input_strength': self.gate.strength,
                'input_status': self.gate.reason, 'scheduler_fault': self.scheduler_fault,
                'hormones': self.hormones.copy(), 'o1': self.o1, 'o2': self.o2,
                'phi': self.phi, 'q_deg': self.q.copy(), 'centers_deg': self.centers.copy(),
                'light': self.light.copy(), 'simulation_limits_only': True}
