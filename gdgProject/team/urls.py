from django.urls import path

from . import views

app_name = 'team'

urlpatterns = [
    path('<int:team_id>/', views.team_management, name='team_management'),
]
