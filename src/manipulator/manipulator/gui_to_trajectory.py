"""Translate Joint State Publisher GUI sliders into Gazebo controller targets."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


class GuiToTrajectory(Node):
    def __init__(self):
        super().__init__('gui_to_trajectory')
        self.arm_names = [f'joint_{i}' for i in range(1, 6)]
        self.gripper_names = ['left_gear_joint']
        self.arm_pub = self.create_publisher(
            JointTrajectory, '/arm_controller/joint_trajectory', 10
        )
        self.gripper_pub = self.create_publisher(
            JointTrajectory, '/gripper_controller/joint_trajectory', 10
        )
        self.create_subscription(JointState, '/joint_states_gui', self.on_joint_state, 10)

    def on_joint_state(self, msg):
        positions = dict(zip(msg.name, msg.position))
        if all(name in positions for name in self.arm_names):
            command = self.make_trajectory(self.arm_names, [positions[n] for n in self.arm_names])
            self.arm_pub.publish(command)
        if all(name in positions for name in self.gripper_names):
            command = self.make_trajectory(
                self.gripper_names, [positions[n] for n in self.gripper_names]
            )
            self.gripper_pub.publish(command)

    @staticmethod
    def make_trajectory(names, values):
        trajectory = JointTrajectory()
        trajectory.joint_names = names
        point = JointTrajectoryPoint()
        point.positions = list(values)
        point.time_from_start.sec = 0
        point.time_from_start.nanosec = 250_000_000
        trajectory.points = [point]
        return trajectory


def main(args=None):
    rclpy.init(args=args)
    node = GuiToTrajectory()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
