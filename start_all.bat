@echo off
title VoicePilot - Main Controller
echo Starting VoicePilot Backend and Frontend...

:: Start the backend with auto-restart in a new window
start "VoicePilot API Backend" cmd /c "title VoicePilot API Backend && :loop && echo Starting Python API Backend... && python -m agent.api && echo Backend exited or timed out. Restarting in 3 seconds... && timeout /t 3 >nul && goto loop"

:: Start the frontend with auto-restart in a new window
start "VoicePilot Frontend" cmd /c "title VoicePilot Frontend && cd apps\desktop && :loop && echo Starting Vite Frontend... && npm run dev && echo Frontend exited. Restarting in 3 seconds... && timeout /t 3 >nul && goto loop"

echo Both services have been started in separate windows with auto-restart enabled!
echo You can close this main window safely.
pause
