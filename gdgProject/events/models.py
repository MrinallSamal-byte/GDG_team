"""
Domain models for the events app.

Event and EventRound are the core domain entities driving the platform.
"""
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class EventCategory(models.TextChoices):
    HACKATHON = "hackathon", _("Hackathon")
    WORKSHOP = "workshop", _("Workshop")
    CODING_CONTEST = "coding_contest", _("Coding Contest")
    QUIZ = "quiz", _("Quiz / Competition")
    PAPER_PRESENTATION = "paper_presentation", _("Paper Presentation")
    DESIGN_CHALLENGE = "design_challenge", _("Design Challenge")
    IDEATHON = "ideathon", _("Ideathon")
    CASE_STUDY = "case_study", _("Case Study")
    CULTURAL = "cultural", _("Cultural")
    SPORTS = "sports", _("Sports")
    OTHER = "other", _("Other")


class EventMode(models.TextChoices):
    ONLINE = "online", _("Online")
    OFFLINE = "offline", _("Offline")
    HYBRID = "hybrid", _("Hybrid")


class ParticipationType(models.TextChoices):
    INDIVIDUAL = "individual", _("Individual")
    TEAM = "team", _("Team")
    BOTH = "both", _("Both")


class EventStatus(models.TextChoices):
    """
    Allowed transitions:
        draft → published → registration_open → registration_closed → ongoing → completed
        draft → cancelled (from any mutable state)
        published → archived (soft-delete)
    """
    DRAFT = "draft", _("Draft")
    PUBLISHED = "published", _("Published")
    REGISTRATION_OPEN = "registration_open", _("Registration Open")
    REGISTRATION_CLOSED = "registration_closed", _("Registration Closed")
    ONGOING = "ongoing", _("Ongoing")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")
    ARCHIVED = "archived", _("Archived")


# ── Managers ─────────────────────────────────────────────────────────────────

class ActiveEventManager(models.Manager):
    """Default manager — excludes soft-deleted events."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllEventManager(models.Manager):
    """Unfiltered manager — includes soft-deleted events (admin use only)."""

    def get_queryset(self):
        return super().get_queryset()


# ── Models ────────────────────────────────────────────────────────────────────

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
        help_text=_("Maximum number of participants or teams"),
    )
    min_team_size = models.PositiveSmallIntegerField(default=1)
    max_team_size = models.PositiveSmallIntegerField(default=1)
    allow_team_creation = models.BooleanField(default=True)
    allow_join_requests = models.BooleanField(default=True)

    # ── Prizes ────────────────────────────────────────────────────────────
    prize_pool = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    prize_1st = models.CharField(max_length=200, blank=True, default="")
    prize_2nd = models.CharField(max_length=200, blank=True, default="")
    prize_3rd = models.CharField(max_length=200, blank=True, default="")
    prize_special = models.CharField(max_length=500, blank=True, default="")

    # ── Certificates & Fee ────────────────────────────────────────────────
    participation_certificate = models.BooleanField(default=False)
    merit_certificate = models.BooleanField(default=False)
    registration_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # ── Eligibility ───────────────────────────────────────────────────────
    eligibility = models.TextField(blank=True, default=_("Open to all"))

    # ── Media ─────────────────────────────────────────────────────────────
    banner = models.ImageField(upload_to="events/banners/", blank=True)
    rules = models.TextField(blank=True, default="")
    faqs = models.JSONField(
        default=list, blank=True,
        help_text='[{"q": "...", "a": "..."}]',
    )
    contact_info = models.TextField(blank=True, default="")

    # ── Featured ────────────────────────────────────────────────────────────
    is_featured = models.BooleanField(default=False, db_index=True)

    # ── Ownership & Audit ─────────────────────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)

    # ── Managers ──────────────────────────────────────────────────────────
    objects = ActiveEventManager()   # default — excludes soft-deleted
    all_objects = AllEventManager()  # includes soft-deleted (admin)

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
                condition=models.Q(registration_end__gte=models.F("registration_start")),
                name="chk_reg_dates",
            ),
            models.CheckConstraint(
                condition=models.Q(event_end__gte=models.F("event_start")),
                name="chk_event_dates",
            ),
            models.CheckConstraint(
                condition=models.Q(max_team_size__gte=models.F("min_team_size")),
                name="chk_team_size",
            ),
            models.CheckConstraint(
                condition=models.Q(capacity__gte=1),
                name="chk_capacity_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"

    def delete(self, using=None, keep_parents=False):  # type: ignore[override]
        """Soft-delete: set is_deleted=True instead of removing the row."""
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "updated_at"])

    def hard_delete(self, **kwargs):
        """Permanent deletion — use only from admin/management commands."""
        super().delete(**kwargs)

    @property
    def is_registration_open(self) -> bool:
        now = timezone.now()
        return (
            self.status == EventStatus.REGISTRATION_OPEN
            and self.registration_start <= now <= self.registration_end
            and not self.is_deleted
        )

    @property
    def spots_remaining(self) -> int:
        """
        Python-side calculation for single-object use.
        For list views use annotated `registered_count` to avoid N+1.
        """
        registered = self.registrations.filter(
            status__in=["confirmed", "submitted"]
        ).count()
        return max(0, self.capacity - registered)

    def save(self, *args, **kwargs) -> None:  # type: ignore[override]
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.title)
            slug = base_slug
            n = 1
            while Event.all_objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        errors: dict = {}
        if self.registration_end and self.registration_start:
            if self.registration_end < self.registration_start:
                errors["registration_end"] = _("Must be after registration start.")
        if self.event_end and self.event_start:
            if self.event_end < self.event_start:
                errors["event_end"] = _("Must be after event start.")
        if self.max_team_size < self.min_team_size:
            errors["max_team_size"] = _("Must be >= min team size.")
        if errors:
            raise ValidationError(errors)


class RoundStatus(models.TextChoices):
    UPCOMING = "upcoming", _("Upcoming")
    ONGOING = "ongoing", _("Ongoing")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")


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
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="chk_round_dates",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event.title} — Round {self.order}: {self.name}"


class SponsorType(models.TextChoices):
    TITLE = "title", _("Title Sponsor")
    GOLD = "gold", _("Gold Sponsor")
    SILVER = "silver", _("Silver Sponsor")
    BRONZE = "bronze", _("Bronze Sponsor")
    PARTNER = "partner", _("Partner")


class EventJudge(models.Model):
    """A judge or mentor associated with an event."""

    id = models.BigAutoField(primary_key=True)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="judges",
    )
    name = models.CharField(max_length=100)
    designation = models.CharField(max_length=200, blank=True, default="")
    photo = models.ImageField(upload_to="events/judges/", blank=True)
    bio = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["event", "name"]

    def __str__(self) -> str:
        return f"{self.name} — {self.event.title}"


class EventSponsor(models.Model):
    """A sponsor or partner associated with an event."""

    id = models.BigAutoField(primary_key=True)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="sponsors",
    )
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to="events/sponsors/", blank=True)
    website_url = models.URLField(blank=True, default="")
    sponsor_type = models.CharField(
        max_length=10,
        choices=SponsorType.choices,
        default=SponsorType.PARTNER,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["event", "sponsor_type", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_sponsor_type_display()}) — {self.event.title}"


class EventAnnouncement(models.Model):
    """An announcement posted by the organizer to event registrants."""

    id = models.BigAutoField(primary_key=True)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="announcements",
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} — {self.event.title}"
