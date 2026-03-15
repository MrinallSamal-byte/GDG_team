import logging

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from events.models import Event
from registration.models import Registration, RegistrationStatus

from .models import CheckIn
from .qr import generate_qr_png

logger = logging.getLogger("campusarena.checkin")


def _wants_json(request) -> bool:
    """Return True if the client prefers a JSON response."""
    accept = request.META.get("HTTP_ACCEPT", "")
    return (
        "application/json" in accept
        or request.content_type == "application/json"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )


def _get_or_create_checkin(registration) -> CheckIn:
    checkin, _ = CheckIn.objects.get_or_create(
        registration=registration,
        defaults={"event": registration.event, "user": registration.user},
    )
    return checkin


@login_required
@require_GET
def my_qr_code(request, event_id):
    """Show the participant their own QR code for check-in."""
    event = get_object_or_404(Event, pk=event_id)
    registration = Registration.objects.filter(
        event=event,
        user=request.user,
        status__in=[RegistrationStatus.CONFIRMED, RegistrationStatus.SUBMITTED],
    ).first()

    if not registration:
        messages.error(request, "You are not registered for this event.")
        return redirect("events:event_detail", event_id=event.pk)

    checkin = _get_or_create_checkin(registration)
    scan_url = request.build_absolute_uri(f"/checkin/scan/{checkin.token}/")

    return render(
        request,
        "checkin/my_qr.html",
        {
            "event": event,
            "registration": registration,
            "checkin": checkin,
            "scan_url": scan_url,
        },
    )


@login_required
@require_GET
def qr_image(request, event_id):
    """Serve the participant's QR code as a raw PNG (used by <img> tags)."""
    event = get_object_or_404(Event, pk=event_id)
    registration = Registration.objects.filter(
        event=event,
        user=request.user,
        status__in=[RegistrationStatus.CONFIRMED, RegistrationStatus.SUBMITTED],
    ).first()

    if not registration:
        return HttpResponse(status=404)

    checkin = _get_or_create_checkin(registration)
    scan_url = request.build_absolute_uri(f"/checkin/scan/{checkin.token}/")

    try:
        png_bytes = generate_qr_png(scan_url)
    except RuntimeError as exc:
        logger.error("QR generation failed: %s", exc)
        return HttpResponse(status=503)

    return HttpResponse(png_bytes, content_type="image/png")


@staff_member_required
@require_GET
def scan_qr(request, token):
    """
    Organiser scans a participant QR code.
    Returns HTML for browser, JSON for mobile scanner apps.
    """
    checkin = (
        CheckIn.objects.filter(token=token)
        .select_related("user", "user__profile", "event", "registration")
        .first()
    )

    if not checkin:
        if _wants_json(request):
            return JsonResponse({"ok": False, "error": "Invalid QR code."}, status=404)
        return render(request, "checkin/scan_result.html", {"valid": False})

    if checkin.event.created_by != request.user and not request.user.is_superuser:
        if _wants_json(request):
            return JsonResponse({"ok": False, "error": "Permission denied."}, status=403)
        messages.error(request, "You are not the organiser of this event.")
        return redirect("eventManagement:organizer_dashboard")

    if _wants_json(request):
        return JsonResponse({
            "ok": True,
            "already_checked_in": checkin.checked_in,
            "name": checkin.user.get_full_name() or checkin.user.username,
            "registration_id": checkin.registration.registration_id,
            "event": checkin.event.title,
            "checked_in_at": checkin.checked_in_at.isoformat() if checkin.checked_in_at else None,
        })

    return render(
        request,
        "checkin/scan_result.html",
        {
            "valid": True,
            "checkin": checkin,
            "already_checked_in": checkin.checked_in,
        },
    )


@staff_member_required
@require_POST
def confirm_checkin(request, token):
    """Mark a participant as checked in. Accepts both browser forms and JSON/AJAX."""
    checkin = get_object_or_404(
        CheckIn.objects.select_related("event", "user"),
        token=token,
    )

    if checkin.event.created_by != request.user and not request.user.is_superuser:
        if _wants_json(request):
            return JsonResponse({"ok": False, "error": "Permission denied."}, status=403)
        messages.error(request, "Permission denied.")
        return redirect("eventManagement:organizer_dashboard")

    if checkin.checked_in:
        name = checkin.user.get_full_name() or checkin.user.username
        if _wants_json(request):
            return JsonResponse({"ok": False, "error": f"{name} is already checked in."}, status=409)
        messages.warning(request, f"{name} was already checked in.")
        return redirect("checkin:dashboard", event_id=checkin.event.pk)

    checkin.checked_in = True
    checkin.checked_in_at = timezone.now()
    checkin.checked_in_by = request.user
    checkin.save(update_fields=["checked_in", "checked_in_at", "checked_in_by"])

    name = checkin.user.get_full_name() or checkin.user.username
    logger.info(
        "Check-in confirmed: user=%d event=%d by organiser=%d",
        checkin.user.pk,
        checkin.event.pk,
        request.user.pk,
    )

    if _wants_json(request):
        return JsonResponse({
            "ok": True,
            "name": name,
            "checked_in_at": checkin.checked_in_at.isoformat(),
        })

    messages.success(request, f"{name} checked in successfully.")
    return redirect("checkin:dashboard", event_id=checkin.event.pk)


@staff_member_required
@require_GET
def checkin_dashboard(request, event_id):
    """Organiser dashboard — shows check-in progress for an event."""
    event = get_object_or_404(
        Event.all_objects,
        pk=event_id,
        created_by=request.user,
    )

    checkins = (
        CheckIn.objects.filter(event=event)
        .select_related("user", "user__profile", "registration", "checked_in_by")
        .order_by("-checked_in_at", "user__first_name")
    )

    total = checkins.count()
    checked = checkins.filter(checked_in=True).count()
    pending = total - checked

    return render(
        request,
        "checkin/dashboard.html",
        {
            "event": event,
            "checkins": checkins,
            "total": total,
            "checked": checked,
            "pending": pending,
            "percent": round((checked / total * 100) if total else 0),
        },
    )


@staff_member_required
@require_POST
def bulk_generate_qr(request, event_id):
    """
    Idempotently create CheckIn records for all confirmed registrations.
    Safe to call multiple times.
    """
    event = get_object_or_404(Event.all_objects, pk=event_id, created_by=request.user)

    # Registrations that don't yet have a check-in record
    registrations = Registration.objects.filter(
        event=event,
        status__in=[RegistrationStatus.CONFIRMED, RegistrationStatus.SUBMITTED],
    ).exclude(checkin__isnull=False)

    created = 0
    for reg in registrations:
        CheckIn.objects.get_or_create(
            registration=reg,
            defaults={"event": event, "user": reg.user},
        )
        created += 1

    messages.success(request, f"Generated QR codes for {created} new registrant(s).")
    return redirect("checkin:dashboard", event_id=event.pk)
