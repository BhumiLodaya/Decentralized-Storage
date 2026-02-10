# Decentralized Storage System - Stop Script
# Usage: .\stop_system.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Stopping Decentralized Storage System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Find all Python processes running node.py or main.py
$processes = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*node.py*" -or $_.CommandLine -like "*main.py*"
}

if ($processes) {
    Write-Host "Found $($processes.Count) Python service(s) running..." -ForegroundColor Yellow
    Write-Host ""
    
    foreach ($proc in $processes) {
        Write-Host "Stopping process $($proc.Id)..." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    
    Start-Sleep -Seconds 2
    
    Write-Host ""
    Write-Host "✓ All services stopped" -ForegroundColor Green
} else {
    Write-Host "No running services found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Verifying shutdown..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ports = @(8001, 8002, 8003, 8004, 8005, 8000)
$anyRunning = $false

foreach ($port in $ports) {
    $connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    
    if ($connection) {
        Write-Host "⚠ Port $port still in use" -ForegroundColor Red
        $anyRunning = $true
    }
}

if (-not $anyRunning) {
    Write-Host "✓ All ports freed - System fully stopped" -ForegroundColor Green
}

Write-Host ""
