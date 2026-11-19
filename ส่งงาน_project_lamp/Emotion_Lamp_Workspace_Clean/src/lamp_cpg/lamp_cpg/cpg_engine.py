import math
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String, Float64MultiArray


class CPGEngine(Node):

    def __init__(self):
        super().__init__('lamp_cpg_engine')

        self.pub = self.create_publisher(
            Float64MultiArray, '/lamp/cpg_offsets', 10
        )

        self.create_subscription(
            String, '/lamp/personality_mode',
            self.mode_callback, 10
        )

        self.create_subscription(
            Bool, '/lamp/interaction_enabled',
            self.enable_callback, 10
        )

        self.mode = 'neutral'
        self.enabled = False

        # Joint order: base, shoulder, elbow, head
        # All angular values are in radians.
        self.profiles = {
            'neutral': {
                'freq': 0.16,
                'pose': [0.0, 0.0, 0.0, 0.0],
                'amp': [0.015, 0.012, 0.010, 0.012],
                'phase': [0.0, 0.5, 1.0, 1.5]
            },
            'happy': {
                'freq': 0.55,
                'pose': [0.0, -0.10, 0.18, -0.08],
                'amp': [0.22, 0.10, 0.15, 0.14],
                'phase': [0.0, 0.8, 1.6, 2.4]
            },
            'sad': {
                'freq': 0.12,
                'pose': [0.0, 0.20, -0.25, 0.18],
                'amp': [0.025, 0.025, 0.035, 0.020],
                'phase': [0.0, 0.3, 0.8, 1.2]
            },
            'curious': {
                'freq': 0.24,
                'pose': [0.10, -0.12, 0.20, -0.15],
                'amp': [0.36, 0.04, 0.05, 0.12],
                'phase': [0.0, 0.5, 1.2, 2.0]
            }
        }

        self.pose = [0.0] * 4
        self.amplitudes = [0.0] * 4
        self.phases = [0.0] * 4

        self.coupling = 1.5
        self.last_time = time.monotonic()

        self.create_timer(0.02, self.update)

        self.get_logger().info(
            '4-DOF Personality CPG ready'
        )

    def mode_callback(self, msg):
        if msg.data not in self.profiles:
            self.get_logger().warn('Unknown personality')
            return

        self.mode = msg.data
        self.get_logger().info(
            f'Personality: {self.mode}'
        )

    def enable_callback(self, msg):
        self.enabled = bool(msg.data)

        self.get_logger().info(
            'Interaction ON' if self.enabled
            else 'Interaction OFF'
        )

    def update(self):
        now = time.monotonic()
        dt = max(0.0, min(now - self.last_time, 0.05))
        self.last_time = now

        profile = self.profiles[self.mode]

        target_pose = (
            profile['pose'] if self.enabled
            else [0.0] * 4
        )

        target_amp = (
            profile['amp'] if self.enabled
            else [0.0] * 4
        )

        # Blend posture and amplitude gradually
        alpha = 1.0 - math.exp(-2.0 * dt)

        for i in range(4):
            self.pose[i] += alpha * (
                target_pose[i] - self.pose[i]
            )

            self.amplitudes[i] += alpha * (
                target_amp[i] - self.amplitudes[i]
            )

        desired = profile['phase']
        derivatives = []

        # Coupled phase oscillator
        for i in range(4):
            dphi = 2.0 * math.pi * profile['freq']

            for j in range(4):
                if i != j:
                    dphi += self.coupling * math.sin(
                        self.phases[j] - self.phases[i]
                        - (desired[j] - desired[i])
                    )

            derivatives.append(dphi)

        for i in range(4):
            self.phases[i] = (
                self.phases[i] + derivatives[i] * dt
            ) % (2.0 * math.pi)

        wave = [math.sin(p) for p in self.phases]

        if self.mode == 'happy':
            # Additional upbeat double-beat motion
            wave[2] = (
                0.65 * math.sin(self.phases[2])
                + 0.35 * math.sin(2 * self.phases[2])
            )
            wave[3] = math.sin(
                2 * self.phases[3]
            )

        elif self.mode == 'curious':
            # Longer gaze near left/right extremes
            wave[0] = math.tanh(
                2.0 * math.sin(self.phases[0])
            )

        offsets = [
            self.pose[i]
            + self.amplitudes[i] * wave[i]
            for i in range(4)
        ]

        msg = Float64MultiArray()
        msg.data = offsets
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = CPGEngine()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
