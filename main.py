import asyncio
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from orchestrator import StorageOrchestrator


# Initialize FastAPI app
app = FastAPI(
    title="Decentralized Storage Gateway",
    description="REST API for distributed file storage with encryption and erasure coding",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your React app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
METADATA_DIR = Path("metadata")
DOWNLOADS_DIR = Path("downloads")
NODE_URLS = [
    "http://localhost:8001",
    "http://localhost:8002",
    "http://localhost:8003",
    "http://localhost:8004",
    "http://localhost:8005"
]

# Initialize directories
METADATA_DIR.mkdir(exist_ok=True)
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Initialize orchestrator
orchestrator = StorageOrchestrator(NODE_URLS)


@app.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "service": "Decentralized Storage Gateway",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "upload": "POST /upload",
            "list_files": "GET /files",
            "download": "GET /download/{filename}",
            "health": "GET /health"
        }
    }


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to the decentralized storage system.
    
    Process:
    1. Save uploaded file to temporary location
    2. Encrypt and shard using StorageOrchestrator
    3. Distribute shards across storage nodes
    4. Generate and save metadata manifest
    
    Returns:
        JSON with upload status, filename, and metadata path
        
    Raises:
        HTTPException 500: If upload fails
    """
    temp_file_path = None
    
    try:
        print(f"\n[API] Received upload request: {file.filename}")
        
        # Create a temporary file to store the upload
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            temp_file_path = temp_file.name
            
            # Copy uploaded file to temp location
            shutil.copyfileobj(file.file, temp_file)
            print(f"[API] Saved to temp file: {temp_file_path}")
        
        # Upload via orchestrator
        metadata_path = await orchestrator.upload_file(temp_file_path)
        
        # Get file size
        file_size = os.path.getsize(temp_file_path)
        
        print(f"[API] Upload successful: {file.filename}")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"File '{file.filename}' uploaded successfully",
                "filename": file.filename,
                "size": file_size,
                "metadata_path": metadata_path,
                "shards_distributed": orchestrator.storage_engine.m_total,
                "recovery_threshold": orchestrator.storage_engine.k_required
            }
        )
        
    except Exception as e:
        print(f"[API ERROR] Upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )
        
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                print(f"[API] Cleaned up temp file: {temp_file_path}")
            except Exception as e:
                print(f"[API WARNING] Failed to clean temp file: {e}")


@app.get("/files")
async def list_files():
    """
    List all files stored in the decentralized system.
    
    Scans the metadata directory and returns information about each file.
    
    Security: Only returns safe metadata. Encryption keys are never exposed.
    
    Returns:
        JSON array with file metadata (filename, size, upload date, etc.)
    """
    try:
        files_list = []
        
        # Scan metadata directory for encrypted metadata files
        for metadata_file in METADATA_DIR.glob("*.metadata.json"):
            try:
                # Load and decrypt metadata
                metadata = orchestrator._load_encrypted_metadata(metadata_file)
                
                # Get file stats
                file_stat = metadata_file.stat()
                upload_date = datetime.fromtimestamp(file_stat.st_ctime)
                
                # Return only SAFE metadata (no encryption keys!)
                files_list.append({
                    "filename": metadata["filename"],
                    "file_hash": metadata["file_hash"][:16] + "...",
                    "size": metadata["file_size"],
                    "upload_date": upload_date.isoformat(),
                    "metadata_file": metadata_file.name,
                    "shards_total": metadata["m_total"],
                    "shards_required": metadata["k_required"],
                    "shard_locations": [
                        info["node_url"] 
                        for info in metadata["shard_metadata"].values()
                    ]
                    # SECURITY: encryption_key explicitly excluded
                })
                
            except Exception as e:
                print(f"[API WARNING] Failed to read metadata {metadata_file}: {e}")
                continue
        
        # Sort by upload date (newest first)
        files_list.sort(key=lambda x: x["upload_date"], reverse=True)
        
        print(f"[API] Returning {len(files_list)} files")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "count": len(files_list),
                "files": files_list
            }
        )
        
    except Exception as e:
        print(f"[API ERROR] Failed to list files: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list files: {str(e)}"
        )


@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download a file from the decentralized storage system.
    
    Process:
    1. Locate encrypted metadata file for the requested filename
    2. Decrypt metadata using master vault key
    3. Retrieve shards from storage nodes
    4. Reconstruct and decrypt file with mandatory integrity verification
    5. Stream file to browser
    
    Args:
        filename: Name of the file to download
        
    Returns:
        File stream for browser download
        
    Raises:
        HTTPException 404: If metadata not found
        HTTPException 500: If download/reconstruction fails
    """
    try:
        print(f"\n[API] Download request: {filename}")
        
        # Find encrypted metadata file
        metadata_files = list(METADATA_DIR.glob("*.metadata.json"))
        metadata_path = None
        
        for mf in metadata_files:
            try:
                # Decrypt and check filename
                metadata = orchestrator._load_encrypted_metadata(mf)
                if metadata["filename"] == filename:
                    metadata_path = mf
                    break
            except Exception as e:
                print(f"[API WARNING] Failed to decrypt {mf}: {e}")
                continue
        
        if not metadata_path:
            print(f"[API ERROR] Metadata not found for: {filename}")
            raise HTTPException(
                status_code=404,
                detail=f"File '{filename}' not found in storage system"
            )
        
        print(f"[API] Found metadata: {metadata_path}")
        
        # Download and reconstruct via orchestrator
        output_path = DOWNLOADS_DIR / filename
        recovered_file = await orchestrator.download_file(
            str(metadata_path),
            str(output_path)
        )
        
        print(f"[API] File reconstructed: {recovered_file}")
        
        # Return file for download
        return FileResponse(
            path=recovered_file,
            filename=filename,
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API ERROR] Download failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Download failed: {str(e)}"
        )


