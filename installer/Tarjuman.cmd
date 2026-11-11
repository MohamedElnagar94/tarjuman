@echo off
rem Tarjuman, installed: starts the app with the Python that came with it.
rem Your videos, settings and .env live in %LOCALAPPDATA%\Tarjuman, apart from the program,
rem so an update or a reinstall never touches them.
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if not defined TARJUMAN_HOME set "TARJUMAN_HOME=%LOCALAPPDATA%\Tarjuman"
if not exist "%TARJUMAN_HOME%" mkdir "%TARJUMAN_HOME%"
if not exist "%TARJUMAN_HOME%\.env" copy /y ".env.example" "%TARJUMAN_HOME%\.env" >nul

if not exist "%TARJUMAN_HOME%\data\models\piper\*.onnx" (
  echo.
  echo   First run: downloading the offline Arabic voice, about 60 MB...
  "python\python.exe" -m tarjuman setup --voice-only
)

"python\python.exe" -m tarjuman %*
if errorlevel 1 pause
