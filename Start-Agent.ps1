# Start-Agent.ps1
# Launches the full FB Content Agent stack with one double-click.
# Starts: API server, automation scheduler, and opens the dashboard.

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force $logDir | Out-Null

Write-Host ""
Write-Host "  FB Content Agent — Starting All Services" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor Cyan

# ── 1. API Server ─────────────────────────────────────────────────────────────
Write-Host "  [1/3] Starting API on port 8002..." -ForegroundColor Yellow
$api = Start-Process -PassThru -WindowStyle Minimized `
    -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "content_api:app", "--port", "8002" `
    -WorkingDirectory $root `
    -RedirectStandardOutput (Join-Path $logDir "api.log") `
    -RedirectStandardError  (Join-Path $logDir "api.err")

$api.Id | Out-File (Join-Path $logDir "api.pid") -NoNewline
Write-Host "    PID $($api.Id) — logs/api.log" -ForegroundColor Green

# Wait for API to be ready
$ready = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Milliseconds 800
    try {
        $r = Invoke-RestMethod "http://localhost:8002/content" -ErrorAction Stop
        $ready = $true
        break
    } catch {}
}

if (-not $ready) {
    Write-Host "  API did not start in time. Check logs/api.err" -ForegroundColor Red
    exit 1
}
Write-Host "    API ready." -ForegroundColor Green

# ── 2. Automation Scheduler ───────────────────────────────────────────────────
Write-Host "  [2/3] Starting automation scheduler..." -ForegroundColor Yellow
$auto = Start-Process -PassThru -WindowStyle Minimized `
    -FilePath "python" `
    -ArgumentList "automate.py" `
    -WorkingDirectory $root `
    -RedirectStandardOutput (Join-Path $logDir "automate.log") `
    -RedirectStandardError  (Join-Path $logDir "automate.err")

$auto.Id | Out-File (Join-Path $logDir "automate.pid") -NoNewline
Write-Host "    PID $($auto.Id) — logs/automate.log" -ForegroundColor Green

# ── 3. Dashboard ──────────────────────────────────────────────────────────────
Write-Host "  [3/3] Opening dashboard..." -ForegroundColor Yellow
$dashDir = Join-Path $root "dashboard"
if (Test-Path $dashDir) {
    $vite = Start-Process -PassThru -WindowStyle Minimized `
        -FilePath "cmd" `
        -ArgumentList "/c", "npm run dev > `"$logDir\vite.log`" 2>&1" `
        -WorkingDirectory $dashDir
    $vite.Id | Out-File (Join-Path $logDir "vite.pid") -NoNewline
    Start-Sleep -Seconds 4
    Start-Process "http://localhost:5173"
    Write-Host "    Dashboard: http://localhost:5173 — logs/vite.log" -ForegroundColor Green
} else {
    Write-Host "    No dashboard directory found — skipping." -ForegroundColor DarkGray
}

# ── Status ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  All services running." -ForegroundColor Cyan
Write-Host "  API      : http://localhost:8002/docs" -ForegroundColor White
Write-Host "  Dashboard: http://localhost:5173" -ForegroundColor White
Write-Host "  Logs     : $logDir" -ForegroundColor White
Write-Host ""
Write-Host "  To stop everything, run: .\Stop-Agent.ps1" -ForegroundColor DarkGray
Write-Host ""
