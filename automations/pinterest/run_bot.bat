@echo off
REM ============================================================
REM Pinterest Affiliate Bot - Quick Run Commands
REM ============================================================
REM Run this file directly for quick commands
REM ============================================================

SET PROJECT_DIR=D:\Proposals\Jarvis\automations\pinterest
SET PYTHON_EXE=%PROJECT_DIR%\venv\Scripts\python.exe
SET RUNNER=%PROJECT_DIR%\scheduled_runner.py

ECHO Pinterest Affiliate Bot - Quick Commands
ECHO ========================================
ECHO.
ECHO 1. Run once (20 pins)
ECHO 2. Run once with trending refill
ECHO 3. Run morning batch (20 pins)
ECHO 4. Run lunch batch (15 pins)
ECHO 5. Run evening batch (20 pins)
ECHO 6. Run night batch (10 pins)
ECHO 7. Weekly trending refill
ECHO 8. Show stats
ECHO 9. View logs
ECHO 0. Exit
ECHO.

SET /P CHOICE="Enter choice [0-9]: "

IF "%CHOICE%"=="1" (
    "%PYTHON_EXE%" "%PROJECT_DIR%\main.py" --count 20
)
IF "%CHOICE%"=="2" (
    "%PYTHON_EXE%" "%PROJECT_DIR%\main.py" refill-trending
    "%PYTHON_EXE%" "%PROJECT_DIR%\main.py" --count 20
)
IF "%CHOICE%"=="3" (
    "%PYTHON_EXE%" "%RUNNER%" morning
)
IF "%CHOICE%"=="4" (
    "%PYTHON_EXE%" "%RUNNER%" lunch
)
IF "%CHOICE%"=="5" (
    "%PYTHON_EXE%" "%RUNNER%" evening
)
IF "%CHOICE%"=="6" (
    "%PYTHON_EXE%" "%RUNNER%" night
)
IF "%CHOICE%"=="7" (
    "%PYTHON_EXE%" "%RUNNER%" weekly-refill
)
IF "%CHOICE%"=="8" (
    "%PYTHON_EXE%" "%PROJECT_DIR%\main.py" stats
)
IF "%CHOICE%"=="9" (
    NOTEPAD "%PROJECT_DIR%\logs\pinterest_bot_%DATE:~-4,4%%DATE:~-10,2%%DATE:~-7,2%.log"
)
IF "%CHOICE%"=="0" (
    EXIT
)

ECHO.
PAUSE