from django.db import models
from django.conf import settings


class Team(models.Model):
    """Team for team-based event participation."""

    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='teams')
    team_name = models.CharField(max_length=100)
    leader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='led_teams')
    max_members = models.PositiveIntegerField(default=4)
    is_open = models.BooleanField(default=True, help_text='Accepting new join requests?')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['event', 'team_name']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.team_name} ({self.event.title})"

    @property
    def member_count(self):
        return self.members.count()

    @property
    def spots_remaining(self):
        return max(0, self.max_members - self.member_count)

    @property
    def is_full(self):
        return self.member_count >= self.max_members

    @property
    def tech_stacks_covered(self):
        """Return set of tech stacks covered by current members."""
        from registrations.models import RegistrationTechStack
        member_user_ids = self.members.values_list('user_id', flat=True)
        reg_ids = self.registrations.filter(user_id__in=member_user_ids).values_list('id', flat=True)
        return list(RegistrationTechStack.objects.filter(
            registration_id__in=reg_ids
        ).values_list('tech_name', flat=True).distinct())

    def auto_close_if_full(self):
        if self.is_full and self.is_open:
            self.is_open = False
            self.save(update_fields=['is_open'])


class TeamMember(models.Model):
    """Individual member within a team."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='team_memberships')
    role_in_team = models.CharField(max_length=50, blank=True, default='')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['team', 'user']

    def __str__(self):
        return f"{self.user.display_name} in {self.team.team_name}"


class TeamJoinRequest(models.Model):
    """Request from a user to join a team."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='join_requests')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='join_requests')
    message = models.TextField(blank=True, default='', help_text='Introduction message')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['team', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.display_name} → {self.team.team_name} ({self.status})"


class Message(models.Model):
    """In-team chat message."""

    TYPE_CHOICES = [
        ('text', 'Text'),
        ('system', 'System Message'),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    message_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='text')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.display_name}: {self.content[:40]}"
