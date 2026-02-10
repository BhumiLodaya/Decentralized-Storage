# Start Frontend Development Server
Write-Host "Starting Decentralized Storage Frontend..." -ForegroundColor Cyan

# Refresh PATH to include Node.js
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Navigate to frontend directory
Set-Location -Path "$PSScriptRoot\frontend"

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install
}

# Start the development server
Write-Host "`nStarting Vite dev server on http://localhost:3000" -ForegroundColor Green
npm run dev
