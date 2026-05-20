@echo off
REM ===============================================================
REM  ONE-CLICK: NLS 2 POLE CHASE
REM  - Backs up cfg/race.ini, installs the preset, fires Crew Chief,
REM    runs acs.exe, and kills CC when AC exits.
REM ===============================================================
setlocal enableextensions

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=F:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\hotlap_nls2_2026.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [NLS 2 POLE CHASE]
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

REM --- Force-load nls2_2026_hotlap setup. AC hotlap mode is fussy about
REM     where it reads setups from, so we write to every plausible path:
REM       (1) setups\<car>\<track>\last.ini   (track-scoped last-used)
REM       (2) setups\<car>\generic\last.ini   (car-scoped last-used)
REM     FIXED_SETUP stays 0 (otherwise the setup tab is non-clickable);
REM     pre-writing last.ini IS the actual auto-load mechanism.
set "SETUP_SRC=%ACDOC%\setups\rss_gtm_mercer_v8\ks_nordschleife\nls2_2026_hotlap.ini"
set "SETUP_DST_TRACK=%ACDOC%\setups\rss_gtm_mercer_v8\ks_nordschleife\last.ini"
set "SETUP_DST_GEN=%ACDOC%\setups\rss_gtm_mercer_v8\generic\last.ini"
if exist "%SETUP_SRC%" (
    copy /Y "%SETUP_SRC%" "%SETUP_DST_TRACK%" >nul
    copy /Y "%SETUP_SRC%" "%SETUP_DST_GEN%" >nul
    echo Loaded setup: nls2_2026_hotlap
) else (
    echo WARNING: setup file not found at %SETUP_SRC%
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
