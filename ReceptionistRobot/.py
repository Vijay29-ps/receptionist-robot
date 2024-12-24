import cv2

try:
    net = cv2.dnn.readNetFromTensorflow('mobilenet_ssd_v2_coco.pb', 'mobilenet_ssd_v2_coco.pbtxt')
    print("Model loaded successfully!")
except Exception as e:
    print(f"Error loading model: {e}")
