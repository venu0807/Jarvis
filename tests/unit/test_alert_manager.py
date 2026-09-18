import os
import json
import unittest
from unittest.mock import patch, mock_open, MagicMock

import alert_manager

class TestAlertManager(unittest.TestCase):

    @patch('alert_manager.os.path.exists')
    @patch('urllib.request.urlopen')
    @patch('alert_manager.datetime')
    def test_add_alert_new_file(self, mock_datetime, mock_urlopen, mock_exists):
        # Setup
        mock_exists.return_value = False
        mock_datetime.datetime.now.return_value = "2023-10-27 12:00:00"
        m_open = mock_open()

        # Action
        with patch('builtins.open', m_open):
            alert_manager.add_alert("TestJob", "Test error message")

        # Assertions
        mock_exists.assert_called_once_with(alert_manager.ALERT_FILE)

        # Verify write
        m_open.assert_called_with(alert_manager.ALERT_FILE, 'w')
        handle = m_open()

        # Since json.dump writes in chunks, we need to get all written content
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        written_json = json.loads(written_content)

        self.assertEqual(len(written_json), 1)
        self.assertEqual(written_json[0]["job"], "TestJob")
        self.assertEqual(written_json[0]["message"], "Test error message")
        self.assertEqual(written_json[0]["time"], "2023-10-27 12:00:00")

        # Verify webhook
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "http://localhost:5678/webhook/jarvis-alerts")
        payload = json.loads(req.data.decode('utf-8'))
        self.assertEqual(payload["subject"], "Jarvis Alert: TestJob")
        self.assertEqual(payload["summary"], "Test error message")

    @patch('alert_manager.os.path.exists')
    @patch('urllib.request.urlopen')
    @patch('alert_manager.datetime')
    def test_add_alert_existing_file(self, mock_datetime, mock_urlopen, mock_exists):
        # Setup
        mock_exists.return_value = True
        mock_datetime.datetime.now.return_value = "2023-10-27 12:05:00"

        existing_alerts = [
            {"job": "OldJob", "time": "2023-10-27 11:00:00", "message": "Old error"}
        ]

        m_open = mock_open(read_data=json.dumps(existing_alerts))

        # Action
        with patch('builtins.open', m_open):
            alert_manager.add_alert("NewJob", "New error")

        # Verify read and write calls
        m_open.assert_any_call(alert_manager.ALERT_FILE, 'r')
        m_open.assert_any_call(alert_manager.ALERT_FILE, 'w')

        handle = m_open()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        written_json = json.loads(written_content)

        # Should have both alerts
        self.assertEqual(len(written_json), 2)
        self.assertEqual(written_json[0]["job"], "OldJob")
        self.assertEqual(written_json[1]["job"], "NewJob")
        self.assertEqual(written_json[1]["message"], "New error")

    @patch('alert_manager.os.path.exists')
    @patch('urllib.request.urlopen')
    @patch('alert_manager.datetime')
    def test_add_alert_invalid_json(self, mock_datetime, mock_urlopen, mock_exists):
        # Setup
        mock_exists.return_value = True
        mock_datetime.datetime.now.return_value = "2023-10-27 12:10:00"

        m_open = mock_open(read_data="invalid json {")

        # Action
        with patch('builtins.open', m_open):
            alert_manager.add_alert("ErrorJob", "Error msg")

        handle = m_open()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        written_json = json.loads(written_content)

        # Should start fresh and have just the new alert
        self.assertEqual(len(written_json), 1)
        self.assertEqual(written_json[0]["job"], "ErrorJob")

    @patch('alert_manager.os.path.exists')
    @patch('urllib.request.urlopen')
    def test_add_alert_webhook_failure(self, mock_urlopen, mock_exists):
        # Setup
        mock_exists.return_value = False
        mock_urlopen.side_effect = Exception("Webhook timeout")
        m_open = mock_open()

        # Action
        with patch('builtins.open', m_open):
            # Should not raise exception
            alert_manager.add_alert("FailJob", "Fail msg")

        # File should still be written
        handle = m_open()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        written_json = json.loads(written_content)

        self.assertEqual(len(written_json), 1)
        self.assertEqual(written_json[0]["job"], "FailJob")

if __name__ == '__main__':
    unittest.main()
