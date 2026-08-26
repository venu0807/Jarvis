"""
prep_generator.py — Generate interview prep sheets via JARVIS policy.
Upgraded with fuzzy company matching, JD discovery, and news fetching.
"""

import sqlite3
import os
import sys
import re
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

# Route via JARVIS chokepoint.
try:
    JARVIS_HOME = str(Path(__file__).resolve().parent.parent.parent)
    if JARVIS_HOME not in sys.path:
        sys.path.insert(0, JARVIS_HOME)
    from policy import call_llm   # type: ignore
except Exception as e:
    raise SystemExit(f"FATAL: prep_generator cannot import ~/.jarvis/policy: {e!r}.")

DB_PATH = Path(__file__).parent.parent / "job-automation" / "output" / "jobs.db"
PREP_DIR = Path(__file__).parent / "prep_sheets"

def get_company_news(company_name: str) -> str:
    print(f"  📰 Fetching real-time news for {company_name}...")
    try:
        # Strip legal suffixes for news search
        clean_name = re.sub(r'(?i)\b(edutech|pvt|ltd|private|limited|technologies|tech|solutions|services|llp|inc|corp)\b', '', company_name).strip()
        url = f"https://news.google.com/rss/search?q={clean_name or company_name}+business+OR+tech"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            root = ET.fromstring(res.text)
            news_items = []
            for item in root.findall(".//item")[:4]:
                title = item.find("title").text
                pubDate = item.find("pubDate").text
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                news_items.append(f"  - {title} ({pubDate})")
            if news_items:
                return "\n".join(news_items)
    except Exception as e:
        print(f"  ⚠️ Could not fetch news: {e}")
    return "  - No recent news found."

def fetch_job_description(company_name: str) -> tuple[str, str]:
    """Fuzzy search jobs.db for the matching company and job description."""
    if not DB_PATH.exists():
        return "Software Developer", ""
    
    clean_comp = re.sub(r'(?i)\b(edutech|pvt|ltd|private|limited|technologies|tech|solutions|services|llp|inc|corp)\b', '', company_name).strip()
    clean_comp = re.sub(r'\s+', ' ', clean_comp).strip()
    first_word = clean_comp.split()[0] if clean_comp else company_name

    try:
        with sqlite3.connect(DB_PATH) as conn:
            # 1. Exact match or broad match
            cur = conn.execute(
                "SELECT title, description FROM jobs WHERE company LIKE ? OR company LIKE ? ORDER BY id DESC LIMIT 1",
                (f"%{clean_comp}%", f"%{first_word}%")
            )
            row = cur.fetchone()
            if row:
                return row[0], row[1]
    except Exception as e:
        print(f"  ⚠️ DB Query error: {e}")
    
    return "Developer", ""

def generate_prep_sheet(company_name: str, interview_date: str = "Upcoming") -> str:
    print(f"🧠 Generating AI Prep Sheet for {company_name}...")
    PREP_DIR.mkdir(parents=True, exist_ok=True)
    
    real_time_news = get_company_news(company_name)
    job_title, jd_text = fetch_job_description(company_name)
    
    if jd_text:
        print(f"  ✅ Found JD: {job_title} @ {company_name}")
    else:
        print(f"  ⚠️ JD not found for {company_name}. Generating tailored developer prep.")

    prompt = f"""You are an elite Silicon Valley interview coach.
I have an interview with {company_name} for the role of "{job_title}" coming up on {interview_date}.

Below is the Job Description for the role I applied for:
---
{jd_text or 'Junior / Fresher Software & Web Developer role focusing on Python, Django, React, HTML, CSS, JavaScript, and backend APIs.'}
---

Here is the real-time news and latest developments about {company_name}:
---
{real_time_news}
---

Generate a concise, highly strategic 1-page "Cheat Sheet" for me to read 15 minutes before the interview:
1. **The Core Mission**: 1-sentence summary of what this role does and how it impacts the business.
2. **Top 3 Technical Focus Areas**: The 3 most critical skills to demonstrate (with specific talking points).
3. **Behavioral Angles**: 2 traits they are looking for (e.g. adaptability, initiative, problem solving).
4. **"Insider" Questions to Ask Them**: 3 brilliant, thoughtful questions to ask the interviewer.

Format using clean Markdown, bold headers, and bullet points. Be extremely concise.
"""

    try:
        result = call_llm(
            prompt=prompt,
            mode="run",
            force="local",
            pii_acknowledged=True,
            task_label=f"prep_sheet:{company_name}",
            timeout_s=240,
        )
        md_content = result.text
        if not md_content:
            print(f"  ⏱ prep_sheet:{company_name} timed out or returned empty.")
            return ""

        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', company_name).lower()
        file_path = PREP_DIR / f"{safe_name}_prep_sheet.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        print(f"  ✅ Prep Sheet saved -> {file_path}")
        return str(file_path)
    except Exception as e:
        print(f"  ❌ Ollama generation failed: {e}")

    return ""

if __name__ == "__main__":
    generate_prep_sheet("Uncodemy", "2026-08-27")
