import json
import logging

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_http_methods

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


@staff_member_required
def organizer_dashboard(request):
    my_events = Event.all_objects.filter(created_by=request.user).annotate(
        registration_count=Count(
            'registrations',
            filter=Q(registrations__status__in=['confirmed', 'submitted']),
        )
    ).order_by('-created_at')

    total_registrations = sum(e.registration_count for e in my_events)
    active_events = my_events.filter(
        status__in=[
            EventStatus.PUBLISHED,
            EventStatus.REGISTRATION_OPEN,
            EventStatus.ONGOING,
        ],
        is_deleted=False,
    ).count()

    analytics = {
        'total_registrations': total_registrations,
        'active_events': active_events,
    }

    return render(
        request,
        'eventManagement/organizer_dashboard.html',
        {
            'analytics': analytics,
            'my_events': my_events,
        },
    )


@staff_member_required
@require_http_methods(['GET', 'POST'])
def create_event(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', '').strip()
        mode = request.POST.get('mode', '').strip()
        start_date = request.POST.get('start_date', '').strip()
        end_date = request.POST.get('end_date', '').strip()
        reg_start = request.POST.get('reg_start_date', '').strip()
        reg_end = request.POST.get('reg_end_date', '').strip()
        description = request.POST.get('description', '').strip()
        venue = request.POST.get('venue', '').strip()
        participation_type = request.POST.get('participation_type', 'individual').strip()
        max_participants = request.POST.get('max_participants', '100').strip()
        min_team_size = request.POST.get('min_team_size', '1').strip()
        max_team_size = request.POST.get('max_team_size', '1').strip()
        registration_fee = request.POST.get('registration_fee', '0').strip()
        rules = request.POST.get('rules', '').strip()
        faqs_raw = request.POST.get('faqs', '').strip()
        prize_1st = request.POST.get('prize_1st', '').strip()
        prize_2nd = request.POST.get('prize_2nd', '').strip()
        prize_3rd = request.POST.get('prize_3rd', '').strip()
        certificates = request.POST.get('certificates', '').strip()
        judges_raw = request.POST.get('judges', '').strip()
        sponsors_raw = request.POST.get('sponsors', '').strip()

        # ── Validation ─────────────────────────────────────────────
        errors = []
        if not title:
            errors.append('Event title is required.')
        if category not in EventCategory.values:
            errors.append('Please select a valid category.')
        if mode not in EventMode.values:
            errors.append('Please select a valid event mode.')
        if not start_date:
            errors.append('Start date is required.')
        if not end_date:
            errors.append('End date is required.')

        from django.utils.timezone import is_naive, make_aware

        def _aware(dt):
            """Return a timezone-aware datetime, converting if naive."""
            return make_aware(dt) if dt and is_naive(dt) else dt

        event_start = _aware(parse_datetime(start_date)) if start_date else None
        event_end = _aware(parse_datetime(end_date)) if end_date else None
        reg_start_dt = _aware(parse_datetime(reg_start)) if reg_start else event_start
        reg_end_dt = _aware(parse_datetime(reg_end)) if reg_end else event_end

        if event_start and event_end and event_start > event_end:
            errors.append('End date must be on or after the start date.')
        if not description:
            errors.append('Event description is required.')

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(
                request,
                'eventManagement/create_event.html',
                {'form_data': request.POST},
            )

        # ── Parse numeric fields ───────────────────────────────────
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

        # ── Parse FAQs ─────────────────────────────────────────────
        faqs = []
        if faqs_raw:
            for line in faqs_raw.split('\n'):
                line = line.strip()
                if not line:
                    continue
                faqs.append({'q': line, 'a': ''})

        # ── Certificates ───────────────────────────────────────────
        participation_cert = certificates in ('participation', 'both')
        merit_cert = certificates in ('merit', 'both')

        # ── Create Event ───────────────────────────────────────────
        event = Event.objects.create(
            title=title,
            description=description,
            category=category,
            mode=mode,
            participation_type=participation_type if participation_type in ParticipationType.values else 'individual',
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
            rules=rules,
            faqs=faqs,
            prize_1st=prize_1st,
            prize_2nd=prize_2nd,
            prize_3rd=prize_3rd,
            participation_certificate=participation_cert,
            merit_certificate=merit_cert,
            created_by=request.user,
        )

        # ── Banner upload ──────────────────────────────────────────
        banner = request.FILES.get('banner_image')
        if banner:
            event.banner = banner
            event.save(update_fields=['banner'])

        # ── Create rounds ──────────────────────────────────────────
        round_names = request.POST.getlist('round_name[]')
        round_dates = request.POST.getlist('round_date[]')
        round_descs = request.POST.getlist('round_desc[]')
        for i, rname in enumerate(round_names):
            rname = rname.strip()
            if not rname:
                continue
            rdate = round_dates[i].strip() if i < len(round_dates) else ''
            rdesc = round_descs[i].strip() if i < len(round_descs) else ''
            rd_start = parse_datetime(rdate) if rdate else event_start
            EventRound.objects.create(
                event=event,
                name=rname,
                description=rdesc,
                order=i + 1,
                start_date=rd_start or event_start,
                end_date=rd_start or event_end,
            )

        # ── Create judges ──────────────────────────────────────────
        if judges_raw:
            for name in judges_raw.split(','):
                name = name.strip()
                if name:
                    EventJudge.objects.create(event=event, name=name)

        # ── Create sponsors ────────────────────────────────────────
        if sponsors_raw:
            for name in sponsors_raw.split(','):
                name = name.strip()
                if name:
                    EventSponsor.objects.create(event=event, name=name)

        logger.info("Event created: %s (id=%d) by user %s", title, event.pk, request.user.pk)
        messages.success(request, f'"{title}" has been created successfully!')
        return redirect('eventManagement:organizer_dashboard')

    return render(request, 'eventManagement/create_event.html')


# ── Valid status transitions ────────────────────────────────────────────────
_VALID_TRANSITIONS = {
    EventStatus.DRAFT: {EventStatus.PUBLISHED, EventStatus.CANCELLED},
    EventStatus.PUBLISHED: {EventStatus.REGISTRATION_OPEN, EventStatus.DRAFT, EventStatus.CANCELLED},
    EventStatus.REGISTRATION_OPEN: {EventStatus.REGISTRATION_CLOSED, EventStatus.CANCELLED},
    EventStatus.REGISTRATION_CLOSED: {EventStatus.ONGOING, EventStatus.REGISTRATION_OPEN, EventStatus.CANCELLED},
    EventStatus.ONGOING: {EventStatus.COMPLETED, EventStatus.CANCELLED},
    EventStatus.COMPLETED: set(),
    EventStatus.CANCELLED: set(),
    EventStatus.ARCHIVED: set(),
}


@staff_member_required
@require_http_methods(['GET', 'POST'])
def edit_event(request, event_id):
    """Allow the event creator to edit an event that has not yet started."""
    event = Event.all_objects.get(pk=event_id) if Event.all_objects.filter(pk=event_id).exists() else None
    if event is None:
        messages.error(request, 'Event not found.')
        return redirect('eventManagement:organizer_dashboard')

    if event.created_by != request.user and not request.user.is_superuser:
        messages.error(request, 'You can only edit your own events.')
        return redirect('eventManagement:organizer_dashboard')

    if event.status in (EventStatus.ONGOING, EventStatus.COMPLETED, EventStatus.CANCELLED):
        messages.warning(request, 'This event cannot be edited in its current status.')
        return redirect('eventManagement:organizer_dashboard')

    if request.method == 'GET':
        return render(request, 'eventManagement/edit_event.html', {'event': event})

    # POST — update the event
    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    category = request.POST.get('category', '').strip()
    mode = request.POST.get('mode', '').strip()
    venue = request.POST.get('venue', '').strip()
    start_date = request.POST.get('start_date', '').strip()
    end_date = request.POST.get('end_date', '').strip()
    reg_start = request.POST.get('reg_start_date', '').strip()
    reg_end = request.POST.get('reg_end_date', '').strip()
    max_participants = request.POST.get('max_participants', '').strip()
    registration_fee = request.POST.get('registration_fee', '').strip()
    rules = request.POST.get('rules', '').strip()
    prize_1st = request.POST.get('prize_1st', '').strip()
    prize_2nd = request.POST.get('prize_2nd', '').strip()
    prize_3rd = request.POST.get('prize_3rd', '').strip()
    certificates = request.POST.get('certificates', '').strip()
    contact_info = request.POST.get('contact_info', '').strip()

    errors = []
    if not title:
        errors.append('Event title is required.')
    if category and category not in EventCategory.values:
        errors.append('Please select a valid category.')
    if mode and mode not in EventMode.values:
        errors.append('Please select a valid event mode.')

    from django.utils.timezone import is_naive, make_aware

    def _aware(dt):
        """Return a timezone-aware datetime, converting if naive."""
        return make_aware(dt) if dt and is_naive(dt) else dt

    event_start = _aware(parse_datetime(start_date)) if start_date else event.event_start
    event_end = _aware(parse_datetime(end_date)) if end_date else event.event_end
    reg_start_dt = _aware(parse_datetime(reg_start)) if reg_start else event.registration_start
    reg_end_dt = _aware(parse_datetime(reg_end)) if reg_end else event.registration_end

    if event_start and event_end and event_start > event_end:
        errors.append('End date must be on or after the start date.')

    if errors:
        for err in errors:
            messages.error(request, err)
        return render(request, 'eventManagement/edit_event.html', {'event': event})

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
    event.participation_certificate = certificates in ('participation', 'both')
    event.merit_certificate = certificates in ('merit', 'both')
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

    banner = request.FILES.get('banner_image')
    if banner:
        event.banner = banner

    event.save()

    logger.info("Event updated: %s (id=%d) by user %s", event.title, event.pk, request.user.pk)
    messages.success(request, f'"{event.title}" has been updated.')
    return redirect('eventManagement:organizer_dashboard')


@staff_member_required
@require_http_methods(['POST'])
def delete_event(request, event_id):
    """Soft-delete an event (archive it) — only the creator can delete."""
    event = Event.all_objects.filter(pk=event_id).first()
    if event is None:
        messages.error(request, 'Event not found.')
        return redirect('eventManagement:organizer_dashboard')

    if event.created_by != request.user and not request.user.is_superuser:
        messages.error(request, 'You can only delete your own events.')
        return redirect('eventManagement:organizer_dashboard')

    if request.POST.get('confirm') != 'yes':
        messages.warning(request, 'Deletion not confirmed.')
        return redirect('eventManagement:organizer_dashboard')

    event.delete()  # soft-delete via model override
    logger.info("Event soft-deleted: %s (id=%d) by user %s", event.title, event_id, request.user.pk)
    messages.success(request, f'"{event.title}" has been archived.')
    return redirect('eventManagement:organizer_dashboard')


@staff_member_required
@require_http_methods(['POST'])
def update_event_status(request, event_id):
    """Transition an event to a new status, enforcing valid transitions."""
    event = Event.all_objects.filter(pk=event_id, is_deleted=False, created_by=request.user).first()
    if event is None:
        messages.error(request, 'Event not found or permission denied.')
        return redirect('eventManagement:organizer_dashboard')

    new_status = request.POST.get('new_status', '').strip()
    if new_status not in EventStatus.values:
        messages.error(request, 'Invalid status.')
        return redirect('eventManagement:organizer_dashboard')

    allowed = _VALID_TRANSITIONS.get(event.status, set())
    if new_status not in allowed:
        messages.error(request, f'Cannot transition from {event.get_status_display()} to {EventStatus(new_status).label}.')
        return redirect('eventManagement:organizer_dashboard')

    event.status = new_status
    event.save(update_fields=['status', 'updated_at'])
    logger.info(
        "Event status changed: %s (id=%d) → %s by user %s",
        event.title, event.pk, new_status, request.user.pk,
    )
    messages.success(request, f'"{event.title}" status updated to {EventStatus(new_status).label}.')
    return redirect('eventManagement:organizer_dashboard')


@staff_member_required
@require_http_methods(['POST'])
def create_announcement(request, event_id):
    """Post an announcement and notify all confirmed registrants."""
    from notification.models import Notification
    from registration.models import Registration

    event = Event.all_objects.filter(pk=event_id, is_deleted=False, created_by=request.user).first()
    if event is None:
        messages.error(request, 'Event not found or permission denied.')
        return redirect('eventManagement:organizer_dashboard')

    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '').strip()

    if not title or not content:
        messages.error(request, 'Announcement title and content are required.')
        return redirect('eventManagement:organizer_dashboard')

    announcement = EventAnnouncement.objects.create(
        event=event,
        title=title,
        content=content,
    )

    # Notify all confirmed/submitted registrants
    registrant_user_ids = list(
        Registration.objects.filter(
            event=event,
            status__in=['confirmed', 'submitted'],
        ).values_list('user_id', flat=True)
    )

    notifications = [
        Notification(
            user_id=uid,
            type='announcement',
            title=f'[{event.title}] {title}',
            body=content[:300],
            actor=request.user,
        )
        for uid in registrant_user_ids
    ]
    if notifications:
        Notification.objects.bulk_create(notifications, ignore_conflicts=True)

    logger.info(
        "Announcement '%s' created for event %d, notified %d users.",
        title, event.pk, len(registrant_user_ids),
    )
    messages.success(request, f'Announcement posted. {len(registrant_user_ids)} participant(s) notified.')
    return redirect('eventManagement:organizer_dashboard')


