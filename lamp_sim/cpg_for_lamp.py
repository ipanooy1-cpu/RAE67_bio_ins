import math
import argparse
import csv
from pathlib import Path

# ==================================================
# 1. การตั้งค่า
# ==================================================

DT = 0.05          # เวลาจำลองต่อขั้น
DURATION = 10.0    # จำลองทั้งหมด 10 วินาที
WARMUP_STEPS = 200

# ขอบเขตตัวอย่างสำหรับ simulation เท่านั้น
JOINT_LIMITS = [
    (60.0, 120.0),  # J1
    (60.0, 120.0),  # J2
    (60.0, 120.0),  # J3
    (60.0, 120.0),  # J4
]

# แต่ละโหมดมีท่าที่เวลา 0, 1 และ 5 วินาที
# poses เป็นมุมกลาง [J1, J2, J3, J4] หน่วยองศา
# gain เป็นตัวคูณสัญญาณ CPG
#
# มุมเหล่านี้เป็นค่าทดลองที่ออกแบบเอง
# สมมติว่าลดมุม J4 = ก้มหัว

PRESETS = {
    "Neutral": {
        "light": {'color': '#ffffff', 'brightness': [(0, 0.6), (1, 0.6), (5, 0.6), (10, 0.6)]},  # white; brightness 0..1 at 0/1/5/10 seconds
        "alpha": 1.10,
        "phi": 0.20,
        "gain": [2.0, 2.0, 2.0, 2.0],
        "poses": [
            (0.0, [90.0, 90.0, 90.0, 90.0]),
            (1.0, [90.0, 90.0, 90.0, 90.0]),
            (5.0, [90.0, 90.0, 90.0, 90.0]),
        ],
    },

    "Happy": {
        "light": {'color': '#ffd43b', 'brightness': [(0, 0.6), (1, 0.8), (5, 1.0), (10, 1.0)]},  # yellow; brightness 0..1 at 0/1/5/10 seconds
        "alpha": 1.10,
        "phi": 0.35,
        "gain": [6.0, 8.0, 6.0, 8.0],
        "poses": [
            (0.0, [90.0, 90.0, 90.0, 90.0]),
            (1.0, [90.0, 95.0, 93.0, 98.0]),
            (5.0, [90.0, 100.0, 95.0, 105.0]),
        ],
    },

    "Sad": {
        "light": {'color': '#377dff', 'brightness': [(0, 0.6), (1, 0.45), (5, 0.25), (10, 0.1)]},  # blue; brightness 0..1 at 0/1/5/10 seconds
        "alpha": 1.10,
        "phi": 0.12,
        "gain": [2.0, 2.0, 2.0, 8.0],
        "head_fade": (5.0, 10.0),  # Fade J4 oscillation to reach exactly 60 degrees
        "poses": [
            (0.0, [90.0, 90.0, 90.0, 105.0]),
            (1.0, [90.0, 85.0, 85.0, 100.0]),
            (5.0, [90.0, 80.0, 80.0, 85.0]),
            (10.0, [90.0, 80.0, 80.0, 60.0]),
        ],
    },

    "Confused": {
        "light": {'color': '#b05cff', 'brightness': [(0, 0.6), (1, 0.75), (5, 0.45), (10, 0.65)]},  # purple; brightness 0..1 at 0/1/5/10 seconds
        "alpha": 1.10,
        "phi": 0.25,
        "gain": [20.0, 2.0, 3.0, 5.0],
        "poses": [
            (0.0, [90.0, 90.0, 90.0, 90.0]),
            (1.0, [95.0, 90.0, 88.0, 85.0]),
            (5.0, [100.0, 90.0, 85.0, 80.0]),
        ],
    },
}


# ==================================================
# 2. สมการ SO(2) CPG
# ==================================================

def so2_step(o1, o2, alpha, phi):
    c = math.cos(phi)
    s = math.sin(phi)

    # ทั้งสองสมการใช้ output เดิมชุดเดียวกัน
    a1_next = alpha * (c * o1 + s * o2)
    a2_next = alpha * (-s * o1 + c * o2)

    o1_next = math.tanh(a1_next)
    o2_next = math.tanh(a2_next)

    return o1_next, o2_next


# ==================================================
# 3. คำนวณมุมกลางตามช่วงเวลา
# ==================================================

