from django.urls import path

from . import views

app_name = 'team'

urlpatterns = [
    path('<int:team_id>/', views.team_management, name='team_management'),
    path('create/<int:event_id>/', views.create_team, name='create_team'),
    path('join/<int:team_id>/', views.request_join, name='request_join'),
    path('<int:team_id>/leave/', views.leave_team, name='leave_team'),
    path('<int:team_id>/toggle-status/', views.toggle_team_status, name='toggle_team_status'),
    path('<int:team_id>/remove/<int:user_id>/', views.remove_member, name='remove_member'),
    path('find/', views.find_teammates, name='find_teammates'),
]
