@echo off
REM ===============================================================
REM  Archive telemetry from the most recent AC session.
REM  Captures CMRT reference laps, AIM telemetry dump, replay,
REM  personal best, and the widget ghost JSON into a timestamped
REM  folder for sharing / coaching analysis.
REM
REM  Run after a session that had a meaningful lap.
REM  Note: CMRT fast.lap is overwritten when you set a new PB,
REM  so archive promptly.
REM ===============================================================
setlocal enableextensions enabledelayedexpansion

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=D:\SteamLibrary\steamapps\common\assettocorsa"
set "ARCHIVE_ROOT=%ACDOC%\telemetry_archive"
set "CMRT_DIR=%ACDOC%\CMRT-Essential-HUD"
set "AIM_FILE=%ACDOC%\aim\telemetry_dump.act"
set "PB_FILE=%ACDOC%\personalbest.ini"
set "RACEOUT=%ACDOC%\out\race_out.json"
set "REPLAY_DIR=%ACDOC%\replay\temp"
set "WIDGET_JSON=%ACINSTALL%\apps\python\verstappen_delta\reference_lap_rss_gtm_mercer_v8__ks_nordschleife__endurance_cup.json"

REM Locale-safe timestamp via PowerShell
for /f %%i in ('powershell -NoLogo -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "TS=%%i"
set "DEST=%ARCHIVE_ROOT%\%TS%"

echo.
echo [Telemetry archive: %TS%]
echo.

if not exist "%ARCHIVE_ROOT%" mkdir "%ARCHIVE_ROOT%"
mkdir "%DEST%" 2>nul

set "COUNT=0"

REM 1. CMRT reference laps (fast + 3 sectors)
if exist "%CMRT_DIR%" (
    for %%F in ("%CMRT_DIR%\*.lap") do (
        copy /Y "%%F" "%DEST%\" >nul && set /a COUNT+=1
    )
    echo  + CMRT laps copied
) else (
    echo  - CMRT dir not found, skipping
)

REM 2. AIM telemetry dump
if exist "%AIM_FILE%" (
    copy /Y "%AIM_FILE%" "%DEST%\telemetry_dump.act" >nul && set /a COUNT+=1
    echo  + AIM telemetry_dump.act copied
) else (
    echo  - AIM dump not found, skipping
)

REM 3. Personal best
if exist "%PB_FILE%" (
    copy /Y "%PB_FILE%" "%DEST%\personalbest.ini" >nul && set /a COUNT+=1
    echo  + personalbest.ini copied
)

REM 4. Race out JSON
if exist "%RACEOUT%" (
    copy /Y "%RACEOUT%" "%DEST%\race_out.json" >nul && set /a COUNT+=1
    echo  + race_out.json copied
)

REM 5. Most recent replay for Mercer / Nordschleife
set "LATEST_REPLAY="
if exist "%REPLAY_DIR%" (
    for /f "delims=" %%R in ('dir /b /o-d /a-d "%REPLAY_DIR%\*rss_gtm_mercer_v8_ks_nordschleife*.acreplay" 2^>nul') do (
        if not defined LATEST_REPLAY set "LATEST_REPLAY=%%R"
    )
)
if defined LATEST_REPLAY (
    copy /Y "%REPLAY_DIR%\%LATEST_REPLAY%" "%DEST%\" >nul && set /a COUNT+=1
    echo  + replay: %LATEST_REPLAY%
) else (
    echo  - no matching replay found
)

REM 6. Widget ghost JSON
if exist "%WIDGET_JSON%" (
    copy /Y "%WIDGET_JSON%" "%DEST%\verstappen_delta_ghost.json" >nul && set /a COUNT+=1
    echo  + widget ghost JSON copied
)

REM Summary file
(
    echo Archived: %TS%
    echo Source:   %ACDOC%
    echo Files:    %COUNT%
    echo.
    echo --- personalbest.ini ---
    if exist "%PB_FILE%" type "%PB_FILE%"
) > "%DEST%\summary.txt"

echo.
echo Archived %COUNT% files to:
echo   %DEST%
echo.

REM ---------------------------------------------------------------
REM  Generate dashboard report (Python via WSL).
REM  Set OPEN_BROWSER=0 below if you don't want the browser to pop.
REM ---------------------------------------------------------------
set "OPEN_BROWSER=1"
set "DASH_SCRIPT=/mnt/c/Users/pablo/Documents/Assetto Corsa/dashboard/dashboard_gen.py"
set "DASH_HTML=%ARCHIVE_ROOT%\dashboard.html"

echo Generating dashboard...
wsl python3 "%DASH_SCRIPT%"
if errorlevel 1 (
    echo  - dashboard generation FAILED ^(non-fatal, archive is intact^)
) else (
    echo  + dashboard.html refreshed
    if "%OPEN_BROWSER%"=="1" if exist "%DASH_HTML%" (
        start "" "%DASH_HTML%"
    )
)

echo.
endlocal
exit /b 0
