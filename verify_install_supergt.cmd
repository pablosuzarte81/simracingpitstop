@echo off
REM ===============================================================
REM  Verify Super GT Fuji Chase install + patch the preset.
REM  - Scans content/cars and content/tracks
REM  - Picks the best Nissan Z GT500 + Fuji match
REM  - Rewrites placeholders in cfg/hotlap_super_gt_fuji_chase.ini
REM  - Adds the combo key to verstappen_delta/combo_targets.json
REM  Idempotent — re-run after each mod install attempt.
REM ===============================================================
setlocal enableextensions

set "VERIFY_PY=/mnt/c/Users/pablo/Documents/Assetto Corsa/dashboard/verify_install_supergt.py"

echo.
echo [Verifying Super GT Fuji Chase install...]
echo.
wsl python3 "%VERIFY_PY%"
set RC=%ERRORLEVEL%

echo.
if %RC%==0 (
    echo SUCCESS — preset patched, ready to launch.
) else (
    echo One or more mods are still missing. See report above.
)
echo.
endlocal
exit /b %RC%
