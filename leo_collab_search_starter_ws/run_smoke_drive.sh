#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run leo_collab_search smoke_drive --robot leo1 --artifact-dir artifacts --duration 2.0 --speed 0.25
