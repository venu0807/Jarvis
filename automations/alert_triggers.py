"""
alert_triggers.py — Specific alerting rules for JARVIS automations.

Checks and alerts for:
- Job automation: 0 applies for 2+ consecutive runs
- Portal session expired (manual re-login needed)
- PostgreSQL connection failures
- Cron job didn't run (scheduler dead > 30 min)
- Disk space > 85%
- Ollama unavailable
"""

import os
import sys
import json
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path
import psutil

# Add project root to path
sys.path.insert(0, os.path.expanduser("~/Proposals/Jarvis"))

from automations.alert_manager import send_warning, send_critical, send_info

logger = logging.getLogger(__name__)


def _resolve_path(*path_parts: str) -> Path:
    """Resolve path trying WSL, Git for Windows, and Windows home prefixes."""
    prefixes = [
        "/home/venu",
        "D:/Programs/Git/home/venu",
        os.path.expanduser("~"),
    ]
    for prefix in prefixes:
        candidate = Path(prefix) / Path(*path_parts)
        if candidate.exists():
            return candidate
    # Default to WSL path for creation
    return Path("/home/venu") / Path(*path_parts)


# Configuration
JARVIS_HOME = _resolve_path("Proposals", "Jarvis")
JOB_AUTO_DIR = _resolve_path("Proposals", "Jarvis", "automations", "job-automation")
LOG_DIR = _resolve_path("Proposals", "Jarvis", "automations", "job-automation", "output", "logs")
SCHEDULER_LOG = _resolve_path("Proposals", "Jarvis", "automations", "jarvis_cron.log")
SECRETS_DIR = _resolve_path(".jarvis", ".secrets")
ALERT_COOLDOWN = timedelta(hours=1)  # Don't re-alert same issue within this time

# Track last alert times to prevent spam
last_alerts = {}

# Newline constant for f-strings
NL = "\n"


def should_alert(alert_key: str, cooldown: timedelta = ALERT_COOLDOWN) -> bool:
    """Check if we should alert based on cooldown"""
    now = datetime.now()
    if alert_key in last_alerts:
        if now - last_alerts[alert_key] < cooldown:
            return False
    last_alerts[alert_key] = now
    return True


def check_job_apply_count():
    """Alert if job automation has 0 applies for 2+ consecutive runs"""
    try:
        # Check recent logs for apply counts
        log_files = sorted(LOG_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)[:5]

        zero_apply_runs = 0
        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    data = json.loads(content)
                    # Check totals.applied
                    totals = data.get("totals", {})
                    applied = totals.get("applied", 0)
                    if applied == 0:
                        zero_apply_runs += 1
                    else:
                        zero_apply_runs = 0  # Reset if we find non-zero
            except:
                continue

        if zero_apply_runs >= 2:
            if should_alert("job_zero_applies"):
                send_critical(
                    title="🚨 Job Automation: Zero Applications",
                    message=(
                        f"Job automation has recorded 0 applications for {zero_apply_runs} consecutive runs.{NL}{NL}"
                        f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}"
                        f"Log directory: {LOG_DIR}{NL}{NL}"
                        "Possible causes:{NL}"
                        "- Portal sessions expired (cookies/auth tokens){NL}"
                        "- Website DOM changes breaking scrapers{NL}"
                        "- Rate limiting or IP blocking{NL}"
                        "- Credential issues{NL}{NL}"
                        "Immediate actions:{NL}"
                        f"1. Check portal session status{NL}"
                        f"2. Run manual test: cd {JOB_AUTO_DIR} && python run_pipeline.py --test{NL}"
                        f"3. Review recent logs in {LOG_DIR}"
                    ),
                    alert_key="job_zero_applies"
                )
                return True
    except Exception as e:
        logger.error(f"Error checking job apply count: {e}")
    return False


def check_postgres_connection():
    """Alert if PostgreSQL connection fails"""
    try:
        # Try TCP socket connection to PostgreSQL (works via Docker Desktop port forwarding)
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('localhost', 5432))
        sock.close()

        if result != 0:
            if should_alert("postgres_connection"):
                send_critical(
                    title="🚨 PostgreSQL Connection Failed",
                    message=(
                        "JARVIS cannot connect to PostgreSQL database.{NL}{NL}"
                        "Error: TCP connection to localhost:5432 failed{NL}"
                        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}{NL}"
                        "Impact:{NL}"
                        "- Job tracking will fail{NL}"
                        "- Event bus may not work{NL}"
                        "- Metrics collection disrupted{NL}"
                        "- All automations relying on DB will fail{NL}{NL}"
                        "Immediate actions:{NL}"
                        "1. Check PostgreSQL container: docker ps | grep postgres{NL}"
                        "2. Restart if needed: docker restart jarvis-postgres{NL}"
                        '3. Verify connection: PGPASSWORD=jarvis psql -h localhost -U jarvis -d jarvis -c "SELECT 1;"{NL}'
                        "4. Check credentials in ~/.jarvis/.secrets/"
                    ),
                    alert_key="postgres_connection"
                )
                return True
        else:
            # Clear alert if it was previously firing
            if "postgres_connection" in last_alerts:
                del last_alerts["postgres_connection"]
    except Exception as e:
        logger.error(f"Error checking PostgreSQL: {e}")
    return False


