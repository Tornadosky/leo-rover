#!/usr/bin/env python3
"""Simulation-only semantic detector for AprilTag/ArUco-like markers.

It reads known marker positions and publishes detections when the robot pose is
close enough. This is the fastest way to test collaborative search before camera
plugins, lighting, calibration, apriltag_ros, or YOLO are ready.
"""
from __future__ import annotations

import json
import math
from typing import Dict, List, Tuple

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import String
from visualization_msgs.msg import Marker, MarkerArray

from .utils import angle_wrap, dist2d, load_yaml, quat_to_yaw


class FakeTagDetector(Node):
    def __init__(self) -> None:
        super().__init__("fake_tag_detector")
        self.declare_parameter("robot", "leo1")
        self.declare_parameter("markers_file", "")
        self.declare_parameter("detection_range", 2.2)
        self.declare_parameter("fov_deg", 120.0)
        self.declare_parameter("require_fov", True)
        self.declare_parameter("publish_rate", 2.0)
        self.declare_parameter("use_sim_time", True)

        self.robot = str(self.get_parameter("robot").value).strip(" /")
        markers_file = str(self.get_parameter("markers_file").value)
        if not markers_file:
            raise RuntimeError("fake_tag_detector requires markers_file parameter")
        self.markers = self._load_markers(markers_file)
        self.detection_range = float(self.get_parameter("detection_range").value)
        self.fov_rad = math.radians(float(self.get_parameter("fov_deg").value))
        self.require_fov = bool(self.get_parameter("require_fov").value)

        self.pose: Tuple[float, float, float] | None = None
        self.obs_pub = self.create_publisher(String, "/semantic_observations", 10)
        self.marker_pub = self.create_publisher(MarkerArray, f"/{self.robot}/fake_tag_markers", 10)
        self.sub = self.create_subscription(Odometry, f"/{self.robot}/odom", self._odom_cb, 10)
        self.timer = self.create_timer(1.0 / float(self.get_parameter("publish_rate").value), self._tick)
        self.get_logger().info(f"Fake tag detector for {self.robot}: {len(self.markers)} markers")

    def _load_markers(self, path: str) -> List[Dict]:
        data = load_yaml(path)
        markers = []
        for m in data.get("markers", []):
            markers.append({
                "id": int(m.get("id", -1)),
                "class_name": str(m.get("class_name", "tag")),
                "x": float(m.get("x", 0.0)),
                "y": float(m.get("y", 0.0)),
                "yaw": float(m.get("yaw", 0.0)),
                "room_id": str(m.get("room_id", "unknown")),
                "label": str(m.get("label", f"tag_{m.get('id', -1)}")),
            })
        return markers

    def _odom_cb(self, msg: Odometry) -> None:
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        self.pose = (float(p.x), float(p.y), quat_to_yaw(q.x, q.y, q.z, q.w))

    def _tick(self) -> None:
        if self.pose is None:
            return
        x, y, yaw = self.pose
        visible = []
        stamp = self.get_clock().now().nanoseconds / 1e9
        for marker in self.markers:
            dx = marker["x"] - x
            dy = marker["y"] - y
            d = math.hypot(dx, dy)
            if d > self.detection_range:
                continue
            bearing = angle_wrap(math.atan2(dy, dx) - yaw)
            if self.require_fov and abs(bearing) > self.fov_rad * 0.5:
                continue
            confidence = max(0.2, 1.0 - d / max(0.01, self.detection_range))
            obs = {
                "stamp": stamp,
                "robot_id": self.robot,
                "source": "fake_tag_detector",
                "marker_id": marker["id"],
                "class_name": marker["class_name"],
                "label": marker["label"],
                "confidence": round(confidence, 3),
                "distance": round(d, 3),
                "bearing": round(bearing, 3),
                "room_id": marker["room_id"],
                "pose_map": {"x": marker["x"], "y": marker["y"], "yaw": marker["yaw"]},
            }
            self.obs_pub.publish(String(data=json.dumps(obs)))
            visible.append(marker)
        self._publish_rviz_markers(visible)

    def _publish_rviz_markers(self, visible: List[Dict]) -> None:
        arr = MarkerArray()
        now = self.get_clock().now().to_msg()
        for idx, marker in enumerate(visible):
            m = Marker()
            m.header.stamp = now
            m.header.frame_id = "map"
            m.ns = f"{self.robot}_visible_fake_tags"
            m.id = int(marker["id"])
            m.type = Marker.CUBE
            m.action = Marker.ADD
            m.pose.position.x = marker["x"]
            m.pose.position.y = marker["y"]
            m.pose.position.z = 0.3
            m.pose.orientation.w = 1.0
            m.scale.x = 0.25
            m.scale.y = 0.25
            m.scale.z = 0.25
            m.color.r = 0.2
            m.color.g = 0.8
            m.color.b = 0.2
            m.color.a = 0.8
            arr.markers.append(m)

            t = Marker()
            t.header.stamp = now
            t.header.frame_id = "map"
            t.ns = f"{self.robot}_visible_fake_tag_text"
            t.id = int(marker["id"]) + 10000
            t.type = Marker.TEXT_VIEW_FACING
            t.action = Marker.ADD
            t.pose.position.x = marker["x"]
            t.pose.position.y = marker["y"]
            t.pose.position.z = 0.75
            t.pose.orientation.w = 1.0
            t.scale.z = 0.25
            t.color.r = 1.0
            t.color.g = 1.0
            t.color.b = 1.0
            t.color.a = 1.0
            t.text = f"{marker['label']} seen by {self.robot}"
            arr.markers.append(t)
        self.marker_pub.publish(arr)


def main(args=None):
    rclpy.init(args=args)
    node = FakeTagDetector()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
