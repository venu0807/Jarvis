import sys
import pytest
import requests
from unittest.mock import patch, MagicMock
from publisher import publish_to_n8n, N8N_WEBHOOK_URL

def test_publish_to_n8n_success(capsys):
    post_content = "Hello, world! This is a test post."

    with patch('requests.post') as mock_post:
        # Configure the mock to return a successful response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Call the function
        publish_to_n8n(post_content)

        # Assertions
        mock_post.assert_called_once_with(N8N_WEBHOOK_URL, json={"text": post_content})
        mock_response.raise_for_status.assert_called_once()

        # Check standard output
        captured = capsys.readouterr()
        assert "Successfully triggered n8n workflow!" in captured.out

def test_publish_to_n8n_request_exception(capsys):
    post_content = "Hello, world! This is a test post."

    with patch('requests.post') as mock_post:
        # Configure the mock to raise a RequestException
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")

        try:
            publish_to_n8n(post_content)
        except SystemExit as e:
            pass # Accept SystemExit if present in current codebase

        # Assertions
        mock_post.assert_called_once_with(N8N_WEBHOOK_URL, json={"text": post_content})

        # Capture stdout to check the print statement
        captured = capsys.readouterr()
        assert "Failed to send to n8n: Connection error" in captured.out

def test_publish_to_n8n_http_error(capsys):
    post_content = "Hello, world! This is a test post."

    with patch('requests.post') as mock_post:
        # Configure the mock to return a failed response
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_post.return_value = mock_response

        try:
            publish_to_n8n(post_content)
        except SystemExit as e:
            pass # Accept SystemExit if present in current codebase

        # Assertions
        mock_post.assert_called_once_with(N8N_WEBHOOK_URL, json={"text": post_content})
        mock_response.raise_for_status.assert_called_once()

        # Capture stdout to check the print statement
        captured = capsys.readouterr()
        assert "Failed to send to n8n: 404 Not Found" in captured.out
