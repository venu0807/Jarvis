"""
Windows Task Scheduler Setup
=============================
Creates scheduled tasks to run the Pinterest bot automatically at optimal times.

Run this ONCE to set up:
  • Morning run: 8:00 AM (before classes)
  • Lunch run:   12:30 PM (study break)
  • Evening run: 8:00 PM (homework time)

Usage:
  python schedule_setup.py install   — Create scheduled tasks
  python schedule_setup.py remove    — Remove scheduled tasks
  python schedule_setup.py status    — Check task status
  python schedule_setup.py run-now   — Trigger a run immediately
"""

import os
import sys
import subprocess
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.absolute()

# Try venv python first, fall back to system python
_venv_python = SCRIPT_DIR / "venv" / "Scripts" / "python.exe"
if _venv_python.exists():
    PYTHON_EXE = _venv_python
else:
    import shutil
    PYTHON_EXE = Path(shutil.which("python") or "python.exe")
    print(f"  ⚠️  Venv python not found at {_venv_python}, using system: {PYTHON_EXE}")

MAIN_SCRIPT = SCRIPT_DIR / "main.py"
TASK_NAME_BASE = "PinterestBot"

# Optimal posting times for student audience
SCHEDULE_SLOTS = [
    {"name": "Morning",   "hour": 8,  "minute": 0,  "description": "Before classes"},
    {"name": "Lunch",     "hour": 12, "minute": 30, "description": "Study break"},
    {"name": "Evening",   "hour": 20, "minute": 0,  "description": "Homework time"},
]


def _check_python() -> bool:
    """Verify Python and main.py exist."""
    if not PYTHON_EXE.exists():
        print(f"  ❌ Python not found: {PYTHON_EXE}")
        print(f"     Expected venv at: {SCRIPT_DIR}\\venv")
        return False
    if not MAIN_SCRIPT.exists():
        print(f"  ❌ Main script not found: {MAIN_SCRIPT}")
        return False
    return True


def _run_schtasks(args: list) -> tuple:
    """Run schtasks command and return (returncode, stdout)."""
    try:
        result = subprocess.run(
            ["schtasks"] + args,
            capture_output=True, text=True, timeout=30
        )
        return result.returncode, result.stdout + result.stderr
    except Exception as e:
        return 1, str(e)


def install():
    """Create 3 scheduled tasks for optimal posting times."""
    print("\n" + "=" * 55)
    print("  📅  INSTALLING SCHEDULED TASKS")
    print("=" * 55)

    if not _check_python():
        return False

    for slot in SCHEDULE_SLOTS:
        task_name = f"{TASK_NAME_BASE}_{slot['name']}"
        time_str = f"{slot['hour']:02d}:{slot['minute']:02d}"

        print(f"\n  Creating task: {task_name} @ {time_str}")

        # Delete existing task first (idempotent)
        _run_schtasks(["/delete", "/tn", task_name, "/f"])

        # Create new task — runs daily at specified time
        cmd = [
            "/create",
            "/tn", task_name,
            "/tr", f'"{PYTHON_EXE}" -m main --count 5',
            "/sc", "daily",
            "/st", time_str,
            "/rl", "highest",       # Run with highest privileges
            "/f",                   # Force overwrite if exists
        ]

        code, output = _run_schtasks(cmd)
        if code == 0:
            print(f"  ✅ {slot['name']} slot installed ({slot['description']})")
        else:
            print(f"  ⚠️  Failed to create {task_name}: {output}")

    print("\n" + "=" * 55)
    print("  ✅ SCHEDULED TASKS INSTALLED!")
    print("  📊 Bot will auto-post at:")
    for slot in SCHEDULE_SLOTS:
        print(f"     • {slot['name']:8s} → {slot['hour']:02d}:{slot['minute']:02d} ({slot['description']})")
    print("=" * 55)
    print("\n  💡 Verify in Task Scheduler GUI → Taskschd.msc")
    print("     Look for: PinterestBot_Morning, _Lunch, _Evening")
    return True


def remove():
    """Remove all Pinterest bot scheduled tasks."""
    print("\n" + "=" * 55)
    print("  🗑️  REMOVING SCHEDULED TASKS")
    print("=" * 55)

    for slot in SCHEDULE_SLOTS:
        task_name = f"{TASK_NAME_BASE}_{slot['name']}"
        print(f"  Removing: {task_name}")
        code, output = _run_schtasks(["/delete", "/tn", task_name, "/f"])
        if code == 0:
            print(f"  ✅ Removed {task_name}")
        else:
            print(f"  ℹ️  {task_name} not found or already removed")

    print("=" * 55)
    return True


def status():
    """Show status of scheduled tasks."""
    print("\n" + "=" * 55)
    print("  📊  SCHEDULED TASK STATUS")
    print("=" * 55)

    for slot in SCHEDULE_SLOTS:
        task_name = f"{TASK_NAME_BASE}_{slot['name']}"
        print(f"\n  {slot['name']} ({slot['hour']:02d}:{slot['minute']:02d}):")
        code, output = _run_schtasks(["/query", "/tn", task_name, "/v", "/fo", "list"])
        if code == 0 and "ERROR" not in output:
            # Parse relevant lines
            for line in output.split("\n"):
                line = line.strip()
                if any(k in line for k in ["Status:", "Next Run Time:", "Last Run Time:"]):
                    print(f"    {line}")
        else:
            print("    ❌ Not installed")

    print("=" * 55)
    return True


def run_now():
    """Trigger the morning task immediately (for testing)."""
    print("\n  🚀 Triggering immediate run...")
    task_name = f"{TASK_NAME_BASE}_Morning"
    code, output = _run_schtasks(["/run", "/tn", task_name])
    if code == 0:
        print(f"  ✅ Triggered {task_name}")
        print(f"     Check main.py output or data.csv for results")
    else:
        print(f"  ⚠️  Failed: {output}")
        print(f"     Run manually: {PYTHON_EXE} -m main")
    return code == 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "install":
        install()
    elif cmd == "remove":
        remove()
    elif cmd == "status":
        status()
    elif cmd == "run-now":
        run_now()
    else:
        print(f"  Unknown command: {cmd}")
        print("  Usage: python schedule_setup.py [install|remove|status|run-now]")
