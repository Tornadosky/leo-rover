#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
set +u
source /opt/ros/jazzy/setup.bash
set -u
rosdep install --from-paths src --ignore-src -r -y || true
colcon build --symlink-install
set +u
source install/setup.bash
set -u
ros2 pkg prefix leo_collab_search
