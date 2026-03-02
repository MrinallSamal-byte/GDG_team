from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('events.urls', namespace='events')),
    path('auth/', include('users.urls', namespace='users')),
    path('registrations/', include('registrations.urls', namespace='registrations')),
    path('teams/', include('teams.urls', namespace='teams')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('api/v1/', include('api.urls', namespace='api')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'CampusArena Administration'
admin.site.site_title = 'CampusArena'
admin.site.index_title = 'Platform Management'
