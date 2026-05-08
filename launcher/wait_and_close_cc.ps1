$ErrorActionPreference = 'SilentlyContinue'

$logPath = "$env:TEMP\cc_close_watcher.log"
function Log($m) { ("[{0:HH:mm:ss}] {1}" -f (Get-Date), $m) | Out-File -FilePath $logPath -Append -Encoding utf8 }
Log "==== watcher start ===="

# Wait up to 60s for acs.exe to actually appear (it's launched async by the parent .cmd).
$appearDeadline = (Get-Date).AddSeconds(60)
$acsAppeared = $false
while ((Get-Date) -lt $appearDeadline) {
    if (Get-Process -Name acs -ErrorAction SilentlyContinue) { $acsAppeared = $true; break }
    Start-Sleep -Milliseconds 500
}

if (-not $acsAppeared) {
    Log "acs.exe never appeared - killing CC anyway so next launch is fresh"
    Stop-Process -Name CrewChiefV4 -Force -ErrorAction SilentlyContinue
    exit 0
}

Log "acs.exe is running - waiting for it to exit"
Wait-Process -Name acs -ErrorAction SilentlyContinue
Log "acs.exe exited - closing CrewChiefV4 + capturing results"
Stop-Process -Name CrewChiefV4 -Force -ErrorAction SilentlyContinue

# --- post-race results capture ---------------------------------------
# Snapshot race_out.json so update_results.py can match it to a tile and
# render the latest finish/PB on the dashboard card.
$ACDOC      = Join-Path $env:USERPROFILE 'Documents\Assetto Corsa'
$raceOut    = Join-Path $ACDOC 'out\race_out.json'
$resultsDir = Join-Path $ACDOC 'dashboard\results\snapshots'
$updater    = Join-Path $ACDOC 'launcher\update_results.py'

if (Test-Path $raceOut) {
    if (-not (Test-Path $resultsDir)) {
        New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null
    }
    $stamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
    $dest = Join-Path $resultsDir "$stamp.json"
    Copy-Item -Path $raceOut -Destination $dest -Force
    Log "snapshot saved: $dest"

    # Run the updater (uses WSL python — same path as archive_telemetry.cmd).
    if (Test-Path $updater) {
        Log "running update_results.py via WSL"
        wsl -e bash -lc "python3 '/mnt/c/Users/pablo/Documents/Assetto Corsa/launcher/update_results.py'" 2>&1 | Out-Null
        Log "update_results.py done"
    } else {
        Log "update_results.py missing, skip"
    }
} else {
    Log "race_out.json missing, skip results capture"
}

Log "watcher done"
