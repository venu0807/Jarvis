import pytest
import sqlite3
import tempfile
from pathlib import Path

from automations.interview_scheduler_prep_bot.prep_generator import fetch_job_description

@pytest.fixture
def temp_db(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "jobs.db"

        # Create dummy database
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE jobs (id INTEGER PRIMARY KEY, title TEXT, description TEXT, company TEXT)")
            # Standard exact match
            conn.execute("INSERT INTO jobs (title, description, company) VALUES ('Software Engineer', 'Standard SWE role', 'Acme')")
            # Word match
            conn.execute("INSERT INTO jobs (title, description, company) VALUES ('QA Engineer', 'Testing role', 'GlobalTech')")
            # Edge cases for company names
            conn.execute("INSERT INTO jobs (title, description, company) VALUES ('Data Scientist', 'Data role', 'TechCorp')")
            conn.execute("INSERT INTO jobs (title, description, company) VALUES ('DevOps Engineer', 'DevOps role', 'Edutech Solutions')")
            conn.commit()

        # Mock DB_PATH in prep_generator
        monkeypatch.setattr("automations.interview_scheduler_prep_bot.prep_generator.DB_PATH", db_path)
        yield db_path

def test_fetch_job_description_no_db(monkeypatch):
    # If DB does not exist
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_db = Path(tmpdir) / "nonexistent.db"
        monkeypatch.setattr("automations.interview_scheduler_prep_bot.prep_generator.DB_PATH", fake_db)

        title, desc = fetch_job_description("Acme")
        assert title == "Software Developer / Tester"
        assert desc == ""

def test_fetch_job_description_exact_match(temp_db):
    title, desc = fetch_job_description("Acme")
    assert title == "Software Engineer"
    assert desc == "Standard SWE role"

def test_fetch_job_description_fuzzy_match_company_suffix(temp_db):
    # Should strip "Inc", "Corp", "Ltd", etc. and match "TechCorp"
    title, desc = fetch_job_description("TechCorp Inc")
    assert title == "Data Scientist"
    assert desc == "Data role"

    title, desc = fetch_job_description("TechCorp Ltd.")
    assert title == "Data Scientist"
    assert desc == "Data role"

def test_fetch_job_description_fuzzy_match_multiple_words(temp_db):
    # Company in DB: "Edutech Solutions"
    # Both words are in the stripped list. The fallback logic will match '%Edutech Solutions%'
    title, desc = fetch_job_description("Edutech Solutions Pvt Ltd")
    assert title == "DevOps Engineer"
    assert desc == "DevOps role"

def test_fetch_job_description_not_found(temp_db):
    title, desc = fetch_job_description("NonexistentCompany")
    assert title == "Software Tester / QA & Python Developer"
    assert desc == ""
