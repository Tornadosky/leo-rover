#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
set +u
source /opt/ros/jazzy/setup.bash
source install/setup.bash
set -u
mkdir -p artifacts
ros2 launch leo_collab_search logical_collab_search.launch.py artifact_dir:=artifacts target_marker_id:=10
