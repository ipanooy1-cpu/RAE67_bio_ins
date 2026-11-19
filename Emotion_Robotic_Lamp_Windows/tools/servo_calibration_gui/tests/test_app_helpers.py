import csv
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.servo_calibration_gui.app import (
    CommandCancelled,
    CommandWorker,
    append_csv_log,
    build_log_row,
    is_shutdown_completion,
    make_jog_observation,
    merge_direction_results,
    output_paths,
    parse_args,
    project_ui_state,
    try_append_csv_log,
)
from tools.servo_calibration_gui.controller import MotionResult


class FakeControllerState:
    def __init__(
        self,
        *,
        connected=False,
        motion_enabled=False,
        faulted=False,
        external_torque_detected=False,
    ):
        self.connected = connected
        self.motion_enabled = motion_enabled
        self.faulted = faulted
        self.external_torque_detected = external_torque_detected


class AppHelperTests(unittest.TestCase):
    def test_parse_args_selects_mock_and_smoke_modes(self):
        args = parse_args(["--mock", "--smoke-test"])
        self.assertTrue(args.mock)
        self.assertTrue(args.smoke_test)

    def test_ui_projection_never_enables_motion_controls_while_busy_or_faulted(self):
        disconnected = project_ui_state(None, busy=False)
        self.assertTrue(disconnected.can_connect)
        self.assertFalse(disconnected.can_move)

        ready = project_ui_state(FakeControllerState(connected=True), busy=False)
        self.assertTrue(ready.can_enable_motion)
        self.assertFalse(ready.can_move)

        enabled = project_ui_state(
            FakeControllerState(connected=True, motion_enabled=True), busy=False
        )
        self.assertTrue(enabled.can_move)

        busy = project_ui_state(
            FakeControllerState(connected=True, motion_enabled=True), busy=True
        )
        self.assertFalse(busy.can_move)
        self.assertTrue(busy.can_torque_off)

        faulted = project_ui_state(
            FakeControllerState(connected=True, faulted=True), busy=False
        )
        self.assertFalse(faulted.can_enable_motion)
        self.assertFalse(faulted.can_move)

    def test_csv_log_writes_header_and_operation_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "servo_test_log.csv"
            row = build_log_row(
                "jog+",
                servo_id=1,
                before=500,
                target=510,
                present=509,
                speed=50,
                status="ok",
                message="",
            )
            append_csv_log(path, row)
            with path.open(newline="", encoding="utf-8-sig") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["operation"], "jog+")
        self.assertEqual(rows[0]["servo_id"], "1")
        self.assertEqual(rows[0]["target"], "510")
        self.assertEqual(rows[0]["speed"], "50")

    def test_log_write_failure_is_reported_without_raising(self):
        row = build_log_row("read_all")
        with patch(
            "tools.servo_calibration_gui.app.append_csv_log",
            side_effect=PermissionError("locked"),
        ):
            error = try_append_csv_log(Path("blocked.csv"), row)
        self.assertIn("locked", error)

    def test_direction_results_merge_without_losing_other_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration_results.json"
            merge_direction_results(
                path, {"0": {"raw_increase_motion": "ซ้าย"}}, mode="real"
            )
            merge_direction_results(
                path, {"1": {"raw_increase_motion": "ยกขึ้น"}}, mode="real"
            )
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["directions"]["0"]["raw_increase_motion"], "ซ้าย")
        self.assertEqual(data["directions"]["1"]["raw_increase_motion"], "ยกขึ้น")
        self.assertEqual(data["mode"], "real")
        self.assertIn("updated_at", data)

    def test_mock_and_real_outputs_are_separate_and_rows_include_mode(self):
        real_log, real_directions = output_paths(False)
        mock_log, mock_directions = output_paths(True)
        self.assertNotEqual(real_log, mock_log)
        self.assertNotEqual(real_directions, mock_directions)
        self.assertEqual(build_log_row("connect", mode="mock")["mode"], "mock")

    def test_direction_observation_is_bound_to_successful_jog_id_and_sign(self):
        moved = MotionResult(0, 404, 414, 413, -1, False)
        observation = make_jog_observation(moved, +1)
        self.assertEqual(observation.servo_id, 0)
        self.assertEqual(observation.sign, +1)
        self.assertEqual(observation.displacement, 9)

        no_motion = MotionResult(3, 0, 0, 0, 0, True)
        self.assertIsNone(make_jog_observation(no_motion, -1))

    def test_cancel_invalidates_queued_motion_before_torque_off_completes(self):
        worker = CommandWorker()
        blocker_started = threading.Event()
        release_blocker = threading.Event()
        actions = []

        def blocker():
            blocker_started.set()
            release_blocker.wait(2)
            actions.append("blocker")

        worker.submit("blocker", blocker, priority=5)
        self.assertTrue(blocker_started.wait(1))
        worker.submit(
            "enable",
            lambda: actions.append("enable"),
            priority=10,
            cancellable=True,
        )
        worker.request_cancel()
        worker.submit("torque off", lambda: actions.append("off"), priority=0)
        release_blocker.set()

        results = []
        deadline = time.monotonic() + 2
        while len(results) < 3 and time.monotonic() < deadline:
            try:
                results.append(worker.results.get(timeout=0.2))
            except Exception:
                pass
        worker.stop()

        self.assertEqual(actions, ["blocker", "off"])
        cancelled = next(result for result in results if result.name == "enable")
        self.assertIsInstance(cancelled.error, CommandCancelled)

    def test_only_safe_close_result_completes_shutdown(self):
        self.assertFalse(is_shutdown_completion("connect"))
        self.assertFalse(is_shutdown_completion("go home"))
        self.assertTrue(is_shutdown_completion("safe close"))


if __name__ == "__main__":
    unittest.main()
