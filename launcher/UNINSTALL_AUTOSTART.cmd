@echo off
title Sim Racing Challenges - Remove Auto-start
echo.
echo ============================================================
echo   REMOVING AUTO-START
echo ============================================================
echo.

set "SHORTCUT=%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\SimRacingChallenges-Agent.lnk"

if exist "%SHORTCUT%" (
    del "%SHORTCUT%"
    echo [OK] Removed startup shortcut.
) else (
    echo [INFO] Startup shortcut wasn't there — nothing to do.
)

echo.
echo The agent will no longer auto-start at login.
echo To start it manually: double-click LAUNCH_BAY.cmd
echo.
pause
