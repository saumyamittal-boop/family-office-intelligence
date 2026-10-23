@echo off
rem Double-click to start the demo. Everything it does is in start-demo.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-demo.ps1" %*
echo.
pause
demo\start-demo.cmd
