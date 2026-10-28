@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" app.py
  if errorlevel 1 pause
  exit /b
)
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 app.py
) else (
  python app.py
)
if errorlevel 1 pause

