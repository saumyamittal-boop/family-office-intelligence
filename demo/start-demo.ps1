# Starts the React + FastAPI version for an in-person demo, checks it, and opens it in the browser.
# Double-click demo\start-demo.cmd (it runs this). Stop with demo\stop-demo.cmd.
#
#   -NoBrowser   do not open the browser
#   -SkipBuild   reuse web\dist instead of building the web app again (about 10 seconds)
#   -SkipCheck   do not run the figures check (a few seconds)
#
# What it does: builds the web app, starts the API on 127.0.0.1:8100 with a FRESH private demo database
# (%LOCALAPPDATA%\fo-demo\demo.db; your development database data\app.db is not touched), serves the built app on
# 127.0.0.1:5181 with the production security headers, waits until both answer, runs tools\demo_check.py against the
# running API (it also warms the engine), then opens the browser. Logs are in %LOCALAPPDATA%\fo-demo\.
# This file is plain ASCII on purpose: Windows PowerShell 5.1 misreads other characters.

param([switch]$NoBrowser, [switch]$SkipBuild, [switch]$SkipCheck, [switch]$Shared)
# -Shared is used by demo\share-demo.cmd: the API runs with the settings a public address needs (secure cookie, no interactive API pages,
# at most 20 sign-ups) and the figures check is skipped, because a secure cookie is not sent back over plain http.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
$vite = Join-Path $root "web\node_modules\vite\bin\vite.js"
$apiPort = 8100
$webPort = 5181
$apiUrl = "http://127.0.0.1:$apiPort"
$webUrl = "http://127.0.0.1:$webPort"
$state = Join-Path $env:LOCALAPPDATA "fo-demo"
$pidFile = Join-Path $state "running.json"
$apiLog = Join-Path $state "api.log"
$webLog = Join-Path $state "web.log"
$db = Join-Path $state "demo.db"

function Say($text) { Write-Host $text }
function Fail($text) { Write-Host ""; Write-Host "STOPPED: $text" -ForegroundColor Red; Write-Host ""; exit 1 }

function Alive($processId) { return [bool](Get-Process -Id $processId -ErrorAction SilentlyContinue) }

function Answers($url) {
    try { return (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200 } catch { return $false }
}

function Who($port) {
    $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $c) { return $null }
    $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
    return "$($p.ProcessName) (process $($c.OwningProcess))"
}

Say ""
Say "Family Office Intelligence: starting the demo"
Say "(synthetic data only; an illustrative simulation, not investment advice)"
Say ""

# Already running from an earlier double-click? Just show it again.
if (Test-Path $pidFile) {
    $old = Get-Content $pidFile -Raw | ConvertFrom-Json
    if ((Alive $old.api) -and (Alive $old.web) -and (Answers "$webUrl/api/health")) {
        Say "The demo is already running at $webUrl"
        if (-not $NoBrowser) { Start-Process $webUrl }
        exit 0
    }
}

# Preflight
if (-not (Test-Path $py)) { Fail "Python environment not found at $py. Follow docs\setup.md section 3 first." }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Fail "Node.js is not installed or not on the PATH (docs\setup.md section 1)." }
if (-not (Test-Path $vite)) { Fail "The web packages are not installed. Run 'npm ci' in the web folder (docs\setup.md section 3)." }
foreach ($port in @($apiPort, $webPort)) {
    $who = Who $port
    if ($who) { Fail "Port $port is already used by $who. Close it (or run demo\stop-demo.cmd) and try again." }
}
if (-not (Test-Path (Join-Path $root "data\models"))) {
    Write-Host "Note: the optional Assistant model is not installed (data\models). The Assistant will still work, with word matching only." -ForegroundColor Yellow
}
New-Item -ItemType Directory -Force -Path $state | Out-Null

# 1. Build the web app
if ($SkipBuild -and (Test-Path (Join-Path $root "web\dist\index.html"))) {
    Say "1/5  Reusing the existing web build."
} else {
    Say "1/5  Building the web app (about 10 seconds)..."
    Push-Location (Join-Path $root "web")
    $env:VITE_CONFIG_NATIVE_IGNORE_WARNING = "true"   # silences a harmless notice about the configuration file
    & node $vite build --logLevel error
    $code = $LASTEXITCODE
    Pop-Location
    if ($code -ne 0) { Fail "The web build failed (exit code $code). Run 'npm run build' in the web folder to see why." }
}

# 2. A fresh private demo database
Say "2/5  Preparing a fresh demo database (your development database is not used)."
Get-ChildItem -Path $state -Filter "demo.db*" -ErrorAction SilentlyContinue | Remove-Item -Force
$env:FO_DB_PATH = $db
$env:FO_API_CORS_ORIGINS = "$webUrl,http://localhost:$webPort"
$env:FO_API_URL = $apiUrl
if ($Shared) {
    $env:FO_API_COOKIE_SECURE = "1"
    $env:FO_API_DOCS = "0"
    $env:FO_MAX_ACCOUNTS = "20"
}

# 3. Start the API and the web server (hidden windows; logs in $state)
Say "3/5  Starting the API and the web server..."
$apiArgs = "/c `"`"$py`" -B -m uvicorn api.main:app --host 127.0.0.1 --port $apiPort --no-server-header > `"$apiLog`" 2>&1`""
$webArgs = "/c `"`"node`" `"$vite`" preview --port $webPort --strictPort --host 127.0.0.1 > `"$webLog`" 2>&1`""
$api = Start-Process -FilePath "cmd.exe" -ArgumentList $apiArgs -WorkingDirectory $root -WindowStyle Hidden -PassThru
$web = Start-Process -FilePath "cmd.exe" -ArgumentList $webArgs -WorkingDirectory (Join-Path $root "web") -WindowStyle Hidden -PassThru
@{ api = $api.Id; web = $web.Id; started = (Get-Date).ToString("s") } | ConvertTo-Json | Set-Content -Path $pidFile -Encoding ascii

# 4. Wait until both answer, including the web server's route to the API
Say "4/5  Waiting for them to answer..."
$ready = $false
for ($i = 0; $i -lt 90; $i++) {
    if (-not (Alive $api.Id)) { Fail "The API stopped while starting. Read $apiLog" }
    if ((Answers "$apiUrl/api/health") -and (Answers "$webUrl/api/health")) { $ready = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $ready) { Fail "They did not answer within 90 seconds. Read $apiLog and $webLog" }

# 5. Check the figures the script quotes, against the running API (also warms the engine)
if ($SkipCheck -or $Shared) {
    Say "5/5  Skipping the figures check."
} else {
    Say "5/5  Checking the demo script's figures against the running app (a few seconds)..."
    Push-Location $root
    & $py -B (Join-Path $root "tools\demo_check.py") --api $apiUrl
    $checked = $LASTEXITCODE
    Pop-Location
    if ($checked -ne 0) {
        Write-Host ""
        Write-Host "WARNING: some figures differ from docs\demo-script-react.md (or could not be read). Do not quote the ones marked MISSING." -ForegroundColor Yellow
    }
}

Say ""
Say "Ready: $webUrl"
Say "  Stop it afterwards with demo\stop-demo.cmd. Logs: $state"
Say "  Each demo family you open is a private copy, so clicking Save is safe."
if (-not $NoBrowser) { Start-Process $webUrl }
exit 0
