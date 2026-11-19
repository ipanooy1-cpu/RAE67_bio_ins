import json
import tempfile
import unittest
from pathlib import Path

from tools.servo_calibration_gui.models import (
    load_config,
    validate_speed,
    validate_step,
    validate_target,
)


CONFIG_PATH = Path(__file__).parents[1] / "servo_config.json"


class RobotConfigTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(CONFIG_PATH)

    def test_loads_the_exact_calibrated_robot(self):
        actual = {
            servo_id: (
                servo.name,
                servo.safe_min,
                servo.safe_max,
                servo.center,
                servo.home,
            )
            for servo_id, servo in self.config.servos.items()
        }
        self.assertEqual(
            actual,
            {
                0: ("ฐาน", 0, 870, 410, 404),
                1: ("ไหล่", 120, 940, 566, 271),
                2: ("ศอก", 165, 1023, 593, 946),
                3: ("หัว", 0, 720, 176, 0),
            },
        )
        self.assertEqual(self.config.port, "COM8")
        self.assertEqual(self.config.baud, 1_000_000)
        self.assertEqual(self.config.default_speed, 50)
        self.assertEqual(self.config.default_step, 10)

    def test_validates_allowed_speed_and_rejects_zero_or_too_fast(self):
        self.assertEqual(validate_speed(50), 50)
        for invalid in (0, 1, 101, 1500):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_speed(invalid)

    def test_validates_allowed_step_and_rejects_over_twenty(self):
        self.assertEqual(validate_step(10), 10)
        for invalid in (0, 2, 21, 100):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_step(invalid)

    def test_rejects_unknown_servo_and_targets_outside_its_limits(self):
        with self.assertRaises(ValueError):
            validate_target(self.config, 99, 500)
        with self.assertRaises(ValueError):
            validate_target(self.config, 1, 119)
        with self.assertRaises(ValueError):
            validate_target(self.config, 1, 941)
        self.assertEqual(validate_target(self.config, 1, 120), 120)
        self.assertEqual(validate_target(self.config, 1, 940), 940)

    def test_rejects_config_that_breaks_required_ids_ranges_or_safe_defaults(self):
        original = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        invalid_variants = []

        missing_id = json.loads(json.dumps(original))
        missing_id["servos"] = missing_id["servos"][:-1]
        invalid_variants.append(missing_id)

        invalid_range = json.loads(json.dumps(original))
        invalid_range["servos"][2]["safe_max"] = 1024
        invalid_variants.append(invalid_range)

        unsafe_speed = json.loads(json.dumps(original))
        unsafe_speed["default_speed"] = 1500
        invalid_variants.append(unsafe_speed)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            for index, invalid in enumerate(invalid_variants):
                with self.subTest(index=index):
                    path.write_text(json.dumps(invalid), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_config(path)


if __name__ == "__main__":
    unittest.main()
