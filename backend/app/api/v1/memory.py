"""Memory inspection and organization preferences router."""

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_and_tenant
from app.db.session import get_db
from app.memory.manager import RivalMemory

router = APIRouter(prefix="/memory", tags=["Memory"])


class RememberPreferenceRequest(BaseModel):
    category: str = "positioning"
    memory_text: str


@router.get("/preferences")
def list_preferences(
    category: str | None = None,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    memory = RivalMemory(db=db)
    return memory.recall(tenant_id=tenant_id, category=category, limit=20)


@router.post("/preferences", status_code=status.HTTP_201_CREATED)
def add_preference(
    payload: RememberPreferenceRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    user, tenant_id = user_and_tenant
    memory = RivalMemory(db=db)
    mem = memory.remember(
        tenant_id=tenant_id,
        memory_text=payload.memory_text,
        category=payload.category,
        user_id=user.id,
    )
    return {
        "id": mem.id,
        "category": mem.category,
        "text": mem.memory_text,
        "created_at": mem.created_at.isoformat(),
    }


@router.get("/timeline")
def get_timeline(
    company_id: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    memory = RivalMemory(db=db)
    return memory.get_timeline(tenant_id=tenant_id, company_id=company_id, limit=limit)
