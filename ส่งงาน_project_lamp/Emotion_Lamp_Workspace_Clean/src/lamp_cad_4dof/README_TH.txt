Lamp CAD 4 DOF — ROS 2 Jazzy

This package is generated from final STL (Servo SC15(1).stl) and implements 4 REVOLUTE joints:
J1 base_link -> base2_link: local Z
J2 base2_link -> arm1_link: local X
J3 arm1_link -> arm3_link: local X
J4 arm3_link -> head2_link: local X

Five linked visual STLs are segmented from FINAL ASSEMBLED reference STL, so at zero radians all pieces share the original assembly positions. Small disconnected geometry far away from the lamp was excluded (kept in reference/excluded_distant_fragment.stl). Group assignment for secondary brackets/servos is approximate.

VERY IMPORTANT: Exact mechanical pivot centres and which servo body stays on each side of a joint cannot be proven from the final STL alone. The initial axes are user-confirmed, but pivot coordinates are approximate from geometry. This is a visualization/test rig, not motor-safe URDF. Review hinge rotation in RViz before operating physical servos. Joint limits/effort/velocity are demo placeholders. No collision/inertial model supplied.

Install on Mac:
  unzip ~/Downloads/lamp_cad_4dof.zip -d ~/emotion_robotic_lamp/src/
On Docker, ensure no duplicate copy of same package exists outside src within /workspace, then:
  cd /workspace
  # Optional: sync joint names with original lamp_description:
  python3 src/lamp_cad_4dof/urdf/sync_original_joint_names.py
  colcon build --packages-select lamp_cad_4dof --symlink-install
  source install/setup.bash
  ros2 launch lamp_cad_4dof view_cad.launch.py gui:=true
In another terminal (with Xvfb/VNC running):
  source /workspace/install/setup.bash
  export DISPLAY=:99 LIBGL_ALWAYS_SOFTWARE=1 QT_QPA_PLATFORM=xcb QT_X11_NO_MITSHM=1
  unset LIBGL_ALWAYS_INDIRECT
  rviz2 -d /workspace/src/lamp_cad_4dof/rviz/lamp_4dof.rviz

Test GUI sliders one joint at a time.

To fix the pivot locations, edit src/lamp_cad_4dof/urdf/joint_pivots.json -> each pivot_ros_m, then:
  python3 src/lamp_cad_4dof/urdf/build_urdf.py
  colcon build --packages-select lamp_cad_4dof --symlink-install
  source install/setup.bash
  # Restart view_cad.launch.py and RViz if needed.

To test with CPG (after confirming original controller publishes J1,J2,J3,J4 in order):
  STOP other joint_state_publisher and lamp_control/lamp_cpg instances first.
  ros2 launch lamp_cad_4dof view_with_cpg.launch.py
  # RViz opened separately; manual interaction cmd
  ros2 topic pub --once /lamp/interaction_enabled std_msgs/msg/Bool "{data: true}"
  ros2 topic pub --once /lamp/personality_mode std_msgs/msg/String "{data: happy}"

IMPORTANT: Do not run lamp_control test_motion.launch.py at the same time as view_with_cpg.launch.py. Both publish robot descriptions. If the controller's /joint_states order differs, adapt mappings in scripts/joint_state_adapter.py.
