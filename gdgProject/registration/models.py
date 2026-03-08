"""
Domain model for event registrations.
"""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


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
                condition=(
                    ~models.Q(type="team") | models.Q(team__isnull=False)
                ),
                name="chk_team_reg_requires_team",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-registered_at"], name="idx_reg_user_time"),
            models.Index(fields=["event", "status"], name="idx_reg_event_status"),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.event.title} ({self.get_status_display()})"
