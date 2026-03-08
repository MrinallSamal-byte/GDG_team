from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Extended profile data for CampusArena users."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    phone = models.CharField(max_length=20, blank=True, default='')
    college = models.CharField(max_length=200, blank=True, default='')
    branch = models.CharField(max_length=100, blank=True, default='')
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True, default='')
    github = models.URLField(blank=True, default='')
    linkedin = models.URLField(blank=True, default='')
    skills = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Comma-separated list of skills',
    )
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} — Profile'

    @property
    def skills_list(self):
        """Return skills as a list."""
        if not self.skills:
            return []
        return [s.strip() for s in self.skills.split(',') if s.strip()]

    @property
    def year_display(self):
        """Return year as ordinal string."""
        if not self.year:
            return ''
        suffixes = {1: 'st', 2: 'nd', 3: 'rd'}
        suffix = suffixes.get(self.year, 'th')
        return f'{self.year}{suffix} Year'
