# Local Editable CPG Design

## Intent

Replace the `robot_cpg_gui` dependency on `face_vision(maincpg).face_vision.lamp_controller` with a self-contained CPG implementation under `tools/robot_cpg_gui`. The new implementation uses the SO(2), hormone-memory, pose interpolation, head-fade, clamp, and slew behavior from the user's pasted model. Operators can inspect and edit every live CPG parameter from the GUI without editing Python.

The camera/MediaPipe perception pipeline may continue using its existing vision modules. This change owns the CPG/controller formula and configuration, not the face classifier.

## Selected Approach

Use a validated versioned JSON profile, a local pure-Python CPG engine, and a GUI editor. Editing is allowed only while CPG motion is stopped. `Save & Apply` validates the entire profile, writes it atomically, then swaps in a fresh controller as one transaction.

Alternatives considered:

- Live sliders during motion: rejected because a changed pose, gain, or limit can create a sudden target change.
- Edit only pose angles: rejected because the user requested all behavior parameters in the GUI.
- Replace the module with the pasted file verbatim: rejected because the pasted file ends mid-statement at `t = round` and is not executable.

## Default Behavior from the Pasted Model

Joint order remains `J1=ID0 base`, `J2=ID1 shoulder`, `J3=ID2 elbow`, `J4=ID3 head`.

| Mode | Time | J1 | J2 | J3 | J4 |
|---|---:|---:|---:|---:|---:|
| Neutral | 0, 1, 5 s | 80 | 90 | 60 | 90 |
| Happy | 0 s | 80 | 90 | 70 | 90 |
| Happy | 1 s | 80 | 95 | 73 | 98 |
| Happy | 5 s | 80 | 100 | 75 | 105 |
| Sad | 0 s | 80 | 90 | 70 | 105 |
| Sad | 1 s | 80 | 85 | 65 | 100 |
| Sad | 5 s | 80 | 80 | 60 | 85 |
| Sad | 10 s | 80 | 80 | 60 | 60 |
| Confused | 0 s | 80 | 90 | 70 | 90 |
| Confused | 1 s | 85 | 90 | 68 | 85 |
| Confused | 5 s | 120 | 90 | 65 | 80 |

The complete canonical defaults are:

- Global: `so2_alpha=1.10`, warmup `200`, oscillation blend `1.0 s`, slew `20 degree/s`, loop-derived `DT=0.05 s`.
- Input gate preserved from the camera integration: strength `0.35`, stable `0.30 s`, timeout `0.50 s`, samples `3`.
- Neutral: `phi=0.20`, gains `[2,2,2,2]`, white `#ffffff`, brightness `[(0,.6),(1,.6),(5,.6),(10,.6)]`.
- Happy: `phi=0.35`, gains `[6,8,6,8]`, yellow `#ffd43b`, brightness `[(0,.6),(1,.8),(5,1),(10,1)]`.
- Sad: `phi=0.12`, gains `[2,2,2,8]`, blue `#377dff`, brightness `[(0,.6),(1,.45),(5,.25),(10,.1)]`, head fade `(5,10)`.
- Confused: `phi=0.25`, gains `[20,2,3,5]`, purple `#b05cff`, brightness `[(0,.6),(1,.75),(5,.45),(10,.65)]`.
- Hormones: Happy `tau_up=.5/tau_down=1.5`, Sad `2/3`, Confused `.4/1` seconds.

Because all pasted presets use the same `alpha=1.10` and the pasted formula does not hormone-mix alpha, the profile exposes one truthful global `so2_alpha` rather than four duplicate fields.

## Components

### `cpg_profile.py` and `cpg_profile.json`

The versioned profile contains every parameter that affects the live CPG:

- Global: schema version, `so2_alpha`, warmup steps, oscillation blend time, maximum slew speed in degrees/second.
- Input gate: minimum expression strength, stable time, timeout, and minimum sample count.
- Four joint limits.
- Hormones Happy/Sad/Confused: `tau_up` and `tau_down`.
- Each mode Neutral/Happy/Sad/Confused: `phi`, four gains, ordered pose keyframes, light color, brightness keyframes, and optional head-fade interval.

`DT` is derived from the robot control loop (`1 / loop_hz`) so the CPG and Servo writer cannot run at contradictory rates. Simulation-only duration, CSV, plotting, and CLI selection are not live parameters and are not included.

Validation is all-or-nothing:

