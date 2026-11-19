# USB Camera Selector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add responsive USB-camera discovery and selection to the integrated CPG GUI.

**Architecture:** A focused discovery module probes OpenCV indices 0–9 and always releases temporary handles. The Tk app runs discovery on a background thread, receives immutable results through a queue, and creates the existing camera worker with the selected index.

**Tech Stack:** Python 3, OpenCV, Tkinter/ttk, threading, queue, unittest.

**Spec:** `docs/superpowers/specs/2026-11-11-usb-camera-selector-design.md`

## Global Constraints

- Never probe while a camera worker owns a device.
- Never call Tk from the discovery thread.
- Probe only indices 0–9 and list only devices that open and return a frame.
- Release every temporary capture handle.
- Mock mode performs no hardware probing.

## Review Focus

- A device opens but cannot return a frame: omit it and release it.
- A probe raises: continue scanning and release any created handle.
- The configured selection disappears: select the first usable camera.
- Scan is clicked twice or while capture is running: do not create concurrent owners.
- Window closes during scanning: ignore late results and do not call destroyed Tk widgets.

---

### Task 1: Discovery, selection UI, and worker index

**Files:**
- Create: `tools/robot_cpg_gui/camera_discovery.py`
- Create: `tools/robot_cpg_gui/tests/test_camera_discovery.py`
- Modify: `tools/robot_cpg_gui/app.py`
- Modify: `tools/robot_cpg_gui/tests/test_app_smoke.py`
- Modify: `tools/robot_cpg_gui/README_TH.md`

**Interfaces:**
- Produces: `CameraChoice(index: int, label: str)` and `discover_cameras(max_index: int = 9, capture_factory=None) -> list[CameraChoice]`.
- GUI consumes a `camera_factory(index: int)` and stores the selected integer index.

- [ ] Write failing discovery tests proving readable indices are returned, unreadable/exception indices are omitted, and every handle is released.
- [ ] Run discovery tests and confirm RED because `camera_discovery` does not exist.
- [ ] Implement bounded discovery with lazy OpenCV import and deterministic labels.
- [ ] Run discovery tests and confirm GREEN.
- [ ] Write failing GUI tests for mock choice, selection fallback, control locking, and passing the selected index to the worker factory.
- [ ] Run GUI tests and confirm RED for the missing selector behavior.
- [ ] Add dropdown, `SCAN CAMERAS`, background thread/queue polling, mock choice, and selected-index worker construction.
- [ ] Run the integrated GUI suite, existing Servo suite, main CPG suite, compileall, and mock smoke test.
- [ ] Update Thai usage documentation.

