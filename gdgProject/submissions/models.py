"""
Submission models.

Teams or individuals submit their hackathon project via a URL,
optional file upload, and free-text description.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class SubmissionStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    SUBMITTED = "submitted", _("Submitted")
    REVIEWED = "reviewed", _("Reviewed")
    DISQUALIFIED = "disqualified", _("Disqualified")


class Submission(models.Model):
    id = models.BigAutoField(primary_key=True)
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    # A submission belongs to a team OR an individual
    team = models.ForeignKey(
        "team.Team",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="submissions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    project_url = models.URLField(blank=True, default="", help_text=_("GitHub / live demo URL"))
    presentation_url = models.URLField(blank=True, default="", help_text=_("Slides / Figma link"))
    file_upload = models.FileField(upload_to="submissions/files/", blank=True)
    status = models.CharField(
        max_length=15,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.DRAFT,
        db_index=True,
    )
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    judge_notes = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # One submission per team per event
            models.UniqueConstraint(
                fields=["event", "team"],
                condition=models.Q(team__isnull=False),
                name="uniq_submission_team_event",
            ),
            # One submission per solo user per event
            models.UniqueConstraint(
                fields=["event", "user"],
                condition=models.Q(team__isnull=True),
                name="uniq_submission_user_event",
            ),
        ]
        indexes = [
            models.Index(fields=["event", "status"], name="idx_submission_event_status"),
        ]

    def __str__(self):
        entity = self.team.name if self.team else (self.user.get_full_name() or self.user.username)
        return f"{self.title} by {entity} @ {self.event.title}"
