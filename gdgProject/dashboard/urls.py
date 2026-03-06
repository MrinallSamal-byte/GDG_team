from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.user_dashboard, name='user_dashboard'),
    path('profile/', views.my_profile, name='my_profile'),
    path('events/', views.my_events, name='my_events'),
    path('teams/', views.my_teams, name='my_teams'),
    path('find-teammates/', views.find_teammates, name='find_teammates'),
    path('requests/', views.pending_requests, name='pending_requests'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('settings/', views.settings_view, name='settings'),
]
