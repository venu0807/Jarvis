import pytest
import email
from automations.interview_scheduler_prep_bot.email_listener import extract_email_text

def test_extract_email_text_simple_plain():
    raw_email = """Subject: Test Subject
From: sender@example.com
Date: This is a plain text email.
Content-Type: text/plain; charset="utf-8"

This is a plain text email."""
    msg = email.message_from_string(raw_email)
    subject, sender, body, html_body = extract_email_text(msg)

    assert subject == 'Test Subject'
    assert sender == 'sender@example.com'
    assert 'This is a plain text email.' in body

def test_extract_email_text_html():
    raw_email = """Subject: HTML Test
From: html@example.com
Content-Type: text/html; charset="utf-8"

<html><body><h1>Hello</h1><p>This is HTML.</p></body></html>"""
    msg = email.message_from_string(raw_email)
    subject, sender, body, html_body = extract_email_text(msg)

    assert subject == 'HTML Test'
    assert sender == 'html@example.com'
    assert 'This is HTML.' in html_body

def test_extract_email_text_multipart():
    raw_email = """Subject: Multipart Test
From: multi@example.com
Date: Plain text version.
Content-Type: multipart/alternative; boundary="boundary-string"

--boundary-string
Content-Type: text/plain; charset="utf-8"

Plain text version.
--boundary-string
Content-Type: text/html; charset="utf-8"

<html><body>HTML <b>version</b>.</body></html>
--boundary-string--"""
    msg = email.message_from_string(raw_email)
    subject, sender, body, html_body = extract_email_text(msg)

    assert subject == 'Multipart Test'
    assert sender == 'multi@example.com'
    assert 'Plain text version.' in body
    assert 'HTML' in html_body

def test_extract_email_text_encoded_subject():
    raw_email = """Subject: =?utf-8?b?SGVsbG8gV29ybGQ=?=
From: sender@example.com
Date: Body

Body"""
    msg = email.message_from_string(raw_email)
    subject, sender, body, html_body = extract_email_text(msg)

    assert subject == 'Hello World'
    assert sender == 'sender@example.com'
    assert 'Body' in body
