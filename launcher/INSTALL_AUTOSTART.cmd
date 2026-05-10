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

REM Point the Startup-folder shortcut at the hidden .vbs launcher.
REM The .vbs invokes WSL with `exec python3 ...` in the foreground of the
REM WSL session — keeps the WSL2 VM alive so the server isn't idle-killed
REM ~60s after login (the failure mode of the previous `nohup ... &` setup).
set "TARGET=%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%TARGET%\SimRacingChallenges-Agent.lnk"
set "VBS=%~dp0SimRacingChallenges-Agent.vbs"

REM Create the Startup-folder shortcut targeting the .vbs (wscript runs hidden by default).
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%SHORTCUT%'); $sc.TargetPath = 'wscript.exe'; $sc.Arguments = '\"' + '%VBS%' + '\"'; $sc.WorkingDirectory = '%~dp0'; $sc.WindowStyle = 7; $sc.Description = 'Sim Racing Challenges agent server'; $sc.Save()"

if exist "%SHORTCUT%" (
    echo [OK]  Startup shortcut created:
    echo       %SHORTCUT%
    echo.
    echo The agent will now auto-start every time you log in.
    echo Server URL: http://localhost:8765/
    echo Launcher:   %VBS%
    echo Log file:   \\wsl$\Ubuntu\tmp\launchbay.log
    echo.
    echo To remove auto-start later: delete the shortcut above
    echo or run UNINSTALL_AUTOSTART.cmd.
) else (
    echo [FAIL] Could not create shortcut. Run this from Windows
    echo        Explorer ^(double-click^) — not from a network share.
)

echo.
pause
