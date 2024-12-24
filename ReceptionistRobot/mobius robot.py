from flask import Flask, render_template, request, redirect, url_for, flash
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key

@app.route('/')
def index():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    email = request.form['email']
    try:
        send_email(email)
        flash('Registration successful! A confirmation email has been sent.', 'success')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
    return redirect(url_for('index'))

def send_email(email):
    msg = MIMEText('Thank you for registering!')
    msg['Subject'] = 'Registration Confirmation'
    msg['From'] = 'your_email@example.com'
    msg['To'] = email

    with smtplib.SMTP('smtp.example.com', 587) as server:  # Replace with actual SMTP server
        server.starttls()
        server.login('psvijay618@gmail.com', 'qjkb zjwy flkr ryml')  # Use environment variables for security
        server.send_message(msg)

if __name__ == '__main__':
    app.run(debug=True)