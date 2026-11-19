#!/usr/bin/env python3
"""Map an existing 4-joint JointState message to CAD joint names in declared order.
The adapter is only for the isolated CAD+CPG launch; it does not change /joint_states.
"""
import json
from pathlib import Path
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from ament_index_python.packages import get_package_share_directory

class Adapter(Node):
    def __init__(self):
        super().__init__('lamp_cad_joint_adapter')
        p=Path(get_package_share_directory('lamp_cad_4dof'))/'urdf'/'joint_pivots.json'
        self.targets=[j['name'] for j in json.loads(p.read_text())['joints']]
        self.p=self.create_publisher(JointState,'/cad_joint_states',10)
        self.create_subscription(JointState,'/joint_states',self.callback,10)
        self.warned=False
        self.get_logger().info('CAD Joint Adapter: targets='+str(self.targets))
        self.get_logger().info('Source joint states will be mapped by order; verify the source order is J1, J2, J3, J4.')
    def callback(self,msg):
        if len(msg.position)<4:
            if not self.warned:
                self.get_logger().warning('Input /joint_states has fewer than 4 values.')
                self.warned=True
            return
        m=JointState()
        m.header=msg.header
        m.name=self.targets
        m.position=[float(v) for v in msg.position[:4]]
        m.velocity=[float(v) for v in msg.velocity[:4]] if len(msg.velocity)>=4 else []
        m.effort=[float(v) for v in msg.effort[:4]] if len(msg.effort)>=4 else []
        self.p.publish(m)

def main():
    rclpy.init()
    node=Adapter()
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:node.destroy_node();rclpy.try_shutdown()

if __name__=='__main__':main()
