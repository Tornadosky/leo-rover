#!/usr/bin/env bash
set -euo pipefail
# Run while one_robot SLAM is active. Saves map into ./artifacts/slam_map.*
cd "$(dirname "$0")"
source /opt/ros/jazzy/setup.bash
source install/setup.bash
mkdir -p artifacts
ros2 run nav2_map_server map_saver_cli -f artifacts/slam_map
if [ -f artifacts/slam_map.pgm ]; then
  ros2 run leo_collab_search map_report --map artifacts/slam_map.yaml --artifact-dir artifacts
fi
