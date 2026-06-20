@echo off
echo ==============================================
echo Starting LinkedIn Outreach Bot Scheduled Run...
echo ==============================================
@REM Canonical project home (consolidated 2026-06-14)
cd /d "D:\Proposals\Jarvis\automations\linkedin-outreach"

@REM Try conda env first, fallback to system Python
if exist "D:\Programs\Python39\python.exe" (
    "D:\Programs\Python39\python.exe" -u main.py
) else (
    python -u main.py
)
