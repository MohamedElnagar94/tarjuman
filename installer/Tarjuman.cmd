@echo off
rem Tarjuman, installed, in a console: for the command line and for troubleshooting.
rem The Start menu shortcut opens the app in its own window instead (pythonw -m tarjuman app).
rem   Tarjuman.cmd            start the server and open the browser
rem   Tarjuman.cmd app        the desktop window, with messages shown here
rem   Tarjuman.cmd doctor     check every component
rem   Tarjuman.cmd update     update yt-dlp and the voice client
rem Your videos, settings and .env live in %LOCALAPPDATA%\Tarjuman, apart from the program.
setlocal
chcp 65001 >nul
cd /d "%~dp0"
"python\python.exe" -m tarjuman %*
if errorlevel 1 pause
