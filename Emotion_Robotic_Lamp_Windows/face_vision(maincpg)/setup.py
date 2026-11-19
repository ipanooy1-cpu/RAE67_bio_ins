from setuptools import setup

package_name = 'face_vision'
setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ROS2 developer',
    maintainer_email='developer@example.com',
    description='USB camera face tracking and expression publisher for ROS 2 Jazzy',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'face_node = face_vision.face_node:main',
        'lamp_node = face_vision.lamp_node:main',
        'live_lamp = face_vision.live_lamp:main',
    ]},
)
