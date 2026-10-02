import pytest
from unittest.mock import patch, MagicMock
from automations.interview_scheduler_prep_bot.prep_generator import get_company_news

def test_get_company_news_happy_path():
    with patch('automations.interview_scheduler_prep_bot.prep_generator.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Google announces new AI - TechCrunch</title>
                    <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
                </item>
                <item>
                    <title>Google earnings report</title>
                    <pubDate>Tue, 02 Jan 2024 12:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """
        mock_get.return_value = mock_response

        result = get_company_news("Google Ltd")

        # Verify requests.get was called with the cleaned name
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        assert "q=Google+business+OR+tech" in call_url

        # Verify the parsing and formatting
        expected = "  - Google announces new AI (Mon, 01 Jan 2024 12:00:00 GMT)\n  - Google earnings report (Tue, 02 Jan 2024 12:00:00 GMT)"
        assert result == expected

def test_get_company_news_empty_items():
    with patch('automations.interview_scheduler_prep_bot.prep_generator.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel></channel></rss>"""
        mock_get.return_value = mock_response

        result = get_company_news("Apple")
        assert result == "  - No recent news found."

def test_get_company_news_non_200():
    with patch('automations.interview_scheduler_prep_bot.prep_generator.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = get_company_news("Microsoft")
        assert result == "  - No recent news found."

def test_get_company_news_exception():
    with patch('automations.interview_scheduler_prep_bot.prep_generator.requests.get', side_effect=Exception("Connection error")):
        result = get_company_news("Amazon")
        assert result == "  - No recent news found."

def test_get_company_news_name_cleaning():
    with patch('automations.interview_scheduler_prep_bot.prep_generator.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404 # Don't care about parsing here
        mock_get.return_value = mock_response

        get_company_news("Acme Corp Solutions Ltd Pvt")
        call_url = mock_get.call_args[0][0]
        assert "q=Acme+business+OR+tech" in call_url
