"""Competitive signals router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_and_tenant
from app.db.models import RawDocument, Signal
from app.db.session import get_db

router = APIRouter(prefix="/signals", tags=["Signals"])


class SignalResponse(BaseModel):
    id: str
    company_id: str
    category: str
    title: str
    summary: str
    event_date: str
    confidence: float
    importance_score: int
    evidence_ids: list[str]
    created_at: str


@router.get("", response_model=list[SignalResponse])
def list_signals(
    company_id: str | None = None,
    category: str | None = None,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(25, ge=1, le=100),
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    query = db.query(Signal).filter(
        Signal.tenant_id == tenant_id,
        Signal.confidence >= min_confidence,
    )
    if company_id:
        query = query.filter(Signal.company_id == company_id)
    if category:
        query = query.filter(Signal.category == category)

    signals = query.order_by(desc(Signal.event_date)).limit(limit).all()

    return [
        SignalResponse(
            id=s.id,
            company_id=s.company_id,
            category=s.category,
            title=s.title,
            summary=s.summary,
            event_date=s.event_date.isoformat(),
            confidence=s.confidence,
            importance_score=s.importance_score,
            evidence_ids=s.evidence_ids or [],
            created_at=s.created_at.isoformat(),
        )
        for s in signals
    ]


@router.get("/{signal_id}")
def get_signal(
    signal_id: str,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    s = db.query(Signal).filter(Signal.id == signal_id, Signal.tenant_id == tenant_id).first()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found")

    evidence_docs = []
    if s.evidence_ids:
        docs = db.query(RawDocument).filter(RawDocument.id.in_(s.evidence_ids)).all()
        evidence_docs = [
            {"id": d.id, "url": d.canonical_url, "provider": d.provider, "content": d.content[:400]}
            for d in docs
        ]

    return {
        "id": s.id,
        "company_id": s.company_id,
        "category": s.category,
        "title": s.title,
        "summary": s.summary,
        "event_date": s.event_date.isoformat(),
        "confidence": s.confidence,
        "importance_score": s.importance_score,
        "evidence": evidence_docs,
        "cluster_id": s.cluster_id,
        "created_at": s.created_at.isoformat(),
    }
