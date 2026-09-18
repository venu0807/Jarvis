import pytest
import socket
from unittest.mock import patch, MagicMock
import urllib.request
import urllib.error
from health_check import check_port, check_http

class TestCheckPort:
    @patch('socket.socket')
    def test_check_port_success(self, mock_socket):
        # Setup mock for successful connection
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect_ex.return_value = 0
        mock_socket.return_value = mock_sock_instance

        # Call function
        result = check_port("localhost", 8080)

        # Assertions
        assert result is True
        mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_sock_instance.settimeout.assert_called_once_with(5)
        mock_sock_instance.connect_ex.assert_called_once_with(("localhost", 8080))
        mock_sock_instance.close.assert_called_once()

    @patch('socket.socket')
    def test_check_port_failure(self, mock_socket):
        # Setup mock for failed connection (connect_ex returns error code e.g. 111)
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect_ex.return_value = 111
        mock_socket.return_value = mock_sock_instance

        # Call function
        result = check_port("localhost", 8080)

        # Assertions
        assert result is False
        mock_sock_instance.connect_ex.assert_called_once_with(("localhost", 8080))
        mock_sock_instance.close.assert_called_once()

    @patch('socket.socket')
    def test_check_port_exception(self, mock_socket):
        # Setup mock to raise exception
        mock_socket.side_effect = socket.error("Mock socket error")

        # Call function
        result = check_port("localhost", 8080)

        # Assertions
        assert result is False

class TestCheckHttp:
    @patch('urllib.request.urlopen')
    def test_check_http_success(self, mock_urlopen):
        # Setup mock for successful HTTP response
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value = mock_response

        # Call function
        result = check_http("http://localhost:8080")

        # Assertions
        assert result is True
        mock_urlopen.assert_called_once()
        args, kwargs = mock_urlopen.call_args
        assert isinstance(args[0], urllib.request.Request)
        assert args[0].full_url == "http://localhost:8080"
        assert kwargs['timeout'] == 5

    @patch('urllib.request.urlopen')
    def test_check_http_failure_status(self, mock_urlopen):
        # Setup mock for non-200 HTTP response
        mock_response = MagicMock()
        mock_response.getcode.return_value = 404
        mock_urlopen.return_value = mock_response

        # Call function
        result = check_http("http://localhost:8080")

        # Assertions
        assert result is False
        mock_urlopen.assert_called_once()

    @patch('urllib.request.urlopen')
    def test_check_http_exception(self, mock_urlopen):
        # Setup mock to raise exception
        mock_urlopen.side_effect = urllib.error.URLError("Mock URL error")

        # Call function
        result = check_http("http://localhost:8080")

        # Assertions
        assert result is False
        mock_urlopen.assert_called_once()
