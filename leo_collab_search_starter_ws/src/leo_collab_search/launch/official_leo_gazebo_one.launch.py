"""Start one official Leo Rover Gazebo simulation in the package corridor world.

This launch intentionally delegates to leo_gz_bringup. It requires:
  sudo apt install ros-$ROS_DISTRO-leo-simulator
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    leo_gz = FindPackageShare('leo_gz_bringup')
    pkg = FindPackageShare('leo_collab_search')
    return LaunchDescription([
        DeclareLaunchArgument('robot_ns', default_value='leo1'),
        DeclareLaunchArgument('sim_world', default_value=PathJoinSubstitution([pkg, 'worlds', 'corridor_rooms.sdf'])),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([leo_gz, 'launch', 'leo_gz.launch.py'])),
            launch_arguments={
                'robot_ns': LaunchConfiguration('robot_ns'),
                'sim_world': LaunchConfiguration('sim_world'),
            }.items(),
        ),
    ])
