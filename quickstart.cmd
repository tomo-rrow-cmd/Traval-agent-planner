@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="
py -3.12 -c "import sys" >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3.12"

if not defined PYTHON_CMD (
    python -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo [ERROR] Python not found. Install Python 3.12 first.
    pause
    exit /b 1
)

%PYTHON_CMD% "scripts\quickstart.py" %*
set "EXIT_CODE=%errorlevel%"

echo.
if not "%EXIT_CODE%"=="0" echo [ERROR] quickstart exited with code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
