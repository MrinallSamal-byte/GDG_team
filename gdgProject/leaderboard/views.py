import logging

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from events.models import Event

from .models import Leaderboard, LeaderboardEntry

logger = logging.getLogger("campusarena.leaderboard")


@require_GET
def event_leaderboard(request, event_id):
    """Public-facing leaderboard for an event (if published by organiser)."""
    event = get_object_or_404(Event, pk=event_id)
    lb = Leaderboard.objects.filter(event=event).first()

    # Hide unpublished leaderboard from non-organisers
    if lb and not lb.is_public:
        is_organiser = (
            request.user.is_authenticated
            and (request.user == event.created_by or request.user.is_superuser)
        )
        if not is_organiser:
            messages.info(request, "The leaderboard for this event has not been published yet.")
            return redirect("events:event_detail", event_id=event.pk)

    entries = lb.entries.select_related("team", "user").order_by("rank") if lb else []

    return render(
        request,
        "leaderboard/event_leaderboard.html",
        {"event": event, "leaderboard": lb, "entries": entries},
    )


@staff_member_required
@require_GET
def manage_leaderboard(request, event_id):
    """Organiser management view — create/edit leaderboard entries."""
    event = get_object_or_404(Event.all_objects, pk=event_id, created_by=request.user)
    lb, _ = Leaderboard.objects.get_or_create(event=event)
    entries = lb.entries.select_related("team", "user").order_by("rank")

    return render(
        request,
        "leaderboard/manage_leaderboard.html",
        {"event": event, "leaderboard": lb, "entries": entries},
    )


@staff_member_required
@require_POST
def upsert_entry(request, event_id):
    """Add or update a leaderboard entry."""
    event = get_object_or_404(Event.all_objects, pk=event_id, created_by=request.user)
    lb, _ = Leaderboard.objects.get_or_create(event=event)

    rank = request.POST.get("rank", "").strip()
    label = request.POST.get("label", "").strip()
    score = request.POST.get("score", "0").strip()
    notes = request.POST.get("notes", "").strip()
    team_id = request.POST.get("team_id", "").strip()
    user_id = request.POST.get("user_id", "").strip()

    if not rank or not label:
        messages.error(request, "Rank and label are required.")
        return redirect("leaderboard:manage", event_id=event.pk)

    try:
        rank_int = int(rank)
        score_dec = float(score)
    except (ValueError, TypeError):
        messages.error(request, "Rank must be a whole number and score must be numeric.")
        return redirect("leaderboard:manage", event_id=event.pk)

    LeaderboardEntry.objects.update_or_create(
        leaderboard=lb,
        rank=rank_int,
        defaults={
            "label": label,
            "score": score_dec,
            "notes": notes,
            "team_id": int(team_id) if team_id else None,
            "user_id": int(user_id) if user_id else None,
        },
    )
    messages.success(request, f"Rank #{rank_int} saved.")
    return redirect("leaderboard:manage", event_id=event.pk)


@staff_member_required
@require_POST
def delete_entry(request, event_id, entry_id):
    event = get_object_or_404(Event.all_objects, pk=event_id, created_by=request.user)
    lb = get_object_or_404(Leaderboard, event=event)
    entry = get_object_or_404(LeaderboardEntry, pk=entry_id, leaderboard=lb)
    rank = entry.rank
    entry.delete()
    messages.success(request, f"Rank #{rank} removed.")
    return redirect("leaderboard:manage", event_id=event.pk)


@staff_member_required
@require_POST
def toggle_visibility(request, event_id):
    event = get_object_or_404(Event.all_objects, pk=event_id, created_by=request.user)
    lb, _ = Leaderboard.objects.get_or_create(event=event)
    lb.is_public = not lb.is_public
    lb.save(update_fields=["is_public", "updated_at"])
    state = "published" if lb.is_public else "hidden"
    messages.success(request, f"Leaderboard is now {state}.")
    return redirect("leaderboard:manage", event_id=event.pk)
