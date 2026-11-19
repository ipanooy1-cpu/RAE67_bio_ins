from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    folder = Path(get_package_share_directory('lamp_cad_assembly_preview'))
    urdf = (folder / 'urdf' / 'lamp_three_parts.urdf').read_text()
    return LaunchDescription([
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             name='lamp_three_parts_robot_state_publisher',
             parameters=[{'robot_description': urdf}]),
    ])
