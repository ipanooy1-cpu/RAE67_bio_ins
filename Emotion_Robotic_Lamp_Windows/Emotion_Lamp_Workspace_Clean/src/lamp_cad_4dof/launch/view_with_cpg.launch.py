from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    p=Path(get_package_share_directory('lamp_cad_4dof'))
    model=(p/'urdf'/'lamp_cad_4dof.urdf').read_text()
    return LaunchDescription([
        Node(package='robot_state_publisher',executable='robot_state_publisher',name='lamp_cad_robot_state_publisher',parameters=[{'robot_description':model}],remappings=[('/joint_states','/cad_joint_states')],output='screen'),
        Node(package='lamp_cad_4dof',executable='joint_state_adapter.py',output='screen'),
        Node(package='lamp_control',executable='motion_controller',output='screen'),
        Node(package='lamp_cpg',executable='cpg_engine',output='screen'),
    ])
