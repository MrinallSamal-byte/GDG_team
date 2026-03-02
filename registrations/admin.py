from django.contrib import admin
from .models import Registration, RegistrationResponse, RegistrationTechStack


class ResponseInline(admin.TabularInline):
    model = RegistrationResponse
    extra = 0


class TechStackInline(admin.TabularInline):
    model = RegistrationTechStack
    extra = 0


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ['registration_id', 'user', 'event', 'registration_type', 'status', 'created_at']
    list_filter = ['status', 'registration_type', 'looking_for_team']
    search_fields = ['registration_id', 'user__username', 'user__email', 'event__title']
    inlines = [ResponseInline, TechStackInline]
    readonly_fields = ['registration_id']
