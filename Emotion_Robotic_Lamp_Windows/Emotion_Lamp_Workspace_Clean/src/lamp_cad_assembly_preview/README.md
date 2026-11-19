# Three-source STL visual alignment preview (not a verified articulated robot)

Inputs: `Base1.stl`, `arm 1.stl`, `head2.stl` exactly as uploaded. File contents and original per-vertex coordinates are preserved, only `arm 1.stl` filename normalized to `arm1.stl`.

Assumption: STL coordinates are millimeters and all three exports share a common Fusion assembly origin. Each mesh is placed with the SAME static transform (X rotation 180 degrees, +0.065 m Z shift). This is just a visual alignment test, NOT complete assembly. The arm between arm1 and head2, servo casings, etc. may be absent and require placement verification.

No real moving joints. This preview uses 3 fixed joints to let robot_state_publisher create TF. Does not touch your existing lamp_control / lamp_cpg packages.

To use in the mounted /workspace:
1. Unzip under /workspace.
2. Copy /workspace/lamp_cad_assembly_preview_ws/src/lamp_cad_assembly_preview into /workspace/src/ (a single installed package copy).
3. `cd /workspace && colcon build --packages-select lamp_cad_assembly_preview --symlink-install && source /workspace/install/setup.bash`
4. `ros2 launch lamp_cad_assembly_preview preview_assembly.launch.py` in one Docker terminal; `rviz2 -d /workspace/src/lamp_cad_assembly_preview/rviz/assembly.rviz` with DISPLAY=:99 in another.
5. Only one robot_state_publisher publishing /robot_description in this session; stop older preview and motion launch first.
