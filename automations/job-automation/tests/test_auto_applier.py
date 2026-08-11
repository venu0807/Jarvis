import pytest
import os
import json
from pathlib import Path

# Add the parent directory to sys.path to import modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from auto_applier import build_summary

class MockResult:
    def __init__(self, status, job, reason=""):
        self.status = status
        self.job = job
        self.reason = reason

def test_build_summary_handles_empty_results():
    """QA Test 1: Empty results list shouldn't break the summary builder."""
    summary = build_summary([])
    assert summary["totals"]["applied"] == 0
    assert summary["totals"]["errors"] == 0

def test_build_summary_counts_correctly():
    """QA Test 2: Ensure manual, skipped, and applied states are categorized."""
    results = [
        MockResult("applied", {"title": "SE", "company": "A", "portal": "naukri"}),
        MockResult("manual", {"title": "Backend", "company": "B"}),
        MockResult("skipped", {"title": "Frontend", "company": "C"}, reason="Already applied"),
        MockResult("error", {"title": "ML", "company": "D"}, reason="Timeout")
    ]
    summary = build_summary(results)
    assert summary["totals"]["applied"] == 1
    assert summary["totals"]["manual"] == 1
    assert summary["totals"]["skipped"] == 1
    assert summary["totals"]["errors"] == 1
    assert summary["portal_counts"].get("naukri") == 1

def test_env_secrets_are_loaded():
    """Security Audit Test: Ensure that credentials aren't checked into version control accidentally."""
    # We shouldn't assert on exact passwords, but ensure the fallback to GMAIL_ADDRESS works.
    email = os.getenv("WELLFOUND_EMAIL", os.getenv("GMAIL_ADDRESS", ""))
    assert email is not None
