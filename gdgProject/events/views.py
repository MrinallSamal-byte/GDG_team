import logging

from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Event, EventCategory, EventStatus

logger = logging.getLogger(__name__)


def home(request):
    """Event listing page with filtering and featured carousel."""
    now = timezone.now()

    category = request.GET.get("category", "")
    mode = request.GET.get("mode", "")
    status_filter = request.GET.get("status", "")
    search = request.GET.get("q", "")

    sort = request.GET.get("sort", "newest")

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
        grid_qs = grid_qs.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    # Apply sort
    if sort == "deadline":
        event_grid = grid_qs.order_by("registration_end")[:24]
    elif sort == "popular":
        event_grid = grid_qs.order_by("-registered_count")[:24]
    else:  # newest (default)
        event_grid = grid_qs.order_by("-event_start")[:24]

    featured_events = base_qs.filter(is_featured=True).order_by("-event_start")[:6]
    if not featured_events.exists():
        featured_events = base_qs.order_by("-event_start")[:3]

    return render(
        request,
        "events/home.html",
        {
            "featured_events": featured_events,
            "event_grid": event_grid,
            # Keys that match the template
            "q": search,
            "active_category": category,
            "active_sort": sort,
            "categories": EventCategory.choices,
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

    participants = event.registrations.filter(
        status__in=["confirmed", "submitted"]
    ).select_related("user", "user__profile")[:50]

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
        messages.info(
            request, "Organizer contact email is not available for this event yet."
        )
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
        logger.exception(
            "Failed to send organizer contact email for event %s", event.pk
        )
        messages.error(
            request, "We could not send your message right now. Please try again later."
        )
        return redirect("events:event_detail", event_id=event.pk)

    messages.success(request, "Your message has been sent to the organizers.")
    return redirect("events:event_detail", event_id=event.pk)