def _handle_scheduler_missing():
    if should_alert("scheduler_missing"):
        send_warning(
            title="⚠️ Scheduler Log Missing",
            message=(
                f"JARVIS scheduler log file not found: {SCHEDULER_LOG}{NL}{NL}"
                "This suggests the cron scheduler may not be running.{NL}"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}{NL}"
                "Immediate actions:{NL}"
                "1. Check cron service: systemctl --user status cron{NL}"
                "2. Check crontab: crontab -l{NL}"
                f"3. Restart scheduler: {JARVIS_HOME}/jarvis_scheduler.sh &{NL}"
                "4. Verify it's running: ps aux | grep jarvis_scheduler"
            ),
            alert_key="scheduler_missing"
        )
        return True
    return False


def _handle_scheduler_stale(mtime):
    if should_alert("scheduler_stale"):
        send_critical(
            title="🚨 Scheduler Appears Dead",
            message=(
                "JARVIS scheduler log has not been updated in >30 minutes.{NL}{NL}"
                f"Last activity: {mtime.strftime('%Y-%m-%d %H:%M:%S')}{NL}"
                f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}"
                f"Log file: {SCHEDULER_LOG}{NL}{NL}"
                "This indicates the cron scheduler may have stopped.{NL}{NL}"
                "Immediate actions:{NL}"
                "1. Check scheduler process: ps aux | grep jarvis_scheduler{NL}"
                "2. Check cron logs: journalctl --user -u cron{NL}"
                f"3. Restart scheduler: nohup {JARVIS_HOME}/jarvis_scheduler.sh &{NL}"
                "4. Verify crontab is installed: crontab -l{NL}"
                "5. Check for errors in scheduler script"
            ),
            alert_key="scheduler_stale"
        )
        return True
    return False


def check_scheduler_health():
    """Alert if cron scheduler appears dead (>30 min no activity)"""
    try:
        if not SCHEDULER_LOG.exists():
            return _handle_scheduler_missing()
        else:
            # Check last modification time
            mtime = datetime.fromtimestamp(SCHEDULER_LOG.stat().st_mtime)
            if datetime.now() - mtime > timedelta(minutes=30):
                return _handle_scheduler_stale(mtime)
            else:
                # Clear alert if it was previously firing
                if "scheduler_stale" in last_alerts:
                    del last_alerts["scheduler_stale"]
                if "scheduler_missing" in last_alerts:
                    del last_alerts["scheduler_missing"]
    except Exception as e:
        logger.error(f"Error checking scheduler: {e}")
    return False


def check_disk_space():
    """Alert if disk space > 85%"""
    try:
        disk = psutil.disk_usage('/')
        percent_used = disk.used / disk.total * 100

        if percent_used > 85:
            if should_alert("disk_space"):
                send_warning(
                    title="⚠️ High Disk Usage",
                    message=(
                        f"Disk usage is critical: {percent_used:.1f}% used{NL}{NL}"
                        f"Total: {disk.total // (1024**3)} GB{NL}"
                        f"Used: {disk.used // (1024**3)} GB{NL}"
                        f"Free: {disk.free // (1024**3)} GB{NL}"
                        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}{NL}"
                        "Immediate actions:{NL}"
                        "1. Clean old backups: find /home/venu/backups -type f -mtime +30 -delete{NL}"
                        "2. Clear pip cache: pip cache purge{NL}"
                        "3. Clear npm cache: npm cache clean --force{NL}"
                        "4. Check large files: du -sh /* | sort -hr | head -10{NL}"
                        "5. Consider expanding disk space"
                    ),
                    alert_key="disk_space"
                )
                return True
        else:
            # Clear alert if it was previously firing
            if "disk_space" in last_alerts:
                del last_alerts["disk_space"]
    except Exception as e:
        logger.error(f"Error checking disk space: {e}")
    return False


