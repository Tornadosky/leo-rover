"""Start one official Leo Rover Gazebo simulation in the package corridor world.

This launch intentionally delegates to leo_gz_bringup. It requires:
  sudo apt install ros-$ROS_DISTRO-leo-simulator
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    leo_gz = FindPackageShare('leo_gz_bringup')
    pkg = FindPackageShare('leo_collab_search')
    return LaunchDescription([
        DeclareLaunchArgument('robot_ns', default_value='leo1'),
        DeclareLaunchArgument('sim_world', default_value=PathJoinSubstitution([pkg, 'worlds', 'corridor_rooms.sdf'])),
        DeclareLaunchArgument('map_yaml', default_value=PathJoinSubstitution([pkg, 'maps', 'corridor_rooms.yaml'])),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([leo_gz, 'launch', 'leo_gz.launch.py'])),
            launch_arguments={
                'robot_ns': LaunchConfiguration('robot_ns'),
                'sim_world': LaunchConfiguration('sim_world'),
            }.items(),
        ),
        # The official Leo Gazebo model exposes camera/IMU/odom but no lidar.
        # Publish a deterministic map-based scan so Nav2 plumbing can be tested in sim.
        Node(
            package='leo_collab_search',
            executable='map_laser_sim',
            output='screen',
            parameters=[{
                'robots': LaunchConfiguration('robot_ns'),
                'map_yaml': LaunchConfiguration('map_yaml'),
                'use_sim_time': True,
            }],
        ),
        Node(
            package='leo_collab_search',
            executable='tf_topic_relay',
            output='screen',
            parameters=[{
                'robot': LaunchConfiguration('robot_ns'),
                'use_sim_time': True,
            }],
        ),
    ])
