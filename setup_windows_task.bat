@echo off
REM ============================================
REM MOKABot Windows Task Setup Script
REM ============================================
REM This script registers the MOKABot bridge as a Windows Scheduled Task
REM The bot will start automatically when you log in to Windows
REM ============================================

echo.
echo ========================================
echo   MOKABot Windows Task Setup
echo ========================================
echo.

REM Get the current directory
set "BOT_DIR=%~dp0"
set "BOT_SCRIPT=%BOT_DIR%mt5_bridge_multi.py"
set "TASK_NAME=MOKABot_Trading_Bridge"

REM Check if Python is installed
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python and try again.
    pause
    exit /b 1
)

REM Get Python path
for /f "delims=" %%i in ('where python') do set "PYTHON_PATH=%%i"
echo [INFO] Python found at: %PYTHON_PATH%
echo [INFO] Bot script: %BOT_SCRIPT%
echo.

REM Delete existing task if it exists
schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Removing existing task...
    schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
)

REM Create the scheduled task
echo [INFO] Creating Windows Task: %TASK_NAME%
echo.

schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "\"%PYTHON_PATH%\" \"%BOT_SCRIPT%\"" ^
    /sc ONLOGON ^
    /rl HIGHEST ^
    /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo   [SUCCESS] Task created successfully!
    echo ========================================
    echo.
    echo The bot will start automatically when you log in.
    echo.
    echo To run the bot NOW, use:
    echo   schtasks /run /tn "%TASK_NAME%"
    echo.
    echo To stop the bot, use:
    echo   schtasks /end /tn "%TASK_NAME%"
    echo.
    echo To delete the task, use:
    echo   schtasks /delete /tn "%TASK_NAME%" /f
    echo.
    echo Or run this script again with /uninstall flag:
    echo   setup_windows_task.bat /uninstall
    echo.
) else (
    echo.
    echo [ERROR] Failed to create task.
    echo Please run this script as Administrator.
    echo.
    echo Right-click on this file and select "Run as administrator"
    echo.
)

REM Check if user wants to run the bot now
echo.
set /p RUN_NOW="Do you want to start the bot now? (Y/N): "
if /i "%RUN_NOW%"=="Y" (
    echo.
    echo [INFO] Starting bot...
    schtasks /run /tn "%TASK_NAME%"
    echo [INFO] Bot started! Check Task Manager for python.exe
)

pause
