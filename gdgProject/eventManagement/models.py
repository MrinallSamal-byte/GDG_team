from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from events.models import Event, EventCategory, EventMode, ParticipationType


class EventRequestStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")


class EventCreationRequest(models.Model):
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_creation_requests",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_event_creation_requests",
    )
    created_event = models.OneToOneField(
        Event,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="creation_request",
    )

    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField()
    category = models.CharField(
        max_length=30,
        choices=EventCategory.choices,
        default=EventCategory.OTHER,
    )
    mode = models.CharField(
        max_length=10,
        choices=EventMode.choices,
        default=EventMode.OFFLINE,
    )
    participation_type = models.CharField(
        max_length=12,
        choices=ParticipationType.choices,
        default=ParticipationType.INDIVIDUAL,
    )
    registration_start = models.DateTimeField()
    registration_end = models.DateTimeField()
    event_start = models.DateTimeField()
    event_end = models.DateTimeField()
    venue = models.CharField(max_length=300, blank=True, default="")
    platform_link = models.URLField(blank=True, default="")
    capacity = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1)],
    )
    min_team_size = models.PositiveSmallIntegerField(default=1)
    max_team_size = models.PositiveSmallIntegerField(default=1)
    registration_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    rules = models.TextField(blank=True, default="")
    contact_info = models.TextField(blank=True, default="")

    status = models.CharField(
        max_length=15,
        choices=EventRequestStatus.choices,
        default=EventRequestStatus.PENDING,
        db_index=True,
    )
    review_note = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "-created_at"]
        indexes = [
            models.Index(
                fields=["status", "-created_at"],
                name="idx_event_request_status_time",
            ),
            models.Index(
                fields=["requested_by", "-created_at"],
                name="idx_event_request_user_time",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    registration_end__gte=models.F("registration_start")
                ),
                name="chk_event_request_reg_dates",
            ),
            models.CheckConstraint(
                condition=models.Q(event_end__gte=models.F("event_start")),
                name="chk_event_request_event_dates",
            ),
            models.CheckConstraint(
                condition=models.Q(max_team_size__gte=models.F("min_team_size")),
                name="chk_event_request_team_size",
            ),
            models.CheckConstraint(
                condition=models.Q(capacity__gte=1),
                name="chk_event_request_capacity_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"
