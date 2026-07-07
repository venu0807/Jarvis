import os
import sys
import time
from datetime import datetime, timezone
import subprocess
from pathlib import Path

# Paths to the scripts
BASE_DIR = Path(__file__).parent.resolve()

SCRIPTS = {
    "Ghost Networker": BASE_DIR / "ghost-networker" / "monitor.py",
    "Micro-Learning": BASE_DIR / "micro-learning" / "generator.py",
    "LinkedIn Outreach": BASE_DIR / "linkedin-outreach" / "main.py",
    "Job Auto-Applier": BASE_DIR / "job-automation" / "run_pipeline.py",
    "Inbox Monitor": BASE_DIR / "inbox-monitor" / "portal_monitor.py",
    "Email Monitor": BASE_DIR / "inbox-monitor" / "imap_scanner.py",
    "Profile Bumper": BASE_DIR / "inbox-monitor" / "profile_bumper.py",
}

def run_script(name: str, path: Path, args: list = None):
    """Executes a Python script and logs the output."""
    if not path.exists():
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ ERROR: {name} script not found at {path}")
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Running {name}...")
    cmd = [sys.executable, str(path)]
    if args:
        cmd.extend(args)
        
    try:
        # We run it synchronously so we don't blow up the GPU RAM
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {name} finished successfully.")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ {name} failed with exit code {result.returncode}")
            print(f"Error Output:\n{result.stderr}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Exception running {name}: {e}")

def main():
    print("==================================================")
    print("🤖 Jarvis Autonomous Orchestrator Initialized")
    print("==================================================")
    print("Press Ctrl+C to stop the orchestrator.")
    
    # We will use simple timing variables for our "cron" equivalent
    last_networker_run = 0
    last_learning_run = 0
    last_jobs_run = 0
    last_inbox_run = 0
    last_bump_run = 0
    
    # 4 hours in seconds
    NETWORKER_INTERVAL = 4 * 60 * 60 
    INBOX_INTERVAL = 4 * 60 * 60
    
    # 24 hours in seconds
    LEARNING_INTERVAL = 24 * 60 * 60
    
    try:
        while True:
            current_time = time.time()
            
            # 1. Run Ghost Networker every 4 hours
            if current_time - last_networker_run > NETWORKER_INTERVAL:
                run_script("Ghost Networker", SCRIPTS["Ghost Networker"])
                last_networker_run = current_time
                
            # 2. Run Micro-Learning once a day
            if current_time - last_learning_run > LEARNING_INTERVAL:
                run_script("Micro-Learning", SCRIPTS["Micro-Learning"])
                last_learning_run = current_time
                
            # 3. Run Job Auto-Applier once a day (staggered)
            if current_time - last_jobs_run > LEARNING_INTERVAL:
                run_script("Job Auto-Applier", SCRIPTS["Job Auto-Applier"])
                last_jobs_run = current_time
                
            # 4. Run Inbox Monitor every 4 hours
            if current_time - last_inbox_run > INBOX_INTERVAL:
                run_script("Inbox Monitor", SCRIPTS["Inbox Monitor"])
                run_script("Email Monitor", SCRIPTS["Email Monitor"])
                last_inbox_run = current_time
                
            # 5. Run Profile Bumper once a day
            if current_time - last_bump_run > LEARNING_INTERVAL:
                run_script("Profile Bumper", SCRIPTS["Profile Bumper"])
                last_bump_run = current_time
                
            # Sleep for 10 minutes before checking the schedule again
            time.sleep(600)
            
    except KeyboardInterrupt:
        print("\n🛑 Orchestrator shut down gracefully.")

if __name__ == "__main__":
    main()
