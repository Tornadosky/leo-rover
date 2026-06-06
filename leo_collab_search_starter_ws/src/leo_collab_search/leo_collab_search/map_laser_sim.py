#!/usr/bin/env python3
"""Publish fake LaserScan messages by ray-casting in a static occupancy map.

This node is a practical bridge between the team's algorithm work and full Gazebo.
It can feed /leo1/scan and /leo2/scan in logical simulation, letting Codex test
Nav2/SLAM-related plumbing without depending on Gazebo lidar plugins.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from tf2_ros import StaticTransformBroadcaster
from geometry_msgs.msg import TransformStamped

from .utils import load_yaml, parse_robot_names, quat_to_yaw


def read_pgm(path: str) -> Tuple[int, int, int, List[int]]:
    """Read a P2/P5 PGM image and return width, height, maxval, flat pixels."""
    data = Path(path).read_bytes()
    idx = 0

    def token() -> bytes:
        nonlocal idx
        while idx < len(data) and data[idx] in b" \t\r\n":
            idx += 1
        if idx < len(data) and data[idx] == ord("#"):
            while idx < len(data) and data[idx] not in b"\r\n":
                idx += 1
            return token()
        start = idx
        while idx < len(data) and data[idx] not in b" \t\r\n":
            idx += 1
        return data[start:idx]

    magic = token()
    width = int(token())
    height = int(token())
    maxval = int(token())
    while idx < len(data) and data[idx] in b" \t\r\n":
        idx += 1
    if magic == b"P5":
        pixels = list(data[idx : idx + width * height])
    elif magic == b"P2":
        pixels = [int(token()) for _ in range(width * height)]
    else:
        raise ValueError(f"Unsupported PGM magic {magic!r}")
    return width, height, maxval, pixels


class MapLaserSim(Node):
    def __init__(self) -> None:
        super().__init__("map_laser_sim")
        self.declare_parameter("robots", "leo1,leo2")
        self.declare_parameter("map_yaml", "")
        self.declare_parameter("angle_min", -math.pi)
        self.declare_parameter("angle_max", math.pi)
        self.declare_parameter("num_rays", 360)
        self.declare_parameter("range_min", 0.05)
        self.declare_parameter("range_max", 8.0)
        self.declare_parameter("ray_step", 0.04)
        self.declare_parameter("publish_rate", 8.0)
        self.declare_parameter("occupied_pixel_threshold", 100)  # dark pixels are occupied
        self.declare_parameter("use_sim_time", True)

        self.robots = parse_robot_names(self.get_parameter("robots").value)
        map_yaml = str(self.get_parameter("map_yaml").value)
        if not map_yaml:
            raise RuntimeError("map_laser_sim requires map_yaml parameter")
        self.map_info = load_yaml(map_yaml)
        image_path = Path(map_yaml).parent / str(self.map_info["image"])
        self.width, self.height, self.maxval, self.pixels = read_pgm(str(image_path))
        self.resolution = float(self.map_info.get("resolution", 0.05))
        origin = self.map_info.get("origin", [0.0, 0.0, 0.0])
        self.origin_x = float(origin[0])
        self.origin_y = float(origin[1])

        self.angle_min = float(self.get_parameter("angle_min").value)
        self.angle_max = float(self.get_parameter("angle_max").value)
        self.num_rays = int(self.get_parameter("num_rays").value)
        self.range_min = float(self.get_parameter("range_min").value)
        self.range_max = float(self.get_parameter("range_max").value)
        self.ray_step = float(self.get_parameter("ray_step").value)
        self.occupied_pixel_threshold = int(self.get_parameter("occupied_pixel_threshold").value)

        self.poses: Dict[str, Tuple[float, float, float]] = {}
        self.scan_pubs = {name: self.create_publisher(LaserScan, f"/{name}/scan", 10) for name in self.robots}
        self.subs = [self.create_subscription(Odometry, f"/{name}/odom", lambda msg, n=name: self._odom_cb(n, msg), 10) for name in self.robots]
        self.static_tf = StaticTransformBroadcaster(self)
        self._publish_static_tf()
        self.timer = self.create_timer(1.0 / float(self.get_parameter("publish_rate").value), self._publish_scans)
        self.get_logger().info(f"Map laser sim loaded {image_path} ({self.width}x{self.height}), robots={self.robots}")

    def _odom_cb(self, robot: str, msg: Odometry) -> None:
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        self.poses[robot] = (float(p.x), float(p.y), quat_to_yaw(q.x, q.y, q.z, q.w))

    def _world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        mx = int((x - self.origin_x) / self.resolution)
        my_bottom = int((y - self.origin_y) / self.resolution)
        # PGM origin is top-left, occupancy-map origin is bottom-left.
        my = self.height - 1 - my_bottom
        return mx, my

    def _is_occupied_world(self, x: float, y: float) -> bool:
        mx, my = self._world_to_grid(x, y)
        if mx < 0 or mx >= self.width or my < 0 or my >= self.height:
            return True
        pix = self.pixels[my * self.width + mx]
        return pix < self.occupied_pixel_threshold

    def _raycast(self, x: float, y: float, yaw: float, rel_angle: float) -> float:
        theta = yaw + rel_angle
        r = self.range_min
        while r <= self.range_max:
            px = x + r * math.cos(theta)
            py = y + r * math.sin(theta)
            if self._is_occupied_world(px, py):
                return r
            r += self.ray_step
        return float("inf")

    def _publish_scans(self) -> None:
        stamp = self.get_clock().now().to_msg()
        angle_increment = (self.angle_max - self.angle_min) / max(1, self.num_rays - 1)
        for robot, pose in self.poses.items():
            x, y, yaw = pose
            msg = LaserScan()
            msg.header.stamp = stamp
            msg.header.frame_id = f"{robot}/laser_frame"
            msg.angle_min = self.angle_min
            msg.angle_max = self.angle_max
            msg.angle_increment = angle_increment
            msg.time_increment = 0.0
            msg.scan_time = 0.125
            msg.range_min = self.range_min
            msg.range_max = self.range_max
            msg.ranges = [self._raycast(x, y, yaw, self.angle_min + i * angle_increment) for i in range(self.num_rays)]
            self.scan_pubs[robot].publish(msg)

    def _publish_static_tf(self) -> None:
        stamp = self.get_clock().now().to_msg()
        transforms = []
        for robot in self.robots:
            t = TransformStamped()
            t.header.stamp = stamp
            t.header.frame_id = f"{robot}/base_link"
            t.child_frame_id = f"{robot}/laser_frame"
            t.transform.translation.x = 0.10
            t.transform.translation.z = 0.18
            t.transform.rotation.w = 1.0
            transforms.append(t)
        self.static_tf.sendTransform(transforms)


def main(args=None):
    rclpy.init(args=args)
    node = MapLaserSim()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
