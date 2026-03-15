"""
WebSocket consumer for real-time registration count updates on event pages.

Group: event_{event_id}_registrations

Pushed to when a new registration is confirmed.
"""

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger("campusarena.events.ws")


class RegistrationUpdateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.event_id = self.scope["url_route"]["kwargs"]["event_id"]
        self.group_name = f"event_{self.event_id}_registrations"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass

    async def registration_update(self, event):
        """Broadcast registration count update to all watchers of this event."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "registration_update",
                    "count": event.get("count"),
                    "participant": event.get("participant"),
                }
            )
        )
