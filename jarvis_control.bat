@echo off
REM =============================================================================
REM JARVIS Automations Control Panel
REM =============================================================================
REM Easy way to start, stop, run, and check your automations.
REM
REM Usage:
REM   jarvis_control.bat status          Show all tasks and their state
REM   jarvis_control.bat start           Enable all scheduled tasks
REM   jarvis_control.bat stop            Disable all scheduled tasks (pauses scheduling)
REM   jarvis_control.bat run <name>      Run a specific automation NOW
REM   jarvis_control.bat log <name>      Show last 20 lines of its log
REM
REM Names:
REM   pinterest-morning / pinterest-lunch / pinterest-evening
REM   job-automation / daily-morning / daily-evening
REM   linkedin / interview / junction
REM
REM Run as Administrator.
REM =============================================================================

setlocal EnableExtensions

set "TASKS=PinterestBot_Morning PinterestBot_Lunch PinterestBot_Evening JobAutomation_Daily DailyReport_Morning DailyReport_Evening LinkedInBot_Daily InterviewEmailListener PromoteJarvisJunction"

if "%1"=="" goto :menu
if /i "%1"=="status" goto :status
if /i "%1"=="start" goto :start_all
if /i "%1"=="stop" goto :stop_all
if /i "%1"=="enable" goto :start_all
if /i "%1"=="disable" goto :stop_all
if /i "%1"=="on" goto :start_all
if /i "%1"=="off" goto :stop_all
if /i "%1"=="run" goto :run_one
if /i "%1"=="log" goto :show_log
if /i "%1"=="help" goto :menu

:menu
echo ================================================================================
echo   JARVIS AUTOMATION CONTROL PANEL
echo ================================================================================
echo.
echo Commands:
echo   jarvis_control.bat status          - Show all tasks and their state
echo   jarvis_control.bat start           - Enable all scheduled tasks
echo   jarvis_control.bat stop            - Disable all scheduled tasks (pauses scheduling)
echo   jarvis_control.bat run ^<name^>      - Run a specific automation NOW
echo   jarvis_control.bat log ^<name^>      - Show recent log entries
echo.
echo Automation names:
echo   pinterest-morning    - 08:00 AM  (3 daily posts)
echo   pinterest-lunch      - 12:30 PM  (3 daily posts)
echo   pinterest-evening    - 08:00 PM  (3 daily posts)
echo   job-automation       - 09:00 AM  (scrape + auto-apply)
echo   daily-morning        - 09:00 AM  (morning brief email)
echo   daily-evening        - 06:00 PM  (evening summary email)
echo   linkedin             - 10:00 AM  (LinkedIn outreach)
echo   interview            - at logon  (email listener - hidden)
echo   junction             - at logon  (C: to D: junction creator)
echo.
pause
exit /b 0

:status
echo ================================================================================
echo   AUTOMATION STATUS
echo ================================================================================
echo.
for %%T in (%TASKS%) do (
    echo --- %%T ---
    schtasks /query /tn "%%T" /fo list /v 2>nul | findstr /C:"Next Run Time" /C:"Status" /C:"Start Time" /C:"Last Run Time" /C:"Last Result" /C:"Task To Run"
    echo.
)
pause
exit /b 0

:start_all
echo Enabling all automation tasks...
for %%T in (%TASKS%) do (
    schtasks /change /tn "%%T" /enable >nul 2>&1 && echo   [OK] %%T enabled || echo   [FAIL] %%T
)
echo.
echo All tasks enabled.
pause
exit /b 0

:stop_all
echo Disabling all automation tasks (schedule paused)...
for %%T in (%TASKS%) do (
    schtasks /change /tn "%%T" /disable >nul 2>&1 && echo   [OK] %%T disabled || echo   [FAIL] %%T
)
echo.
echo All tasks disabled. Tasks will NOT run on schedule until re-enabled.
echo PromoteJarvisJunction will still run at next logon (required for junction).
pause
exit /b 0

