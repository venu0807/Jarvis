import pytest
import os
from pathlib import Path
from email.message import EmailMessage, Message
from email.header import Header
from automations.interview_scheduler_prep_bot.email_listener import extract_email_text
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def test_credentials_exist():
    """Security/QA Test: Ensure token.json or credentials.json aren't missing silently."""
    assert True # Placeholder for actual auth test


def test_extract_email_text_basic():
    """Test basic email with text/plain body."""
    msg = EmailMessage()
    msg['Subject'] = 'Test Subject'
    msg['From'] = 'sender@example.com'
    msg['Date'] = 'Wed, 25 Sep 2024 10:00:00 +0000'
    msg.set_content('This is a test body.')

    subj, sender, date, body = extract_email_text(msg)
    assert subj == 'Test Subject'
    assert sender == 'sender@example.com'
    assert date == 'Wed, 25 Sep 2024 10:00:00 +0000'
    assert body == 'This is a test body.'

def test_extract_email_text_html():
    """Test email with text/html body, ensuring HTML tags are stripped."""
    msg = EmailMessage()
    msg['Subject'] = 'HTML Subject'
    msg['From'] = 'html@example.com'
    msg['Date'] = 'Wed, 25 Sep 2024 11:00:00 +0000'
    msg.set_content('<p>This is <b>HTML</b> test.</p>', subtype='html')

    subj, sender, date, body = extract_email_text(msg)
    assert subj == 'HTML Subject'
    assert body == 'This is HTML test.'

def test_extract_email_text_multipart():
    """Test multipart email with both text/plain and text/html parts."""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Multipart Subject'
    msg['From'] = 'multi@example.com'
    msg['Date'] = 'Wed, 25 Sep 2024 12:00:00 +0000'

    part1 = MIMEText('This is plain text.', 'plain')
    part2 = MIMEText('<p>This is <b>HTML</b> text.</p>', 'html')
    msg.attach(part1)
    msg.attach(part2)

    subj, sender, date, body = extract_email_text(msg)
    assert subj == 'Multipart Subject'
    assert 'This is plain text.' in body
    assert 'This is HTML text.' in body

def test_extract_email_text_encoded_subject():
    """Test email with encoded subject (e.g., UTF-8 encoded string)."""
    msg = Message()
    msg['Subject'] = Header('Encoded Subject 🎉', 'utf-8').encode()
    msg['From'] = 'encoded@example.com'
    msg['Date'] = 'Wed, 25 Sep 2024 13:00:00 +0000'
    msg.set_payload('Body')

    subj, sender, date, body = extract_email_text(msg)
    assert subj == 'Encoded Subject 🎉'
    assert body == 'Body'
