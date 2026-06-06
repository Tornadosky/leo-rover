"""Start two official Leo Rovers in Gazebo.

Note: official spawn_robot.launch.py may not expose x/y spawn offsets in all
versions. This launch is a convenience wrapper for smoke testing. If both robots
spawn too close, Codex should switch to a direct custom spawn launch or use the
team's Humble sensor simulator as a reference.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    leo_gz = FindPackageShare('leo_gz_bringup')
    pkg = FindPackageShare('leo_collab_search')
    return LaunchDescription([
        DeclareLaunchArgument('robot1_ns', default_value='leo1'),
        DeclareLaunchArgument('robot2_ns', default_value='leo2'),
        DeclareLaunchArgument('sim_world', default_value=PathJoinSubstitution([pkg, 'worlds', 'corridor_rooms.sdf'])),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([leo_gz, 'launch', 'leo_gz.launch.py'])),
            launch_arguments={'robot_ns': LaunchConfiguration('robot1_ns'), 'sim_world': LaunchConfiguration('sim_world')}.items(),
        ),
        TimerAction(
            period=5.0,
            actions=[
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(PathJoinSubstitution([leo_gz, 'launch', 'spawn_robot.launch.py'])),
                    launch_arguments={'robot_ns': LaunchConfiguration('robot2_ns')}.items(),
                )
            ],
        ),
    ])
