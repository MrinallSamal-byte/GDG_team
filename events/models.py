from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone


class Event(models.Model):
    """Core event model with all fields from the specification."""

    CATEGORY_CHOICES = [
        ('hackathon', 'Hackathon'),
        ('coding_contest', 'Coding Contest'),
        ('workshop', 'Workshop'),
        ('quiz', 'Quiz / Competition'),
        ('paper_presentation', 'Paper Presentation'),
        ('design', 'Design Challenge'),
        ('ideathon', 'Ideathon'),
        ('case_study', 'Case Study'),
        ('cultural', 'Cultural'),
        ('sports', 'Sports'),
        ('other', 'Other'),
    ]

    MODE_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('hybrid', 'Hybrid'),
    ]

    PARTICIPATION_CHOICES = [
        ('individual', 'Individual'),
        ('team', 'Team-Based'),
        ('both', 'Both'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organized_events')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    description = models.TextField(help_text='Rich text description of the event')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    banner_image = models.ImageField(upload_to='events/banners/', blank=True, null=True)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    venue = models.CharField(max_length=300, blank=True, default='')
    platform_link = models.URLField(max_length=500, blank=True, default='')

    # Timeline
    registration_start = models.DateTimeField()
    registration_end = models.DateTimeField()
    event_start = models.DateTimeField()
    event_end = models.DateTimeField()
    submission_deadline = models.DateTimeField(null=True, blank=True)

    # Participation
    participation_type = models.CharField(max_length=15, choices=PARTICIPATION_CHOICES, default='individual')
    min_team_size = models.PositiveIntegerField(null=True, blank=True)
    max_team_size = models.PositiveIntegerField(null=True, blank=True)
    allow_team_creation = models.BooleanField(default=True)
    allow_join_requests = models.BooleanField(default=True)

    # Details
    eligibility = models.TextField(blank=True, default='')
    prize_pool_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    has_participation_certificate = models.BooleanField(default=False)
    has_merit_certificate = models.BooleanField(default=False)
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    contact_email = models.EmailField(max_length=255, blank=True, default='')
    contact_phone = models.CharField(max_length=15, blank=True, default='')
    rules = models.TextField(blank=True, default='')

    # Status
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'category']),
            models.Index(fields=['registration_end']),
            models.Index(fields=['is_featured']),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('events:event_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.title)
            slug = base_slug
            n = 1
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_registration_open(self):
        now = timezone.now()
        return self.registration_start <= now <= self.registration_end and self.status == 'published'

    @property
    def is_team_event(self):
        return self.participation_type in ('team', 'both')

    @property
    def registration_count(self):
        return self.registrations.filter(status='confirmed').count()

    @property
    def spots_remaining(self):
        if self.max_participants:
            return max(0, self.max_participants - self.registration_count)
        return None

    @property
    def is_full(self):
        if self.max_participants:
            return self.registration_count >= self.max_participants
        return False

    @property
    def registration_percentage(self):
        if self.max_participants and self.max_participants > 0:
            return min(100, int((self.registration_count / self.max_participants) * 100))
        return 0

    @property
    def days_until_deadline(self):
        delta = self.registration_end - timezone.now()
        return max(0, delta.days)

    @property
    def is_free(self):
        return self.registration_fee == 0


class EventPrize(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='prizes')
    position = models.CharField(max_length=50)
    prize_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prize_description = models.CharField(max_length=500, blank=True, default='')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.position} — ₹{self.prize_amount}"


class EventRound(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='rounds')
    round_number = models.PositiveIntegerField()
    round_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    elimination_criteria = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['round_number']

    def __str__(self):
        return f"Round {self.round_number}: {self.round_name}"


class EventFAQ(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='faqs')
    question = models.TextField()
    answer = models.TextField()
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.question[:60]


class EventJudge(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='judges')
    name = models.CharField(max_length=100)
    designation = models.CharField(max_length=200, blank=True, default='')
    photo = models.ImageField(upload_to='events/judges/', blank=True, null=True)
    bio = models.TextField(blank=True, default='')

    def __str__(self):
        return self.name


class EventSponsor(models.Model):
    SPONSOR_TYPE_CHOICES = [
        ('title', 'Title Sponsor'),
        ('gold', 'Gold Sponsor'),
        ('silver', 'Silver Sponsor'),
        ('bronze', 'Bronze Sponsor'),
        ('partner', 'Partner'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='sponsors')
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='events/sponsors/', blank=True, null=True)
    website_url = models.URLField(max_length=500, blank=True, default='')
    sponsor_type = models.CharField(max_length=10, choices=SPONSOR_TYPE_CHOICES, default='partner')

    class Meta:
        ordering = ['sponsor_type']

    def __str__(self):
        return f"{self.name} ({self.get_sponsor_type_display()})"


class EventAnnouncement(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class CustomFormField(models.Model):
    """Organizer-defined custom fields for event registration forms."""

    FIELD_TYPE_CHOICES = [
        ('text', 'Short Text'),
        ('textarea', 'Long Text'),
        ('number', 'Number'),
        ('dropdown', 'Dropdown Select'),
        ('multi_select', 'Multi-Select'),
        ('radio', 'Radio Buttons'),
        ('file', 'File Upload'),
        ('date', 'Date Picker'),
        ('url', 'URL Input'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='custom_fields')
    field_label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES)
    field_options = models.JSONField(default=list, blank=True, help_text='Options for dropdown/multi-select/radio')
    is_required = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    placeholder = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return f"{self.field_label} ({self.get_field_type_display()})"
