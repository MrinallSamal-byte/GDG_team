import logging
import textwrap
from datetime import timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_http_methods, require_POST
from events.models import (
    Event,
    EventAnnouncement,
    EventCategory,
    EventJudge,
    EventMode,
    EventRound,
    EventSponsor,
    EventStatus,
    ParticipationType,
)

logger = logging.getLogger(__name__)


def _aware(dt):
    if dt is None:
        return dt
    from django.utils.timezone import is_naive, make_aware
    return make_aware(dt) if is_naive(dt) else dt


@staff_member_required
def organizer_dashboard(request):
    my_events = (
        Event.all_objects.filter(created_by=request.user)
        .annotate(
            registration_count=Count(
                "registrations",
                filter=Q(registrations__status__in=["confirmed", "submitted"]),
            )
        )
        .order_by("-created_at")
    )

    total_registrations = sum(e.registration_count for e in my_events)
    active_events = my_events.filter(
        status__in=[
            EventStatus.PUBLISHED,
            EventStatus.REGISTRATION_OPEN,
            EventStatus.ONGOING,
        ],
        is_deleted=False,
    ).count()

    return render(
        request,
        "eventManagement/organizer_dashboard.html",
        {
            "analytics": {
                "total_registrations": total_registrations,
                "active_events": active_events,
            },
            "my_events": my_events,
        },
    )


