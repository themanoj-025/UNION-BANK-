@echo off
title Union Bank - Running Tests
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   UNION BANK - Running Test Suite...     ║
echo  ╚══════════════════════════════════════════╝
echo.

REM --- Check if Python is installed ---
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [!] Python is not installed or not in PATH.
    echo      Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM --- Create virtual environment if missing ---
if not exist "venv\" (
    echo  [*] Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo  [!] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  [+] Virtual environment created.
) else (
    echo  [*] Virtual environment found.
)

echo.

REM --- Activate virtual environment ---
call venv\Scripts\activate.bat

REM --- Install dependencies ---
echo  [*] Installing dependencies...
pip install -r requirements.txt -q
if %ERRORLEVEL% neq 0 (
    echo  [!] Failed to install dependencies.
    pause
    exit /b 1
)
echo  [+] Dependencies installed.

echo.

REM --- Run tests with coverage (single pass) ---
echo  [*] Running tests...
echo.
python -m pytest tests/ -v --cov --cov-report=term --cov-report=html
set TEST_EXIT=%ERRORLEVEL%

echo.
if %TEST_EXIT% equ 0 (
    echo  [v] All tests passed!
) else (
    echo  [!] Some tests failed (exit code: %TEST_EXIT%).
)

echo.
echo  [*] Coverage report saved to htmlcov\index.html
echo  [*] Press any key to close this window.
pause >nul
exit /b %TEST_EXIT%
