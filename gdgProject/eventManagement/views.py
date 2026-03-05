"""
Event management views — create, edit, dashboard, settings, CSV export.
"""
import csv
import json

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from events.models import Event, EventCategory, EventMode, EventStatus, ParticipationType
from registration.models import Registration, RegistrationStatus


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date(value):
    """Parse a date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM) into a datetime."""
    from django.utils.dateparse import parse_datetime, parse_date
    from django.utils import timezone
    import datetime

    if not value:
        return None
    dt = parse_datetime(value)
    if dt:
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
    d = parse_date(value)
    if d:
        return timezone.make_aware(datetime.datetime.combine(d, datetime.time.min))
    return None


# ── Views ─────────────────────────────────────────────────────────────────────

@staff_member_required
def organizer_dashboard(request):
    # Events created by this user (staff see all)
    events_qs = (
        Event.objects
        .filter(created_by=request.user)
        .annotate(reg_count=Count("registrations"))
        .order_by("-created_at")
    )

    total_events = events_qs.count()
    total_regs = Registration.objects.filter(event__in=events_qs).count()
    confirmed_regs = Registration.objects.filter(
        event__in=events_qs, status=RegistrationStatus.CONFIRMED
    ).count()

    analytics = {
        "active_events": events_qs.filter(
            status__in=[
                EventStatus.REGISTRATION_OPEN,
                EventStatus.ONGOING,
                EventStatus.PUBLISHED,
            ]
        ).count(),
        "total_registrations": total_regs,
        "confirmed_registrations": confirmed_regs,
        "total_events": total_events,
    }

    recent_regs = (
        Registration.objects
        .filter(event__created_by=request.user)
        .select_related("user", "event", "team")
        .order_by("-registered_at")[:20]
    )
    participants = [
        {
            "name": r.user.get_full_name() or r.user.username,
            "event": r.event.title,
            "event_id": r.event.id,
            "status": r.get_status_display(),
            "team": r.team.name if r.team else None,
        }
        for r in recent_regs
    ]

    return render(request, "eventManagement/organizer_dashboard.html", {
        "analytics": analytics,
        "participants": participants,
        "events": events_qs,
    })


@staff_member_required
@require_http_methods(["GET", "POST"])
def create_event(request):
    categories = EventCategory.choices
    modes = EventMode.choices
    ptypes = ParticipationType.choices

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        category = request.POST.get("category", "").strip()
        mode = request.POST.get("mode", "").strip()
        description = request.POST.get("description", "").strip()
        venue = request.POST.get("venue", "").strip()
        platform_link = request.POST.get("platform_link", "").strip()
        registration_start = _parse_date(request.POST.get("registration_start", ""))
        registration_end = _parse_date(request.POST.get("registration_end", ""))
        event_start = _parse_date(request.POST.get("start_date", ""))
        event_end = _parse_date(request.POST.get("end_date", ""))
        capacity = request.POST.get("max_participants") or 100
        participation_type = request.POST.get("participation_type", "individual")
        min_team_size = request.POST.get("min_team_size") or 1
        max_team_size = request.POST.get("max_team_size") or 1
        prize_1st = request.POST.get("prize_1st", "").strip()
        prize_2nd = request.POST.get("prize_2nd", "").strip()
        prize_3rd = request.POST.get("prize_3rd", "").strip()
        eligibility = request.POST.get("eligibility", "").strip()
        rules = request.POST.get("rules", "").strip()
        cert = request.POST.get("certificates", "")

        errors = []
        if not title:
            errors.append("Event title is required.")
        if not category or category not in dict(EventCategory.choices):
            errors.append("Please select a valid category.")
        if not mode or mode not in dict(EventMode.choices):
            errors.append("Please select an event mode.")
        if not event_start:
            errors.append("Event start date is required.")
        if not event_end:
            errors.append("Event end date is required.")
        if event_start and event_end and event_end < event_start:
            errors.append("Event end must be on or after the start date.")
        if not registration_start:
            errors.append("Registration start date is required.")
        if not registration_end:
            errors.append("Registration end date is required.")
        if registration_start and registration_end and registration_end < registration_start:
            errors.append("Registration end must be on or after registration start.")
        if not description:
            errors.append("Event description is required.")

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, "eventManagement/create_event.html", {
                "form_data": request.POST,
                "categories": categories,
                "modes": modes,
                "ptypes": ptypes,
            })

        Event.objects.create(
            title=title,
            category=category,
            mode=mode,
            description=description,
            venue=venue,
            platform_link=platform_link,
            registration_start=registration_start,
            registration_end=registration_end,
            event_start=event_start,
            event_end=event_end,
            capacity=int(capacity),
            participation_type=participation_type,
            min_team_size=int(min_team_size),
            max_team_size=int(max_team_size),
            prize_1st=prize_1st,
            prize_2nd=prize_2nd,
            prize_3rd=prize_3rd,
            eligibility=eligibility or "Open to all",
            rules=rules,
            participation_certificate="participation" in cert.lower() or "both" in cert.lower(),
            merit_certificate="merit" in cert.lower() or "both" in cert.lower(),
            status=EventStatus.DRAFT,
            created_by=request.user,
        )

        messages.success(request, f'"{title}" created successfully! It is saved as Draft.')
        return redirect("eventManagement:organizer_dashboard")

    return render(request, "eventManagement/create_event.html", {
        "categories": categories,
        "modes": modes,
        "ptypes": ptypes,
    })


