import unittest
from unittest.mock import patch

from tools.servo_calibration_gui.bus import BusError
from tools.servo_calibration_gui.feetech_bus import FeetechBus, SdkUnavailableError


class FakeGroupSyncWrite:
    def __init__(self, packet):
        self.packet = packet
        self.tx_count = 0
        self.clear_count = 0

    def txPacket(self):
        self.tx_count += 1
        for servo_id, values in self.packet.sync_params.items():
            self.packet.positions[servo_id] = values[0]
        return self.packet.sync_result

    def clearParam(self):
        self.clear_count += 1
        self.packet.sync_params.clear()


class FakePacket:
    def __init__(self, _port):
        self.positions = {0: 404, 1: 271, 2: 946, 3: 0}
        self.torque = {0: False, 1: False, 2: False, 3: False}
        self.sync_params = {}
        self.sync_result = 0
        self.groupSyncWrite = FakeGroupSyncWrite(self)
        self.write_calls = []
        self.fail_prepare_ids = set()

    def ping(self, servo_id):
        if servo_id not in self.positions:
            return 0, -6, 0
        return 15, 0, 0

    def ReadPosSpeed(self, servo_id):
        return self.positions[servo_id], 0, 0, 0

    def ReadMoving(self, _servo_id):
        return 0, 0, 0

    def read1ByteTxRx(self, servo_id, address):
        if address != 40:
            raise AssertionError(f"unexpected address {address}")
        return int(self.torque[servo_id]), 0, 0

    def WritePos(self, servo_id, target, move_time, speed):
        self.write_calls.append((servo_id, target, move_time, speed))
        self.positions[servo_id] = target
        return 0, 0

    def write1ByteTxRx(self, servo_id, address, value):
        if address != 40:
            raise AssertionError(f"unexpected address {address}")
        self.torque[servo_id] = bool(value)
        return 0, 0

    def SyncWritePos(self, servo_id, target, move_time, speed):
        if servo_id in self.sync_params or servo_id in self.fail_prepare_ids:
            return False
        self.sync_params[servo_id] = (target, move_time, speed)
        return True

    def getTxRxResult(self, result):
        return f"comm={result}"

    def getRxPacketError(self, error):
        return f"servo={error}"


class FakePort:
    def __init__(self, name, open_result=True, baud_result=True):
        self.name = name
        self.open_result = open_result
        self.baud_result = baud_result
        self.closed = False
        self.baud = None

    def openPort(self):
        return self.open_result

    def setBaudRate(self, baud):
        self.baud = baud
        return self.baud_result

    def closePort(self):
        self.closed = True


class FakeSdk:
    COMM_SUCCESS = 0

    def __init__(self, *, open_result=True, baud_result=True):
        self.open_result = open_result
        self.baud_result = baud_result
        self.port = None
        self.packet = None

    def PortHandler(self, name):
        self.port = FakePort(name, self.open_result, self.baud_result)
        return self.port

    def scscl(self, port):
        self.packet = FakePacket(port)
        return self.packet


class FeetechBusTests(unittest.TestCase):
    def test_open_sets_port_and_one_megabaud(self):
        sdk = FakeSdk()
        bus = FeetechBus("COM8", 1_000_000, sdk_module=sdk)
        bus.open()
        self.assertEqual(sdk.port.name, "COM8")
        self.assertEqual(sdk.port.baud, 1_000_000)
        bus.close()
        self.assertTrue(sdk.port.closed)

    def test_open_or_baud_failure_raises_bus_error(self):
        with self.assertRaisesRegex(BusError, "open COM8"):
            FeetechBus("COM8", 1_000_000, sdk_module=FakeSdk(open_result=False)).open()
        sdk = FakeSdk(baud_result=False)
        with self.assertRaisesRegex(BusError, "baud"):
            FeetechBus("COM8", 1_000_000, sdk_module=sdk).open()
        self.assertTrue(sdk.port.closed)

    def test_ping_and_feedback_translate_sdk_results(self):
        sdk = FakeSdk()
        bus = FeetechBus("COM8", 1_000_000, sdk_module=sdk)
        bus.open()
        self.assertTrue(bus.ping(0))
        self.assertFalse(bus.ping(9))
        feedback = bus.read_feedback(0)
        self.assertEqual((feedback.position, feedback.speed), (404, 0))
        self.assertFalse(feedback.moving)
        self.assertFalse(feedback.torque_enabled)

    def test_write_position_uses_scscl_writepos_with_nonzero_speed(self):
        sdk = FakeSdk()
        bus = FeetechBus("COM8", 1_000_000, sdk_module=sdk)
        bus.open()
        bus.write_position(1, 281, 50)
        self.assertEqual(sdk.packet.write_calls, [(1, 281, 0, 50)])

    def test_torque_uses_register_40(self):
        sdk = FakeSdk()
        bus = FeetechBus("COM8", 1_000_000, sdk_module=sdk)
        bus.open()
        bus.set_torque(2, True)
        self.assertTrue(bus.read_feedback(2).torque_enabled)
        bus.set_torque(2, False)
        self.assertFalse(bus.read_feedback(2).torque_enabled)

    def test_sync_write_prepares_all_targets_then_transmits_and_clears(self):
        sdk = FakeSdk()
        bus = FeetechBus("COM8", 1_000_000, sdk_module=sdk)
        bus.open()
        targets = {0: 410, 1: 566, 2: 593, 3: 176}
        bus.sync_write_positions(targets, 50)
        self.assertEqual(sdk.packet.groupSyncWrite.tx_count, 1)
        self.assertGreaterEqual(sdk.packet.groupSyncWrite.clear_count, 2)
        self.assertEqual(sdk.packet.positions, targets)
        self.assertEqual(sdk.packet.sync_params, {})

    def test_partial_sync_preparation_never_transmits_or_changes_positions(self):
        sdk = FakeSdk()
        bus = FeetechBus("COM8", 1_000_000, sdk_module=sdk)
        bus.open()
        original = dict(sdk.packet.positions)
        sdk.packet.fail_prepare_ids = {2}

        with self.assertRaisesRegex(BusError, "ID 2"):
            bus.sync_write_positions({0: 410, 1: 566, 2: 593, 3: 176}, 50)

        self.assertEqual(sdk.packet.groupSyncWrite.tx_count, 0)
        self.assertEqual(sdk.packet.positions, original)
        self.assertEqual(sdk.packet.sync_params, {})

    def test_missing_sdk_has_actionable_error(self):
        bus = FeetechBus("COM8", 1_000_000)
        with patch("importlib.import_module", side_effect=ModuleNotFoundError("missing")):
            with self.assertRaisesRegex(SdkUnavailableError, "ftservo-python-sdk"):
                bus.open()


if __name__ == "__main__":
    unittest.main()
