"""
WebSocket consumers for team chat.

Group naming:
  team_{team_id}_chat     — room for all members of a team
  team_{team_id}_typing   — typing indicators
"""

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger("campusarena.team.ws")


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Real-time team chat consumer.

    Validates membership on connect; relays messages to all members
    in the room and persists them to the database.
    """

    async def connect(self):
        self.team_id = self.scope["url_route"]["kwargs"]["team_id"]
        self.room_group = f"team_{self.team_id}_chat"
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        if not await self._is_member():
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()
        logger.info("WS chat connect: user=%d team=%s", self.user.pk, self.team_id)

    async def disconnect(self, close_code):
        if hasattr(self, "room_group"):
            await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type", "message")

        if msg_type == "typing":
            await self.channel_layer.group_send(
                self.room_group,
                {
                    "type": "typing_indicator",
                    "sender_id": self.user.pk,
                    "sender_name": self.user.get_full_name() or self.user.username,
                    "is_typing": data.get("is_typing", False),
                },
            )
            return

        body = data.get("body", "").strip()
        if not body or len(body) > 4000:
            return

        message = await self._save_message(body)
        if not message:
            return

        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "chat_message",
                "message_id": message["id"],
                "sender_id": self.user.pk,
                "sender_name": self.user.get_full_name() or self.user.username,
                "body": message["body"],
                "timestamp": message["timestamp"],
            },
        )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message",
                    "message_id": event["message_id"],
                    "sender_id": event["sender_id"],
                    "sender_name": event["sender_name"],
                    "body": event["body"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def typing_indicator(self, event):
        # Don't echo back to the sender
        if event["sender_id"] == self.user.pk:
            return
        await self.send(
            text_data=json.dumps(
                {
                    "type": "typing",
                    "sender_id": event["sender_id"],
                    "sender_name": event["sender_name"],
                    "is_typing": event["is_typing"],
                }
            )
        )

    @database_sync_to_async
    def _is_member(self) -> bool:
        from team.models import Team, TeamMembership

        return (
            TeamMembership.objects.filter(
                team_id=self.team_id, user=self.user
            ).exists()
            or Team.objects.filter(pk=self.team_id, leader=self.user).exists()
        )

    @database_sync_to_async
    def _save_message(self, body: str) -> dict | None:
        from team.models import ChatMessage, Team

        try:
            team = Team.objects.get(pk=self.team_id)
        except Team.DoesNotExist:
            return None

        msg = ChatMessage.objects.create(team=team, sender=self.user, body=body)
        return {
            "id": msg.pk,
            "body": msg.body,
            "timestamp": msg.created_at.isoformat(),
        }
