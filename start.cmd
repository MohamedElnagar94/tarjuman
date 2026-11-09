@echo off
rem Tarjuman: double-click to start. The first run installs everything (a few minutes).
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo   First run: setting up Tarjuman...
  where py >nul 2>nul && (py -3.13 -m venv .venv 2>nul || py -3 -m venv .venv) || python -m venv .venv
  if not exist ".venv\Scripts\python.exe" (
    echo.
    echo   Python 3.11+ was not found. Install it from https://www.python.org/downloads/
    echo   and tick "Add python.exe to PATH", then run this file again.
    pause
    exit /b 1
  )
  set "PYTHONPATH=%~dp0backend"
  ".venv\Scripts\python.exe" -m tarjuman setup || (pause & exit /b 1)
)

set "PYTHONPATH=%~dp0backend"
".venv\Scripts\python.exe" -m tarjuman %*
if errorlevel 1 pause
