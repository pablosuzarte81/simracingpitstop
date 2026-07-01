@echo off
REM ===============================================================
REM  ONE-CLICK: MONACO HOTLAP 2026 — RED BULL RB21
REM  - Pre-writes Pablo's saved Monaco setup to last.ini (both the
REM    monaco_2020 and generic folders) so hotlap mode (TYPE=4) loads
REM    it by default. FIXED_SETUP=0 keeps the garage open to change it.
REM  - Backs up cfg/race.ini, installs the preset, fires Crew Chief,
REM    runs acs.exe, and kills CC when AC exits.
REM ===============================================================
setlocal enableextensions

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=F:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\hotlap_monaco_2026.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

set "SETUPSRC=%ACDOC%\setups\rss_formula_hybrid_2025_alpine\monaco_2020\Monaco_Hotlap_2026.ini"
set "SETUPTRK=%ACDOC%\setups\rss_formula_hybrid_2025_alpine\monaco_2020\last.ini"
set "SETUPGEN=%ACDOC%\setups\rss_formula_hybrid_2025_alpine\generic\last.ini"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [MONACO HOTLAP 2026 - RED BULL RB21]
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

REM --- Force-load Pablo's Monaco setup (hotlap mode reads last.ini)
if exist "%SETUPSRC%" (
    echo Loading saved Monaco setup...
    copy /Y "%SETUPSRC%" "%SETUPTRK%" >nul
    copy /Y "%SETUPSRC%" "%SETUPGEN%" >nul
) else (
    echo WARNING: saved Monaco setup not found, AC will use its last-used setup:
    echo   %SETUPSRC%
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
