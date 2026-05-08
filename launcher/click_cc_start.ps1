$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes,System.Windows.Forms

$logPath = "$env:TEMP\cc_start_click.log"
function Log($m) { ("[{0:HH:mm:ss}] {1}" -f (Get-Date), $m) | Out-File -FilePath $logPath -Append -Encoding utf8 }
Log "==== run begin ===="

$sig = @"
using System;
using System.Runtime.InteropServices;
public static class Win32 {
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, IntPtr dwExtraInfo);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    public const uint LEFTDOWN = 0x0002;
    public const uint LEFTUP   = 0x0004;
    public const int  SW_RESTORE = 9;
}
"@
if (-not ([System.Management.Automation.PSTypeName]'Win32').Type) {
    Add-Type -TypeDefinition $sig -Language CSharp
}

$deadline = (Get-Date).AddSeconds(20)
$btn = $null
$proc = $null
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500
    $proc = Get-Process -Name CrewChiefV4 -ErrorAction SilentlyContinue |
            Where-Object { $_.MainWindowHandle -ne 0 } |
            Select-Object -First 1
    if (-not $proc) { continue }
    $root = [System.Windows.Automation.AutomationElement]::FromHandle($proc.MainWindowHandle)
    if (-not $root) { continue }

    $nameCond = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty,
        'Start Crew Chief'
    )
    $btn = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $nameCond)
    if ($btn) { Log ("found exact-name button on hwnd " + $proc.MainWindowHandle); break }

    $btnTypeCond = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Button
    )
    $buttons = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $btnTypeCond)
    foreach ($b in $buttons) {
        $n = $b.Current.Name
        if ($n -and $n -match '(?i)start.*crew.*chief') { $btn = $b; Log ("matched-by-regex: $n"); break }
    }
    if ($btn) { break }
}

if (-not $btn) {
    Log "TIMEOUT: never found Start Crew Chief button"
    exit 1
}

try {
    $pattern = $btn.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
    if ($pattern) {
        $pattern.Invoke()
        Log "InvokePattern.Invoke() fired"
        exit 0
    }
} catch {
    Log ("InvokePattern unsupported: " + $_.Exception.Message + " - falling back to mouse click")
}

try {
    [Win32]::ShowWindow($proc.MainWindowHandle, [Win32]::SW_RESTORE) | Out-Null
    [Win32]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null
    Start-Sleep -Milliseconds 250

    $rect = $btn.Current.BoundingRectangle
    if ($rect.Width -lt 1 -or $rect.Height -lt 1) {
        Log "button rect is empty, aborting"
        exit 4
    }
    $cx = [int]($rect.X + $rect.Width / 2)
    $cy = [int]($rect.Y + $rect.Height / 2)
    $rw = [int]$rect.Width
    $rh = [int]$rect.Height
    Log ("clicking at " + $cx + "," + $cy + " (rect " + [int]$rect.X + "," + [int]$rect.Y + " " + $rw + "x" + $rh + ")")

    [Win32]::SetCursorPos($cx, $cy) | Out-Null
    Start-Sleep -Milliseconds 80
    [Win32]::mouse_event([Win32]::LEFTDOWN, 0, 0, 0, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 60
    [Win32]::mouse_event([Win32]::LEFTUP,   0, 0, 0, [IntPtr]::Zero)
    Log "mouse click sent"
    exit 0
} catch {
    Log ("mouse-click fallback exception: " + $_.Exception.Message)
    exit 3
}
