@echo off
cd /d "%~dp0"
echo Training API: http://127.0.0.1:8767/health
echo Keep this window open. Stop with Ctrl+C.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" training_api.py --open-browser
  if errorlevel 1 pause
  exit /b
)
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 training_api.py --open-browser
) else (
  python training_api.py --open-browser
)
if errorlevel 1 pause
