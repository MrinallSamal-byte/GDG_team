from django.urls import path

from . import views

app_name = 'eventManagement'

urlpatterns = [
    path('', views.organizer_dashboard, name='organizer_dashboard'),
    path('create/', views.create_event, name='create_event'),
]
