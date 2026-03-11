from django.urls import path

from . import views

app_name = "notification"

urlpatterns = [
    path("api/unread-count/", views.unread_count, name="unread_count"),
    path("api/mark-read/<int:notification_id>/", views.mark_read, name="mark_read"),
    path("api/mark-all-read/", views.mark_all_read, name="mark_all_read"),
]
