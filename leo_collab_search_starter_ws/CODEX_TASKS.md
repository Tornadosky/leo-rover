# Codex Task Plan with Deliverables

Codex should implement/verify these milestones one at a time. Do not proceed until the deliverable file exists and the pass condition is true.

## Milestone 0 — Build environment

Command:

```bash
./setup_ubuntu24_ros_jazzy.sh
./build_ws.sh
```

Deliverable:

```bash
ros2 pkg prefix leo_collab_search
```

Pass condition:

- Command returns a valid install path.
- `colcon build` exits 0.

## Milestone 1 — Validate maps

Command:

```bash
./make_map_reports.sh
```

Deliverables:

```text
artifacts/map_reports/corridor_rooms_map_report.json
artifacts/map_reports/office_loop_map_report.json
artifacts/map_reports/open_area_map_report.json
artifacts/map_reports/warehouse_like_map_report.json
```

Pass condition:

- Each JSON has `pass: true`.
- Each map has nonzero occupied and free pixels.

## Milestone 2 — Spawn logical two-robot simulation

Command:

```bash
ros2 launch leo_collab_search logical_collab_search.launch.py artifact_dir:=artifacts target_marker_id:=10
```

Deliverables:

```text
artifacts/logical_robot_sim_initial.json
artifacts/logical_robot_sim_latest.json
```

Pass condition:

- Latest JSON has `pass: true`.
- It contains both `leo1` and `leo2` poses.

## Milestone 3 — Verify topics

Run while milestone 2 is active:

```bash
./run_topic_snapshot.sh
```

Deliverable:

```text
artifacts/topics_after_launch.json
```

Pass condition:

- JSON has `pass: true`.
- Required topics exist: `/semantic_observations`, `/semantic_map`, `/search_status`, `/leo1/odom`, `/leo2/odom`, `/leo1/scan`, `/leo2/scan`.

## Milestone 4 — Verify robot motion

Run while milestone 2 is active:

```bash
./run_smoke_drive.sh
```

Deliverable:

```text
artifacts/smoke_drive_leo1.json
```

Pass condition:

- JSON has `pass: true`.
- `distance_moved > 0.05`.

## Milestone 5 — Collaborative tag search

Command:

```bash
ros2 launch leo_collab_search logical_collab_search.launch.py artifact_dir:=artifacts target_marker_id:=10
```

Wait until the search finishes or target is found.

Deliverables:

```text
artifacts/semantic_map_latest.json
artifacts/search_status_latest.json
artifacts/collaborative_search_result.json
```

Pass condition:

- `collaborative_search_result.json` has `pass: true`.
- `target_found: true`.
- Target observation has `robot_id`, `marker_id`, `room_id`, and `pose_map`.

## Milestone 6 — RViz visual check

Command:

```bash
rviz2
```

Add displays:

```text
TF
LaserScan: /leo1/scan
LaserScan: /leo2/scan
MarkerArray: /semantic_map_markers
MarkerArray: /leo1/fake_tag_markers
MarkerArray: /leo2/fake_tag_markers
```

Deliverable:

```text
screenshots/rviz_logical_demo.png
```

Pass condition:

- Both robots' TF frames appear.
- Scans appear.
- Semantic target marker appears.

## Milestone 7 — Official Leo Gazebo smoke test

Command:

```bash
ros2 launch leo_collab_search official_leo_gazebo_one.launch.py robot_ns:=leo1
```

Deliverables:

```bash
ros2 topic list
ros2 topic echo /leo1/odom --once
ros2 topic echo /leo1/scan --once
```

Pass condition:

- Gazebo opens.
- `/leo1/odom` exists.
- `/leo1/scan` exists or Codex documents the actual scan topic and updates launch/config remaps.

## Milestone 8 — Single real/sim Leo Nav2

Use the official Leo navigation tutorial first. Then verify:

Deliverable:

```text
artifacts/nav2_single_robot_goal.json
```

Pass condition:

- Robot reaches at least one room waypoint using Nav2 or the artifact explains exactly which missing topic/frame blocks it.

## Milestone 9 — Two real/sim Leo collaborative search

Start two rovers, then run:

```bash
ros2 launch leo_collab_search semantic_nodes_for_real_robots.launch.py robots:=leo1,leo2 use_nav2:=true target_marker_id:=10
```

Deliverable:

```text
artifacts/collaborative_search_result.json
```

Pass condition:

- Two robots receive different assigned goals.
- Target is detected or a clear failure artifact states which detector/topic is missing.

## Milestone 10 — Jetson object detection replacement

Keep the same semantic map server. Replace fake tags with object detection by publishing JSON to:

```text
/<robot>/raw_object_detections
```

Example:

```bash
ros2 topic pub /leo1/raw_object_detections std_msgs/msg/String \
'{data: "{\"class_name\":\"backpack\",\"confidence\":0.9,\"range_m\":1.3,\"bearing_rad\":0.0,\"room_id\":\"room_c\"}"}'
```

Launch adapter:

```bash
ros2 run leo_collab_search object_detection_adapter --ros-args -p robot:=leo1
```

Deliverable:

```text
artifacts/semantic_map_latest.json
```

Pass condition:

- Object appears in semantic map with class name, confidence, robot ID, room, and map pose.
