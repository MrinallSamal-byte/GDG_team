"""
Dashboard views — all wired to the real database.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from notification.models import Notification
from registration.models import Registration
from team.models import JoinRequest, JoinRequestStatus, TeamMembership
from users.models import UserProfile


def _get_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@login_required
def user_dashboard(request):
    profile = _get_profile(request.user)
    recent_registrations = (
        Registration.objects
        .filter(user=request.user)
        .select_related("event", "team")
        .order_by("-registered_at")[:5]
    )
    my_events = [
        {
            "id": r.event.id,
            "title": r.event.title,
            "status": r.get_status_display(),
            "team": r.team.name if r.team else None,
        }
        for r in recent_registrations
    ]

    memberships = (
        TeamMembership.objects
        .filter(user=request.user)
        .select_related("team__event")
        .order_by("-joined_at")[:5]
    )
    my_teams = [
        {
            "id": m.team.id,
            "name": m.team.name,
            "event": m.team.event.title,
            "role": m.get_role_display(),
        }
        for m in memberships
    ]

    unread_notifications = (
        Notification.objects
        .filter(user=request.user, read=False)
        .order_by("-created_at")[:5]
    )

    return render(request, "dashboard/user_dashboard.html", {
        "my_events": my_events,
        "my_teams": my_teams,
        "notifications": unread_notifications,
        "current_page": "overview",
        "profile": profile,
    })


@login_required
def my_profile(request):
    profile = _get_profile(request.user)
    user = request.user

    profile_data = {
        "name": user.get_full_name() or user.username,
        "email": user.email,
        "phone": profile.phone or "Not set",
        "college": profile.college or "Not set",
        "branch": profile.branch or "Not set",
        "year": profile.year_display or "Not set",
        "github": profile.github or "Not set",
        "linkedin": profile.linkedin or "Not set",
        "bio": profile.bio or "No bio yet. Click Edit Profile to add one.",
        "skills": profile.skills_list or [],
    }
    events_joined = Registration.objects.filter(user=user).count()
    teams_count = TeamMembership.objects.filter(user=user).count()
    stats = {
        "events_joined": events_joined,
        "teams": teams_count,
        "certificates": 0,
    }
    return render(request, "dashboard/my_profile.html", {
        "profile": profile_data,
        "stats": stats,
        "current_page": "profile",
    })


@login_required
def my_events(request):
    registrations = (
        Registration.objects
        .filter(user=request.user)
        .select_related("event", "team")
        .order_by("-registered_at")
    )
    events = [
        {
            "id": r.event.id,
            "title": r.event.title,
            "category": r.event.get_category_display() if hasattr(r.event, "get_category_display") else "",
            "mode": r.event.get_mode_display() if hasattr(r.event, "get_mode_display") else "",
            "date": r.event.start_date.strftime("%b %d, %Y") if r.event.start_date else "TBD",
            "status": r.get_status_display(),
            "team": r.team.name if r.team else None,
            "team_id": r.team.id if r.team else None,
            "role": r.get_type_display(),
        }
        for r in registrations
    ]
    return render(request, "dashboard/my_events.html", {
        "events": events,
        "current_page": "events",
    })


@login_required
def my_teams(request):
    memberships = (
        TeamMembership.objects
        .filter(user=request.user)
        .select_related("team__event")
        .prefetch_related("team__memberships__user")
        .order_by("-joined_at")
    )
    teams = [
        {
            "id": m.team.id,
            "name": m.team.name,
            "event": m.team.event.title,
            "role": m.get_role_display(),
            "members": [
                mem.user.get_full_name() or mem.user.username
                for mem in m.team.memberships.all()
            ],
        }
        for m in memberships
    ]
    return render(request, "dashboard/my_teams.html", {
        "teams": teams,
        "current_page": "teams",
    })


@login_required
def pending_requests(request):
    # Incoming: join requests to teams the user leads
    incoming_qs = (
        JoinRequest.objects
        .filter(team__leader=request.user, status=JoinRequestStatus.PENDING)
        .select_related("user", "team__event")
        .order_by("-created_at")
    )
    incoming = [
        {
            "id": r.id,
            "team_id": r.team.id,
            "from": r.user.get_full_name() or r.user.username,
            "team": r.team.name,
            "event": r.team.event.title,
            "role": r.get_role_display(),
            "skills": r.skills,
        }
        for r in incoming_qs
    ]

    # Outgoing: requests this user sent to other teams
    outgoing_qs = (
        JoinRequest.objects
        .filter(user=request.user)
        .exclude(status=JoinRequestStatus.PENDING)
        .select_related("team__event")
        .order_by("-created_at")
    )
    pending_qs = (
        JoinRequest.objects
        .filter(user=request.user, status=JoinRequestStatus.PENDING)
        .select_related("team__event")
        .order_by("-created_at")
    )
    outgoing = [
        {
            "team": r.team.name,
            "team_id": r.team.id,
            "event": r.team.event.title,
            "status": r.get_status_display(),
        }
        for r in list(pending_qs) + list(outgoing_qs)
    ]

    return render(request, "dashboard/pending_requests.html", {
        "incoming": incoming,
        "outgoing": outgoing,
        "current_page": "requests",
    })


@login_required
def notifications_view(request):
    notifs = (
        Notification.objects
        .filter(user=request.user)
        .order_by("-created_at")
    )
    # Map Notification type to icon / css class
    type_map = {
        "success": "success",
        "join_request": "info",
        "announcement": "info",
        "reminder": "warning",
        "system": "default",
    }
    notifications = [
        {
            "id": n.id,
            "message": n.body,
            "title": n.title,
            "time": n.created_at,
            "type": type_map.get(n.type, "default"),
            "read": n.read,
        }
        for n in notifs
    ]
    unread_count = sum(1 for n in notifications if not n["read"])
    return render(request, "dashboard/notifications.html", {
        "notifications": notifications,
        "unread_count": unread_count,
        "current_page": "notifications",
    })


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(user=request.user, read=False).update(read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect("dashboard:notifications")


@login_required
@require_http_methods(["GET", "POST"])
def settings_view(request):
    profile = _get_profile(request.user)

    if request.method == "POST":
        display_name = request.POST.get("display_name", "").strip()
        email = request.POST.get("email", "").strip()

        if display_name:
            parts = display_name.split(" ", 1)
            request.user.first_name = parts[0]
            request.user.last_name = parts[1] if len(parts) > 1 else ""
            request.user.save(update_fields=["first_name", "last_name"])

        if email and email != request.user.email:
            from django.contrib.auth.models import User
            if User.objects.filter(email=email).exclude(pk=request.user.pk).exists():
                messages.error(request, "That email is already in use by another account.")
            else:
                request.user.email = email
                request.user.save(update_fields=["email"])

        messages.success(request, "Settings saved successfully!")
        return redirect("dashboard:settings")

    return render(request, "dashboard/settings.html", {
        "current_page": "settings",
        "profile": profile,
    })
