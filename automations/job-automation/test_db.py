import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from db_logger import save_jobs_to_db
from portals.base import ApplicationResult

job = {
    "id": "test_job_001",
    "title": "Test AI Engineer",
    "company": "Jarvis Corp",
    "location": "Remote",
    "portal": "TestPortal",
    "url": "https://example.com/job",
    "description": "Test job",
    "scraped_at": "2026-08-07"
}

r = ApplicationResult(job=job, status="applied")
save_jobs_to_db([r])
print("Test complete.")