- All numeric fields must be finite.
- Times are nonnegative and strictly increasing; the first pose and brightness keyframes start at zero.
- Each pose has exactly four angles.
- Joint limits satisfy `60 <= min < 90 < max <= 120`; every range must contain the 90-degree controller start, and poses must fall inside their corresponding limits.
- `0.01 <= so2_alpha <= 2.0`; `-pi <= phi <= pi`; each gain is `0..30 degrees`.
- Warmup is an integer `0..5000`; minimum samples is an integer `1..100`.
- Slew is `0.1..20 degree/s`; oscillation blend is `0..10 s`.
- Gate strength is `0..1`; stable time is `0..10 s`; timeout is greater than stable time and no more than `10 s`.
- Hormone time constants are `DT..60 s`; keyframe and head-fade times are `0..60 s`.
- Colors are `#RRGGBB`; brightness and hormone values stay in valid ranges.
- `tau_up/tau_down >= DT`; input timeout exceeds stable time; warmup/sample counts are bounded integers.
- Head fade has `0 <= start < end`. It is optional for every mode; the pasted default defines it only for Sad.

The hard hardware envelope, EEPROM safe limits, centers, directions, `180°/1024`, Servo speed, and Emergency behavior remain in `robot_config.json` and are not editable from the CPG tab.

### `cpg_engine.py`

This local module owns the pure formula:

- expression debounce/watchdog;
- forward-Euler hormone state;
- normalized emotion weights;
- SO(2) oscillator step;
- pose and brightness interpolation;
- hormone-weighted centers, gains, phase and light;
- one-second oscillation blend-in;
- Sad J4 timed descent and oscillation fade;
- joint-limit clamp and 20 Hz slew limiting.

The blend duration comes from the profile and defaults to one second. When Sad begins, the engine captures the live J4 command and substitutes it for the first Sad J4 keyframe; later editable keyframes are followed literally. This generalizes the pasted simulation behavior without a hard-coded `105 -> 60` remap.

It has no Tkinter, camera, serial, ROS, or external `face_vision(maincpg)` dependency.

### `maincpg_adapter.py`

The adapter imports the local engine. It retains the existing camera mailbox contract and stale-frame safety behavior.

It exposes a thread-safe `profile_snapshot()` and `apply_profile(profile)` API. Apply constructs a new controller completely before taking the swap lock. Under the lock it swaps the controller and resets camera readiness, requiring a fresh valid observation before CPG can start. `step()` and `observe()` use the same lock, so the runtime never sees a partially changed model.

### GUI: `CPG Settings` tab

Add a third notebook tab with a scrollable form:

- `Global & Input`: alpha, warmup, oscillation blend, slew speed, gate parameters, hormone time constants, joint min/max.
- One sub-tab per emotion: phi, gains J1-J4, editable pose-keyframe table, light color, brightness-keyframe table, and head fade when present.
- Buttons: `VALIDATE`, `RELOAD SAVED`, `RESET TO PASTED DEFAULTS`, and `SAVE & APPLY`.
- Status line clearly shows `Modified`, `Valid`, `Applied`, or the first validation error.

All numeric edits are text entries so exact values can be typed. Pose/brightness rows can be added and removed, except that at least one row is required.

Settings controls and `Save & Apply` are disabled while runtime state is `RUNNING`, `CENTERING`, `STOPPING`, `FAULT`, `EMERGENCY`, or during shutdown. They are enabled in `DISCONNECTED`, `CONNECTED`, or settled `ARMED`. Validation and reload never command Servo motion.

`Save & Apply` is ordered as: parse form -> validate complete profile -> atomically replace JSON -> apply controller -> log success. Any failure leaves both the previous file and active controller unchanged.

## Motion and Failure Safety

- Applying a profile never writes a Servo target.
- A newly applied controller starts at `[90, 90, 90, 90]` and uses the configured slew limit, so the next CPG run ramps toward the selected pose.
- Existing `Arm -> successful Center -> camera ready -> Start CPG` gating remains mandatory.
- Runtime mapping still clamps every command to the ±171-raw envelope and per-ID safe limits.
- Emergency Torque Off and its motion-transaction precedence are unchanged.
- Invalid/missing profile at application startup is an actionable startup error; it does not silently fall back for real hardware. Mock mode may explicitly use the built-in pasted defaults.

## Tests and Acceptance

- Profile parsing, complete field coverage, validation boundaries, JSON round-trip, and atomic-save failure.
- Exact pasted default poses/gains/phase/hormones/light/head-fade.
- SO(2), hormone, interpolation, bounds, Sad head descent, and slew behavior.
- Adapter imports no external CPG controller, preserves camera timeout behavior, and swaps profiles atomically.
- GUI exposes every profile field, rejects invalid input, does not save partial data, and locks editing in unsafe runtime states.
- Camera observation -> local CPG -> degree mapper -> raw Servo target integration.
- Existing 69 integrated tests, 38 Servo GUI tests, main vision tests, compile, and mock smoke remain green.

Physical acceptance remains separate: begin with supported joints and Emergency ready, verify directions and angles with a protractor, then test full emotional trajectories.
