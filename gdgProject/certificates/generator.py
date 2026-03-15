"""
Certificate generation service.

Uses ReportLab to generate PDF certificates entirely in Python —
no external template files needed. The design is a clean A4 landscape
certificate with event name, participant name, date, and a QR code
that links to the public verification URL.
"""

import io
import logging

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("campusarena.certificates")


def generate_certificate_pdf(certificate) -> bytes:
    """
    Generate a PDF for the given Certificate instance.
    Returns raw PDF bytes.

    Requires: reportlab, qrcode[pil]
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
    except ImportError:
        raise RuntimeError(
            "reportlab is required for PDF generation. "
            "Install it with: pip install reportlab"
        )

    try:
        import qrcode
        from PIL import Image as PILImage
    except ImportError:
        qrcode = None

    page_width, page_height = landscape(A4)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A4))

    # ── Background ───────────────────────────────────────────────────────────
    c.setFillColorRGB(0.98, 0.98, 0.96)
    c.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    # ── Decorative border ────────────────────────────────────────────────────
    c.setStrokeColorRGB(0.33, 0.29, 0.72)  # purple-600
    c.setLineWidth(4)
    margin = 20
    c.rect(margin, margin, page_width - 2 * margin, page_height - 2 * margin, fill=0)
    c.setLineWidth(1.5)
    c.rect(margin + 6, margin + 6, page_width - 2 * (margin + 6), page_height - 2 * (margin + 6), fill=0)

    # ── Header — platform name ────────────────────────────────────────────────
    c.setFillColorRGB(0.33, 0.29, 0.72)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(page_width / 2, page_height - 60, "CampusArena")

    # ── Title ────────────────────────────────────────────────────────────────
    cert_label = {
        "participation": "Certificate of Participation",
        "merit": "Certificate of Merit",
        "winner": "Certificate of Achievement",
    }.get(certificate.cert_type, "Certificate")

    c.setFillColorRGB(0.15, 0.15, 0.15)
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(page_width / 2, page_height - 120, cert_label)

    # ── "This certifies that" ─────────────────────────────────────────────────
    c.setFont("Helvetica", 14)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawCentredString(page_width / 2, page_height - 165, "This is to certify that")

    # ── Participant name ──────────────────────────────────────────────────────
    full_name = certificate.user.get_full_name() or certificate.user.username
    c.setFont("Helvetica-Bold", 28)
    c.setFillColorRGB(0.33, 0.29, 0.72)
    c.drawCentredString(page_width / 2, page_height - 220, full_name)

    # ── Underline beneath name ───────────────────────────────────────────────
    c.setStrokeColorRGB(0.33, 0.29, 0.72)
    c.setLineWidth(0.5)
    name_width = len(full_name) * 16
    c.line(
        page_width / 2 - name_width / 2, page_height - 230,
        page_width / 2 + name_width / 2, page_height - 230,
    )

    # ── Event participation text ──────────────────────────────────────────────
    c.setFont("Helvetica", 14)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    participation_text = {
        "participation": "has successfully participated in",
        "merit": "has demonstrated exceptional merit in",
        "winner": "has won an award at",
    }.get(certificate.cert_type, "has participated in")
    c.drawCentredString(page_width / 2, page_height - 265, participation_text)

    # ── Event name ────────────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 20)
    c.setFillColorRGB(0.15, 0.15, 0.15)
    c.drawCentredString(page_width / 2, page_height - 305, certificate.event.title)

    # ── Event date ────────────────────────────────────────────────────────────
    event_date = certificate.event.event_start.strftime("%B %d, %Y")
    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(page_width / 2, page_height - 335, f"Held on {event_date}")

    # ── Issue date ────────────────────────────────────────────────────────────
    issue_date = certificate.issued_at.strftime("%B %d, %Y")
    c.drawCentredString(page_width / 2, page_height - 360, f"Issued: {issue_date}")

    # ── QR Code ───────────────────────────────────────────────────────────────
    if qrcode:
        try:
            verify_url = f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://campusarena.dev'}{certificate.verify_url}"
            qr = qrcode.make(verify_url)
            qr_buf = io.BytesIO()
            qr.save(qr_buf, format="PNG")
            qr_buf.seek(0)
            from reportlab.lib.utils import ImageReader
            qr_img = ImageReader(qr_buf)
            c.drawImage(qr_img, page_width - 130, 40, width=90, height=90)
            c.setFont("Helvetica", 8)
            c.setFillColorRGB(0.6, 0.6, 0.6)
            c.drawCentredString(page_width - 85, 35, "Verify certificate")
        except Exception as exc:
            logger.warning("QR code generation failed: %s", exc)

    # ── Verification ID ───────────────────────────────────────────────────────
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.7, 0.7, 0.7)
    c.drawString(40, 40, f"Certificate ID: {certificate.verification_token}")

    c.save()
    return buf.getvalue()
