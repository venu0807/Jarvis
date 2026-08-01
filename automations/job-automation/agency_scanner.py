import json
import os
import sys
from pathlib import Path
from datetime import date

try:
    JARVIS_HOME = str(Path(__file__).resolve().parent.parent.parent)
    if JARVIS_HOME not in sys.path:
        sys.path.insert(0, JARVIS_HOME)
    from policy import call_llm
except Exception as e:
    call_llm = None

def scan_for_leads():
    print("🚀 [Agency Scanner] Searching for B2B consulting leads...")
    today = date.today().isoformat()
    jobs_file = Path(__file__).parent / "output" / f"jobs_{today}.json"
    
    if not jobs_file.exists():
        print(f"  ℹ️ No job listings found for {today}.")
        return

    try:
        with open(jobs_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        jobs = data if isinstance(data, list) else data.get("applied", [])
        if not jobs:
            print("  ℹ️ Empty jobs list.")
            return

        leads_found = []
        for entry in jobs:
            job = entry if "title" in entry else entry.get("job", {})
            title = job.get("title", "")
            desc = job.get("description", "")
            
            if "manual" in desc.lower() or "data entry" in desc.lower() or "automation" in desc.lower():
                leads_found.append(job.get("company", "Unknown Company"))
        
        if leads_found:
            print(f"  🎯 Found {len(leads_found)} potential agency leads!")
            for lead in leads_found:
                print(f"     - {lead}")
        else:
            print("  ℹ️ No obvious leads found today.")

    except Exception as e:
        print(f"  ❌ Error scanning jobs: {e}")

if __name__ == "__main__":
    scan_for_leads()
