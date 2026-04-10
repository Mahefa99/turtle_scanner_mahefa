import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from turtle_interfaces.srv import ResetMission


class MissionClientNode(Node):
    def __init__(self):
        super().__init__('mission_client')
        self.reset_client = self.create_client(ResetMission, '/reset_mission')
        self.detected_sub = self.create_subscription(
            Bool, '/target_detected', self.detected_callback, 10
        )
        self.sent_cycles = 0
        self.max_cycles = 3
        self.waiting_for_detection = True
        self.last_detection_state = False

        while not self.reset_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('En attente du service /reset_mission...')

    def detected_callback(self, msg: Bool):
        if self.sent_cycles >= self.max_cycles:
            return

        rising_edge = msg.data and not self.last_detection_state
        self.last_detection_state = msg.data

        if rising_edge and self.waiting_for_detection:
            self.waiting_for_detection = False
            self.send_reset_request()

    def send_reset_request(self):
        request = ResetMission.Request()
        request.target_x = 0.0
        request.target_y = 0.0
        request.random_target = True

        self.sent_cycles += 1
        future = self.reset_client.call_async(request)
        future.add_done_callback(self.handle_reset_response)

    def handle_reset_response(self, future):
        try:
            response = future.result()
            self.get_logger().info(response.message)
            if self.sent_cycles >= self.max_cycles:
                self.get_logger().info('Les 3 cycles automatiques sont termines.')
            else:
                self.waiting_for_detection = True
        except Exception as exc:  # pylint: disable=broad-except
            self.get_logger().error(f'Erreur lors de l appel du service : {exc}')
            self.sent_cycles -= 1
            self.waiting_for_detection = True


def main(args=None):
    rclpy.init(args=args)
    node = MissionClientNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
