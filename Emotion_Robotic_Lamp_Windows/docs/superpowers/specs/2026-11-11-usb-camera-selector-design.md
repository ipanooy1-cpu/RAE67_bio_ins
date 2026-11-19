# USB Camera Selector Design

## Intent

Let the operator see which USB cameras are usable and select one in the integrated Camera CPG GUI before starting capture.

## Behavior

- Add a `SCAN CAMERAS` button and read-only camera dropdown above the preview.
- Probe OpenCV camera indices 0 through 9 and list only devices that both open and return one frame.
- Display `Camera <index>` plus an available backend/device label; retain the configured camera index when it remains valid, otherwise select the first result.
- Run discovery off the Tk main thread so X11 and the Emergency control remain responsive.
- Disable Scan and camera selection while a camera worker owns the device or while shutdown is in progress.
- `START CAMERA` uses the currently selected index. An empty result disables Start and shows an actionable status.
- Mock mode exposes one `Mock Camera` without probing hardware.

## Approaches

- Selected: bounded OpenCV probing (indices 0–9), because the same behavior works on Windows and Raspberry Pi.
- Rejected: Linux-only `/dev/video*` enumeration, because it does not cover Windows testing and a video node may still be unreadable.
- Rejected: manual numeric entry only, because it does not show which attached camera actually works.

## Safety and tests

- Every probe releases its temporary capture handle, including failed reads and exceptions.
- Discovery cannot replace or start a second camera owner.
- Tests cover filtering unreadable devices, releasing handles, preserving/falling back selection, worker factory index, mock behavior, and UI control locking.

