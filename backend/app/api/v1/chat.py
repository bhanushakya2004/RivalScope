"""Chat and interactive Q&A follow-up router."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_and_tenant
from app.core.mock_model import MockModel
from app.db.session import get_db
from app.delivery.followup import FollowUpHandler
from app.memory.manager import RivalMemory

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    question: str
    competitor_name: str | None = None


class ChatResponse(BaseModel):
    answer: str
    competitor: str | None = None
    tenant_id: str


@router.post("", response_model=ChatResponse)
async def handle_chat_question(
    payload: ChatRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    user, tenant_id = user_and_tenant
    model = MockModel(id="chat-assistant-model")
    memory = RivalMemory(db=db)
    handler = FollowUpHandler(model=model, memory=memory)
    res = await handler.handle_query(
        tenant_id=tenant_id,
        user_id=user.id,
        question=payload.question,
        competitor_name=payload.competitor_name,
    )
    return ChatResponse(
        answer=res["answer"],
        competitor=res.get("competitor"),
        tenant_id=tenant_id,
    )
