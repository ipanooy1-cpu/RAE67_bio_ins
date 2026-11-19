from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from pathlib import Path

def generate_launch_description():
    p = Path(get_package_share_directory('lamp_cad_full_preview'))
    description = (p / 'urdf' / 'lamp_staging.urdf').read_text()
    return LaunchDescription([
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             name='lamp_cad_full_staging_publisher', output='screen',
             parameters=[{'robot_description': description}])
    ])
