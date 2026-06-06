#!/usr/bin/env python3
"""Simple collaborative room-search manager.

MVP behavior:
- Load room waypoints and fixed/generic assignments from YAML.
- Send each robot sequential PoseStamped goals to /<robot>/goal_pose for logical sim.
- Optionally use Nav2 NavigateToPose actions with use_nav2:=true.
- Stop when target marker/class is found, or finish all assigned waypoints.
- Write artifacts/collaborative_search_result.json continuously.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from std_msgs.msg import String

from .utils import ensure_artifact_dir, load_yaml, parse_robot_names, yaw_to_quat, write_json, as_bool

try:
    from nav2_msgs.action import NavigateToPose
    from rclpy.action import ActionClient
except Exception:  # noqa: BLE001
    NavigateToPose = None
    ActionClient = None


@dataclass
class RobotPlan:
    robot: str
    goals: List[Dict] = field(default_factory=list)
    index: int = 0
    active_goal: Optional[Dict] = None
    finished: bool = False
    nav2_goal_handle: object = None


class RoomSearchManager(Node):
    def __init__(self) -> None:
        super().__init__("room_search_manager")
        self.declare_parameter("robots", "leo1,leo2")
        self.declare_parameter("rooms_file", "")
        self.declare_parameter("artifact_dir", "artifacts")
        self.declare_parameter("target_marker_id", -1)
        self.declare_parameter("target_class", "")
        self.declare_parameter("assignment_mode", "fixed")  # fixed or greedy
        self.declare_parameter("use_nav2", False)
        self.declare_parameter("start_delay_sec", 1.0)
        self.declare_parameter("publish_rate", 1.0)
        self.declare_parameter("use_sim_time", True)

        self.robots = parse_robot_names(self.get_parameter("robots").value)
        rooms_file = str(self.get_parameter("rooms_file").value)
        if not rooms_file:
            raise RuntimeError("room_search_manager requires rooms_file")
        self.rooms_data = load_yaml(rooms_file)
        self.artifact_dir = ensure_artifact_dir(str(self.get_parameter("artifact_dir").value))
        self.target_marker_id = int(self.get_parameter("target_marker_id").value)
        self.target_class = str(self.get_parameter("target_class").value).strip()
        self.assignment_mode = str(self.get_parameter("assignment_mode").value)
        self.use_nav2 = as_bool(self.get_parameter("use_nav2").value)
        if self.use_nav2 and NavigateToPose is None:
            raise RuntimeError("use_nav2:=true requires nav2_msgs to be installed")

        self.plans: Dict[str, RobotPlan] = self._build_plans()
        self.target_found = False
        self.target_observation: Optional[Dict] = None
        self.started = False
        self.start_time = self.get_clock().now().nanoseconds / 1e9

        self.goal_pubs = {r: self.create_publisher(PoseStamped, f"/{r}/goal_pose", 10) for r in self.robots}
        self.status_pub = self.create_publisher(String, "/search_status", 10)
        self.subs = [
            self.create_subscription(String, "/semantic_observations", self._obs_cb, 50),
        ]
        for r in self.robots:
            self.subs.append(self.create_subscription(String, f"/{r}/goal_reached", lambda msg, robot=r: self._goal_reached_cb(robot, msg), 10))

        self.nav2_clients = {}
        if self.use_nav2:
            for r in self.robots:
                self.nav2_clients[r] = ActionClient(self, NavigateToPose, f"/{r}/navigate_to_pose")

        self.timer = self.create_timer(1.0 / float(self.get_parameter("publish_rate").value), self._tick)
        self.get_logger().info(f"Room search manager started; robots={self.robots}, use_nav2={self.use_nav2}")

    def _build_plans(self) -> Dict[str, RobotPlan]:
        plans = {r: RobotPlan(robot=r) for r in self.robots}
        rooms = self.rooms_data.get("rooms", {})
        assignments = self.rooms_data.get("assignments", {})
        if self.assignment_mode == "fixed" and assignments:
            for robot in self.robots:
                for room_id in assignments.get(robot, []):
                    room = rooms.get(room_id, {})
                    for wp in room.get("search_waypoints", []):
                        goal = dict(wp)
                        goal["room_id"] = room_id
                        plans[robot].goals.append(goal)
            return plans

        # Greedy fallback: round-robin all rooms over all robots.
        all_goals = []
        for room_id, room in rooms.items():
            for wp in room.get("search_waypoints", []):
                goal = dict(wp)
                goal["room_id"] = room_id
                all_goals.append(goal)
        for idx, goal in enumerate(all_goals):
            plans[self.robots[idx % len(self.robots)]].goals.append(goal)
        return plans

    def _obs_cb(self, msg: String) -> None:
        try:
            obs = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        marker_id = int(obs.get("marker_id", -1))
        class_name = str(obs.get("class_name", ""))
        if self.target_marker_id >= 0 and marker_id == self.target_marker_id:
            self._mark_target_found(obs)
        elif self.target_class and class_name == self.target_class:
            self._mark_target_found(obs)

    def _mark_target_found(self, obs: Dict) -> None:
        if not self.target_found:
            self.get_logger().info(f"Target found by {obs.get('robot_id')}: {obs}")
        self.target_found = True
        self.target_observation = obs
        self._write_result(pass_value=True, reason="target_found")

    def _goal_reached_cb(self, robot: str, msg: String) -> None:
        plan = self.plans[robot]
        if plan.finished:
            return
        plan.active_goal = None
        plan.index += 1
        if plan.index >= len(plan.goals):
            plan.finished = True
            self.get_logger().info(f"{robot} finished assigned search goals")
        else:
            self._send_next_goal(robot)

    def _tick(self) -> None:
        now = self.get_clock().now().nanoseconds / 1e9
        if not self.started and now - self.start_time >= float(self.get_parameter("start_delay_sec").value):
            self.started = True
            for robot in self.robots:
                self._send_next_goal(robot)

        if self.target_found:
            # Do not send more goals once the target is found in MVP.
            for plan in self.plans.values():
                plan.finished = True
        elif self.started:
            for robot, plan in self.plans.items():
                if not plan.finished and plan.active_goal is None:
                    self._send_next_goal(robot)

        self._publish_status()
        if all(p.finished for p in self.plans.values()) and not self.target_found:
            self._write_result(pass_value=False, reason="all_goals_finished_without_target")

    def _send_next_goal(self, robot: str) -> None:
        plan = self.plans[robot]
        if plan.index >= len(plan.goals):
            plan.finished = True
            return
        goal = plan.goals[plan.index]
        plan.active_goal = goal
        if self.use_nav2:
            self._send_nav2_goal(robot, goal)
        else:
            self.goal_pubs[robot].publish(self._goal_msg(goal))
        self.get_logger().info(f"Sent {robot} to {goal.get('room_id', 'unknown')} waypoint {plan.index + 1}/{len(plan.goals)}")

    def _goal_msg(self, goal: Dict) -> PoseStamped:
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        msg.pose.position.x = float(goal.get("x", 0.0))
        msg.pose.position.y = float(goal.get("y", 0.0))
        qx, qy, qz, qw = yaw_to_quat(float(goal.get("yaw", 0.0)))
        msg.pose.orientation.x = qx
        msg.pose.orientation.y = qy
        msg.pose.orientation.z = qz
        msg.pose.orientation.w = qw
        return msg

    def _send_nav2_goal(self, robot: str, goal: Dict) -> None:
        if NavigateToPose is None:
            return
        client = self.nav2_clients[robot]
        if not client.wait_for_server(timeout_sec=2.0):
            self.get_logger().warning(f"Nav2 action server not available for {robot}")
            return
        action_goal = NavigateToPose.Goal()
        action_goal.pose = self._goal_msg(goal)
        future = client.send_goal_async(action_goal)
        future.add_done_callback(lambda fut, r=robot: self._nav2_goal_response_cb(r, fut))

    def _nav2_goal_response_cb(self, robot: str, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warning(f"Nav2 goal rejected for {robot}")
            self.plans[robot].active_goal = None
            return
        self.plans[robot].nav2_goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(lambda fut, r=robot: self._nav2_result_cb(r, fut))

    def _nav2_result_cb(self, robot: str, future):
        # Treat any Nav2 result as completion for MVP; Codex can refine status codes.
        self._goal_reached_cb(robot, String(data=json.dumps({"event": "nav2_goal_result"})))

    def _payload(self) -> Dict:
        return {
            "pass": bool(self.target_found),
            "node": "room_search_manager",
            "target_found": self.target_found,
            "target_observation": self.target_observation,
            "robots": {
                robot: {
                    "assigned_goals": len(plan.goals),
                    "current_index": plan.index,
                    "active_goal": plan.active_goal,
                    "finished": plan.finished,
                }
                for robot, plan in self.plans.items()
            },
        }

    def _publish_status(self) -> None:
        payload = self._payload()
        self.status_pub.publish(String(data=json.dumps(payload)))
        write_json(f"{self.artifact_dir}/search_status_latest.json", payload)

    def _write_result(self, pass_value: bool, reason: str) -> None:
        payload = self._payload()
        payload["pass"] = pass_value
        payload["reason"] = reason
        write_json(f"{self.artifact_dir}/collaborative_search_result.json", payload)


def main(args=None):
    rclpy.init(args=args)
    node = RoomSearchManager()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
