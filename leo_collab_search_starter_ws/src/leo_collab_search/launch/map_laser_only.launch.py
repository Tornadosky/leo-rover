from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare('leo_collab_search')
    return LaunchDescription([
        DeclareLaunchArgument('robots', default_value='leo1'),
        DeclareLaunchArgument('map_yaml', default_value=PathJoinSubstitution([pkg, 'maps', 'corridor_rooms.yaml'])),
        Node(
            package='leo_collab_search', executable='map_laser_sim', output='screen',
            parameters=[{'robots': LaunchConfiguration('robots'), 'map_yaml': LaunchConfiguration('map_yaml'), 'use_sim_time': False}],
        ),
    ])
