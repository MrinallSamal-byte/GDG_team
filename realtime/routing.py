from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/event/(?P<event_id>\d+)/registrations/$', consumers.RegistrationConsumer.as_asgi()),
    re_path(r'ws/event/(?P<event_id>\d+)/teams/$', consumers.TeamConsumer.as_asgi()),
    re_path(r'ws/team/(?P<team_id>\d+)/chat/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/team/(?P<team_id>\d+)/requests/$', consumers.JoinRequestConsumer.as_asgi()),
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
