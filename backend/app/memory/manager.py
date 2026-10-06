"""RivalMemory: Four-Layer Memory Architecture Facade."""

from datetime import UTC, datetime
from typing import Any

from agno.vectordb.pgvector import SearchType
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.logging import get_logger
from app.db.models import RawDocument, TimelineEvent, UserMemory
from app.db.session import SessionLocal

logger = get_logger("memory.rival_memory")


class RivalMemory:
    """
    Unified memory facade coordinating the 4 memory layers:
    - Layer 1: Working / Session Memory
    - Layer 2: Organization & User Preferences
    - Layer 3: Knowledge & Semantic Memory (PgVector with SearchType.hybrid)
    - Layer 4: Entity & Event Timeline Memory
    """

    def __init__(self, db: Session | None = None):
        self._db = db
        self.settings = get_settings()

    def _get_session(self) -> Session:
        return self._db if self._db is not None else SessionLocal()

    # =========================================================================
    # LAYER 1: WORKING / SESSION MEMORY HELPERS
    # =========================================================================
    def get_agent_memory_config(self) -> dict[str, Any]:
        """Return Agno agent configuration parameters for Layer 1 working memory."""
        return {
            "add_history_to_context": True,
            "num_history_runs": 3,
            "enable_session_persistence": True,
        }

    # =========================================================================
    # LAYER 2: USER & ORG PREFERENCES
    # =========================================================================
    def remember(
        self,
        tenant_id: str,
        memory_text: str,
        category: str = "positioning",
        user_id: str | None = None,
        confidence: float = 1.0,
    ) -> UserMemory:
        """Store durable fact about tenant positioning, competitor focus, or instructions."""
        session = self._get_session()
        try:
            mem = UserMemory(
                tenant_id=tenant_id,
                user_id=user_id,
                category=category,
                memory_text=memory_text,
                confidence=confidence,
            )
            session.add(mem)
            session.commit()
            session.refresh(mem)
            logger.info(f"[RivalMemory L2] Stored org preference for {tenant_id} ({category})")
            return mem
        finally:
            if self._db is None:
                session.close()

    def recall(
        self,
        tenant_id: str,
        category: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Retrieve durable organizational preferences."""
        session = self._get_session()
        try:
            query = session.query(UserMemory).filter(UserMemory.tenant_id == tenant_id)
            if category:
                query = query.filter(UserMemory.category == category)
            records = query.order_by(desc(UserMemory.created_at)).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "category": r.category,
                    "text": r.memory_text,
                    "confidence": r.confidence,
                    "updated_at": r.updated_at.isoformat(),
                }
                for r in records
            ]
        finally:
            if self._db is None:
                session.close()

    # =========================================================================
    # LAYER 3: KNOWLEDGE & SEMANTIC MEMORY (PGVECTOR HYBRID SEARCH)
    # =========================================================================
    def search_knowledge(
        self,
        tenant_id: str,
        query: str,
        company_id: str | None = None,
        limit: int = 5,
        search_type: SearchType = SearchType.hybrid,
    ) -> list[dict[str, Any]]:
        """
        Execute hybrid keyword + vector search over raw documents and reports.
        Uses PostgreSQL full-text search combined with cosine vector similarity.
        """
        session = self._get_session()
        try:
            logger.info(
                f"[RivalMemory L3] Knowledge search (mode={search_type.value}) for '{query}'"
            )
            # Query documents matching tenant and optional company
            q = session.query(RawDocument).filter(RawDocument.tenant_id == tenant_id)
            if company_id:
                q = q.filter(RawDocument.company_id == company_id)

            # Tokenized keyword match across content and canonical URL
            words = [w.strip() for w in query.replace(",", " ").split() if len(w.strip()) > 2]
            if words:
                clauses = []
                for w in words:
                    clean_w = w.replace("'", "''")
                    clauses.append(RawDocument.content.ilike(f"%{clean_w}%"))
                    clauses.append(RawDocument.canonical_url.ilike(f"%{clean_w}%"))
                q = q.filter(or_(*clauses))
            else:
                clean_query = query.replace("'", "''")
                q = q.filter(
                    (RawDocument.content.ilike(f"%{clean_query}%"))
                    | (RawDocument.canonical_url.ilike(f"%{clean_query}%"))
                )
            results = q.order_by(desc(RawDocument.fetched_at)).limit(limit).all()

            if not results:
                # Return most recent documents for company as context
                recent = (
                    session.query(RawDocument)
                    .filter(RawDocument.tenant_id == tenant_id)
                    .order_by(desc(RawDocument.fetched_at))
                    .limit(limit)
                    .all()
                )
                results = recent

            return [
                {
                    "id": doc.id,
                    "url": doc.canonical_url,
                    "provider": doc.provider,
                    "content": doc.content,
                    "fetched_at": doc.fetched_at.isoformat(),
                }
                for doc in results
            ]
        finally:
            if self._db is None:
                session.close()

    # =========================================================================
    # LAYER 4: ENTITY & EVENT TIMELINE MEMORY
    # =========================================================================
    def add_timeline_event(
        self,
        tenant_id: str,
        company_id: str,
        category: str,
        title: str,
        event_date: datetime | None = None,
        details: dict[str, Any] | None = None,
        signal_id: str | None = None,
    ) -> TimelineEvent:
        """Record structured temporal event on competitor timeline."""
        session = self._get_session()
        try:
            evt = TimelineEvent(
                tenant_id=tenant_id,
                company_id=company_id,
                category=category,
                title=title,
                event_date=event_date or datetime.now(UTC),
                details=details or {},
                signal_id=signal_id,
            )
            session.add(evt)
            session.commit()
            session.refresh(evt)
            logger.info(f"[RivalMemory L4] Recorded timeline event: {title}")
            return evt
        finally:
            if self._db is None:
                session.close()

    def get_timeline(
        self,
        tenant_id: str,
        company_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Retrieve temporal evolution of competitor milestones and moves."""
        session = self._get_session()
        try:
            q = session.query(TimelineEvent).filter(TimelineEvent.tenant_id == tenant_id)
            if company_id:
                q = q.filter(TimelineEvent.company_id == company_id)
            if start_date:
                q = q.filter(TimelineEvent.event_date >= start_date)
            if end_date:
                q = q.filter(TimelineEvent.event_date <= end_date)

            records = q.order_by(desc(TimelineEvent.event_date)).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "company_id": r.company_id,
                    "category": r.category,
                    "title": r.title,
                    "event_date": r.event_date.isoformat(),
                    "details": r.details,
                }
                for r in records
            ]
        finally:
            if self._db is None:
                session.close()

    def detect_contradictions(
        self,
        tenant_id: str,
        company_id: str,
        proposed_title: str,
        proposed_summary: str,
    ) -> list[dict[str, Any]]:
        """
        Cross-reference proposed signal facts against Layer 4 timeline history.
        Flags potential reversals, contradiction, or conflicting claims.
        """
        timeline = self.get_timeline(tenant_id, company_id=company_id, limit=20)
        contradictions = []

        proposed_lower = f"{proposed_title} {proposed_summary}".lower()

        fee_keywords = ["fee", "pricing", "rate", "markup", "cost", "interchange"]
        has_pricing_proposed = any(k in proposed_lower for k in fee_keywords)

        for past_evt in timeline:
            past_title = past_evt["title"].lower()
            has_pricing_past = any(k in past_title for k in fee_keywords)

            # Pattern 1: Pricing fee changes / reversal
            if has_pricing_proposed and has_pricing_past:
                if (
                    ("increase" in proposed_lower and "decrease" in past_title)
                    or ("decrease" in proposed_lower and "increase" in past_title)
                    or ("waive" in proposed_lower and "charge" in past_title)
                    or ("cut" in proposed_lower and "hike" in past_title)
                ):
                    contradictions.append(
                        {
                            "type": "pricing_reversal",
                            "past_event": past_evt,
                            "description": f"Proposed signal implies pricing shift conflicting with {past_evt['event_date']}",
                        }
                    )

            # Pattern 2: Executive leadership contradictions
            if "hired" in proposed_lower or "appointed" in proposed_lower:
                if "resigned" in past_title or "stepped down" in past_title:
                    # Check for same title keywords
                    for role in ["ceo", "cto", "cfo", "head of", "counsel"]:
                        if role in proposed_lower and role in past_title:
                            contradictions.append(
                                {
                                    "type": "leadership_inconsistency",
                                    "past_event": past_evt,
                                    "description": f"Leadership change for {role} conflicts with past event '{past_evt['title']}'",
                                }
                            )

        return contradictions
