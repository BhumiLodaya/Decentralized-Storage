# Decentralized Storage System - Startup Script
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Decentralized Storage System - Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$PYTHON_EXE = "C:/Users/bhumi/OneDrive/Desktop/professional/decentralized/.venv/Scripts/python.exe"

# Start storage nodes
Write-Host "[1/6] Starting Storage Node 1 (port 8001)..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath $PYTHON_EXE -ArgumentList "node.py --port 8001"
Start-Sleep -Seconds 1

Write-Host "[2/6] Starting Storage Node 2 (port 8002)..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath $PYTHON_EXE -ArgumentList "node.py --port 8002"
Start-Sleep -Seconds 1

Write-Host "[3/6] Starting Storage Node 3 (port 8003)..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath $PYTHON_EXE -ArgumentList "node.py --port 8003"
Start-Sleep -Seconds 1

Write-Host "[4/6] Starting Storage Node 4 (port 8004)..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath $PYTHON_EXE -ArgumentList "node.py --port 8004"
Start-Sleep -Seconds 1

Write-Host "[5/6] Starting Storage Node 5 (port 8005)..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath $PYTHON_EXE -ArgumentList "node.py --port 8005"
Start-Sleep -Seconds 2

Write-Host "[6/6] Starting Gateway API (port 8000)..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath $PYTHON_EXE -ArgumentList "main.py"

Write-Host ""
Write-Host "Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check if services are running
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Service Status Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$ports = @(8001, 8002, 8003, 8004, 8005, 8000)
$portNames = @("Storage Node 1", "Storage Node 2", "Storage Node 3", "Storage Node 4", "Storage Node 5", "Gateway API")

for ($i = 0; $i -lt $ports.Length; $i++) {
    $port = $ports[$i]
    $name = $portNames[$i]
    
    $connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    
    if ($connection) {
        Write-Host "✓ $name (port $port) - RUNNING" -ForegroundColor Green
    } else {
        Write-Host "✗ $name (port $port) - NOT RUNNING" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "System Ready!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Gateway API: http://localhost:8000" -ForegroundColor Green
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
