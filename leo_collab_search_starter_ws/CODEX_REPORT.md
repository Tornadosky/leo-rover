# Codex Progress Report

Date: 2026-06-07

This report summarizes the work completed against `CODEX_TASKS.md`, the evidence found in the current workspace, and the blockers that remain before the full real/sim Leo rover collaborative search flow is complete.

## Executive summary

Milestones 0 through 7 are achieved in the current workspace:

- The ROS 2 Jazzy workspace builds and `ros2 pkg prefix leo_collab_search` resolves to the local install path.
- All four map validation reports pass with nonzero occupied and free pixels.
- The logical two-robot simulation publishes both robot poses, required topics, synthetic scans, semantic observations, semantic map, and search status.
- The logical collaborative tag search finds target marker `10` in `room_c` from `leo2`.
- RViz has a captured visual check showing TF, scans, semantic map markers, and fake tag marker displays enabled with global status OK.
- The official Leo Gazebo smoke test opens Gazebo, spawns `leo1`, exposes `/leo1/odom`, and now exposes `/leo1/scan` through a deterministic map-based scan publisher.

The main remaining blocker is Milestone 8: Nav2 on the official Leo Gazebo setup still cannot use the `odom -> leo1/base_footprint` transform during local costmap activation. That blocks the full Nav2-backed single-robot goal test and, by extension, the two real/sim Leo collaborative Nav2 search in Milestone 9.

## Implementation completed

- Hardened the shell scripts that source ROS setup files while `set -u` is active by temporarily disabling nounset around `source /opt/ros/jazzy/setup.bash` and `source install/setup.bash`.
- Removed local redeclaration of the ROS-managed `use_sim_time` parameter from the Python nodes so launch files can set it cleanly.
- Added `tf_topic_relay`, which relays `/<robot>/tf` from the official Leo Gazebo bridge onto standard `/tf`.
- Added the `tf2_msgs` dependency and `tf_topic_relay` console entry point.
- Updated the official one-robot and two-robot Leo Gazebo launch files to start:
  - `map_laser_sim`, because the installed official Leo Gazebo model does not provide a native LaserScan topic.
  - `tf_topic_relay`, because the official bridge publishes dynamic TF on namespaced TF topics.
- Added `config/nav2_params_leo1_gazebo.yaml` for the single official Gazebo Leo Nav2 experiment.
- Added `screenshots/rviz_logical_demo.png` as the RViz visual deliverable.

## Verification run in this session

Command:

```bash
./build_ws.sh
```

Result:

- `colcon build` exited 0.
- `ros2 pkg prefix leo_collab_search` returned:

```text
/home/tornadosky/Desktop/leo-rover/leo_collab_search_starter_ws/install/leo_collab_search
```

Note: `rosdep` still reports that it cannot resolve `ament_python` on this machine, but the script continues after resolvable dependencies and the package build succeeds.

Command:

```bash
./make_map_reports.sh
```

Result:

- `corridor_rooms`: pass, `4303` occupied pixels, `34097` free pixels.
- `office_loop`: pass, `4586` occupied pixels, `45814` free pixels.
- `open_area`: pass, `2751` occupied pixels, `37249` free pixels.
- `warehouse_like`: pass, `7671` occupied pixels, `56329` free pixels.

Command:

```bash
./check_artifacts.py
```

Result:

- `artifacts/collaborative_search_result.json`: PASS.
- `artifacts/semantic_map_latest.json`: PASS.
- `artifacts/logical_robot_sim_latest.json`: PASS.

RViz screenshot:

- `screenshots/rviz_logical_demo.png` was visually checked.
- The screenshot shows RViz global status OK, TF enabled, both `leo1` and `leo2` scan displays enabled, semantic map markers enabled, and both fake tag marker displays enabled.

## Milestone status

### Milestone 0 - Build environment

Status: Achieved.

Evidence:

- `./build_ws.sh` completes successfully.
- `ros2 pkg prefix leo_collab_search` returns the local install path.

