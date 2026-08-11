"""Naukri chatbot resolver regression tests.

The old resolver fell through to a canned "Yes" for ANY unhandled question —
the manual run log showed "What is your full name?" -> A: 'Yes' and
"What is your email address?" -> A: 'Yes', i.e. invalid applications being
submitted with the word "Yes" in identity fields. The resolver must (a) answer
identity/contact questions from the profile and (b) return None for questions
it can't confidently answer so the caller marks the job manual instead.
"""
from portals.naukri import NaukriPortal
from portals.base import NAME, EMAIL, PHONE_DIGITS, FIRST_NAME, LAST_NAME


def make() -> NaukriPortal:
    return NaukriPortal(email="test@example.com", password="x")


def test_name_question_uses_profile_not_yes():
    assert make()._resolve_chatbot_answer("What is your full name?") == NAME
    assert make()._resolve_chatbot_answer("Enter your name") == NAME


def test_name_split_questions():
    p = make()
    assert p._resolve_chatbot_answer("What is your first name?") == FIRST_NAME
    assert p._resolve_chatbot_answer("What is your last name?") == LAST_NAME


def test_email_and_phone():
    p = make()
    assert p._resolve_chatbot_answer("What is your email address?") == EMAIL
    assert p._resolve_chatbot_answer("What is your contact number?") == PHONE_DIGITS


def test_unknown_free_text_returns_none():
    # These must NOT get a canned answer — the caller marks the job manual.
    p = make()
    assert p._resolve_chatbot_answer("Describe a project you have worked on") is None
    assert p._resolve_chatbot_answer("Why do you want to work at this company?") is None
    assert p._resolve_chatbot_answer("") is None
    assert p._resolve_chatbot_answer(None) is None


def test_experience_count_vs_yes_no():
    p = make()
    assert p._resolve_chatbot_answer("How many years of experience you have in AI coding?") == "0"
    # yes/no skill question mentions a resume skill -> Yes
    assert p._resolve_chatbot_answer("Do you have experience with Python?") == "Yes"


def test_count_question_with_skill_name_is_not_yes():
    # "How many years … in Data Structures?" names a resume skill, but it
    # asks for a COUNT, not yes/no. Must answer "0", not "Yes".
    p = make()
    assert p._resolve_chatbot_answer(
        "How many years of experience do you have in Data Structures?") == "0"
    assert p._resolve_chatbot_answer(
        "How many years of experience do you have in Algorithms?") == "0"


def test_fresher_basics_still_work():
    p = make()
    assert p._resolve_chatbot_answer("How many years of experience you have?") == "0"
    assert p._resolve_chatbot_answer("What is your current salary?") == "0"
    assert p._resolve_chatbot_answer("What is your expected salary?") == "600000"
    assert p._resolve_chatbot_answer("What is your notice period?") in ("Immediate", "15 days")
    assert p._resolve_chatbot_answer("What is your highest qualification?") == "MCA"