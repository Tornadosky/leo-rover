#!/usr/bin/env bash
set -euo pipefail

# Run inside Ubuntu 24.04 Desktop / WSL2 Ubuntu 24.04.
# This installs ROS 2 Jazzy, Nav2, SLAM Toolbox, Leo simulator, and tools needed by this workspace.

if ! grep -q "24.04" /etc/os-release; then
  echo "ERROR: This script expects Ubuntu 24.04. Use Ubuntu 24.04 LTS Desktop or WSL Ubuntu-24.04." >&2
  exit 1
fi

sudo apt update
sudo apt install -y software-properties-common curl gnupg lsb-release locales git python3-pip
sudo add-apt-repository -y universe
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Official ROS apt source package flow from ROS 2 Jazzy docs.
export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F'"' '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb

sudo apt update
sudo apt upgrade -y
sudo apt install -y \
  ros-jazzy-desktop \
  ros-dev-tools \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-yaml \
  python3-pil \
  ros-jazzy-navigation2 \
  ros-jazzy-nav2-bringup \
  ros-jazzy-slam-toolbox \
  ros-jazzy-teleop-twist-keyboard \
  ros-jazzy-tf-transformations

# Leo simulator is the official path for Leo Rover simulation. If the package is temporarily unavailable,
# the logical simulator in this workspace still works and Codex can proceed with early milestones.
sudo apt install -y ros-jazzy-leo-simulator ros-jazzy-leo-teleop || true

if ! grep -q "source /opt/ros/jazzy/setup.bash" ~/.bashrc; then
  echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
fi
if ! grep -q "export ROS_DOMAIN_ID=11" ~/.bashrc; then
  echo "export ROS_DOMAIN_ID=11" >> ~/.bashrc
fi

set +u
source /opt/ros/jazzy/setup.bash
set -u
sudo rosdep init 2>/dev/null || true
rosdep update

echo "Done. Open a new terminal or run: source /opt/ros/jazzy/setup.bash"
