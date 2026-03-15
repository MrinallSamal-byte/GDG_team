from django.contrib import admin

from .models import Event, EventAnnouncement, EventJudge, EventRound, EventSponsor


class EventRoundInline(admin.TabularInline):
    model = EventRound
    extra = 0
    ordering = ["order"]


class EventJudgeInline(admin.TabularInline):
    model = EventJudge
    extra = 0


class EventSponsorInline(admin.TabularInline):
    model = EventSponsor
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "status",
        "mode",
        "event_start",
        "capacity",
        "is_featured",
        "created_by",
    )
    list_filter = (
        "status",
        "category",
        "mode",
        "participation_type",
        "is_featured",
        "is_deleted",
    )
    search_fields = ("title", "description", "slug")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "event_start"
    inlines = [EventRoundInline, EventJudgeInline, EventSponsorInline]

    list_select_related = ("created_by",)

    def get_queryset(self, request):
        """Show all events including soft-deleted in admin."""
        return Event.all_objects.select_related("created_by")


@admin.register(EventRound)
class EventRoundAdmin(admin.ModelAdmin):
    list_display = ("name", "event", "order", "start_date", "status")
    list_filter = ("status",)
    search_fields = ("name", "event__title")


@admin.register(EventJudge)
class EventJudgeAdmin(admin.ModelAdmin):
    list_display = ("name", "designation", "event")
    search_fields = ("name", "event__title")


@admin.register(EventSponsor)
class EventSponsorAdmin(admin.ModelAdmin):
    list_display = ("name", "sponsor_type", "event")
    list_filter = ("sponsor_type",)
    search_fields = ("name", "event__title")


@admin.register(EventAnnouncement)
class EventAnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "event", "created_at")
    search_fields = ("title", "content", "event__title")
    readonly_fields = ("created_at",)
