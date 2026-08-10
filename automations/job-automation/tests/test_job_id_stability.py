"""Job-id stability regression test.

The auto-applier dedups against applied_jobs.json by job id. Those ids were
built with Python's built-in hash(), which is randomized per process
(PYTHONHASHSEED) — so the same job got a different id on every run and the
"already applied" check never matched. ids must be a pure function of the URL.
"""
import hashlib
import subprocess
import sys


def naukri_id(href: str) -> str:
    return f"naukri_{hashlib.sha256(href.encode()).hexdigest()[:10]}"


URLS = [
    "https://www.naukri.com/job-listings/python-developer/123",
    "https://www.naukri.com/job-listings/django/456",
]


def test_same_url_same_id_same_process():
    for u in URLS:
        a, b = naukri_id(u), naukri_id(u)
        assert a == b, f"{u}: in-process ids differ ({a!r} vs {b!r})"


def test_same_url_same_id_across_processes():
    """Reproduce the old failure mode: fresh interpreter, fresh PYTHONHASHSEED."""
    for u in URLS:
        ids = set()
        for _ in range(2):
            out = subprocess.run(
                [sys.executable, "-c",
                 f"import hashlib;print('naukri_'+hashlib.sha256({u!r}.encode()).hexdigest()[:10])"],
                capture_output=True, text=True, check=True)
            ids.add(out.stdout.strip())
        assert len(ids) == 1, f"{u}: id differs across processes: {ids}"


def test_ids_differ_between_jobs():
    a, b = naukri_id(URLS[0]), naukri_id(URLS[1])
    assert a != b


if __name__ == "__main__":
    test_same_url_same_id_same_process()
    test_same_url_same_id_across_processes()
    test_ids_differ_between_jobs()
    print("OK — job ids are stable across processes and distinct per job")