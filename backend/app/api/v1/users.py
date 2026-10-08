"""Team and User Management router with Role-Based Access Control (RBAC)."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_and_tenant, require_admin
from app.core.security import hash_password
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/users", tags=["Team & Users"])


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str | None = None
    role: Literal["admin", "analyst", "viewer"] = "analyst"


class UpdateUserRequest(BaseModel):
    name: str | None = None
    role: Literal["admin", "analyst", "viewer"] | None = None
    is_active: bool | None = None
    password: str | None = None


@router.get("")
def list_team_members(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """List all team members for current tenant."""
    _, tenant_id = user_and_tenant
    users = (
        db.query(User)
        .filter(User.tenant_id == tenant_id)
        .order_by(User.created_at.asc())
        .all()
    )
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name or u.email.split("@")[0].capitalize(),
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_team_member(
    payload: CreateUserRequest,
    admin_and_tenant=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new team member with specific RBAC role (Admin only)."""
    _, tenant_id = admin_and_tenant

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{payload.email}' already exists",
        )

    new_user = User(
        tenant_id=tenant_id,
        email=payload.email,
        name=payload.name or payload.email.split("@")[0].capitalize(),
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "id": new_user.id,
        "email": new_user.email,
        "name": new_user.name,
        "role": new_user.role,
        "is_active": new_user.is_active,
        "created_at": new_user.created_at.isoformat(),
    }


@router.patch("/{user_id}")
def update_team_member(
    user_id: str,
    payload: UpdateUserRequest,
    admin_and_tenant=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update role, display name, or active status of a team member (Admin only)."""
    admin_user, tenant_id = admin_and_tenant

    target_user = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == tenant_id)
        .first()
    )
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Protect against removing the last active admin
    if payload.role and payload.role != "admin" and target_user.role == "admin":
        active_admins = (
            db.query(User)
            .filter(
                User.tenant_id == tenant_id,
                User.role == "admin",
                User.is_active == True,  # noqa: E712
            )
            .count()
        )
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the sole active administrator for the tenant",
            )

    if payload.name is not None:
        target_user.name = payload.name
    if payload.role is not None:
        target_user.role = payload.role
    if payload.is_active is not None:
        target_user.is_active = payload.is_active
    if payload.password:
        target_user.hashed_password = hash_password(payload.password)

    db.commit()
    db.refresh(target_user)

    return {
        "id": target_user.id,
        "email": target_user.email,
        "name": target_user.name,
        "role": target_user.role,
        "is_active": target_user.is_active,
    }


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team_member(
    user_id: str,
    admin_and_tenant=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Remove team member from tenant (Admin only)."""
    admin_user, tenant_id = admin_and_tenant

    if admin_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot delete their own account",
        )

    target_user = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == tenant_id)
        .first()
    )
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    db.delete(target_user)
    db.commit()
