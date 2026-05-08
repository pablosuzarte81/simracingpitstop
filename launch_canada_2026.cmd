@echo off
REM ===============================================================
REM  ONE-CLICK: Canadian GP 2026 simulation — Verstappen + 11 F1 cars
REM  - Backs up current cfg\race.ini -> race.ini.bak
REM  - Installs the Canada 2026 preset
REM  - 5-lap race, AI 80-99 (real 2026 form post-Miami), no track limits
REM  - Player = Max Verstappen #1 on pole, Circuit Gilles Villeneuve
REM  - 19-car real 2026 grid on RSS Formula Hybrid Alpine 2025
REM    (X 2026 car renders white on this system — debug separately)
REM  - Launches AC directly via acs.exe (bypasses launcher)
REM  Steam must be running.
REM  After the race: run restore_race_ini.cmd to put back your old config
REM ===============================================================
setlocal enableextensions

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=D:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\race_canada_2026.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [CANADIAN GP 2026 — VERSTAPPEN POLE LAP TO FLAG]
echo  Red Bull RB21 #1 vs 18-car real 2026 field, Montreal F1 2025
echo  5 laps, AI 80-99 (real 2026 form post-Miami), no track limits
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

echo Installing Canadian GP 2026 preset...
copy /Y "%PRESET%" "%TARGET%" >nul

REM --- Crew Chief auto-launch + auto-press Start (see launcher\start_crew_chief.cmd)
call "%~dp0launcher\start_crew_chief.cmd"

echo Launching Assetto Corsa...
echo (after the race, exit AC and a race summary will auto-open in your browser)
echo.

REM /WAIT blocks this script until acs.exe exits, so we can post-process race_out.json
start "" /WAIT /D "%ACINSTALL%" "%ACINSTALL%\acs.exe"

REM Close Crew Chief now that AC has exited (so next launch starts fresh).
taskkill /IM CrewChiefV4.exe /F >NUL 2>&1

echo.
echo  =============================================================
echo  Race finished. Generating summary...
echo  =============================================================

REM Give AC a moment to flush race_out.json
timeout /t 2 /nobreak >nul

REM Generate the race summary HTML via WSL python
wsl -e bash -lc "python3 '/mnt/c/Users/pablo/Documents/Assetto Corsa/dashboard/montreal/race_summary_montreal.py'"

if exist "%ACDOC%\dashboard\montreal\race_summary.html" (
    echo Opening race summary in browser...
    start "" "%ACDOC%\dashboard\montreal\race_summary.html"
) else (
    echo Could not locate race_summary.html — check the python script output above.
)

endlocal
exit /b 0
