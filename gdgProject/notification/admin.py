from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for in-app notifications."""

    list_display = ("user", "type", "title", "read", "created_at")
    list_filter = ("type", "read")
    search_fields = ("user__username", "title", "body")
    readonly_fields = ("created_at",)
    raw_id_fields = ("user", "actor")
