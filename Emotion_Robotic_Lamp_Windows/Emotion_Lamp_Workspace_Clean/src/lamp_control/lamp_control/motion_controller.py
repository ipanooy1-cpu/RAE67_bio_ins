import math
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, Float64MultiArray


class MotionController(Node):

    def __init__(self):
        super().__init__('lamp_motion_controller')

        self.publisher = self.create_publisher(
            JointState, '/joint_states', 10
        )

        self.create_subscription(
            Float64MultiArray,
            '/lamp/cpg_offsets',
            self.cpg_callback, 10
        )

        self.create_subscription(
            Bool,
            '/lamp/interaction_enabled',
            self.interaction_callback, 10
        )

        self.joint_names = [
            'joint1_base',
            'joint2_shoulder',
            'joint3_elbow',
            'joint4_head'
        ]

        self.positions = [0.0] * 4
        self.cpg_offsets = [0.0] * 4

        self.last_cpg_time = None
        self.interaction_enabled = False

        self.state = 'STANDBY'
        self.state_start = time.monotonic()

        self.standby_duration = 30.0
        self.search_angle = math.radians(60)

        # Conservative simulation-only angle limits
        self.limits = [
            (-math.radians(60), math.radians(60)),
            (-0.55, 0.55),
            (-0.55, 0.55),
            (-0.45, 0.45)
        ]

        # Maximum simulation angular speed
        self.max_speed = 0.7

        self.last_update = time.monotonic()

        self.create_timer(0.05, self.update_motion)

        self.get_logger().info(
            'Motion Controller with 4-DOF CPG ready'
        )

    def cpg_callback(self, msg):
        if len(msg.data) != 4:
            return

        if not all(math.isfinite(v) for v in msg.data):
            return

        self.cpg_offsets = list(msg.data)
        self.last_cpg_time = time.monotonic()

    def interaction_callback(self, msg):
        enabled = bool(msg.data)

        if enabled == self.interaction_enabled:
            return

        self.interaction_enabled = enabled
        self.state_start = time.monotonic()

        if enabled:
            self.state = 'INTERACT'
            self.get_logger().info(
                'INTERACT: Personality active'
            )
        else:
            self.state = 'STANDBY'
            self.get_logger().info(
                'STANDBY: Personality stopped'
            )

    def smooth(self, a, b, progress):
        progress = max(0.0, min(1.0, progress))
        s = (1.0 - math.cos(math.pi * progress)) / 2.0
        return a + (b - a) * s

    def update_motion(self):
        now = time.monotonic()
        dt = max(
            0.0, min(now - self.last_update, 0.10)
        )
        self.last_update = now

        elapsed = now - self.state_start

        targets = [0.0] * 4

        if self.state == 'STANDBY':
            if elapsed >= self.standby_duration:
                self.state = 'SEARCH'
                self.state_start = now
                elapsed = 0.0
                self.get_logger().info('SEARCH started')

        if self.state == 'SEARCH':
            a = self.search_angle

            if elapsed < 3.0:
                targets[0] = self.smooth(
                    0.0, -a, elapsed / 3.0
                )
            elif elapsed < 9.0:
                targets[0] = self.smooth(
                    -a, a, (elapsed - 3.0) / 6.0
                )
            elif elapsed < 12.0:
                targets[0] = self.smooth(
                    a, 0.0, (elapsed - 9.0) / 3.0
                )
            else:
                self.state = 'STANDBY'
                self.state_start = now
                self.get_logger().info(
                    'SEARCH complete: STANDBY'
                )

        elif self.state == 'INTERACT':
            if (
                self.last_cpg_time is not None
                and now - self.last_cpg_time < 0.5
            ):
                targets = self.cpg_offsets.copy()

        # Enforce simulated joint angle limits
        for i in range(4):
            lower, upper = self.limits[i]
            targets[i] = max(
                lower, min(upper, targets[i])
            )

        # Slew rate limiting for all four joints
        max_step = self.max_speed * dt

        for i in range(4):
            difference = (
                targets[i] - self.positions[i]
            )

            step = max(
                -max_step,
                min(max_step, difference)
            )

            self.positions[i] += step

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = self.joint_names
        msg.position = self.positions.copy()

        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = MotionController()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
