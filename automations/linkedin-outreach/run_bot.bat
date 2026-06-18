@echo off
echo ==============================================
echo Starting LinkedIn Outreach Bot Scheduled Run...
echo ==============================================
@REM Canonical project home (consolidated 2026-06-14)
cd /d "D:\Proposals\Jarvis\automations\linkedin-outreach"

@REM Try conda env first, fallback to system Python
where conda >nul 2>&1
if %errorlevel% equ 0 (
    conda run -n linkedin-outreach python main.py
) else (
    python main.py
)
