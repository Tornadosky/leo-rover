#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run leo_collab_search topic_snapshot --artifact-dir artifacts --name topics_after_launch --required /semantic_observations,/semantic_map,/search_status,/leo1/odom,/leo2/odom,/leo1/scan,/leo2/scan
