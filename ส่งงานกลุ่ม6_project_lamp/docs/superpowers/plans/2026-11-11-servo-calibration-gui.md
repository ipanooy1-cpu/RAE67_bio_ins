# Servo Calibration GUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a slow, safety-gated Windows Tkinter GUI for testing and recording calibration of four Feetech SCS15 servos.

**Architecture:** A pure controller owns validation and state, depends on a small bus interface, and is exercised with a mock bus. A Feetech adapter wraps the official SDK. Tkinter submits hardware work to one worker thread and renders results on the main thread.

**Tech Stack:** Python 3.12, Tkinter, `ftservo-python-sdk`, standard-library `unittest`, JSON, CSV

**Spec:** `docs/superpowers/specs/2026-11-11-servo-calibration-gui-design.md`

## Global Constraints

- Real mode starts disconnected and never moves on startup or Connect.
- Default speed is 50 raw; allowed speed is 20, 50, or 100 and never 0.
- Default jog step is 10; allowed step is 1, 5, 10, or 20.
- IDs and targets: 0 base 0..870 center 410 home 404; 1 shoulder 120..940 center 566 home 271; 2 elbow 165..1023 center 593 home 946; 3 head 0..720 center 176 home 0.
- All bus access is serialized. Any communication fault disables motion and attempts Torque Off.
- No EEPROM writes.
- This workspace is not a Git repository, so commit steps are omitted.

## Review Focus

- Present Position outside configured limits must fault without automatic recovery: Task 2.
- Enabling torque must set Goal to current positions first: Task 2.
- Missing IDs or partial sync-write preparation must block all pose movement: Tasks 2 and 3.
- Torque Off must cancel queued motion and disable motion state: Tasks 2 and 4.
- Missing official SDK must show an actionable error while mock mode remains usable: Tasks 3 and 4.

---

### Task 1: Configuration and Pure Validation

**Files:**
- Create: `tools/servo_calibration_gui/__init__.py`
- Create: `tools/servo_calibration_gui/servo_config.json`
- Create: `tools/servo_calibration_gui/models.py`
- Test: `tools/servo_calibration_gui/tests/test_models.py`

**Interfaces:**
- Produces: `ServoConfig`, `RobotConfig`, `load_config(path)`, `validate_target(config, id, target)`, `validate_speed(value)`, `validate_step(value)`

- [x] Write tests for exact ID mappings/limits/poses, valid choices, unknown IDs, out-of-range targets, speed 0, and step over 20.
- [x] Run `python -m unittest tools.servo_calibration_gui.tests.test_models -v` and verify failure.
- [x] Implement the dataclasses, JSON loader, and validation functions.
- [x] Re-run the Task 1 tests and verify pass.

### Task 2: Safety Controller and Mock Bus

**Files:**
- Create: `tools/servo_calibration_gui/bus.py`
- Create: `tools/servo_calibration_gui/controller.py`
- Test: `tools/servo_calibration_gui/tests/test_controller.py`

**Interfaces:**
- Consumes: Task 1 config and validators.
- Produces: `ServoBus` protocol, `MockServoBus`, `CalibrationController.connect`, `enable_motion`, `jog`, `move_pose`, `torque_off_all`, `read_all`, and `record_direction`.

- [x] Write failing tests for read-only Connect, missing ID, out-of-range present position, safe enable sequence, jog-from-present, clamping/rejecting limit crossing, exact Home/Center maps, fault-triggered Torque Off, direction recording, and queued-motion cancellation state.
- [x] Run the Task 2 test module and verify failure.
- [x] Implement MockServoBus and the controller with no Tkinter dependency.
- [x] Re-run Task 1-2 tests and verify pass.

### Task 3: Official Feetech SDK Adapter

**Files:**
- Create: `tools/servo_calibration_gui/feetech_bus.py`
- Test: `tools/servo_calibration_gui/tests/test_feetech_bus.py`

**Interfaces:**
- Consumes: `ServoBus` behavior from Task 2.
- Produces: `FeetechBus(port, baud)`, lazy SDK import, ping/read/write/sync-write/torque methods, and actionable `SdkUnavailableError`.

- [x] Write tests using injected fake SDK objects for open/baud failure, ping result handling, `WritePos`, register 40 torque writes, `SyncWritePos` plus `txPacket`/`clearParam`, and missing SDK.
- [x] Run the adapter tests and verify failure.
- [x] Implement the SDK adapter without opening COM8 during import.
- [x] Re-run Task 1-3 tests and verify pass.

### Task 4: Tkinter GUI, Worker, and Logs

**Files:**
- Create: `tools/servo_calibration_gui/app.py`
- Create: `tools/servo_calibration_gui/tests/test_app_helpers.py`

**Interfaces:**
- Consumes: Task 2 controller and Task 3 real adapter.
- Produces: `ServoCalibrationApp`, single-worker command queue, high-priority Torque Off request, CSV log, JSON direction results, and `python -m tools.servo_calibration_gui.app [--mock]` entry point.

- [x] Write tests for CLI mode selection, log row generation, direction result merge, and UI state projection without creating a display.
- [x] Run helper tests and verify failure.
- [x] Implement the Tkinter window, confirmation dialogs, dynamic labels, connection/motion state, feedback table, and worker/result queues.
- [x] Re-run all unit tests and verify pass.
- [x] Run `python -m tools.servo_calibration_gui.app --mock --smoke-test` and verify construction/clean shutdown without mainloop.

### Task 5: Windows Launchers and Operator Guide

**Files:**
- Create: `tools/servo_calibration_gui/requirements.txt`
- Create: `tools/servo_calibration_gui/START_SERVO_GUI.bat`
- Create: `tools/servo_calibration_gui/START_SERVO_GUI_MOCK.bat`
- Create: `tools/servo_calibration_gui/README_TH.md`
- Modify: `ROBOT_TEST_DATA.txt`

**Interfaces:**
- Produces: double-click real/mock launch, dependency install instructions, exact safe operating sequence, and project change-history entry.

- [x] Add dependencies and launchers that run from any current directory.
- [x] Document closing FD, supporting the arm before Torque Off, Connect/read-only, Enable Motion, jog-first, pose buttons, logs, and emergency limitations.
- [x] Record the GUI path/default limits/speed in `ROBOT_TEST_DATA.txt` without marking hardware acceptance as complete.
- [x] Run all tests, compile all Python files, validate JSON, and launch mock smoke test.

