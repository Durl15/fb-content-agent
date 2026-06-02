# Stop-Agent.ps1 — gracefully stops all FB Content Agent processes

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $root "logs"

Write-Host "  Stopping FB Content Agent..." -ForegroundColor Yellow

foreach ($svc in @("api", "automate", "vite")) {
    $pidFile = Join-Path $logDir "$svc.pid"
    if (Test-Path $pidFile) {
        $id = Get-Content $pidFile
        try {
            Stop-Process -Id $id -Force -ErrorAction Stop
            Write-Host "  [stopped] $svc (PID $id)" -ForegroundColor Green
        } catch {
            Write-Host "  [gone]    $svc (PID $id already exited)" -ForegroundColor DarkGray
        }
        Remove-Item $pidFile -ErrorAction SilentlyContinue
    }
}

# Also kill anything still on the ports
@(8002, 5173) | ForEach-Object {
    $conns = Get-NetTCPConnection -LocalPort $_ -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "  Done." -ForegroundColor Cyan
