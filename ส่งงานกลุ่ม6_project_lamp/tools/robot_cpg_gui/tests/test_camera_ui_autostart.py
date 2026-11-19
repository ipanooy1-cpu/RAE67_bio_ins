import unittest
import tkinter as tk
from pathlib import Path

from tools.robot_cpg_gui.app import RobotCpgApp
from tools.robot_cpg_gui.camera import CameraMailbox
from tools.robot_cpg_gui.config import load_runtime_config
from tools.robot_cpg_gui.mapping import HardwareMapper
from tools.robot_cpg_gui.runtime import RuntimeCommand, RobotRuntime
from fakes import FakeBus, FakeCpgSource

DIR = Path(__file__).resolve().parents[1]


class CameraUiTests(unittest.TestCase):
    def test_camera_button_enables_auto_search_and_stop_disables_it(self):
        class Worker:
            def __init__(self):
                self.running = False
            def start(self):
                self.running = True
            def stop(self, timeout=0.0):
                self.running = False
                return True
            def is_alive(self):
                return self.running
        config = load_runtime_config(DIR / 'robot_config.json')
        runtime = RobotRuntime(config, HardwareMapper(config), FakeBus(), FakeCpgSource())
        root = tk.Tk()
        root.withdraw()
        app = RobotCpgApp(root, config, HardwareMapper(config), runtime, CameraMailbox(),
                          camera_factory=lambda index: Worker(), mock_mode=True)
        try:
            self.assertFalse(app.led_config.enabled)
            app._start_camera()
            self.assertTrue(app.camera_running)
            self.assertEqual(runtime._commands.get_nowait(), RuntimeCommand.CAMERA_AUTO_ON)
            app._stop_camera()
            self.assertFalse(app.camera_running)
            self.assertEqual(runtime._commands.get_nowait(), RuntimeCommand.CAMERA_AUTO_OFF)
            # _complete_camera_stop publishes an error and updates UI only;
            # no implicit arm/center/servo move is allowed.
            self.assertFalse(any(e[0] == 'sync' for e in runtime.bus.events))
        finally:
            app.close()
            runtime.process_once(0.0)
            root.update_idletasks()
            if not app.closed:
                app._poll_shutdown()


if __name__ == '__main__':
    unittest.main()
