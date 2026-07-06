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
import xml.etree.ElementTree as ET
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

def get_company_news(company_name: str) -> str:
    print(f"  📰 Fetching real-time news for {company_name}...")
    try:
        url = f"https://news.google.com/rss/search?q={company_name}+business+OR+tech"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            root = ET.fromstring(res.text)
            news_items = []
            for item in root.findall(".//item")[:4]:
                title = item.find("title").text
                pubDate = item.find("pubDate").text
                # Remove the generic source name from the end if present
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                news_items.append(f"  - {title} ({pubDate})")
            if news_items:
                return "\n".join(news_items)
    except Exception as e:
        print(f"  ⚠️ Could not fetch news: {e}")
    return "  - No recent news found."

def generate_prep_sheet(company_name: str, interview_date: str = "Unknown") -> str:
    print(f"🧠 Generating AI Prep Sheet for {company_name}...")
    PREP_DIR.mkdir(parents=True, exist_ok=True)
    
    real_time_news = get_company_news(company_name)
    
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
    prompt = f"""You are an elite Silicon Valley interview coach.
I have an interview with {company_name} coming up on {interview_date}.

Below is the Job Description for the role I applied for:
---
{jd_text}
---

Here is the real-time news and latest developments about {company_name} from this week:
---
{real_time_news}
---

Based on the JD and the real-time news, generate a concise, highly strategic 1-page "Cheat Sheet" for me to read 15 minutes before the interview. 

Your cheat sheet MUST include:
1. **The Core Mission**: 1 sentence summary of what this role actually does based on the JD.
2. **Top 3 Technical Focus Areas**: What they care about most technically.
3. **Behavioral Angles**: 2 traits they are looking for based on the JD's tone.
4. **"Insider" Questions to Ask Them**: Give me 3 brilliant questions to ask the interviewer at the end. Use the Real-Time News provided above to make at least one question hyper-specific to their current business challenges (e.g., mentioning a recent product launch or market shift).

Format using clean Markdown, bold headers, and bullet points. Be extremely concise. No fluff.
"""

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
