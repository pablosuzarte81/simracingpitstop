@echo off
REM ===============================================================
REM  ONE-CLICK: VERSTAPPEN VS HAASE - 3 LAP DUSK -> NIGHT (light rain)
REM  - You drive Max Verstappen (Mercedes-AMG #3), Haase Audi #16 is the AI rival.
REM  - Race starts at deep dusk in light rain (sol_34_light_rain).
REM  - TIME_MULT=4 advances time so it's full dark by lap 3.
REM  - All driven by race.ini (no Pure Planner dependency).
REM ===============================================================
setlocal enableextensions

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=F:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\race_verstappen_1v1_3lap_dusk.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [VERSTAPPEN VS HAASE - 3 LAP DUSK -^> RAIN -^> NIGHT]
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

echo Installing preset...
copy /Y "%PRESET%" "%TARGET%" >nul

REM --- Crew Chief auto-launch + auto-press Start
call "%~dp0launcher\start_crew_chief.cmd"

echo Launching Assetto Corsa...
echo.
start "" /D "%ACINSTALL%" "%ACINSTALL%\acs.exe"

REM --- Watch for AC exit, then close Crew Chief
start "" /B powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0launcher\wait_and_close_cc.ps1"

endlocal
exit /b 0
