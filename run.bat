@echo off
setlocal
title C: Drive Large File Finder and Ranker
cd /d "%~dp0"

echo ====================================================================
echo           C: DRIVE DISK SPACE ANALYZER ^& FILE CLEANER
echo ====================================================================
echo.

:: Check for Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your Windows PATH.
    echo Please install Python 3 from https://www.python.org/downloads/
    echo and make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Check for pywin32
python -c "import win32com.client" >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Installing required pywin32 library for Windows shortcuts...
    python -m pip install --quiet pywin32
)

echo [*] Launching analyzer and starting Drive C: scan...
python "app.py"

if %errorlevel% neq 0 (
    echo.
    echo [!] Program exited with an error.
    pause
)
