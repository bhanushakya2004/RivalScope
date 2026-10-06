"""Interactive Follow-up Q&A Handler for Slack and Telegram interactions."""

from typing import Any

from agno.models.base import Model

from app.core.logging import get_logger
from app.memory.manager import RivalMemory
from app.teams.ci_team import create_ci_team

logger = get_logger("delivery.followup")


class FollowUpHandler:
    """Handles conversational follow-up questions from executives in chat surfaces."""

    def __init__(self, model: Model, memory: RivalMemory | None = None):
        self.model = model
        self.memory = memory or RivalMemory()
        self.team = create_ci_team(model=model, memory=self.memory)

    async def handle_query(
        self,
        tenant_id: str,
        user_id: str,
        question: str,
        competitor_name: str | None = None,
    ) -> dict[str, Any]:
        """Process natural language question and coordinate team response."""
        logger.info(f"Processing follow-up question for {tenant_id}: '{question}'")

        # Query relevant memory context
        recalled_prefs = self.memory.recall(tenant_id=tenant_id, limit=3)
        pref_context = (
            "\n".join([f"- {p['text']}" for p in recalled_prefs]) if recalled_prefs else ""
        )

        full_prompt = (
            f"Tenant Organization Context:\n{pref_context}\n\n"
            f"User Question: {question}\n"
            f"Target Competitor: {competitor_name or 'General Fintech Rivals'}\n"
            "Coordinate team members to answer accurately with evidence citations."
        )

        res = self.team.run(full_prompt)
        return {
            "answer": str(res.content),
            "tenant_id": tenant_id,
            "competitor": competitor_name,
        }
