#!/usr/bin/env python3
"""
Jarvis Quick Setup — guided setup for ₹15k service clients.
Run: python quick_setup.py
"""
import os
import subprocess
import sys
import shlex
from pathlib import Path

BASE = Path(__file__).parent

def step(num, title, command=None):
    print(f"\n{'='*60}")
    print(f"  Step {num}: {title}")
    print(f"{'='*60}")
    if command:
        if isinstance(command, str):
            command = shlex.split(command)
        result = subprocess.run(command, shell=False, cwd=BASE)
        if result.returncode != 0:
            print(f"  ⚠️  Step {num} had issues. Check above.")

def main():
    print("""
    🦞 JARVIS QUICK SETUP
    =====================
    This will install everything needed to run job automation.
    """)

    input("Press Enter to start setup (laptop must have 8GB+ RAM)...")

    # Python version
    py = sys.executable
    print(f"  Using Python: {py}")

    # Step 1: Install Python deps
    step(1, "Installing Python dependencies (Playwright, Ollama client, etc.)",
         f'"{py}" -m pip install -r automations/job-automation/requirements.txt')

    # Step 2: Install Playwright browsers
    step(2, "Installing Playwright browsers (Chromium ~150MB)",
         f'"{py}" -m playwright install chromium')

    # Step 3: Check Ollama
    print(f"\n{'='*60}")
    print("  Step 3: Checking Ollama")
    print(f"{'='*60}")
    ollama_check = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
    if ollama_check.returncode == 0:
        print(f"  ✅ Ollama found: {ollama_check.stdout.strip()}")
    else:
        print("  ⚠️  Ollama not found.")
        print("  Download from: https://ollama.com/download")
        print("  After installing, run: ollama pull phi4-mini")
        input("  Press Enter after installing Ollama...")

    # Step 4: Ensure Ollama model
    step(4, "Pulling AI model (phi4-mini ~2.5GB, first-time download)",
         "ollama pull phi4-mini")

    # Step 5: Config
    print(f"\n{'='*60}")
    print("  Step 5: Configuration")
    print(f"{'='*60}")
    print("  You need to provide:")
    print("    1. Naukri/Internshala/Indeed login credentials")
    print("    2. Gmail app password (for daily reports)")
    print()
    print("  Edit .env.example → rename to .env")
    print(f"  File location: {BASE / '.env.example'}")
    print()
    input("  Press Enter after configuring .env...")

    # Step 6: Test run
    print(f"\n{'='*60}")
    print("  Setup complete! Ready for test run.")
    print(f"{'='*60}")
    print()
    print("  Start daily pipeline:")
    print(f"    cd {BASE}")
    print('    python automations/job-automation/run_pipeline.py')
    print()
    print("  Or auto-apply only (recommended first test):")
    print(f'    cd {BASE}')
    print('    python automations/job-automation/auto_applier.py')
    print()

if __name__ == "__main__":
    main()
