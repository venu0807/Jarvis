@echo off
REM ============================================================
REM Pinterest Affiliate Bot - Windows Task Scheduler Setup
REM ============================================================
REM This script creates scheduled tasks to run the bot at optimal times:
REM   - 7:00 AM  (Morning - before class)
REM   - 12:00 PM (Lunch - study break)
REM   - 7:00 PM  (Evening - homework time)
REM   - 11:00 PM (Late night - scrolling before bed)
REM
REM Run this script AS ADMINISTRATOR to create the tasks.
REM ============================================================

SET PROJECT_DIR=D:\Proposals\Jarvis\automations\pinterest
SET PYTHON_EXE=%PROJECT_DIR%\venv\Scripts\python.exe
SET RUNNER=%PROJECT_DIR%\scheduled_runner.py
SET LOG_DIR=%PROJECT_DIR%\logs

REM Create logs directory
IF NOT EXIST "%LOG_DIR%" MKDIR "%LOG_DIR%"

ECHO Creating scheduled tasks for Pinterest Affiliate Bot...
ECHO Project: %PROJECT_DIR%
ECHO Python: %PYTHON_EXE%
ECHO Runner: %RUNNER%
ECHO.

REM Task 1: Morning (7:00 AM)
SCHTASKS /CREATE /TN "PinterestBot_Morning" ^
    /TR "\"%PYTHON_EXE%\" \"%RUNNER%\" morning" ^
    /SC DAILY /ST 07:00 ^
    /F /RL HIGHEST ^
    /IT

REM Task 2: Lunch (12:00 PM)
SCHTASKS /CREATE /TN "PinterestBot_Lunch" ^
    /TR "\"%PYTHON_EXE%\" \"%RUNNER%\" lunch" ^
    /SC DAILY /ST 12:00 ^
    /F /RL HIGHEST ^
    /IT

REM Task 3: Evening (7:00 PM)
SCHTASKS /CREATE /TN "PinterestBot_Evening" ^
    /TR "\"%PYTHON_EXE%\" \"%RUNNER%\" evening" ^
    /SC DAILY /ST 19:00 ^
    /F /RL HIGHEST ^
    /IT

REM Task 4: Late Night (11:00 PM)
SCHTASKS /CREATE /TN "PinterestBot_Night" ^
    /TR "\"%PYTHON_EXE%\" \"%RUNNER%\" night" ^
    /SC DAILY /ST 23:00 ^
    /F /RL HIGHEST ^
    /IT

REM Task 5: Weekly refill with trending products (Sunday 3:00 AM)
SCHTASKS /CREATE /TN "PinterestBot_WeeklyRefill" ^
    /TR "\"%PYTHON_EXE%\" \"%RUNNER%\" weekly-refill" ^
    /SC WEEKLY /D SUN /ST 03:00 ^
    /F /RL HIGHEST ^
    /IT

ECHO.
ECHO ============================================================
ECHO All tasks created successfully!
ECHO ============================================================
ECHO.
ECHO To view tasks:    SCHTASKS /QUERY /TN "PinterestBot_*" /V /FO LIST
ECHO To run manually:  SCHTASKS /RUN /TN "PinterestBot_Morning"
ECHO To delete all:    SCHTASKS /DELETE /TN "PinterestBot_*" /F
ECHO.
ECHO Logs will be in: %LOG_DIR%
ECHO.
PAUSE