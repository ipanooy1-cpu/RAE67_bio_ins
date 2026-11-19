from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    folder = Path(get_package_share_directory('lamp_cad_preview'))
    robot_description = (folder / 'urdf' / 'cad_parts_preview.urdf').read_text()
    return LaunchDescription([
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             name='lamp_cad_preview_publisher', parameters=[{'robot_description': robot_description}]),
    ])
