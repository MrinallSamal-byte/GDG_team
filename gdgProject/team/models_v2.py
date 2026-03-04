"""
Domain models for the team app.

Team, TeamMembership (through table), and JoinRequest — the second
critical domain cluster. Drives team formation, skill-balancing, and
the join-request approval workflow.
"""
from django.conf import settings
from django.db import models


class TeamStatus(models.TextChoices):
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"
    DISBANDED = "disbanded", "Disbanded"


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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

    def __str__(self):
        return f"{self.name} ({self.event.title})"

    @property
    def member_count(self):
        return self.memberships.count()

    @property
    def is_full(self):
        return self.member_count >= self.event.max_team_size

    @property
    def spots_available(self):
        return max(0, self.event.max_team_size - self.member_count)


class MemberRole(models.TextChoices):
    FRONTEND = "frontend", "Frontend Developer"
    BACKEND = "backend", "Backend Developer"
    FULLSTACK = "fullstack", "Full Stack Developer"
    MOBILE = "mobile", "Mobile Developer"
    UIUX = "uiux", "UI/UX Designer"
    ML_AI = "ml_ai", "ML/AI Engineer"
    DATA = "data", "Data Scientist"
    DEVOPS = "devops", "DevOps Engineer"
    PM = "pm", "Project Manager"
    OTHER = "other", "Other"


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
        help_text="Comma-separated skills for this event context",
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

    def __str__(self):
        return f"{self.user} in {self.team.name}"


class JoinRequestStatus(models.TextChoices):
    """
    Transitions:
        pending → approved | declined | cancelled
        (terminal states: approved, declined, cancelled)
    """
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    DECLINED = "declined", "Declined"
    CANCELLED = "cancelled", "Cancelled"


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
        help_text="Optional message to the team leader",
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
            models.Index(
                fields=["team", "status"],
                name="idx_joinreq_team_status",
            ),
            models.Index(
                fields=["user", "status"],
                name="idx_joinreq_user_status",
            ),
        ]

    def __str__(self):
        return f"{self.user} → {self.team.name} ({self.get_status_display()})"
