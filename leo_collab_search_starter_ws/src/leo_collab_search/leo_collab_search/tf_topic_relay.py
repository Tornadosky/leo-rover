#!/usr/bin/env python3
"""Relay a namespaced TF topic onto the standard /tf topic.

The official Leo Gazebo bridge publishes dynamic transforms on /<robot>/tf.
Nav2 listens on /tf, so this small relay keeps the official bridge untouched
while making the simulator usable with standard Nav2 bringup.
"""
from __future__ import annotations

import rclpy
from rclpy.node import Node
from tf2_msgs.msg import TFMessage


class TfTopicRelay(Node):
    def __init__(self) -> None:
        super().__init__("tf_topic_relay")
        self.declare_parameter("robot", "leo1")

        robot = str(self.get_parameter("robot").value).strip(" /")
        if not robot:
            raise RuntimeError("tf_topic_relay requires a non-empty robot parameter")

        self.input_topic = f"/{robot}/tf"
        self.pub = self.create_publisher(TFMessage, "/tf", 100)
        self.sub = self.create_subscription(TFMessage, self.input_topic, self.pub.publish, 100)
        self.get_logger().info(f"Relaying {self.input_topic} -> /tf")


def main(args=None):
    rclpy.init(args=args)
    node = TfTopicRelay()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
