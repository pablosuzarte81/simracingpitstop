@echo off
REM ===============================================================
REM  ONE-CLICK: 1v1 grudge match — Verstappen vs Haase
REM  - Backs up your current cfg\race.ini -> race.ini.bak
REM  - Installs the 1v1 preset (Mercer V8 #3 vs Scherer PHX Audi #15)
REM  - 1-lap race, AI 100, aggression 85, no track limits (F1-style)
REM  - Launches AC directly via acs.exe (bypasses launcher)
REM  Steam must be running.
REM  After the race: run restore_race_ini.cmd to put back your old config
REM ===============================================================
setlocal enableextensions

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=D:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\race_verstappen_1v1.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [1v1 THE REMATCH — VERSTAPPEN vs HAASE]
echo Mercedes-AMG #3 (Auer/Verstappen) vs Scherer Sport PHX Audi #16 (Green/Haase/Sims)
echo Nordschleife endurance_cup, 1 lap, AI 100 / aggression 85, no track limits
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

echo Installing 1v1 preset...
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
