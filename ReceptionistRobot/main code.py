import tensorflow as tf
import cv2
import numpy as np
import threading
import logging
from flask import Flask, render_template, Response
import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pyttsx3
from googletrans import Translator
import re
import tkinter as tk  # Import Tkinter for registration form
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Flask App
app = Flask(__name__)

# Logging Configuration
logging.basicConfig(level=logging.INFO)

# Configurable Model Paths for TensorFlow Object Detection
MODEL_PATH = os.getenv("MODEL_PATH", "/home/vps/tensorflow_model/saved_model/ssd_mobilenet_v2_coco_2018_03_29/saved_model")

# Load TensorFlow Object Detection Model
try:
    model = tf.saved_model.load(MODEL_PATH)
    logging.info("TensorFlow model loaded successfully.")
except Exception as e:
    logging.error(f"Error loading model: {e}")
    model = None

# SQLite setup
conn = sqlite3.connect('visitors.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS visitors
             (name TEXT, email TEXT, phone TEXT, visitor_type TEXT, visit_purpose TEXT, time TIMESTAMP, language TEXT)''')
conn.commit()

# Text-to-Speech Engine
engine = pyttsx3.init()

# Email Configuration (use environment variables for security)
EMAIL_ADDRESS = os.getenv("psvijay618@gmail.com")
EMAIL_PASSWORD = os.getenv("jhyq gybo odyd pghl")
# Email Validation
def validate_email(email):
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(regex, email))

# Send Email Notifications
def send_email(visitor_type, visitor_name, visit_purpose, visitor_email, phone):
    receiver_email = {
        "Interview Candidate": os.getenv("HR_EMAIL", "ps.vijay@mobiusdtaas.ai"),
        "Delivery": os.getenv("PURCHASE_MANAGER_EMAIL", "vijay2905ps2gmail.com"),
        "Guest": os.getenv("DEFAULT_EMAIL", "jayps2905@gmail.com")
    }.get(visitor_type, os.getenv("DEFAULT_EMAIL", "default@example.com"))

    subject = f"Visitor Registration: {visitor_type}"
    body = (f"Visitor Name: {visitor_name}\n"
            f"Purpose: {visit_purpose}\n"
            f"Email: {visitor_email}\n"
            f"Phone: {phone}\n")

    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, receiver_email, msg.as_string())
        logging.info("Email sent successfully.")
    except Exception as e:
        logging.error(f"Error sending email: {e}")

# Store Visitor Data
def store_visitor_data(visitor_data):
    try:
        c.execute("INSERT INTO visitors (name, email, phone, visitor_type, visit_purpose, time, language) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  visitor_data)
        conn.commit()
        logging.info("Visitor data stored successfully.")
    except Exception as e:
        logging.error(f"Error storing visitor data: {e}")

# Text-to-Speech
def speak(text, language="en"):
    translator = Translator()
    if language != "en":
        text = translator.translate(text, src="en", dest=language).text
    engine.setProperty('rate', 150)
    engine.say(text)
    engine.runAndWait()

# TensorFlow Object Detection
def detect_objects(frame):
    try:
        if model is None:
            return []

        # Convert image to RGB as TensorFlow models expect RGB input
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        input_tensor = tf.convert_to_tensor(image_rgb)
        input_tensor = input_tensor[tf.newaxis,...]

        # Run inference
        detections = model(input_tensor)

        # Extract detection data
        detection_boxes = detections['detection_boxes'][0].numpy()
        detection_classes = detections['detection_classes'][0].numpy().astype(np.int64)
        detection_scores = detections['detection_scores'][0].numpy()

        result = []
        height, width, _ = frame.shape

        for i in range(len(detection_scores)):
            if detection_scores[i] > 0.5:
                box = detection_boxes[i]
                ymin, xmin, ymax, xmax = box
                (x1, y1, x2, y2) = (int(xmin * width), int(ymin * height), int(xmax * width), int(ymax * height))

                label = str(detection_classes[i])  # You can map the class ID to class name here
                confidence = detection_scores[i]
                result.append((label, confidence, (x1, y1, x2, y2)))

        return result
    except Exception as e:
        logging.error(f"Error in detection: {e}")
        return []

# Video Streaming with Object Detection
def generate_frames():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logging.error("Error: Unable to access the camera.")
        return

    registration_open = False  # Flag to track if registration form is open

    while True:
        success, frame = cap.read()
        if not success:
            break

        detections = detect_objects(frame)
        for label, confidence, box in detections:
            x1, y1, x2, y2 = box
            if label == "1":  # Adjust this based on class ID for person (1 is for "person" in COCO dataset)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                text = f"Person: {confidence:.2f}"
                cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # Greet the person and show the registration form
                speak("Welcome to Mobius Family, please register", language="en")

                # Open registration form only if it's not already open
                if not registration_open:
                    registration_open = True
                    threading.Thread(target=open_registration_form_thread, daemon=True).start()

            else:  # Highlight other detected objects (e.g., robot)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                text = f"{label}: {confidence:.2f}"
                cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    cap.release()

# Open the Registration Form in Tkinter (Thread-safe)
def open_registration_form_thread():
    # Tkinter should run on the main thread
    app.after(0, open_registration_form)

def open_registration_form():
    try:
        # Create a simple Tkinter registration form window
        root = tk.Tk()
        root.title("Visitor Registration")

        # Example form components
        name_label = tk.Label(root, text="Name:")
        name_label.pack()
        name_entry = tk.Entry(root)
        name_entry.pack()

        email_label = tk.Label(root, text="Email:")
        email_label.pack()
        email_entry = tk.Entry(root)
        email_entry.pack()

        phone_label = tk.Label(root, text="Phone:")
        phone_label.pack()
        phone_entry = tk.Entry(root)
        phone_entry.pack()

        submit_button = tk.Button(root, text="Submit", command=lambda: submit_form(name_entry.get(), email_entry.get(), phone_entry.get()))
        submit_button.pack()

        def submit_form(name, email, phone):
            if not validate_email(email):
                speak("Invalid email. Please enter a valid email address.", language="en")
                return
            visitor_data = (name, email, phone, "Guest", "Business", datetime.now(), "English")  # Example data
            store_visitor_data(visitor_data)
            send_email("Guest", name, "Business", email, phone)
            speak(f"Registration complete for {name}. Thank you.", language="en")
            root.quit()

        root.mainloop()

    except Exception as e:
        logging.error(f"Error opening registration form: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False)
