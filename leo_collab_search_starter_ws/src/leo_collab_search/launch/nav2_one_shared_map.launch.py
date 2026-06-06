from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare('leo_collab_search')
    nav2 = FindPackageShare('nav2_bringup')
    robot = LaunchConfiguration('robot')
    # Keep this simple for Codex: default robot=leo1. For robot=leo2 pass params_file manually.
    return LaunchDescription([
        DeclareLaunchArgument('robot', default_value='leo1'),
        DeclareLaunchArgument('map_yaml', default_value=PathJoinSubstitution([pkg, 'maps', 'corridor_rooms.yaml'])),
        DeclareLaunchArgument('params_file', default_value=PathJoinSubstitution([pkg, 'config', 'nav2_params_leo1.yaml'])),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([nav2, 'launch', 'bringup_launch.py'])),
            launch_arguments={
                'namespace': robot,
                'use_namespace': 'True',
                'slam': 'False',
                'map': LaunchConfiguration('map_yaml'),
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'params_file': LaunchConfiguration('params_file'),
                'autostart': 'True',
            }.items(),
        ),
    ])
