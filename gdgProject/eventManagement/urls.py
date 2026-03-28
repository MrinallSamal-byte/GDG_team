from django.urls import path

from . import views

app_name = "eventManagement"

urlpatterns = [
    path("", views.organizer_dashboard, name="organizer_dashboard"),
    path("creator/", views.creator_dashboard, name="creator_dashboard"),
    path("creator/request/", views.request_event, name="request_event"),
    path("create/", views.create_event, name="create_event"),
    path(
        "requests/<int:request_id>/review/",
        views.review_event_request,
        name="review_event_request",
    ),
    path("users/<int:user_id>/status/", views.toggle_user_status, name="toggle_user_status"),
    path(
        "users/<int:user_id>/password/",
        views.update_user_password,
        name="update_user_password",
    ),
    path("<int:event_id>/edit/", views.edit_event, name="edit_event"),
    path("<int:event_id>/delete/", views.delete_event, name="delete_event"),
    path("<int:event_id>/status/", views.update_event_status, name="update_event_status"),
    path(
        "<int:event_id>/announce/",
        views.create_announcement,
        name="create_announcement",
    ),
    path(
        "<int:event_id>/export/",
        views.export_registrations,
        name="export_registrations",
    ),
    path("<int:event_id>/clone/", views.clone_event, name="clone_event"),
    path(
        "registration/<int:reg_id>/status/",
        views.update_registration_status,
        name="update_registration_status",
    ),
]
