import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class RegistrationConsumer(AsyncWebsocketConsumer):
    """Real-time registration count updates for event detail page."""

    async def connect(self):
        self.event_id = self.scope['url_route']['kwargs']['event_id']
        self.group_name = f'event_{self.event_id}_registrations'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def registration_update(self, event):
        await self.send(text_data=json.dumps(event['data']))


class TeamConsumer(AsyncWebsocketConsumer):
    """Real-time team updates for event page."""

    async def connect(self):
        self.event_id = self.scope['url_route']['kwargs']['event_id']
        self.group_name = f'event_{self.event_id}_teams'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def team_update(self, event):
        await self.send(text_data=json.dumps(event['data']))


class ChatConsumer(AsyncWebsocketConsumer):
    """Real-time team chat."""

    async def connect(self):
        self.team_id = self.scope['url_route']['kwargs']['team_id']
        self.group_name = f'team_{self.team_id}_chat'
        user = self.scope.get('user')

        if user and user.is_authenticated:
            is_member = await self._is_team_member(user.id, self.team_id)
            if is_member:
                await self.channel_layer.group_add(self.group_name, self.channel_name)
                await self.accept()
                return
        await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        user = self.scope['user']
        content = data.get('message', '').strip()
        if not content:
            return

        msg = await self._save_message(user.id, self.team_id, content)

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',
                'data': {
                    'message_id': msg['id'],
                    'sender_id': user.id,
                    'sender_name': user.display_name,
                    'sender_initials': user.initials,
                    'content': content,
                    'timestamp': msg['timestamp'],
                    'message_type': 'text',
                }
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['data']))

    @database_sync_to_async
    def _is_team_member(self, user_id, team_id):
        from teams.models import TeamMember
        return TeamMember.objects.filter(team_id=team_id, user_id=user_id).exists()

    @database_sync_to_async
    def _save_message(self, user_id, team_id, content):
        from teams.models import Message
        msg = Message.objects.create(
            team_id=team_id,
            sender_id=user_id,
            content=content,
            message_type='text',
        )
        return {'id': msg.id, 'timestamp': msg.created_at.isoformat()}


class JoinRequestConsumer(AsyncWebsocketConsumer):
    """Real-time join request notifications for team leaders."""

    async def connect(self):
        self.team_id = self.scope['url_route']['kwargs']['team_id']
        self.group_name = f'team_{self.team_id}_requests'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def join_request_update(self, event):
        await self.send(text_data=json.dumps(event['data']))


class NotificationConsumer(AsyncWebsocketConsumer):
    """Real-time notifications for individual users."""

    async def connect(self):
        user = self.scope.get('user')
        if user and user.is_authenticated:
            self.group_name = f'user_{user.id}_notifications'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_notification(self, event):
        await self.send(text_data=json.dumps(event['data']))
