# ==============================================================================
# AEGIS Stop Script — Gracefully stops Backend, Collector, and Frontend
# ==============================================================================

Write-Host "Stopping AEGIS platform services..." -ForegroundColor Yellow

# Kill ports 8000, 8001, and 3000
$ports = @(8000, 8001, 3000)
foreach ($p in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        if ($conn.OwningProcess -and $conn.OwningProcess -ne 0) {
            Write-Host "  -> Stopping process PID $($conn.OwningProcess) on port $p..." -ForegroundColor Gray
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}

# Kill any python processes running collector
$procs = Get-WmiObject Win32_Process -Filter "name = 'python.exe'" -ErrorAction SilentlyContinue
foreach ($p in $procs) {
    if ($p.CommandLine -like "*collector*") {
        Write-Host "  -> Stopping Collector PID $($p.ProcessId)..." -ForegroundColor Gray
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "✅ All AEGIS services stopped." -ForegroundColor Green
