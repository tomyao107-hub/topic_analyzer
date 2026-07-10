@echo off
setlocal
cd /d %~dp0

echo Starting frozen PySide6 v1 fallback...
if not exist .venv py -m venv .venv
call .venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 exit /b %errorlevel%
call .venv\Scripts\python.exe main.py
exit /b %errorlevel%
