@echo off
REM ===============================================================
REM  ONE-CLICK: Canadian GP Hotlap (VRC Formula Alpha 2025)
REM  - Backs up current cfg\race.ini -> race.ini.bak
REM  - Installs the Canada VRC Hotlap preset
REM  - Player = Verstappen #1 in VRC Formula Alpha 2025 (Pro)
REM  - Setup: Montreal_Hotlap_v1 (low DF · 14L · soft tyres · F-bias 58)
REM  - Hotlap mode (single car, no AI, no fuel use, no tyre wear)
REM  - Ghost car of your PB enabled
REM  Steam must be running.
REM  After: run restore_race_ini.cmd to put back your old config
REM ===============================================================
setlocal enableextensions

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=D:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\hotlap_canada_vrc.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [CANADA HOTLAP - VRC FORMULA ALPHA 2025]
echo  Verstappen #1 + Montreal F1 2025 + Montreal_Hotlap_v1 setup
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
    pause
    exit /b 1
)

if exist "%TARGET%" (
    echo Backing up current race.ini -^> race.ini.bak
    copy /Y "%TARGET%" "%BACKUP%" >nul
)

echo Installing Canada VRC Hotlap preset...
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
