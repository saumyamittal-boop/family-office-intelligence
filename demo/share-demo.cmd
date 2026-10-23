@echo off
rem Double-click to share the demo behind a password. Everything it does is in share-demo.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0share-demo.ps1" %*
echo.
pause
