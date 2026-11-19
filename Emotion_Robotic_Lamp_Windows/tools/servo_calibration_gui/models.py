import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ServoConfig:
    servo_id: int
    name: str
    safe_min: int
    safe_max: int
    center: int
    home: int
    direction_labels: tuple[str, str]


@dataclass(frozen=True)
class RobotConfig:
    port: str
    baud: int
    default_speed: int
    default_step: int
    servos: dict[int, ServoConfig]
    allowed_speeds: tuple[int, ...] = (20, 50, 100)
    allowed_steps: tuple[int, ...] = (1, 5, 10, 20)


def load_config(path: Path | str) -> RobotConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    port = str(data["port"]).strip()
    baud = int(data["baud"])
    if not port:
        raise ValueError("serial port must not be empty")
    if baud <= 0:
        raise ValueError("baud must be greater than zero")
    allowed_speeds = tuple(int(value) for value in data["allowed_speeds"])
    allowed_steps = tuple(int(value) for value in data["allowed_steps"])
    if not allowed_speeds or len(set(allowed_speeds)) != len(allowed_speeds):
        raise ValueError("allowed_speeds must be unique and non-empty")
    if not allowed_steps or len(set(allowed_steps)) != len(allowed_steps):
        raise ValueError("allowed_steps must be unique and non-empty")
    for speed in allowed_speeds:
        validate_speed(speed)
    for step in allowed_steps:
        validate_step(step)
    default_speed = int(data["default_speed"])
    default_step = int(data["default_step"])
    if default_speed not in allowed_speeds:
        raise ValueError("default_speed must be in allowed_speeds")
    if default_step not in allowed_steps:
        raise ValueError("default_step must be in allowed_steps")

    servos: dict[int, ServoConfig] = {}
    for item in data["servos"]:
        servo_id = int(item["id"])
        if servo_id in servos:
            raise ValueError(f"duplicate servo ID {servo_id}")
        servo = ServoConfig(
            servo_id=servo_id,
            name=str(item["name"]),
            safe_min=int(item["safe_min"]),
            safe_max=int(item["safe_max"]),
            center=int(item["center"]),
            home=int(item["home"]),
            direction_labels=tuple(item["direction_labels"]),
        )
        if not (0 <= servo.safe_min <= servo.safe_max <= 1023):
            raise ValueError(f"invalid safe limits for ID {servo_id}")
        if not (servo.safe_min <= servo.center <= servo.safe_max):
            raise ValueError(f"center for ID {servo_id} is outside safe limits")
        if not (servo.safe_min <= servo.home <= servo.safe_max):
            raise ValueError(f"home for ID {servo_id} is outside safe limits")
        if (
            len(servo.direction_labels) != 2
            or len(set(servo.direction_labels)) != 2
            or any(not label.strip() for label in servo.direction_labels)
        ):
            raise ValueError(f"ID {servo_id} needs two distinct direction labels")
        servos[servo_id] = servo
    if set(servos) != {0, 1, 2, 3}:
        raise ValueError("servo IDs must be exactly 0, 1, 2, 3")
    return RobotConfig(
        port=port,
        baud=baud,
        default_speed=default_speed,
        default_step=default_step,
        servos=servos,
        allowed_speeds=allowed_speeds,
        allowed_steps=allowed_steps,
    )


def validate_speed(value: int) -> int:
    value = int(value)
    if value not in (20, 50, 100):
        raise ValueError("speed must be 20, 50, or 100; speed 0 is unsafe")
    return value


def validate_step(value: int) -> int:
    value = int(value)
    if value not in (1, 5, 10, 20):
        raise ValueError("step must be 1, 5, 10, or 20")
    return value


def validate_target(config: RobotConfig, servo_id: int, target: int) -> int:
    if servo_id not in config.servos:
        raise ValueError(f"unknown servo ID {servo_id}")
    target = int(target)
    servo = config.servos[servo_id]
    if not (servo.safe_min <= target <= servo.safe_max):
        raise ValueError(
            f"target {target} for ID {servo_id} is outside "
            f"{servo.safe_min}..{servo.safe_max}"
        )
    return target
