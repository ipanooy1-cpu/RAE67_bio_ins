from __future__ import annotations

import importlib
from types import ModuleType

from .bus import BusError, ServoFeedback


TORQUE_ENABLE_ADDRESS = 40


class SdkUnavailableError(BusError):
    """Raised when the official Feetech Python SDK is not installed."""


class FeetechBus:
    def __init__(
        self,
        port: str,
        baud: int,
        *,
        sdk_module: ModuleType | object | None = None,
    ) -> None:
        self.port_name = port
        self.baud = int(baud)
        self._sdk = sdk_module
        self._port = None
        self._packet = None
        self._is_open = False

    def _load_sdk(self):
        if self._sdk is not None:
            return self._sdk
        try:
            self._sdk = importlib.import_module("scservo_sdk")
        except ModuleNotFoundError as exc:
            raise SdkUnavailableError(
                "ไม่พบ Feetech SDK: รัน python -m pip install ftservo-python-sdk"
            ) from exc
        return self._sdk

    def open(self) -> None:
        if self._is_open:
            return
        sdk = self._load_sdk()
        port = sdk.PortHandler(self.port_name)
        if not port.openPort():
            raise BusError(f"cannot open {self.port_name}; close Feetech FD first")
        if not port.setBaudRate(self.baud):
            port.closePort()
            raise BusError(f"cannot set baud {self.baud} on {self.port_name}")
        self._port = port
        self._packet = sdk.scscl(port)
        self._is_open = True

    def close(self) -> None:
        if self._port is not None:
            self._port.closePort()
        self._is_open = False
        self._port = None
        self._packet = None

    def ping(self, servo_id: int) -> bool:
        packet = self._require_packet()
        _model, comm_result, servo_error = packet.ping(int(servo_id))
        if comm_result != self._sdk.COMM_SUCCESS:
            return False
        self._check_result(comm_result, servo_error, f"ping ID {servo_id}")
        return True

    def read_feedback(self, servo_id: int) -> ServoFeedback:
        packet = self._require_packet()
        position, speed, comm_result, servo_error = packet.ReadPosSpeed(servo_id)
        self._check_result(comm_result, servo_error, f"read position ID {servo_id}")
        moving, comm_result, servo_error = packet.ReadMoving(servo_id)
        self._check_result(comm_result, servo_error, f"read moving ID {servo_id}")
        torque, comm_result, servo_error = packet.read1ByteTxRx(
            servo_id, TORQUE_ENABLE_ADDRESS
        )
        self._check_result(comm_result, servo_error, f"read torque ID {servo_id}")
        return ServoFeedback(
            position=int(position),
            speed=int(speed),
            moving=bool(moving),
            torque_enabled=bool(torque),
        )

    def write_position(self, servo_id: int, target: int, speed: int) -> None:
        if speed <= 0:
            raise ValueError("speed must be greater than zero")
        packet = self._require_packet()
        comm_result, servo_error = packet.WritePos(
            int(servo_id), int(target), 0, int(speed)
        )
        self._check_result(comm_result, servo_error, f"write position ID {servo_id}")

    def sync_write_positions(self, targets: dict[int, int], speed: int) -> None:
        if speed <= 0:
            raise ValueError("speed must be greater than zero")
        packet = self._require_packet()
        group = packet.groupSyncWrite
        group.clearParam()
        try:
            for servo_id, target in sorted(targets.items()):
                if not packet.SyncWritePos(int(servo_id), int(target), 0, int(speed)):
                    raise BusError(f"cannot prepare sync-write for ID {servo_id}")
            comm_result = group.txPacket()
            if comm_result != self._sdk.COMM_SUCCESS:
                message = packet.getTxRxResult(comm_result)
                raise BusError(f"sync-write failed: {message}")
        finally:
            group.clearParam()

    def set_torque(self, servo_id: int, enabled: bool) -> None:
        packet = self._require_packet()
        comm_result, servo_error = packet.write1ByteTxRx(
            int(servo_id), TORQUE_ENABLE_ADDRESS, int(bool(enabled))
        )
        action = "enable" if enabled else "disable"
        self._check_result(comm_result, servo_error, f"{action} torque ID {servo_id}")

    def _require_packet(self):
        if not self._is_open or self._packet is None:
            raise BusError("servo port is not open")
        return self._packet

    def _check_result(self, comm_result: int, servo_error: int, operation: str) -> None:
        if comm_result != self._sdk.COMM_SUCCESS:
            message = self._packet.getTxRxResult(comm_result)
            raise BusError(f"{operation}: {message}")
        if servo_error:
            message = self._packet.getRxPacketError(servo_error)
            raise BusError(f"{operation}: {message}")

