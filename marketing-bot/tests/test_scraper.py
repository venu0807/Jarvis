import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scraper import get_top_stories

@patch('scraper.requests.get')
def test_get_top_stories_success(mock_get):
    # Mock responses for the requests
    # First request gets top stories
    mock_top_stories = MagicMock()
    mock_top_stories.status_code = 200
    mock_top_stories.json.return_value = [1, 2, 3]

    # Subsequent requests get individual stories
    mock_story_1 = MagicMock()
    mock_story_1.status_code = 200
    mock_story_1.json.return_value = {'title': 'Story 1', 'url': 'http://example.com/1', 'score': 100}

    mock_story_2 = MagicMock()
    mock_story_2.status_code = 200
    mock_story_2.json.return_value = {'title': 'Story 2', 'score': 200} # missing url

    mock_get.side_effect = [mock_top_stories, mock_story_1, mock_story_2]

    # Act
    stories = get_top_stories(limit=2)

    # Assert
    assert len(stories) == 2
    assert stories[0]['title'] == 'Story 1'
    assert stories[0]['url'] == 'http://example.com/1'
    assert stories[0]['score'] == 100

    assert stories[1]['title'] == 'Story 2'
    assert stories[1]['url'] == 'https://news.ycombinator.com/item?id=2'
    assert stories[1]['score'] == 200

@patch('scraper.requests.get')
def test_get_top_stories_fetch_error(mock_get):
    mock_top_stories = MagicMock()
    mock_top_stories.status_code = 500
    mock_get.return_value = mock_top_stories

    with pytest.raises(SystemExit) as excinfo:
        get_top_stories()

    assert excinfo.value.code == 1

@patch('scraper.requests.get')
def test_get_top_stories_individual_story_error(mock_get):
    mock_top_stories = MagicMock()
    mock_top_stories.status_code = 200
    mock_top_stories.json.return_value = [1, 2]

    mock_story_1 = MagicMock()
    mock_story_1.status_code = 500 # this one fails

    mock_story_2 = MagicMock()
    mock_story_2.status_code = 200
    mock_story_2.json.return_value = {'title': 'Story 2', 'url': 'http://example.com/2', 'score': 200}

    mock_get.side_effect = [mock_top_stories, mock_story_1, mock_story_2]

    stories = get_top_stories(limit=2)

    # only one story should be returned because the first one failed
    assert len(stories) == 1
    assert stories[0]['title'] == 'Story 2'
