@echo off
setlocal
cd /d %~dp0

where npm.cmd >nul 2>nul
if %errorlevel% neq 0 (
    echo Node.js/npm not found. Install Node.js before starting the Tauri v2 desktop app.
    pause
    exit /b 1
)

where cargo.exe >nul 2>nul
if %errorlevel% neq 0 (
    echo Rust/cargo not found. Install Rust before starting the Tauri v2 desktop app.
    pause
    exit /b 1
)

if not exist .venv (
    py -m venv .venv
)
call .venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 exit /b %errorlevel%

cd desktop
if not exist node_modules call npm.cmd install
call npm.cmd run tauri dev
exit /b %errorlevel%
