#!/bin/bash
set -e

cd /workspace
source /opt/ros/jazzy/setup.bash

echo "Checking ROS 2 packages..."
test -d /workspace/src/lamp_cad_4dof
test -d /workspace/src/lamp_cpg
test -d /workspace/src/lamp_control

echo "Building ROS 2 workspace..."
colcon build --symlink-install
source /workspace/install/setup.bash

export DISPLAY=:99
export LIBGL_ALWAYS_SOFTWARE=1
export QT_QPA_PLATFORM=xcb
export QT_X11_NO_MITSHM=1
unset LIBGL_ALWAYS_INDIRECT

echo "Starting Xvfb..."
if ! pgrep -x Xvfb >/dev/null; then
    Xvfb :99 -screen 0 1280x800x24 \
      +extension GLX +render -noreset \
      >/tmp/lamp_xvfb.log 2>&1 &
fi

sleep 2

echo "Preparing VNC password..."
mkdir -p /workspace/.vnc

if [ ! -f /workspace/.vnc/passwd ]; then
    echo "VNC password is not configured."
    echo "Please enter a VNC password:"
    x11vnc -storepasswd /workspace/.vnc/passwd
fi

if [ ! -s /workspace/.vnc/passwd ]; then
    echo "ERROR: VNC password file was not created."
    exit 1
fi

chmod 600 /workspace/.vnc/passwd

echo "Starting VNC..."
if ! pgrep -x x11vnc >/dev/null; then
    x11vnc -display :99 -rfbport 5900 \
      -rfbauth /workspace/.vnc/passwd -forever -shared -noxdamage \
      >/tmp/lamp_vnc.log 2>&1 &
fi

echo "Starting CAD + CPG..."
ros2 launch lamp_cad_4dof view_with_cpg.launch.py &
LAUNCH_PID=$!

sleep 4

echo "Starting RViz2..."
rviz2 -d /workspace/src/lamp_cad_4dof/rviz/lamp_4dof.rviz &
RVIZ_PID=$!

echo ""
echo "======================================"
echo "Emotion Robotic Lamp is running"
echo "VNC: localhost:5901"
echo "======================================"

wait "$LAUNCH_PID"
