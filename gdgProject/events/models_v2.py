"""
Domain models for the events app.

These are the two most critical domain models — Event and EventRound.
They replace the empty models.py stub and drive the entire platform.
"""
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class EventCategory(models.TextChoices):
    HACKATHON = "hackathon", "Hackathon"
    WORKSHOP = "workshop", "Workshop"
    CODING_CONTEST = "coding_contest", "Coding Contest"
    QUIZ = "quiz", "Quiz / Competition"
    PAPER_PRESENTATION = "paper_presentation", "Paper Presentation"
    DESIGN_CHALLENGE = "design_challenge", "Design Challenge"
    IDEATHON = "ideathon", "Ideathon"
    CASE_STUDY = "case_study", "Case Study"
    CULTURAL = "cultural", "Cultural"
    SPORTS = "sports", "Sports"
    OTHER = "other", "Other"


class EventMode(models.TextChoices):
    ONLINE = "online", "Online"
    OFFLINE = "offline", "Offline"
    HYBRID = "hybrid", "Hybrid"


class ParticipationType(models.TextChoices):
    INDIVIDUAL = "individual", "Individual"
    TEAM = "team", "Team"
    BOTH = "both", "Both"


class EventStatus(models.TextChoices):
    """
    Allowed transitions:
        draft → published → registration_open → registration_closed → ongoing → completed
        draft → cancelled (from any mutable state)
        published → archived (soft-delete)
    """
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    REGISTRATION_OPEN = "registration_open", "Registration Open"
    REGISTRATION_CLOSED = "registration_closed", "Registration Closed"
    ONGOING = "ongoing", "Ongoing"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    ARCHIVED = "archived", "Archived"


class Event(models.Model):
    """
    Core event entity — hackathons, workshops, quizzes, etc.
    Invariants:
    - registration_end >= registration_start
    - event_end >= event_start
    - max_team_size >= min_team_size (when team-based)
    - capacity >= 1
    """

    # ── Identity ──────────────────────────────────────────────────────────
    id = models.BigAutoField(primary_key=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField()

    # ── Classification ────────────────────────────────────────────────────
    category = models.CharField(
        max_length=30,
        choices=EventCategory.choices,
        default=EventCategory.OTHER,
        db_index=True,
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
    status = models.CharField(
        max_length=25,
        choices=EventStatus.choices,
        default=EventStatus.DRAFT,
        db_index=True,
    )

    # ── Dates ─────────────────────────────────────────────────────────────
    registration_start = models.DateTimeField()
    registration_end = models.DateTimeField()
    event_start = models.DateTimeField()
    event_end = models.DateTimeField()
    submission_deadline = models.DateTimeField(null=True, blank=True)

    # ── Location / Platform ───────────────────────────────────────────────
    venue = models.CharField(max_length=300, blank=True, default="")
    platform_link = models.URLField(blank=True, default="")

    # ── Capacity & Team Rules ─────────────────────────────────────────────
    capacity = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        help_text="Maximum number of participants or teams",
    )
    min_team_size = models.PositiveSmallIntegerField(default=1)
    max_team_size = models.PositiveSmallIntegerField(default=1)
    allow_team_creation = models.BooleanField(default=True)
    allow_join_requests = models.BooleanField(default=True)

    # ── Prizes ────────────────────────────────────────────────────────────
    prize_pool = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    prize_1st = models.CharField(max_length=200, blank=True, default="")
    prize_2nd = models.CharField(max_length=200, blank=True, default="")
    prize_3rd = models.CharField(max_length=200, blank=True, default="")
    prize_special = models.CharField(max_length=500, blank=True, default="")

    # ── Certificates & Fee ────────────────────────────────────────────────
    participation_certificate = models.BooleanField(default=False)
    merit_certificate = models.BooleanField(default=False)
    registration_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )

    # ── Eligibility ───────────────────────────────────────────────────────
    eligibility = models.TextField(blank=True, default="Open to all")

    # ── Media ─────────────────────────────────────────────────────────────
    banner = models.ImageField(upload_to="events/banners/", blank=True)
    rules = models.TextField(blank=True, default="")
    faqs = models.JSONField(default=list, blank=True, help_text='[{"q": "...", "a": "..."}]')
    contact_info = models.TextField(blank=True, default="")

    # ── Ownership & Audit ─────────────────────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-event_start"]
        indexes = [
            models.Index(fields=["status", "category"], name="idx_event_status_cat"),
            models.Index(fields=["registration_end"], name="idx_event_reg_end"),
            models.Index(fields=["created_by", "-created_at"], name="idx_event_owner"),
            models.Index(
                fields=["status"],
                name="idx_event_active",
                condition=models.Q(is_deleted=False),
            ),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(registration_end__gte=models.F("registration_start")),
                name="chk_reg_dates",
            ),
            models.CheckConstraint(
                check=models.Q(event_end__gte=models.F("event_start")),
                name="chk_event_dates",
            ),
            models.CheckConstraint(
                check=models.Q(max_team_size__gte=models.F("min_team_size")),
                name="chk_team_size",
            ),
            models.CheckConstraint(
                check=models.Q(capacity__gte=1),
                name="chk_capacity_positive",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def is_registration_open(self):
        now = timezone.now()
        return (
            self.status == EventStatus.REGISTRATION_OPEN
            and self.registration_start <= now <= self.registration_end
            and not self.is_deleted
        )

    @property
    def spots_remaining(self):
        """Requires annotation or sub-query in practice; placeholder logic."""
        registered = self.registrations.filter(
            status__in=["confirmed", "submitted"]
        ).count()
        return max(0, self.capacity - registered)

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        if self.registration_end and self.registration_start:
            if self.registration_end < self.registration_start:
                errors["registration_end"] = "Must be after registration start."
        if self.event_end and self.event_start:
            if self.event_end < self.event_start:
                errors["event_end"] = "Must be after event start."
        if self.max_team_size < self.min_team_size:
            errors["max_team_size"] = "Must be >= min team size."
        if errors:
            raise ValidationError(errors)


class RoundStatus(models.TextChoices):
    UPCOMING = "upcoming", "Upcoming"
    ONGOING = "ongoing", "Ongoing"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class EventRound(models.Model):
    """
    A phase/round within an event (e.g., Idea Screening → Prototype → Finals).
    Invariants:
    - order is unique per event
    - end_date >= start_date
    """

    id = models.BigAutoField(primary_key=True)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="rounds",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    order = models.PositiveSmallIntegerField(default=1)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(
        max_length=15,
        choices=RoundStatus.choices,
        default=RoundStatus.UPCOMING,
    )
    elimination_criteria = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["event", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "order"],
                name="uniq_event_round_order",
            ),
            models.CheckConstraint(
                check=models.Q(end_date__gte=models.F("start_date")),
                name="chk_round_dates",
            ),
        ]

    def __str__(self):
        return f"{self.event.title} — Round {self.order}: {self.name}"
