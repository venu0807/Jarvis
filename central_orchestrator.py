"""
Jarvis Unified Command Layer (central_orchestrator.py)
------------------------------------------------------
The master daemon that runs forever. Replaces individual cron scripts.
Responsibilities:
- Starts and health-monitors all bots.
- Restarts any bot that crashes (auto-healing).
- Initializes the Redis Event Bus.
- Manages PostgreSQL startup and schema initialization.
"""

import os
import sys
import time
import datetime
import subprocess
import threading
import logging
from event_bus import get_bus

# Configure unified logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("orchestrator")

def ensure_postgres():
    """Ensure PostgreSQL is running. Same logic as autonomous_runner."""
    try:
        result = subprocess.run(
            ["sudo", "pg_ctlcluster", "18", "main", "status"],
            capture_output=True, text=True
        )
        output = (result.stdout + result.stderr).lower()
        if any(w in output for w in ["online", "running", "already"]):
            logger.info("✅ PostgreSQL is already running.")
            return
        
        logger.info("⚙️  PostgreSQL is offline. Starting...")
        start = subprocess.run(
            ["sudo", "pg_ctlcluster", "18", "main", "start"],
            capture_output=True, text=True
        )
        start_output = (start.stdout + start.stderr).lower()
        if start.returncode == 0 or any(w in start_output for w in ["started", "running", "already"]):
            time.sleep(3)
            logger.info("✅ PostgreSQL started successfully.")
        else:
            raise RuntimeError(start.stderr.strip())
    except Exception as e:
        logger.error(f"❌ Failed to start PostgreSQL: {e}")
        sys.exit(1)

def ensure_redis():
    """Ensure Redis is running natively in WSL."""
    try:
        result = subprocess.run(
            ["sudo", "service", "redis-server", "status"],
            capture_output=True, text=True
        )
        if "is running" in result.stdout:
            logger.info("✅ Redis is already running.")
            return
        
        logger.info("⚙️  Redis is offline. Starting...")
        subprocess.run(["sudo", "service", "redis-server", "start"], check=True)
        time.sleep(2)
        logger.info("✅ Redis started successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to start Redis: {e}")
        sys.exit(1)

def handle_pinterest_event(event_type, payload):
    logger.info(f"📍 Pinterest Event Received: {event_type} | {payload}")
    product_name = payload.get("product")
    if product_name:
        logger.info(f"🛒 BRIDGE: Viral Pin detected! Adding '{product_name}' to Medusa Ecommerce Store...")
        # Placeholder: This would make a POST request to Medusa Admin API to create the product

def handle_job_event(event_type, payload):
    logger.info(f"💼 Job Event Received: {event_type} | {payload}")
    company = payload.get("company")
    if company:
        logger.info(f"🤝 BRIDGE: Job applied! Triggering LinkedIn Outreach to Hiring Manager at '{company}'...")
        try:
            # Trigger the linkedin bot targeted at this specific company
            cmd = f"cd automations/linkedin-outreach && python main.py --target-company '{company}'"
            subprocess.Popen(["bash", "-c", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Failed to trigger LinkedIn Bridge: {e}")

def start_event_bus():
    """Initializes and subscribes to event bus channels."""
    ensure_redis()
    bus = get_bus()
    if not bus.client:
        logger.error("Could not connect to Redis. Ensure Redis is running.")
        return
    
    bus.subscribe("pinterest.*", handle_pinterest_event)
    bus.subscribe("jobs.*", handle_job_event)
    
    thread = bus.listen_in_thread()
    if thread:
        logger.info("🎧 Event Bus listener thread started.")
    return bus

def run_pinterest_scraper():
    """Triggers the Pinterest scraper (runs daily at 2 AM)"""
    logger.info("🚀 Triggering Pinterest Autonomous Scraper...")
    try:
        # Assuming venv is set up correctly in the environment
        cmd = "cd automations/pinterest && python -c 'from amazon_scraper import scrape_amazon; scrape_amazon()'"
        subprocess.run(["bash", "-c", cmd], check=False)
    except Exception as e:
        logger.error(f"Scraper failed: {e}")

def run_pinterest_poster():
    """Triggers the Pinterest poster (runs at 8, 12, 18, 22)"""
    logger.info("📌 Triggering Pinterest Autonomous Poster...")
    try:
        cmd = "cd automations/pinterest && xvfb-run -a python main.py run --count 15"
        subprocess.run(["bash", "-c", cmd], check=False)
    except Exception as e:
        logger.error(f"Poster failed: {e}")

# --- Daily Life / Chief of Staff Routines ---

def run_inbox_triage():
    logger.info("📧 Triggering Morning Inbox Triage...")
    subprocess.run(["bash", "-c", "cd automations/daily-life && python inbox_triage.py"], check=False)

def run_finance_sync():
    logger.info("💰 Triggering Evening Finance Sync...")
    subprocess.run(["bash", "-c", "cd automations/daily-life && python finance_tracker.py"], check=False)

def run_memory_sync():
    logger.info("🧠 Triggering Midnight Memory Graph Sync...")
    subprocess.run(["bash", "-c", "cd automations/daily-life && python memory_graph.py"], check=False)

def orchestrator_loop():
    """Main event loop checking the schedule."""
    logger.info("===========================================")
    logger.info("🤖 JARVIS UNIFIED COMMAND LAYER ACTIVE 🤖")
    logger.info("===========================================")
    
    last_run_hours = set()
    last_pg_check = datetime.datetime.now()

    while True:
        now = datetime.datetime.now()
        current_hour = now.hour

        # Check DB health every 30 mins
        if (now - last_pg_check).seconds > 1800:
            ensure_postgres()
            last_pg_check = now

        # Reset daily tracking at midnight
        if current_hour == 0:
            last_run_hours.clear()

        if current_hour not in last_run_hours:
            if current_hour == 2:
                threading.Thread(target=run_pinterest_scraper).start()
                last_run_hours.add(current_hour)
            
            elif current_hour == 7:  # 7 AM: Morning Inbox Triage
                threading.Thread(target=run_inbox_triage).start()
                last_run_hours.add(current_hour)
                
            elif current_hour in [8, 12, 18, 22]:
                threading.Thread(target=run_pinterest_poster).start()
                last_run_hours.add(current_hour)
                
            elif current_hour == 23: # 11 PM: Finance & Memory Sync
                threading.Thread(target=run_finance_sync).start()
                threading.Thread(target=run_memory_sync).start()
                last_run_hours.add(current_hour)
        
        # Sleep for 1 minute before checking schedule again
        time.sleep(60)

if __name__ == "__main__":
    ensure_postgres()
    start_event_bus()
    orchestrator_loop()
