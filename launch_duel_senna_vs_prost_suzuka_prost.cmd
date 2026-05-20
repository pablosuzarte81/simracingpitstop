@echo off
REM ===============================================================
REM  ONE-CLICK: SENNA VS PROST SUZUKA - BE PROST — BE PROST perspective
REM ===============================================================
setlocal enableextensions

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=F:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\duel_senna_vs_prost_suzuka_prost.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [SENNA VS PROST SUZUKA - BE PROST]
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
    copy /Y "%TARGET%" "%BACKUP%" >/dev/null
)

echo Installing preset...
copy /Y "%PRESET%" "%TARGET%" >/dev/null

echo Launching Assetto Corsa...
start "" /D "%ACINSTALL%" "%ACINSTALL%\acs.exe"

endlocal
exit /b 0
