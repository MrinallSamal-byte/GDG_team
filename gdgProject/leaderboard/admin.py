from django.contrib import admin
from .models import Leaderboard, LeaderboardEntry


class EntryInline(admin.TabularInline):
    model = LeaderboardEntry
    extra = 1


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ("event", "is_public", "updated_at")
    inlines = [EntryInline]
