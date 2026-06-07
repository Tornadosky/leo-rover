#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
set +u
source /opt/ros/jazzy/setup.bash
source install/setup.bash
set -u
mkdir -p artifacts/map_reports
for m in src/leo_collab_search/maps/*.yaml; do
  ros2 run leo_collab_search map_report --map "$m" --artifact-dir artifacts/map_reports
done
