import os
import smtplib
from email.mime.text import MIMEText

def send_email(subject, body):
    # Email configuration
    sender_email = "your_email@example.com"
    receiver_email = "user_email@example.com"
    password = os.environ.get("EMAIL_PASSWORD", "")

    # Create the message
    message = MIMEText(body)
    message['Subject'] = subject
    message['From'] = sender_email
    message['To'] = receiver_email

    try:
        # Connect to the SMTP server and send the email
        server = smtplib.SMTP('smtp.example.com', 587)
        server.starttls()
        server.login(sender_email, password)
        server.send_message(message)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        server.quit()

# Example usage
send_email('Subject of the Email', 'This is the body of the email.')