"""Run only the collaborative semantic layer for real Leo Rovers.

Use this after real robots are already publishing odom/camera/scan and Nav2 is
running separately. Replace fake_tag_detector with apriltag_ros/object detector
adapters when real perception is ready.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare('leo_collab_search')
    return LaunchDescription([
        DeclareLaunchArgument('robots', default_value='leo1,leo2'),
        DeclareLaunchArgument('artifact_dir', default_value='artifacts'),
        DeclareLaunchArgument('rooms_file', default_value=PathJoinSubstitution([pkg, 'config', 'rooms_corridor.yaml'])),
        DeclareLaunchArgument('target_marker_id', default_value='10'),
        DeclareLaunchArgument('use_nav2', default_value='true'),
        Node(
            package='leo_collab_search', executable='semantic_map_server', output='screen',
            parameters=[{'artifact_dir': LaunchConfiguration('artifact_dir'), 'target_marker_id': LaunchConfiguration('target_marker_id')}],
        ),
        Node(
            package='leo_collab_search', executable='room_search_manager', output='screen',
            parameters=[{
                'robots': LaunchConfiguration('robots'),
                'rooms_file': LaunchConfiguration('rooms_file'),
                'artifact_dir': LaunchConfiguration('artifact_dir'),
                'target_marker_id': LaunchConfiguration('target_marker_id'),
                'use_nav2': LaunchConfiguration('use_nav2'),
            }],
        ),
    ])
