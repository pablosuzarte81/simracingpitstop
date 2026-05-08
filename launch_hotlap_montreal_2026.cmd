@echo off
REM ===============================================================
REM  ONE-CLICK: Montreal Hotlap 2026 — chase Canadian GP qualy time
REM  - Backs up current cfg\race.ini -> race.ini.bak
REM  - Installs the Montreal Hotlap preset
REM  - Player = Max Verstappen #1 in RSS Formula Hybrid Alpine 2025
REM  - Setup: Montreal_Hotlap_v1 (low-DF, fwd brake bias, open ducts)
REM  - Hotlap mode (single car, no AI, no fuel use, no tyre wear)
REM  - Ghost car of your PB enabled
REM  - F1 HUD overlays active via cfg/python.ini
REM  Steam must be running.
REM  After: run restore_race_ini.cmd to put back your old config
REM ===============================================================
setlocal enableextensions

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=D:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\hotlap_montreal_2026.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [MONTREAL HOTLAP 2026 — CHASE THE QUALY TIME]
echo  RB21 + Montreal F1 2025 + Montreal_Hotlap_v1 setup
echo  Hotlap mode, ghost ON, F1 HUD active
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
    echo Edit ACINSTALL at the top of this script.
    pause
    exit /b 1
)

if exist "%TARGET%" (
    echo Backing up current race.ini -^> race.ini.bak
    copy /Y "%TARGET%" "%BACKUP%" >nul
)

echo Installing Montreal Hotlap preset...
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
