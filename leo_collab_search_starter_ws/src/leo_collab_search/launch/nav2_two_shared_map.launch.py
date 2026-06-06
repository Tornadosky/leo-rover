"""Launch two Nav2 bringups on one shared saved map.

Use this after /leo1/scan,/leo1/odom,/leo1/tf and /leo2/... exist from either
logical simulation, Leo Gazebo with lidar, or real robots.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def nav2_include(namespace, params_file, map_yaml):
    nav2 = FindPackageShare('nav2_bringup')
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([nav2, 'launch', 'bringup_launch.py'])),
        launch_arguments={
            'namespace': namespace,
            'use_namespace': 'True',
            'slam': 'False',
            'map': map_yaml,
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'params_file': params_file,
            'autostart': 'True',
        }.items(),
    )


def generate_launch_description():
    pkg = FindPackageShare('leo_collab_search')
    map_yaml = LaunchConfiguration('map_yaml')
    return LaunchDescription([
        DeclareLaunchArgument('map_yaml', default_value=PathJoinSubstitution([pkg, 'maps', 'corridor_rooms.yaml'])),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        nav2_include('leo1', PathJoinSubstitution([pkg, 'config', 'nav2_params_leo1.yaml']), map_yaml),
        nav2_include('leo2', PathJoinSubstitution([pkg, 'config', 'nav2_params_leo2.yaml']), map_yaml),
    ])
