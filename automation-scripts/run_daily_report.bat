@echo off
REM Daily email report launcher.
REM Passes --mode morning|evening (etc.) through to daily_report.py.
REM JARVIS_HOME resolution: process env > registry > D:\Proposals\Jarvis > D:\Venu\jarvis > C:\Users\Venu\.jarvis
REM Python resolution: Python39 first (matches all other JARVIS launchers), then Miniconda, then PATH.
REM Used by TWO scheduled tasks:
REM   - Morning Brief: 09:00 IST daily
REM   - Evening Report: 18:00 IST daily
REM Telegram removed 2026-06-16 — this now sends email only.

setlocal EnableExtensions EnableDelayedExpansion

REM 1. Read JARVIS_HOME from User registry (set during Hermes / JARVIS profile install)
for /f "tokens=*" %%A in ('powershell.exe -NoProfile -Command "[Environment]::GetEnvironmentVariable('JARVIS_HOME','User')"') do set "REG_JARVIS_HOME=%%A"

REM 2. Resolve JARVIS_HOME — first valid candidate wins.
set "JARVIS_HOME="

REM 2a. Process-level env (highest priority)
if defined JARVIS_HOME (
    if exist "%JARVIS_HOME%\daily_report.py" goto :jarvis_known
)
REM 2b. Registry
if defined REG_JARVIS_HOME (
    if exist "%REG_JARVIS_HOME%\daily_report.py" (
        set "JARVIS_HOME=%REG_JARVIS_HOME%"
        goto :jarvis_known
    )
)
REM 2c. Try common locations in order
for %%P in (D:\Proposals\Jarvis D:\Venu\jarvis C:\Users\Venu\.jarvis) do (
    if "!JARVIS_HOME!"=="" if exist "%%~P\daily_report.py" set "JARVIS_HOME=%%~P"
)

:jarvis_known
if "%JARVIS_HOME%"=="" goto :fatal_no_jarvis

REM 3. Pick Python interpreter — prefer Python 3.9 for consistency
set "PYTHON_EXE="
for %%P in (D:\Programs\Python39\python.exe D:\Programs\Miniconda3\python.exe) do (
    if "!PYTHON_EXE!"=="" if exist "%%~P" set "PYTHON_EXE=%%~P"
)
if "%PYTHON_EXE%"=="" (
    for /f "tokens=*" %%Q in ('where python 2^>nul') do (
        if "!PYTHON_EXE!"=="" set "PYTHON_EXE=%%Q"
    )
)
if "%PYTHON_EXE%"=="" goto :fatal_no_python

REM 4. Export for daily_report.py (it reads JARVIS_HOME for path resolution).
REM Co-located: the repo at JARVIS_HOME IS the OPENCLAW_HOME / automations root.
set "JARVIS_HOME=%JARVIS_HOME%"
set "OPENCLAW_HOME=%JARVIS_HOME%"

REM 5. Ensure logs dir
if not exist "%JARVIS_HOME%\logs" mkdir "%JARVIS_HOME%\logs" 2>nul

REM 6. Run
REM Note: do NOT use "> > log.txt" redirect — Windows file sharing conflicts
REM with Python's "a"-mode open of the same file. daily_report.py writes
REM to %JARVIS_HOME%\logs\daily_report.log itself.
echo [%DATE% %TIME%] JDR_DAILY: JARVIS_HOME=%JARVIS_HOME% PYTHON=%PYTHON_EXE% ARGS=%*
"%PYTHON_EXE%" "%JARVIS_HOME%\daily_report.py" %*
set "RC=%ERRORLEVEL%"
echo [%DATE% %TIME%] JDR_DAILY_DONE: rc=%RC%

endlocal & exit /b %RC%

:fatal_no_jarvis
echo [run_daily_report.bat] FATAL: cannot locate daily_report.py under any known JARVIS_HOME
echo Tried: registry=%REG_JARVIS_HOME%, D:\Proposals\Jarvis, D:\Venu\jarvis, C:\Users\Venu\.jarvis
exit /b 2

:fatal_no_python
echo [run_daily_report.bat] FATAL: no Python interpreter found
exit /b 3
