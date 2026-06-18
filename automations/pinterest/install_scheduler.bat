@echo off
REM ============================================================
REM Pinterest + TikTok + Reels Bot — Task Scheduler Installer
REM ============================================================
REM Right-click this file → "Run as administrator"
REM
REM Creates 4 daily tasks:
REM   - PinterestBot_Morning @ 08:00 (before classes) → Pinterest
REM   - PinterestBot_Lunch   @ 12:30 (study break)    → Pinterest
REM   - PinterestBot_Evening @ 20:00 (homework time)  → Pinterest
REM   - CrossPostBot_Night   @ 22:00 (prime scroller) → TikTok + Reels + Bio refresh
REM ============================================================

echo.
echo ============================================================
echo    Multi-Platform Bot — Task Scheduler Setup
echo ============================================================
echo.

REM Check for admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] This script must be run as Administrator!
    echo  Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

REM Set paths
set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=%SCRIPT_DIR%venv\Scripts\python.exe"
set "WORK_DIR=%SCRIPT_DIR%"

REM Verify Python exists
if not exist "%PYTHON_EXE%" (
    echo  [ERROR] Python venv not found at: %PYTHON_EXE%
    echo  Expected: %SCRIPT_DIR%venv\Scripts\python.exe
    pause
    exit /b 1
)

echo  Using Python: %PYTHON_EXE%
echo  Working dir:  %WORK_DIR%
echo.

REM ── Pinterest morning ──
echo  Creating PinterestBot_Morning @ 08:00 (5 Pinterest pins)...
schtasks /delete /tn "PinterestBot_Morning" /f >nul 2>&1
schtasks /create /tn "PinterestBot_Morning" /tr "\"%PYTHON_EXE%\" -m main --count 5" /sc daily /st 08:00 /rl highest /f
if %errorlevel% equ 0 (echo    [OK]) else (echo    [FAILED])

REM ── Pinterest lunch ──
echo  Creating PinterestBot_Lunch @ 12:30 (5 Pinterest pins)...
schtasks /delete /tn "PinterestBot_Lunch" /f >nul 2>&1
schtasks /create /tn "PinterestBot_Lunch" /tr "\"%PYTHON_EXE%\" -m main --count 5" /sc daily /st 12:30 /rl highest /f
if %errorlevel% equ 0 (echo    [OK]) else (echo    [FAILED])

REM ── Pinterest evening ──
echo  Creating PinterestBot_Evening @ 20:00 (5 Pinterest pins)...
schtasks /delete /tn "PinterestBot_Evening" /f >nul 2>&1
schtasks /create /tn "PinterestBot_Evening" /tr "\"%PYTHON_EXE%\" -m main --count 5" /sc daily /st 20:00 /rl highest /f
if %errorlevel% equ 0 (echo    [OK]) else (echo    [FAILED])

REM ── Bio page refresh morning ──
echo  Creating BioRefreshBot_Morning @ 07:00 (refresh bio page + trending)...
schtasks /delete /tn "BioRefreshBot_Morning" /f >nul 2>&1
schtasks /create /tn "BioRefreshBot_Morning" /tr "\"%PYTHON_EXE%\" -m main bio" /sc daily /st 07:00 /rl highest /f
if %errorlevel% equ 0 (echo    [OK]) else (echo    [FAILED])

echo.
echo ============================================================
echo  [DONE] Pinterest-only scheduler installed!
echo.
echo  Daily posting schedule:
echo    07:00  → Refresh bio page + product links
echo    08:00  → 5 Pinterest pins (before classes)
echo    12:30  → 5 Pinterest pins (lunch break)
echo    20:00  → 5 Pinterest pins (homework time)
echo    22:00  → 1 Instagram Reel (prime scrolling)
echo ============================================================
echo.
echo  Total per day (auto):
echo    •  15 Pinterest pins
echo    •   1 Instagram Reel
echo    •   Bio page auto-refreshed daily
echo.
echo  Verify in Task Scheduler GUI (taskschd.msc)
echo ============================================================
echo.
pause
