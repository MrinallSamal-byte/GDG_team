import logging

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Event, EventStatus

logger = logging.getLogger(__name__)


def home(request):
    """Event listing page with filtering and featured carousel."""
    now = timezone.now()

    # ── Filters from query params ──────────────────────────────────────────
    category = request.GET.get('category', '')
    mode = request.GET.get('mode', '')
    status_filter = request.GET.get('status', '')
    search = request.GET.get('q', '')

    base_qs = Event.objects.filter(
        status__in=[
            EventStatus.PUBLISHED,
            EventStatus.REGISTRATION_OPEN,
            EventStatus.REGISTRATION_CLOSED,
            EventStatus.ONGOING,
            EventStatus.COMPLETED,
        ]
    ).annotate(
        registered_count=Count(
            'registrations',
            filter=Q(registrations__status__in=['confirmed', 'submitted']),
        )
    )

    grid_qs = base_qs

    if category:
        grid_qs = grid_qs.filter(category=category)
    if mode:
        grid_qs = grid_qs.filter(mode=mode)
    if status_filter == 'open':
        grid_qs = grid_qs.filter(
            status=EventStatus.REGISTRATION_OPEN,
            registration_start__lte=now,
            registration_end__gte=now,
        )
    elif status_filter == 'closed':
        grid_qs = grid_qs.filter(
            status__in=[EventStatus.REGISTRATION_CLOSED, EventStatus.COMPLETED]
        )
    if search:
        grid_qs = grid_qs.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    event_grid = grid_qs.order_by('-event_start')[:24]

    # ── Featured events ────────────────────────────────────────────────────
    featured_events = base_qs.filter(is_featured=True).order_by('-event_start')[:6]
    # Fallback: if no featured events, show upcoming ones
    if not featured_events.exists():
        featured_events = base_qs.order_by('-event_start')[:3]

    return render(
        request,
        'events/home.html',
        {
            'featured_events': featured_events,
            'event_grid': event_grid,
            'current_category': category,
            'current_mode': mode,
            'current_status': status_filter,
            'search_query': search,
        },
    )


def event_detail(request, event_id):
    """Full event detail page with all tab data."""
    event = get_object_or_404(
        Event.objects.annotate(
            registered_count=Count(
                'registrations',
                filter=Q(registrations__status__in=['confirmed', 'submitted']),
            )
        ),
        pk=event_id,
    )

    rounds = event.rounds.all().order_by('order')

    # Registered participants (confirmed/submitted)
    participants = event.registrations.filter(
        status__in=['confirmed', 'submitted']
    ).select_related('user', 'user__profile')[:50]

    # Open teams for this event
    teams_open = event.teams.filter(
        status='open', is_deleted=False,
    ).select_related('leader').annotate(
        current_members=Count('memberships'),
    )

    # Judges and sponsors
    judges = event.judges.all()
    sponsors = event.sponsors.all()

    # Announcements
    announcements = event.announcements.all()[:10]

    # Check if current user is already registered
    is_registered = False
    user_registration = None
    if request.user.is_authenticated:
        user_registration = event.registrations.filter(user=request.user).first()
        is_registered = user_registration is not None

    # Participants looking for a team
    looking_for_team_regs = event.registrations.filter(
        looking_for_team=True,
        status__in=['confirmed', 'submitted'],
    ).select_related('user', 'user__profile')[:30]

    return render(
        request,
        'events/event_detail.html',
        {
            'event': event,
            'rounds': rounds,
            'participants': participants,
            'teams_open': teams_open,
            'judges': judges,
            'sponsors': sponsors,
            'announcements': announcements,
            'is_registered': is_registered,
            'user_registration': user_registration,
            'looking_for_team_regs': looking_for_team_regs,
        },
    )
