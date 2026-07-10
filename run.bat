@echo off
setlocal
cd /d %~dp0

echo [1/3] Checking Python...
py -V >nul 2>nul
if %errorlevel% neq 0 (
    echo Python launcher 'py' not found. Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist .venv (
    echo [2/3] Creating virtual environment...
    py -m venv .venv
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo [3/3] Installing/checking dependencies...
call .venv\Scripts\python.exe -m pip install --upgrade pip
call .venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Dependency installation failed.
    pause
    exit /b 1
)

echo Launching app...
call .venv\Scripts\python.exe main.py
if %errorlevel% neq 0 (
    echo Application exited with error.
    pause
    exit /b %errorlevel%
)

endlocal
