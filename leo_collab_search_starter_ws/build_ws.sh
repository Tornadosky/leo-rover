#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y || true
colcon build --symlink-install
source install/setup.bash
ros2 pkg prefix leo_collab_search