Remaining issue:

- Non-fatal `rosdep` warning for unresolved `ament_python` remains on this host.

### Milestone 1 - Validate maps

Status: Achieved.

Evidence:

- All map report JSON outputs have `pass: true`.
- Each map has nonzero occupied and free pixels.

Generated reports:

- `artifacts/map_reports/corridor_rooms_map_report.json`
- `artifacts/map_reports/office_loop_map_report.json`
- `artifacts/map_reports/open_area_map_report.json`
- `artifacts/map_reports/warehouse_like_map_report.json`

Note: `artifacts/` is intentionally ignored by Git, so this report records the important values instead of tracking generated artifacts.

### Milestone 2 - Spawn logical two-robot simulation

Status: Achieved.

Evidence from `artifacts/logical_robot_sim_latest.json`:

- `pass: true`
- `leo1` pose was present.
- `leo2` pose was present.

Latest sampled poses:

- `leo1`: `x=-0.0794`, `y=-2.1400`, `yaw=-0.2019`
- `leo2`: `x=4.1501`, `y=0.8985`, `yaw=1.3217`

### Milestone 3 - Verify topics

Status: Achieved.

Evidence from `artifacts/topics_after_launch.json`:

- `pass: true`
- Missing topics list was empty.
- Required topics were present:
  - `/semantic_observations`
  - `/semantic_map`
  - `/search_status`
  - `/leo1/odom`
  - `/leo2/odom`
  - `/leo1/scan`
  - `/leo2/scan`

### Milestone 4 - Verify robot motion

Status: Achieved.

Evidence from `artifacts/smoke_drive_leo1.json`:

- `pass: true`
- `distance_moved: 0.5461535549999998`
- The required threshold was `distance_moved > 0.05`.

### Milestone 5 - Collaborative tag search

Status: Achieved in the logical simulator.

Evidence from `artifacts/collaborative_search_result.json`:

- `pass: true`
- `target_found: true`
- Target marker `10` was detected by `leo2`.
- Target room was `room_c`.
- Target map pose was `x=4.4`, `y=2.6`, `yaw=0.0`.

Evidence from `artifacts/semantic_map_latest.json`:

- `pass: true`
- `target_found: true`
- `object_count: 2`
- Semantic objects included `tag:3` and `tag:10`.

### Milestone 6 - RViz visual check

Status: Achieved for the logical demo.

Evidence:

- `screenshots/rviz_logical_demo.png`
- Visual inspection confirms the requested displays are enabled and RViz global status is OK.

### Milestone 7 - Official Leo Gazebo smoke test

Status: Achieved with simulator plumbing.

Evidence from `artifacts/gazebo_smoke_report.json`:

- `pass: true`
- `gazebo_opened: true`
- `robot_spawned: true`
- `odom_topic: /leo1/odom`
- `scan_topic: /leo1/scan`

Important note:

- The installed official Leo Gazebo model did not expose a native lidar topic.
- The launch files now start `map_laser_sim` to publish `/leo1/scan` or `/leo2/scan` from the known map so Nav2 plumbing can be tested.
- The launch files now start `tf_topic_relay` to republish `/<robot>/tf` onto `/tf`.

### Milestone 8 - Single real/sim Leo Nav2

Status: Blocked.

Evidence from `artifacts/nav2_single_robot_goal.json`:

- `pass: false`
- `blocked: true`
- `goal_sent: false`
- Target waypoint was `corridor` at `x=-4.5`, `y=-2.2`, `yaw=0.0`.

Current blocker:

```text
Timed out waiting for transform from leo1/base_footprint to odom to become available;
Invalid frame ID "odom" passed to canTransform argument target_frame - frame does not exist
```

What is already available:

- `/leo1/odom`
- `/leo1/scan`
- `/tf`
- `/leo1/tf`

What was tried:

