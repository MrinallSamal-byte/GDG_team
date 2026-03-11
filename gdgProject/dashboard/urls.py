from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.user_dashboard, name="user_dashboard"),
    path("", views.user_dashboard, name="home"),  # alias used across templates
    path("profile/", views.my_profile, name="my_profile"),
    path("events/", views.my_events, name="my_events"),
    path("teams/", views.my_teams, name="my_teams"),
    path("find-teammates/", views.find_teammates, name="find_teammates"),
    path("requests/", views.pending_requests, name="pending_requests"),
    path("notifications/", views.notifications_view, name="notifications"),
    path("notifications/mark-all-read/", views.mark_all_read, name="mark_all_read"),
    path("settings/", views.settings_view, name="settings"),
    path("edit-profile/", views.edit_profile, name="edit_profile"),
]
