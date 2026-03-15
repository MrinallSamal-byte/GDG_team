"""
Certificate models.

One row per participant per event. Stores the certificate type,
generated PDF path, and a unique verification token.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class CertificateType(models.TextChoices):
    PARTICIPATION = "participation", _("Participation")
    MERIT = "merit", _("Merit")
    WINNER = "winner", _("Winner")


class Certificate(models.Model):
    id = models.BigAutoField(primary_key=True)
    registration = models.ForeignKey(
        "registration.Registration",
        on_delete=models.CASCADE,
        related_name="certificates",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="certificates",
    )
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="certificates",
    )
    cert_type = models.CharField(
        max_length=20,
        choices=CertificateType.choices,
        default=CertificateType.PARTICIPATION,
    )
    # UUID token used for public verification URL
    verification_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    pdf_file = models.FileField(upload_to="certificates/pdfs/", blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issued_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["registration", "cert_type"],
                name="uniq_cert_per_registration_type",
            )
        ]
        indexes = [
            models.Index(fields=["user", "-issued_at"], name="idx_cert_user"),
            models.Index(fields=["verification_token"], name="idx_cert_token"),
        ]

    def __str__(self):
        return f"{self.get_cert_type_display()} — {self.user} @ {self.event.title}"

    @property
    def verify_url(self):
        return f"/certificates/verify/{self.verification_token}/"