@staff_member_required
@require_http_methods(["GET", "POST"])
def create_event(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        category = request.POST.get("category", "").strip()
        mode = request.POST.get("mode", "").strip()
        start_date = request.POST.get("start_date", "").strip()
        end_date = request.POST.get("end_date", "").strip()
        reg_start = request.POST.get("reg_start_date", "").strip()
        reg_end = request.POST.get("reg_end_date", "").strip()
        description = request.POST.get("description", "").strip()
        venue = request.POST.get("venue", "").strip()
        participation_type = request.POST.get("participation_type", "individual").strip()
        max_participants = request.POST.get("max_participants", "100").strip()
        min_team_size = request.POST.get("min_team_size", "1").strip()
        max_team_size = request.POST.get("max_team_size", "1").strip()
        registration_fee = request.POST.get("registration_fee", "0").strip()
        rules = request.POST.get("rules", "").strip()
        faqs_raw = request.POST.get("faqs", "").strip()
        prize_1st = request.POST.get("prize_1st", "").strip()
        prize_2nd = request.POST.get("prize_2nd", "").strip()
        prize_3rd = request.POST.get("prize_3rd", "").strip()
        certificates = request.POST.get("certificates", "").strip()
        judges_raw = request.POST.get("judges", "").strip()
        sponsors_raw = request.POST.get("sponsors", "").strip()

        errors = []
        if not title:
            errors.append("Event title is required.")
        if category not in EventCategory.values:
            errors.append("Please select a valid category.")
        if mode not in EventMode.values:
            errors.append("Please select a valid event mode.")
        if not start_date:
            errors.append("Start date is required.")
        if not end_date:
            errors.append("End date is required.")
        if not description:
            errors.append("Event description is required.")

        event_start = _aware(parse_datetime(start_date)) if start_date else None
        event_end = _aware(parse_datetime(end_date)) if end_date else None
        reg_start_dt = _aware(parse_datetime(reg_start)) if reg_start else event_start
        reg_end_dt = _aware(parse_datetime(reg_end)) if reg_end else event_end

        if event_start and event_end and event_start > event_end:
            errors.append("End date must be on or after the start date.")

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(
                request,
                "eventManagement/create_event.html",
                {"form_data": request.POST},
            )

        try:
            capacity = int(max_participants) if max_participants else 100
        except ValueError:
            capacity = 100
        try:
            min_ts = int(min_team_size) if min_team_size else 1
        except ValueError:
            min_ts = 1
        try:
            max_ts = int(max_team_size) if max_team_size else 1
        except ValueError:
            max_ts = 1
        try:
            fee = float(registration_fee) if registration_fee else 0
        except ValueError:
            fee = 0

        faqs = []
        if faqs_raw:
            for line in faqs_raw.split("\n"):
                line = line.strip()
                if line:
                    faqs.append({"q": line, "a": ""})

        participation_cert = certificates in ("participation", "both")
        merit_cert = certificates in ("merit", "both")

        event = Event.objects.create(
            title=title,
            description=description,
            category=category,
            mode=mode,
            participation_type=(
                participation_type
                if participation_type in ParticipationType.values
                else "individual"
            ),
            status=EventStatus.DRAFT,
            event_start=event_start,
            event_end=event_end,
            registration_start=reg_start_dt,
            registration_end=reg_end_dt,
            venue=venue,
            capacity=max(1, capacity),
            min_team_size=max(1, min_ts),
            max_team_size=max(1, max_ts),
            registration_fee=max(0, fee),
            prize_pool=max(0, float(request.POST.get("prize_pool", "0") or "0")),
            rules=rules,
            faqs=faqs,
            prize_1st=prize_1st,
            prize_2nd=prize_2nd,
            prize_3rd=prize_3rd,
            participation_certificate=participation_cert,
            merit_certificate=merit_cert,
            created_by=request.user,
        )

        banner = request.FILES.get("banner_image")
        if banner:
            event.banner = banner
            event.save(update_fields=["banner"])

        # ── Create rounds (BUG FIX: each round now gets its own end_date) ──
        round_names = request.POST.getlist("round_name[]")
        round_start_dates = request.POST.getlist("round_start_date[]")
        round_end_dates = request.POST.getlist("round_end_date[]")
        round_descs = request.POST.getlist("round_desc[]")
        for i, rname in enumerate(round_names):
            rname = rname.strip()
            if not rname:
                continue
            rstart_raw = round_start_dates[i].strip() if i < len(round_start_dates) else ""
            rend_raw = round_end_dates[i].strip() if i < len(round_end_dates) else ""
            rdesc = round_descs[i].strip() if i < len(round_descs) else ""

            rd_start = _aware(parse_datetime(rstart_raw)) if rstart_raw else event_start
            # FIX: use the round's own end date; default to rd_start + 1 day
            rd_end = _aware(parse_datetime(rend_raw)) if rend_raw else (
                rd_start + timedelta(days=1) if rd_start else event_end
            )

            EventRound.objects.create(
                event=event,
                name=rname,
                description=rdesc,
                order=i + 1,
                start_date=rd_start or event_start,
                end_date=rd_end or event_end,
            )

        if judges_raw:
            for name in judges_raw.split(","):
                name = name.strip()
                if name:
                    EventJudge.objects.create(event=event, name=name)

        if sponsors_raw:
            for name in sponsors_raw.split(","):
                name = name.strip()
                if name:
                    EventSponsor.objects.create(event=event, name=name)

        logger.info("Event created: %s (id=%d) by user %s", title, event.pk, request.user.pk)
        messages.success(request, f'"{title}" has been created successfully!')
        return redirect("eventManagement:organizer_dashboard")

    return render(
        request,
        "eventManagement/create_event.html",
        {
            "categories": EventCategory.choices,
            "modes": EventMode.choices,
            "participation_types": ParticipationType.choices,
        },
    )


_VALID_TRANSITIONS = {
    EventStatus.DRAFT: {EventStatus.PUBLISHED, EventStatus.CANCELLED},
    EventStatus.PUBLISHED: {
        EventStatus.REGISTRATION_OPEN,
        EventStatus.DRAFT,
        EventStatus.CANCELLED,
    },
    EventStatus.REGISTRATION_OPEN: {
        EventStatus.REGISTRATION_CLOSED,
        EventStatus.CANCELLED,
    },
    EventStatus.REGISTRATION_CLOSED: {
        EventStatus.ONGOING,
        EventStatus.REGISTRATION_OPEN,
        EventStatus.CANCELLED,
    },
    EventStatus.ONGOING: {EventStatus.COMPLETED, EventStatus.CANCELLED},
    EventStatus.COMPLETED: set(),
    EventStatus.CANCELLED: set(),
    EventStatus.ARCHIVED: set(),
}


@staff_member_required
@require_http_methods(["GET", "POST"])
def edit_event(request, event_id):
    event = Event.all_objects.filter(pk=event_id).first()
    if event is None:
        messages.error(request, "Event not found.")
        return redirect("eventManagement:organizer_dashboard")

    if event.created_by != request.user and not request.user.is_superuser:
        messages.error(request, "You can only edit your own events.")
        return redirect("eventManagement:organizer_dashboard")

    if event.status in (EventStatus.ONGOING, EventStatus.COMPLETED, EventStatus.CANCELLED):
        messages.warning(request, "This event cannot be edited in its current status.")
        return redirect("eventManagement:organizer_dashboard")

    if request.method == "GET":
        return render(
            request,
            "eventManagement/edit_event.html",
            {
                "event": event,
                "categories": EventCategory.choices,
                "modes": EventMode.choices,
                "participation_types": ParticipationType.choices,
            },
        )

    title = request.POST.get("title", "").strip()
    description = request.POST.get("description", "").strip()
    category = request.POST.get("category", "").strip()
    mode = request.POST.get("mode", "").strip()
    venue = request.POST.get("venue", "").strip()
    start_date = request.POST.get("start_date", "").strip()
    end_date = request.POST.get("end_date", "").strip()
    reg_start = request.POST.get("reg_start_date", "").strip()
    reg_end = request.POST.get("reg_end_date", "").strip()
    max_participants = request.POST.get("max_participants", "").strip()
    registration_fee = request.POST.get("registration_fee", "").strip()
    rules = request.POST.get("rules", "").strip()
    prize_1st = request.POST.get("prize_1st", "").strip()
    prize_2nd = request.POST.get("prize_2nd", "").strip()
    prize_3rd = request.POST.get("prize_3rd", "").strip()
    certificates = request.POST.get("certificates", "").strip()
    contact_info = request.POST.get("contact_info", "").strip()

    errors = []
    if not title:
        errors.append("Event title is required.")
    if category and category not in EventCategory.values:
        errors.append("Please select a valid category.")
    if mode and mode not in EventMode.values:
        errors.append("Please select a valid event mode.")

    event_start = _aware(parse_datetime(start_date)) if start_date else event.event_start
    event_end = _aware(parse_datetime(end_date)) if end_date else event.event_end
    reg_start_dt = _aware(parse_datetime(reg_start)) if reg_start else event.registration_start
    reg_end_dt = _aware(parse_datetime(reg_end)) if reg_end else event.registration_end

    if event_start and event_end and event_start > event_end:
        errors.append("Event end date must be on or after the start date.")
    if reg_start_dt and reg_end_dt and reg_start_dt > reg_end_dt:
        errors.append("Registration end date must be on or after the registration start date.")
    if reg_end_dt and event_start and reg_end_dt > event_start:
        errors.append("Registration must close before the event starts.")

    if errors:
        for err in errors:
            messages.error(request, err)
        return render(
            request,
            "eventManagement/edit_event.html",
            {
                "event": event,
                "categories": EventCategory.choices,
                "modes": EventMode.choices,
                "participation_types": ParticipationType.choices,
            },
        )

    event.title = title or event.title
    event.description = description or event.description
    if category and category in EventCategory.values:
        event.category = category
    if mode and mode in EventMode.values:
        event.mode = mode
    event.venue = venue
    event.event_start = event_start
    event.event_end = event_end
    event.registration_start = reg_start_dt
    event.registration_end = reg_end_dt
    event.rules = rules
    event.prize_1st = prize_1st
    event.prize_2nd = prize_2nd
    event.prize_3rd = prize_3rd
    event.participation_certificate = certificates in ("participation", "both")
    event.merit_certificate = certificates in ("merit", "both")
    event.contact_info = contact_info

    if max_participants:
        try:
            event.capacity = max(1, int(max_participants))
        except ValueError:
            pass
    if registration_fee:
        try:
            event.registration_fee = max(0, float(registration_fee))
        except ValueError:
            pass

    banner = request.FILES.get("banner_image")
    if banner:
        event.banner = banner

    event.save()
    logger.info("Event updated: %s (id=%d) by user %s", event.title, event.pk, request.user.pk)
    messages.success(request, f'"{event.title}" has been updated.')
    return redirect("eventManagement:organizer_dashboard")


@staff_member_required
@require_POST
def delete_event(request, event_id):
    event = Event.all_objects.filter(pk=event_id).first()
    if event is None:
        messages.error(request, "Event not found.")
        return redirect("eventManagement:organizer_dashboard")

    if event.created_by != request.user and not request.user.is_superuser:
        messages.error(request, "You can only delete your own events.")
        return redirect("eventManagement:organizer_dashboard")

    if request.POST.get("confirm") != "yes":
        messages.warning(request, "Deletion not confirmed.")
        return redirect("eventManagement:organizer_dashboard")

    event.delete()
    logger.info("Event soft-deleted: %s (id=%d) by user %s", event.title, event_id, request.user.pk)
    messages.success(request, f'"{event.title}" has been archived.')
    return redirect("eventManagement:organizer_dashboard")


@staff_member_required
@require_POST
def update_event_status(request, event_id):
    event = Event.all_objects.filter(pk=event_id, is_deleted=False, created_by=request.user).first()
    if event is None:
        messages.error(request, "Event not found or permission denied.")
        return redirect("eventManagement:organizer_dashboard")

    new_status = request.POST.get("new_status", "").strip()
    if new_status not in EventStatus.values:
        messages.error(request, "Invalid status.")
        return redirect("eventManagement:organizer_dashboard")

    allowed = _VALID_TRANSITIONS.get(event.status, set())
    if new_status not in allowed:
        messages.error(
            request,
            f"Cannot transition from {event.get_status_display()} to {EventStatus(new_status).label}.",
        )
        return redirect("eventManagement:organizer_dashboard")

    event.status = new_status
    event.save(update_fields=["status", "updated_at"])
    logger.info(
        "Event status changed: %s (id=%d) → %s by user %s",
        event.title, event.pk, new_status, request.user.pk,
    )
    messages.success(request, f'"{event.title}" status updated to {EventStatus(new_status).label}.')
    return redirect("eventManagement:organizer_dashboard")


@staff_member_required
@require_POST
def create_announcement(request, event_id):
    from notification.models import Notification
    from registration.models import Registration

    event = Event.all_objects.filter(pk=event_id, is_deleted=False, created_by=request.user).first()
    if event is None:
        messages.error(request, "Event not found or permission denied.")
        return redirect("eventManagement:organizer_dashboard")

    title = request.POST.get("title", "").strip()
    content = request.POST.get("content", "").strip()

    if not title or not content:
        messages.error(request, "Announcement title and content are required.")
        return redirect("eventManagement:organizer_dashboard")

    EventAnnouncement.objects.create(event=event, title=title, content=content)

    registrant_user_ids = list(
        Registration.objects.filter(
            event=event, status__in=["confirmed", "submitted"]
        ).values_list("user_id", flat=True)
    )

    if registrant_user_ids:
        Notification.objects.bulk_create(
            [
                Notification(
                    user_id=uid,
                    type="announcement",
                    title=f"[{event.title}] {title}",
                    body=textwrap.shorten(content, width=300, placeholder="…"),
                    actor=request.user,
                )
                for uid in registrant_user_ids
            ],
            ignore_conflicts=True,
        )

    logger.info(
        "Announcement '%s' created for event %d, notified %d users.",
        title, event.pk, len(registrant_user_ids),
    )
    messages.success(
        request,
        f"Announcement posted. {len(registrant_user_ids)} participant(s) notified.",
    )
    return redirect("eventManagement:organizer_dashboard")


@staff_member_required
@require_POST
def update_registration_status(request, reg_id):
    from registration.models import Registration, RegistrationStatus

    reg = Registration.objects.select_related("event").filter(pk=reg_id).first()
    if reg is None:
        messages.error(request, "Registration not found.")
        return redirect("eventManagement:organizer_dashboard")

    if reg.event.created_by != request.user and not request.user.is_superuser:
        messages.error(request, "Permission denied.")
        return redirect("eventManagement:organizer_dashboard")

    new_status = request.POST.get("status", "").strip()
    if new_status not in RegistrationStatus.values:
        messages.error(request, "Invalid registration status.")
        return redirect("eventManagement:organizer_dashboard")

    reg.status = new_status
    reg.save(update_fields=["status", "updated_at"])
    messages.success(request, f"Registration {reg.registration_id} updated to {new_status}.")
    return redirect("eventManagement:organizer_dashboard")


@staff_member_required
def export_registrations(request, event_id):
    import csv
    from django.http import StreamingHttpResponse
    from registration.models import Registration

    event = Event.all_objects.filter(pk=event_id, created_by=request.user, is_deleted=False).first()
    if event is None:
        messages.error(request, "Event not found or permission denied.")
        return redirect("eventManagement:organizer_dashboard")

    registrations = (
        Registration.objects.filter(event=event)
        .select_related("user", "user__profile", "team")
        .order_by("registered_at")
    )

    class Echo:
        def write(self, value):
            return value

    def csv_rows():
        writer = csv.writer(Echo())
        yield writer.writerow([
            "registration_id", "name", "email", "college", "branch",
            "year", "phone", "type", "status", "team", "role",
            "looking_for_team", "registered_at",
        ])
        for reg in registrations:
            profile = getattr(reg.user, "profile", None)
            yield writer.writerow([
                reg.registration_id,
                reg.user.get_full_name() or reg.user.username,
                reg.user.email,
                profile.college if profile else "",
                profile.branch if profile else "",
                profile.year if profile else "",
                profile.phone if profile else "",
                reg.get_type_display(),
                reg.get_status_display(),
                reg.team.name if reg.team else "",
                reg.preferred_role,
                reg.looking_for_team,
                reg.registered_at.strftime("%Y-%m-%d %H:%M:%S"),
            ])

    filename = f"registrations_{event.slug or event.pk}.csv"
    response = StreamingHttpResponse(csv_rows(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# ── [E10] Event Cloning ───────────────────────────────────────────────────────

@staff_member_required
@require_POST
def clone_event(request, event_id):
    """
    Create a full copy of an existing event in DRAFT status.

    Copies: all event fields, rounds, FAQs, judges, sponsors.
    Does NOT copy: registrations, teams, announcements.
    """
    source = get_object_or_404(
        Event.all_objects, pk=event_id, created_by=request.user
    )

    with transaction.atomic():
        cloned = Event.objects.create(
            title=f"Copy of {source.title}",
            description=source.description,
            category=source.category,
            mode=source.mode,
            participation_type=source.participation_type,
            status=EventStatus.DRAFT,
            event_start=source.event_start,
            event_end=source.event_end,
            registration_start=source.registration_start,
            registration_end=source.registration_end,
            submission_deadline=source.submission_deadline,
            venue=source.venue,
            platform_link=source.platform_link,
            capacity=source.capacity,
            min_team_size=source.min_team_size,
            max_team_size=source.max_team_size,
            allow_team_creation=source.allow_team_creation,
            allow_join_requests=source.allow_join_requests,
            prize_pool=source.prize_pool,  # preserved from source
            prize_1st=source.prize_1st,
            prize_2nd=source.prize_2nd,
            prize_3rd=source.prize_3rd,
            prize_special=source.prize_special,
            participation_certificate=source.participation_certificate,
            merit_certificate=source.merit_certificate,
            registration_fee=source.registration_fee,
            eligibility=source.eligibility,
            rules=source.rules,
            faqs=source.faqs,
            contact_info=source.contact_info,
            is_featured=False,
            created_by=request.user,
        )

        # Clone rounds
        for round_ in source.rounds.all():
            EventRound.objects.create(
                event=cloned,
                name=round_.name,
                description=round_.description,
                order=round_.order,
                start_date=round_.start_date,
                end_date=round_.end_date,
                elimination_criteria=round_.elimination_criteria,
            )

        # Clone judges
        for judge in source.judges.all():
            EventJudge.objects.create(
                event=cloned,
                name=judge.name,
                designation=judge.designation,
                bio=judge.bio,
            )

        # Clone sponsors
        for sponsor in source.sponsors.all():
            EventSponsor.objects.create(
                event=cloned,
                name=sponsor.name,
                website_url=sponsor.website_url,
                sponsor_type=sponsor.sponsor_type,
            )

    logger.info(
        "Event cloned: source=%d → clone=%d by user %s",
        source.pk, cloned.pk, request.user.pk,
    )
    messages.success(
        request,
        f'"{source.title}" has been cloned. Edit the copy below before publishing.',
    )
    return redirect("eventManagement:edit_event", event_id=cloned.pk)
