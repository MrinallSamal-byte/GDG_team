from django.urls import path

from . import views

app_name = 'eventManagement'

urlpatterns = [
    path('', views.organizer_dashboard, name='organizer_dashboard'),
    path('create/', views.create_event, name='create_event'),
    path('<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('<int:event_id>/delete/', views.delete_event, name='delete_event'),
    path('<int:event_id>/status/', views.update_event_status, name='update_event_status'),
    path('<int:event_id>/announce/', views.create_announcement, name='create_announcement'),
    path('<int:event_id>/export/', views.export_registrations, name='export_registrations'),
    path('registration/<int:reg_id>/status/', views.update_registration_status, name='update_registration_status'),
]
