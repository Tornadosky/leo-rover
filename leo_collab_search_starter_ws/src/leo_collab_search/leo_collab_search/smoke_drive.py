#!/usr/bin/env python3
"""Publish cmd_vel briefly and verify odometry changes.

Works with logical_robot_sim and real/sim Leo if /<robot>/cmd_vel and /<robot>/odom exist.
"""
from __future__ import annotations

import argparse
import json
import math
from typing import Optional, Tuple

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node

from .utils import write_json


class SmokeDrive(Node):
    def __init__(self, robot: str, artifact_dir: str, duration: float, speed: float) -> None:
        super().__init__("smoke_drive")
        self.robot = robot.strip(" /")
        self.artifact_dir = artifact_dir
        self.duration = duration
        self.speed = speed
        self.start_pose: Optional[Tuple[float, float]] = None
        self.last_pose: Optional[Tuple[float, float]] = None
        self.pub = self.create_publisher(Twist, f"/{self.robot}/cmd_vel", 10)
        self.sub = self.create_subscription(Odometry, f"/{self.robot}/odom", self._odom_cb, 10)
        self.start_time = self.get_clock().now().nanoseconds / 1e9
        self.timer = self.create_timer(0.05, self._tick)
        self.done = False

    def _odom_cb(self, msg: Odometry) -> None:
        p = msg.pose.pose.position
        pose = (float(p.x), float(p.y))
        if self.start_pose is None:
            self.start_pose = pose
        self.last_pose = pose

    def _tick(self) -> None:
        now = self.get_clock().now().nanoseconds / 1e9
        elapsed = now - self.start_time
        cmd = Twist()
        if elapsed < self.duration:
            cmd.linear.x = self.speed
        self.pub.publish(cmd)
        if elapsed > self.duration + 1.0 and not self.done:
            self.done = True
            moved = 0.0
            if self.start_pose and self.last_pose:
                moved = math.hypot(self.last_pose[0] - self.start_pose[0], self.last_pose[1] - self.start_pose[1])
            report = {
                "pass": moved > 0.05,
                "robot": self.robot,
                "start_pose": self.start_pose,
                "last_pose": self.last_pose,
                "distance_moved": moved,
                "duration": self.duration,
                "speed": self.speed,
            }
            write_json(f"{self.artifact_dir}/smoke_drive_{self.robot}.json", report)
            print(json.dumps(report, indent=2))
            rclpy.shutdown()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--robot", default="leo1")
    parser.add_argument("--artifact-dir", default="artifacts")
    parser.add_argument("--duration", type=float, default=2.0)
    parser.add_argument("--speed", type=float, default=0.25)
    args = parser.parse_args(argv)
    rclpy.init()
    node = SmokeDrive(args.robot, args.artifact_dir, args.duration, args.speed)
    try:
        rclpy.spin(node)
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
