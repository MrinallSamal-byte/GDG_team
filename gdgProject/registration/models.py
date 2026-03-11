"""
Domain model for event registrations.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


def _generate_registration_id():
    """Generate a short unique registration ID."""
    return f"REG-{uuid.uuid4().hex[:8].upper()}"


class RegistrationType(models.TextChoices):
    INDIVIDUAL = "individual", _("Individual")
    TEAM = "team", _("Team")


class RegistrationStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    CONFIRMED = "confirmed", _("Confirmed")
    CANCELLED = "cancelled", _("Cancelled")
    SUBMITTED = "submitted", _("Submitted")


class Registration(models.Model):
    """
    Records a user's participation in an event — either solo or as part of a team.

    Invariants:
    - (event, user) must be unique
    - type='team' requires team IS NOT NULL
    """

    id = models.BigAutoField(primary_key=True)
    registration_id = models.CharField(
        max_length=20,
        unique=True,
        default=_generate_registration_id,
        editable=False,
        help_text=_("Auto-generated unique readable ID, e.g. EVT-2026-00123"),
    )
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="registrations",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="registrations",
    )
    type = models.CharField(
        max_length=12,
        choices=RegistrationType.choices,
        default=RegistrationType.INDIVIDUAL,
    )
    team = models.ForeignKey(
        "team.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registrations",
    )
    status = models.CharField(
        max_length=12,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.PENDING,
        db_index=True,
    )
    looking_for_team = models.BooleanField(
        default=False,
        help_text=_("User is looking for a team to join"),
    )
    preferred_role = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text=_("Preferred role in a team, e.g. Frontend Developer"),
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-registered_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "user"],
                name="uniq_reg_per_event",
            ),
            models.CheckConstraint(
                condition=(~models.Q(type="team") | models.Q(team__isnull=False)),
                name="chk_team_reg_requires_team",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-registered_at"], name="idx_reg_user_time"),
            models.Index(fields=["event", "status"], name="idx_reg_event_status"),
        ]

    def __str__(self) -> str:
        return f"{self.registration_id} — {self.user} @ {self.event.title}"


# ── Custom Registration Form Fields ──────────────────────────────────────────


class FieldType(models.TextChoices):
    """Supported input types for organizer-defined registration form fields."""

    TEXT = "text", _("Short Text")
    TEXTAREA = "textarea", _("Long Text")
    NUMBER = "number", _("Number")
    DROPDOWN = "dropdown", _("Dropdown")
    MULTI_SELECT = "multi_select", _("Multi-Select")
    RADIO = "radio", _("Radio Buttons")
    FILE = "file", _("File Upload")
    DATE = "date", _("Date")
    URL = "url", _("URL")


class CustomFormField(models.Model):
    """
    An organizer-defined custom field added to an event's registration form.

    Displayed to participants during registration after the default fields.
    """

    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="custom_fields",
    )
    field_label = models.CharField(max_length=200)
    field_type = models.CharField(
        max_length=15,
        choices=FieldType.choices,
        default=FieldType.TEXT,
    )
    field_options = models.JSONField(
        default=list,
        blank=True,
        help_text=_(
            '["Option A", "Option B"] — for dropdown/radio/multi-select fields'
        ),
    )
    is_required = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0, db_index=True)
    placeholder = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["event", "display_order"]

    def __str__(self) -> str:
        return f"{self.event.title} — {self.field_label}"


class RegistrationResponse(models.Model):
    """
    A participant's answer to one custom form field.

    One row per (Registration, CustomFormField) pair.
    """

    registration = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    field = models.ForeignKey(
        CustomFormField,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    response_value = models.TextField(blank=True, default="")
    file_url = models.FileField(
        upload_to="registrations/uploads/",
        blank=True,
        help_text=_("Uploaded file for file-type custom fields"),
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["registration", "field"],
                name="uniq_response_per_field",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.registration.registration_id} — {self.field.field_label}"


class RegistrationTechStack(models.Model):
    """
    A tech stack entry tied to a specific registration (event context).

    Allows capturing skills per-event rather than only at the profile level.
    """

    registration = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE,
        related_name="tech_stacks",
    )
    tech_name = models.CharField(max_length=50)
    is_primary = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["registration", "tech_name"],
                name="uniq_reg_tech",
            ),
        ]
        ordering = ["registration", "-is_primary", "tech_name"]

    def __str__(self) -> str:
        label = "Primary" if self.is_primary else "Secondary"
        return f"{self.registration.registration_id} — {self.tech_name} ({label})"
