#!/usr/bin/env python3
"""Fix syntax errors in alert_triggers.py"""

with open('/home/venu/Proposals/Jarvis/automations/alert_triggers.py', 'r') as f:
    content = f.read()

# Fix check_disk_space function - the message block is corrupted
# Find the start of check_disk_space and fix the message
import re

# Pattern to find the broken disk space message
# It starts with "message=(" and has the broken "Free" duplicate lines
# We'll replace from the message=( to the closing ),
# But it's complex. Let's do a more targeted fix.

# Fix 1: Remove the duplicate/stray lines in check_disk_space
# The broken pattern has:
# f"Free: {disk.free // (1024**3)} GB{NL}"
# "
#     f"Free: {disk.free // (1024**3)} GB\n"
# "
#     f"Time: ...

# Find and replace this specific broken section
broken_disk = '''                        f"Free: {disk.free // (1024**3)} GB{NL}"
"
                            f"Free: {disk.free // (1024**3)} GB\n"
"
                            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"Immediate actions:\n"
                            f"1. Clean old backups: find /home/venu/backups -type f -mtime +30 -delete\n"
                            f"2. Clear pip cache: pip cache purge\n"
                            f"3. Clear npm cache: npm cache clean --force\n"
                            f"4. Check large files: du -sh /* | sort -hr | head -10\n"
                            f"5. Consider expanding disk space",
                    ),'''

fixed_disk = '''                        f"Free: {disk.free // (1024**3)} GB{NL}"
                        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}{NL}"
                        "Immediate actions:{NL}"
                        "1. Clean old backups: find /home/venu/backups -type f -mtime +30 -delete{NL}"
                        "2. Clear pip cache: pip cache purge{NL}"
                        "3. Clear npm cache: npm cache clean --force{NL}"
                        "4. Check large files: du -sh /* | sort -hr | head -10{NL}"
                        "5. Consider expanding disk space"
                    ),'''

if broken_disk in content:
    content = content.replace(broken_disk, fixed_disk)
    print("Fixed check_disk_space message block")
else:
    print("Broken disk pattern not found")

# Fix 2: Fix the ollama availability check message
broken_ollama = '''                    message=(                        "message=f"Ollama API is not responding correctly."                    ),
"
                            f"Status code: {response.status_code}\n"
"
                            f"Response: {response.text[:200] if response.text else 'No response'}\n"
"
                            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"Impact:\n"
                            f"- AI job classification will fail\n"
                            f"- Cover letter generation disabled\n"
                            f"- Resume tailoring unavailable\n"
                            f"- Interview preparation affected"""'''

fixed_ollama = '''                    message=(
                        "Ollama API is not responding correctly.{NL}{NL}"
                        f"Status code: {response.status_code}{NL}"
                        f"Response: {response.text[:200] if response.text else 'No response'}{NL}"
                        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}{NL}"
                        "Impact:{NL}"
                        "- AI job classification will fail{NL}"
                        "- Cover letter generation disabled{NL}"
                        "- Resume tailoring unavailable{NL}"
                        "- Interview preparation affected"
                    ),'''

if broken_ollama in content:
    content = content.replace(broken_ollama, fixed_ollama)
    print("Fixed check_ollama_availability message block")
else:
    print("Broken ollama pattern not found")

# Write back
with open('/home/venu/Proposals/Jarvis/automations/alert_triggers.py', 'w') as f:
    f.write(content)

print("Done fixing alert_triggers.py")