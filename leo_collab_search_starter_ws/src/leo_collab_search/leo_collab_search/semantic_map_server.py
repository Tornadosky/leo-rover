#!/usr/bin/env python3
"""Shared semantic map server for collaborative search.

Input:  /semantic_observations  std_msgs/String JSON
Output: /semantic_map           std_msgs/String JSON
        /semantic_map_markers   visualization_msgs/MarkerArray
Artifacts:
        artifacts/semantic_map_latest.json
        artifacts/search_result.json if target found
"""
from __future__ import annotations

import json
from typing import Dict, Tuple

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from visualization_msgs.msg import Marker, MarkerArray

from .utils import ensure_artifact_dir, write_json


class SemanticMapServer(Node):
    def __init__(self) -> None:
        super().__init__("semantic_map_server")
        self.declare_parameter("artifact_dir", "artifacts")
        self.declare_parameter("target_marker_id", -1)
        self.declare_parameter("target_class", "")
        self.declare_parameter("merge_distance", 0.65)
        self.declare_parameter("publish_rate", 1.0)
        self.declare_parameter("use_sim_time", True)

        self.artifact_dir = ensure_artifact_dir(str(self.get_parameter("artifact_dir").value))
        self.target_marker_id = int(self.get_parameter("target_marker_id").value)
        self.target_class = str(self.get_parameter("target_class").value).strip()
        self.merge_distance = float(self.get_parameter("merge_distance").value)
        self.objects: Dict[str, Dict] = {}
        self.observation_count = 0
        self.target_found = False
        self.target_object_key = None

        self.sub = self.create_subscription(String, "/semantic_observations", self._obs_cb, 50)
        self.map_pub = self.create_publisher(String, "/semantic_map", 10)
        self.marker_pub = self.create_publisher(MarkerArray, "/semantic_map_markers", 10)
        self.timer = self.create_timer(1.0 / float(self.get_parameter("publish_rate").value), self._publish)
        self.get_logger().info("Semantic map server started")

    def _key_for_observation(self, obs: Dict) -> str:
        marker_id = int(obs.get("marker_id", -1))
        if marker_id >= 0:
            return f"tag:{marker_id}"
        class_name = str(obs.get("class_name", "object"))
        pose = obs.get("pose_map", {})
        x = float(pose.get("x", 0.0))
        y = float(pose.get("y", 0.0))
        # Simple nearest-neighbor fusion for untagged objects.
        for key, obj in self.objects.items():
            if obj.get("class_name") != class_name:
                continue
            ox = obj["pose_map"]["x"]
            oy = obj["pose_map"]["y"]
            if ((x - ox) ** 2 + (y - oy) ** 2) ** 0.5 <= self.merge_distance:
                return key
        return f"obj:{class_name}:{len(self.objects) + 1}"

    def _obs_cb(self, msg: String) -> None:
        try:
            obs = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().warning(f"Ignoring malformed observation: {msg.data[:100]}")
            return
        self.observation_count += 1
        key = self._key_for_observation(obs)
        pose = obs.get("pose_map", {})
        stamp = float(obs.get("stamp", self.get_clock().now().nanoseconds / 1e9))
        confidence = float(obs.get("confidence", 0.5))
        if key not in self.objects:
            self.objects[key] = {
                "object_id": key,
                "marker_id": int(obs.get("marker_id", -1)),
                "class_name": str(obs.get("class_name", "object")),
                "label": str(obs.get("label", key)),
                "pose_map": {
                    "x": float(pose.get("x", 0.0)),
                    "y": float(pose.get("y", 0.0)),
                    "yaw": float(pose.get("yaw", 0.0)),
                },
                "room_id": str(obs.get("room_id", "unknown")),
                "confidence": confidence,
                "first_seen": stamp,
                "last_seen": stamp,
                "seen_by": [str(obs.get("robot_id", "unknown"))],
                "observations": 1,
                "source": str(obs.get("source", "unknown")),
            }
        else:
            obj = self.objects[key]
            old_conf = float(obj.get("confidence", 0.5))
            obj["confidence"] = round(0.75 * old_conf + 0.25 * confidence, 3)
            obj["last_seen"] = stamp
            obj["observations"] = int(obj.get("observations", 0)) + 1
            robot_id = str(obs.get("robot_id", "unknown"))
            if robot_id not in obj["seen_by"]:
                obj["seen_by"].append(robot_id)
            # Tags are fixed; untagged objects are averaged for stability.
            if int(obj.get("marker_id", -1)) < 0:
                alpha = 0.2
                obj["pose_map"]["x"] = round((1 - alpha) * obj["pose_map"]["x"] + alpha * float(pose.get("x", 0.0)), 3)
                obj["pose_map"]["y"] = round((1 - alpha) * obj["pose_map"]["y"] + alpha * float(pose.get("y", 0.0)), 3)

        if self._is_target(self.objects[key]):
            self.target_found = True
            self.target_object_key = key
            write_json(f"{self.artifact_dir}/search_result.json", {
                "pass": True,
                "event": "target_found",
                "target": self.objects[key],
                "observation_count": self.observation_count,
            })

    def _is_target(self, obj: Dict) -> bool:
        if self.target_marker_id >= 0 and int(obj.get("marker_id", -1)) == self.target_marker_id:
            return True
        if self.target_class and str(obj.get("class_name", "")) == self.target_class:
            return True
        return False

    def _map_payload(self) -> Dict:
        return {
            "pass": True,
            "node": "semantic_map_server",
            "observation_count": self.observation_count,
            "object_count": len(self.objects),
            "target_found": self.target_found,
            "target_object_key": self.target_object_key,
            "objects": list(self.objects.values()),
        }

    def _publish(self) -> None:
        payload = self._map_payload()
        self.map_pub.publish(String(data=json.dumps(payload)))
        self._publish_markers()
        write_json(f"{self.artifact_dir}/semantic_map_latest.json", payload)

    def _publish_markers(self) -> None:
        arr = MarkerArray()
        now = self.get_clock().now().to_msg()
        for i, obj in enumerate(self.objects.values()):
            pose = obj["pose_map"]
            marker = Marker()
            marker.header.stamp = now
            marker.header.frame_id = "map"
            marker.ns = "semantic_objects"
            marker.id = i
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            marker.pose.position.x = float(pose["x"])
            marker.pose.position.y = float(pose["y"])
            marker.pose.position.z = 0.25
            marker.pose.orientation.w = 1.0
            marker.scale.x = 0.35
            marker.scale.y = 0.35
            marker.scale.z = 0.35
            if self._is_target(obj):
                marker.color.r = 1.0
                marker.color.g = 0.2
                marker.color.b = 0.2
            else:
                marker.color.r = 0.2
                marker.color.g = 0.6
                marker.color.b = 1.0
            marker.color.a = 0.9
            arr.markers.append(marker)

            text = Marker()
            text.header.stamp = now
            text.header.frame_id = "map"
            text.ns = "semantic_object_labels"
            text.id = i + 10000
            text.type = Marker.TEXT_VIEW_FACING
            text.action = Marker.ADD
            text.pose.position.x = float(pose["x"])
            text.pose.position.y = float(pose["y"])
            text.pose.position.z = 0.75
            text.pose.orientation.w = 1.0
            text.scale.z = 0.28
            text.color.r = 1.0
            text.color.g = 1.0
            text.color.b = 1.0
            text.color.a = 1.0
            text.text = f"{obj.get('label', obj['object_id'])}\nseen:{','.join(obj.get('seen_by', []))}"
            arr.markers.append(text)
        self.marker_pub.publish(arr)


def main(args=None):
    rclpy.init(args=args)
    node = SemanticMapServer()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
