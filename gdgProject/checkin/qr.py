"""
QR code generation utility for check-in tokens.

Generates a PNG QR code image as bytes.
Requires: qrcode[pil]
"""

import io
import logging

logger = logging.getLogger("campusarena.checkin")


def generate_qr_png(data: str) -> bytes:
    """Return raw PNG bytes for a QR code encoding *data*."""
    try:
        import qrcode
        from qrcode.image.pil import PilImage
    except ImportError:
        raise RuntimeError(
            "qrcode[pil] is required for QR generation. "
            "Install with: pip install 'qrcode[pil]'"
        )

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
