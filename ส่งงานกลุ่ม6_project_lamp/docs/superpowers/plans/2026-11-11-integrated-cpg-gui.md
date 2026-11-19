# Integrated Camera CPG Robot GUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested Pure Python GUI that connects USB camera emotion input and the existing main CPG to four SCS15 servos with emergency stop and live graphs.

**Architecture:** A single runtime thread owns the Feetech bus and runs the 20 Hz controller. Camera and GUI communicate with it through bounded queues/events; pure mapping and state components remain independently testable. The existing calibration GUI and main CPG remain unchanged and are imported as dependencies.

**Tech Stack:** Python 3.12+, Tkinter Canvas, OpenCV/MediaPipe, Pillow, Feetech `scservo_sdk`, `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-11-integrated-cpg-gui-design.md`

## Global Constraints

- No ROS 2 in the first hardware path.
- Servo loop runs at 20 Hz and never waits for X11 drawing.
- Initial hardware envelope is Center ±5 raw at speed 20.
- Emergency never commands a recovery move; it attempts torque-off for IDs 0–3.
- Only the runtime thread accesses the serial bus.
- Real camera/SDK imports stay lazy so mock mode and tests work without hardware dependencies.
- The workspace is not a Git repository; replace commit steps with ledger updates and never initialize Git without user authorization.

## Review Focus

- Emergency requested while a normal move is pending must win before another sync-write.
- Serial failure during torque-off must remain a visible latched fault and must not report safe torque state.
- A stale or stopped camera must drive Neutral rather than retain an emotion indefinitely.
- Invalid/non-finite CPG values must never become Servo targets.
- Closing during RUNNING must stop scheduling writes and attempt torque-off exactly through the emergency path.

---

### Task 1: Hardware mapping and rolling graph data

**Files:**
- Create: `tools/robot_cpg_gui/__init__.py`
- Create: `tools/robot_cpg_gui/config.py`
- Create: `tools/robot_cpg_gui/mapping.py`
- Create: `tools/robot_cpg_gui/history.py`
- Create: `tools/robot_cpg_gui/robot_config.json`
- Test: `tools/robot_cpg_gui/tests/test_mapping.py`
- Test: `tools/robot_cpg_gui/tests/test_history.py`

**Interfaces:**
- Produces: `load_runtime_config(path) -> RuntimeConfig`.
- Produces: `HardwareMapper.targets_from_cpg(q_deg) -> dict[int, int]` and `feedback_relative_deg(raw_by_id) -> dict[int, float]`.
- Produces: `RollingHistory.append(timestamp, values)` and `series(now) -> dict[str, list[tuple[float,float]]]`.

- [ ] Write mapping/history tests for exact centers/directions, ±5 clamp, safe-limit clamp, non-finite rejection, time-window eviction, and non-monotonic timestamp rejection.
- [ ] Run the new tests and verify they fail because the package does not exist.
- [ ] Implement the smallest config, mapper, and history classes that pass.
- [ ] Run Task 1 tests and both baseline suites.
- [ ] Record Task 1 result in the plan ledger.

### Task 2: Safety runtime and emergency precedence

**Files:**
- Create: `tools/robot_cpg_gui/runtime.py`
- Create: `tools/robot_cpg_gui/tests/fakes.py`
- Create: `tools/robot_cpg_gui/tests/test_runtime.py`

**Interfaces:**
- Consumes: `RuntimeConfig`, `HardwareMapper`.
- Produces: `RobotRuntime.start()`, `submit(command)`, `request_emergency()`, `latest_snapshot()`, and `close()`.
- Produces: immutable `RuntimeSnapshot` with state, Servo feedback, CPG output, hormones, emotion, input status, and fault text.

- [ ] Write failing tests for connect/ping, arming current position, Start gating, 20 Hz target writes, Stop-to-Center, emergency-before-next-write, serial fault torque-off, and close-through-emergency.
- [ ] Run tests and confirm failures name missing runtime behavior.
- [ ] Implement the runtime state machine with a single bus-owning thread and priority emergency event.
- [ ] Run Task 2 tests and all Task 1 tests.
- [ ] Record Task 2 result in the plan ledger.

### Task 3: Main CPG and camera adapters

