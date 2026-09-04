# This is a patch to fix the path issue in auto_applier.py
# The issue is that the script is trying to access Windows paths that don't exist in the WSL/Linux-like environment

from pathlib import Path

# Fix the session directory path to use the correct WSL path
def fix_session_path():
    """Ensure session directory uses correct path"""
    # Use the WSL path that we know exists
    base_path = Path("/home/venu/.jarvis")
    sessions_path = base_path / "automations" / "job-automation" / ".sessions"
    sessions_path.mkdir(parents=True, exist_ok=True)
    return sessions_path

# Apply the fix at module load time
fix_session_path()