from django.contrib import admin
from .models import Team, TeamMember, TeamJoinRequest, Message


class MemberInline(admin.TabularInline):
    model = TeamMember
    extra = 0


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['team_name', 'event', 'leader', 'max_members', 'member_count', 'is_open']
    list_filter = ['is_open', 'event']
    search_fields = ['team_name', 'leader__username', 'event__title']
    inlines = [MemberInline]


@admin.register(TeamJoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'team', 'status', 'created_at']
    list_filter = ['status']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'team', 'content_preview', 'message_type', 'created_at']
    list_filter = ['message_type']

    def content_preview(self, obj):
        return obj.content[:60]
    content_preview.short_description = 'Content'
