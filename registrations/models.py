import uuid
from django.db import models
from django.conf import settings


class Registration(models.Model):
    """Event registration for individual or team participation."""

    TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('team', 'Team'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]

    ROLE_CHOICES = [
        ('frontend_dev', 'Frontend Developer'),
        ('backend_dev', 'Backend Developer'),
        ('fullstack_dev', 'Full Stack Developer'),
        ('mobile_dev', 'Mobile Developer'),
        ('ui_ux', 'UI/UX Designer'),
        ('ml_ai', 'ML/AI Engineer'),
        ('data_scientist', 'Data Scientist'),
        ('devops', 'DevOps Engineer'),
        ('project_manager', 'Project Manager'),
        ('other', 'Other'),
    ]

    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='registrations')
    team = models.ForeignKey('teams.Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='registrations')
    registration_type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='confirmed')
    registration_id = models.CharField(max_length=20, unique=True, editable=False)
    looking_for_team = models.BooleanField(default=False)
    preferred_role = models.CharField(max_length=30, choices=ROLE_CHOICES, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['event', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.registration_id} — {self.user.display_name} → {self.event.title}"

    def save(self, *args, **kwargs):
        if not self.registration_id:
            self.registration_id = self._generate_id()
        super().save(*args, **kwargs)

    def _generate_id(self):
        short = uuid.uuid4().hex[:6].upper()
        return f"CA-{self.event_id or '0'}-{short}"


class RegistrationResponse(models.Model):
    """Stores responses to custom form fields."""

    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='responses')
    field = models.ForeignKey('events.CustomFormField', on_delete=models.CASCADE)
    response_value = models.TextField(blank=True, default='')
    file_url = models.FileField(upload_to='registrations/uploads/', blank=True, null=True)

    def __str__(self):
        return f"{self.field.field_label}: {self.response_value[:50]}"


class RegistrationTechStack(models.Model):
    """Tech stacks selected during event registration."""

    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='tech_stacks')
    tech_name = models.CharField(max_length=50)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_primary', 'tech_name']

    def __str__(self):
        return self.tech_name
