@echo off
REM ===============================================================
REM  ONE-CLICK: Canadian GP 2026 Race (VRC Formula Alpha 2025)
REM  - 20-car real F1 2026 grid (Verstappen + 19 AI rivals)
REM  - 5-lap sprint, no qualy => player starts P20 (back of grid)
REM  - Setup: Montreal_Race_v1 (DF 5/5 · 30L · soft tyres · F-bias 58)
REM  Steam must be running.
REM  After: run restore_race_ini.cmd to put back your old config
REM ===============================================================
setlocal enableextensions

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=D:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\race_canada_vrc.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [CANADIAN GP 2026 - VRC FORMULA ALPHA 2025 GRID]
echo  20-car real F1 grid - Verstappen vs Norris/Russell/Leclerc/...
echo  5 laps, charge from P20
echo.

if not exist "%PRESET%" (
    echo ERROR: preset not found:
    echo   %PRESET%
    pause
    exit /b 1
)

if not exist "%ACINSTALL%\acs.exe" (
    echo ERROR: AC install not found at:
    echo   %ACINSTALL%
    pause
    exit /b 1
)

if exist "%TARGET%" (
    echo Backing up current race.ini -^> race.ini.bak
    copy /Y "%TARGET%" "%BACKUP%" >nul
)

echo Installing Canada VRC race preset...
copy /Y "%PRESET%" "%TARGET%" >nul

REM --- Crew Chief auto-launch + auto-press Start (see launcher\start_crew_chief.cmd)
call "%~dp0launcher\start_crew_chief.cmd"

echo Launching Assetto Corsa...
echo.
start "" /D "%ACINSTALL%" "%ACINSTALL%\acs.exe"

REM --- Watch for AC exit, then close Crew Chief so next launch starts fresh
start "" /B powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0launcher\wait_and_close_cc.ps1"

endlocal
exit /b 0
