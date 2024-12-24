from flask import Flask, render_template, Response, request, redirect, url_for, flash
import cv2
import numpy as np
import os
import pyttsx3
import sqlite3
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Flask app initialization
app = Flask(__name__)
app.secret_key = "secret_key"

# Paths to YOLO model files (ensure these paths are correct)
MODEL_CFG = "/home/vps/ReceptionistRobot/yolov3.cfg"
MODEL_WEIGHTS = "/home/vps/ReceptionistRobot/yolov3.weights"
COCO_NAMES = "/home/vps/ReceptionistRobot/coco.names"

# Ensure YOLO files exist
REQUIRED_FILES = [MODEL_CFG, MODEL_WEIGHTS, COCO_NAMES]
for file_path in REQUIRED_FILES:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Missing YOLO file: {file_path}. Please check the paths.")

# Load YOLO class names
with open(COCO_NAMES, "r") as f:
    class_names = f.read().strip().split("\n")

# Initialize YOLO network
net = cv2.dnn.readNetFromDarknet(MODEL_CFG, MODEL_WEIGHTS)
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

# Camera index
USB_CAMERA_INDEX = 0

# YOLO input size
INPUT_WIDTH = 416
INPUT_HEIGHT = 416

# Text-to-Speech Engine
engine = pyttsx3.init()

# Visitor database setup
DATABASE_PATH = "visitors.db"
conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS visitors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        phone TEXT,
        purpose TEXT,
        timestamp TIMESTAMP
    )
''')
conn.commit()

def speak(text):
    """Convert text to speech with interruption handling."""
    engine.stop()  # Stop any ongoing speech
    engine.say(text)
    engine.runAndWait()

def detect_objects(frame):
    """Detect objects in a frame using YOLO."""
    height, width = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (INPUT_WIDTH, INPUT_HEIGHT), swapRB=True, crop=False)
    net.setInput(blob)

    # Get output layer names
    layer_names = net.getLayerNames()
    output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers().flatten()]

    # YOLO forward pass
    detections = net.forward(output_layers)
    boxes, confidences, class_ids = [], [], []

    for output in detections:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.5:  # Confidence threshold
                center_x, center_y, w, h = (detection[:4] * np.array([width, height, width, height])).astype("int")
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                boxes.append([x, y, int(w), int(h)])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
    results = []
    if len(indices) > 0:
        for i in indices.flatten():
            x, y, w, h = boxes[i]
            label = class_names[class_ids[i]]
            results.append((label, confidences[i], (x, y, x + w, y + h)))

    return results

def generate_frames():
    """Generate video frames from the camera."""
    cap = cv2.VideoCapture(USB_CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError("Unable to access the camera. Check its connection and permissions.")

    try:
        while True:
            success, frame = cap.read()
            if not success:
                break

            detections = detect_objects(frame)

            # Draw bounding boxes and labels
            for label, confidence, box in detections:
                x1, y1, x2, y2 = box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                text = f"{label}: {confidence:.2f}"
                cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    finally:
        cap.release()

# Email sending function
SMTP_SERVER = 'smtp.gmail.com'  # Example for Gmail
SMTP_PORT = 587
SENDER_EMAIL = 'psvijay618@gmail.com'  # Your email
SENDER_PASSWORD = 'cqec rtoj xjui kqsl'  # Your email password
RECIPIENT_EMAIL = 'vijayps2905@gmail.com'  # Default recipient email, can be modified dynamically

def send_email(subject, body, recipient_email):
    """Send an email notification."""
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Secure the connection
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, recipient_email, text)
        server.quit()
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

@app.route('/')
def index():
    """Render the main page."""
    speak("Welcome to Mobius Family. Please register to proceed.")
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Provide live video feed."""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/register', methods=['POST'])
def register():
    """Handle visitor registration."""
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    purpose = request.form.get('purpose')

    if not all([name, email, phone, purpose]):
        flash("All fields are required.", "danger")
        return redirect(url_for('index'))

    timestamp = datetime.now()
    c.execute("INSERT INTO visitors (name, email, phone, purpose, timestamp) VALUES (?, ?, ?, ?, ?)",
              (name, email, phone, purpose, timestamp))
    conn.commit()

    # Send registration confirmation email to the visitor
    subject = "Visitor Registration Confirmation"
    body = f"Hello {name},\n\nThank you for registering with us. We look forward to your visit.\n\nPurpose of Visit: {purpose}\n\nRegards,\nMobius Family"
    send_email(subject, body, email)

    # Send notification email to the concerned person based on the purpose of visit
    if purpose.lower() == "interview":
        recipient_email = "ps.vijay@mobiusdtaas.ai"  # HR email for interview purposes
    elif purpose.lower() == "delivery":
        recipient_email = "jayps2905@gmail.com"  # Purchase Manager email for delivery purposes
    else:
        recipient_email = "Astra@gmail.com"  # Astra's email for other purposes

    subject = "New Visitor Registration"
    body = f"A new visitor has registered:\n\nName: {name}\nEmail: {email}\nPhone: {phone}\nPurpose: {purpose}\nTime: {timestamp}"
    send_email(subject, body, recipient_email)

    speak(f"Thank you, {name}. Your registration is complete.")
    flash("Registration successful!", "success")
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
