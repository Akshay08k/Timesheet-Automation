"""AES-256-GCM encryption for storing Azure DevOps PATs securely at rest."""

import base64
import os
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from backend.app.config.settings import get_settings


class CryptoManager:
    def __init__(self, key_b64: Optional[str] = None):
        settings = get_settings()
        raw_key = key_b64 or settings.pat_encryption_key
        if not raw_key:
            raise ValueError(
                "PAT_ENCRYPTION_KEY is not configured. Set a 32-byte base64-encoded key in environment."
            )
        try:
            self._key = base64.b64decode(raw_key)
            if len(self._key) != 32:
                raise ValueError("Decoded PAT_ENCRYPTION_KEY must be exactly 32 bytes for AES-256-GCM.")
        except Exception as e:
            raise ValueError(f"Invalid PAT_ENCRYPTION_KEY: {e}")

        self._aesgcm = AESGCM(self._key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypts a plaintext string (e.g. PAT) using AES-256-GCM with a random 96-bit nonce.
        Returns base64 encoded string containing nonce + ciphertext + tag.
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


_crypto_manager: Optional[CryptoManager] = None


def get_crypto_manager() -> CryptoManager:
    global _crypto_manager
    if _crypto_manager is None:
        _crypto_manager = CryptoManager()
    return _crypto_manager


def encrypt_pat(pat: str) -> str:
    return get_crypto_manager().encrypt(pat)


def decrypt_pat(encrypted_pat: str) -> str:
    return get_crypto_manager().decrypt(encrypted_pat)