def pose_at_time(t, poses):
    # ก่อนหรือเท่าจุดเริ่มต้น
    if t <= poses[0][0]:
        return poses[0][1].copy()

    # หาช่วงที่เวลาปัจจุบันอยู่
    for i in range(len(poses) - 1):
        start_time, start_angles = poses[i]
        end_time, end_angles = poses[i + 1]

        if t <= end_time:
            progress = (
                (t - start_time)
                / (end_time - start_time)
            )

            # เปลี่ยนมุมกลางแบบเส้นตรงระหว่างสองท่า
            return [
                start + (end - start) * progress
                for start, end in zip(
                    start_angles,
                    end_angles,
                )
            ]

    # หลังจุดเวลาสุดท้าย คงมุมกลางของท่าสุดท้าย
    return poses[-1][1].copy()


# ==================================================
# 4. แปลง CPG เป็นมุมข้อต่อ
# ==================================================

def clamp(value, low, high):
    return max(low, min(high, value))


def decode_angles(o1, o2, centers, gains, t, head_fade=None):
    # ค่อย ๆ เปิดการแกว่งในวินาทีแรก
    # เพื่อให้ที่ t=0 มุมตรงกับท่าเริ่มต้นพอดี
    blend = clamp(t / 1.0, 0.0, 1.0)

    head_blend = blend
    if head_fade is not None:
        start, end = head_fade
        head_blend *= 1.0 - clamp((t - start) / (end - start), 0.0, 1.0)

    targets = [
        centers[0] + blend * gains[0] * o1,
        centers[1] + blend * gains[1] * o2,
        centers[2] - blend * gains[2] * o1,
        centers[3] + head_blend * gains[3] * o2,
    ]

    return [
        clamp(angle, low, high)
        for angle, (low, high) in zip(
            targets,
            JOINT_LIMITS,
        )
    ]


def time_segment(t):
    if t < 1.0:
        return "0→1s"
    elif t < 5.0:
        return "1→5s"
    elif t < 10.0:
        return "5→10s"
    else:
        return "ค้างท่า"


# ==================================================
# 5. รันการจำลอง
# ==================================================

def select_presets():
    print("\nเลือกโหมดที่ต้องการวาดกราฟ")
    choices = {
        "1": "Neutral",
        "2": "Happy",
        "3": "Sad",
        "4": "Confused",
    }
    for number, mode in choices.items():
        print(f"{number} = {mode}")
    print("5 = ทุกโหมด")
    print("พิมพ์ชื่อโหมดแทนหมายเลขได้ เช่น Happy หรือ sad")

    while True:
        choice = input("เลือกโหมด: ").strip().lower()
        if choice in ("5", "all"):
            return PRESETS.copy()

        mode = choices.get(choice)
        if mode is None:
            mode = next(
                (name for name in PRESETS if name.lower() == choice),
                None,
            )
        if mode is not None:
            return {mode: PRESETS[mode]}
        print("กรุณาใส่หมายเลข 1–5 หรือชื่อ Neutral, Happy, Sad, Confused")


# ==================================================
# 6. Hormone: แบบจำลองที่เสนอสำหรับโคมไฟนี้
# ==================================================
# ค่า tau เป็นค่าทดลอง ไม่ใช่ค่าฮอร์โมนที่วัดจากสิ่งมีชีวิต
# H_happy / H_sad / H_curious มีช่วง 0..1
HORMONE_SETTINGS = {
    "Happy": {"name": "H_happy", "tau_up": 0.5, "tau_down": 1.5},
    "Sad": {"name": "H_sad", "tau_up": 2.0, "tau_down": 3.0},
    "Confused": {"name": "H_curious", "tau_up": 0.4, "tau_down": 1.0},
}


def hormone_step(hormones, mode, dt):
    """Forward Euler: ทุกตัวอ่าน H เดิม ก่อนคืน H ใหม่พร้อมกัน."""
    if mode not in PRESETS:
        raise ValueError(f"Unknown mode: {mode}")
    if not math.isfinite(dt) or dt < 0:
        raise ValueError("dt must be finite and nonnegative")
    result = {}
    for emotion, settings in HORMONE_SETTINGS.items():
        old_h = hormones[emotion]
        if not math.isfinite(old_h) or not 0 <= old_h <= 1:
            raise ValueError("Hormone must be finite and within [0, 1]")
        target = 1.0 if emotion == mode else 0.0
        tau = settings["tau_up"] if target > old_h else settings["tau_down"]
        # Euler ควรใช้ dt <= tau เพื่อไม่ให้ข้ามเป้าหมาย
        if dt > tau:
            raise ValueError("dt must not exceed hormone tau")
        next_h = old_h + dt * (target - old_h) / tau
        result[emotion] = clamp(next_h, 0.0, 1.0)
    return result


