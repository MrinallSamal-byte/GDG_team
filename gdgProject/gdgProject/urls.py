from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from core.views import health

handler404 = "django.views.defaults.page_not_found"
handler500 = "django.views.defaults.server_error"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),

    # ── Core apps ────────────────────────────────────────────────────────────
    path("", include("events.urls")),
    path("registration/", include("registration.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("teams/", include("team.urls")),
    path("organizer/", include("eventManagement.urls")),
    path("auth/", include("users.urls")),
    path("notifications/", include("notification.urls")),

    # ── New feature apps ─────────────────────────────────────────────────────
    path("payments/", include("payments.urls")),
    path("certificates/", include("certificates.urls")),
    path("leaderboard/", include("leaderboard.urls")),
    path("submissions/", include("submissions.urls")),
    path("checkin/", include("checkin.urls")),

    # ── [E6] OAuth (Google / GitHub) via django-allauth ───────────────────────
    # Only the social-account URLs are included here so allauth's own login/logout
    # pages don't conflict with our custom auth views at /auth/*.
    # Social callback URLs will be at /auth/social/<provider>/login/callback/.
    path("auth/social/", include("allauth.socialaccount.urls")),

    # ── [E7] PWA ──────────────────────────────────────────────────────────────
    path(
        "manifest.json",
        TemplateView.as_view(
            template_name="pwa/manifest.json",
            content_type="application/manifest+json",
        ),
        name="pwa_manifest",
    ),
    path(
        "sw.js",
        TemplateView.as_view(
            template_name="pwa/sw.js",
            content_type="application/javascript",
        ),
        name="service_worker",
    ),
    path(
        "offline/",
        TemplateView.as_view(template_name="pwa/offline.html"),
        name="offline",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
