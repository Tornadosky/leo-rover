# Leo Collaborative Search Starter Workspace

This is a ROS 2 Jazzy starter workspace for a distributed-robotics-lab project:

> Two Leo Rovers collaboratively search an indoor map for tags first, then objects later.

The package is intentionally built in the least fragile order:

1. Logical/tiny simulator first, no Gazebo required.
2. Fake LaserScan from prebuilt maps.
3. Fake AprilTag/ArUco-style detections from known marker locations.
4. Shared semantic map and collaborative room search.
5. Optional Nav2 and official Leo Gazebo integration.
6. Real Leo Rover indoor deployment.
7. Jetson Orin object detection adapter.

## Quick start

```bash
cd ~/leo_collab_search_starter_ws
./setup_ubuntu24_ros_jazzy.sh
./build_ws.sh
./make_map_reports.sh
./run_logical_demo.sh
```

In a second terminal while the demo is running:

```bash
cd ~/leo_collab_search_starter_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
./run_topic_snapshot.sh
python3 check_artifacts.py
rviz2
```

Expected success artifact:

```text
artifacts/collaborative_search_result.json
```

It should contain:

```json
"pass": true,
"target_found": true
```

## What the MVP does

- Publishes two logical robots: `/leo1` and `/leo2`.
- Publishes `/leo1/odom`, `/leo2/odom`, `/leo1/scan`, `/leo2/scan`.
- Assigns rooms to the robots.
- Publishes fake marker detections to `/semantic_observations`.
- Builds a shared semantic map on `/semantic_map` and `/semantic_map_markers`.
- Stops the search once target marker `10` is found.
- Writes machine-checkable JSON artifacts.

## Most important launch files

```bash
# Full no-Gazebo, two-robot collaborative tag search
ros2 launch leo_collab_search logical_collab_search.launch.py

# Laser-only simulated scans from map
ros2 launch leo_collab_search map_laser_only.launch.py

# Start official Leo Gazebo single robot if ros-jazzy-leo-simulator is installed
ros2 launch leo_collab_search official_leo_gazebo_one.launch.py

# Semantic/task layer for real robots or Gazebo robots when odom/scan already exist
ros2 launch leo_collab_search semantic_nodes_for_real_robots.launch.py use_nav2:=true
```

## Maps included

```text
corridor_rooms  - default indoor corridor + rooms map
office_loop     - loop-style office map
open_area       - simple open-area map
warehouse_like  - rows/aisles map
```

Each map includes `.yaml`, `.pgm`, and `.png`. The PNG is for humans; the YAML/PGM are for ROS tools.

## Recommended development rule

Do not start with full collaborative SLAM. First get this working:

```text
shared saved map + two localized robots + shared detections + room/task assignment
```

Then replace one piece at a time:

```text
logical simulator -> Leo Gazebo -> real Leo
fake tags -> apriltag_ros -> object detection on Jetson
simple goal topics -> Nav2 actions
shared saved map -> collaborative SLAM, if time permits
```
