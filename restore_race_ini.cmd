@echo off
REM Restore the previous cfg\race.ini from the backup created by launch_24h_nurburgring_2026.cmd
setlocal enableextensions

set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

if not exist "%BACKUP%" (
    echo No backup found at:
    echo   %BACKUP%
    echo Nothing to restore.
    pause
    exit /b 1
)

copy /Y "%BACKUP%" "%TARGET%" >nul
echo Restored cfg\race.ini from backup.
endlocal
exit /b 0
