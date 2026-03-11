"""
Domain models for the team app.

Team, TeamMembership (through model), JoinRequest, and ChatMessage.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class TeamStatus(models.TextChoices):
    OPEN = "open", _("Open")
    CLOSED = "closed", _("Closed")
    DISBANDED = "disbanded", _("Disbanded")


# ── Managers ─────────────────────────────────────────────────────────────────


class ActiveTeamManager(models.Manager):
    """Default manager — excludes soft-deleted / disbanded teams."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllTeamManager(models.Manager):
    """Unfiltered manager — includes soft-deleted teams."""

    def get_queryset(self):
        return super().get_queryset()


# ── Models ────────────────────────────────────────────────────────────────────


class Team(models.Model):
    """
    A team registered for a specific event.

    Invariants:
    - (event, name) is unique
    - A user can lead at most one team per event
    """

    id = models.BigAutoField(primary_key=True)
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="teams",
    )
    name = models.CharField(max_length=100)
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="led_teams",
    )
    status = models.CharField(
        max_length=12,
        choices=TeamStatus.choices,
        default=TeamStatus.OPEN,
        db_index=True,
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Managers ──────────────────────────────────────────────────────────
    objects = ActiveTeamManager()  # default — excludes soft-deleted
    all_objects = AllTeamManager()  # includes soft-deleted

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "name"],
                name="uniq_team_name_per_event",
            ),
            models.UniqueConstraint(
                fields=["event", "leader"],
                name="uniq_leader_per_event",
            ),
        ]
        indexes = [
            models.Index(fields=["event", "status"], name="idx_team_event_status"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.event.title})"

    def delete(self, using=None, keep_parents=False):  # type: ignore[override]
        """Soft-delete."""
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "updated_at"])

    def hard_delete(self, **kwargs):
        super().delete(**kwargs)

    @property
    def member_count(self) -> int:
        return self.memberships.count()

    @property
    def is_full(self) -> bool:
        return self.member_count >= self.event.max_team_size

    @property
    def spots_available(self) -> int:
        return max(0, self.event.max_team_size - self.member_count)


class MemberRole(models.TextChoices):
    FRONTEND = "frontend", _("Frontend Developer")
    BACKEND = "backend", _("Backend Developer")
    FULLSTACK = "fullstack", _("Full Stack Developer")
    MOBILE = "mobile", _("Mobile Developer")
    UIUX = "uiux", _("UI/UX Designer")
    ML_AI = "ml_ai", _("ML/AI Engineer")
    DATA = "data", _("Data Scientist")
    DEVOPS = "devops", _("DevOps Engineer")
    PM = "pm", _("Project Manager")
    OTHER = "other", _("Other")


class TeamMembership(models.Model):
    """
    Through model for Team ↔ User (M2M).

    Invariants:
    - A user can be in only one team per event (enforced at service layer + constraint)
    """

    id = models.BigAutoField(primary_key=True)
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="team_memberships",
    )
    role = models.CharField(
        max_length=15,
        choices=MemberRole.choices,
        default=MemberRole.OTHER,
    )
    skills = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text=_("Comma-separated skills for this event context"),
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["team", "user"],
                name="uniq_user_per_team",
            ),
        ]
        indexes = [
            models.Index(fields=["user"], name="idx_membership_user"),
        ]

    def __str__(self) -> str:
        return f"{self.user} in {self.team.name}"


class JoinRequestStatus(models.TextChoices):
    """
    Transitions:
        pending → approved | declined | cancelled
        (terminal states: approved, declined, cancelled)
    """

    PENDING = "pending", _("Pending")
    APPROVED = "approved", _("Approved")
    DECLINED = "declined", _("Declined")
    CANCELLED = "cancelled", _("Cancelled")


class JoinRequest(models.Model):
    """
    A request from a user to join a team.

    Invariants:
    - (team, user) is unique per pending request
    - User cannot request to join their own team
    - User cannot request if already a member of another team for the same event
    """

    id = models.BigAutoField(primary_key=True)
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="join_requests",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="join_requests_sent",
    )
    role = models.CharField(
        max_length=15,
        choices=MemberRole.choices,
        default=MemberRole.OTHER,
    )
    skills = models.CharField(max_length=500, blank=True, default="")
    message = models.TextField(
        max_length=500,
        blank=True,
        default="",
        help_text=_("Optional message to the team leader"),
    )
    status = models.CharField(
        max_length=12,
        choices=JoinRequestStatus.choices,
        default=JoinRequestStatus.PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "user"],
                condition=models.Q(status="pending"),
                name="uniq_pending_request_per_team_user",
            ),
        ]
        indexes = [
            models.Index(fields=["team", "status"], name="idx_joinreq_team_status"),
            models.Index(fields=["user", "status"], name="idx_joinreq_user_status"),
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.team.name} ({self.get_status_display()})"


class ChatMessage(models.Model):
    """
    A persistent chat message within a team's channel.
    """

    id = models.BigAutoField(primary_key=True)
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="team_messages",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["team", "created_at"]
        indexes = [
            models.Index(fields=["team", "created_at"], name="idx_chat_team_time"),
        ]

    def __str__(self) -> str:
        sender_name = self.sender.username if self.sender else _("deleted user")
        return f"{sender_name} → {self.team.name}: {self.body[:50]}"
