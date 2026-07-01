@echo off
REM ===============================================================
REM  ONE-CLICK: RED BULL RING HOTLAP 2026 — MERCEDES-AMG W16 (ANTONELLI)
REM  - Backs up cfg/race.ini, installs the preset, fires Crew Chief,
REM    runs acs.exe, and kills CC when AC exits.
REM  - Pre-writes the low-downforce quali setup (RedBullRing_Quali_2026,
REM    12 L, trimmed wings for the three straights) to last.ini (both the
REM    fn_redbullring and generic folders) so hotlap mode (TYPE=4)
REM    loads it by default. FIXED_SETUP=0 keeps the garage open.
REM ===============================================================
setlocal enableextensions

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=F:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\hotlap_austria_2026.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"
set "SETUPSRC=%ACDOC%\setups\rss_formula_hybrid_2025_alpine\fn_redbullring\RedBullRing_Quali_2026.ini"
set "SETUPTRK=%ACDOC%\setups\rss_formula_hybrid_2025_alpine\fn_redbullring\last.ini"
set "SETUPGEN=%ACDOC%\setups\rss_formula_hybrid_2025_alpine\generic\last.ini"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [RED BULL RING HOTLAP 2026 - MERCEDES-AMG W16]
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

REM --- Force-load the low-downforce quali setup (hotlap mode reads last.ini)
if exist "%SETUPSRC%" (
    echo Loading Red Bull Ring quali setup ^(12 L, trimmed wings^)...
    copy /Y "%SETUPSRC%" "%SETUPTRK%" >nul
    copy /Y "%SETUPSRC%" "%SETUPGEN%" >nul
) else (
    echo WARNING: Red Bull Ring quali setup not found, AC will use its last-used setup:
    echo   %SETUPSRC%
)

REM --- Crew Chief auto-launch + auto-press Start
call "%~dp0launcher\start_crew_chief.cmd"

echo Launching Assetto Corsa...
echo.
start "" /D "%ACINSTALL%" "%ACINSTALL%\acs.exe"

REM --- Watch for AC exit, then close Crew Chief so next launch starts fresh
start "" /B powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0launcher\wait_and_close_cc.ps1"

endlocal
exit /b 0
