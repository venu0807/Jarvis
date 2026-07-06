import time
import datetime
import subprocess
import sys
import os

def ensure_postgres():
    """Ensure PostgreSQL is running. Safe to call on every startup."""
    try:
        result = subprocess.run(
            ["sudo", "pg_ctlcluster", "18", "main", "status"],
            capture_output=True, text=True
        )
        output = (result.stdout + result.stderr).lower()
        already_running = any(w in output for w in ["online", "running", "already"])
        if already_running:
            print("  ✅ PostgreSQL is already running.")
            return
        print("  ⚙️  PostgreSQL is offline. Starting...")
        start = subprocess.run(
            ["sudo", "pg_ctlcluster", "18", "main", "start"],
            capture_output=True, text=True
        )
        start_output = (start.stdout + start.stderr).lower()
        if start.returncode == 0 or any(w in start_output for w in ["started", "running", "already"]):
            time.sleep(3)
            print("  ✅ PostgreSQL started successfully.")
        else:
            raise RuntimeError(start.stderr.strip())
    except Exception as e:
        print(f"  ❌ Failed to start PostgreSQL: {e}")
        print("  ⚠️  Run manually: sudo pg_ctlcluster 18 main start")
        sys.exit(1)

def main():
    print("===========================================")
    print("🤖 JARVIS FULLY AUTONOMOUS ENGINE STARTED 🤖")
    print("===========================================")
    print("  • PostgreSQL: Auto-managed ✅")
    print("  • Scraper scheduled for 02:00 AM daily")
    print("  • Poster scheduled for 08:00 AM, 12:00 PM, 06:00 PM, 10:00 PM")
    print("  Leave this script running in the background to generate passive income.\n")

    # ── Step 1: Ensure PostgreSQL is running ─────────────────────────────
    print("[STARTUP] Checking database...")
    ensure_postgres()

    # ── Step 2: Import after DB is confirmed up ───────────────────────────
    from amazon_scraper import scrape_amazon
    from main import run_automation
    from cookie_renewal import check_and_renew
    from analytics_dashboard import generate_dashboard


    # Track which hours we've already executed today so we don't double-post
    last_run_hours = set()
    last_pg_check = datetime.datetime.now()

    while True:
        now = datetime.datetime.now()
        current_hour = now.hour

        # Re-check PostgreSQL every 30 minutes to auto-recover if it crashes
        if (now - last_pg_check).seconds > 1800:
            ensure_postgres()
            last_pg_check = now

        # Clear tracker at midnight for the new day
        if current_hour == 0:
            last_run_hours.clear()

        if current_hour not in last_run_hours:
            if current_hour == 2:
                print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] 🚀 Running Autonomous Scraper...")
                try:
                    scrape_amazon()
                except Exception as e:
                    print(f"  ❌ Scraper failed: {e}")
                last_run_hours.add(current_hour)

            elif current_hour in [6, 10, 14, 18, 22]:
                print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] 📌 Running Autonomous Poster...")
                # Check cookie health before every posting session
                check_and_renew()
                try:
                    run_automation(max_pins=6)
                    # Regenerate analytics dashboard after every successful run
                    generate_dashboard()
                    print("  📊 Analytics dashboard updated.")
                except Exception as e:
                    print(f"  ❌ Poster failed: {e}")
                last_run_hours.add(current_hour)

        # Sleep for 5 minutes before checking the time again
        time.sleep(300)

if __name__ == "__main__":
    main()
