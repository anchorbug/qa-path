@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" launcher.py start
  if errorlevel 1 pause
  exit /b
)
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 launcher.py start
) else (
  python launcher.py start
)
if errorlevel 1 pause

