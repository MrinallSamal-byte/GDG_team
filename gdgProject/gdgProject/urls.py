"""
URL configuration for gdgProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.views import health

handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health, name='health'),
    path('', include('events.urls')),
    path('registration/', include('registration.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('teams/', include('team.urls')),
    path('organizer/', include('eventManagement.urls')),
    path('auth/', include('users.urls')),
    path('notifications/', include('notification.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
