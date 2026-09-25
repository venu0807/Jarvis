import unittest
from unittest.mock import patch, MagicMock
import requests
import sys

from llm_summarizer import generate_linkedin_post

class TestLLMSummarizer(unittest.TestCase):
    def setUp(self):
        self.sample_stories = [
            {"title": "Story 1", "url": "http://story1.com"},
            {"title": "Story 2", "url": "http://story2.com"}
        ]

    @patch('llm_summarizer.requests.post')
    def test_generate_linkedin_post_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {'response': 'Drafted post!'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = generate_linkedin_post(self.sample_stories)

        self.assertEqual(result, 'Drafted post!')
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://localhost:11434/api/generate")
        self.assertIn("Story 1 - http://story1.com", kwargs['json']['prompt'])
        self.assertIn("Story 2 - http://story2.com", kwargs['json']['prompt'])

    @patch('llm_summarizer.sys.exit')
    @patch('llm_summarizer.requests.post')
    def test_generate_linkedin_post_api_error(self, mock_post, mock_exit):
        mock_post.side_effect = requests.exceptions.RequestException("API down")

        generate_linkedin_post(self.sample_stories)

        mock_exit.assert_called_once_with(1)
