@echo off
REM AUTO-GENERATED weekly race launcher — FORMULA 1 · BRITISH · HOTLAP
setlocal enableextensions
set "ACDOC=%USERPROFILE%\Documents\Assetto Corsa"
set "ACINSTALL=F:\SteamLibrary\steamapps\common\assettocorsa"
set "PRESET=%ACDOC%\cfg\hotlap_week_f1.ini"
set "TARGET=%ACDOC%\cfg\race.ini"
set "BACKUP=%ACDOC%\cfg\race.ini.bak"

echo  [WEEKLY · FORMULA 1 · BRITISH · HOTLAP]
if not exist "%PRESET%" ( echo ERROR: preset not found: %PRESET% & pause & exit /b 1 )
if not exist "%ACINSTALL%\acs.exe" ( echo ERROR: AC not found & pause & exit /b 1 )
if exist "%TARGET%" copy /Y "%TARGET%" "%BACKUP%" >nul
copy /Y "%PRESET%" "%TARGET%" >nul
call "%~dp0launcher\start_crew_chief.cmd"
start "" /D "%ACINSTALL%" "%ACINSTALL%\acs.exe"
start "" /B powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0launcher\wait_and_close_cc.ps1"
endlocal
exit /b 0
