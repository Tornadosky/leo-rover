#!/usr/bin/env python3
"""A tiny 2D robot simulator for fast collaborative-search tests.

Why this exists:
- It lets Codex validate the semantic-search logic without Gazebo, Leo hardware,
  Nav2, or camera plugins.
- It publishes odometry, TF, and accepts simple PoseStamped goals.
- It also accepts cmd_vel, so smoke tests can verify that motion commands change
  odometry.

This is not meant to replace Leo/Gazebo. It is a deterministic first-stage test
fixture that should remain useful for CI and debugging.
"""
from __future__ import annotations

import json
import math
from typing import Dict, Optional

import rclpy
from geometry_msgs.msg import PoseStamped, TransformStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import String
from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster

from .utils import Pose2D, angle_wrap, load_yaml, parse_robot_names, quat_to_yaw, yaw_to_quat, write_json, ensure_artifact_dir


class RobotState:
    def __init__(self, name: str, pose: Pose2D) -> None:
        self.name = name
        self.pose = pose
        self.goal: Optional[Pose2D] = None
        self.last_cmd = Twist()
        self.cmd_timeout_sec = 0.5
        self.last_cmd_time: float = -999.0
        self.goal_reached_once = True


class LogicalRobotSim(Node):
    def __init__(self) -> None:
        super().__init__("logical_robot_sim")
        self.declare_parameter("robots", "leo1,leo2")
        self.declare_parameter("start_poses_file", "")
        self.declare_parameter("artifact_dir", "artifacts")
        self.declare_parameter("linear_speed", 0.45)
        self.declare_parameter("angular_speed", 1.2)
        self.declare_parameter("goal_tolerance", 0.12)
        self.declare_parameter("yaw_tolerance", 0.25)
        self.declare_parameter("timer_period", 0.05)
        self.declare_parameter("use_sim_time", True)

        self.artifact_dir = ensure_artifact_dir(self.get_parameter("artifact_dir").value)
        self.linear_speed = float(self.get_parameter("linear_speed").value)
        self.angular_speed = float(self.get_parameter("angular_speed").value)
        self.goal_tolerance = float(self.get_parameter("goal_tolerance").value)
        self.yaw_tolerance = float(self.get_parameter("yaw_tolerance").value)
        timer_period = float(self.get_parameter("timer_period").value)

        robot_names = parse_robot_names(self.get_parameter("robots").value)
        start_poses = self._load_start_poses(robot_names)
        self.robots: Dict[str, RobotState] = {name: RobotState(name, start_poses[name]) for name in robot_names}

        self.odom_pubs: Dict[str, object] = {}
        self.status_pubs: Dict[str, object] = {}
        self.goal_reached_pubs: Dict[str, object] = {}
        self.tf_broadcaster = TransformBroadcaster(self)
        self.static_tf_broadcaster = StaticTransformBroadcaster(self)
        self.subscriptions_keepalive = []

        for name in robot_names:
            self.odom_pubs[name] = self.create_publisher(Odometry, f"/{name}/odom", 10)
            self.status_pubs[name] = self.create_publisher(String, f"/{name}/sim_status", 10)
            self.goal_reached_pubs[name] = self.create_publisher(String, f"/{name}/goal_reached", 10)
            self.subscriptions_keepalive.append(
                self.create_subscription(PoseStamped, f"/{name}/goal_pose", lambda msg, n=name: self._goal_cb(n, msg), 10)
            )
            self.subscriptions_keepalive.append(
                self.create_subscription(Twist, f"/{name}/cmd_vel", lambda msg, n=name: self._cmd_cb(n, msg), 10)
            )

        self.last_tick = self.get_clock().now()
        self.timer = self.create_timer(timer_period, self._tick)
        self._publish_static_transforms()
        self._write_artifact("initial")
        self.get_logger().info(f"Logical sim running for robots: {robot_names}")

    def _load_start_poses(self, robot_names):
        poses = {name: Pose2D(float(i) * 1.0, 0.0, 0.0) for i, name in enumerate(robot_names)}
        path = str(self.get_parameter("start_poses_file").value or "")
        if path:
            try:
                data = load_yaml(path)
                raw = data.get("start_poses", {})
                for name in robot_names:
                    if name in raw:
                        poses[name] = Pose2D.from_any(raw[name])
            except Exception as exc:  # noqa: BLE001
                self.get_logger().warning(f"Could not load start poses from {path}: {exc}")
        return poses

    def _goal_cb(self, robot_name: str, msg: PoseStamped) -> None:
        pose = msg.pose
        yaw = quat_to_yaw(pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w)
        self.robots[robot_name].goal = Pose2D(pose.position.x, pose.position.y, yaw)
        self.robots[robot_name].goal_reached_once = False
        self.get_logger().info(f"{robot_name} got logical goal x={pose.position.x:.2f}, y={pose.position.y:.2f}, yaw={yaw:.2f}")

    def _cmd_cb(self, robot_name: str, msg: Twist) -> None:
        state = self.robots[robot_name]
        state.last_cmd = msg
        state.last_cmd_time = self.get_clock().now().nanoseconds / 1e9
        # cmd_vel overrides current goal briefly, like real teleop would.

    def _tick(self) -> None:
        now = self.get_clock().now()
        dt = max(0.001, (now - self.last_tick).nanoseconds / 1e9)
        self.last_tick = now
        now_sec = now.nanoseconds / 1e9

        for state in self.robots.values():
            cmd_active = (now_sec - state.last_cmd_time) < state.cmd_timeout_sec
            if cmd_active:
                self._integrate_cmd(state, dt)
            elif state.goal is not None:
                self._move_towards_goal(state, dt)
            self._publish_state(state)
        self._write_artifact("latest")

    def _integrate_cmd(self, state: RobotState, dt: float) -> None:
        vx = float(state.last_cmd.linear.x)
        wz = float(state.last_cmd.angular.z)
        state.pose.x += vx * math.cos(state.pose.yaw) * dt
        state.pose.y += vx * math.sin(state.pose.yaw) * dt
        state.pose.yaw = angle_wrap(state.pose.yaw + wz * dt)

    def _move_towards_goal(self, state: RobotState, dt: float) -> None:
        assert state.goal is not None
        dx = state.goal.x - state.pose.x
        dy = state.goal.y - state.pose.y
        distance = math.hypot(dx, dy)
        if distance <= self.goal_tolerance:
            yaw_err = angle_wrap(state.goal.yaw - state.pose.yaw)
            if abs(yaw_err) <= self.yaw_tolerance:
                if not state.goal_reached_once:
                    payload = {
                        "robot_id": state.name,
                        "event": "goal_reached",
                        "goal": state.goal.as_dict(),
                        "pose": state.pose.as_dict(),
                        "stamp": self.get_clock().now().nanoseconds / 1e9,
                    }
                    self.goal_reached_pubs[state.name].publish(String(data=json.dumps(payload)))
                    state.goal_reached_once = True
                    self.get_logger().info(f"{state.name} reached logical goal")
                state.goal = None
                return
            state.pose.yaw = angle_wrap(state.pose.yaw + max(-self.angular_speed * dt, min(self.angular_speed * dt, yaw_err)))
            return

        desired_yaw = math.atan2(dy, dx)
        yaw_err = angle_wrap(desired_yaw - state.pose.yaw)
        if abs(yaw_err) > 0.20:
            state.pose.yaw = angle_wrap(state.pose.yaw + max(-self.angular_speed * dt, min(self.angular_speed * dt, yaw_err)))
            return
        step = min(self.linear_speed * dt, distance)
        state.pose.x += step * math.cos(state.pose.yaw)
        state.pose.y += step * math.sin(state.pose.yaw)

    def _publish_state(self, state: RobotState) -> None:
        stamp = self.get_clock().now().to_msg()
        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = f"{state.name}/odom"
        odom.child_frame_id = f"{state.name}/base_link"
        odom.pose.pose.position.x = state.pose.x
        odom.pose.pose.position.y = state.pose.y
        qx, qy, qz, qw = yaw_to_quat(state.pose.yaw)
        odom.pose.pose.orientation.x = qx
        odom.pose.pose.orientation.y = qy
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x = state.last_cmd.linear.x
        odom.twist.twist.angular.z = state.last_cmd.angular.z
        self.odom_pubs[state.name].publish(odom)

        map_to_odom = TransformStamped()
        map_to_odom.header.stamp = stamp
        map_to_odom.header.frame_id = "map"
        map_to_odom.child_frame_id = f"{state.name}/odom"
        map_to_odom.transform.rotation.w = 1.0

        odom_to_base = TransformStamped()
        odom_to_base.header.stamp = stamp
        odom_to_base.header.frame_id = f"{state.name}/odom"
        odom_to_base.child_frame_id = f"{state.name}/base_link"
        odom_to_base.transform.translation.x = state.pose.x
        odom_to_base.transform.translation.y = state.pose.y
        odom_to_base.transform.rotation.x = qx
        odom_to_base.transform.rotation.y = qy
        odom_to_base.transform.rotation.z = qz
        odom_to_base.transform.rotation.w = qw
        self.tf_broadcaster.sendTransform([map_to_odom, odom_to_base])

        status = {
            "robot_id": state.name,
            "pose": state.pose.as_dict(),
            "goal": state.goal.as_dict() if state.goal else None,
            "stamp": self.get_clock().now().nanoseconds / 1e9,
        }
        self.status_pubs[state.name].publish(String(data=json.dumps(status)))

    def _publish_static_transforms(self) -> None:
        transforms = []
        stamp = self.get_clock().now().to_msg()
        for name in self.robots:
            t = TransformStamped()
            t.header.stamp = stamp
            t.header.frame_id = f"{name}/base_link"
            t.child_frame_id = f"{name}/laser_frame"
            t.transform.translation.x = 0.10
            t.transform.translation.z = 0.18
            t.transform.rotation.w = 1.0
            transforms.append(t)
        if transforms:
            self.static_tf_broadcaster.sendTransform(transforms)

    def _write_artifact(self, suffix: str) -> None:
        payload = {
            "pass": True,
            "node": "logical_robot_sim",
            "robots": {name: state.pose.as_dict() for name, state in self.robots.items()},
        }
        write_json(f"{self.artifact_dir}/logical_robot_sim_{suffix}.json", payload)


def main(args=None):
    rclpy.init(args=args)
    node = LogicalRobotSim()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
