
import cv2
cap = cv2.VideoCapture(0)
ok, frame = cap.read()
print("Camera index 0:", ok)
cap.release()

cap = cv2.VideoCapture(1)
ok, frame = cap.read()
print("Camera index 1:", ok)
cap.release()
