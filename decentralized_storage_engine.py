import hashlib
from typing import Dict, List, Tuple, Optional
from cryptography.fernet import Fernet
import zfec


class DecentralizedStorageEngine:
    """
    Secure storage engine implementing encryption, sharding, and integrity verification.
    """
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        Initialize the storage engine with an encryption key.
        
        Args:
            encryption_key: Fernet encryption key. If None, generates a new key.
        
        Security Note: In production, store this key securely (HSM, key vault, etc.)
        """
        if encryption_key is None:
            self.encryption_key = Fernet.generate_key()
            print(f"[SECURITY] New encryption key generated: {self.encryption_key.decode()}")
        else:
            self.encryption_key = encryption_key
        
        self.cipher = Fernet(self.encryption_key)
        
        # Erasure coding parameters: k=3 shards required, m=5 total shards
        self.k_required = 3  # Minimum shards needed for reconstruction
        self.m_total = 5     # Total shards created
    
    
    def _calculate_hash(self, data: bytes) -> str:
        """
        Calculate SHA-256 hash for integrity verification.
        
        Args:
            data: Byte string to hash
            
        Returns:
            Hexadecimal string representation of the hash
            
        Security Note: SHA-256 provides cryptographic integrity verification
        """
        return hashlib.sha256(data).hexdigest()
    
    
    def encrypt_and_shard(self, plaintext: bytes) -> Tuple[List[bytes], Dict[int, str]]:
        """
        Encrypt data and split into redundant shards with integrity metadata.
        
        Security Flow:
        1. Encrypt plaintext using Fernet (AES-128 in CBC mode with HMAC)
        2. Shard encrypted data using erasure coding (zfec)
        3. Generate SHA-256 hash for each shard (integrity verification)
        4. Store hashes in metadata for later verification
        
        Args:
            plaintext: Original data to protect
            
        Returns:
            Tuple of (shard_list, metadata_dict)
            - shard_list: List of 5 encrypted shards
            - metadata_dict: Dictionary mapping shard_id -> SHA-256 hash
            
        Security Properties:
        - Confidentiality: Fernet encryption protects data at rest
        - Availability: Any 3 of 5 shards can reconstruct data
        - Integrity: SHA-256 hashes detect tampering
        """
        print(f"\n[ENCRYPT] Encrypting {len(plaintext)} bytes of plaintext...")
        
        # Step 1: Client-side encryption
        # Fernet provides authenticated encryption (AES-128 + HMAC-SHA256)
        encrypted_data = self.cipher.encrypt(plaintext)
        print(f"[ENCRYPT] Encrypted data size: {len(encrypted_data)} bytes")
        
        # Step 2: Data sharding with erasure coding
        # Create encoder: k=3 required shards, m=5 total shards
        encoder = zfec.Encoder(self.k_required, self.m_total)
        
        # zfec requires input size to be divisible by k
        # Pad if necessary
        padding_length = (self.k_required - (len(encrypted_data) % self.k_required)) % self.k_required
        padded_data = encrypted_data + b'\x00' * padding_length
        
        # Split into k equal chunks for encoding
        chunk_size = len(padded_data) // self.k_required
        chunks = [padded_data[i:i+chunk_size] for i in range(0, len(padded_data), chunk_size)]
        
        # Encode chunks into m shards
        shards = encoder.encode(chunks)
        print(f"[SHARD] Created {len(shards)} shards, each {len(shards[0])} bytes")
        print(f"[SHARD] Redundancy: Any {self.k_required} of {self.m_total} shards can reconstruct data")
        
        # Step 3: Integrity verification - calculate SHA-256 for each shard
        metadata = {}
        for shard_id, shard in enumerate(shards):
            shard_hash = self._calculate_hash(shard)
            metadata[shard_id] = shard_hash
            print(f"[INTEGRITY] Shard {shard_id} hash: {shard_hash[:16]}...")
        
        return list(shards), metadata
    
    
    def recover_and_decrypt(self, 
                           shards: List[bytes], 
                           shard_ids: List[int],
                           metadata: Dict[int, str]) -> bytes:
        """
        Verify shard integrity, reconstruct encrypted data, and decrypt.
        
        Security Flow:
        1. MANDATORY integrity verification using SHA-256 hash
        2. Detect tampering - abort if hash mismatch found
        3. Reconstruct encrypted data using erasure decoding
        4. Decrypt using Fernet to recover plaintext
        
        Args:
            shards: List of available shards (at least k_required)
            shard_ids: Corresponding shard IDs
            metadata: Dictionary with expected SHA-256 hashes
            
        Returns:
            Original plaintext bytes
            
        Raises:
            ValueError: If integrity verification fails (tampering detected)
            ValueError: If insufficient shards provided
            
        Security Properties:
        - Tamper Detection: MANDATORY SHA-256 verification before reconstruction
        - Fail-Safe: Abort on any integrity violation
        - Confidentiality: Decryption only after integrity verified
        
        Note: Integrity verification is ALWAYS enforced and cannot be bypassed.
        """
        print(f"\n[RECOVER] Attempting recovery with {len(shards)} shards (IDs: {shard_ids})")
        
        # Step 1: Verify minimum shard requirement
        if len(shards) < self.k_required:
            raise ValueError(
                f"[SECURITY ERROR] Insufficient shards: {len(shards)} provided, "
                f"{self.k_required} required for reconstruction"
            )
        
        # Step 2: MANDATORY Integrity verification - detect tampering
        print("[INTEGRITY] Verifying shard integrity (MANDATORY)...")
        for shard_id, shard in zip(shard_ids, shards):
            expected_hash = metadata.get(shard_id)
            if expected_hash is None:
                raise ValueError(
                    f"[SECURITY ERROR] No metadata found for shard {shard_id}. "
                    f"Possible data corruption or missing metadata."
                )
            
            actual_hash = self._calculate_hash(shard)
            
            if actual_hash != expected_hash:
                # CRITICAL: Tampering detected
                print(f"[SECURITY ALERT] Shard {shard_id} INTEGRITY VIOLATION!")
                print(f"  Expected: {expected_hash}")
                print(f"  Actual:   {actual_hash}")
                raise ValueError(
                    f"[SECURITY ERROR] Shard {shard_id} integrity check FAILED. "
                    f"Tampering detected! Aborting reconstruction for security."
                )
            
            print(f"[INTEGRITY] Shard {shard_id} verified: {actual_hash[:16]}... ✓")
        
        # Step 3: Reconstruct encrypted data using erasure decoding
        print("[RECONSTRUCT] All shards verified. Reconstructing data...")
        decoder = zfec.Decoder(self.k_required, self.m_total)
        
        # Use only k_required shards for reconstruction
        selected_shards = shards[:self.k_required]
        selected_ids = shard_ids[:self.k_required]
        
        # Decode shards back to original chunks
        reconstructed_chunks = decoder.decode(selected_shards, selected_ids)
        
        # Combine chunks to get padded encrypted data
        reconstructed_data = b''.join(reconstructed_chunks)
        
        # Step 4: Decrypt using Fernet
        try:
            plaintext = self.cipher.decrypt(reconstructed_data.rstrip(b'\x00'))
            print(f"[DECRYPT] Successfully decrypted {len(plaintext)} bytes")
            return plaintext
        except Exception as e:
            raise ValueError(f"[SECURITY ERROR] Decryption failed: {str(e)}")


def demonstrate_secure_storage():
    """
    Demonstration of the decentralized storage engine with security features.
    """
    print("="*70)
    print("DECENTRALIZED STORAGE ENGINE - SECURITY DEMONSTRATION")
    print("="*70)
    
    # Initialize storage engine
    engine = DecentralizedStorageEngine()
    
    # Original sensitive data
    original_data = b"CONFIDENTIAL: User financial records and PII data that must be protected"
    print(f"\n[ORIGINAL] Data: {original_data.decode()}")
    print(f"[ORIGINAL] Size: {len(original_data)} bytes")
    
    # ========================================================================
    # SCENARIO 1: Normal Operation - Encrypt, Shard, Store, Recover
    # ========================================================================
    print("\n" + "="*70)
    print("SCENARIO 1: Normal Secure Storage & Recovery")
    print("="*70)
    
    # Encrypt and shard the data
    shards, metadata = engine.encrypt_and_shard(original_data)
    
    print(f"\n[STORAGE] Data distributed across {len(shards)} storage nodes")
    print(f"[STORAGE] Each node holds one encrypted shard")
    
    # Simulate distributed storage: only 3 out of 5 shards available
    available_shards = [shards[0], shards[2], shards[4]]
    available_ids = [0, 2, 4]
    
    print(f"\n[SCENARIO] Simulating retrieval: Nodes 0, 2, 4 available")
    print(f"[SCENARIO] Nodes 1, 3 offline/unavailable")
    
    # Recover and decrypt
    recovered_data = engine.recover_and_decrypt(
        available_shards, 
        available_ids, 
        metadata
    )
    
    # Verify correctness
    assert recovered_data == original_data, "Data integrity compromised!"
    print(f"\n[SUCCESS] ✓ Data recovered successfully: {recovered_data.decode()}")
    
    # ========================================================================
    # SCENARIO 2: Security Test - Tampered Shard Detection
    # ========================================================================
    print("\n" + "="*70)
    print("SCENARIO 2: Tamper Detection - Modified Shard")
    print("="*70)
    
    # Simulate attacker tampering with a shard
    tampered_shards = available_shards.copy()
    tampered_shards[1] = b"TAMPERED_DATA" + tampered_shards[1][13:]  # Modify shard
    
    print(f"\n[ATTACK] Simulating attacker modifying shard 2...")
    print(f"[ATTACK] Original shard hash: {metadata[2][:16]}...")
    
    try:
        # Attempt recovery with tampered shard
        engine.recover_and_decrypt(
            tampered_shards,
            available_ids,
            metadata
        )
        print("[FAILURE] ✗ Tampering NOT detected - SECURITY BREACH!")
    except ValueError as e:
        print(f"\n[SUCCESS] ✓ Tampering detected and blocked!")
        print(f"[SUCCESS] ✓ Error: {str(e)}")
    
    # ========================================================================
    # SCENARIO 3: Insufficient Shards
    # ========================================================================
    print("\n" + "="*70)
    print("SCENARIO 3: Availability Test - Insufficient Shards")
    print("="*70)
    
    insufficient_shards = [shards[0], shards[1]]  # Only 2 shards
    insufficient_ids = [0, 1]
    
    print(f"\n[SCENARIO] Only 2 shards available (need {engine.k_required})")
    
    try:
        engine.recover_and_decrypt(
            insufficient_shards,
            insufficient_ids,
            metadata
        )
        print("[FAILURE] ✗ Should not succeed with insufficient shards!")
    except ValueError as e:
        print(f"\n[SUCCESS] ✓ Correctly rejected insufficient shards")
        print(f"[SUCCESS] ✓ Error: {str(e)}")
    
    print("\n" + "="*70)
    print("SECURITY DEMONSTRATION COMPLETE")
    print("="*70)
    print("\n[SUMMARY] Security Properties Verified:")
    print("  ✓ Confidentiality: Data encrypted before sharding")
    print("  ✓ Availability: Any 3 of 5 shards can recover data")
    print("  ✓ Integrity: SHA-256 detects tampering")
    print("  ✓ Fail-Safe: Tampered shards rejected before decryption")


if __name__ == "__main__":
    # Install required packages:
    # pip install cryptography zfec
    
    demonstrate_secure_storage()
