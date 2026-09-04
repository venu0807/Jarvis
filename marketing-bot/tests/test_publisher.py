import sys
import pytest
from unittest.mock import patch, MagicMock
from publisher import publish_to_n8n, N8N_WEBHOOK_URL

def test_publish_to_n8n_success():
    post_content = "This is a test post."
    payload = {"text": post_content}

    with patch("publisher.requests.post") as mock_post:
        # Configure the mock response
        mock_response = MagicMock()
        mock_post.return_value = mock_response

        # Call the function
        publish_to_n8n(post_content)

        # Verify the post request was made correctly
        mock_post.assert_called_once_with(N8N_WEBHOOK_URL, json=payload)
        # Verify raise_for_status was called
        mock_response.raise_for_status.assert_called_once()

def test_publish_to_n8n_failure_requests_exception():
    post_content = "This is a test post."

    with patch("publisher.requests.post") as mock_post, \
         patch("publisher.sys.exit") as mock_exit:

        # Simulate a request failure
        mock_post.side_effect = Exception("Connection error")

        # Call the function
        publish_to_n8n(post_content)

        # Verify sys.exit was called with 1
        mock_exit.assert_called_once_with(1)

def test_publish_to_n8n_failure_http_error():
    post_content = "This is a test post."

    with patch("publisher.requests.post") as mock_post, \
         patch("publisher.sys.exit") as mock_exit:

        # Simulate a failed response status (e.g., 500)
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_post.return_value = mock_response

        # Call the function
        publish_to_n8n(post_content)

        # Verify sys.exit was called with 1
        mock_exit.assert_called_once_with(1)
