"""Unit tests for security, JWT auth, and envelope encryption."""

import pytest
from app.core.security import (
    create_access_token,
    decode_access_token,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    verify_password,
)


def test_password_hashing_and_verification():
    raw = "TopSecretPassword123!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_roundtrip():
    token = create_access_token(
        subject="user-123",
        tenant_id="tenant-456",
        role="analyst",
    )
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["tenant_id"] == "tenant-456"
    assert payload["role"] == "analyst"


def test_aes_envelope_encryption():
    secret = "sk-live-super-secret-mcp-api-key"
    salt = "tenant-specific-salt-789"
    encrypted = encrypt_secret(secret, tenant_salt=salt)
    assert encrypted != secret

    decrypted = decrypt_secret(encrypted, tenant_salt=salt)
    assert decrypted == secret

    # Wrong salt must fail decryption
    with pytest.raises(ValueError):
        decrypt_secret(encrypted, tenant_salt="different-salt")
