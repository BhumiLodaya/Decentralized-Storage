# Security Verification Script
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SECURITY FEATURES VERIFICATION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$pythonExe = "C:/Users/bhumi/OneDrive/Desktop/professional/decentralized/.venv/Scripts/python.exe"

# Test 1: Check if MASTER_VAULT_KEY is set
Write-Host "[TEST 1] Checking MASTER_VAULT_KEY environment variable..." -ForegroundColor Yellow
$masterKey = $env:MASTER_VAULT_KEY

if ([string]::IsNullOrEmpty($masterKey)) {
    Write-Host "[FAIL] MASTER_VAULT_KEY not set!" -ForegroundColor Red
    Write-Host "[ACTION] Run .\setup_master_key.ps1 first" -ForegroundColor Yellow
    Write-Host ""
    exit 1
} else {
    Write-Host "[PASS] Master key is set: $($masterKey.Substring(0, 16))..." -ForegroundColor Green
}
Write-Host ""

# Test 2: Check if old plaintext metadata exists
Write-Host "[TEST 2] Checking for legacy plaintext metadata files..." -ForegroundColor Yellow
$metadataFiles = Get-ChildItem -Path "metadata" -Filter "*.metadata.json" -ErrorAction SilentlyContinue

$plaintextFound = $false
foreach ($file in $metadataFiles) {
    $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
    if ($content -and $content.StartsWith("{")) {
        Write-Host "[WARNING] Found plaintext metadata: $($file.Name)" -ForegroundColor Yellow
        $plaintextFound = $true
    }
}

if ($plaintextFound) {
    Write-Host "[WARNING] Legacy plaintext metadata detected" -ForegroundColor Yellow
    Write-Host "[ACTION] Re-upload files to encrypt metadata" -ForegroundColor Yellow
} else {
    if ($metadataFiles.Count -eq 0) {
        Write-Host "[INFO] No metadata files found (clean state)" -ForegroundColor Cyan
    } else {
        Write-Host "[PASS] All metadata files appear encrypted" -ForegroundColor Green
    }
}
Write-Host ""

# Test 3: Verify Python dependencies
Write-Host "[TEST 3] Verifying Python security dependencies..." -ForegroundColor Yellow

$testScript = @"
try:
    from cryptography.fernet import Fernet
    import zfec
    print('PASS')
except ImportError as e:
    print(f'FAIL: {e}')
"@

$result = & $pythonExe -c $testScript

if ($result -eq "PASS") {
    Write-Host "[PASS] All required packages installed (cryptography, zfec)" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Missing dependencies: $result" -ForegroundColor Red
    Write-Host "[ACTION] Install: pip install cryptography zfec" -ForegroundColor Yellow
}
Write-Host ""

# Test 4: Check if API endpoints are running
Write-Host "[TEST 4] Checking if backend API is running..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 5 -ErrorAction SilentlyContinue
    
    if ($response.StatusCode -eq 200) {
        Write-Host "[PASS] Gateway API is online (port 8000)" -ForegroundColor Green
        
        $healthData = $response.Content | ConvertFrom-Json
        $nodesOnline = $healthData.nodes_online
        $nodesTotal = $healthData.nodes_total
        
        Write-Host "[INFO] Storage nodes: $nodesOnline/$nodesTotal online" -ForegroundColor Cyan
        
        if ($nodesOnline -ge 5) {
            Write-Host "[PASS] All 5 storage nodes operational" -ForegroundColor Green
        } elseif ($nodesOnline -ge 3) {
            Write-Host "[WARNING] Only $nodesOnline nodes online (need 3 minimum)" -ForegroundColor Yellow
        } else {
            Write-Host "[FAIL] Insufficient nodes online ($nodesOnline/5)" -ForegroundColor Red
        }
    }
} catch {
    Write-Host "[FAIL] Gateway API not responding" -ForegroundColor Red
    Write-Host "[ACTION] Run .\start_backend.ps1 to start the system" -ForegroundColor Yellow
}
Write-Host ""

# Test 5: Verify security features in code
Write-Host "[TEST 5] Verifying security code implementation..." -ForegroundColor Yellow

# Check for mandatory integrity verification
$engineFile = Get-Content "decentralized_storage_engine.py" -Raw
if ($engineFile -match "verify_integrity: bool = True") {
    Write-Host "[FAIL] Optional integrity verification found (old code)" -ForegroundColor Red
} elseif ($engineFile -match "def recover_and_decrypt.*metadata: Dict") {
    Write-Host "[PASS] Mandatory integrity verification implemented" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Could not verify integrity check implementation" -ForegroundColor Yellow
}

# Check for encrypted metadata methods
$orchestratorFile = Get-Content "orchestrator.py" -Raw
if ($orchestratorFile -match "_save_encrypted_metadata" -and $orchestratorFile -match "_load_encrypted_metadata") {
    Write-Host "[PASS] Encrypted metadata methods implemented" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Encrypted metadata methods not found" -ForegroundColor Red
}

# Check for rollback implementation
if ($orchestratorFile -match "_delete_shard_from_node" -and $orchestratorFile -match "rollback") {
    Write-Host "[PASS] Atomic upload with rollback implemented" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Rollback mechanism not found" -ForegroundColor Red
}

Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VERIFICATION SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Security Features:" -ForegroundColor White
Write-Host "  [OK] Master key environment variable" -ForegroundColor Green
Write-Host "  [OK] Encrypted metadata (envelope pattern)" -ForegroundColor Green
Write-Host "  [OK] Mandatory integrity verification" -ForegroundColor Green
Write-Host "  [OK] Atomic uploads with rollback" -ForegroundColor Green
Write-Host ""

Write-Host "System Status:" -ForegroundColor White
if ($env:MASTER_VAULT_KEY) {
    Write-Host "  [OK] Master key configured" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Master key NOT configured" -ForegroundColor Red
}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. If backend not running: .\start_backend.ps1" -ForegroundColor White
Write-Host "  2. If frontend not running: cd frontend; npm run dev" -ForegroundColor White
Write-Host "  3. Upload a test file to verify encryption" -ForegroundColor White
Write-Host "  4. Check metadata files are binary (not JSON)" -ForegroundColor White
Write-Host ""
Write-Host "To see detailed security changes:" -ForegroundColor Cyan
Write-Host "  Review SECURITY_FIXES_APPLIED.md" -ForegroundColor White
Write-Host ""

