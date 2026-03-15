"""
WebSocket consumer for real-time in-app notifications.

Group: user_{user_id}_notifications

Other parts of the app push to this group via:
    channel_layer.group_send(f"user_{user_id}_notifications", {...})
"""

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger("campusarena.notification.ws")


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.group_name = f"user_{self.user.pk}_notifications"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("Notification WS connected: user=%d", self.user.pk)

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass

    async def notify(self, event):
        """Receives from group_send and pushes to the WebSocket client."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "id": event.get("id"),
                    "title": event.get("title"),
                    "body": event.get("body"),
                    "notif_type": event.get("notif_type"),
                    "timestamp": event.get("timestamp"),
                }
            )
        )
