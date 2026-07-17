@echo off
REM ============================================
REM MOKABot Windows Task Uninstall Script
REM ============================================

set "TASK_NAME=MOKABot_Trading_Bridge"

echo.
echo ========================================
echo   MOKABot Windows Task Removal
echo ========================================
echo.

REM Check if task exists
schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Task "%TASK_NAME%" does not exist.
    echo Nothing to remove.
    pause
    exit /b 0
)

REM Stop the task if running
echo [INFO] Stopping bot if running...
schtasks /end /tn "%TASK_NAME%" >nul 2>&1

REM Delete the task
echo [INFO] Removing task: %TASK_NAME%
schtasks /delete /tn "%TASK_NAME%" /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo   [SUCCESS] Task removed successfully!
    echo ========================================
    echo.
    echo The bot will no longer start automatically.
    echo You can still run it manually with:
    echo   cd C:\Moss\Development\MOKABotTRADE
    echo   python mt5_bridge_multi.py
    echo.
) else (
    echo.
    echo [ERROR] Failed to remove task.
    echo Please run this script as Administrator.
    echo.
)

pause
