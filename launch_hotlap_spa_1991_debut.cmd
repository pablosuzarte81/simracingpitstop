@echo off
REM ===============================================================
REM  ONE-CLICK: SPA · 1991 DEBUT
REM  - Backs up cfg/race.ini, installs the preset, fires Crew Chief,
REM    runs acs.exe, and kills CC when AC exits.
REM ===============================================================
setlocal enableextensions

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=D:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\hotlap_spa_1991_debut.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [SPA · 1991 DEBUT]
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

REM --- Watch for AC exit, then close Crew Chief so next launch starts fresh
start "" /B powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0launcher\wait_and_close_cc.ps1"

endlocal
exit /b 0
