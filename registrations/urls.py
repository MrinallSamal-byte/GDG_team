from django.urls import path
from . import views

app_name = 'registrations'

urlpatterns = [
    path('event/<int:event_id>/register/', views.RegisterForEventView.as_view(), name='register_for_event'),
    path('<int:pk>/confirmation/', views.RegistrationConfirmationView.as_view(), name='confirmation'),
    path('<int:pk>/cancel/', views.CancelRegistrationView.as_view(), name='cancel'),
    path('<int:pk>/calendar/', views.DownloadCalendarView.as_view(), name='download_calendar'),
]
