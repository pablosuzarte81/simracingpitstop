@echo off
REM ===============================================================
REM  ONE-CLICK: NLS 2 2026 simulation — Verstappen + 15 GT3s
REM  - Backs up current cfg\race.ini -> race.ini.bak
REM  - Installs the NLS 2 preset
REM  - 3-lap race, AI 91-95 grid, no qualy, no track limits
REM  - Mercer V8 #3 + Haase Audi #4 + 14 other GT3s
REM  - Launches AC directly via acs.exe (bypasses launcher)
REM  Steam must be running.
REM  After the race: run restore_race_ini.cmd to put back your old config
REM ===============================================================
setlocal enableextensions

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=D:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\race_nls2_2026.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [NLS 2 2026 — VERSTAPPEN vs THE GT3 FIELD]
echo Mercedes-AMG #3 vs Audi Scherer #4 + 14 other SP9 PRO entries
echo Nordschleife endurance_cup, 3 laps, AI 91-95, no track limits
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

echo Installing NLS 2 preset...
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
