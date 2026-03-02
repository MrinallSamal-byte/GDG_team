from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import JsonResponse

from events.models import Event
from registrations.models import Registration
from teams.models import Team, Message, TeamJoinRequest
from notifications.models import Notification
from .serializers import (
    EventSerializer, RegistrationSerializer, TeamSerializer,
    MessageSerializer, NotificationSerializer, JoinRequestSerializer
)


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.filter(status='published', is_archived=False)
    filterset_fields = ['category', 'mode', 'participation_type']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'event_start', 'registration_end']


class EventRegistrationsAPIView(generics.ListAPIView):
    serializer_class = RegistrationSerializer

    def get_queryset(self):
        return Registration.objects.filter(
            event_id=self.kwargs['event_id'],
            status='confirmed'
        ).select_related('user', 'team')


class EventTeamsAPIView(generics.ListAPIView):
    serializer_class = TeamSerializer

    def get_queryset(self):
        return Team.objects.filter(
            event_id=self.kwargs['event_id']
        ).prefetch_related('members__user')


class TeamMessagesAPIView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(
            team_id=self.kwargs['team_id']
        ).select_related('sender')


class JoinRequestAPIView(generics.ListCreateAPIView):
    serializer_class = JoinRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TeamJoinRequest.objects.filter(
            team_id=self.kwargs['team_id']
        ).select_related('user')


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MyEventsAPIView(generics.ListAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Registration.objects.filter(
            user=self.request.user
        ).select_related('event', 'team')


class MyTeamsAPIView(generics.ListAPIView):
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Team.objects.filter(
            members__user=self.request.user
        ).select_related('event', 'leader').distinct()


class ToggleThemeAPIView(APIView):
    def post(self, request):
        current = getattr(request, 'theme', 'light')
        new_theme = 'dark' if current == 'light' else 'light'
        if request.user.is_authenticated:
            request.user.theme_preference = new_theme
            request.user.save(update_fields=['theme_preference'])
        response = Response({'theme': new_theme})
        response.set_cookie('theme', new_theme, max_age=365 * 24 * 60 * 60, httponly=True, samesite='Lax')
        return response
