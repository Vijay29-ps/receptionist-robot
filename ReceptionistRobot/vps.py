import cv2
from picamera2 import Picamera2

# Initialize the Raspberry Pi Camera
picam = Picamera2()
picam_config = picam.create_preview_configuration()
picam.configure(picam_config)
picam.start()

# Load Haarcascade for Face Detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

print("Press 'q' to exit the video stream.")

try:
    while True:
        # Capture frame-by-frame
        frame = picam.capture_array()

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        # Draw rectangles around faces
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

        # Display the resulting frame
        cv2.imshow('Face Recognition', frame)

        # Break the loop on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("Exiting program...")

# Release resources
picam.stop()
cv2.destroyAllWindows()
