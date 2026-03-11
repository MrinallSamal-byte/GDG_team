from django.contrib import admin

from .models import ChatMessage, JoinRequest, Team, TeamMembership


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 0
    raw_id_fields = ("user",)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "event",
        "leader",
        "status",
        "member_count",
        "is_deleted",
        "created_at",
    )
    list_filter = ("status", "is_deleted")
    search_fields = ("name", "event__title", "leader__username")
    raw_id_fields = ("leader", "event")
    inlines = [TeamMembershipInline]

    def get_queryset(self, request):
        """Show all teams including soft-deleted in admin."""
        return Team.all_objects.all()


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "team", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("user__username", "team__name")
    raw_id_fields = ("user", "team")


@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "team", "role", "status", "created_at", "reviewed_at")
    list_filter = ("status", "role")
    search_fields = ("user__username", "team__name")
    raw_id_fields = ("user", "team", "reviewed_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "team", "body_preview", "created_at", "is_deleted")
    list_filter = ("is_deleted",)
    search_fields = ("body", "sender__username", "team__name")
    raw_id_fields = ("sender", "team")

    def body_preview(self, obj):
        """Show first 50 chars of message."""
        return obj.body[:50] + "..." if len(obj.body) > 50 else obj.body

    body_preview.short_description = "Message"
