import random

import rclpy
from rclpy.node import Node
from turtlesim.srv import Spawn


class SpawnTargetNode(Node):
    def __init__(self):
        super().__init__('spawn_target')
        self.spawn_client = self.create_client(Spawn, '/spawn')

        while not self.spawn_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('En attente du service /spawn...')

        self.spawn_target()

    def spawn_target(self):
        request = Spawn.Request()
        request.x = random.uniform(1.0, 10.0)
        request.y = random.uniform(1.0, 10.0)
        request.theta = 0.0
        request.name = 'turtle_target'

        future = self.spawn_client.call_async(request)
        future.add_done_callback(
            lambda done_future: self._handle_spawn_response(done_future, request.x, request.y)
        )

    def _handle_spawn_response(self, future, target_x, target_y):
        try:
            future.result()
            self.get_logger().info(f'Cible creee en x={target_x:.2f}, y={target_y:.2f}')
        except Exception as exc:  # pylint: disable=broad-except
            self.get_logger().error(f'Erreur lors du spawn de la cible : {exc}')
        finally:
            self.destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = SpawnTargetNode()
    rclpy.spin(node)
    if rclpy.ok():
        node.destroy_node()
    rclpy.shutdown()
