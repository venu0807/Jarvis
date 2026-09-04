import pytest
from unittest.mock import patch
from automations.interview_scheduler_prep_bot.email_listener import parse_interview_with_llm

def test_parse_interview_with_llm_exception():
    """Test that parse_interview_with_llm returns {'is_interview': False} on Exception."""
    with patch('automations.interview_scheduler_prep_bot.email_listener.call_llm', side_effect=Exception("Test Exception")):
        result = parse_interview_with_llm(subject="Subject", sender="Sender", body="Body")
        assert result == {"is_interview": False}
