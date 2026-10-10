@echo off
title VoicePilot API Backend

:loop
echo Starting Python API Backend...
python -m agent.api
echo Backend exited or timed out. Restarting in 3 seconds...
timeout /t 3 >nul
goto loop
