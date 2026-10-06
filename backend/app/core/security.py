"""Security utilities: password hashing, JWT management, and AES-256-GCM envelope encryption."""

import base64
import hashlib
import hmac
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings
from app.core.errors import AuthenticationError


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and salt."""
    salt = secrets.token_bytes(16)
    kdf = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{base64.b64encode(salt).decode('utf-8')}${base64.b64encode(kdf).decode('utf-8')}"


# Alias for compatibility
get_password_hash = hash_password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against salt and PBKDF2 hash."""
    try:
        salt_b64, hash_b64 = hashed_password.split("$")
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        expected_hash = base64.b64decode(hash_b64.encode("utf-8"))
        computed_hash = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(expected_hash, computed_hash)
    except Exception:
        return False


def create_access_token(
    subject: str,
    tenant_id: str,
    role: str = "analyst",
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Generate signed JWT access token."""
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))

    payload: dict[str, Any] = {
        "sub": subject,
        "tenant_id": tenant_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate JWT access token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.PyJWTError as e:
        raise AuthenticationError(f"Token verification failed: {str(e)}") from e


def _get_encryption_key(tenant_salt: str | None = None) -> bytes:
    """Derive 256-bit AES key from master key and optional tenant salt."""
    settings = get_settings()
    master = settings.encryption_master_key.encode("utf-8")
    salt = (tenant_salt or "rivalscope-default-salt").encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", master, salt, 50_000, dklen=32)


def encrypt_secret(plaintext: str, tenant_salt: str | None = None) -> str:
    """Encrypt plaintext string using AES-256-GCM. Returns base64(nonce + ciphertext + tag)."""
    if not plaintext:
        return ""
    key = _get_encryption_key(tenant_salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_secret(encrypted_payload: str, tenant_salt: str | None = None) -> str:
    """Decrypt base64(nonce + ciphertext + tag) string using AES-256-GCM."""
    if not encrypted_payload:
        return ""
    try:
        raw = base64.b64decode(encrypted_payload.encode("utf-8"))
        nonce, ciphertext = raw[:12], raw[12:]
        key = _get_encryption_key(tenant_salt)
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted.decode("utf-8")
    except Exception as e:
        raise ValueError("Failed to decrypt payload with current encryption key") from e
