"""
prep_generator.py — Generate interview prep sheets via JARVIS policy.

Routed through ~/.jarvis/policy.call_llm() (mode="run") so the call is
audit-logged and PII detection runs even though the local model is already
the default. The prompt contains a JD snippet sourced from the local SQLite
DB which may contain user-applied job info — keep it policy-routed.
"""

import sqlite3
import os
import sys
import requests
from pathlib import Path

# Route via JARVIS chokepoint.
try:
    # Resolve project root relative to this script — always correct.
    JARVIS_HOME = str(Path(__file__).resolve().parent.parent.parent)
    if JARVIS_HOME not in sys.path:
        sys.path.insert(0, JARVIS_HOME)
    from policy import call_llm   # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit(
        f"FATAL: prep_generator cannot import ~/.jarvis/policy: {e!r}. "
        "Refusing direct ollama — strict-zero-leak requires policy audit log."
    )

DB_PATH = Path(__file__).parent.parent / "job-automation" / "output" / "jobs.db"
PREP_DIR = Path(__file__).parent / "prep_sheets"

def generate_prep_sheet(company_name: str, interview_date: str = "Unknown") -> str:
    print(f"🧠 Generating AI Prep Sheet for {company_name}...")
    PREP_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Fetch JD from DB
    jd_text = ""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Look for jobs matching the company name
            cur = conn.execute("SELECT title, description FROM jobs WHERE company LIKE ? LIMIT 1", (f"%{company_name}%",))
            row = cur.fetchone()
            if row:
                job_title, jd_text = row
                print(f"  ✅ Found JD: {job_title} @ {company_name}")
            else:
                print(f"  ⚠️ JD not found for {company_name}. Using generic prep.")
                job_title = "Unknown Role"
    except Exception as e:
        print(f"  ❌ DB Error: {e}")
        return ""

    # 2. Prompt JARVIS policy
    # Prompt tuned 2026-06-15: the original verbose template routinely hit
    # ollama's response generation past the 120s budget for unknown JDs.
    # Trimmed to ~50% the words and explicit 240s timeout so:
    #   * known-JD company → ~13s (unchanged, was already fast)
    #   * unknown-JD fallback → still finishes inside 240s
    # The lower num_predict cap on the local call matches phi4-mini's sweet
    # spot for structured markdown of this size (5 tech + 3 STAR questions).
    prompt = f"""Interview coach: prep {company_name} ({job_title}).

Job Description:
{jd_text[:1500] if jd_text else "Not available — use generic backend/frontend prep."}

Reply in Markdown:
## Company
Brief overview (2-3 lines).

## Tech Stack
5 bullet points derived from the JD.

## Technical Questions
5 questions with one-line answer hints each.

## Behavioral Questions (STAR)
3 STAR-method prompts.

Be concise. No intro/outro paragraphs. Markdown only."""

    try:
        # Route through JARVIS policy so this call is audit-logged.
        # mode="run" + pii_acknowledged=True because the JD snippet may
        # contain applied-job-bodies that include company-specific PII.
        # timeout_s=240 handles unknown-JD prompts that the trimmed
        # template still occasionally generates past 120s.
        result = call_llm(
            prompt=prompt,
            mode="run",
            force="local",
            pii_acknowledged=True,
            task_label=f"prep_sheet:{company_name}",
            timeout_s=240,
        )
        md_content = result.text

        # Detect timeout-fallback (call_llm returns empty text + audit-logged
        # ollama_timeout when timeout exceeded). Don't write an empty file;
        # surface the failure cleanly so the caller knows to retry or skip.
        if not md_content:
            print(
                f"  ⏱  prep_sheet:{company_name} timed out after the budget. "
                f"See ~/.jarvis/audit.log for the ollama_timeout event. "
                f"Not writing an empty prep file."
            )
            return ""

        # 3. Save to file
        safe_name = company_name.replace(" ", "_").lower()
        file_path = PREP_DIR / f"{safe_name}_prep_sheet.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        print(f"  ✅ Prep Sheet saved -> {file_path} (via {result.model}, {result.provider})")
        return str(file_path)
    except Exception as e:
        print(f"  ❌ Ollama generation failed: {e}")

    return ""

if __name__ == "__main__":
    generate_prep_sheet("Scoutit")
