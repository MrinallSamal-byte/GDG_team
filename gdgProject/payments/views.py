"""
Razorpay payment views for CampusArena.

Flow:
  1. GET  /payments/initiate/<reg_id>/  → create Razorpay order, render checkout
  2. POST /payments/callback/           → verify HMAC signature, confirm registration
  3. GET  /payments/success/<reg_id>/   → success confirmation page
  4. GET  /payments/failed/<reg_id>/    → failure page with retry link
"""

import hashlib
import hmac
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from registration.models import Registration, RegistrationStatus

from .models import Payment, PaymentStatus

logger = logging.getLogger("campusarena.payments")


def _razorpay_client():
    import razorpay

    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@login_required
@require_GET
def initiate_payment(request, registration_id):
    """Create a Razorpay order and render the payment checkout page."""
    registration = get_object_or_404(
        Registration.objects.select_related("event", "user"),
        pk=registration_id,
        user=request.user,
    )

    # Already paid — skip straight to success
    if Payment.objects.filter(registration=registration, status=PaymentStatus.COMPLETED).exists():
        return redirect("payments:success", registration_id=registration.pk)

    # Free event — skip payment
    if not registration.event.registration_fee or registration.event.registration_fee <= 0:
        return redirect("registration:confirmation", registration_id=registration.pk)

    amount_paise = int(registration.event.registration_fee * 100)

    try:
        client = _razorpay_client()
        order = client.order.create(
            {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": registration.registration_id,
                "payment_capture": 1,
            }
        )
    except Exception:
        logger.error("Razorpay order creation failed", exc_info=True)
        messages.error(request, "Payment gateway is unavailable right now. Please try again.")
        return redirect("events:event_detail", event_id=registration.event.pk)

    payment, _ = Payment.objects.get_or_create(
        registration=registration,
        defaults={
            "user": request.user,
            "amount": registration.event.registration_fee,
            "razorpay_order_id": order["id"],
        },
    )
    # Refresh order_id if a new Razorpay order was created for an existing Payment row
    if payment.razorpay_order_id != order["id"]:
        payment.razorpay_order_id = order["id"]
        payment.save(update_fields=["razorpay_order_id", "updated_at"])

    return render(
        request,
        "payments/checkout.html",
        {
            "registration": registration,
            "payment": payment,
            "razorpay_order_id": order["id"],
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "amount_paise": amount_paise,
            "amount_display": registration.event.registration_fee,
            "event": registration.event,
        },
    )


@csrf_exempt
@require_POST
def payment_callback(request):
    """
    Razorpay POSTs here after the checkout modal completes.
    Verifies HMAC-SHA256 signature before confirming the registration.
    """
    razorpay_order_id = request.POST.get("razorpay_order_id", "")
    razorpay_payment_id = request.POST.get("razorpay_payment_id", "")
    razorpay_signature = request.POST.get("razorpay_signature", "")

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return HttpResponseBadRequest("Missing payment data.")

    payment = Payment.objects.filter(razorpay_order_id=razorpay_order_id).first()
    if not payment:
        logger.warning("Callback received for unknown Razorpay order: %s", razorpay_order_id)
        return HttpResponseBadRequest("Unknown order.")

    # HMAC-SHA256 signature verification
    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected_sig = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        msg,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, razorpay_signature):
        payment.status = PaymentStatus.FAILED
        payment.save(update_fields=["status", "updated_at"])
        logger.warning("Razorpay signature mismatch for order %s", razorpay_order_id)
        return redirect("payments:failed", registration_id=payment.registration_id)

    # Signature valid — mark payment and registration as confirmed
    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = razorpay_signature
    payment.status = PaymentStatus.COMPLETED
    payment.save(update_fields=["razorpay_payment_id", "razorpay_signature", "status", "updated_at"])

    registration = payment.registration
    if registration.status != RegistrationStatus.CONFIRMED:
        registration.status = RegistrationStatus.CONFIRMED
        registration.save(update_fields=["status", "updated_at"])

    logger.info(
        "Payment completed: order=%s payment=%s registration=%s",
        razorpay_order_id,
        razorpay_payment_id,
        registration.registration_id,
    )

    from registration.views import _send_confirmation_email

    _send_confirmation_email(registration)

    return redirect("payments:success", registration_id=registration.pk)


@login_required
@require_GET
def payment_success(request, registration_id):
    registration = get_object_or_404(
        Registration.objects.select_related("event"),
        pk=registration_id,
        user=request.user,
    )
    return render(request, "payments/success.html", {"registration": registration})


@login_required
@require_GET
def payment_failed(request, registration_id):
    registration = get_object_or_404(
        Registration.objects.select_related("event"),
        pk=registration_id,
        user=request.user,
    )
    return render(request, "payments/failed.html", {"registration": registration})
