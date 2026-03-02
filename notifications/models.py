from django.db import models
from django.conf import settings


class Notification(models.Model):
    """In-app notification for user activities."""

    TYPE_CHOICES = [
        ('join_request', 'Join Request'),
        ('request_approved', 'Request Approved'),
        ('request_declined', 'Request Declined'),
        ('new_message', 'New Message'),
        ('announcement', 'Announcement'),
        ('registration', 'Registration'),
        ('reminder', 'Event Reminder'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    reference_type = models.CharField(max_length=50, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} → {self.user.display_name}"

    @classmethod
    def create_notification(cls, user, title, message, notification_type, reference_id=None, reference_type=''):
        return cls.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            reference_id=reference_id,
            reference_type=reference_type,
        )
