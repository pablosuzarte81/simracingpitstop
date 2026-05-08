@echo off
REM Background launcher — runs server with no window. Logs to launchbay.log.
start "" /b wsl -d Ubuntu -e bash -lc "nohup python3 '/mnt/c/Users/pablo/Documents/Assetto Corsa/launcher/launcher_dashboard.py' --no-browser ^> /tmp/launchbay.log 2^>^&1 ^&"
