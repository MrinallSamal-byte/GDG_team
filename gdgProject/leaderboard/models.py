"""
Leaderboard models.

Each event can have one leaderboard. Entries are per-team or per-user
depending on the event's participation type.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Leaderboard(models.Model):
    """One leaderboard per event."""

    event = models.OneToOneField(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="leaderboard",
    )
    is_public = models.BooleanField(
        default=False,
        help_text=_("If False, only the organizer can see the leaderboard."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Leaderboard — {self.event.title}"


class LeaderboardEntry(models.Model):
    """A single ranked entry on a leaderboard."""

    leaderboard = models.ForeignKey(
        Leaderboard,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    rank = models.PositiveSmallIntegerField()
    score = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    label = models.CharField(
        max_length=200,
        help_text=_("Team name or participant name"),
    )
    # Optional FK to team or user — one of these will be set
    team = models.ForeignKey(
        "team.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leaderboard_entries",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leaderboard_entries",
    )
    notes = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["leaderboard", "rank"]
        constraints = [
            models.UniqueConstraint(
                fields=["leaderboard", "rank"],
                name="uniq_leaderboard_rank",
            )
        ]

    def __str__(self):
        return f"#{self.rank} {self.label} — {self.leaderboard.event.title}"
