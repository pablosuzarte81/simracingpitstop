@echo off
REM ===============================================================
REM  ONE-CLICK: NLS 2 Hotlap - chase Verstappen's 7:51.751 pole
REM  - Backs up current cfg\race.ini -> race.ini.bak
REM  - Installs the NLS 2 Hotlap preset (solo, ghost on)
REM  - Mercer V8 GT3 + Nordschleife endurance_cup, Verstappen #3 livery
REM  - Hotlap mode (single car, no AI, no fuel use, no tyre wear)
REM  Steam must be running.
REM  After: run restore_race_ini.cmd to put back your old config
REM ===============================================================
setlocal enableextensions

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=D:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\hotlap_nls2_2026.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [NLS 2 HOTLAP - CHASE 7:51.751]
echo  Mercer V8 GT3 + Nordschleife endurance_cup + Verstappen #3
echo  Hotlap mode, ghost ON
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

echo Installing NLS 2 Hotlap preset...
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
