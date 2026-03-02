from django.urls import path
from . import views

app_name = 'teams'

urlpatterns = [
    path('<int:pk>/', views.TeamDetailView.as_view(), name='team_detail'),
    path('<int:pk>/dashboard/', views.TeamDashboardView.as_view(), name='team_dashboard'),
    path('event/<int:event_id>/create/', views.CreateTeamView.as_view(), name='create_team'),
    path('<int:pk>/join/', views.JoinRequestView.as_view(), name='join_request'),
    path('request/<int:pk>/approve/', views.ApproveRequestView.as_view(), name='approve_request'),
    path('request/<int:pk>/decline/', views.DeclineRequestView.as_view(), name='decline_request'),
    path('<int:pk>/leave/', views.LeaveTeamView.as_view(), name='leave_team'),
    path('<int:pk>/chat/', views.TeamChatView.as_view(), name='team_chat'),
]
