import logging
from collections.abc import Sequence
from dataclasses import dataclass

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailDeliveryResult:
    sent: bool
    error_message: str | None = None


def _smtp_backend_is_active() -> bool:
    return getattr(settings, "EMAIL_BACKEND", "").endswith("smtp.EmailBackend")


def _effective_from_email() -> str:
    default_from = str(getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip()
    host_user = str(getattr(settings, "EMAIL_HOST_USER", "") or "").strip()
    return default_from or host_user


def _validate_email_settings() -> EmailDeliveryResult | None:
    if not _smtp_backend_is_active():
        return None

    missing = []
    if not str(getattr(settings, "EMAIL_HOST", "") or "").strip():
        missing.append("EMAIL_HOST")
    if not str(getattr(settings, "EMAIL_PORT", "") or "").strip():
        missing.append("EMAIL_PORT")
    if not str(getattr(settings, "EMAIL_HOST_USER", "") or "").strip():
        missing.append("EMAIL_HOST_USER")
    if not str(getattr(settings, "EMAIL_HOST_PASSWORD", "") or "").strip():
        missing.append("EMAIL_HOST_PASSWORD")
    if not _effective_from_email():
        missing.append("DEFAULT_FROM_EMAIL")

    if not missing:
        return None

    logger.error("Email delivery is not configured. Missing settings: %s", missing)
    return EmailDeliveryResult(
        sent=False,
        error_message="Email delivery is not configured on the server yet.",
    )


def send_plaintext_email(
    *,
    subject: str,
    body: str,
    recipients: Sequence[str],
    log_context: str,
) -> EmailDeliveryResult:
    normalized_recipients = [recipient.strip() for recipient in recipients if recipient]
    if not normalized_recipients:
        logger.error("Email delivery skipped due to missing recipient. context=%s", log_context)
        return EmailDeliveryResult(
            sent=False,
            error_message="We couldn't find a valid recipient email address.",
        )

    config_error = _validate_email_settings()
    if config_error is not None:
        return config_error

    from_email = _effective_from_email()
    if not from_email:
        logger.error(
            "Email delivery is missing a sender address. context=%s",
            log_context,
        )
        return EmailDeliveryResult(
            sent=False,
            error_message="Email delivery is not configured on the server yet.",
        )

    try:
        connection = get_connection(fail_silently=False)
        message = EmailMultiAlternatives(
            subject=subject.strip(),
            body=body,
            from_email=from_email,
            to=normalized_recipients,
            connection=connection,
        )
        sent_messages = message.send(fail_silently=False)
    except Exception:
        logger.exception("Email delivery failed. context=%s", log_context)
        return EmailDeliveryResult(
            sent=False,
            error_message="We couldn't send the email right now. Please try again.",
        )

    if sent_messages < 1:
        logger.error(
            "Email backend reported zero delivered messages. context=%s",
            log_context,
        )
        return EmailDeliveryResult(
            sent=False,
            error_message="We couldn't send the email right now. Please try again.",
        )

    logger.info(
        "Email delivered successfully. context=%s recipients=%d",
        log_context,
        len(normalized_recipients),
    )
    return EmailDeliveryResult(sent=True)
