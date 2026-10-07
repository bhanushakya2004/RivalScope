"""Chat and interactive Q&A follow-up router with persistent database sessions."""

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_current_user_and_tenant
from app.core.model_factory import resolve_model
from app.db.models.chat import ChatMessage, ChatSession
from app.db.session import get_db
from app.delivery.followup import FollowUpHandler
from app.memory.manager import RivalMemory

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    question: str
    competitor_name: str | None = None
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    competitor: str | None = None
    tenant_id: str
    session_id: str


class ChatMessageRead(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: str
    metadata_json: dict[str, Any] = {}


class ChatSessionRead(BaseModel):
    id: str
    tenant_id: str
    title: str
    competitor_name: str | None = None
    created_at: str
    updated_at: str
    messages_count: int = 0


def _get_or_create_session(
    db: Session,
    tenant_id: str,
    user_id: str | None,
    session_id: str | None,
    question: str,
    competitor_name: str | None = None,
) -> ChatSession:
    if session_id:
        sess = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.tenant_id == tenant_id)
            .first()
        )
        if sess:
            return sess

    # Create new session
    title = question.strip()[:40] + ("..." if len(question.strip()) > 40 else "")
    sess = ChatSession(
        tenant_id=tenant_id,
        user_id=user_id,
        title=title or "Intelligence Session",
        competitor_name=competitor_name,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


@router.get("/sessions", response_model=list[ChatSessionRead])
def list_chat_sessions(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Retrieve all chat sessions for the current tenant."""
    _, tenant_id = user_and_tenant
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.tenant_id == tenant_id)
        .order_by(ChatSession.updated_at.desc())
        .limit(50)
        .all()
    )
    return [
        ChatSessionRead(
            id=s.id,
            tenant_id=s.tenant_id,
            title=s.title,
            competitor_name=s.competitor_name,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
            messages_count=len(s.messages) if s.messages else 0,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageRead])
def get_session_messages(
    session_id: str,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Retrieve full message transcript for a specific chat session."""
    _, tenant_id = user_and_tenant
    sess = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.tenant_id == tenant_id)
        .first()
    )
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id, ChatMessage.tenant_id == tenant_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        ChatMessageRead(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            created_at=m.created_at.isoformat(),
            metadata_json=m.metadata_json or {},
        )
        for m in messages
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    session_id: str,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Delete a chat session and its transcripts."""
    _, tenant_id = user_and_tenant
    sess = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.tenant_id == tenant_id)
        .first()
    )
    if sess:
        db.delete(sess)
        db.commit()
    return None


@router.post("", response_model=ChatResponse)
async def handle_chat_question(
    payload: ChatRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Handle synchronous chat question, persist session & messages, and return complete response."""
    user, tenant_id = user_and_tenant
    session = _get_or_create_session(
        db=db,
        tenant_id=tenant_id,
        user_id=user.id,
        session_id=payload.session_id,
        question=payload.question,
        competitor_name=payload.competitor_name,
    )

    # Persist user question
    db.add(
        ChatMessage(
            session_id=session.id,
            tenant_id=tenant_id,
            role="user",
            content=payload.question,
            metadata_json={"competitor": payload.competitor_name},
        )
    )
    db.commit()

    model = resolve_model("chat-assistant-model")
    memory = RivalMemory(db=db)
    handler = FollowUpHandler(model=model, memory=memory)
    res = await handler.handle_query(
        tenant_id=tenant_id,
        user_id=user.id,
        question=payload.question,
        competitor_name=payload.competitor_name,
    )

    # Persist assistant response
    answer_text = res["answer"]
    db.add(
        ChatMessage(
            session_id=session.id,
            tenant_id=tenant_id,
            role="assistant",
            content=answer_text,
            metadata_json={"competitor": res.get("competitor")},
        )
    )
    session.updated_at = datetime.now(UTC)
    db.commit()

    return ChatResponse(
        answer=answer_text,
        competitor=res.get("competitor"),
        tenant_id=tenant_id,
        session_id=session.id,
    )


@router.post("/stream")
async def stream_chat_question_post(
    payload: ChatRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Stream chat responses via SSE (POST) and durably record conversation into session storage."""
    user, tenant_id = user_and_tenant
    session = _get_or_create_session(
        db=db,
        tenant_id=tenant_id,
        user_id=user.id,
        session_id=payload.session_id,
        question=payload.question,
        competitor_name=payload.competitor_name,
    )

    # Save user message
    db.add(
        ChatMessage(
            session_id=session.id,
            tenant_id=tenant_id,
            role="user",
            content=payload.question,
            metadata_json={"competitor": payload.competitor_name},
        )
    )
    db.commit()

    model = resolve_model("chat-assistant-model")
    memory = RivalMemory(db=db)
    handler = FollowUpHandler(model=model, memory=memory)

    async def sse_wrapper():
        full_tokens: list[str] = []
        async for chunk in handler.stream_query(
            tenant_id=tenant_id,
            user_id=user.id,
            question=payload.question,
            competitor_name=payload.competitor_name,
        ):
            if chunk.get("event") == "start":
                # Inject session_id into start event
                try:
                    data = json.loads(chunk["data"])
                    data["session_id"] = session.id
                    chunk["data"] = json.dumps(data)
                except Exception:
                    pass
            elif chunk.get("event") == "delta":
                try:
                    data = json.loads(chunk["data"])
                    if "token" in data:
                        full_tokens.append(data["token"])
                except Exception:
                    pass
            elif chunk.get("event") == "done":
                # Save assistant message to database
                final_content = "".join(full_tokens) or "Response generated."
                try:
                    db.add(
                        ChatMessage(
                            session_id=session.id,
                            tenant_id=tenant_id,
                            role="assistant",
                            content=final_content,
                            metadata_json={"competitor": payload.competitor_name},
                        )
                    )
                    session.updated_at = datetime.now(UTC)
                    db.commit()
                except Exception:
                    pass
            yield chunk

    return EventSourceResponse(sse_wrapper())


@router.get("/stream")
async def stream_chat_question_get(
    question: str,
    competitor_name: str | None = None,
    session_id: str | None = None,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Stream chat responses via SSE (GET for EventSource) and persist session history."""
    req = ChatRequest(question=question, competitor_name=competitor_name, session_id=session_id)
    return await stream_chat_question_post(payload=req, user_and_tenant=user_and_tenant, db=db)
