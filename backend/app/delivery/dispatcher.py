"""Notification delivery dispatcher and multi-channel routing."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.security import decrypt_secret
from app.db.models import DeliveryLog, NotificationChannel
from app.providers.notify import (
    BaseNotifier,
    MockNotifier,
    SlackNotifier,
    TelegramNotifier,
    WebhookNotifier,
)

logger = get_logger("delivery.dispatcher")


class DeliveryDispatcher:
    """Dispatches competitive intelligence reports across tenant notification channels."""

    def __init__(self, db: Session | None = None):
        self.db = db

    def _resolve_notifier(self, channel: NotificationChannel) -> BaseNotifier:
        """Resolve notifier instance based on channel type and decrypted config."""
        c_type = channel.channel_type.lower()
        try:
            config_str = (
                decrypt_secret(channel.encrypted_config, tenant_salt=channel.tenant_id)
                if channel.encrypted_config.startswith("==") or len(channel.encrypted_config) > 40
                else channel.encrypted_config
            )
        except Exception:
            config_str = channel.encrypted_config

        if c_type == "slack":
            return SlackNotifier(bot_token=config_str)
        elif c_type == "telegram":
            return TelegramNotifier(bot_token=config_str)
        elif c_type == "webhook":
            return WebhookNotifier()
        return MockNotifier()

    async def dispatch(
        self,
        tenant_id: str,
        title: str,
        content: str,
        signal_id: str | None = None,
        report_id: str | None = None,
        channels: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Dispatch report to all active channels for the tenant."""
        if self.db is None:
            # Fallback mock send
            await MockNotifier().send(target="#intel", title=title, message=content)
            return [{"channel_type": "mock", "status": "sent"}]

        query = self.db.query(NotificationChannel).filter(
            NotificationChannel.tenant_id == tenant_id,
            NotificationChannel.is_active,
        )
        if channels:
            query = query.filter(NotificationChannel.id.in_(channels))

        active_channels = query.all()
        results = []

        now = datetime.now(UTC)
        today_str = now.strftime("%Y-%m-%d")

        for ch in active_channels:
            idempotency_key = f"{tenant_id}:{signal_id or report_id or 'adhoc'}:{ch.id}:{today_str}"

            # Check if already delivered
            existing_log = (
                self.db.query(DeliveryLog)
                .filter(DeliveryLog.idempotency_key == idempotency_key)
                .first()
            )
            if existing_log and existing_log.status == "sent":
                logger.info(f"Skipping delivery to {ch.name} (idempotent key already sent)")
                results.append({"channel": ch.name, "status": "skipped", "reason": "idempotent"})
                continue

            notifier = self._resolve_notifier(ch)
            success = await notifier.send(
                target=ch.name,
                title=title,
                message=content,
            )

            # Record in delivery logs
            log = DeliveryLog(
                tenant_id=tenant_id,
                signal_id=signal_id,
                report_id=report_id,
                channel_id=ch.id,
                channel_type=ch.channel_type,
                idempotency_key=idempotency_key,
                status="sent" if success else "failed",
                error=None if success else "Provider failed to send",
                sent_at=now,
            )
            self.db.add(log)
            self.db.commit()

            results.append(
                {
                    "channel": ch.name,
                    "type": ch.channel_type,
                    "status": "sent" if success else "failed",
                }
            )

        return results