def check_ollama_availability():
    """Alert if Ollama is unavailable"""
    try:
        # Try to connect to Ollama API
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)

        if response.status_code != 200:
            if should_alert("ollama_unavailable"):
                send_warning(
                    title="⚠️ Ollama Unavailable",
                    message=(
                        "Ollama API is not responding correctly.{NL}{NL}"
                        f"Status code: {response.status_code}{NL}"
                        f"Response: {response.text[:200] if response.text else 'No response'}{NL}"
                        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}{NL}"
                        "Impact:{NL}"
                        "- AI job classification will fail{NL}"
                        "- Cover letter generation disabled{NL}"
                        "- Resume tailoring unavailable{NL}"
                        "- Interview preparation affected{NL}{NL}"
                        "Immediate actions:{NL}"
                        "1. Check Ollama service: systemctl --user status ollama{NL}"
                        "2. Restart Ollama: systemctl --user restart ollama{NL}"
                        "3. Verify it's running: curl http://localhost:11434/api/tags{NL}"
                        "4. Check logs: journalctl --user -u ollama{NL}"
                        "5. Pull a model to test: ollama pull llama3.2"
                    ),
                    alert_key="ollama_unavailable"
                )
                return True
        else:
            # Clear alert if it was previously firing
            if "ollama_unavailable" in last_alerts:
                del last_alerts["ollama_unavailable"]
    except Exception as e:
        if should_alert("ollama_unavailable"):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            send_warning(
                title="⚠️ Ollama Unavailable",
                message=(
                    "Cannot connect to Ollama API.{NL}{NL}"
                    f"Error: {str(e)}{NL}"
                    f"Time: {timestamp}{NL}{NL}"
                    "This usually means Ollama is not running.{NL}{NL}"
                    "Immediate actions:{NL}"
                    "1. Start Ollama: systemctl --user start ollama{NL}"
                    "2. Enable at startup: systemctl --user enable ollama{NL}"
                    "3. Verify installation: which ollama{NL}"
                    "4. Pull a test model: ollama pull llama3.2{NL}"
                    "5. Check if port 11434 is listening: ss -tlnp | grep 11434"
                ),
                alert_key="ollama_unavailable"
            )
            return True
    return False


def check_portal_sessions():
    """Check for expired portal sessions (placeholder - would need portal-specific checks)"""
    # This is a simplified check - in reality, each portal would need specific logic
    # For now, we'll check if session files are very old
    try:
        session_dirs = [
            JOB_AUTO_DIR / ".sessions",
            JARVIS_HOME / ".linkedin_sessions",
            JARVIS_HOME / ".naukri_sessions",
            JARVIS_HOME / ".indeed_sessions"
        ]

        old_sessions = []
        for session_dir in session_dirs:
            if session_dir.exists():
                # Check if any session files are older than 7 days
                cutoff = datetime.now() - timedelta(days=7)
                for session_file in session_dir.rglob("*"):
                    if session_file.is_file():
                        mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
                        if mtime < cutoff:
                            old_sessions.append(f"{session_dir.name}: {session_file.name}")

        if old_sessions and should_alert("portal_sessions_old"):
            send_info(
                title="ℹ️ Portal Sessions May Be Expired",
                message=(
                    "Some portal session files are older than 7 days.{NL}{NL}"
                    "Old sessions found:{NL}" + "\n".join(f"  - {s}" for s in old_sessions[:5]) +
                    (f"{NL}  - ... and {len(old_sessions)-5} more" if len(old_sessions) > 5 else "") +
                    f"{NL}{NL}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}{NL}"
                    "Note: This is informational. Actual expiration varies by portal.{NL}"
                    "Most portals require re-login every 1-7 days.{NL}{NL}"
                    "Recommended action:{NL}"
                    "Run manual login refresh for portals showing issues:{NL}"
                    '- LinkedIn: python3 -c "from automations.linkedin_outreach.linkedin_bot import LinkedInBot; b=LinkedInBot(); b.login()"{NL}'
                    "- Naukri: Similar process in job-automation{NL}"
                    "- Indeed: Check job-automation/indeed_scraper.py"
                ),
                alert_key="portal_sessions_old"
            )
            return True
    except Exception as e:
        logger.error(f"Error checking portal sessions: {e}")
    return False


def run_checks():
    """Run all alert checks and return list of triggered alerts"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(JARVIS_HOME / "automations" / "alert_triggers.log"),
            logging.StreamHandler()
        ]
    )

    logger.info("Starting JARVIS alert triggers check")

    alerts_triggered = []

    # Run all checks
    checks = [
        ("Job Apply Count", check_job_apply_count),
        ("PostgreSQL Connection", check_postgres_connection),
        ("Scheduler Health", check_scheduler_health),
        ("Disk Space", check_disk_space),
        ("Ollama Availability", check_ollama_availability),
        ("Portal Sessions", check_portal_sessions),
    ]

    for name, check_func in checks:
        try:
            if check_func():
                alerts_triggered.append(name)
                logger.info(f"Alert triggered: {name}")
            else:
                logger.debug(f"No alert: {name}")
        except Exception as e:
            logger.error(f"Error in check {name}: {e}")

    if alerts_triggered:
        logger.info(f"Alert check complete. Triggered: {', '.join(alerts_triggered)}")
    else:
        logger.info("Alert check complete. No alerts triggered.")

    return alerts_triggered


def main():
    """Run all alert checks"""
    return run_checks()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)