def emotion_weights(hormones):
    # เมื่อเปลี่ยนโหมด H เก่ายังไม่หายทันที
    # normalize ถ้า H รวมเกิน 1 เพื่อไม่ให้ท่าทาง/ตัวคูณรวมกันเกิน preset
    total = sum(hormones.values())
    scale = max(1.0, total)
    weights = {name: value / scale for name, value in hormones.items()}
    weights["Neutral"] = max(0.0, 1.0 - total)
    return weights


def value_at_time(t, frames):
    # ใช้ interpolation เดียวกับ poses สำหรับความสว่าง
    return pose_at_time(t, [(time, [value]) for time, value in frames])[0]


def rgb_from_hex(color):
    return [int(color[i:i + 2], 16) for i in (1, 3, 5)]


def hormone_parameters(hormones, elapsed):
    weights = emotion_weights(hormones)
    centers = [0.0] * 4
    gains = [0.0] * 4
    phi = 0.0
    rgb = [0.0] * 3
    brightness = 0.0
    for name, weight in weights.items():
        preset = PRESETS[name]
        local_t = elapsed[name]
        pose = pose_at_time(local_t, preset["poses"])
        for j in range(4):
            centers[j] += weight * pose[j]
            gains[j] += weight * preset["gain"][j]
        phi += weight * preset["phi"]
        light = preset["light"]
        brightness += weight * value_at_time(local_t, light["brightness"])
        for j, channel in enumerate(rgb_from_hex(light["color"])):
            rgb[j] += weight * channel
    channels = [round(clamp(v, 0, 255)) for v in rgb]
    return {
        "centers": centers, "gains": gains, "phi": phi,
        "light": {"color": "#" + "".join(f"{v:02x}" for v in channels),
                  "brightness": clamp(brightness, 0.0, 1.0)},
    }


def simulate(mode, schedule=None):
    """จำลองแยกโหมด หรือ schedule เช่น [(0,'Sad'),(5,'Neutral')].

    เวลา t คือ state หลัง update ช่วงก่อนหน้า dt; t=0 ยังมี H=0.
    schedule เป็นอินพุตเลือกอารมณ์ ไม่ใช่การตรวจจับอารมณ์อัตโนมัติ.
    """
    if mode not in PRESETS:
        raise ValueError(f"Unknown mode: {mode}")
    schedule = [(0.0, mode)] if schedule is None else list(schedule)
    if not schedule or schedule[0][0] != 0:
        raise ValueError("Schedule must start at t=0")
    for i, (t, name) in enumerate(schedule):
        if (not math.isfinite(t) or not 0 <= t <= DURATION or name not in PRESETS
                or (i and t <= schedule[i - 1][0])):
            raise ValueError("Schedule times must increase within the trial")
    hormones = {name: 0.0 for name in HORMONE_SETTINGS}
    o1, o2 = 0.10, 0.00
    # Warmup เฉพาะ CPG ด้วย Neutral เหมือนกันทุกโหมด ไม่ warmup ฮอร์โมน
    for _ in range(WARMUP_STEPS):
        o1, o2 = so2_step(o1, o2, PRESETS["Neutral"]["alpha"], PRESETS["Neutral"]["phi"])
    active = schedule[0][1]
    onset = {name: 0.0 for name in PRESETS}
    index = 1
    sad_start = PRESETS[active]["poses"][0][1][3]
    samples = []
    for step in range(round(DURATION / DT) + 1):
        t = round(step * DT, 10)
        # Update ด้วยอินพุตของช่วงที่ผ่านมา ก่อนรับ event ที่ t ปัจจุบัน
        if step:
            hormones = hormone_step(hormones, active, DT)
        while index < len(schedule) and t >= schedule[index][0]:
            new_mode = schedule[index][1]
            if new_mode != active:
                active = new_mode
                onset[active] = t
                if active == "Sad":
                    sad_start = samples[-1]["centers"][3]
            index += 1
        elapsed = {name: max(0.0, t - onset[name]) for name in PRESETS}
        params = hormone_parameters(hormones, elapsed)
        if step:
            o1, o2 = so2_step(o1, o2, PRESETS["Neutral"]["alpha"], params["phi"])
        centers = params["centers"]
        head_fade = None
        local_t = elapsed[active]
        if active == "Sad":
            # ข้อยกเว้นที่ตั้งใจ: J4 ตามเวลา ไม่คูณ H ซ้ำ
            # เพื่อให้ถึง 60 องศาที่ 10 s นับจากเริ่ม Sad จริง ๆ
            sad_poses = [(time, angles.copy()) for time, angles in PRESETS["Sad"]["poses"]]
            sad_poses[0][1][3] = sad_start
            centers[3] = pose_at_time(local_t, sad_poses)[3]
            head_fade = tuple(onset["Sad"] + v for v in PRESETS["Sad"]["head_fade"])
        q = decode_angles(o1, o2, centers, params["gains"], t, head_fade)
        samples.append({
            "t": t, "mode": active, "o1": o1, "o2": o2,
            "hormones": hormones.copy(), "phi": params["phi"],
            "gains": params["gains"].copy(), "centers": centers.copy(),
            "q": q, "light": params["light"],
        })
    return samples


