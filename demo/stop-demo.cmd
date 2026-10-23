@echo off
rem Double-click to stop the demo started by start-demo.cmd.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-demo.ps1"
echo.
pause
