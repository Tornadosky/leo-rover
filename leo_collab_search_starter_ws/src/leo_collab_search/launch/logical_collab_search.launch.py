from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare('leo_collab_search')
    robots = LaunchConfiguration('robots')
    artifact_dir = LaunchConfiguration('artifact_dir')
    rooms_file = LaunchConfiguration('rooms_file')
    markers_file = LaunchConfiguration('markers_file')
    map_yaml = LaunchConfiguration('map_yaml')
    target_marker_id = LaunchConfiguration('target_marker_id')

    return LaunchDescription([
        DeclareLaunchArgument('robots', default_value='leo1,leo2'),
        DeclareLaunchArgument('artifact_dir', default_value='artifacts'),
        DeclareLaunchArgument('rooms_file', default_value=PathJoinSubstitution([pkg, 'config', 'rooms_corridor.yaml'])),
        DeclareLaunchArgument('markers_file', default_value=PathJoinSubstitution([pkg, 'config', 'markers_corridor_tags.yaml'])),
        DeclareLaunchArgument('map_yaml', default_value=PathJoinSubstitution([pkg, 'maps', 'corridor_rooms.yaml'])),
        DeclareLaunchArgument('target_marker_id', default_value='10'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),

        Node(
            package='leo_collab_search', executable='logical_robot_sim', output='screen',
            parameters=[{
                'robots': robots,
                'start_poses_file': rooms_file,
                'artifact_dir': artifact_dir,
                'use_sim_time': False,
            }],
        ),
        Node(
            package='leo_collab_search', executable='map_laser_sim', output='screen',
            parameters=[{
                'robots': robots,
                'map_yaml': map_yaml,
                'use_sim_time': False,
            }],
        ),
        Node(
            package='leo_collab_search', executable='semantic_map_server', output='screen',
            parameters=[{
                'artifact_dir': artifact_dir,
                'target_marker_id': target_marker_id,
                'use_sim_time': False,
            }],
        ),
        Node(
            package='leo_collab_search', executable='room_search_manager', output='screen',
            parameters=[{
                'robots': robots,
                'rooms_file': rooms_file,
                'artifact_dir': artifact_dir,
                'target_marker_id': target_marker_id,
                'use_nav2': False,
                'use_sim_time': False,
            }],
        ),
        Node(
            package='leo_collab_search', executable='fake_tag_detector', output='screen', name='fake_tag_detector_leo1',
            parameters=[{'robot': 'leo1', 'markers_file': markers_file, 'use_sim_time': False}],
        ),
        Node(
            package='leo_collab_search', executable='fake_tag_detector', output='screen', name='fake_tag_detector_leo2',
            parameters=[{'robot': 'leo2', 'markers_file': markers_file, 'use_sim_time': False}],
        ),
    ])
