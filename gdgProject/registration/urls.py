from django.urls import path

from . import views

app_name = 'registration'

urlpatterns = [
    path('event/<int:event_id>/', views.register_event, name='register_event'),
    path('confirmation/<int:registration_id>/', views.registration_confirmation, name='confirmation'),
]
