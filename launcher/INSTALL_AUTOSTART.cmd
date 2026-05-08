@echo off
title Sim Racing Challenges - Install Auto-start
echo.
echo ============================================================
echo   INSTALLING AUTO-START FOR LAUNCH BAY
echo ============================================================
echo   This creates a Windows startup shortcut so the local
echo   agent server starts automatically when you log in.
echo.
echo   No more "server down" messages.
echo.
echo   This script does NOT need admin rights.
echo ============================================================
echo.

REM Build a silent-launch wrapper that starts the server in the background
REM with no visible cmd window using PowerShell.
set "TARGET=%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%TARGET%\SimRacingChallenges-Agent.lnk"
set "CMD=%~dp0LAUNCH_BAY_BACKGROUND.cmd"

REM Write the silent background launcher
> "%CMD%" echo @echo off
>> "%CMD%" echo REM Background launcher — runs server with no window. Logs to launchbay.log.
>> "%CMD%" echo start "" /b wsl -d Ubuntu -e bash -lc "nohup python3 '/mnt/c/Users/pablo/Documents/Assetto Corsa/launcher/launcher_dashboard.py' --no-browser ^> /tmp/launchbay.log 2^>^&1 ^&"

REM Create the Startup-folder shortcut
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%SHORTCUT%'); $sc.TargetPath = '%CMD%'; $sc.WorkingDirectory = '%~dp0'; $sc.WindowStyle = 7; $sc.Description = 'Sim Racing Challenges agent server'; $sc.Save()"

if exist "%SHORTCUT%" (
    echo [OK]  Startup shortcut created:
    echo       %SHORTCUT%
    echo.
    echo The agent will now auto-start every time you log in.
    echo Server URL: http://localhost:8765/
    echo Log file: \\wsl$\Ubuntu\tmp\launchbay.log
    echo.
    echo To remove auto-start later: delete the shortcut above
    echo or run UNINSTALL_AUTOSTART.cmd.
) else (
    echo [FAIL] Could not create shortcut. Run this from Windows
    echo        Explorer ^(double-click^) — not from a network share.
)

echo.
pause
