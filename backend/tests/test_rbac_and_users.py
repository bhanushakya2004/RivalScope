"""Unit tests for RBAC roles, JWT tokens, and user management."""

import pytest
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.db.models import Tenant, User
from app.db.session import SessionLocal


def test_password_hashing_and_verification():
    raw_pass = "EnterpriseSecret!2026"
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_rbac_tokens():
    tenant_id = "t-test-enterprise"
    user_id = "u-analyst-123"
    token = create_access_token(subject=user_id, tenant_id=tenant_id, role="analyst")
    
    claims = decode_access_token(token)
    assert claims["sub"] == user_id
    assert claims["tenant_id"] == tenant_id
    assert claims["role"] == "analyst"


def test_admin_and_analyst_user_creation():
    db = SessionLocal()
    try:
        # Create test tenant
        import uuid
        tenant = Tenant(name="Test RBAC Tenant", slug=f"test-rbac-{uuid.uuid4().hex[:8]}")
        db.add(tenant)
        db.flush()


        # Create admin user
        admin_user = User(
            tenant_id=tenant.id,
            email=f"admin_{tenant.id[:8]}@example.com",
            name="Admin User",
            hashed_password=hash_password("adminpass123"),
            role="admin",
            is_active=True,
        )
        db.add(admin_user)

        # Create analyst user
        analyst_user = User(
            tenant_id=tenant.id,
            email=f"analyst_{tenant.id[:8]}@example.com",
            name="Analyst User",
            hashed_password=hash_password("analystpass123"),
            role="analyst",
            is_active=True,
        )

        db.add(analyst_user)
        db.commit()

        # Verify DB records
        queried_admin = db.query(User).filter(User.id == admin_user.id).first()
        assert queried_admin is not None
        assert queried_admin.role == "admin"
        assert queried_admin.is_active is True

        queried_analyst = db.query(User).filter(User.id == analyst_user.id).first()
        assert queried_analyst is not None
        assert queried_analyst.role == "analyst"

        # Cleanup
        db.delete(admin_user)
        db.delete(analyst_user)
        db.delete(tenant)
        db.commit()
    finally:
        db.close()
