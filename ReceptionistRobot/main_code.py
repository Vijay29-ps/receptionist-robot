from flask import Flask, render_template, Response
import cv2
import numpy as np
import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pyttsx3
import speech_recognition as sr
import re
from googletrans import Translator

# Flask App
app = Flask(__name__)

# YOLO Model Paths
MODEL_CFG = "/home/vps/ReceptionistRobot/yolov3.cfg"
MODEL_WEIGHTS = "/home/vps/ReceptionistRobot/yolov3.weights"
COCO_NAMES = "/home/vps/ReceptionistRobot/coco.names"

# Check if YOLO files exist
for file_path in [MODEL_CFG, MODEL_WEIGHTS, COCO_NAMES]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} not found. Please check the path.")

# Load YOLO network
with open(COCO_NAMES, "r") as f:
    class_names = f.read().strip().split("\n")

net = cv2.dnn.readNetFromDarknet(MODEL_CFG, MODEL_WEIGHTS)
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

INPUT_WIDTH = 416
INPUT_HEIGHT = 416
USB_CAMERA_INDEX = 2

# SQLite setup
conn = sqlite3.connect('visitors.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS visitors
             (name TEXT, email TEXT, phone TEXT, visitor_type TEXT, visit_purpose TEXT, time TIMESTAMP, language TEXT)''')
conn.commit()

# Text-to-Speech Engine
engine = pyttsx3.init()

# Email Validation
def validate_email(email):
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(regex, email))

# Send Email Notifications
def send_email(visitor_type, visitor_name, visit_purpose, visitor_email, phone):
    sender_email = "psvijay618@gmail.com"
    sender_password = "jhyq gybo odyd pghl"

    receiver_email = {
        "Interview Candidate": "ps.vijay@mobiusdtaas.ai",
        "Delivery": "vijayps2905@gmail.com",
        "Guest": "jayps2905@gmail.com"
    }.get(visitor_type, "default@example.com")

    subject = f"Visitor Registration: {visitor_type}"
    body = (f"Visitor Name: {visitor_name}\n"
            f"Purpose: {visit_purpose}\n"
            f"Email: {visitor_email}\n"
            f"Phone: {phone}\n")

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")

# Store Visitor Data
def store_visitor_data(visitor_data):
    try:
        c.execute("INSERT INTO visitors (name, email, phone, visitor_type, visit_purpose, time, language) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  visitor_data)
        conn.commit()
        print("Visitor data stored successfully.")
    except Exception as e:
        print(f"Error storing visitor data: {e}")

# Text-to-Speech
def speak(text, language="en"):
    translator = Translator()
    if language != "en":
        text = translator.translate(text, src="en", dest=language).text
    engine.setProperty('rate', 150)
    engine.say(text)
    engine.runAndWait()

# YOLO Object Detection
def detect_objects(frame):
    height, width = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (INPUT_WIDTH, INPUT_HEIGHT), swapRB=True, crop=False)
    net.setInput(blob)
    layer_names = net.getLayerNames()
    output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
    detections = net.forward(output_layers)

    boxes, confidences, class_ids = [], [], []
    for output in detections:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.5:
                center_x, center_y, w, h = (detection[:4] * np.array([width, height, width, height])).astype("int")
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                boxes.append([x, y, int(w), int(h)])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
    result = []
    if len(indices) > 0:
        for i in indices.flatten():
            x, y, w, h = boxes[i]
            label = class_names[class_ids[i]]
            result.append((label, confidences[i], (x, y, x + w, y + h)))

    return result

# Video Streaming
def generate_frames():
    cap = cv2.VideoCapture(USB_CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to access camera at index {USB_CAMERA_INDEX}.")

    while True:
        success, frame = cap.read()
        if not success:
            break
        detections = detect_objects(frame)
        for label, confidence, box in detections:
            x1, y1, x2, y2 = box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            text = f"{label}: {confidence:.2f}"
            cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    cap.release()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Tkinter GUI
def main_gui():
    root = tk.Tk()
    root.title("Receptionist Robot - Astra")
    root.geometry("800x600")
    root.configure(bg="#f0f5f9")

    tk.Label(root, text="Welcome to Mobius Family", font=("Helvetica", 24, "bold"), bg="#f0f5f9").pack(pady=20)

    tk.Label(root, text="Please select your preferred language:", bg="#f0f5f9").pack(pady=10)
    language_var = tk.StringVar(value="en")
    language_menu = ttk.OptionMenu(root, language_var, "English", "French", "Spanish", "Hindi", "Tamil")
    language_menu.pack()

    tk.Button(root, text="Visitor Registration", command=lambda: print("Voice Registration Triggered"), bg="#4caf50", fg="white").pack(pady=10)
    tk.Button(root, text="Exit", command=root.quit, bg="#f44336", fg="white").pack(pady=10)

    root.mainloop()

# Run Flask and Tkinter concurrently
if __name__ == "__main__":
    flask_thread = threading.Thread(target=app.run, kwargs={"debug": True, "host": "0.0.0.0"})
    flask_thread.start()
    main_gui()