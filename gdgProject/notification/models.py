"""
Domain model for in-app notifications.
"""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    """
    An in-app notification for a user.

    Supports a generic foreign key (`target_ct` + `target_id`) so a single
    notification type can point at any model instance (Event, Team, JoinRequest…).
    """

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(
        max_length=50,
        db_index=True,
        help_text=_("join_request | announcement | reminder | system"),
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    read = models.BooleanField(default=False, db_index=True)

    # ── Actor (the user who triggered the notification) ────────────────────
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_notifications",
    )

    # ── Generic target (points at any model instance) ─────────────────────
    target_ct = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    target_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey("target_ct", "target_id")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_notif_user_time"),
            models.Index(fields=["user", "read"], name="idx_notif_user_read"),
        ]

    def __str__(self) -> str:
        return f"{self.user}: {self.title}"
