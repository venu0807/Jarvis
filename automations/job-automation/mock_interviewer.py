import sys
import os
import sqlite3
import random
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR.parent.parent))

# Import the policy chokepoint to use the local LLM
try:
    from policy import call_llm
except ImportError as e:
    print(f"❌ FATAL: Could not import policy.py. Ensure you are in the Jarvis environment. Error: {e}")
    sys.exit(1)

load_dotenv(BASE_DIR / ".env")

DB_PATH = BASE_DIR / "output" / "jobs.db"

def get_random_applied_job():
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        sys.exit(1)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Get jobs where status is applied or manual
    cursor.execute("SELECT title, company, description FROM jobs WHERE status IN ('applied', 'manual')")
    jobs = cursor.fetchall()
    conn.close()
    
    if not jobs:
        print("❌ No applied or manual jobs found in the database.")
        sys.exit(1)
        
    return random.choice(jobs)

def main():
    print("🤖 Initializing AI Mock Interviewer...")
    title, company, description = get_random_applied_job()
    
    print(f"\n========================================================")
    print(f"🏢 Company: {company}")
    print(f"💼 Role: {title}")
    print(f"========================================================\n")
    
    user_name = os.getenv("USER_FULL_NAME_UPPER", "Candidate").title()
    
    system_prompt = f"""
You are a strict, highly technical senior engineering manager at {company} interviewing {user_name} for the "{title}" position.
Your goal is to assess their technical competence based on the job description.
Be direct, professional, and do not break character. Ask one technical question at a time.
Wait for the user's response. Do NOT provide the user's answers for them.
If their answer is incomplete or wrong, grill them on it.
Keep your responses concise (1-3 sentences max). Do not include any prefixes like "Hiring Manager:".

Job Description Reference:
{description[:2000]}
"""

    chat_history = system_prompt + "\n\nYou start the interview by greeting the candidate and asking the first technical question."

    print(f"Entering interview mode. Type 'exit' or 'quit' to end.\n")
    
    # Generate the first question
    response = call_llm(
        prompt=chat_history,
        mode="run",
        force="local",
        pii_acknowledged=True,
        task_label="mock_interview"
    )
    ai_reply = response.text.strip()
    print(f"[Hiring Manager] {ai_reply}")
    chat_history += f"\n\nHiring Manager: {ai_reply}"
    
    while True:
        try:
            user_input = input(f"\n[{user_name}] ")
            if user_input.strip().lower() in ['exit', 'quit']:
                print("\nInterview ended by candidate.")
                break
            
            if not user_input.strip():
                continue
                
            chat_history += f"\n\nCandidate ({user_name}): {user_input.strip()}\n\nHiring Manager:"
            
            print("...")
            response = call_llm(
                prompt=chat_history,
                mode="run",
                force="local",
                pii_acknowledged=True,
                task_label="mock_interview"
            )
            ai_reply = response.text.strip()
            # Remove prefix if LLM generated it
            if ai_reply.startswith("Hiring Manager:"):
                ai_reply = ai_reply[len("Hiring Manager:"):].strip()
                
            print(f"\n[Hiring Manager] {ai_reply}")
            chat_history += f" {ai_reply}"
            
        except KeyboardInterrupt:
            print("\nInterview ended.")
            break
        except Exception as e:
            print(f"\n⚠️ Error: {e}")
            break

if __name__ == "__main__":
    main()
