#!/usr/bin/env python3
"""Minimal adapter for the later Jetson/Object Detection milestone.

Input topic, per robot:
  /<robot>/raw_object_detections std_msgs/String JSON
Example input:
  {"class_name":"backpack", "confidence":0.88, "range_m":1.4, "bearing_rad":0.05, "room_id":"room_c"}

Output:
  /semantic_observations std_msgs/String JSON, same format as fake_tag_detector.

This keeps the collaboration/map code unchanged when the team replaces fake tags
with YOLO/DepthAI/Isaac ROS detections on Jetson Orin.
"""
from __future__ import annotations

import json
import math
from typing import Optional, Tuple

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import String

from .utils import quat_to_yaw


class ObjectDetectionAdapter(Node):
    def __init__(self) -> None:
        super().__init__("object_detection_adapter")
        self.declare_parameter("robot", "leo1")
        self.declare_parameter("raw_topic", "")
        self.declare_parameter("default_room_id", "unknown")
        self.declare_parameter("use_sim_time", True)

        self.robot = str(self.get_parameter("robot").value).strip(" /")
        raw_topic = str(self.get_parameter("raw_topic").value).strip()
        self.raw_topic = raw_topic or f"/{self.robot}/raw_object_detections"
        self.default_room_id = str(self.get_parameter("default_room_id").value)
        self.pose: Optional[Tuple[float, float, float]] = None

        self.odom_sub = self.create_subscription(Odometry, f"/{self.robot}/odom", self._odom_cb, 10)
        self.raw_sub = self.create_subscription(String, self.raw_topic, self._raw_cb, 10)
        self.obs_pub = self.create_publisher(String, "/semantic_observations", 10)
        self.get_logger().info(f"Object adapter for {self.robot}; input={self.raw_topic}")

    def _odom_cb(self, msg: Odometry) -> None:
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        self.pose = (float(p.x), float(p.y), quat_to_yaw(q.x, q.y, q.z, q.w))

    def _raw_cb(self, msg: String) -> None:
        if self.pose is None:
            return
        try:
            det = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().warning("Ignoring invalid object detection JSON")
            return
        rx, ry, yaw = self.pose
        rng = float(det.get("range_m", 1.0))
        bearing = float(det.get("bearing_rad", 0.0))
        x = rx + rng * math.cos(yaw + bearing)
        y = ry + rng * math.sin(yaw + bearing)
        class_name = str(det.get("class_name", "object"))
        stamp = self.get_clock().now().nanoseconds / 1e9
        obs = {
            "stamp": stamp,
            "robot_id": self.robot,
            "source": "object_detection_adapter",
            "marker_id": -1,
            "class_name": class_name,
            "label": str(det.get("label", class_name)),
            "confidence": float(det.get("confidence", 0.0)),
            "distance": rng,
            "bearing": bearing,
            "room_id": str(det.get("room_id", self.default_room_id)),
            "pose_map": {"x": round(x, 3), "y": round(y, 3), "yaw": 0.0},
            "bbox": det.get("bbox", []),
        }
        self.obs_pub.publish(String(data=json.dumps(obs)))


def main(args=None):
    rclpy.init(args=args)
    node = ObjectDetectionAdapter()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
