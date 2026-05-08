@echo off
title SimRacingPitStop - Launch Bay
echo.
echo ============================================================
echo   SIMRACINGPITSTOP - LAUNCH BAY
echo ============================================================
echo.
echo   Server: http://localhost:8765/
echo   Browser opens automatically in ~3 seconds.
echo.
echo   Keep this window open. Ctrl+C (or close) to stop server.
echo ============================================================
echo.

REM Background helper: wait for server, then open browser via Windows.
start "" /MIN cmd /c "timeout /t 3 /nobreak >nul && start \"\" \"http://localhost:8765/\""

REM Server runs in this window so logs are visible.
wsl python3 "/mnt/c/Users/pablo/Documents/Assetto Corsa/launcher/launcher_dashboard.py" --no-browser

echo.
echo ============================================================
echo   Server stopped.
echo ============================================================
pause
