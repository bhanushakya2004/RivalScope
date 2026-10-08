"""Authentication and user session router with RBAC token issuance."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_and_tenant
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import Tenant, User
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str | None = None
    tenant_name: str | None = None
    role: str = "analyst"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email and password, issuing role-scoped JWT token."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact an administrator.",
        )

    token = create_access_token(
        subject=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name or user.email.split("@")[0].capitalize(),
            "role": user.role,
            "tenant_id": user.tenant_id,
        },
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register user and tenant, issuing initial administrator JWT token."""
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{payload.email}' already exists",
        )

    # Check for demo/default tenant or create new one
    tenant = db.query(Tenant).first()
    role_to_assign = payload.role
    if not tenant or payload.tenant_name:
        t_name = payload.tenant_name or "Enterprise Workspace"
        t_slug = t_name.lower().replace(" ", "-")[:50]
        tenant = Tenant(name=t_name, slug=t_slug)
        db.add(tenant)
        db.flush()
        role_to_assign = "admin"  # Creator of new tenant is always admin

    new_user = User(
        tenant_id=tenant.id,
        email=payload.email,
        name=payload.name or payload.email.split("@")[0].capitalize(),
        hashed_password=hash_password(payload.password),
        role=role_to_assign,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(
        subject=new_user.id,
        tenant_id=new_user.tenant_id,
        role=new_user.role,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user={
            "id": new_user.id,
            "email": new_user.email,
            "name": new_user.name,
            "role": new_user.role,
            "tenant_id": new_user.tenant_id,
        },
    )


@router.get("/me")
def get_me(user_and_tenant=Depends(get_current_user_and_tenant)):
    """Retrieve current authenticated user context and active permissions."""
    user, tenant_id = user_and_tenant
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name or user.email.split("@")[0].capitalize(),
        "role": user.role,
        "tenant_id": tenant_id,
        "is_active": user.is_active,
    }
