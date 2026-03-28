import logging

from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Event, EventCategory, EventStatus

logger = logging.getLogger(__name__)


def _build_event_queryset(params):
    """Build a filtered/sorted queryset from request params (shared by page & API)."""
    now = timezone.now()
    category = params.get("category", "")
    mode = params.get("mode", "")
    status_filter = params.get("status", "")
    search = params.get("q", "")
    sort = params.get("sort", "newest")

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
            "registrations",
            filter=Q(registrations__status__in=["confirmed", "submitted"]),
        )
    )

    grid_qs = base_qs

    if category:
        grid_qs = grid_qs.filter(category=category)
    if mode:
        grid_qs = grid_qs.filter(mode=mode)
    if status_filter == "open":
        grid_qs = grid_qs.filter(
            status=EventStatus.REGISTRATION_OPEN,
            registration_start__lte=now,
            registration_end__gte=now,
        )
    elif status_filter == "closed":
        grid_qs = grid_qs.filter(
            status__in=[EventStatus.REGISTRATION_CLOSED, EventStatus.COMPLETED]
        )
    if search:
        grid_qs = grid_qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

    if sort == "deadline":
        grid_qs = grid_qs.order_by("registration_end")
    elif sort == "popular":
        grid_qs = grid_qs.order_by("-registered_count")
    else:
        grid_qs = grid_qs.order_by("-event_start")

    return grid_qs, base_qs


def events_api(request):
    """Return filtered events as JSON for AJAX requests."""
    grid_qs, _ = _build_event_queryset(request.GET)
    events = grid_qs[:50]

    data = []
    for ev in events:
        data.append(
            {
                "id": ev.id,
                "title": ev.title,
                "category": ev.category,
                "category_display": ev.get_category_display(),
                "mode_display": ev.get_mode_display(),
                "participation_type_display": ev.get_participation_type_display(),
                "status": ev.status,
                "status_display": ev.get_status_display(),
                "event_start": ev.event_start.strftime("%d %b"),
                "event_end": (
                    ev.event_end.strftime("%d %b")
                    if ev.event_end and ev.event_end.date() != ev.event_start.date()
                    else ""
                ),
                "registered_count": ev.registered_count,
                "capacity": ev.capacity,
                "fill_pct": (round(ev.registered_count / ev.capacity * 100) if ev.capacity else 0),
                "prize_pool": str(int(ev.prize_pool)) if ev.prize_pool else "",
            }
        )

    return JsonResponse({"events": data})


def home(request):
    """Event listing page with filtering and featured carousel."""
    search = request.GET.get("q", "")
    category = request.GET.get("category", "")
    sort = request.GET.get("sort", "newest")

    grid_qs, base_qs = _build_event_queryset(request.GET)
    event_page = Paginator(grid_qs, 16).get_page(request.GET.get("page") or 1)
    pagination_params = request.GET.copy()
    pagination_params.pop("page", None)

    featured_events = base_qs.filter(is_featured=True).order_by("-event_start")[:6]
    if not featured_events.exists():
        featured_events = base_qs.order_by("-event_start")[:3]

    return render(
        request,
        "events/home.html",
        {
            "featured_events": featured_events,
            "event_page": event_page,
            "q": search,
            "active_category": category,
            "active_sort": sort,
            "categories": EventCategory.choices,
            "pagination_query": pagination_params.urlencode(),
        },
    )


def event_detail(request, event_id):
    """Full event detail page with all tab data."""
    event = get_object_or_404(
        Event.objects.annotate(
            registered_count=Count(
                "registrations",
                filter=Q(registrations__status__in=["confirmed", "submitted"]),
            )
        ),
        pk=event_id,
    )

    rounds = event.rounds.all().order_by("order")

    participants = event.registrations.filter(status__in=["confirmed", "submitted"]).select_related(
        "user", "user__profile"
    )[:50]

    teams_open = (
        event.teams.filter(status="open", is_deleted=False)
        .select_related("leader")
        .annotate(current_members=Count("memberships"))
    )

    judges = event.judges.all()
    sponsors = event.sponsors.all()
    announcements = event.announcements.all()[:10]

    is_registered = False
    user_registration = None
    if request.user.is_authenticated:
        user_registration = event.registrations.filter(user=request.user).first()
        is_registered = user_registration is not None

    looking_for_team_regs = event.registrations.filter(
        looking_for_team=True,
        status__in=["confirmed", "submitted"],
    ).select_related("user", "user__profile")[:30]

    return render(
        request,
        "events/event_detail.html",
        {
            "event": event,
            "rounds": rounds,
            "participants": participants,
            "teams_open": teams_open,
            "judges": judges,
            "sponsors": sponsors,
            "announcements": announcements,
            "is_registered": is_registered,
            "user_registration": user_registration,
            "looking_for_team_regs": looking_for_team_regs,
        },
    )


def event_detail_slug(request, slug):
    """Canonical slug-based URL — resolves to the event detail page."""
    event = get_object_or_404(Event, slug=slug)
    return redirect("events:event_detail", event_id=event.pk, permanent=True)


@require_http_methods(["GET", "POST"])
def contact_organizer(request, event_id):
    event = get_object_or_404(Event.objects.select_related("created_by"), pk=event_id)

    if request.method == "GET":
        return redirect("events:event_detail", event_id=event.pk)

    message_body = request.POST.get("message", "").strip()
    if not message_body:
        messages.error(request, "Enter a message before contacting the organizers.")
        return redirect("events:event_detail", event_id=event.pk)

    organizer_email = event.created_by.email
    if not organizer_email:
        messages.info(request, "Organizer contact email is not available for this event yet.")
        return redirect("events:event_detail", event_id=event.pk)

    sender_name = "Anonymous user"
    sender_email = "No email provided"
    if request.user.is_authenticated:
        sender_name = request.user.get_full_name() or request.user.username
        sender_email = request.user.email or sender_email

    try:
        send_mail(
            subject=f"CampusArena event inquiry: {event.title}",
            message=(
                f"Event: {event.title}\n"
                f"From: {sender_name}\n"
                f"Email: {sender_email}\n\n"
                f"{message_body}"
            ),
            from_email=None,
            recipient_list=[organizer_email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send organizer contact email for event %s", event.pk)
        messages.error(request, "We could not send your message right now. Please try again later.")
        return redirect("events:event_detail", event_id=event.pk)

    messages.success(request, "Your message has been sent to the organizers.")
    return redirect("events:event_detail", event_id=event.pk)
