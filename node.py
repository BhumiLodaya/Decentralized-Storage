import argparse
import os
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI()

# Storage directory
STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)


@app.post("/upload/{shard_id}")
async def upload_shard(shard_id: str, file: UploadFile = File(...)):
    """
    Upload a shard file to local storage.
    """
    try:
        file_path = STORAGE_DIR / shard_id
        
        # Save the uploaded file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return {
            "status": "success",
            "shard_id": shard_id,
            "size": len(content)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/download/{shard_id}")
async def download_shard(shard_id: str):
    """
    Download a shard file from local storage.
    """
    file_path = STORAGE_DIR / shard_id
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Shard {shard_id} not found")
    
    return FileResponse(
        path=file_path,
        filename=shard_id,
        media_type="application/octet-stream"
    )


@app.delete("/delete/{shard_id}")
async def delete_shard(shard_id: str):
    """
    Delete a shard file from local storage (for rollback operations).
    """
    try:
        file_path = STORAGE_DIR / shard_id
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Shard {shard_id} not found")
        
        # Delete the file
        os.remove(file_path)
        
        return {
            "status": "success",
            "message": f"Shard {shard_id} deleted",
            "shard_id": shard_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@app.get("/heartbeat")
async def heartbeat():
    """
    Health check endpoint to verify node is active.
    """
    return {"status": "online"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a storage node server")
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port number to run the server on (default: 8001)"
    )
    
    args = parser.parse_args()
    
    print(f"Starting storage node on port {args.port}...")
    uvicorn.run(app, host="0.0.0.0", port=args.port)
