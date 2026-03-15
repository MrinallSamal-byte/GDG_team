from django.urls import path

from . import views

app_name = "leaderboard"

urlpatterns = [
    path("event/<int:event_id>/", views.event_leaderboard, name="event_leaderboard"),
    path("event/<int:event_id>/manage/", views.manage_leaderboard, name="manage"),
    path("event/<int:event_id>/entry/", views.upsert_entry, name="upsert_entry"),
    path("event/<int:event_id>/entry/<int:entry_id>/delete/", views.delete_entry, name="delete_entry"),
    path("event/<int:event_id>/toggle/", views.toggle_visibility, name="toggle_visibility"),
]
