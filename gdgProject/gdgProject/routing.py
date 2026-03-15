"""
WebSocket URL routing for Django Channels.
Maps ws:// paths to their consumer classes.
"""

from django.urls import re_path

from notification import consumers as notification_consumers
from team import consumers as team_consumers
from events import consumers as event_consumers

websocket_urlpatterns = [
    re_path(
        r"ws/team/(?P<team_id>\d+)/chat/$",
        team_consumers.ChatConsumer.as_asgi(),
    ),
    re_path(
        r"ws/user/notifications/$",
        notification_consumers.NotificationConsumer.as_asgi(),
    ),
    re_path(
        r"ws/event/(?P<event_id>\d+)/registrations/$",
        event_consumers.RegistrationUpdateConsumer.as_asgi(),
    ),
]
