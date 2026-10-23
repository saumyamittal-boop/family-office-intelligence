# Puts the demo behind a password and opens a temporary public https address to it (a Cloudflare "quick tunnel": no account).
# Double-click demo\share-demo.cmd. Close the link, and the demo, with demo\stop-demo.cmd.
#
# What becomes reachable: ONLY the demo, through demo\gate.py, which asks for the password first. Your development database is not used.
# Everything in it is synthetic. The link works only while this laptop is awake, online and this window's processes are running.
# Plain ASCII on purpose (Windows PowerShell 5.1).
#
# One-time: demo\bin\cloudflared.exe must exist (see docs\plan-sharing-and-deployment.md, section 5b). It is not part of the repository.

param([string]$Password = "")

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
$cloudflared = Join-Path $PSScriptRoot "bin\cloudflared.exe"
$state = Join-Path $env:LOCALAPPDATA "fo-demo"
$pidFile = Join-Path $state "running.json"
$tunnelLog = Join-Path $state "tunnel.log"
$gateLog = Join-Path $state "gate.log"

function Say($text) { Write-Host $text }
function Fail($text) {
    Write-Host ""; Write-Host "STOPPED: $text" -ForegroundColor Red; Write-Host ""
    & (Join-Path $PSScriptRoot "stop-demo.ps1") | Out-Null
    exit 1
}

Say ""
Say "Family Office Intelligence: sharing the demo (synthetic data only; not investment advice)"
Say ""
if (-not (Test-Path $cloudflared)) { Fail "demo\bin\cloudflared.exe is missing. See docs\plan-sharing-and-deployment.md section 5b." }
if (-not (Test-Path $py)) { Fail "Python environment not found at $py. Follow docs\setup.md section 3 first." }

# 1. A clean demo in shared mode (secure cookie, no interactive API pages, at most 20 sign-ups)
Say "1/4  Starting the demo in shared mode..."
& (Join-Path $PSScriptRoot "stop-demo.ps1") | Out-Null
& (Join-Path $PSScriptRoot "start-demo.ps1") -Shared -NoBrowser | Out-Null
if ($LASTEXITCODE -ne 0) { Fail "The demo did not start. Run demo\start-demo.cmd to see why." }

# 2. The password
if (-not $Password) {
    $alphabet = "abcdefghjkmnpqrstuvwxyz23456789"
    $bytes = New-Object byte[] 16
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    $chars = $bytes | ForEach-Object { $alphabet[$_ % $alphabet.Length] }
    $Password = (($chars[0..3] -join ""), ($chars[4..7] -join ""), ($chars[8..11] -join ""), ($chars[12..15] -join "")) -join "-"
}

# 3. The tunnel, to the gate's port (the gate is not started yet; the tunnel only needs the port to exist by the time someone visits)
Say "2/4  Opening the tunnel..."
Remove-Item $tunnelLog -ErrorAction SilentlyContinue
$tunnelArgs = "/c `"`"$cloudflared`" tunnel --no-autoupdate --url http://127.0.0.1:8200 > `"$tunnelLog`" 2>&1`""
$tunnel = Start-Process -FilePath "cmd.exe" -ArgumentList $tunnelArgs -WindowStyle Hidden -PassThru
$url = $null
for ($i = 0; $i -lt 60 -and -not $url; $i++) {
    Start-Sleep -Seconds 1
    if (-not (Get-Process -Id $tunnel.Id -ErrorAction SilentlyContinue)) { Fail "The tunnel program stopped. Read $tunnelLog" }
    if (Test-Path $tunnelLog) {
        $m = Select-String -Path $tunnelLog -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' | Select-Object -First 1
        if ($m) { $url = $m.Matches[0].Value }
    }
}
if (-not $url) { Fail "No public address appeared within a minute. Read $tunnelLog" }

# 4. The gate, which knows the public address so it can check where requests come from
Say "3/4  Starting the password gate..."
$env:FO_GATE_PASSWORD = $Password
$env:FO_GATE_PUBLIC_ORIGIN = $url
$gateArgs = "/c `"`"$py`" -B `"$PSScriptRoot\gate.py`" > `"$gateLog`" 2>&1`""
$gate = Start-Process -FilePath "cmd.exe" -ArgumentList $gateArgs -WorkingDirectory $root -WindowStyle Hidden -PassThru
$running = Get-Content $pidFile -Raw | ConvertFrom-Json
$running | Add-Member -NotePropertyName gate -NotePropertyValue $gate.Id -Force
$running | Add-Member -NotePropertyName tunnel -NotePropertyValue $tunnel.Id -Force
$running | ConvertTo-Json | Set-Content -Path $pidFile -Encoding ascii

# 5. Prove it from the outside: no password is refused, the password gets the app
Say "4/4  Checking the public address (the first requests can take a few seconds while the new name spreads)..."
$auth = @{ Authorization = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("demo:$Password")) }
$refused = $false
$served = $false
for ($i = 0; $i -lt 45 -and -not ($refused -and $served); $i++) {
    if (-not $refused) {
        try { Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5 | Out-Null } catch {
            if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 401) { $refused = $true }
        }
    }
    if (-not $served) {
        try {
            $r = Invoke-WebRequest -Uri "$url/api/health" -Headers $auth -UseBasicParsing -TimeoutSec 5
            if ($r.StatusCode -eq 200) { $served = $true }
        } catch { }
    }
    if (-not ($refused -and $served)) { Start-Sleep -Seconds 1 }
}
if (-not $refused) { Fail "The public address answered without asking for the password. Not sharing it." }
if (-not $served) { Fail "The public address did not serve the app with the password. Read $gateLog and $tunnelLog" }

Set-Clipboard -Value "Family Office Intelligence demo (synthetic data)`r`nLink: $url`r`nUser name: anything`r`nPassword: $Password"
Say ""
Say "Shared. Send him this (it is also on your clipboard):"
Say ""
Say "   Link:       $url"
Say "   User name:  anything"
Say "   Password:   $Password"
Say ""
Say "  * The link works only while this laptop is on and online. It changes every time you run this."
Say "  * Everything is synthetic; each visitor gets a private copy of a demo family. Do not type real data."
Say "  * Close it with demo\stop-demo.cmd."
exit 0
