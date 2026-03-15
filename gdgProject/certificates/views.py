import logging

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .generator import generate_certificate_pdf
from .models import Certificate, CertificateType

logger = logging.getLogger("campusarena.certificates")


@login_required
@require_GET
def my_certificates(request):
    """List all certificates for the current user."""
    certs = (
        Certificate.objects.filter(user=request.user)
        .select_related("event")
        .order_by("-issued_at")
    )
    return render(request, "certificates/my_certificates.html", {"certificates": certs})


@login_required
@require_GET
def download_certificate(request, certificate_id):
    """Generate on first download (cached to disk), then stream as PDF."""
    cert = get_object_or_404(
        Certificate.objects.select_related("event", "user"),
        pk=certificate_id,
        user=request.user,
    )

    if not cert.pdf_file:
        try:
            pdf_bytes = generate_certificate_pdf(cert)
            filename = f"certificate_{cert.verification_token}.pdf"
            cert.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
        except RuntimeError as exc:
            logger.error("PDF generation failed for cert %d: %s", cert.pk, exc)
            from django.contrib import messages

            messages.error(request, "Certificate generation is currently unavailable.")
            return redirect("certificates:my_certificates")

    return FileResponse(
        cert.pdf_file.open("rb"),
        as_attachment=True,
        filename=f"certificate_{cert.event.slug or cert.event.pk}.pdf",
        content_type="application/pdf",
    )


@require_GET
def verify_certificate(request, token):
    """Public verification page — no login required."""
    cert = (
        Certificate.objects.filter(verification_token=token)
        .select_related("event", "user")
        .first()
    )
    if not cert:
        return render(request, "certificates/verify.html", {"valid": False})
    return render(request, "certificates/verify.html", {"valid": True, "certificate": cert})


@login_required
@require_POST
def issue_certificate(request, registration_id):
    """
    Organiser issues a participation certificate to one registrant.
    Safe to call multiple times — idempotent via get_or_create.
    """
    from django.contrib import messages
    from registration.models import Registration

    reg = get_object_or_404(
        Registration.objects.select_related("event", "user"),
        pk=registration_id,
    )

    if reg.event.created_by != request.user and not request.user.is_superuser:
        messages.error(request, "Permission denied.")
        return redirect("eventManagement:organizer_dashboard")

    cert, created = Certificate.objects.get_or_create(
        registration=reg,
        cert_type=CertificateType.PARTICIPATION,
        defaults={
            "user": reg.user,
            "event": reg.event,
        },
    )

    if created:
        logger.info(
            "Certificate issued: cert=%d user=%d event=%d",
            cert.pk,
            reg.user.pk,
            reg.event.pk,
        )

    messages.success(
        request,
        f"Certificate issued to {reg.user.get_full_name() or reg.user.username}.",
    )
    return redirect("eventManagement:organizer_dashboard")
