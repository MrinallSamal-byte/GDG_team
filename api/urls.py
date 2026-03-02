from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'api'

router = DefaultRouter()
router.register(r'events', views.EventViewSet, basename='events')
router.register(r'notifications', views.NotificationViewSet, basename='notifications')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/toggle-theme/', views.ToggleThemeAPIView.as_view(), name='toggle_theme'),
    path('events/<int:event_id>/registrations/', views.EventRegistrationsAPIView.as_view(), name='event_registrations'),
    path('events/<int:event_id>/teams/', views.EventTeamsAPIView.as_view(), name='event_teams'),
    path('teams/<int:team_id>/messages/', views.TeamMessagesAPIView.as_view(), name='team_messages'),
    path('teams/<int:team_id>/join-requests/', views.JoinRequestAPIView.as_view(), name='join_requests'),
    path('dashboard/my-events/', views.MyEventsAPIView.as_view(), name='my_events'),
    path('dashboard/my-teams/', views.MyTeamsAPIView.as_view(), name='my_teams'),
]
