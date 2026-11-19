import unittest
from pathlib import Path

from tools.servo_calibration_gui.bus import MockServoBus
from tools.servo_calibration_gui.controller import CalibrationController, ControllerError
from tools.servo_calibration_gui.models import load_config


CONFIG_PATH = Path(__file__).parents[1] / "servo_config.json"
HOME_POSITIONS = {0: 404, 1: 271, 2: 946, 3: 0}


class CancelAfterFirstTorqueBus(MockServoBus):
    def __init__(self, positions, cancel):
        super().__init__(positions)
        self.cancel = cancel
        self.enabled_count = 0

    def set_torque(self, servo_id, enabled):
        super().set_torque(servo_id, enabled)
        if enabled:
            self.enabled_count += 1
            if self.enabled_count == 1:
                self.cancel["requested"] = True


class OutOfRangeAfterWriteBus(MockServoBus):
    def write_position(self, servo_id, target, speed):
        super().write_position(servo_id, target, speed)
        self.positions[servo_id] = -1


class CalibrationControllerTests(unittest.TestCase):
    def make_controller(self, **bus_kwargs):
        config = load_config(CONFIG_PATH)
        bus = MockServoBus(HOME_POSITIONS, **bus_kwargs)
        return CalibrationController(config, bus), bus

    def test_connect_is_read_only_and_reports_all_positions(self):
        controller, bus = self.make_controller()
        readings = controller.connect()

        self.assertEqual(
            {servo_id: reading.position for servo_id, reading in readings.items()},
            HOME_POSITIONS,
        )
        self.assertTrue(controller.connected)
        self.assertFalse(controller.motion_enabled)
        self.assertEqual(bus.position_write_count, 0)
        self.assertEqual(bus.torque_write_count, 0)

    def test_missing_id_faults_and_blocks_motion(self):
        controller, _ = self.make_controller(missing_ids={2})
        with self.assertRaisesRegex(ControllerError, "ID 2"):
            controller.connect()
        self.assertTrue(controller.faulted)
        self.assertFalse(controller.motion_enabled)

    def test_present_position_outside_limits_faults_without_recovery_move(self):
        positions = dict(HOME_POSITIONS)
        positions[1] = 119
        config = load_config(CONFIG_PATH)
        bus = MockServoBus(positions)
        controller = CalibrationController(config, bus)

        with self.assertRaisesRegex(ControllerError, "outside safe range"):
            controller.connect()
        self.assertEqual(bus.positions[1], 119)
        self.assertEqual(bus.position_write_count, 0)

    def test_read_all_out_of_range_always_turns_torque_off(self):
        controller, bus = self.make_controller()
        controller.connect()
        controller.enable_motion()
        bus.positions[1] = 119

        with self.assertRaisesRegex(ControllerError, "outside safe range"):
            controller.read_all()

        self.assertTrue(controller.faulted)
        self.assertFalse(controller.motion_enabled)
        self.assertTrue(all(enabled is False for enabled in bus.torque_enabled.values()))

    def test_enable_motion_syncs_current_goals_before_enabling_torque(self):
        controller, bus = self.make_controller()
        controller.connect()
        bus.trace.clear()

        controller.enable_motion()

        self.assertTrue(controller.motion_enabled)
        sync_call = ("sync_write", HOME_POSITIONS, 50)
        sync_index = bus.trace.index(sync_call)
        first_torque_index = next(
            index
            for index, call in enumerate(bus.trace)
            if call[0] == "torque"
        )
        self.assertLess(sync_index, first_torque_index)
        self.assertEqual(
            bus.trace[first_torque_index:],
            [("torque", servo_id, True) for servo_id in range(4)],
        )

    def test_existing_torque_must_be_turned_off_before_enable(self):
        controller, bus = self.make_controller(torque_enabled={0: True})
        controller.connect()
        self.assertTrue(controller.external_torque_detected)
        with self.assertRaisesRegex(ControllerError, "Torque Off"):
            controller.enable_motion()

        controller.torque_off_all()
        controller.enable_motion()
        self.assertTrue(controller.motion_enabled)
        self.assertTrue(all(bus.torque_enabled.values()))

    def test_failed_torque_off_blocks_enable_until_verified_retry_succeeds(self):
        controller, bus = self.make_controller()
        controller.connect()
        controller.enable_motion()
        bus.fail_torque_ids = {0}

        with self.assertRaisesRegex(ControllerError, "ID 0"):
            controller.torque_off_all()

        self.assertTrue(controller.faulted)
        self.assertTrue(controller.external_torque_detected)
        self.assertTrue(controller.torque_state_unknown)
        with self.assertRaises(ControllerError):
            controller.enable_motion()

        bus.fail_torque_ids.clear()
        controller.torque_off_all()
        self.assertFalse(controller.faulted)
        self.assertFalse(controller.torque_state_unknown)
        controller.enable_motion()
        self.assertTrue(controller.motion_enabled)

    def test_jog_uses_fresh_present_position_and_clamps_at_limit(self):
        controller, bus = self.make_controller()
        controller.connect()
        controller.enable_motion()
        bus.positions[1] = 500

        moved = controller.jog(1, +1, step=10, speed=50)
        self.assertEqual((moved.before, moved.target, moved.present), (500, 510, 510))
        self.assertFalse(moved.clipped)

        bus.positions[3] = 5
        clipped = controller.jog(3, -1, step=10, speed=50)
        self.assertEqual((clipped.before, clipped.target, clipped.present), (5, 0, 0))
        self.assertTrue(clipped.clipped)

    def test_pose_targets_match_calibrated_home_and_center(self):
        controller, bus = self.make_controller()
        controller.connect()
        controller.enable_motion()

        home = controller.move_pose("home", speed=50)
        self.assertEqual({key: value.target for key, value in home.items()}, HOME_POSITIONS)

        center = controller.move_pose("center", speed=50)
        self.assertEqual(
            {key: value.target for key, value in center.items()},
            {0: 410, 1: 566, 2: 593, 3: 176},
        )
        self.assertEqual(bus.positions, {0: 410, 1: 566, 2: 593, 3: 176})

    def test_pose_speed_is_fixed_at_fifty(self):
        controller, bus = self.make_controller()
        controller.connect()
        controller.enable_motion()
        before = dict(bus.positions)
        with self.assertRaisesRegex(ValueError, "fixed at 50"):
            controller.move_pose("center", speed=100)
        self.assertEqual(bus.positions, before)

    def test_communication_failure_faults_and_turns_all_torque_off(self):
        controller, bus = self.make_controller()
        controller.connect()
        controller.enable_motion()
        bus.fail_operation = "write_position"

        with self.assertRaisesRegex(ControllerError, "write_position"):
            controller.jog(0, +1, step=10, speed=50)

        self.assertTrue(controller.faulted)
        self.assertFalse(controller.motion_enabled)
        self.assertTrue(all(enabled is False for enabled in bus.torque_enabled.values()))

    def test_records_observed_motion_for_plus_and_minus(self):
        controller, _ = self.make_controller()
        controller.connect()

        plus = controller.record_direction(0, +1, "ซ้าย")
        minus = controller.record_direction(0, -1, "ขวา")

        self.assertEqual(plus["0"]["raw_increase_motion"], "ซ้าย")
        self.assertEqual(minus["0"]["raw_decrease_motion"], "ขวา")
        with self.assertRaises(ValueError):
            controller.record_direction(0, +1, "ยกขึ้น")

    def test_torque_off_disables_motion_and_clears_external_torque_flag(self):
        controller, bus = self.make_controller()
        controller.connect()
        controller.enable_motion()

        controller.torque_off_all()

        self.assertFalse(controller.motion_enabled)
        self.assertFalse(controller.external_torque_detected)
        self.assertTrue(all(enabled is False for enabled in bus.torque_enabled.values()))

    def test_cancel_request_blocks_new_motion_and_turns_torque_off(self):
        cancel = {"requested": False}
        config = load_config(CONFIG_PATH)
        bus = MockServoBus(HOME_POSITIONS)
        controller = CalibrationController(
            config,
            bus,
            cancel_requested=lambda: cancel["requested"],
        )
        controller.connect()
        controller.enable_motion()
        writes_before_cancel = bus.position_write_count
        cancel["requested"] = True

        with self.assertRaisesRegex(ControllerError, "cancel"):
            controller.jog(0, +1, step=10, speed=50)

        self.assertEqual(bus.position_write_count, writes_before_cancel)
        self.assertFalse(controller.motion_enabled)
        self.assertTrue(all(enabled is False for enabled in bus.torque_enabled.values()))

    def test_cancel_during_enable_checks_before_each_torque_on(self):
        cancel = {"requested": False}
        config = load_config(CONFIG_PATH)
        bus = CancelAfterFirstTorqueBus(HOME_POSITIONS, cancel)
        controller = CalibrationController(
            config,
            bus,
            cancel_requested=lambda: cancel["requested"],
        )
        controller.connect()

        with self.assertRaisesRegex(ControllerError, "cancel"):
            controller.enable_motion()

        self.assertFalse(controller.motion_enabled)
        self.assertTrue(all(enabled is False for enabled in bus.torque_enabled.values()))

    def test_polling_out_of_range_faults_and_turns_torque_off_immediately(self):
        config = load_config(CONFIG_PATH)
        bus = OutOfRangeAfterWriteBus({0: 404, 1: 271, 2: 946, 3: 10})
        controller = CalibrationController(config, bus)
        controller.connect()
        controller.enable_motion()

        with self.assertRaisesRegex(ControllerError, "outside safe range"):
            controller.jog(3, -1, step=10, speed=50)

        self.assertTrue(controller.faulted)
        self.assertTrue(all(enabled is False for enabled in bus.torque_enabled.values()))


if __name__ == "__main__":
    unittest.main()
