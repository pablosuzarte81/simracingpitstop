@echo off
echo This script will validate AC files with Steam, but it needs to wait
echo for Assetto Corsa to close for everything to work
timeout /T 3 /NOBREAK >NUL
explorer steam://validate/244210
