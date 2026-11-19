from __future__ import annotations

import copy
import time
from dataclasses import dataclass
from typing import Callable

from .bus import BusError, ServoBus, ServoFeedback
from .models import RobotConfig, validate_speed, validate_step, validate_target


class ControllerError(RuntimeError):
    """A safety or communication condition that blocks motion."""


@dataclass(frozen=True)
class MotionResult:
    servo_id: int
    before: int
    target: int
    present: int
    error: int
    clipped: bool = False


class CalibrationController:
    POSITION_TOLERANCE = 8

    def __init__(
        self,
        config: RobotConfig,
        bus: ServoBus,
        *,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> None:
        self.config = config
        self.bus = bus
        self.connected = False
        self.motion_enabled = False
        self.faulted = False
        self.external_torque_detected = False
        self.torque_state_unknown = False
        self.last_error = ""
        self._fault_recoverable_by_torque_off = False
        self.direction_observations: dict[str, dict[str, str]] = {}
        self._cancel_requested = cancel_requested or (lambda: False)

    def connect(self) -> dict[int, ServoFeedback]:
        if self.connected:
            return self.read_all()
        try:
            self.bus.open()
            self.connected = True
            missing = [
                servo_id
                for servo_id in sorted(self.config.servos)
                if not self.bus.ping(servo_id)
            ]
            if missing:
                self._mark_fault(f"missing servo ID {', '.join(map(str, missing))}")
                raise ControllerError(f"ไม่พบ Servo ID {', '.join(map(str, missing))}")
            readings = self._read_all_unchecked()
            self._validate_present_positions(readings)
            self.external_torque_detected = any(
                reading.torque_enabled for reading in readings.values()
            )
            return readings
        except ControllerError as exc:
            self._mark_fault(str(exc))
            raise
        except Exception as exc:
            self._mark_fault(str(exc))
            raise ControllerError(f"connect failed: {exc}") from exc

    def disconnect(self) -> None:
        if not self.connected:
            return
        torque_error: ControllerError | None = None
        try:
            self.torque_off_all()
        except ControllerError as exc:
            torque_error = exc
        finally:
            self.bus.close()
            self.connected = False
            self.motion_enabled = False
        if torque_error is not None:
            raise torque_error

    def read_all(self) -> dict[int, ServoFeedback]:
        self._require_connected()
        try:
            readings = self._read_all_unchecked()
            self._validate_present_positions(readings)
            return readings
        except ControllerError as exc:
            self._enter_fault(str(exc))
            raise
        except Exception as exc:
            self._enter_fault(str(exc))
            raise ControllerError(f"read failed: {exc}") from exc

    def enable_motion(self) -> None:
        self._require_connected()
        if self.faulted:
            raise ControllerError(f"faulted: {self.last_error}")
        if self.external_torque_detected or self.torque_state_unknown:
            raise ControllerError("พบ Torque เปิดอยู่ กรุณากด Torque Off ก่อน Enable Motion")
        try:
            self._check_cancel()
            speed = validate_speed(self.config.default_speed)
            readings = self._read_all_unchecked()
            self._validate_present_positions(readings)
            current_targets = {
                servo_id: reading.position for servo_id, reading in readings.items()
            }
            self._check_cancel()
            self.bus.sync_write_positions(current_targets, speed)
            for servo_id in sorted(self.config.servos):
                self._check_cancel()
                self.bus.set_torque(servo_id, True)
            self.motion_enabled = True
        except Exception as exc:
            self._enter_fault(str(exc), recoverable=self._is_cancel_error(exc))
            if isinstance(exc, ControllerError):
                raise
            raise ControllerError(f"enable motion failed: {exc}") from exc

    def jog(
        self,
        servo_id: int,
        sign: int,
        *,
        step: int,
        speed: int,
    ) -> MotionResult:
        self._require_motion()
        if sign not in (-1, 1):
            raise ValueError("jog sign must be -1 or +1")
        step = validate_step(step)
        speed = validate_speed(speed)
        servo = self.config.servos.get(servo_id)
        if servo is None:
            raise ValueError(f"unknown servo ID {servo_id}")
        try:
            self._check_cancel()
            before_feedback = self.bus.read_feedback(servo_id)
            validate_target(self.config, servo_id, before_feedback.position)
            requested = before_feedback.position + sign * step
            target = min(max(requested, servo.safe_min), servo.safe_max)
            validate_target(self.config, servo_id, target)
            self._check_cancel()
            self.bus.write_position(servo_id, target, speed)
            present = self._wait_for_one(
                servo_id, target, before_feedback.position, speed
            )
            return MotionResult(
                servo_id=servo_id,
                before=before_feedback.position,
                target=target,
                present=present,
                error=present - target,
                clipped=target != requested,
            )
        except Exception as exc:
            self._enter_fault(str(exc), recoverable=self._is_cancel_error(exc))
            if isinstance(exc, (ControllerError, ValueError)):
                raise
            raise ControllerError(f"jog failed: {exc}") from exc

    def move_pose(self, pose: str, *, speed: int) -> dict[int, MotionResult]:
        self._require_motion()
        if int(speed) != 50:
            raise ValueError("Home/Center speed is fixed at 50")
        speed = validate_speed(50)
        if pose not in ("home", "center"):
            raise ValueError("pose must be 'home' or 'center'")
        targets = {
            servo_id: getattr(servo, pose)
            for servo_id, servo in self.config.servos.items()
        }
        for servo_id, target in targets.items():
            validate_target(self.config, servo_id, target)
        try:
            self._check_cancel()
            before_readings = self._read_all_unchecked()
            self._validate_present_positions(before_readings)
            self._check_cancel()
            self.bus.sync_write_positions(targets, speed)
            final_readings = self._wait_for_many(targets, before_readings, speed)
            return {
                servo_id: MotionResult(
                    servo_id=servo_id,
                    before=before_readings[servo_id].position,
                    target=target,
                    present=final_readings[servo_id].position,
                    error=final_readings[servo_id].position - target,
                    clipped=False,
                )
                for servo_id, target in targets.items()
            }
        except Exception as exc:
            self._enter_fault(str(exc), recoverable=self._is_cancel_error(exc))
            if isinstance(exc, (ControllerError, ValueError)):
                raise
            raise ControllerError(f"move {pose} failed: {exc}") from exc

    def torque_off_all(self) -> None:
        was_recoverable = self._fault_recoverable_by_torque_off
        errors = self._attempt_torque_off_and_verify()
        if errors:
            message = "Torque Off incomplete: " + "; ".join(errors)
            self._mark_fault(message)
            self._fault_recoverable_by_torque_off = True
            raise ControllerError(message)
        if was_recoverable:
            self.faulted = False
            self.last_error = ""
            self._fault_recoverable_by_torque_off = False

    def record_direction(self, servo_id: int, sign: int, motion: str):
        if sign not in (-1, 1):
            raise ValueError("direction sign must be -1 or +1")
        servo = self.config.servos.get(servo_id)
        if servo is None:
            raise ValueError(f"unknown servo ID {servo_id}")
        if motion not in servo.direction_labels:
            raise ValueError(
                f"motion for ID {servo_id} must be one of {servo.direction_labels}"
            )
        key = "raw_increase_motion" if sign > 0 else "raw_decrease_motion"
        record = self.direction_observations.setdefault(str(servo_id), {})
        record[key] = motion
        return copy.deepcopy(self.direction_observations)

    def _read_all_unchecked(self) -> dict[int, ServoFeedback]:
        return {
            servo_id: self.bus.read_feedback(servo_id)
            for servo_id in sorted(self.config.servos)
        }

    def _validate_present_positions(
        self, readings: dict[int, ServoFeedback]
    ) -> None:
        for servo_id, reading in readings.items():
            servo = self.config.servos[servo_id]
            if not (servo.safe_min <= reading.position <= servo.safe_max):
                raise ControllerError(
                    f"ID {servo_id} position {reading.position} outside safe range "
                    f"{servo.safe_min}..{servo.safe_max}"
                )

    def _wait_for_one(
        self, servo_id: int, target: int, before: int, speed: int
    ) -> int:
        timeout = min(30.0, max(5.0, abs(target - before) / speed + 3.0))
        deadline = time.monotonic() + timeout
        while True:
            self._check_cancel()
            feedback = self.bus.read_feedback(servo_id)
            self._validate_present_positions({servo_id: feedback})
            if not feedback.moving and abs(feedback.position - target) <= self.POSITION_TOLERANCE:
                return feedback.position
            if time.monotonic() >= deadline:
                raise BusError(f"ID {servo_id} motion timeout")
            time.sleep(0.1)

    def _wait_for_many(
        self,
        targets: dict[int, int],
        before: dict[int, ServoFeedback],
        speed: int,
    ) -> dict[int, ServoFeedback]:
        max_delta = max(
            abs(target - before[servo_id].position)
            for servo_id, target in targets.items()
        )
        timeout = min(30.0, max(5.0, max_delta / speed + 3.0))
        deadline = time.monotonic() + timeout
        while True:
            self._check_cancel()
            readings = self._read_all_unchecked()
            self._validate_present_positions(readings)
            settled = all(
                not readings[servo_id].moving
                and abs(readings[servo_id].position - target)
                <= self.POSITION_TOLERANCE
                for servo_id, target in targets.items()
            )
            if settled:
                return readings
            if time.monotonic() >= deadline:
                raise BusError("pose motion timeout")
            time.sleep(0.1)

    def _require_connected(self) -> None:
        if not self.connected:
            raise ControllerError("not connected")

    def _require_motion(self) -> None:
        self._require_connected()
        if self.faulted:
            raise ControllerError(f"faulted: {self.last_error}")
        if not self.motion_enabled:
            raise ControllerError("motion is not enabled")

    def _check_cancel(self) -> None:
        if self._cancel_requested():
            raise ControllerError("motion cancelled by Torque Off request")

    def _mark_fault(self, message: str) -> None:
        self.faulted = True
        self.motion_enabled = False
        self.last_error = message

    def _enter_fault(self, message: str, *, recoverable: bool = False) -> None:
        self._mark_fault(message)
        self._fault_recoverable_by_torque_off = recoverable
        errors = self._attempt_torque_off_and_verify()
        if errors:
            self.last_error += "; Torque Off incomplete: " + "; ".join(errors)

    def _attempt_torque_off_and_verify(self) -> list[str]:
        errors: list[str] = []
        for servo_id in sorted(self.config.servos):
            try:
                self.bus.set_torque(servo_id, False)
            except Exception as exc:
                errors.append(f"ID {servo_id}: {exc}")
        for servo_id in sorted(self.config.servos):
            try:
                feedback = self.bus.read_feedback(servo_id)
                if feedback.torque_enabled:
                    errors.append(f"ID {servo_id}: torque still enabled")
            except Exception as exc:
                errors.append(f"ID {servo_id}: verify failed: {exc}")
        self.motion_enabled = False
        self.torque_state_unknown = bool(errors)
        self.external_torque_detected = bool(errors)
        return errors

    @staticmethod
    def _is_cancel_error(error: Exception) -> bool:
        return isinstance(error, ControllerError) and "cancel" in str(error).lower()

