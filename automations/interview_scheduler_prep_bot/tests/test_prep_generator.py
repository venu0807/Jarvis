import pytest
import requests
from unittest.mock import patch, MagicMock
from automations.interview_scheduler_prep_bot.prep_generator import get_company_news

@patch("automations.interview_scheduler_prep_bot.prep_generator.requests.get")
def test_get_company_news_happy_path(mock_get):
    """Test successful fetching and parsing of company news."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Uncodemy Launches New Tech Course - Tech Crunch</title>
      <pubDate>Mon, 01 Jan 2026 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Uncodemy expansion plans revealed</title>
      <pubDate>Tue, 02 Jan 2026 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Short title - WSJ</title>
      <pubDate>Wed, 03 Jan 2026 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Another News Item - BBC</title>
      <pubDate>Thu, 04 Jan 2026 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Should not be included - Too many</title>
      <pubDate>Fri, 05 Jan 2026 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
'''
    mock_get.return_value = mock_response

    # Call function
    result = get_company_news("Uncodemy")

    # Assertions
    expected = (
        "  - Uncodemy Launches New Tech Course (Mon, 01 Jan 2026 12:00:00 GMT)\n"
        "  - Uncodemy expansion plans revealed (Tue, 02 Jan 2026 12:00:00 GMT)\n"
        "  - Short title (Wed, 03 Jan 2026 12:00:00 GMT)\n"
        "  - Another News Item (Thu, 04 Jan 2026 12:00:00 GMT)"
    )
    assert result == expected
    mock_get.assert_called_once_with("https://news.google.com/rss/search?q=Uncodemy+business+OR+tech", timeout=10)


@patch("automations.interview_scheduler_prep_bot.prep_generator.requests.get")
def test_get_company_news_name_cleaning(mock_get):
    """Test that company suffixes are removed for the search query."""
    mock_response = MagicMock()
    mock_response.status_code = 404 # Returning non-200 just to trigger early exit after fetch
    mock_get.return_value = mock_response

    get_company_news("Acme Pvt Ltd")
    mock_get.assert_called_once_with("https://news.google.com/rss/search?q=Acme+business+OR+tech", timeout=10)


@patch("automations.interview_scheduler_prep_bot.prep_generator.requests.get")
def test_get_company_news_non_200(mock_get):
    """Test behavior when the API returns a non-200 status code."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    result = get_company_news("Acme")
    assert result == "  - No recent news found."


@patch("automations.interview_scheduler_prep_bot.prep_generator.requests.get")
def test_get_company_news_exception(mock_get):
    """Test behavior when a network exception occurs."""
    mock_get.side_effect = requests.Timeout("Connection timed out")

    result = get_company_news("Acme")
    assert result == "  - No recent news found."


@patch("automations.interview_scheduler_prep_bot.prep_generator.requests.get")
def test_get_company_news_empty_xml(mock_get):
    """Test behavior when the RSS feed is empty."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
  </channel>
</rss>
'''
    mock_get.return_value = mock_response

    result = get_company_news("Acme")
    assert result == "  - No recent news found."
