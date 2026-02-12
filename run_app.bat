@echo off
cd /d "%~dp0"
echo Starting File Organizer...
echo Opening Browser...
start http://127.0.0.1:8000
venv\Scripts\python.exe -m uvicorn app.main:app --reload
pause
