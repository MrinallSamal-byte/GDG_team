from django.urls import path

from . import views

app_name = 'notification'

urlpatterns = [
    path('api/unread-count/', views.unread_count, name='unread_count'),
]
