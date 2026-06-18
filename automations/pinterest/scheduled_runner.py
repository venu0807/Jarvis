#!/usr/bin/env python3
"""
Scheduled Runner with Logging
=============================
Wrapper script for Windows Task Scheduler that adds proper logging,
error handling, and notifications.
"""

import sys
import os
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Setup paths
PROJECT_DIR = Path(__file__).parent

# Try venv python first, fall back to system python
_venv_python = PROJECT_DIR / "venv" / "Scripts" / "python.exe"
if _venv_python.exists():
    PYTHON_EXE = _venv_python
else:
    import shutil
    PYTHON_EXE = Path(shutil.which("python") or "python.exe")
    print(f"  ⚠️  Venv python not found at {_venv_python}, using system: {PYTHON_EXE}")

MAIN_SCRIPT = PROJECT_DIR / "main.py"
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Setup logging
log_file = LOG_DIR / f"pinterest_bot_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def run_bot(args: list, task_name: str = "scheduled") -> int:
    """Run the bot with given arguments and return exit code."""
    cmd = [str(PYTHON_EXE), str(MAIN_SCRIPT)] + args
    logger.info(f"[{task_name}] Starting: {' '.join(cmd)}")
    
    try:
        # Run with timeout (2 hours max)
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=7200,  # 2 hours
            encoding="utf-8",
            errors="replace"
        )
        
        # Log stdout
        for line in result.stdout.strip().split('\n'):
            if line:
                logger.info(f"[{task_name}] {line}")
        
        # Log stderr if any
        if result.stderr:
            for line in result.stderr.strip().split('\n'):
                if line:
                    logger.warning(f"[{task_name}] STDERR: {line}")
        
        if result.returncode == 0:
            logger.info(f"[{task_name}] Completed successfully")
        else:
            logger.error(f"[{task_name}] Failed with exit code {result.returncode}")
        
        return result.returncode
        
    except subprocess.TimeoutExpired:
        logger.error(f"[{task_name}] TIMEOUT - process exceeded 2 hours")
        return 124
    except Exception as e:
        logger.error(f"[{task_name}] Exception: {e}")
        return 1


def main():
    """Main entry point for scheduled runs."""
    if len(sys.argv) < 2:
        print("Usage: python scheduled_runner.py <task_name> [args...]")
        print("Tasks: morning, lunch, evening, night, weekly-refill")
        sys.exit(1)
    
    task = sys.argv[1].lower()
    extra_args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    task_configs = {
        "morning": (["--count", "20"], "Morning Run (7 AM)"),
        "lunch": (["--count", "15"], "Lunch Run (12 PM)"),
        "evening": (["--count", "20"], "Evening Run (7 PM)"),
        "night": (["--count", "10"], "Night Run (11 PM)"),
        "weekly-refill": (["refill-trending"], "Weekly Trending Refill (Sunday 3 AM)"),
    }
    
    if task not in task_configs:
        logger.error(f"Unknown task: {task}")
        sys.exit(1)
    
    args, description = task_configs[task]
    # Create a NEW list — do NOT mutate the config tuple in-place (args.extend
    # would modify the original list stored in the dict, causing it to grow
    # on every invocation with extra_args)
    args = [*args, *extra_args]
    
    logger.info("=" * 60)
    logger.info(f"  {description}")
    logger.info("=" * 60)
    
    exit_code = run_bot(args, task)
    
    logger.info("=" * 60)
    logger.info(f"  {description} - Exit code: {exit_code}")
    logger.info("=" * 60)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()