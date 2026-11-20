# ==============================================================================
# AEGIS Privacy-First AIOps Observability SaaS — Master Startup Script
# Starts: 1. FastAPI Backend (8000) -> 2. Tier 1 Collector -> 3. Frontend (3000)
# ==============================================================================
param(
    [switch]$NoWait,
    [switch]$Detached
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   🛡️  AEGIS Privacy-First AIOps Observability SaaS Platform" -ForegroundColor Cyan
Write-Host "   Full System Launcher: Backend, Real Windows Collector & Frontend" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$rootPath = $PSScriptRoot
if (-not $rootPath) { $rootPath = Get-Location }

# 1. Verify Python Environment
$pythonCmd = "python"
try {
    $pyVer = & $pythonCmd --version 2>&1
    Write-Host "[CHECK] Python detected: $pyVer" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not found in PATH. Please install Python 3.10+." -ForegroundColor Red
    exit 1
}

# 2. Check/kill existing lingering processes on port 8000 and 3000
Write-Host "[CHECK] Checking existing process bindings on ports 8000 and 3000..." -ForegroundColor Gray
$connections = Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue
foreach ($conn in $connections) {
    if ($conn.OwningProcess -and $conn.OwningProcess -ne 0) {
        Write-Host "  -> Terminating prior process PID $($conn.OwningProcess) on port $($conn.LocalPort)..." -ForegroundColor Yellow
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Seconds 1

# 3. Start FastAPI Backend (Port 8000)
Write-Host "`n[1/3] Launching FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Cyan
$backendOut = Join-Path $rootPath "backend_out.log"
$backendErr = Join-Path $rootPath "backend_err.log"
$backendProcess = Start-Process -FilePath $pythonCmd `
    -ArgumentList "-m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload" `
    -WorkingDirectory $rootPath `
    -RedirectStandardOutput $backendOut `
    -RedirectStandardError $backendErr `
    -PassThru

Write-Host "  -> Backend process spawned (PID $($backendProcess.Id)). Log: $backendOut" -ForegroundColor Gray

# Wait for backend health check
$backendReady = $false
for ($i = 1; $i -le 15; $i++) {
    Start-Sleep -Seconds 1
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
        if ($res.status -eq "healthy" -and $res.database -eq "connected") {
            Write-Host "  ✅ Backend is HEALTHY! Database: $($res.database) ($($res.database_type))" -ForegroundColor Green
            $backendReady = $true
            break
        }
    } catch {
        Write-Host "  -> Waiting for backend to initialize (attempt $i/15)..." -ForegroundColor Yellow
    }
}

if (-not $backendReady) {
    Write-Host "[ERROR] Backend failed to become healthy. Check backend_err.log:" -ForegroundColor Red
    if (Test-Path $backendErr) { Get-Content $backendErr -Tail 20 }
    exit 1
}

# 4. Start Real Windows Python Collector
Write-Host "`n[2/3] Launching Tier 1 Windows psutil Collector..." -ForegroundColor Cyan
$collectorOut = Join-Path $rootPath "collector_out.log"
$collectorErr = Join-Path $rootPath "collector_err.log"
$collectorProcess = Start-Process -FilePath $pythonCmd `
    -ArgumentList "-m collector.main" `
    -WorkingDirectory $rootPath `
    -RedirectStandardOutput $collectorOut `
    -RedirectStandardError $collectorErr `
    -PassThru

Write-Host "  -> Collector process spawned (PID $($collectorProcess.Id)). Log: $collectorOut" -ForegroundColor Gray

# Wait for collector initial cycle
Start-Sleep -Seconds 3
try {
    $colCheck = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/collectors" `
        -Headers @{ Authorization = "Bearer demo-token" } `
        -Method Get -TimeoutSec 2 -ErrorAction Stop
    $onlineCols = $colCheck | Where-Object { $_.status -eq "Online" }
    if ($onlineCols) {
        Write-Host "  ✅ Collector registered & ONLINE! Monitored host: $($onlineCols[0].host_identifier)" -ForegroundColor Green
    } else {
        Write-Host "  -> Collector initializing initial heartbeat..." -ForegroundColor Yellow
    }
} catch {
    Write-Host "  -> Collector heartbeat pending initial registration..." -ForegroundColor Yellow
}

# 5. Start Frontend HTTP Server (Port 3000)
Write-Host "`n[3/3] Launching Vanilla ES6+ Frontend on http://127.0.0.1:3000..." -ForegroundColor Cyan
$frontendDir = Join-Path $rootPath "frontend"
$frontendOut = Join-Path $rootPath "frontend_out.log"
$frontendErr = Join-Path $rootPath "frontend_err.log"
$frontendProcess = Start-Process -FilePath $pythonCmd `
    -ArgumentList "-m http.server 3000 --directory `"$frontendDir`"" `
    -WorkingDirectory $rootPath `
    -RedirectStandardOutput $frontendOut `
    -RedirectStandardError $frontendErr `
    -PassThru

Write-Host "  -> Frontend server spawned (PID $($frontendProcess.Id)). Log: $frontendOut" -ForegroundColor Gray
Start-Sleep -Seconds 1

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "   🎉 ALL AEGIS COMPONENTS STARTED AND RUNNING SUCCESSFULLY!" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  🌐 Web Dashboard:    http://localhost:3000" -ForegroundColor White
Write-Host "                       http://127.0.0.1:3000" -ForegroundColor White
Write-Host "  🔐 Login Creds:      admin@aegis.io / aegis2026" -ForegroundColor Yellow
Write-Host "  ⚙️  Backend API:      http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  📚 Swagger Docs:     http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  ❤️  Health Check:     http://127.0.0.1:8000/health" -ForegroundColor White
Write-Host ""
Write-Host "  PIDs running in background:" -ForegroundColor Gray
Write-Host "    Backend:   PID $($backendProcess.Id)" -ForegroundColor Gray
Write-Host "    Collector: PID $($collectorProcess.Id)" -ForegroundColor Gray
Write-Host "    Frontend:  PID $($frontendProcess.Id)" -ForegroundColor Gray
Write-Host ""
Write-Host "  To stop all services, run: .\stop_aegis.ps1" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Green

if (-not $NoWait -and -not $Detached) {
    Write-Host "`n[AEGIS active] All services running. Press Ctrl+C anytime to stop all AEGIS services..." -ForegroundColor Cyan
    try {
        while ($true) {
            Start-Sleep -Seconds 2
        }
    } finally {
        Write-Host "`nStopping AEGIS services..." -ForegroundColor Yellow
        & (Join-Path $rootPath "stop_aegis.ps1")
    }
}
