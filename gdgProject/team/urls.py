from django.urls import path

from . import views

app_name = 'team'

urlpatterns = [
    path('<int:team_id>/', views.team_management, name='team_management'),
    path('<int:team_id>/approve/<int:request_id>/', views.approve_request, name='approve_request'),
    path('<int:team_id>/decline/<int:request_id>/', views.decline_request, name='decline_request'),
    path('<int:team_id>/leave/', views.leave_team, name='leave_team'),
]
