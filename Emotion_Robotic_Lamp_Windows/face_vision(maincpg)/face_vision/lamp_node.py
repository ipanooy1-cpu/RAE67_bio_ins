"""ROS 2 atomic face observations -> four-DOF lamp command topics (no motor driver)."""
import json
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float64MultiArray, Float32MultiArray, ColorRGBA
from .lamp_controller import LampController


class LampEmotionNode(Node):
    def __init__(self):
        super().__init__('lamp_emotion_node')
        self.declare_parameter('min_strength', .35)
        self.declare_parameter('stable_s', .30)
        self.declare_parameter('timeout_s', .50)
        self.declare_parameter('max_speed_deg_s', 20.0)
        self.timeout = float(self.get_parameter('timeout_s').value)
        self.controller = LampController(
            min_strength=float(self.get_parameter('min_strength').value),
            stable_s=float(self.get_parameter('stable_s').value), timeout_s=self.timeout,
            max_speed_deg_s=float(self.get_parameter('max_speed_deg_s').value),
            start_time=time.monotonic())
        self.subscription = self.create_subscription(String, '/face/observation', self.receive, 10)
        self.pub_command = self.create_publisher(String, '/lamp/command', 10)
        self.pub_joints = self.create_publisher(Float64MultiArray, '/lamp/joint_commands_deg', 10)
        self.pub_rgb = self.create_publisher(ColorRGBA, '/lamp/rgb_command', 10)
        self.pub_hormones = self.create_publisher(Float32MultiArray, '/lamp/hormones', 10)
        self.pub_emotion = self.create_publisher(String, '/lamp/emotion', 10)
        self.timer = self.create_timer(self.controller.dt, self.tick)
        self.get_logger().info('Lamp controller started; outputs are commands, no servo driver attached')

    def receive(self, message):
        try:
            observation = json.loads(message.data)
            if not isinstance(observation, dict):
                raise ValueError('Observation must be an object')
            stamp = observation.get('stamp_ns')
            if type(stamp) is not int:
                raise ValueError('Missing ROS source stamp')
            age = (self.get_clock().now().nanoseconds - stamp) / 1e9
            # Requires common ROS clock / synchronized hosts. This is not camera exposure time.
            if age < -.1 or age > self.timeout:
                self.controller.gate.invalidate('source_timestamp_invalid_or_stale')
                return
            self.controller.observe(observation, time.monotonic())
        except (ValueError, TypeError, OverflowError):
            self.controller.gate.invalidate('invalid_observation_json')

    def tick(self):
        s = self.controller.step(time.monotonic())
        self.pub_command.publish(String(data=json.dumps(s, allow_nan=False)))
        self.pub_joints.publish(Float64MultiArray(data=s['q_deg']))
        self.pub_hormones.publish(Float32MultiArray(data=[s['hormones'][k] for k in ('Happy', 'Sad', 'Confused')]))
        self.pub_emotion.publish(String(data=s['mode']))
        color, b = s['light']['color'], s['light']['brightness']
        channels = [int(color[i:i + 2], 16) / 255.0 * b for i in (1, 3, 5)]
        self.pub_rgb.publish(ColorRGBA(r=channels[0], g=channels[1], b=channels[2], a=1.0))


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = LampEmotionNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
