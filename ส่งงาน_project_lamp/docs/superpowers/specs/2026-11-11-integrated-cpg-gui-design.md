# Integrated Camera CPG Robot GUI Design

## Intent

Build one Pure Python application for Raspberry Pi 5 (8 GB) that is displayed on the operator PC through `ssh -X`. The application owns the USB camera, existing `face_vision(maincpg)` emotion/hormone/CPG controller, and the Feetech SCS15 bus. ROS 2 is deliberately not in the first hardware path.

## Goals

- Reuse `face_vision(maincpg)/face_vision/lamp_controller.py` as the authoritative CPG core.
- Reuse the tested Feetech bus code from `tools/servo_calibration_gui`.
- Show camera preview, accepted emotion, input status, and three hormone values.
- Provide Connect, Enable Motion, Center, Start CPG, Stop CPG, and Emergency Torque Off controls.
- Plot rolling Servo feedback and CPG output for all four joints.
- Run the 20 Hz CPG/servo loop on the Pi independently of X11 rendering latency.
- Support real hardware and a no-hardware mock mode.

## Non-goals

- ROS 2 integration, face-position tracking, LED hardware output, and automatic startup services.
- Full-range movement or copying the simulation range of 60–120 degrees directly to hardware.
- Claiming calibrated physical joint angles before linkage calibration is complete.

## Architecture

The application is split into a camera producer, the existing `LampController`, a hardware mapper, a single-owner runtime thread, and a Tkinter GUI. Only the runtime thread calls the Feetech bus. The GUI submits commands and renders immutable snapshots; it never performs serial I/O.

The runtime consumes `q_deg=[J1,J2,J3,J4]`, treats 90 degrees as the calibrated Center pose, attenuates the delta, converts it using the known raw directions, and clamps every target to a five-count working envelope around Center as well as the EEPROM safe limits.

## Calibrated Values

| ID | Joint | Center raw | Raw direction for positive CPG delta | EEPROM safe range |
|---:|---|---:|---:|---:|
| 0 | base | 410 | -1 | 0–870 |
| 1 | shoulder | 566 | -1 | 120–940 |
| 2 | elbow | 593 | +1 | 165–1023 |
| 3 | head | 176 | +1 | 0–720 |

Initial hardware settings are speed 20, loop 20 Hz, maximum offset ±5 raw, and nominal SCS15 conversion 300 degrees per 1023 counts for display only. Servo feedback plots must say that their degree values are nominal estimates and also show raw values numerically.

## Safety State Machine

- `DISCONNECTED`: no bus and all motion controls disabled.
- `CONNECTED`: IDs 0–3 pinged and all feedback lies inside configured safe limits.
- `ARMED`: current raw targets are synchronized before torque is enabled.
- `CENTERING`: Center has been commanded; fresh feedback is monitored until all joints settle or a bounded timeout enters FAULT and attempts torque-off.
- `RUNNING`: camera is active and CPG targets are emitted at 20 Hz.
- `STOPPING`: targets slew back to Center, then the system remains ARMED and holding Center.
- `FAULT`: no further motion commands; torque-off is attempted and the error remains visible.
- `EMERGENCY`: emergency event has priority over normal commands; torque-off is attempted for every ID and restart requires an explicit reconnect/re-arm sequence.

Emergency does not move toward Center. Emergency checkpoints run between calculations, reads, writes, and individual torque-enable operations. Closing the application requests robot Emergency before stopping the camera and keeps the status window visible until the serial owner confirms shutdown. Camera loss or stale capture timestamps clear camera readiness and return the CPG to Neutral; serial errors enter FAULT and attempt torque-off.

## GUI

The top row contains connection and camera status. A red Emergency Torque Off button remains available whenever a real or mock bus is open. Normal controls are gated by the runtime state.

The center contains a 320×240 preview updated at no more than 10 FPS plus emotion, input status, and hormone indicators. The bottom contains two custom Tk Canvas rolling plots covering approximately ten seconds:

- Servo Feedback: nominal relative degrees for IDs 0–3, with current raw counts in the legend/table.
- CPG Output: absolute CPG command degrees for J1–J4.

Custom Canvas plots avoid adding Matplotlib work to the 20 Hz controller and reduce X11 overhead.

## Testing

- Unit tests cover mapping, clamping, graph history, state transitions, command gating, emergency injection during active operations, stale capture timestamps, camera-owner shutdown, monitored Center timeout, reconnect, and confirmed shutdown torque-off.
- Hardware and camera are replaced by deterministic fakes in automated tests.
- A mock launcher provides synthetic face modes, CPG data, Servo feedback, and camera frames for GUI smoke testing.
- Existing Servo GUI and main CPG suites must remain green.

## Deployment Assumptions

- Raspberry Pi 5, 8 GB; 64-bit OS details will be confirmed before dependency installation.
- USB UVC camera appears as `/dev/video0` or another auto-detected `/dev/video*` path.
- CH343 appears as `/dev/ttyUSB0` or another configured serial path.
- The PC supplies an X server and connects with `ssh -X`.

