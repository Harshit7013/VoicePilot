@echo off
title VoicePilot Frontend

cd apps\desktop
:loop
echo Starting Vite Frontend...
npm run dev
echo Frontend exited. Restarting in 3 seconds...
timeout /t 3 >nul
goto loop
