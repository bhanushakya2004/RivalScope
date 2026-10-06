"""Delivery notification providers: Slack, Telegram, Webhook, and Mock."""

from typing import Any

import httpx

from app.config import get_settings
from app.core.logging import get_logger
from app.providers.base import BaseNotifier

logger = get_logger("providers.notify")


class MockNotifier(BaseNotifier):
    """In-memory delivery provider for tests and local demo mode."""

    def __init__(self):
        self.sent_messages: list[dict[str, Any]] = []

    async def send(
        self,
        target: str,
        title: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        record = {
            "target": target,
            "title": title,
            "message": message,
            "metadata": metadata or {},
        }
        self.sent_messages.append(record)
        logger.info(f"[MockNotifier] Delivered notification to '{target}': {title}")
        return True


class SlackNotifier(BaseNotifier):
    """Slack delivery provider via incoming webhook or chat.postMessage."""

    def __init__(self, bot_token: str | None = None):
        settings = get_settings()
        self.bot_token = bot_token or settings.slack_bot_token

    async def send(
        self,
        target: str,
        title: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        if not self.bot_token:
            logger.warning("Slack bot token not configured; logging message locally")
            logger.info(f"[Slack Notification] To: {target} | {title}\n{message}")
            return True

        url = "https://slack.com/api/chat.postMessage"
        headers = {"Authorization": f"Bearer {self.bot_token}"}
        payload = {
            "channel": target,
            "text": f"*{title}*\n\n{message}",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                data = resp.json()
                if not data.get("ok"):
                    logger.error(f"Slack delivery failed: {data.get('error')}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Slack delivery exception: {e}")
            return False


class TelegramNotifier(BaseNotifier):
    """Telegram bot delivery provider."""

    def __init__(self, bot_token: str | None = None):
        settings = get_settings()
        self.bot_token = bot_token or settings.telegram_bot_token

    async def send(
        self,
        target: str,
        title: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        if not self.bot_token:
            logger.warning("Telegram bot token not configured; logging message locally")
            logger.info(f"[Telegram Notification] To: {target} | {title}\n{message}")
            return True

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": target,
            "text": f"*{title}*\n\n{message}",
            "parse_mode": "Markdown",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                data = resp.json()
                if not data.get("ok"):
                    logger.error(f"Telegram delivery failed: {data.get('description')}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Telegram delivery exception: {e}")
            return False


class WebhookNotifier(BaseNotifier):
    """Generic JSON webhook delivery provider."""

    async def send(
        self,
        target: str,
        title: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        payload = {
            "title": title,
            "message": message,
            "metadata": metadata or {},
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(target, json=payload)
                resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Webhook delivery failed for {target}: {e}")
            return False
