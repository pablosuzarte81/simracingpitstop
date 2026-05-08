@echo off
REM Launch Crew Chief if not already running, then SYNCHRONOUSLY auto-press Start
REM (parent script must wait — otherwise AC steals focus before click lands).
set "CCEXE=C:\Program Files (x86)\Britton IT Ltd\CrewChiefV4\CrewChiefV4.exe"
if not exist "%CCEXE%" goto :end
tasklist /FI "IMAGENAME eq CrewChiefV4.exe" 2>NUL | find /I "CrewChiefV4.exe" >NUL || start "" "%CCEXE%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0click_cc_start.ps1"
:end
exit /b 0
