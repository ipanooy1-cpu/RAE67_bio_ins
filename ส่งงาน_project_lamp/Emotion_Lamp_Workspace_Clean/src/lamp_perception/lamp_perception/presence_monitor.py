import json
import time
import urllib.request

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool


class PresenceMonitor(Node):

    def __init__(self):
        super().__init__('lamp_presence_monitor')

        self.declare_parameter(
            'camera_url',
            'http://host.docker.internal:8765/presence'
        )
        self.declare_parameter('detection_delay', 1.0)
        self.declare_parameter('lost_timeout', 30.0)

        self.url = self.get_parameter(
            'camera_url'
        ).value

        self.detection_delay = float(
            self.get_parameter('detection_delay').value
        )

        self.lost_timeout = float(
            self.get_parameter('lost_timeout').value
        )

        self.publisher = self.create_publisher(
            Bool,
            '/lamp/interaction_enabled',
            10
        )

        self.interacting = False
        self.first_detected = None
        self.last_detected = None
        self.last_error_log = 0.0

        self.timer = self.create_timer(
            0.25,
            self.check_presence
        )

        self.get_logger().info(
            'Presence Monitor started'
        )

    def read_camera(self):
        with urllib.request.urlopen(
            self.url, timeout=0.7
        ) as response:
            data = json.load(response)

        return (
            data.get('camera_ok') is True
            and data.get('human_detected') is True
        )

    def publish_interaction(self, enabled):
        msg = Bool()
        msg.data = enabled
        self.publisher.publish(msg)

        if enabled:
            self.get_logger().info(
                'HUMAN DETECTED -> INTERACT'
            )
        else:
            self.get_logger().info(
                'HUMAN LOST -> STANDBY'
            )

    def check_presence(self):
        now = time.monotonic()

        try:
            detected = self.read_camera()

        except Exception as exc:
            detected = False

            if now - self.last_error_log > 10.0:
                self.get_logger().warning(
                    f'Camera Bridge unavailable: {exc}'
                )
                self.last_error_log = now

        if detected:
            self.last_detected = now

            if self.first_detected is None:
                self.first_detected = now

            if (
                not self.interacting
                and now - self.first_detected
                >= self.detection_delay
            ):
                self.interacting = True
                self.publish_interaction(True)

        else:
            self.first_detected = None

            if (
                self.interacting
                and self.last_detected is not None
                and now - self.last_detected
                >= self.lost_timeout
            ):
                self.interacting = False
                self.last_detected = None
                self.publish_interaction(False)


def main(args=None):
    rclpy.init(args=args)
    node = PresenceMonitor()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
