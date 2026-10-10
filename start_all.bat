@echo off
title VoicePilot - Main Controller
echo Starting VoicePilot Backend and Frontend...

start "VoicePilot API Backend" cmd /c "start_backend.bat"
start "VoicePilot Frontend" cmd /c "start_frontend.bat"

echo Both services have been started in separate windows with auto-restart enabled!
echo You can close this main window safely.
pause
