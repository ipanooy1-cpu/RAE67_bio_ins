from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class BusError(RuntimeError):
    """Communication or device error reported by a servo bus."""


@dataclass(frozen=True)
class ServoFeedback:
    position: int
    speed: int = 0
    moving: bool = False
    torque_enabled: bool = False


class ServoBus(Protocol):
    def open(self) -> None: ...

    def close(self) -> None: ...

    def ping(self, servo_id: int) -> bool: ...

    def read_feedback(self, servo_id: int) -> ServoFeedback: ...

    def write_position(self, servo_id: int, target: int, speed: int) -> None: ...

    def sync_write_positions(self, targets: dict[int, int], speed: int) -> None: ...

    def set_torque(self, servo_id: int, enabled: bool) -> None: ...


class MockServoBus:
    """In-memory bus used by --mock mode and controller tests."""

    def __init__(
        self,
        positions: dict[int, int],
        *,
        missing_ids: set[int] | None = None,
        torque_enabled: dict[int, bool] | None = None,
    ) -> None:
        self.positions = dict(positions)
        self.missing_ids = set(missing_ids or ())
        self.torque_enabled = {servo_id: False for servo_id in positions}
        self.torque_enabled.update(torque_enabled or {})
        self.is_open = False
        self.trace: list[tuple] = []
        self.position_write_count = 0
        self.torque_write_count = 0
        self.fail_operation: str | None = None
        self.fail_torque_ids: set[int] = set()

    def _maybe_fail(self, operation: str) -> None:
        if self.fail_operation == operation:
            self.fail_operation = None
            raise BusError(f"mock {operation} failure")

    def _require_servo(self, servo_id: int) -> None:
        if servo_id in self.missing_ids or servo_id not in self.positions:
            raise BusError(f"ID {servo_id} is unavailable")

    def open(self) -> None:
        self._maybe_fail("open")
        self.is_open = True
        self.trace.append(("open",))

    def close(self) -> None:
        self.is_open = False
        self.trace.append(("close",))

    def ping(self, servo_id: int) -> bool:
        self._maybe_fail("ping")
        self.trace.append(("ping", servo_id))
        return servo_id in self.positions and servo_id not in self.missing_ids

    def read_feedback(self, servo_id: int) -> ServoFeedback:
        self._maybe_fail("read_feedback")
        self._require_servo(servo_id)
        self.trace.append(("read", servo_id))
        return ServoFeedback(
            position=self.positions[servo_id],
            speed=0,
            moving=False,
            torque_enabled=self.torque_enabled.get(servo_id, False),
        )

    def write_position(self, servo_id: int, target: int, speed: int) -> None:
        self._maybe_fail("write_position")
        self._require_servo(servo_id)
        self.trace.append(("write", servo_id, target, speed))
        self.position_write_count += 1
        self.positions[servo_id] = target

    def sync_write_positions(self, targets: dict[int, int], speed: int) -> None:
        self._maybe_fail("sync_write_positions")
        for servo_id in targets:
            self._require_servo(servo_id)
        copied_targets = dict(targets)
        self.trace.append(("sync_write", copied_targets, speed))
        self.position_write_count += len(copied_targets)
        self.positions.update(copied_targets)

    def set_torque(self, servo_id: int, enabled: bool) -> None:
        self._maybe_fail("set_torque")
        self._require_servo(servo_id)
        if not enabled and servo_id in self.fail_torque_ids:
            raise BusError(f"mock Torque Off failure for ID {servo_id}")
        self.trace.append(("torque", servo_id, bool(enabled)))
        self.torque_write_count += 1
        self.torque_enabled[servo_id] = bool(enabled)