**Files:**
- Create: `tools/robot_cpg_gui/maincpg_adapter.py`
- Create: `tools/robot_cpg_gui/camera.py`
- Create: `tools/robot_cpg_gui/tests/test_maincpg_adapter.py`
- Create: `tools/robot_cpg_gui/tests/test_camera_mailbox.py`

**Interfaces:**
- Consumes: existing `face_vision.lamp_controller.LampController` and camera observation schema 1.
- Produces: `MainCpgAdapter.observe(observation, received_at)` and `step(now) -> CpgSnapshot`.
- Produces: latest-only `CameraMailbox` and lazy `UsbCameraWorker` emitting observation plus preview frame.

- [ ] Write failing tests for import fallback, finite four-joint output, stale input returning Neutral, and latest-only camera mailbox behavior.
- [ ] Run tests and confirm expected failures.
- [ ] Implement adapters without importing OpenCV/MediaPipe until a real camera worker starts.
- [ ] Run Task 3 tests plus the original main CPG suite.
- [ ] Connect `MainCpgAdapter` snapshots to `RobotRuntime` and add an integration test from observation to bounded raw targets.
- [ ] Record Task 3 result in the plan ledger.

### Task 4: Tkinter GUI, emergency control, and live plots

**Files:**
- Create: `tools/robot_cpg_gui/plot_widget.py`
- Create: `tools/robot_cpg_gui/app.py`
- Create: `tools/robot_cpg_gui/tests/test_app_projection.py`
- Create: `tools/robot_cpg_gui/tests/test_app_smoke.py`

**Interfaces:**
- Consumes: `RobotRuntime`, `RuntimeSnapshot`, `RollingHistory`, and camera preview mailbox.
- Produces: `project_ui(snapshot) -> UiProjection` and `RobotCpgApp`.

- [ ] Write failing projection tests proving unsafe buttons are disabled per state and Emergency stays available while connected.
- [ ] Write a failing smoke test that constructs and closes the GUI in mock mode without entering mainloop.
- [ ] Implement the GUI layout, 320×240 preview, state/hormone labels, Servo table, and two Canvas plots.
- [ ] Bind Emergency directly to `runtime.request_emergency()` and normal buttons to queued commands.
- [ ] Run projection/smoke tests and the complete new package suite.
- [ ] Record Task 4 result in the plan ledger.

### Task 5: Launchers, mock demonstration, and operator documentation

**Files:**
- Create: `tools/robot_cpg_gui/mock_components.py`
- Create: `tools/robot_cpg_gui/START_CPG_GUI.bat`
- Create: `tools/robot_cpg_gui/START_CPG_GUI_MOCK.bat`
- Create: `tools/robot_cpg_gui/start_cpg_gui.sh`
- Create: `tools/robot_cpg_gui/requirements-pi.txt`
- Create: `tools/robot_cpg_gui/README_TH.md`
- Modify: `ROBOT_TEST_DATA.txt`

**Interfaces:**
- Produces: `python -m tools.robot_cpg_gui.app --mock` for no-hardware validation and default real mode for Pi/Windows.

- [ ] Write a launcher/config test that parses real, mock, and smoke arguments without importing hardware dependencies.
- [ ] Run it and verify the launcher behavior is absent.
- [ ] Implement synthetic camera/CPG/Servo components and cross-platform launchers.
- [ ] Document `ssh -X`, X11 prerequisites, serial/video detection, safe startup order, Stop versus Emergency, and the nominal-angle warning.
- [ ] Run mock smoke, all new tests, all existing Servo GUI tests, and all existing main CPG tests.
- [ ] Record Task 5 result and final verification commands in the ledger.

### Task 6: Whole-change safety review

**Files:**
- Review all files created or modified by Tasks 1–5.

**Interfaces:**
- Consumes: completed implementation and test evidence.
- Produces: severity-graded review findings and one TDD fix pass for Critical/Important findings.

- [ ] Dispatch a fresh reviewer against the spec, plan, ledger, and complete file list.
- [ ] Re-grade findings by operator impact.
- [ ] For every Critical/Important finding, write a reproducing failing test, implement the fix, and rerun the full suite.
- [ ] Record deferred Minor findings and final verification in the ledger.

