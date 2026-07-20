import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

''' This is CameraNode which is using your system's camera
capturing your frames and publishing it to /camera/image_raw '''

# 👇 Every ROS2 node is a class extending 'Node'
class CameraNode(Node):
    def __init__(self):
        # Initialize the node and give it a name 'camera_node'
        super().__init__('camera_node')

        # Create a publisher that sends Image messages on topic '/camera/image_raw'
        # The '10' means it can queue up to 10 messages
        self.publisher_ = self.create_publisher(Image, '/camera/image_raw', 10)

        # Bridge for converting between OpenCV (cv2) and ROS Image messages
        self.bridge = CvBridge()

        # Open the default webcam (0)
        self.cap = cv2.VideoCapture(0,cv2.CAP_V4L2)

        # Create a timer that calls 'timer_callback' every 0.03 seconds (~30 FPS)
        self.timer = self.create_timer(0.03, self.timer_callback)

        # Log that the camera node has started
        self.get_logger().info("Camera node started")


    # 👇 This function runs every 0.03 seconds (timer callback)
    def timer_callback(self):
        try:
            # Read one frame from the webcam
            ret, frame = self.cap.read()

            # If frame not captured, warn and skip
            if not ret:
                self.get_logger().warn("Frame not captured")
                return

            # Convert the OpenCV frame (numpy array) to a ROS2 Image message
            img_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')

            # Publish the image to the '/camera/image_raw' topic
            self.publisher_.publish(img_msg)
            self.get_logger().info("📸 Frame published")

     
        except Exception as e:
            self.get_logger().error(e)

    # 👇 When the node shuts down, release the webcam
    def destroy_node(self):
        self.cap.release()
        super().destroy_node()
        
# -------------------------------------
# MAIN FUNCTION
# -------------------------------------
def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
