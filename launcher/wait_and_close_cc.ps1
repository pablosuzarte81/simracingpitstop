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
# Wait-Process returns when ALL processes with that name have exited.
Wait-Process -Name acs -ErrorAction SilentlyContinue
Log "acs.exe exited - closing CrewChiefV4"
Stop-Process -Name CrewChiefV4 -Force -ErrorAction SilentlyContinue
Log "watcher done"
