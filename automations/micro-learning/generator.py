import sqlite3
import sys
import time
from pathlib import Path

try:
    JARVIS_HOME = str(Path(__file__).resolve().parent.parent.parent)
    if JARVIS_HOME not in sys.path:
        sys.path.insert(0, JARVIS_HOME)
    from policy import call_llm   # type: ignore
except Exception as e:
    raise SystemExit(f"FATAL: micro-learning cannot import ~/.jarvis/policy: {e!r}.")

DB_PATH = Path(__file__).parent.parent / "job-automation" / "output" / "jobs.db"
OUTPUT_FILE = Path(__file__).parent / "daily_lesson.md"

def fetch_skipped_jobs():
    """Fetch 3 recent jobs from the database to analyze."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # First try to find jobs with a status (like skipped or rejected)
            # If there's no status column, just grab the most recent 3 jobs
            try:
                cur = conn.execute("SELECT title, description FROM jobs WHERE status IN ('skipped', 'rejected') ORDER BY id DESC LIMIT 3")
                rows = cur.fetchall()
            except sqlite3.OperationalError:
                # Fallback if 'status' column doesn't exist
                cur = conn.execute("SELECT title, description FROM jobs ORDER BY id DESC LIMIT 3")
                rows = cur.fetchall()
            return rows
    except Exception as e:
        print(f"❌ DB Error: {e}")
        return []

def generate_daily_lesson():
    print("🧠 Starting Daily Micro-Learning Generator...")
    jobs = fetch_skipped_jobs()
    if not jobs:
        print("⚠️ No jobs found to analyze.")
        return

    # Combine the job descriptions
    jd_context = ""
    for idx, (title, desc) in enumerate(jobs):
        jd_context += f"Job {idx+1}: {title}\n{desc[:1000]}\n\n"

    prompt = f"""You are an elite Senior Engineer mentoring a Junior Python/Django Developer.

I recently looked at these 3 job descriptions but felt underqualified or got rejected:
\"\"\"
{jd_context}
\"\"\"

My current core skills are: Python, Django, React.js, and basic ML (TensorFlow/CNNs).

TASK:
1. Analyze the job descriptions and identify the single most critical, high-paying skill or tool that I am MISSING (e.g. Docker, GraphQL, Redis, AWS, CI/CD, Kubernetes, etc.).
2. Write a highly engaging, 5-minute crash course on that specific skill.
3. Include a practical, copy-pasteable code example (e.g., a Dockerfile, a Redis cache snippet).
4. End with a 1-question quiz to test my understanding.

Format perfectly in Markdown. Start directly with the title of the skill (e.g. "# Today's Skill: Docker"). No introductory fluff.
"""
    
    print("🤖 Analyzing missing skills and generating lesson...")
    try:
        result = call_llm(
            prompt=prompt,
            mode="run",
            force="local",
            pii_acknowledged=True, 
            task_label="micro_learning",
            timeout_s=300
        )
        
        md_content = result.text
        if md_content:
            OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(md_content)
            print(f"✅ Daily lesson saved to {OUTPUT_FILE}")
        else:
            print("⚠️ Generation returned empty content.")
    except Exception as e:
        print(f"❌ LLM generation failed: {e}")

if __name__ == "__main__":
    generate_daily_lesson()
