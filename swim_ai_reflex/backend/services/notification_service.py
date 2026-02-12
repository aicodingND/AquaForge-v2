"""
Real-Time Notification Service

WebSocket and SSE notifications for optimization complete, new results, etc.
"""

import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class NotificationService:
    """Manages real-time notifications to connected clients"""

    def __init__(self):
        self.subscribers: dict[str, set] = {
            "optimization_complete": set(),
            "roster_update": set(),
            "error": set(),
        }

    def subscribe(self, event_type: str, callback):
        """Subscribe to notification events"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = set()

        self.subscribers[event_type].add(callback)
        logger.info(f"New subscriber for {event_type}")

    def unsubscribe(self, event_type: str, callback):
        """Unsubscribe from events"""
        if event_type in self.subscribers:
            self.subscribers[event_type].discard(callback)

    async def notify(self, event_type: str, data: dict):
        """Send notification to all subscribers"""
        if event_type not in self.subscribers:
            return

        payload = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        dead_callbacks = set()

        for callback in self.subscribers[event_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(payload)
                else:
                    callback(payload)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")
                dead_callbacks.add(callback)

        for callback in dead_callbacks:
            self.subscribers[event_type].discard(callback)

    async def notify_optimization_complete(
        self,
        session_id: str,
        seton_score: float,
        opponent_score: float,
        lineup: list[dict],
    ):
        """Notify when optimization completes"""
        await self.notify(
            "optimization_complete",
            {
                "session_id": session_id,
                "seton_score": seton_score,
                "opponent_score": opponent_score,
                "lineup_count": len(lineup),
                "margin": seton_score - opponent_score,
            },
        )

    async def notify_error(self, error_message: str, context: dict | None = None):
        """Notify about errors"""
        await self.notify("error", {"message": error_message, "context": context or {}})

    async def notify_roster_update(self, team: str, changes: dict):
        """Notify about roster changes"""
        await self.notify("roster_update", {"team": team, "changes": changes})


# Global notification service
notification_service = NotificationService()
