import pytest
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import extractor
sys.path.insert(0, str(Path(__file__).parent.parent))
from extractor import extract_email_from_text

def test_extract_email_from_text_empty():
    assert extract_email_from_text(None) is None
    assert extract_email_from_text("") is None

def test_extract_email_from_text_valid():
    text = "Reach out to me at john.doe@example.com for more info."
    assert extract_email_from_text(text) == "john.doe@example.com"

def test_extract_email_from_text_trailing_punctuation():
    # Test stripping punctuation like ),.>;:'"!
    assert extract_email_from_text("Email: jane@gmail.com.") == "jane@gmail.com"
    assert extract_email_from_text("Contact me (jane@gmail.com)") == "jane@gmail.com"
    assert extract_email_from_text("jane@gmail.com;") == "jane@gmail.com"
    assert extract_email_from_text("jane@gmail.com!") == "jane@gmail.com"
    assert extract_email_from_text("jane@gmail.com?>") == "jane@gmail.com"
    assert extract_email_from_text("Contact 'jane@gmail.com'") == "jane@gmail.com"

def test_extract_email_from_text_invalid_garbage():
    # Consecutive dots before @
    assert extract_email_from_text("My email is john..doe@gmail.com") is None

    # Missing TLD (regex should fail or custom check will discard)
    assert extract_email_from_text("Contact me at john@localhost") is None

    # Just generic non-emails
    assert extract_email_from_text("Hello there! Contact me on my website.") is None

def test_extract_email_from_text_multiple_emails():
    text = "First try bob..invalid@gmail.com, then try valid@example.com and maybe another@example.com."
    # Should skip the invalid one and return the first valid one
    assert extract_email_from_text(text) == "valid@example.com"

def test_extract_email_from_text_with_spaces_and_newlines():
    text = """
    Hey!
    You can reach out to:
    test_user123@domain.co.uk
    Thanks!
    """
    assert extract_email_from_text(text) == "test_user123@domain.co.uk"
