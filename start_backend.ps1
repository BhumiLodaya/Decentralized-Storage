# Start Backend System
Write-Host "Starting Decentralized Storage Backend..." -ForegroundColor Cyan

$PYTHON = "C:/Users/bhumi/OneDrive/Desktop/professional/decentralized/.venv/Scripts/python.exe"

Write-Host "Starting 5 storage nodes..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath $PYTHON -ArgumentList "node.py --port 8001"
Start-Sleep -Seconds 1
Start-Process -NoNewWindow -FilePath $PYTHON -ArgumentList "node.py --port 8002"
Start-Sleep -Seconds 1
Start-Process -NoNewWindow -FilePath $PYTHON -ArgumentList "node.py --port 8003"
Start-Sleep -Seconds 1
Start-Process -NoNewWindow -FilePath $PYTHON -ArgumentList "node.py --port 8004"
Start-Sleep -Seconds 1
Start-Process -NoNewWindow -FilePath $PYTHON -ArgumentList "node.py --port 8005"
Start-Sleep -Seconds 2

Write-Host "Starting API Gateway..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath $PYTHON -ArgumentList "main.py"

Write-Host ""
Write-Host "Backend started on http://localhost:8000" -ForegroundColor Green
Write-Host "Refresh your browser to see nodes go online!" -ForegroundColor Green
