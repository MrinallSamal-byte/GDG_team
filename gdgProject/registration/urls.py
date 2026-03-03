from django.urls import path

from . import views

app_name = 'registration'

urlpatterns = [
    path('event/<int:event_id>/', views.register_event, name='register_event'),
]