@app.get("/health")
async def check_health():
    """
    Check the health status of all storage nodes.
    
    Pings each node's /heartbeat endpoint to verify availability.
    Returns comprehensive system health information.
    
    Returns:
        JSON with overall system health and individual node status
    """
    try:
        print("[API] Health check requested")
        
        # Check each node
        node_status = []
        
        for node_url in NODE_URLS:
            is_healthy = await orchestrator._check_node_health(node_url)
            
            node_status.append({
                "url": node_url,
                "status": "online" if is_healthy else "offline",
                "healthy": is_healthy
            })
        
        # Calculate overall system health
        healthy_count = sum(1 for node in node_status if node["healthy"])
        total_nodes = len(node_status)
        min_required = orchestrator.storage_engine.k_required
        
        # Determine system status
        if healthy_count >= orchestrator.storage_engine.m_total:
            system_status = "optimal"
            can_store = True
            can_retrieve = True
        elif healthy_count >= min_required:
            system_status = "degraded"
            can_store = False
            can_retrieve = True
        else:
            system_status = "critical"
            can_store = False
            can_retrieve = False
        
        result = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "system_status": system_status,
            "nodes_online": healthy_count,
            "nodes_total": total_nodes,
            "nodes_required_for_storage": orchestrator.storage_engine.m_total,
            "nodes_required_for_retrieval": min_required,
            "capabilities": {
                "can_store_new_files": can_store,
                "can_retrieve_files": can_retrieve
            },
            "nodes": node_status
        }
        
        print(f"[API] Health: {healthy_count}/{total_nodes} nodes online ({system_status})")
        
        return JSONResponse(status_code=200, content=result)
        
    except Exception as e:
        print(f"[API ERROR] Health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )


@app.get("/metadata/{filename}")
async def get_metadata(filename: str):
    """
    Get detailed metadata for a specific file.
    
    Security: Encryption key is redacted from response.
    
    Args:
        filename: Name of the file
        
    Returns:
        JSON with complete metadata (excluding encryption key)
    """
    try:
        # Find encrypted metadata file
        metadata_files = list(METADATA_DIR.glob("*.metadata.json"))
        
        for mf in metadata_files:
            try:
                # Decrypt metadata
                metadata = orchestrator._load_encrypted_metadata(mf)
                
                if metadata["filename"] == filename:
                    # SECURITY: Redact encryption key before returning
                    safe_metadata = metadata.copy()
                    safe_metadata["encryption_key"] = "[REDACTED - Protected by Master Vault Key]"
                    
                    return JSONResponse(
                        status_code=200,
                        content={
                            "status": "success",
                            "metadata": safe_metadata
                        }
                    )
            except Exception as e:
                print(f"[API WARNING] Failed to decrypt {mf}: {e}")
                continue
        
        raise HTTPException(
            status_code=404,
            detail=f"Metadata for '{filename}' not found"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve metadata: {str(e)}"
        )


if __name__ == "__main__":
    print("="*70)
    print("DECENTRALIZED STORAGE GATEWAY")
    print("="*70)
    print(f"\nStorage Nodes: {len(NODE_URLS)}")
    for i, url in enumerate(NODE_URLS, 1):
        print(f"  {i}. {url}")
    
    print(f"\nMetadata Directory: {METADATA_DIR.absolute()}")
    print(f"Downloads Directory: {DOWNLOADS_DIR.absolute()}")
    
    print("\n" + "="*70)
    print("Starting Gateway API Server...")
    print("="*70)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
