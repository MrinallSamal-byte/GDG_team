from django.contrib import admin

from .models import EventCreationRequest


@admin.register(EventCreationRequest)
class EventCreationRequestAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "requested_by",
        "status",
        "category",
        "mode",
        "created_at",
        "reviewed_by",
    )
    list_filter = ("status", "category", "mode", "created_at")
    search_fields = ("title", "requested_by__username", "requested_by__email")
    readonly_fields = ("created_at", "updated_at", "reviewed_at", "created_event")
