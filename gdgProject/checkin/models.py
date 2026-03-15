"""
Check-in models.

Each registration gets one QR token. Scanning it marks the participant
as checked-in. Tokens are scoped to an event so the same QR cannot be
reused across events.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class CheckIn(models.Model):
    """One check-in record per registration."""

    id = models.BigAutoField(primary_key=True)
    registration = models.OneToOneField(
        "registration.Registration",
        on_delete=models.CASCADE,
        related_name="checkin",
    )
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="checkins",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="checkins",
    )
    # Opaque token embedded in the QR code
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checkins_performed",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event", "checked_in"], name="idx_checkin_event_status"),
        ]

    def __str__(self):
        status = "checked-in" if self.checked_in else "pending"
        return f"{self.user} @ {self.event.title} ({status})"

    @property
    def scan_url(self):
        return f"/checkin/scan/{self.token}/"
