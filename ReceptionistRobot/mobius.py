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

# Initialize SQLite database
conn = sqlite3.connect('visitors.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS visitors
             (name TEXT, email TEXT, phone TEXT, visitor_type TEXT, visit_purpose TEXT, time TIMESTAMP, language TEXT)''')
conn.commit()

# Initialize Text-to-Speech engine
engine = pyttsx3.init()

# Function to validate email
def validate_email(email):
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(regex, email))

# Function to send email notifications
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

# Function to store visitor data
def store_visitor_data(visitor_data):
    try:
        c.execute("INSERT INTO visitors (name, email, phone, visitor_type, visit_purpose, time, language) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  visitor_data)
        conn.commit()
        print("Visitor data stored successfully.")
    except Exception as e:
        print(f"Error storing visitor data: {e}")

# Function for text-to-speech
def speak(text, language="en"):
    translator = Translator()
    if language != "en":
        text = translator.translate(text, src="en", dest=language).text
    engine.setProperty('rate', 150)
    engine.say(text)
    engine.runAndWait()

# Enhanced voice-based registration with fallback
def voice_registration(language):
    def ask_detail(prompt):
        recognizer = sr.Recognizer()
        attempts = 3
        for _ in range(attempts):
            speak(prompt, language)
            with sr.Microphone() as source:
                print(f"Listening for {prompt}...")
                try:
                    audio = recognizer.listen(source, timeout=5)
                    text = recognizer.recognize_google(audio, language=language)
                    print(f"Understood: {text}")
                    return text
                except sr.UnknownValueError:
                    speak("Sorry, I couldn't understand. Please repeat.", language)
                except sr.RequestError:
                    speak("Sorry, there seems to be a connection issue.", language)
        return None

    # Collecting details
    name = ask_detail("What is your name?")
    email = ask_detail("What is your email address?")
    phone = ask_detail("What is your phone number?")
    purpose = ask_detail("What is the purpose of your visit?")
    visitor_type = ask_detail("Are you a guest, delivery person, or interview candidate?")

    # If any field is None, switch to manual registration
    if not all([name, email, phone, purpose, visitor_type]) or not validate_email(email):
        messagebox.showinfo("Manual Registration", "Voice registration failed. Switching to manual registration.")
        manual_registration(language)
        return

    visitor_data = (name, email, phone, visitor_type, purpose, datetime.now(), language)
    store_visitor_data(visitor_data)
    send_email(visitor_type, name, purpose, email, phone)
    speak("Thank you! Your registration is complete.", language)
    messagebox.showinfo("Success", "Visitor registered successfully.")

# Manual registration GUI
def manual_registration(language):
    def submit_manual_form():
        name = name_entry.get()
        email = email_entry.get()
        phone = phone_entry.get()
        visitor_type = visitor_type_combobox.get()
        purpose = purpose_entry.get()

        if not validate_email(email):
            messagebox.showerror("Error", "Invalid email address.")
            return

        visitor_data = (name, email, phone, visitor_type, purpose, datetime.now(), language)
        store_visitor_data(visitor_data)
        send_email(visitor_type, name, purpose, email, phone)
        speak("Thank you! Your registration is complete.", language)
        messagebox.showinfo("Success", "Visitor registered successfully.")
        manual_window.destroy()

    manual_window = tk.Toplevel()
    manual_window.title("Manual Registration")
    manual_window.geometry("400x400")

    tk.Label(manual_window, text="Name:").pack(pady=5)
    name_entry = tk.Entry(manual_window)
    name_entry.pack(pady=5)

    tk.Label(manual_window, text="Email:").pack(pady=5)
    email_entry = tk.Entry(manual_window)
    email_entry.pack(pady=5)

    tk.Label(manual_window, text="Phone:").pack(pady=5)
    phone_entry = tk.Entry(manual_window)
    phone_entry.pack(pady=5)

    tk.Label(manual_window, text="Visitor Type:").pack(pady=5)
    visitor_type_combobox = ttk.Combobox(manual_window, values=["Guest", "Delivery", "Interview Candidate"])
    visitor_type_combobox.pack(pady=5)

    tk.Label(manual_window, text="Purpose of Visit:").pack(pady=5)
    purpose_entry = tk.Entry(manual_window)
    purpose_entry.pack(pady=5)

    tk.Button(manual_window, text="Submit", command=submit_manual_form).pack(pady=20)

# Main GUI
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

    tk.Button(root, text="Visitor Registration", command=lambda: voice_registration(language_var.get()), bg="#4caf50", fg="white").pack(pady=10)
    tk.Button(root, text="Exit", command=root.quit, bg="#f44336", fg="white").pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main_gui()
