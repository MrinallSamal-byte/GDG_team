from django.contrib import admin
from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("title", "event", "user", "team", "status", "score", "submitted_at")
    list_filter = ("status", "event")
    search_fields = ("title", "user__email", "team__name")
    readonly_fields = ("created_at", "updated_at")
