from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.UserDashboardView.as_view(), name='user_dashboard'),
    path('my-events/', views.MyEventsView.as_view(), name='my_events'),
    path('my-teams/', views.MyTeamsView.as_view(), name='my_teams'),
    path('pending-requests/', views.PendingRequestsView.as_view(), name='pending_requests'),
    path('organizer/', views.OrganizerDashboardView.as_view(), name='organizer_dashboard'),
    path('organizer/event/<int:event_id>/', views.EventManagementView.as_view(), name='event_management'),
    path('organizer/event/<int:event_id>/participants/', views.ParticipantManagementView.as_view(), name='participants'),
    path('organizer/event/<int:event_id>/export/', views.ExportRegistrationsView.as_view(), name='export_registrations'),
    path('organizer/event/<int:event_id>/form-builder/', views.FormBuilderView.as_view(), name='form_builder'),
]
