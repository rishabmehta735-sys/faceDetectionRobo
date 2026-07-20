#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import os
import pickle
from deepface import DeepFace #type: ignore
from scipy.spatial.distance import cosine # For fast distance calculation


# ArcFace is used for representation/verification because it's a good balance of accuracy and speed.
RECOGNITION_MODEL = 'ArcFace'
# 'opencv' is much faster than 'retinaface' for real-time detection, but less accurate.
DETECTOR_BACKEND = 'mediapipe' 
# Maximum allowable distance for two faces to be considered the same person (check DeepFace documentation for model thresholds)
# For ArcFace, a common threshold is around 0.68. Distance < Threshold = Match.
VERIFICATION_THRESHOLD = 0.68 


'''This is FaceRecognitionNode which is subscribing '/camera/image_raw' 
skipping few frames for optimization analzying the face and checking 
whether face exists if it exists then fine otherwise it will store 
it in known_faces directory  '''
class FaceRecognitionNode(Node):
    def __init__(self):
        try:
            super().__init__('face_recognition_node')
            self.bridge = CvBridge()
            self.subscription = self.create_subscription(
                Image,
                '/camera/image_raw',
                self.listener_callback,
                1
            )
            self.publisher = self.create_publisher(Image, '/face_recognition/image', 10)
            
            # --- Memory Caching Setup ---
            self.memory_path = "known_faces"
            os.makedirs(self.memory_path, exist_ok=True)
            # Dictionary to hold the pre-calculated embeddings: {'user_name': numpy_embedding_vector}
            self.known_embeddings = {}
            self.get_logger().info("Reaching to load_embeddings")
            self.load_known_embeddings()
            
            self.get_logger().info("✅ Face Recognition Node Started")
        except Exception as e:
            print("ERROR IS :",e)

    # -------------------------------------
    # Initialization: Load and cache embeddings
    # -------------------------------------
    def load_known_embeddings(self):
        self.get_logger().info("Loading and calculating known face embeddings...")
        
        # 1. Clean up old .jpg files and look for new ones
        for file_name in os.listdir(self.memory_path):
            if file_name.endswith(".jpg"):
                user_name = file_name[:-4]
                file_path = os.path.join(self.memory_path, file_name)
                
                try:
                    # DeepFace.represent calculates the 512-dimensional vector (embedding) once
                    result = DeepFace.represent(
                        img_path=file_path, 
                        model_name=RECOGNITION_MODEL, 
                        detector_backend=DETECTOR_BACKEND,
                        enforce_detection=True # Ensures we only store valid faces
                    )
                    # DeepFace.represent returns a list of dictionaries; we take the first embedding
                    self.known_embeddings[user_name] = result[0]["embedding"]
                    self.get_logger().info(f"Loaded embedding for: {user_name}")
                except Exception as e:
                    self.get_logger().error(f"Could not process {user_name}: {e}")
        
        self.get_logger().info(f"Loaded {len(self.known_embeddings)} known faces into memory.")

    # -------------------------------------
    # Core Logic: Find a match using fast vector distance
    # -------------------------------------
    def find_match(self, detected_face_embedding):
        best_match_name = "Unknown"
        min_distance = VERIFICATION_THRESHOLD # Start at the max allowed distance

        if not self.known_embeddings:
            return best_match_name
            
        # Iterate over cached embeddings (this is a fast NumPy operation!)
        for name, known_emb in self.known_embeddings.items():
            # Calculate Cosine Distance (1 - Cosine Similarity)
            # This is much faster than calling DeepFace.verify() repeatedly
            distance = cosine(np.array(detected_face_embedding), np.array(known_emb))
            
            if distance < min_distance:
                min_distance = distance
                best_match_name = name
                
        return best_match_name

    # -------------------------------------
    # Save a NEW face (and immediately generate its embedding)
    # -------------------------------------
    def save_new_face(self, detected_face_crop):
        try:
            # 1. Generate the name
            new_id = len(self.known_embeddings) + 1
            new_name = f"person_{new_id}"
            file_path = os.path.join(self.memory_path, f"{new_name}.jpg")

            # 2. Save the image file (for persistence)
            cv2.imwrite(file_path, detected_face_crop)
            
            # 3. Generate and cache the embedding (THE FAST PART)
            new_embedding = DeepFace.represent(
                img_path=file_path, 
                model_name=RECOGNITION_MODEL, 
                detector_backend=DETECTOR_BACKEND,
                enforce_detection=True
            )[0]["embedding"]
            
            self.known_embeddings[new_name] = new_embedding
            self.get_logger().info(f"🧠 New face stored as {new_name}")
            return new_name
            
        except Exception as e:
            self.get_logger().error(f"Error saving new face: {e}")
            return "Unknown"

    # -------------------------------------
    # CALLBACK: Runs every time a new frame arrives
    # -------------------------------------
    def listener_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            
            # --- OPTIMIZATION 1: Frame Skipping ---
            # The frame is still processed, but the heavy DeepFace call is skipped.
            self.frame_count = getattr(self, 'frame_count', 0) + 1
            self.skip_rate = 3  # Process roughly 10 FPS / 3 = 3.3 FPS
            
            if self.frame_count % self.skip_rate != 0:
                # If skipping, just publish the raw frame or the last annotated frame
                self.publisher.publish(self.bridge.cv2_to_imgmsg(frame, 'bgr8'))
                return

            
            # OPTIMIZATION 2: Use faster detector backend
            detections = DeepFace.extract_faces(
                img_path=frame,
                detector_backend=DETECTOR_BACKEND, 
                enforce_detection=False # Allows processing even if DeepFace is unsure
                )

            for face in detections:
                region = face["facial_area"]
                x, y, w, h = region["x"], region["y"], region["w"], region["h"]
                    
                # Ensure the crop is within frame boundaries
                detected_face = frame[y:y+h, x:x+w]
                    
                # --- VERIFICATION ---
                # 1. Get the embedding for the detected face *once*
                # DeepFace.represent is still slow, but it's only run once per detected face, 
                # instead of once for EVERY KNOWN face (as in your old loop).
                detected_embedding = DeepFace.represent(
                img_path=detected_face, 
                model_name=RECOGNITION_MODEL, 
                detector_backend=DETECTOR_BACKEND, # Ensure same detector is used for consistency
                enforce_detection=False
                )[0]["embedding"]
                    
                # 2. Find the match using the fast NumPy comparison
                match_name = self.find_match(detected_embedding)

                if match_name != "Unknown":
                    # Known Face
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(frame, match_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        
                        # --- PUBLISH THE ID TO THE VOICE NODE (NEW LOGIC) ---
                        # You would publish the recognized ID here, e.g., self.id_publisher.publish(String(data=match_name))

                else:
                    # New Face - Logic to store a new face
                    # NOTE: Saving a new face here will cause a stutter due to file I/O and embedding generation.
                    # In a production system, this should be done only on a dedicated "enrollment" command.
                        
                    # For a quick start, we save it instantly:
                    new_id = self.save_new_face(detected_face)
                        
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                    cv2.putText(frame, new_id, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
          
     
        except Exception as e:
            self.get_logger().error(f"Major Error: {e}")

        # Publish annotated frame
        self.publisher.publish(self.bridge.cv2_to_imgmsg(frame, 'bgr8'))

# -------------------------------------
# MAIN FUNCTION
# -------------------------------------
def main(args=None):
    rclpy.init(args=args)
    node = FaceRecognitionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()