from django.contrib import admin
from .models import CheckIn


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "checked_in", "checked_in_at", "checked_in_by")
    list_filter = ("checked_in", "event")
    search_fields = ("user__email", "token")
    readonly_fields = ("token", "created_at")
