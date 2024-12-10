from flask import Flask, render_template, request, jsonify
import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from validate_email_address import validate_email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

app = Flask(__name__)

# Setup logging
logging.basicConfig(filename='email_sending.log', level=logging.INFO)

# Function to validate URL
def validate_url(url):
    try:
        response = requests.get(url)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

# Function to extract emails from a URL
def extract_emails(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    emails = set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', soup.get_text()))
    return emails

# Function to validate email format
def validate_email_format(email):
    return validate_email(email)

# Function to send email via Gmail SMTP
def send_email(recipient, subject, body, sender_email, sender_password):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient, msg.as_string())
        server.quit()
        logging.info(f"Email sent to {recipient}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email to {recipient}: {e}")
        return False

# Function to process URL file (CSV/Excel)
def process_url_file(file_path):
    # Load file into pandas dataframe (supports CSV, Excel)
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.endswith('.xlsx'):
        df = pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file format")
    
    # Extract URLs from the dataframe
    urls = df.iloc[:, 0].tolist()
    return urls

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Save the uploaded file
        file = request.files['file']
        if file:
            file_path = os.path.join("uploads", file.filename)
            file.save(file_path)
            
            # Process the uploaded file
            urls = process_url_file(file_path)
            
            # Email details
            sender_email = request.form['sender_email']
            sender_password = request.form['sender_password']
            subject = request.form['subject']
            body_template = request.form['body_template']
            
            # Send bulk emails
            for url in urls:
                if validate_url(url):
                    emails = extract_emails(url)
                    for email in emails:
                        if validate_email_format(email):
                            email_body = body_template.format(email=email)
                            send_email(email, subject, email_body, sender_email, sender_password)
            
            # Return a success response
            return jsonify({"status": "success", "message": "Emails have been sent successfully!"})

    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
