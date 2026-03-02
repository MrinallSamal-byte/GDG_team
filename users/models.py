from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class User(AbstractUser):
    """Custom user model with extended profile fields for CampusArena."""

    ROLE_CHOICES = [
        ('admin', 'Super Admin'),
        ('organizer', 'Event Organizer'),
        ('participant', 'Participant'),
    ]

    YEAR_CHOICES = [
        (1, '1st Year'),
        (2, '2nd Year'),
        (3, '3rd Year'),
        (4, '4th Year'),
        (5, '5th Year'),
    ]

    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
    ]

    phone = models.CharField(max_length=15, blank=True, default='')
    college_name = models.CharField(max_length=200, blank=True, default='')
    branch = models.CharField(max_length=100, blank=True, default='', help_text='Department or branch of study')
    year_of_study = models.PositiveSmallIntegerField(choices=YEAR_CHOICES, null=True, blank=True)
    bio = models.TextField(blank=True, default='')
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    github_url = models.URLField(max_length=500, blank=True, default='')
    linkedin_url = models.URLField(max_length=500, blank=True, default='')
    portfolio_url = models.URLField(max_length=500, blank=True, default='')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='participant')
    email_verified = models.BooleanField(default=False)
    theme_preference = models.CharField(max_length=10, choices=THEME_CHOICES, default='light')

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return self.get_full_name() or self.username

    def get_absolute_url(self):
        return reverse('users:profile', kwargs={'pk': self.pk})

    @property
    def is_organizer(self):
        return self.role in ('organizer', 'admin')

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def initials(self):
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        return self.username[:2].upper()

    @property
    def primary_skills(self):
        return self.tech_stacks.filter(is_primary=True)

    @property
    def secondary_skills(self):
        return self.tech_stacks.filter(is_primary=False)


class UserTechStack(models.Model):
    """Tech skills associated with a user profile."""

    PROFICIENCY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tech_stacks')
    tech_name = models.CharField(max_length=50)
    proficiency = models.CharField(max_length=20, choices=PROFICIENCY_CHOICES, default='intermediate')
    is_primary = models.BooleanField(default=False)

    class Meta:
        unique_together = ['user', 'tech_name']
        ordering = ['-is_primary', 'tech_name']

    def __str__(self):
        return f"{self.tech_name} ({self.get_proficiency_display()})"
