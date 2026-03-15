from django.contrib import admin
from .models import Certificate


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "cert_type", "issued_at", "verification_token")
    list_filter = ("cert_type",)
    search_fields = ("user__email", "event__title")
    readonly_fields = ("verification_token", "issued_at")
