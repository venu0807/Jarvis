import os
import pytest
from unittest.mock import MagicMock, mock_open
import smtplib

# Adjust python path if needed in the actual environment,
# assuming PYTHONPATH is set properly for pytest.
import mailer

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_USER", "testuser@example.com")
    monkeypatch.setenv("SMTP_APP_PASSWORD", "testpass")

def test_send_email_success_port_465(mock_env, mocker):
    """Test successful email sending over SSL (port 465)."""
    mock_smtp_ssl = mocker.patch("smtplib.SMTP_SSL")
    mock_server = MagicMock()
    mock_smtp_ssl.return_value.__enter__.return_value = mock_server

    result = mailer.send_email("recipient@example.com", "Test Subject", "Test Body")

    assert result is True
    mock_smtp_ssl.assert_called_once()
    mock_server.login.assert_called_once_with("testuser@example.com", "testpass")
    mock_server.send_message.assert_called_once()

def test_send_email_success_port_587(monkeypatch, mocker):
    """Test successful email sending over STARTTLS (port 587)."""
    monkeypatch.setenv("SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "testuser@example.com")
    monkeypatch.setenv("SMTP_APP_PASSWORD", "testpass")

    mock_smtp = mocker.patch("smtplib.SMTP")
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server

    result = mailer.send_email("recipient@example.com", "Test Subject", "Test Body")

    assert result is True
    mock_smtp.assert_called_once()
    assert mock_server.ehlo.call_count == 2
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("testuser@example.com", "testpass")
    mock_server.send_message.assert_called_once()

def test_send_email_with_valid_attachment(mock_env, mocker):
    """Test sending an email with a valid attachment."""
    mock_smtp_ssl = mocker.patch("smtplib.SMTP_SSL")
    mock_server = MagicMock()
    mock_smtp_ssl.return_value.__enter__.return_value = mock_server

    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("builtins.open", mock_open(read_data=b"dummy resume data"))

    # We'll just verify it doesn't crash and sends the message
    result = mailer.send_email("recipient@example.com", "Subject", "Body", "resume.pdf")

    assert result is True
    mock_server.send_message.assert_called_once()

    # Verify the message contains the attachment
    sent_msg = mock_server.send_message.call_args[0][0]
    assert sent_msg.is_multipart()
    parts = sent_msg.get_payload()
    assert len(parts) == 2  # Text body and attachment
    assert parts[1].get_content_disposition() == 'attachment'
    assert parts[1].get_filename() == 'resume.pdf'

def test_send_email_attachment_not_found(mock_env, mocker, capsys):
    """Test fallback to text-only if attachment path doesn't exist."""
    mock_smtp_ssl = mocker.patch("smtplib.SMTP_SSL")
    mock_server = MagicMock()
    mock_smtp_ssl.return_value.__enter__.return_value = mock_server

    mocker.patch("os.path.exists", return_value=False)

    result = mailer.send_email("recipient@example.com", "Subject", "Body", "missing.pdf")

    assert result is True
    captured = capsys.readouterr()
    assert "attachment file not found" in captured.out

    sent_msg = mock_server.send_message.call_args[0][0]
    parts = sent_msg.get_payload()
    assert len(parts) == 1  # Only the text body

def test_send_email_attachment_error(mock_env, mocker, capsys):
    """Test exception handling during attachment encoding."""
    mock_smtp_ssl = mocker.patch("smtplib.SMTP_SSL")
    mock_server = MagicMock()
    mock_smtp_ssl.return_value.__enter__.return_value = mock_server

    mocker.patch("os.path.exists", return_value=True)
    # Raising an error during file reading
    mocker.patch("builtins.open", side_effect=PermissionError("Access denied"))

    result = mailer.send_email("recipient@example.com", "Subject", "Body", "locked.pdf")

    assert result is True
    captured = capsys.readouterr()
    assert "could not attach resume" in captured.out

    sent_msg = mock_server.send_message.call_args[0][0]
    parts = sent_msg.get_payload()
    assert len(parts) == 1  # Only the text body

def test_send_email_auth_error(mock_env, mocker, capsys):
    """Test handling of SMTPAuthenticationError."""
    mock_smtp_ssl = mocker.patch("smtplib.SMTP_SSL")
    mock_server = MagicMock()
    mock_smtp_ssl.return_value.__enter__.return_value = mock_server

    mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")

    result = mailer.send_email("recipient@example.com", "Subject", "Body")

    assert result is False
    captured = capsys.readouterr()
    assert "SMTP auth failed" in captured.out

def test_send_email_general_smtp_error(mock_env, mocker, capsys):
    """Test handling of general SMTP errors."""
    mock_smtp_ssl = mocker.patch("smtplib.SMTP_SSL")
    mock_server = MagicMock()
    mock_smtp_ssl.return_value.__enter__.return_value = mock_server

    mock_server.send_message.side_effect = smtplib.SMTPException("Some network error")

    result = mailer.send_email("recipient@example.com", "Subject", "Body")

    assert result is False
    captured = capsys.readouterr()
    assert "SMTP error: Some network error" in captured.out

def test_send_email_missing_credentials(monkeypatch, capsys):
    """Test failure when SMTP credentials are not set."""
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_APP_PASSWORD", raising=False)

    result = mailer.send_email("recipient@example.com", "Subject", "Body")

    assert result is False
    captured = capsys.readouterr()
    assert "SMTP credentials not set" in captured.out
