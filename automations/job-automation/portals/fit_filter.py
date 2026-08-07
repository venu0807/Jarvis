"""portals/fit_filter.py — optional LLM job-fit filter.

Rule-based `is_experienced_role` (base.py) already gates every portal. This is
the deeper LLM filter: rejects jobs that are experienced-only, use a different
primary language, or are non-technical. It never actually ran before — the
old `evaluate_job_fit` only lived on the dead scraped-jobs path. Now it's a
reusable async hook portals call just before applying.

Safe by construction:
- Cached per job id (one LLM call per job per run).
- Runs in a thread so the event loop never blocks.
- Falls back to True (apply) if the LLM is unavailable or errors — a broken
  filter must never block applications.
"""
import asyncio
from typing import Optional

_cache: dict = {}

PROMPT = """Evaluate this job for a Full Stack AI Engineer / Python Developer.
Criteria for REJECTION (Reply NO if any match):
- Requires strictly 2+ years of professional industry experience (Candidate only has 0-1 years of experience / fresh graduate).
- Requires C#, Ruby, PHP, or Go as the primary language (Candidate uses Python, Java, React).
- Is a non-technical role (e.g., Sales, HR, Marketing, Customer Support).

Reply with EXACTLY ONE WORD: "YES" if it's a good fit, or "NO" if it's a bad fit.

Job Title: {title}
Job Description: {desc}"""


async def evaluate_job_fit(job: dict) -> bool:
    """Return True if the job is a good fit (apply). Never raises.
    Judges on title even when portals scrape no description."""
    jid = job.get("id") or job.get("url", "")
    if jid in _cache:
        return _cache[jid]

    title = job.get("title", "")
    desc = job.get("description", "")
    if not (title or desc):
        _cache[jid] = True
        return True

    try:
        from policy import call_llm
    except ImportError:
        _cache[jid] = True
        return True

    try:
        # Cap the LLM round-trip so a hung/Ollama-down doesn't freeze the
        # apply loop. asyncio.to_thread threads can't be cancelled, but
        # wait_for unblocks the coroutine and we fall back to apply (True).
        res = await asyncio.wait_for(
            asyncio.to_thread(
                call_llm,
                PROMPT.format(title=(title or "")[:200], desc=(desc or "(none provided)")[:2000]),
                mode="run", force="local", pii_acknowledged=True, task_label="job_filter",
            ),
            timeout=15,
        )
        reply = res.text.strip().upper()
        fit = "NO" not in reply[:10]
    except Exception:
        fit = True
    _cache[jid] = fit
    return fit


def make_filter(enabled: bool = True):
    """Return an async filter callable, or None when disabled.

    Portals call `if job_filter and not await job_filter(job): skip`.
    Disabled (or LLM missing) → None → no behavior change.
    """
    if not enabled:
        return None
    try:
        from policy import call_llm  # noqa: F401  — verify availability once
        return evaluate_job_fit
    except ImportError:
        return None
