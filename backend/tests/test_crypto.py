"""Tests for AES-256-GCM PAT encryption and decryption."""

import pytest
from backend.app.security.crypto import encrypt_pat, decrypt_pat, CryptoManager


def test_encryption_decryption_roundtrip():
    secret_pat = "vsts-personal-access-token-1234567890abcdef"
    encrypted = encrypt_pat(secret_pat)

    assert encrypted != secret_pat
    assert len(encrypted) > len(secret_pat)

    decrypted = decrypt_pat(encrypted)
    assert decrypted == secret_pat


def test_unique_nonce_per_encryption():
    secret_pat = "sample-pat"
    enc1 = encrypt_pat(secret_pat)
    enc2 = encrypt_pat(secret_pat)

    # Different nonces produce different ciphertexts
    assert enc1 != enc2
    assert decrypt_pat(enc1) == secret_pat
    assert decrypt_pat(enc2) == secret_pat


def test_tampered_ciphertext_fails():
    secret_pat = "sample-pat"
    encrypted = encrypt_pat(secret_pat)
    tampered = encrypted[:-4] + "AAAA"

    with pytest.raises(Exception):
        decrypt_pat(tampered)
