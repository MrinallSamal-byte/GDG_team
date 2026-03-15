from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("", views.home, name="home"),
    path("events/<int:event_id>/", views.event_detail, name="event_detail"),
    path("events/<slug:slug>/", views.event_detail_slug, name="event_detail_slug"),
    path(
        "events/<int:event_id>/contact/",
        views.contact_organizer,
        name="contact_organizer",
    ),
]
