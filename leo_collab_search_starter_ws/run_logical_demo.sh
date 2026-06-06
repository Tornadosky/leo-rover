#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source /opt/ros/jazzy/setup.bash
source install/setup.bash
mkdir -p artifacts
ros2 launch leo_collab_search logical_collab_search.launch.py artifact_dir:=artifacts target_marker_id:=10
