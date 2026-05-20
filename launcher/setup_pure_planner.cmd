@echo off
REM ===============================================================
REM  Switches pureCtrl/settings.ini to load a specific Pure Planner
REM  Timed/ plan, backing up the original settings.ini first.
REM
REM  Usage:
REM    call setup_pure_planner.cmd <plan_basename>
REM    where <plan_basename> is the file in
REM    F:\SteamLibrary\steamapps\common\assettocorsa\extension\config-ext\PurePlanner\Plans\Timed\
REM    WITHOUT the .json extension.
REM
REM  After AC exits, wait_and_restore_pure_planner.ps1 puts the
REM  original settings.ini back.
REM ===============================================================
setlocal enableextensions

set "PLAN_NAME=%~1"
if "%PLAN_NAME%"=="" (
    echo [setup_pure_planner] ERROR: no plan basename passed.
    exit /b 1
)

set "PURECTRL=F:\SteamLibrary\steamapps\common\assettocorsa\extension\weather-controllers\pureCtrl"
set "SETTINGS=%PURECTRL%\settings.ini"
set "BACKUP=%PURECTRL%\settings.ini.bak"

if not exist "%SETTINGS%" (
    echo [setup_pure_planner] ERROR: settings.ini not found at %SETTINGS%
    exit /b 1
)

if not exist "%BACKUP%" (
    copy /Y "%SETTINGS%" "%BACKUP%" >nul
    echo [setup_pure_planner] backed up settings.ini -^> settings.ini.bak
) else (
    echo [setup_pure_planner] backup already exists, leaving as-is
)

> "%SETTINGS%" echo [SETTINGS]
>> "%SETTINGS%" echo LIVE=0 ; Use live data ; 1 or 0
>> "%SETTINGS%" echo LAST_USED=0 ; Load last used plan. Uncheck this to be able to load a plan set in the "Plan" field! ; 1 or 0 ;
>> "%SETTINGS%" echo PLAN = Timed/%PLAN_NAME% ; Relative to /extension/config-ext/PurePlanner/Plans/ folder. Use slash - not backslash;
>> "%SETTINGS%" echo AUTOSTART=1 ; Start plan with the race ; 1 or 0
>> "%SETTINGS%" echo CM_WEATHER=1
>> "%SETTINGS%" echo START_WETNESS=1
>> "%SETTINGS%" echo START_PUDDLES=1

echo [setup_pure_planner] settings.ini now points at Timed/%PLAN_NAME%

endlocal
exit /b 0
