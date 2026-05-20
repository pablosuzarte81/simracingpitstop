@echo off
REM ===============================================================
REM  ONE-CLICK: INTERLAGOS 2008
REM ===============================================================
setlocal enableextensions
set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=F:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\f1_2008_brazil.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [INTERLAGOS 2008]
echo.

if not exist "%PRESET%" ( echo ERROR: preset not found: %PRESET% & pause & exit /b 1 )
if not exist "%ACINSTALL%\acs.exe" ( echo ERROR: AC install missing & pause & exit /b 1 )
if exist "%TARGET%" ( copy /Y "%TARGET%" "%BACKUP%" >/dev/null )
copy /Y "%PRESET%" "%TARGET%" >/dev/null

call "%~dp0launcher\start_crew_chief.cmd"

echo Launching Assetto Corsa...
start "" /D "%ACINSTALL%" "%ACINSTALL%\acs.exe"
start "" /B powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0launcher\wait_and_close_cc.ps1"
endlocal
exit /b 0
