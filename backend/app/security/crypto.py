"""AES-256-GCM encryption for storing Azure DevOps PATs and sensitive data securely at rest."""

import base64
import hashlib
import os
from typing import Optional, Dict, Any, List
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from backend.app.config.settings import get_settings


class CryptoManager:
    """Manages AES-256-GCM symmetric encryption for securing sensitive fields at rest in MongoDB."""

    def __init__(self, key_b64: Optional[str] = None):
        settings = get_settings()
        raw_key = key_b64 or settings.pat_encryption_key

        if raw_key:
            # Try decoding base64 key
            try:
                decoded = base64.b64decode(raw_key)
                if len(decoded) == 32:
                    self._key = decoded
                elif len(raw_key.encode("utf-8")) == 32:
                    self._key = raw_key.encode("utf-8")
                else:
                    self._key = hashlib.sha256(raw_key.encode("utf-8")).digest()
            except Exception:
                self._key = hashlib.sha256(raw_key.encode("utf-8")).digest()
        else:
            # Securely derive 32-byte encryption key from SECRET_KEY
            self._key = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()

        self._aesgcm = AESGCM(self._key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypts a plaintext string using AES-256-GCM with a random 96-bit nonce.
        Returns base64 encoded string containing nonce (12 bytes) + ciphertext + tag.
        """
        if not plaintext:
            return ""
        nonce = os.urandom(12)  # 96 bits nonce for GCM
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ciphertext).decode("utf-8")

    def decrypt(self, encrypted_b64: str) -> str:
        """Decrypts a base64 encoded string containing nonce + ciphertext + tag.
        Returns the original plaintext string.
        """
        if not encrypted_b64:
            return ""
        data = base64.b64decode(encrypted_b64)
        if len(data) < 28:  # 12 bytes nonce + min 16 bytes tag
            raise ValueError("Invalid encrypted data format or too short.")
        nonce = data[:12]
        ciphertext = data[12:]
        decrypted_bytes = self._aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted_bytes.decode("utf-8")

    def encrypt_field(self, value: Optional[str]) -> Optional[str]:
        """Convenience method to encrypt a field value, preserving None."""
        if value is None:
            return None
        return self.encrypt(str(value))

    def decrypt_field(self, value: Optional[str]) -> Optional[str]:
        """Convenience method to decrypt a field value, preserving None."""
        if value is None:
            return None
        return self.decrypt(value)


_crypto_manager: Optional[CryptoManager] = None


def get_crypto_manager() -> CryptoManager:
    global _crypto_manager
    if _crypto_manager is None:
        _crypto_manager = CryptoManager()
    return _crypto_manager


def encrypt_pat(pat: str) -> str:
    """Encrypts Azure DevOps PAT using AES-256-GCM before saving to database."""
    return get_crypto_manager().encrypt(pat)


def decrypt_pat(encrypted_pat: str) -> str:
    """Decrypts Azure DevOps PAT retrieved from database for API authentication."""
    return get_crypto_manager().decrypt(encrypted_pat)


def encrypt_field(value: Optional[str]) -> Optional[str]:
    """Encrypts an arbitrary sensitive string field."""
    return get_crypto_manager().encrypt_field(value)


def decrypt_field(value: Optional[str]) -> Optional[str]:
    """Decrypts an arbitrary sensitive string field."""
    return get_crypto_manager().decrypt_field(value)
