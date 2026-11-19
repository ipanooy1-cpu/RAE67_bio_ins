# Direct-Drive CPG Degrees Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the four direct-drive joints follow main CPG angles 1:1 in nominal physical degrees while preserving monitored Center, safe raw limits, faults, and Emergency Torque Off.

**Architecture:** The mapper converts absolute CPG degrees around 90° directly to nominal SCS15 raw counts at scale 1.0 and exposes absolute feedback degrees. Runtime tracks whether Center has settled and rejects CPG start until it has. The GUI plots Servo feedback and CPG command on the same 60–120° scale.

**Tech Stack:** Python 3, Tkinter, SCS15/Feetech SDK abstraction, unittest.

**Spec:** `docs/superpowers/specs/2026-11-11-direct-drive-cpg-degrees-design.md`

## Global Constraints

- Centers remain `410, 566, 593, 176`; directions remain `-1, -1, +1, +1`.
- SCS15 `180° / 1024 raw`, scale `1.0`, envelope `±171 raw`, CPG limits `60–120°`.
- Speed remains 20 and loop remains 20 Hz.
- Existing EEPROM limits, monitored Stop/Center, serial fault handling, and Emergency behavior remain unchanged.
- `START CPG` requires a successful Center settlement after every Arm.

## Review Focus

- 60°/120° direction mapping per ID must not invert a joint.
- Raw rounding must keep nominal angular error at or below half a count.
- Out-of-range CPG/fake input must remain inside ±171 and EEPROM limits.
- Arming away from Center must not permit Start CPG before Center settles.
- Emergency during Center or full-range CPG write must retain transaction precedence.

---

### Task 1: Nominal 1:1 mapping and absolute feedback

**Files:**
- Modify: `tools/robot_cpg_gui/robot_config.json`
- Modify: `tools/robot_cpg_gui/mapping.py`
- Modify: `tools/robot_cpg_gui/tests/test_mapping.py`

**Interfaces:**
- Produces: `targets_from_cpg(q_deg)` at direct-drive scale and `feedback_absolute_deg(raw_by_id)`.

- [x] Change mapping tests first to assert raw targets at 60°, 80°, 90°, 100°, and 120°, ±171 clamping, and absolute feedback; run and confirm RED.
- [x] Set scale `1.0`, envelope `171`, and implement absolute feedback conversion; run mapping tests GREEN.

### Task 2: Require successful Center before CPG start

**Files:**
- Modify: `tools/robot_cpg_gui/runtime.py`
- Modify: `tools/robot_cpg_gui/tests/test_runtime.py`

**Interfaces:**
- Consumes: existing `CENTERING` settlement path.
- Produces: internal Center-ready latch reset by Arm and set only after Center/Stop settles.

- [x] Add failing tests for Start rejection immediately after Arm and acceptance only after Center settles.
- [x] Implement the Center-ready latch without changing Emergency transaction interlocks; run runtime tests GREEN.

### Task 3: Absolute-degree GUI and documentation

**Files:**
- Modify: `tools/robot_cpg_gui/app.py`
- Modify: `tools/robot_cpg_gui/tests/test_app_smoke.py`
- Modify: `tools/robot_cpg_gui/README_TH.md`
- Modify: `ROBOT_TEST_DATA.txt`

**Interfaces:**
- Consumes: `feedback_absolute_deg()`.
- Produces: Servo feedback graph/table in absolute nominal degrees on a 60–120° axis.

- [x] Add failing GUI test that Center raw renders as 90° and graph data uses absolute angles.
- [x] Change graph/table labels and history conversion; run GUI tests GREEN.
- [x] Document full-range direct-drive behavior, Center-before-Start, nominal accuracy, and pending physical acceptance.
- [x] Run integrated GUI, Servo baseline, main CPG baseline, compileall, and mock smoke verification.

