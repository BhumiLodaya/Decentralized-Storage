# Decentralized Storage System - Quick Start Guide

## Prerequisites
All dependencies should already be installed:
- cryptography
- zfec
- httpx
- fastapi
- uvicorn
- python-multipart

## Running the System

### Step 1: Start All Storage Nodes (5 terminals or background processes)

```powershell
# Terminal 1 - Node 1
python node.py --port 8001

# Terminal 2 - Node 2
python node.py --port 8002

# Terminal 3 - Node 3
python node.py --port 8003

# Terminal 4 - Node 4
python node.py --port 8004

# Terminal 5 - Node 5
python node.py --port 8005
```

**OR** start all in background (PowerShell):
```powershell
Start-Process python -ArgumentList "node.py --port 8001" -NoNewWindow
Start-Process python -ArgumentList "node.py --port 8002" -NoNewWindow
Start-Process python -ArgumentList "node.py --port 8003" -NoNewWindow
Start-Process python -ArgumentList "node.py --port 8004" -NoNewWindow
Start-Process python -ArgumentList "node.py --port 8005" -NoNewWindow
```

### Step 2: Start the Gateway API

```powershell
python main.py
```

The gateway will start on: **http://localhost:8000**

## API Endpoints

### 1. Upload File
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@myfile.pdf"
```

### 2. List All Files
```bash
curl "http://localhost:8000/files"
```

### 3. Download File
```bash
curl "http://localhost:8000/download/myfile.pdf" --output myfile.pdf
```

### 4. Check System Health
```bash
curl "http://localhost:8000/health"
```

### 5. Get File Metadata
```bash
curl "http://localhost:8000/metadata/myfile.pdf"
```

## Testing from Browser

Open: **http://localhost:8000/docs**

FastAPI provides an interactive Swagger UI where you can:
- Upload files via the web interface
- Test all endpoints
- See request/response formats

## React Frontend Integration

Your React app can use the API like this:

```javascript
// Upload file
const formData = new FormData();
formData.append('file', selectedFile);

const response = await fetch('http://localhost:8000/upload', {
  method: 'POST',
  body: formData
});

// List files
const files = await fetch('http://localhost:8000/files').then(r => r.json());

// Download file
window.location.href = `http://localhost:8000/download/${filename}`;

// Check health
const health = await fetch('http://localhost:8000/health').then(r => r.json());
```

## System Architecture

```
┌─────────────────┐
│  React Frontend │
│  (Port 3000)    │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│  Gateway API    │  ← main.py
│  (Port 8000)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Orchestrator   │  ← orchestrator.py
└────────┬────────┘
         │
    ┌────┴────┬────────┬────────┬────────┐
    ▼         ▼        ▼        ▼        ▼
┌──────┐  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│Node 1│  │Node 2│ │Node 3│ │Node 4│ │Node 5│
│:8001 │  │:8002 │ │:8003 │ │:8004 │ │:8005 │
└──────┘  └──────┘ └──────┘ └──────┘ └──────┘
```

## Security Features

✓ **Encryption**: All data encrypted with Fernet (AES-128 + HMAC)
✓ **Sharding**: Files split into 5 pieces (any 3 needed for recovery)
✓ **Integrity**: SHA-256 hashes verify each shard
✓ **Fault Tolerance**: System works even if 2 nodes are down
✓ **Privacy**: No single node has complete data

## Troubleshooting

**Error: "Insufficient healthy nodes"**
- Check all 5 nodes are running: `netstat -ano | findstr "800[1-5]"`
- Restart failed nodes

**Error: "Module not found"**
- Install dependencies: `pip install httpx fastapi uvicorn python-multipart cryptography zfec`

**CORS Issues with React**
- The gateway has CORS enabled for all origins
- In production, update `allow_origins` in main.py to your specific domain

## Stop All Services

```powershell
# Find Python processes
Get-Process python | Stop-Process -Force
```

## Configuration File

The system uses a configuration file to store the encryption key and other settings.

### File: `config.json`
{
  "encryption_key": "ra0vMt_JUZRjC-R7yWaTsXn15g7zxNbBAorMUENjijY=",  // ⚠️ EXPOSED!
  "node_count": 5,
  "shard_count": 3
}

### File: `main.py`
```
from config import config

# Use the encryption key from config.json
encryption_key = config["encryption_key"]
```
