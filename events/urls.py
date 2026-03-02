from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('events/', views.EventListView.as_view(), name='event_list'),
    path('events/create/', views.EventCreateView.as_view(), name='event_create'),
    path('events/<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('events/<int:pk>/edit/', views.EventEditView.as_view(), name='event_edit'),
    path('events/<int:pk>/delete/', views.EventDeleteView.as_view(), name='event_delete'),
    path('events/<int:pk>/announce/', views.AnnouncementCreateView.as_view(), name='event_announce'),
]
