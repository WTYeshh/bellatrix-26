import os
import base64
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# 256-bit AES-GCM Encryption Key
_ENV_KEY = os.getenv("AEGIS_ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")

def _get_key_bytes(key: Optional[str] = None) -> bytes:
    k = key or _ENV_KEY
    if len(k) == 64:
        try:
            return bytes.fromhex(k)
        except ValueError:
            pass
    return k.encode("utf-8")[:32].ljust(32, b"0")

def encrypt_field(plaintext: str, key: Optional[str] = None) -> str:
    """
    Encrypts a sensitive string field using AES-256-GCM with a randomized 96-bit nonce.
    Returns URL-safe base64 encoded string: nonce + ciphertext + tag.
    """
    if not plaintext:
        return ""
    key_bytes = _get_key_bytes(key)
    aesgcm = AESGCM(key_bytes)
    nonce = os.urandom(12)  # Standard 96-bit GCM nonce
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("utf-8")

def decrypt_field(encoded_ciphertext: str, key: Optional[str] = None) -> str:
    """
    Decrypts an AES-256-GCM encoded string.
    """
    if not encoded_ciphertext:
        return ""
    try:
        raw = base64.urlsafe_b64decode(encoded_ciphertext.encode("utf-8"))
        if len(raw) < 28: # 12-byte nonce + min 16-byte GCM tag
            return encoded_ciphertext
        nonce = raw[:12]
        ciphertext = raw[12:]
        key_bytes = _get_key_bytes(key)
        aesgcm = AESGCM(key_bytes)
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted.decode("utf-8")
    except Exception:
        # Fail gracefully if plaintext or different key
        return encoded_ciphertext