@staff_member_required
@require_http_methods(['POST'])
def update_registration_status(request, reg_id):
    """Approve or reject a participant registration (when moderation is enabled)."""
    from registration.models import Registration, RegistrationStatus

    reg = Registration.objects.select_related('event').filter(pk=reg_id).first()
    if reg is None:
        messages.error(request, 'Registration not found.')
        return redirect('eventManagement:organizer_dashboard')

    if reg.event.created_by != request.user and not request.user.is_superuser:
        messages.error(request, 'Permission denied.')
        return redirect('eventManagement:organizer_dashboard')

    new_status = request.POST.get('status', '').strip()
    if new_status not in RegistrationStatus.values:
        messages.error(request, 'Invalid registration status.')
        return redirect('eventManagement:organizer_dashboard')

    reg.status = new_status
    reg.save(update_fields=['status', 'updated_at'])
    logger.info(
        "Registration %s status set to %s by organizer %s",
        reg.registration_id, new_status, request.user.pk,
    )
    messages.success(request, f'Registration {reg.registration_id} updated to {new_status}.')
    return redirect('eventManagement:organizer_dashboard')


@staff_member_required
def export_registrations(request, event_id):
    """Export all registrations for an event as a CSV file."""
    import csv

    from django.http import StreamingHttpResponse

    from registration.models import Registration

    event = Event.all_objects.filter(pk=event_id, created_by=request.user, is_deleted=False).first()
    if event is None:
        messages.error(request, 'Event not found or permission denied.')
        return redirect('eventManagement:organizer_dashboard')

    registrations = Registration.objects.filter(event=event).select_related(
        'user', 'user__profile', 'team',
    ).order_by('registered_at')

    class Echo:
        """Adapter that implements the write method of a file-like object."""

        def write(self, value):
            """Write the value by returning it, instead of storing in a buffer."""
            return value

    def csv_rows():
        """Yield rows as CSV strings."""
        writer = csv.writer(Echo())
        yield writer.writerow([
            'registration_id', 'name', 'email', 'college', 'branch',
            'year', 'phone', 'type', 'status', 'team', 'role',
            'looking_for_team', 'registered_at',
        ])
        for reg in registrations:
            profile = getattr(reg.user, 'profile', None)
            yield writer.writerow([
                reg.registration_id,
                reg.user.get_full_name() or reg.user.username,
                reg.user.email,
                profile.college if profile else '',
                profile.branch if profile else '',
                profile.year if profile else '',
                profile.phone if profile else '',
                reg.get_type_display(),
                reg.get_status_display(),
                reg.team.name if reg.team else '',
                reg.preferred_role,
                reg.looking_for_team,
                reg.registered_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])

    filename = f"registrations_{event.slug or event.pk}.csv"
    response = StreamingHttpResponse(csv_rows(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

