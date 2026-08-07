"""Pure-function tests for portals.base.is_experienced_role.

No browser, no network, no LLM — fast enough to run every time.
Covers the range-upper-bound bug (0-1 yrs) and the "work/professional
experience" phrasing gap.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from portals.base import is_experienced_role


def test_intern_and_fresher_titles():
    assert not is_experienced_role("Python Developer Intern", "Internship 6 months")
    assert not is_experienced_role("Junior Engineer", "Entry level")


def test_senior_and_lead_titles():
    assert is_experienced_role("Senior Software Engineer", "")
    assert is_experienced_role("Lead Developer", "")


def test_plus_range_is_experienced():
    assert is_experienced_role("Backend Dev", "Requires 5+ years of experience")
    assert is_experienced_role("DevOps", "2 to 4 years of experience required")


def test_fresher_range_not_experienced():
    # Regression: "0-1 years" must not match the "1 years" upper bound.
    assert not is_experienced_role("Python Developer", "Fresher friendly, 0-1 years experience")
    assert not is_experienced_role("QA", "fresher, 0 to 1 year of work experience")
    assert not is_experienced_role("Frontend Dev", "0-1 years of work experience preferred")


def test_work_and_professional_phrasing():
    # Regression: "X years of work/professional experience" must match.
    assert is_experienced_role("Data Engineer", "Bachelor degree, 1 year of work experience")
    assert is_experienced_role("SDE", "2 years of professional experience")


def test_no_experience_mention():
    assert not is_experienced_role("AI ML Engineer", "No experience required. Training provided.")
