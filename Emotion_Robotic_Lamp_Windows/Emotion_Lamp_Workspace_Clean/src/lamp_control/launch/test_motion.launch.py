import os

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command, FindExecutable
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    description_path = get_package_share_directory(
        'lamp_description'
    )

    xacro_file = os.path.join(
        description_path,
        'urdf',
        'lamp.urdf.xacro'
    )

    robot_description = ParameterValue(
        Command([
            FindExecutable(name='xacro'),
            ' ',
            xacro_file
        ]),
        value_type=str
    )

    return LaunchDescription([

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[{
                'robot_description': robot_description
            }],
            output='screen'
        ),

        Node(
            package='lamp_control',
            executable='motion_controller',
            name='lamp_motion_controller',
            output='screen'
        )

    ])
