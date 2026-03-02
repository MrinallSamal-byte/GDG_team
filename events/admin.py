from django.contrib import admin
from .models import (
    Event, EventPrize, EventRound, EventFAQ,
    EventJudge, EventSponsor, EventAnnouncement, CustomFormField
)


class PrizeInline(admin.TabularInline):
    model = EventPrize
    extra = 1


class RoundInline(admin.TabularInline):
    model = EventRound
    extra = 1


class FAQInline(admin.TabularInline):
    model = EventFAQ
    extra = 1


class JudgeInline(admin.TabularInline):
    model = EventJudge
    extra = 1


class SponsorInline(admin.TabularInline):
    model = EventSponsor
    extra = 1


class CustomFieldInline(admin.TabularInline):
    model = CustomFormField
    extra = 1


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'mode', 'status', 'organizer', 'registration_start', 'event_start', 'is_featured']
    list_filter = ['category', 'mode', 'status', 'is_featured', 'participation_type']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [PrizeInline, RoundInline, FAQInline, JudgeInline, SponsorInline, CustomFieldInline]
    date_hierarchy = 'event_start'


@admin.register(EventAnnouncement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'event', 'created_at']
    list_filter = ['event']
