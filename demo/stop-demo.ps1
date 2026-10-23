# Stops the demo started by demo\start-demo.cmd, and the shared link if demo\share-demo.cmd started one.
# Plain ASCII on purpose (Windows PowerShell 5.1).
$ErrorActionPreference = "Continue"
$state = Join-Path $env:LOCALAPPDATA "fo-demo"
$pidFile = Join-Path $state "running.json"

if (Test-Path $pidFile) {
    $running = Get-Content $pidFile -Raw | ConvertFrom-Json
    # the link first (so nobody can reach a half-stopped demo), then the app
    foreach ($processId in @($running.tunnel, $running.gate, $running.web, $running.api)) {
        if ($processId -and (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
            & taskkill.exe /PID $processId /T /F | Out-Null
        }
    }
    Remove-Item $pidFile -Force
    if ($running.tunnel) { Write-Host "The shared link is closed." }
    Write-Host "The demo is stopped."
} else {
    Write-Host "No demo was started by demo\start-demo.cmd."
}
foreach ($port in @(8100, 5181, 8200)) {
    $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($c) {
        $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        Write-Host "Port $port is still in use by $($p.ProcessName) (process $($c.OwningProcess)). It was not started by the demo, so it was left alone."
    }
}
