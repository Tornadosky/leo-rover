# Windows / VirtualBox Setup

Recommended VM for this project:

- VirtualBox: 7.x
- Guest OS: Ubuntu 24.04 LTS Desktop, 64-bit AMD64 ISO
- ROS: ROS 2 Jazzy Jalisco
- CPU: 6 virtual CPUs if available, minimum 4
- RAM: 16 GB recommended, minimum 8 GB
- Disk: 80 GB dynamically allocated, minimum 50 GB
- Graphics: enable 3D acceleration, 128 MB video memory
- Network for simulation only: NAT is fine
- Network for real Leo Rovers: Bridged Adapter to the Wi-Fi/Ethernet interface connected to the rovers

Inside Ubuntu:

```bash
sudo apt update && sudo apt install -y git unzip
cd ~
unzip leo_collab_search_starter_ws.zip
cd leo_collab_search_starter_ws
./setup_ubuntu24_ros_jazzy.sh
./build_ws.sh
./run_logical_demo.sh
```

If Gazebo GUI is slow in VirtualBox, keep using the logical simulator for early coding and run Gazebo only for the official Leo-sim smoke test.

WSL2 alternative:

```powershell
wsl --install -d Ubuntu-24.04
wsl --update
```

WSL2 works well for ROS/RViz on Windows 11, but VirtualBox Ubuntu Desktop is simpler for students who want a full Linux desktop and Gazebo GUI in one place.
