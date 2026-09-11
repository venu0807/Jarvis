"""
prep_generator.py — Generate comprehensive interview master guides via JARVIS policy.
Upgraded with full topic coverage, fuzzy company matching, JD discovery, and news fetching.
"""

import sqlite3
import os
import sys
import re
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
import itertools

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
        clean_name = re.sub(r'(?i)\b(edutech|pvt|ltd|private|limited|technologies|tech|solutions|services|llp|inc|corp)\b', '', company_name).strip()
        url = f"https://news.google.com/rss/search?q={clean_name or company_name}+business+OR+tech"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            root = ET.fromstring(res.text)
            news_items = []
            for item in itertools.islice(root.iter("item"), 4):
                title = item.findtext("title")
                pubDate = item.findtext("pubDate")
                if title and " - " in title:
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
        return "Software Developer / Tester", ""
    
    clean_comp = re.sub(r'(?i)\b(edutech|pvt|ltd|private|limited|technologies|tech|solutions|services|llp|inc|corp)\b', '', company_name).strip()
    clean_comp = re.sub(r'\s+', ' ', clean_comp).strip()
    first_word = clean_comp.split()[0] if clean_comp else company_name

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(
                "SELECT title, description FROM jobs WHERE company LIKE ? OR company LIKE ? ORDER BY id DESC LIMIT 1",
                (f"%{clean_comp}%", f"%{first_word}%")
            )
            row = cur.fetchone()
            if row:
                return row[0], row[1]
    except Exception as e:
        print(f"  ⚠️ DB Query error: {e}")
    
    return "Software Tester / QA & Python Developer", ""

def generate_prep_sheet(company_name: str, interview_date: str = "Upcoming") -> str:
    print(f"🧠 Generating Comprehensive Master Prep Guide for {company_name}...")
    PREP_DIR.mkdir(parents=True, exist_ok=True)
    
    real_time_news = get_company_news(company_name)
    job_title, jd_text = fetch_job_description(company_name)
    
    if jd_text:
        print(f"  ✅ Found JD: {job_title} @ {company_name}")
    else:
        print(f"  ⚠️ JD not found for {company_name}. Generating tailored comprehensive prep.")

    prompt = f"""You are an elite Silicon Valley technical interview coach and QA/Engineering Lead.
I have an interview with {company_name} for the role of "{job_title}" coming up on {interview_date}.

Job Description / Context:
---
{jd_text or 'Software Tester / QA Automation Engineer & Python Developer (Manual testing, Playwright, PyTest, REST API testing, SQL queries, Python DSA, Bug Life Cycle, SDLC/STLC).'}
---

Recent News & Company Info:
---
{real_time_news}
---

Generate an exhaustive, comprehensive, 360-degree Master Interview Preparation Guide in clean Markdown:
1. **🏢 Company & Domain Context**: 1-sentence mission, core business products, and key architecture components.
2. **🧪 Core Technical Competencies & Deep Dives**: Detailed explanation and talking points for:
   - SDLC vs STLC, Test Design Techniques (BVA, ECP, Decision Tables), Bug Life Cycle (Severity vs Priority).
   - Test Automation (Playwright/Selenium, PyTest fixtures, POM architecture).
   - REST API Testing (HTTP methods, status codes, payload validation).
   - SQL & DB verification queries (Joins, Aggregations, Data integrity checks).
3. **💻 Real-World Domain Test Scenarios & Edge Cases**: 3 specific complex test scenarios relevant to this company's platform (e.g. login, streaming/workflows, checkout/payments).
4. **🐍 High-Frequency Technical & Coding Challenges**: 3 Python coding/logic questions with concise solutions.
5. **🗣️ Behavioral & Situational Questions (STAR Method)**: "Tell me about yourself", handling developer disagreements on bugs, and tight deadline prioritization.
6. **💡 Strategic Reverse Questions**: 3 high-impact questions to ask the interviewer.

Format with clear markdown tables, code snippets, bold highlights, and clean typography."""

    try:
        result = call_llm(
            prompt=prompt,
            mode="run",
            force="local",
            pii_acknowledged=True,
            task_label=f"prep_sheet:{company_name}",
            timeout_s=300,
        )
        md_content = result.text
        if not md_content:
            print(f"  ⏱ prep_sheet:{company_name} timed out or returned empty.")
            return ""

        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', company_name).lower()
        file_path = PREP_DIR / f"{safe_name}_prep_sheet.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        print(f"  ✅ Comprehensive Prep Sheet saved -> {file_path}")
        return str(file_path)
    except Exception as e:
        print(f"  ❌ Ollama generation failed: {e}")

    return ""

if __name__ == "__main__":
    generate_prep_sheet("Uncodemy", "2026-08-27")
