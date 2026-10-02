import os
import smtplib
from email.mime.text import MIMEText

def send_email(subject, body):
    # Email configuration from environment variables
    sender_email = os.getenv("SMTP_USER")
    receiver_email = os.getenv("NOTIFY_EMAIL")
    password = os.getenv("SMTP_APP_PASSWORD")

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not sender_email or not password:
        print("Error: SMTP_USER and SMTP_APP_PASSWORD environment variables must be set.")
        return

    if not receiver_email:
        print("Warning: NOTIFY_EMAIL not set. Attempting to send without a specific receiver.")

    # Create the message
    message = MIMEText(body)
    message['Subject'] = subject
    message['From'] = sender_email
    if receiver_email:
        message['To'] = receiver_email

    server = None
    try:
        # Connect to the SMTP server and send the email
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(sender_email, password)
        server.send_message(message)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        if server:
            server.quit()

# Example usage
send_email('Subject of the Email', 'This is the body of the email.')