- Added `tf_topic_relay` to relay `/leo1/tf` onto `/tf`.
- Added Gazebo-specific Nav2 params using:
  - `base_frame_id: leo1/base_footprint`
  - `odom_frame_id: odom`
  - `scan_topic: /leo1/scan`

Observed complication:

- A TF sample from the Gazebo smoke run contains `frame_id: odom` and `child_frame_id: leo1/base_footprint`, but Nav2 still did not receive a usable transform during local costmap activation in the Nav2 run.
- The Nav2 run was performed under Xvfb/software rendering with very low Gazebo real-time factor, and the notes captured ROS CLI daemon/context instability.

### Milestone 9 - Two real/sim Leo collaborative search

Status: Not completed; blocked by Milestone 8.

The logical collaborative search works and assigns work to both robots, but the two real/sim Nav2-backed workflow has not been validated because single-robot Nav2 cannot yet activate cleanly against the official Leo Gazebo TF tree.

Expected next validation once Milestone 8 is fixed:

- Start two official Leo Gazebo rovers.
- Launch `semantic_nodes_for_real_robots.launch.py` with `robots:=leo1,leo2 use_nav2:=true target_marker_id:=10`.
- Confirm the two robots receive different goals.
- Confirm target detection or write a clear detector/topic failure artifact.

### Milestone 10 - Jetson object detection replacement

Status: Partially implemented; not fully hardware-validated.

What exists:

- `object_detection_adapter` subscribes to raw JSON detections on `/<robot>/raw_object_detections` by default.
- It publishes semantic observations compatible with the existing semantic map server.
- The semantic map server can continue to merge observations without depending on fake tags.

Remaining blocker:

- No live Jetson detector/camera feed was available in this workspace session.
- The fake tag path is still the validated end-to-end detector path.
- A hardware or recorded-detection test still needs to publish representative detections and confirm they appear in `artifacts/semantic_map_latest.json`.

## Current blockers

1. Nav2 transform availability in official Leo Gazebo.

   Nav2 needs a stable, timely transform chain involving `odom`, `leo1/base_footprint`, and the scan frame. The relay makes `/tf` available, but Nav2 still timed out during local costmap activation.

2. Official Leo Gazebo lacks native lidar in this installed model.

   `map_laser_sim` is a useful deterministic simulator shim, but a real rover or a more realistic Gazebo run still needs an actual lidar topic or sensor plugin.

3. Headless Gazebo/RViz performance and ROS graph instability.

   The captured Nav2 run notes very low real-time factor under Xvfb/software rendering and ROS CLI daemon/context instability. That may be contributing to TF timing or lifecycle startup failures.

4. Real two-robot Nav2 search is downstream of single-robot Nav2.

   Until one official Leo can activate Nav2 and reach a room waypoint, the two-robot real/sim search cannot be considered complete.

5. Jetson object detection is adapter-ready but not detector-validated.

   The JSON adapter path exists, but the actual Jetson model process, camera source, and live publication contract still need to be tested.

## Recommended next steps

1. Debug Milestone 8 with a live TF-focused run:

   ```bash
   ros2 run tf2_ros tf2_echo odom leo1/base_footprint
   ros2 topic echo /tf --once
   ros2 topic echo /leo1/tf --once
   ros2 topic echo /tf_static --once
   ros2 topic echo /clock --once
   ```

2. Confirm the full scan transform chain:

   - `odom -> leo1/base_footprint`
   - `leo1/base_footprint -> leo1/laser_frame`
   - `/leo1/scan.header.frame_id == leo1/laser_frame`

3. If `/tf` is present but Nav2 still cannot see it, check QoS and startup ordering for the TF relay versus Nav2 lifecycle activation.

4. Re-run single-robot Nav2 after the TF chain is stable and update `artifacts/nav2_single_robot_goal.json`.

5. Then proceed to two-robot official Gazebo Nav2 search and finally replace fake tags with live or recorded Jetson detections through `object_detection_adapter`.