@staff_member_required
@require_http_methods(["GET", "POST"])
def edit_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id, created_by=request.user)
    categories = EventCategory.choices
    modes = EventMode.choices
    ptypes = ParticipationType.choices
    statuses = EventStatus.choices

    if request.method == "POST":
        event.title = request.POST.get("title", event.title).strip()
        event.category = request.POST.get("category", event.category)
        event.mode = request.POST.get("mode", event.mode)
        event.description = request.POST.get("description", event.description).strip()
        event.venue = request.POST.get("venue", event.venue).strip()
        event.eligibility = request.POST.get("eligibility", event.eligibility).strip()
        event.rules = request.POST.get("rules", event.rules).strip()
        event.prize_1st = request.POST.get("prize_1st", event.prize_1st).strip()
        event.prize_2nd = request.POST.get("prize_2nd", event.prize_2nd).strip()
        event.prize_3rd = request.POST.get("prize_3rd", event.prize_3rd).strip()
        cap = request.POST.get("max_participants")
        if cap:
            event.capacity = int(cap)
        new_status = request.POST.get("status", event.status)
        if new_status in dict(EventStatus.choices):
            event.status = new_status
        rs = _parse_date(request.POST.get("registration_start", ""))
        re = _parse_date(request.POST.get("registration_end", ""))
        es = _parse_date(request.POST.get("start_date", ""))
        ee = _parse_date(request.POST.get("end_date", ""))
        if rs:
            event.registration_start = rs
        if re:
            event.registration_end = re
        if es:
            event.event_start = es
        if ee:
            event.event_end = ee
        event.save()
        messages.success(request, f'"{event.title}" updated.')
        return redirect("eventManagement:organizer_dashboard")

    return render(request, "eventManagement/edit_event.html", {
        "event": event,
        "categories": categories,
        "modes": modes,
        "ptypes": ptypes,
        "statuses": statuses,
    })


@staff_member_required
@require_POST
def update_event_status(request, event_id):
    event = get_object_or_404(Event, pk=event_id, created_by=request.user)
    new_status = request.POST.get("status", "").strip()
    if new_status in dict(EventStatus.choices):
        event.status = new_status
        event.save(update_fields=["status", "updated_at"])
        messages.success(request, f'Status updated to "{event.get_status_display()}".')
    else:
        messages.error(request, "Invalid status.")
    return redirect("eventManagement:organizer_dashboard")


@staff_member_required
def export_participants_csv(request, event_id):
    event = get_object_or_404(Event, pk=event_id, created_by=request.user)
    regs = (
        Registration.objects
        .filter(event=event)
        .select_related("user", "team")
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="participants_{event.slug}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(["#", "Name", "Email", "Type", "Team", "Status", "Registered At"])
    for i, r in enumerate(regs, 1):
        writer.writerow([
            i,
            r.user.get_full_name() or r.user.username,
            r.user.email,
            r.get_type_display(),
            r.team.name if r.team else "",
            r.get_status_display(),
            r.registered_at.strftime("%Y-%m-%d %H:%M"),
        ])

    return response
