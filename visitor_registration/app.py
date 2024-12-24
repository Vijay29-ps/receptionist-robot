from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('visitor_form.html')  # This file will be created next.

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    purpose = request.form['purpose']
    # Save visitor details
    with open('visitors.txt', 'a') as f:
        f.write(f"{name}, {purpose}\n")
    return f"Thank you, {name}! You are registered."

if __name__ == '__main__':
    app.run(debug=True)
