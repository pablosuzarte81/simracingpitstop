@echo off
REM ===============================================================
REM  ONE-CLICK: VETTEL · RB7 · NORDSCHLEIFE 24h LAYOUT (solo hotlap)
REM  - You drive Sebastian Vettel in the F1 2011 Red Bull RB7 (V8 era).
REM  - Track: Nordschleife 24h 2024 layout (same as the GT3 duels).
REM  - Solo hotlap, ghost on.
REM ===============================================================
setlocal enableextensions

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=F:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\hotlap_vettel_rb7_nordschleife.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [VETTEL - RB7 - NORDSCHLEIFE 24h LAYOUT (HOTLAP)]
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
