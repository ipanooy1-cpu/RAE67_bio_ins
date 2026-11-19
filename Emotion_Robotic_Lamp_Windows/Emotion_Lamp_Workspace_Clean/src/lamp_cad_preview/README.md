# Lamp CAD parts preview (not a kinematic URDF)

The assets in meshes/ are unchanged STL bytes from lamp_assembly_export(2).zip.
The generated URDF lays available parts out in a 4-column inspection grid and
recenters each mesh using its bounding box. It does NOT reproduce the assembled
CAD or moving joint positions. No CPG integration yet.

This source ZIP contained 18 STL files; expected meshes for hidden parts
arm2, servo3, head, test and 3 root bodies were absent.

## Quick start
Mac Terminal:
  unzip ~/Downloads/lamp_cad_preview_ws.zip -d ~/emotion_robotic_lamp
  docker exec -it emotion_lamp_jazzy bash
Docker Terminal:
  cp -a /workspace/lamp_cad_preview_ws/src/lamp_cad_preview /workspace/src/
  cd /workspace
  colcon build --packages-select lamp_cad_preview --symlink-install
  source /workspace/install/setup.bash
  ros2 launch lamp_cad_preview preview.launch.py

Open RViz with the existing Xvfb/VNC display in a second Docker terminal:
  source /workspace/install/setup.bash
  export DISPLAY=:99 LIBGL_ALWAYS_SOFTWARE=1 QT_QPA_PLATFORM=xcb QT_X11_NO_MITSHM=1
  rviz2 -d /workspace/src/lamp_cad_preview/rviz/preview.rviz

Do not concurrently launch lamp_control/test_motion.launch.py or lamp_description/display.launch.py for this preview because they also publish /robot_description, possibly conflicting with the preview display. The preview can be stopped with Ctrl+C. Restart normal CPG workflow afterward.

### Mesh list from actual user ZIP
- 0000_aecesry_1.stl | base:1+aecesry (1):1 | size mm [100.0, 100.0, 9.0]
- 0002_base2.stl | base2:1 | size mm [100.0, 100.0, 55.5]
- 0003_acesry.stl | arm1:1+acesry:1 | size mm [35.8, 56.4, 48.0]
- 0005_servo.stl | servo:1 | size mm [40.0, 20.0, 51.1]
- 0006_servo2.stl | servo2:1 | size mm [40.0, 20.0, 51.1]
- 0009_arm3.stl | arm3:1 | size mm [40.0, 178.3, 80.0]
- 0010_ac2.stl | arm servo:1+STS3215_03a v1:1+ac2:1 | size mm [20.0, 20.0, 2.1]
- 0011_ac1.stl | arm servo:1+STS3215_03a v1:1+ac1:1 | size mm [20.0, 20.0, 8.8]
- 0024_Servo_SC15.f3d.stl | servo 4:1+Servo SC15.f3d :1 | size mm [40.0, 51.1, 20.0]
- 0027_Servo_SC15.f3d.stl | servo5:1+Servo SC15.f3d :1 | size mm [40.0, 51.1, 20.0]
- 0029_aecesry.stl | head2:1+aecesry:1 | size mm [10.0, 35.5, 30.2]
- 0030_aecesry.stl | head2:1+aecescry:1+aecesry:2 | size mm [10.0, 35.5, 30.2]
- 0033_ac2.stl | arm servo test:1+arm servo:2+STS3215_03a v1:1+ac2:1 | size mm [20.0, 20.0, 2.1]
- 0034_ac1.stl | arm servo test:1+arm servo:2+STS3215_03a v1:1+ac1:1 | size mm [20.0, 20.0, 8.8]
- 0046_ac2.stl | arm servo test:1+arm servo:3+STS3215_03a v1:1+ac2:1 | size mm [20.0, 20.0, 2.1]
- 0047_ac1.stl | arm servo test:1+arm servo:3+STS3215_03a v1:1+ac1:1 | size mm [20.0, 20.0, 8.8]
- 0059_ac2.stl | arm servo test:1+arm servo:4+STS3215_03a v1:1+ac2:1 | size mm [20.0, 20.0, 2.1]
- 0060_ac1.stl | arm servo test:1+arm servo:4+STS3215_03a v1:1+ac1:1 | size mm [20.0, 20.0, 8.8]
