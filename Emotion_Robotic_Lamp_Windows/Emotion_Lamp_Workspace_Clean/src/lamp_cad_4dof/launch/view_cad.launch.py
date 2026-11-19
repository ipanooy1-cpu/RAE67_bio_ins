from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg=Path(get_package_share_directory('lamp_cad_4dof'))
    model=(pkg/'urdf'/'lamp_cad_4dof.urdf').read_text()
    gui=LaunchConfiguration('gui')
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='false',description='Run joint slider GUI instead of non-GUI joint state publisher'),
        Node(package='robot_state_publisher',executable='robot_state_publisher',name='lamp_cad_robot_state_publisher', output='screen',parameters=[{'robot_description':model}]),
        Node(package='joint_state_publisher',executable='joint_state_publisher',name='lamp_cad_joint_state_publisher',condition=UnlessCondition(gui),output='screen',parameters=[{'robot_description':model}]),
        Node(package='joint_state_publisher_gui',executable='joint_state_publisher_gui',name='lamp_cad_joint_state_publisher_gui',condition=IfCondition(gui),output='screen',parameters=[{'robot_description':model}]),
    ])
