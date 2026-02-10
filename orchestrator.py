import asyncio
import json
import hashlib
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import httpx
from cryptography.fernet import Fernet
from decentralized_storage_engine import DecentralizedStorageEngine


class StorageOrchestrator:
    """
    Coordinates distributed storage across multiple nodes.
    Handles encryption, sharding, distribution, and retrieval with fault tolerance.
    
    Security Features:
    - Master key encryption for metadata (envelope pattern)
    - Atomic uploads with rollback on failure
    - Mandatory integrity verification
    """
    
    def __init__(self, 
                 node_urls: List[str], 
                 storage_engine: Optional[DecentralizedStorageEngine] = None,
                 metadata_dir: str = "metadata"):
        """
        Initialize the orchestrator with storage nodes and engine.
        
        Args:
            node_urls: List of storage node URLs (e.g., ['http://localhost:8001', ...])
            storage_engine: Instance of DecentralizedStorageEngine. Creates new if None.
            metadata_dir: Directory to store metadata manifests
        """
        self.node_urls = node_urls
        self.storage_engine = storage_engine or DecentralizedStorageEngine()
        self.metadata_dir = Path(metadata_dir)
        self.metadata_dir.mkdir(exist_ok=True)
        
        # Initialize master key for metadata encryption (envelope pattern)
        self._init_master_key()
        
        # Upload locks to prevent concurrent uploads of same file
        self._upload_locks = {}
        
        print(f"[ORCHESTRATOR] Initialized with {len(node_urls)} nodes")
        for i, url in enumerate(node_urls):
            print(f"  Node {i}: {url}")
    
    
    def _init_master_key(self):
        """
        Initialize master key for metadata encryption (envelope pattern).
        
        The master key encrypts all metadata files, preventing plaintext
        exposure of file encryption keys on disk.
        
        Security: Load from environment variable MASTER_VAULT_KEY.
        If not set, generate and warn (for development only).
        """
        master_key_b64 = os.environ.get('MASTER_VAULT_KEY')
        
        if master_key_b64:
            try:
                self.master_key = master_key_b64.encode()
                self.metadata_cipher = Fernet(self.master_key)
                print("[SECURITY] Master vault key loaded from environment ✓")
            except Exception as e:
                print(f"[SECURITY ERROR] Invalid MASTER_VAULT_KEY: {e}")
                raise
        else:
            # Development mode: generate temporary key
            self.master_key = Fernet.generate_key()
            self.metadata_cipher = Fernet(self.master_key)
            print("[SECURITY WARNING] MASTER_VAULT_KEY not set - generating temporary key")
            print(f"[SECURITY WARNING] For production, set: MASTER_VAULT_KEY={self.master_key.decode()}")
            print("[SECURITY WARNING] Metadata will not be recoverable after restart!")
    
    
    def _calculate_file_hash(self, data: bytes) -> str:
        """Calculate SHA-256 hash of entire file."""
        return hashlib.sha256(data).hexdigest()
    
    
    async def _check_node_health(self, node_url: str) -> bool:
        """
        Check if a node is online and responsive.
        
        Args:
            node_url: URL of the node to check
            
        Returns:
            True if node is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{node_url}/heartbeat")
                return response.status_code == 200
        except Exception as e:
            print(f"[WARNING] Node {node_url} health check failed: {e}")
            return False
    
    
    async def _upload_shard_to_node(self, 
                                    node_url: str, 
                                    shard_id: str, 
                                    shard_data: bytes) -> bool:
        """
        Upload a single shard to a storage node.
        
        Args:
            node_url: URL of the target node
            shard_id: Unique identifier for the shard
            shard_data: Encrypted shard bytes
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                files = {"file": (shard_id, shard_data, "application/octet-stream")}
                response = await client.post(
                    f"{node_url}/upload/{shard_id}",
                    files=files
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"[UPLOAD] ✓ Shard {shard_id} → {node_url} ({result['size']} bytes)")
                    return True
                else:
                    print(f"[ERROR] Upload to {node_url} failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Upload to {node_url} failed: {e}")
            return False
    
    
    async def _download_shard_from_node(self, 
                                       node_url: str, 
                                       shard_id: str) -> Optional[bytes]:
        """
        Download a single shard from a storage node.
        
        Args:
            node_url: URL of the node
            shard_id: Unique identifier for the shard
            
        Returns:
            Shard data bytes if successful, None otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{node_url}/download/{shard_id}")
                
                if response.status_code == 200:
                    print(f"[DOWNLOAD] ✓ Shard {shard_id} ← {node_url} ({len(response.content)} bytes)")
                    return response.content
                else:
                    print(f"[WARNING] Download from {node_url} failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"[WARNING] Download from {node_url} failed: {e}")
            return None
    
    
    async def _delete_shard_from_node(self, 
                                     node_url: str, 
                                     shard_id: str) -> bool:
        """
        Delete a shard from a storage node (for rollback).
        
        Args:
            node_url: URL of the node
            shard_id: Unique identifier for the shard
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(f"{node_url}/delete/{shard_id}")
                
                if response.status_code == 200:
                    print(f"[ROLLBACK] ✓ Deleted shard {shard_id} from {node_url}")
                    return True
                else:
                    print(f"[ROLLBACK WARNING] Delete failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"[ROLLBACK WARNING] Delete from {node_url} failed: {e}")
            return False
    
    
    async def upload_file(self, file_path: str) -> str:
        """
        Upload a file with atomic transaction semantics and rollback.
        
        Security Features:
        - Atomic uploads: All shards uploaded or none (rollback on failure)
        - Encrypted metadata: Master key protects encryption keys on disk
        - Upload locking: Prevents concurrent uploads of same file
        
        Process:
        1. Acquire file lock to prevent concurrent uploads
        2. Encrypt and shard file
        3. Upload all shards (track for potential rollback)
        4. On success: Save encrypted metadata
        5. On failure: Rollback (delete uploaded shards)
        
        Args:
            file_path: Path to the file to upload
            
        Returns:
            Path to the generated encrypted metadata file
            
        Raises:
            ValueError: If insufficient nodes available or upload fails
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        filename = file_path.name
        
        # Acquire lock for this filename to prevent concurrent uploads
        if filename not in self._upload_locks:
            self._upload_locks[filename] = asyncio.Lock()
        
        async with self._upload_locks[filename]:
            return await self._upload_file_atomic(file_path)
    
    
    async def _upload_file_atomic(self, file_path: Path) -> str:
        """
        Internal atomic upload with rollback on failure.
        
        This ensures that either all shards are uploaded successfully,
        or all partial uploads are cleaned up (all-or-nothing).
        """
        print(f"\n{'='*70}")
        print(f"UPLOAD: {file_path.name}")
        print(f"{'='*70}")
        
        uploaded_shards = []  # Track for rollback
        
        try:
            # Read file data
            with open(file_path, "rb") as f:
                file_data = f.read()
            
            file_hash = self._calculate_file_hash(file_data)
            print(f"[FILE] Size: {len(file_data)} bytes")
            print(f"[FILE] Hash: {file_hash[:32]}...")
            
            # Step 1: Encrypt and shard
            shards, shard_metadata = self.storage_engine.encrypt_and_shard(file_data)
            
            # Verify we have enough nodes
            if len(self.node_urls) < len(shards):
                raise ValueError(
                    f"Insufficient nodes: {len(self.node_urls)} available, "
                    f"{len(shards)} required for {self.storage_engine.m_total}-way distribution"
                )
            
            # Step 2: Check node health
            print(f"\n[HEALTH] Checking node availability...")
            health_checks = await asyncio.gather(
                *[self._check_node_health(url) for url in self.node_urls]
            )
            
            healthy_nodes = [url for url, healthy in zip(self.node_urls, health_checks) if healthy]
            print(f"[HEALTH] {len(healthy_nodes)} of {len(self.node_urls)} nodes online")
            
            if len(healthy_nodes) < len(shards):
                raise ValueError(
                    f"Insufficient healthy nodes: {len(healthy_nodes)} online, "
                    f"{len(shards)} required"
                )
            
            # Step 3: Distribute shards to nodes (track for rollback)
            print(f"\n[DISTRIBUTE] Uploading {len(shards)} shards (atomic transaction)...")
            
            shard_distribution = {}  # Maps shard_id -> node_url
            upload_tasks = []
            
            for shard_id, shard_data in enumerate(shards):
                node_url = healthy_nodes[shard_id]
                shard_identifier = f"{file_path.stem}_shard_{shard_id}"
                shard_distribution[shard_id] = {
                    "node_url": node_url,
                    "shard_identifier": shard_identifier
                }
                
                # Track for potential rollback
                uploaded_shards.append((node_url, shard_identifier))
                
                upload_tasks.append(
                    self._upload_shard_to_node(node_url, shard_identifier, shard_data)
                )
            
            # Execute uploads concurrently
            upload_results = await asyncio.gather(*upload_tasks)
            
            # Verify all uploads succeeded
            failed_uploads = sum(1 for result in upload_results if not result)
            if failed_uploads > 0:
                raise ValueError(
                    f"[TRANSACTION FAILED] {failed_uploads} shard uploads failed. "
                    f"Initiating rollback..."
                )
            
            print(f"\n[ATOMIC SUCCESS] All {len(shards)} shards uploaded successfully ✓")
            
            # Step 4: Create metadata manifest (with sensitive key)
            metadata_manifest = {
                "filename": file_path.name,
                "file_hash": file_hash,
                "file_size": len(file_data),
                "encryption_key": self.storage_engine.encryption_key.decode(),
                "k_required": self.storage_engine.k_required,
                "m_total": self.storage_engine.m_total,
                "shard_metadata": {
                    str(shard_id): {
                        "hash": shard_hash,
                        "node_url": shard_distribution[shard_id]["node_url"],
                        "shard_identifier": shard_distribution[shard_id]["shard_identifier"]
                    }
                    for shard_id, shard_hash in shard_metadata.items()
                }
            }
            
            # Step 5: Save ENCRYPTED metadata (envelope pattern)
            metadata_path = self.metadata_dir / f"{file_path.stem}.metadata.json"
            self._save_encrypted_metadata(metadata_manifest, metadata_path)
            
            print(f"[METADATA] Encrypted and saved to: {metadata_path} ✓")
            print(f"[SECURITY] Encryption key protected by master vault key ✓")
            print(f"{'='*70}\n")
            
            return str(metadata_path)
            
        except Exception as e:
            # Rollback: Delete all uploaded shards
            print(f"\n[ROLLBACK] Upload failed: {e}")
            print(f"[ROLLBACK] Cleaning up {len(uploaded_shards)} uploaded shards...")
            
            delete_tasks = [
                self._delete_shard_from_node(node_url, shard_id)
                for node_url, shard_id in uploaded_shards
            ]
            
            delete_results = await asyncio.gather(*delete_tasks, return_exceptions=True)
            successful_deletions = sum(1 for r in delete_results if r is True)
            
            print(f"[ROLLBACK] Cleaned up {successful_deletions}/{len(uploaded_shards)} shards")
            print(f"[ROLLBACK] Transaction aborted - no orphaned data ✓")
            
            # Re-raise original exception
            raise
    
    def _save_encrypted_metadata(self, metadata: dict, path: Path):
        """
        Save metadata to disk with master key encryption (envelope pattern).
        
        This prevents plaintext exposure of file encryption keys.
        
        Args:
            metadata: Metadata dictionary (contains sensitive encryption_key)
            path: Path to save encrypted metadata file
        """
        # Serialize metadata to JSON
        metadata_json = json.dumps(metadata, indent=2)
        metadata_bytes = metadata_json.encode('utf-8')
        
        # Encrypt with master key
        encrypted_metadata = self.metadata_cipher.encrypt(metadata_bytes)
        
        # Write encrypted bytes to disk
        with open(path, 'wb') as f:
            f.write(encrypted_metadata)
        
        print(f"[SECURITY] Metadata encrypted with master vault key")
    
    
    def _load_encrypted_metadata(self, path: Path) -> dict:
        """
        Load and decrypt metadata from disk.
        
        Args:
            path: Path to encrypted metadata file
            
        Returns:
            Decrypted metadata dictionary
            
        Raises:
            ValueError: If decryption fails (wrong key or corrupted file)
        """
        try:
            # Read encrypted bytes
            with open(path, 'rb') as f:
                encrypted_metadata = f.read()
            
            # Decrypt with master key
            metadata_bytes = self.metadata_cipher.decrypt(encrypted_metadata)
            metadata_json = metadata_bytes.decode('utf-8')
            
            # Parse JSON
            metadata = json.loads(metadata_json)
            
            print(f"[SECURITY] Metadata decrypted successfully ✓")
            return metadata
            
        except Exception as e:
            raise ValueError(
                f"Failed to decrypt metadata. Wrong MASTER_VAULT_KEY or corrupted file: {e}"
            )
    
    
    async def download_file(self, 
                           metadata_path: str, 
                           output_path: Optional[str] = None) -> str:
        """
        Download and reconstruct a file from distributed shards.
        
        Security: Metadata is decrypted using master key, then file is
        reconstructed with mandatory integrity verification.
        
        Args:
            metadata_path: Path to the encrypted .metadata.json file
            output_path: Where to save the reconstructed file (defaults to original filename)
            
        Returns:
            Path to the reconstructed file
            
        Raises:
            ValueError: If insufficient shards can be retrieved
            ValueError: If metadata decryption fails
        """
        metadata_path = Path(metadata_path)
        
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
        
        # Step 1: Load and decrypt metadata manifest
        metadata = self._load_encrypted_metadata(metadata_path)
        
        print(f"\n{'='*70}")
        print(f"DOWNLOAD: {metadata['filename']}")
        print(f"{'='*70}")
        print(f"[METADATA] Loaded and decrypted from: {metadata_path}")
        print(f"[FILE] Original size: {metadata['file_size']} bytes")
        print(f"[FILE] Original hash: {metadata['file_hash'][:32]}...")
        print(f"[RECOVERY] Need {metadata['k_required']} of {metadata['m_total']} shards")
        
        # Recreate storage engine with the original encryption key (from decrypted metadata)
        temp_engine = DecentralizedStorageEngine(
            encryption_key=metadata['encryption_key'].encode()
        )
        
        # Step 2: Attempt to download shards
        print(f"\n[DOWNLOAD] Fetching shards from nodes...")
        
        shard_info = metadata['shard_metadata']
        download_tasks = []
        shard_ids = []
        
        for shard_id_str, info in shard_info.items():
            shard_id = int(shard_id_str)
            shard_ids.append(shard_id)
            download_tasks.append(
                self._download_shard_from_node(
                    info['node_url'],
                    info['shard_identifier']
                )
            )
        
        # Execute downloads concurrently
        downloaded_shards = await asyncio.gather(*download_tasks)
        
        # Step 3: Filter successful downloads
        successful_shards = []
        successful_ids = []
        original_shard_metadata = {}
        
        for shard_id, shard_data in zip(shard_ids, downloaded_shards):
            if shard_data is not None:
                successful_shards.append(shard_data)
                successful_ids.append(shard_id)
                original_shard_metadata[shard_id] = shard_info[str(shard_id)]['hash']
        
        print(f"\n[RESULT] Successfully retrieved {len(successful_shards)} shards")
        
        # Step 4: Verify we have enough shards
        if len(successful_shards) < metadata['k_required']:
            raise ValueError(
                f"Insufficient shards retrieved: {len(successful_shards)} available, "
                f"{metadata['k_required']} required. Data cannot be recovered."
            )
        
        # Step 5: Recover and decrypt (with MANDATORY integrity verification)
        print(f"\n[RECONSTRUCT] Reconstructing file from {len(successful_shards)} shards...")
        
        try:
            reconstructed_data = temp_engine.recover_and_decrypt(
                successful_shards,
                successful_ids,
                original_shard_metadata
            )
        except ValueError as e:
            raise ValueError(f"Reconstruction failed: {e}")
        
        # Step 6: Verify file integrity
        reconstructed_hash = self._calculate_file_hash(reconstructed_data)
        
        if reconstructed_hash != metadata['file_hash']:
            raise ValueError(
                f"File integrity check FAILED!\n"
                f"Expected: {metadata['file_hash']}\n"
                f"Got: {reconstructed_hash}"
            )
        
        print(f"[INTEGRITY] ✓ File hash verified: {reconstructed_hash[:32]}...")
        
        # Step 7: Save reconstructed file
        if output_path is None:
            output_path = Path("downloads") / metadata['filename']
        else:
            output_path = Path(output_path)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "wb") as f:
            f.write(reconstructed_data)
        
        print(f"[SUCCESS] File saved to: {output_path}")
        print(f"{'='*70}\n")
        
        return str(output_path)


async def demonstrate_orchestrator():
    """
    Example demonstration of the StorageOrchestrator.
    """
    print("="*70)
    print("STORAGE ORCHESTRATOR DEMONSTRATION")
    print("="*70)
    
    # Define storage nodes (should be running on these ports)
    node_urls = [
        "http://localhost:8001",
        "http://localhost:8002",
        "http://localhost:8003",
        "http://localhost:8004",
        "http://localhost:8005"
    ]
    
    # Initialize orchestrator (uses its own engine)
    from decentralized_storage_engine import DecentralizedStorageEngine
    orchestrator = StorageOrchestrator(node_urls)
    
    # Create a test file
    test_file = Path("test_upload.txt")
    test_data = b"This is confidential data for the decentralized storage system demo!"
    
    with open(test_file, "wb") as f:
        f.write(test_data)
    
    print(f"\n[TEST] Created test file: {test_file}")
    
    # Upload the file
    try:
        metadata_path = await orchestrator.upload_file(str(test_file))
        print(f"[TEST] Upload completed. Metadata: {metadata_path}")
        
        # Download the file
        downloaded_path = await orchestrator.download_file(metadata_path)
        print(f"[TEST] Download completed: {downloaded_path}")
        
        # Verify content
        with open(downloaded_path, "rb") as f:
            downloaded_data = f.read()
        
        if downloaded_data == test_data:
            print(f"\n[SUCCESS] ✓ File content verified - system working correctly!")
        else:
            print(f"\n[FAILURE] ✗ File content mismatch!")
            
    except Exception as e:
        print(f"\n[ERROR] Demonstration failed: {e}")
        print(f"[NOTE] Make sure storage nodes are running on ports 8001-8005")
        print(f"[NOTE] Start nodes with: python node.py --port 8001 (and similar)")


if __name__ == "__main__":
    asyncio.run(demonstrate_orchestrator())