def save_csv(samples, filename):
    fields = ["time_s", "mode", "H_happy", "H_sad", "H_curious", "phi_rad",
              "o1", "o2", "J1_deg", "J2_deg", "J3_deg", "J4_deg",
              "light_color", "brightness"]
    with filename.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        for s in samples:
            writer.writerow([s["t"], s["mode"],
                             *[s["hormones"][name] for name in HORMONE_SETTINGS],
                             s["phi"], s["o1"], s["o2"], *s["q"],
                             s["light"]["color"], s["light"]["brightness"]])


def main():
    parser = argparse.ArgumentParser(description="Lamp CPG with hormone memory (simulation only)")
    parser.add_argument("--mode", choices=[*PRESETS, "all"], help="Omit for interactive menu")
    parser.add_argument("--output-dir", default="output/hormone")
    parser.add_argument("--no-show", action="store_true", help="Save graphs without opening windows")
    args = parser.parse_args()
    if args.mode:
        selected = PRESETS if args.mode == "all" else {args.mode: PRESETS[args.mode]}
    else:
        selected = select_presets()
    import matplotlib
    if args.no_show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    count = len(selected)
    cols = 1 if count == 1 else 2
    rows = 1 if count == 1 else 2
    fig, axes = plt.subplots(rows, cols, figsize=(12, 5) if count == 1 else (15, 10), squeeze=False)
    detail, detail_axes = plt.subplots(3, count, figsize=(8, 9) if count == 1 else (18, 10), squeeze=False)
    colors = ["#0099cc", "#f28e2b", "#59a14f", "#b279a2"]
    for column, mode in enumerate(selected):
        samples = simulate(mode)
        times = [s["t"] for s in samples]
        ax = axes.flat[column]
        for j in range(4):
            ax.plot(times, [s["q"][j] for s in samples], color=colors[j], label=f"J{j+1}")
            ax.plot(times, [s["centers"][j] for s in samples], color=colors[j], linestyle="--", alpha=.4)
        for boundary in [1, 5, 10]:
            ax.axvline(boundary, color="gray", linestyle=":", linewidth=1)
        ax.set(title=f"{mode} | hormone-modulated CPG", xlabel="Time (s)", ylabel="Command (degrees)", xlim=(0, DURATION))
        ax.grid(alpha=.25)
        ax.legend()
        for emotion, settings in HORMONE_SETTINGS.items():
            detail_axes[0, column].plot(times, [s["hormones"][emotion] for s in samples], label=settings["name"])
        detail_axes[0, column].set(title=mode, ylabel="Hormone H", ylim=(-.03, 1.03))
        detail_axes[0, column].legend(fontsize=8)
        detail_axes[1, column].plot(times, [s["phi"] for s in samples], color="#333333")
        detail_axes[1, column].set(ylabel="phi (rad/update)")
        detail_axes[2, column].plot(times, [s["light"]["brightness"] for s in samples], color="#aa8800")
        detail_axes[2, column].set(xlabel="Time (s)", ylabel="Brightness", ylim=(0, 1.05))
        for row in range(3):
            detail_axes[row, column].grid(alpha=.25)
        filename = output / f"lamp_{mode.lower()}_hormone.csv"
        save_csv(samples, filename)
        print(f"{mode}: at 10 s H={samples[-1]['hormones']}, J4={samples[-1]['q'][3]:.2f} deg")
        print(f"Saved data: {filename.resolve()}")
    fig.suptitle("Lamp with hormone memory | Solid: command | Dashed: pose center")
    detail.suptitle("Hormone -> CPG phase parameter and light brightness")
    fig.tight_layout(rect=[0, 0, 1, .95])
    detail.tight_layout(rect=[0, 0, 1, .95])
    label = "all_modes" if count > 1 else next(iter(selected)).lower()
    for chart, name in [(fig, f"lamp_{label}_hormone.png"), (detail, f"lamp_{label}_hormone_details.png")]:
        filename = output / name
        chart.savefig(filename, dpi=180, bbox_inches="tight")
        print(f"Saved graph: {filename.resolve()}")
    if args.no_show:
        plt.close("all")
    else:
        plt.show()


if __name__ == "__main__":
    main()
