$ErrorActionPreference = 'SilentlyContinue'

$logPath = "$env:TEMP\pure_planner_restore.log"
function Log($m) { ("[{0:HH:mm:ss}] {1}" -f (Get-Date), $m) | Out-File -FilePath $logPath -Append -Encoding utf8 }
Log "==== Pure Planner restore watcher start ===="

$pureCtrl = "F:\SteamLibrary\steamapps\common\assettocorsa\extension\weather-controllers\pureCtrl"
$settings = Join-Path $pureCtrl 'settings.ini'
$backup   = Join-Path $pureCtrl 'settings.ini.bak'

if (-not (Test-Path $backup)) {
    Log "no backup at $backup - nothing to restore, exiting"
    exit 0
}

# Wait up to 60s for acs.exe to actually appear (parent .cmd launches it async).
$appearDeadline = (Get-Date).AddSeconds(60)
$acsAppeared = $false
while ((Get-Date) -lt $appearDeadline) {
    if (Get-Process -Name acs -ErrorAction SilentlyContinue) { $acsAppeared = $true; break }
    Start-Sleep -Milliseconds 500
}

if (-not $acsAppeared) {
    Log "acs.exe never appeared - restoring settings.ini anyway"
} else {
    Log "acs.exe is running - waiting for it to exit before restoring"
    Wait-Process -Name acs -ErrorAction SilentlyContinue
    Log "acs.exe exited - restoring pureCtrl/settings.ini from backup"
}

Copy-Item -Path $backup -Destination $settings -Force
Remove-Item -Path $backup -Force
Log "settings.ini restored, backup removed"
Log "watcher done"
