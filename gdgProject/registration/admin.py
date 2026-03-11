from django.contrib import admin

from .models import (
    CustomFormField,
    Registration,
    RegistrationResponse,
    RegistrationTechStack,
)


class RegistrationResponseInline(admin.TabularInline):
    """Inline display of registration responses inside a Registration record."""

    model = RegistrationResponse
    extra = 0
    readonly_fields = ("field", "response_value")
    can_delete = False


class RegistrationTechStackInline(admin.TabularInline):
    model = RegistrationTechStack
    extra = 0


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    """Admin for participant registrations."""

    list_display = (
        "registration_id",
        "user",
        "event",
        "type",
        "status",
        "looking_for_team",
        "registered_at",
    )
    list_filter = ("status", "type", "looking_for_team")
    search_fields = ("registration_id", "user__username", "user__email", "event__title")
    readonly_fields = ("registration_id", "registered_at", "updated_at")
    raw_id_fields = ("user", "event", "team")
    inlines = [RegistrationResponseInline, RegistrationTechStackInline]


@admin.register(CustomFormField)
class CustomFormFieldAdmin(admin.ModelAdmin):
    """Admin for organizer-defined registration form fields."""

    list_display = (
        "field_label",
        "event",
        "field_type",
        "is_required",
        "display_order",
    )
    list_filter = ("field_type", "is_required")
    search_fields = ("field_label", "event__title")
    raw_id_fields = ("event",)
    ordering = ("event", "display_order")


@admin.register(RegistrationResponse)
class RegistrationResponseAdmin(admin.ModelAdmin):
    """Admin for participant responses to custom form fields."""

    list_display = ("registration", "field", "response_value")
    search_fields = ("registration__registration_id", "field__field_label")
    raw_id_fields = ("registration", "field")