:run_one
if "%2"=="" (
    echo Usage: jarvis_control.bat run ^<name^>
    echo Names: pinterest-morning, pinterest-lunch, pinterest-evening, job-automation,
    echo        daily-morning, daily-evening, linkedin, interview, junction
    pause
    exit /b 1
)
call :resolve_task %2
if errorlevel 1 exit /b 1

echo Running %2 now (Task: %RESOLVED_NAME%)...
schtasks /run /tn "%RESOLVED_NAME%"
if errorlevel 1 (
    echo [FAIL] Could not start task.
    pause
    exit /b 1
)
echo Started. Check logs in D:\Proposals\Jarvis\automa...
pause
exit /b 0

:show_log
if "%2"=="" (
    echo Usage: jarvis_control.bat log ^<name^>
    pause
    exit /b 1
)
call :resolve_log %2
if errorlevel 1 exit /b 1

echo ================================================================================
echo   RECENT LOG: %2
echo   File: %LOG_PATH%
echo ================================================================================
if not exist "%LOG_PATH%" (
    echo No log yet for this automation.
    pause
    exit /b 1
)
powershell.exe -NoProfile -Command "Get-Content '%LOG_PATH%' -Tail 20"
pause
exit /b 0

:resolve_task
set "RESOLVED_NAME="
if /i "%~1"=="pinterest-morning" set "RESOLVED_NAME=PinterestBot_Morning"
if /i "%~1"=="pinterest-lunch"   set "RESOLVED_NAME=PinterestBot_Lunch"
if /i "%~1"=="pinterest-evening" set "RESOLVED_NAME=PinterestBot_Evening"
if /i "%~1"=="job-automation"   set "RESOLVED_NAME=JobAutomation_Daily"
if /i "%~1"=="daily-morning"    set "RESOLVED_NAME=DailyReport_Morning"
if /i "%~1"=="daily-evening"    set "RESOLVED_NAME=DailyReport_Evening"
if /i "%~1"=="linkedin"         set "RESOLVED_NAME=LinkedInBot_Daily"
if /i "%~1"=="interview"        set "RESOLVED_NAME=InterviewEmailListener"
if /i "%~1"=="junction"         set "RESOLVED_NAME=PromoteJarvisJunction"
if "%RESOLVED_NAME%"=="" (
    echo Unknown automation: "%~1"
    echo Try: pinterest-morning, pinterest-lunch, pinterest-evening, job-automation,
    echo       daily-morning, daily-evening, linkedin, interview, junction
    exit /b 1
)
exit /b 0

:resolve_log
set "LOG_PATH="
if /i "%~1"=="pinterest-morning" set "LOG_PATH=D:\Proposals\Jarvis\automations\pinterest\logs\pinterest_bot_%DATE:~-4%%DATE:~-10,2%%DATE:~-7,2%.log"
if /i "%~1"=="pinterest-lunch"   set "LOG_PATH=D:\Proposals\Jarvis\automations\pinterest\logs\pinterest_bot_%DATE:~-4%%DATE:~-10,2%%DATE:~-7,2%.log"
if /i "%~1"=="pinterest-evening" set "LOG_PATH=D:\Proposals\Jarvis\automations\pinterest\logs\pinterest_bot_%DATE:~-4%%DATE:~-10,2%%DATE:~-7,2%.log"
if /i "%~1"=="job-automation"    set "LOG_PATH=D:\Proposals\Jarvis\automations\job-automation\output\logs\job_pipeline.log"
if /i "%~1"=="daily-morning"     set "LOG_PATH=D:\Proposals\Jarvis\logs\daily_report.log"
if /i "%~1"=="daily-evening"     set "LOG_PATH=D:\Proposals\Jarvis\logs\daily_report.log"
if /i "%~1"=="linkedin"          set "LOG_PATH=D:\Proposals\Jarvis\automations\linkedin-outreach\sent_log.jsonl"
if "%LOG_PATH%"=="" (
    echo No log path mapped for "%~1" (may run hidden - check Task Scheduler history).
    exit /b 1
)
exit /b 0
