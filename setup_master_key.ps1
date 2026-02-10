# Security Setup Script - Set Master Vault Key
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SECURITY SETUP - Master Vault Key" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if master key already exists
$existingKey = $env:MASTER_VAULT_KEY

if ($existingKey) {
    Write-Host "[INFO] MASTER_VAULT_KEY already set in current session" -ForegroundColor Yellow
    Write-Host "[INFO] Current key: $($existingKey.Substring(0, 16))..." -ForegroundColor Yellow
    Write-Host ""
    
    $response = Read-Host "Do you want to generate a new key? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "[INFO] Using existing key" -ForegroundColor Green
        exit 0
    }
}

Write-Host "[SECURITY] Generating new master vault key..." -ForegroundColor Yellow

# Generate a new Fernet key using Python
$pythonExe = "C:/Users/bhumi/OneDrive/Desktop/professional/decentralized/.venv/Scripts/python.exe"
$newKey = & $pythonExe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrEmpty($newKey)) {
    Write-Host "[ERROR] Failed to generate key. Make sure Python and cryptography are installed." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "NEW MASTER VAULT KEY GENERATED" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Your master key:" -ForegroundColor Cyan
Write-Host $newKey -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "IMPORTANT: SAVE THIS KEY SECURELY!" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Copy this key to a secure location (password manager, vault)" -ForegroundColor Yellow
Write-Host "2. DO NOT commit it to version control" -ForegroundColor Yellow
Write-Host "3. You CANNOT recover files without this key!" -ForegroundColor Yellow
Write-Host ""

# Set for current session
$env:MASTER_VAULT_KEY = $newKey
Write-Host "[SUCCESS] Key set for current PowerShell session" -ForegroundColor Green
Write-Host ""

# Ask if user wants to set permanently
Write-Host "Do you want to set this key PERMANENTLY?" -ForegroundColor Cyan
Write-Host "Options:" -ForegroundColor Cyan
Write-Host "  1. Current session only (temporary - key lost on close)" -ForegroundColor White
Write-Host "  2. User environment variable (persistent for your user)" -ForegroundColor White
Write-Host "  3. System environment variable (persistent for all users - requires admin)" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Enter choice (1/2/3)"

switch ($choice) {
    "1" {
        Write-Host "[INFO] Key set for current session only" -ForegroundColor Green
        Write-Host "[WARNING] You'll need to run this script again after closing PowerShell" -ForegroundColor Yellow
    }
    "2" {
        try {
            [System.Environment]::SetEnvironmentVariable('MASTER_VAULT_KEY', $newKey, 'User')
            Write-Host "[SUCCESS] Key saved to user environment variables" -ForegroundColor Green
            Write-Host "[INFO] Key will persist across PowerShell sessions" -ForegroundColor Green
        }
        catch {
            Write-Host "[ERROR] Failed to set user environment variable: $_" -ForegroundColor Red
        }
    }
    "3" {
        try {
            [System.Environment]::SetEnvironmentVariable('MASTER_VAULT_KEY', $newKey, 'Machine')
            Write-Host "[SUCCESS] Key saved to system environment variables" -ForegroundColor Green
            Write-Host "[INFO] Key will be available to all users" -ForegroundColor Green
        }
        catch {
            Write-Host "[ERROR] Failed to set system environment variable: $_" -ForegroundColor Red
            Write-Host "[ERROR] You may need to run PowerShell as Administrator" -ForegroundColor Red
        }
    }
    default {
        Write-Host "[INFO] Key set for current session only" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SETUP COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "  1. Run .\start_backend.ps1 to start the system" -ForegroundColor White
Write-Host "  2. System will use the master key to encrypt all metadata" -ForegroundColor White
Write-Host "  3. Test by uploading a file via the web interface" -ForegroundColor White
Write-Host ""
Write-Host "To verify the key is set:" -ForegroundColor Green
Write-Host '  echo $env:MASTER_VAULT_KEY' -ForegroundColor White
Write-Host ""

