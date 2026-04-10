import math
import random
from typing import List, Optional, Tuple

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Bool
from turtle_interfaces.srv import ResetMission
from turtlesim.msg import Pose
from turtlesim.srv import Kill, Spawn


class TurtleScannerNode(Node):
    def __init__(self):
        super().__init__('turtle_scanner_node')

        self.pose_scanner: Optional[Pose] = None
        self.pose_target: Optional[Pose] = None
        self.target_detected = False

        self.nb_lignes = 5
        self.y_start = 1.0
        self.y_step = 2.0
        self.x_min = 1.0
        self.x_max = 10.0
        self.waypoint_tolerance = 0.3
        self.detection_radius = 1.5
        self.kp_ang = 4.0
        self.kp_lin = 1.5
        self.linear_speed_max = 2.0

        self.waypoints = self.generate_waypoints()
        self.current_waypoint_index = 0

        self.pose_scanner_sub = self.create_subscription(
            Pose, '/turtle1/pose', self.scanner_pose_callback, 10
        )
        self.pose_target_sub = self.create_subscription(
            Pose, '/turtle_target/pose', self.target_pose_callback, 10
        )
        self.cmd_vel_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        self.detected_pub = self.create_publisher(Bool, '/target_detected', 10)

        self.spawn_client = self.create_client(Spawn, '/spawn')
        self.kill_client = self.create_client(Kill, '/kill')
        self.reset_service = self.create_service(
            ResetMission, '/reset_mission', self.handle_reset_mission
        )

        self.timer = self.create_timer(0.05, self.scan_step)

    def scanner_pose_callback(self, msg: Pose):
        self.pose_scanner = msg

    def target_pose_callback(self, msg: Pose):
        self.pose_target = msg

    def generate_waypoints(self) -> List[Tuple[float, float]]:
        waypoints = []
        for index in range(self.nb_lignes):
            y_value = self.y_start + index * self.y_step
            x_value = self.x_max if index % 2 == 0 else self.x_min
            waypoints.append((x_value, y_value))
        return waypoints

    def compute_angle(self, current_x: float, current_y: float, target_x: float, target_y: float):
        return math.atan2(target_y - current_y, target_x - current_x)

    def compute_distance(
        self, current_x: float, current_y: float, target_x: float, target_y: float
    ) -> float:
        return math.sqrt((target_x - current_x) ** 2 + (target_y - current_y) ** 2)

    def normalize_angle(self, angle: float) -> float:
        return math.atan2(math.sin(angle), math.cos(angle))

    def publish_detection(self, detected: bool):
        msg = Bool()
        msg.data = detected
        self.detected_pub.publish(msg)

    def stop_turtle(self):
        self.cmd_vel_pub.publish(Twist())

    def scan_step(self):
        if self.pose_scanner is None:
            return

        if self.pose_target is not None and not self.target_detected:
            distance_to_target = self.compute_distance(
                self.pose_scanner.x,
                self.pose_scanner.y,
                self.pose_target.x,
                self.pose_target.y,
            )
            if distance_to_target < self.detection_radius:
                self.target_detected = True
                self.stop_turtle()
                self.publish_detection(True)
                self.get_logger().info(
                    f'Cible detectee a ({self.pose_target.x:.2f}, {self.pose_target.y:.2f}) !'
                )
                return

        if self.target_detected:
            self.publish_detection(True)
            return

        self.publish_detection(False)

        if self.current_waypoint_index >= len(self.waypoints):
            self.stop_turtle()
            self.get_logger().info('Balayage termine')
            return

        target_x, target_y = self.waypoints[self.current_waypoint_index]
        distance = self.compute_distance(
            self.pose_scanner.x, self.pose_scanner.y, target_x, target_y
        )

        if distance < self.waypoint_tolerance:
            self.current_waypoint_index += 1
            if self.current_waypoint_index >= len(self.waypoints):
                self.stop_turtle()
                self.get_logger().info('Balayage termine')
            return

        desired_angle = self.compute_angle(
            self.pose_scanner.x, self.pose_scanner.y, target_x, target_y
        )
        angle_error = math.atan(math.tan((desired_angle - self.pose_scanner.theta) / 2.0))

        cmd = Twist()
        cmd.angular.z = self.kp_ang * angle_error
        cmd.linear.x = min(self.kp_lin * distance, self.linear_speed_max)
        self.cmd_vel_pub.publish(cmd)

    def reset_mission_state(self):
        self.waypoints = self.generate_waypoints()
        self.current_waypoint_index = 0
        self.target_detected = False
        self.publish_detection(False)

    def wait_for_required_services(self) -> bool:
        if not self.kill_client.wait_for_service(timeout_sec=2.0):
            return False
        if not self.spawn_client.wait_for_service(timeout_sec=2.0):
            return False
        return True

    def delete_previous_target(self):
        request = Kill.Request()
        request.name = 'turtle_target'
        future = self.kill_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)

    def spawn_new_target(self, target_x: float, target_y: float):
        request = Spawn.Request()
        request.x = target_x
        request.y = target_y
        request.theta = 0.0
        request.name = 'turtle_target'
        future = self.spawn_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
        future.result()

    def handle_reset_mission(self, request, response):
        if not self.wait_for_required_services():
            response.success = False
            response.message = 'Les services /kill ou /spawn ne sont pas disponibles.'
            return response

        target_x = request.target_x
        target_y = request.target_y
        if request.random_target:
            target_x = random.uniform(1.0, 10.0)
            target_y = random.uniform(1.0, 10.0)

        try:
            self.delete_previous_target()
        except Exception:  # pylint: disable=broad-except
            pass

        try:
            self.spawn_new_target(target_x, target_y)
            self.reset_mission_state()
            self.stop_turtle()
            response.success = True
            response.message = f'Mission reinitialisee. Nouvelle cible en x={target_x:.2f}, y={target_y:.2f}.'
            self.get_logger().info(response.message)
        except Exception as exc:  # pylint: disable=broad-except
            response.success = False
            response.message = f'Echec de la reinitialisation : {exc}'
            self.get_logger().error(response.message)

        return response


def main(args=None):
    rclpy.init(args=args)
    node = TurtleScannerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
