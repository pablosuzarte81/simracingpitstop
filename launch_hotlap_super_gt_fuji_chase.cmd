@echo off
REM ===============================================================
REM  ONE-CLICK: Super GT Fuji Chase 2026
REM  Recreate the Red Bull / Verstappen Nissan Z GT500 wet test.
REM  - Backs up current cfg\race.ini -^> race.ini.bak
REM  - Installs the Fuji Chase hotlap preset
REM  - Player = Max Verstappen #1 in the Nissan Z GT500
REM  - Verstappen Delta HUD shows live deltas vs:
REM      MIYAKE 1:44.075   (benchmark to beat)
REM      VERSTAPPEN 1:42.290 (stretch goal)
REM  - Hotlap mode (single car, no AI, ghost ON)
REM  - Pure LCS heavy rain, 14^|16C, JST sun
REM  - Steam must be running.
REM  After: run restore_race_ini.cmd to put back your old config.
REM ===============================================================
setlocal enableextensions

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=D:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\hotlap_super_gt_fuji_chase.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [SUPER GT FUJI CHASE 2026 — BEAT MIYAKE 1:44.075]
echo  Nissan Z GT500 + Fuji Speedway + Pure heavy rain
echo  Hotlap mode, ghost ON, HUD overrides ACTIVE
echo.

if not exist "%PRESET%" (
    echo ERROR: preset not found:
    echo   %PRESET%
    pause
    exit /b 1
)

findstr /C:"__FUJI_TRACK__" "%PRESET%" >nul
if not errorlevel 1 (
    echo ERROR: preset still has placeholder track/car names.
    echo Run verify_install_supergt.cmd first to detect and fill them in.
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

echo Installing Super GT Fuji Chase preset...
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
