from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from notification.models import Notification
from registration.models import Registration, RegistrationStatus
from team.models import JoinRequest, JoinRequestStatus, Team, TeamMembership
from users.models import UserProfile


def _get_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@login_required
def user_dashboard(request):
    my_regs = (
        Registration.objects.filter(user=request.user)
        .select_related("event")
        .order_by("-registered_at")[:5]
    )
    my_events = [
        {"title": reg.event.title, "status": reg.get_status_display(), "id": reg.event.pk}
        for reg in my_regs
    ]

    my_memberships = (
        TeamMembership.objects.filter(user=request.user, team__is_deleted=False)
        .select_related("team", "team__event")
        .order_by("-joined_at")[:5]
    )
    my_teams = [
        {
            "name": m.team.name,
            "event": m.team.event.title,
            "role": m.get_role_display(),
            "id": m.team.pk,
        }
        for m in my_memberships
    ]

    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:5]

    return render(
        request,
        "dashboard/user_dashboard.html",
        {
            "my_events": my_events,
            "my_teams": my_teams,
            "notifications": notifications,
            "current_page": "overview",
        },
    )


@login_required
def my_profile(request):
    profile = _get_profile(request.user)
    user = request.user

    # Live certificate count
    from certificates.models import Certificate

    cert_count = Certificate.objects.filter(user=user).count()

    profile_data = {
        "name": user.get_full_name() or user.username,
        "email": user.email,
        "phone": profile.phone or "Not set",
        "college": profile.college or "Not set",
        "branch": profile.branch or "Not set",
        "year": profile.year_display or "Not set",
        "github": profile.github or "",
        "linkedin": profile.linkedin or "",
        "portfolio": profile.portfolio or "",
        "bio": profile.bio or "No bio yet. Click Edit Profile to add one.",
        "skills": profile.skills_list or [],
        "profile_picture_url": profile.profile_picture.url if profile.profile_picture else None,
    }
    stats = {
        "events_joined": Registration.objects.filter(user=user).count(),
        "teams": TeamMembership.objects.filter(user=user, team__is_deleted=False).count(),
        "certificates": cert_count,
    }
    return render(
        request,
        "dashboard/my_profile.html",
        {"profile": profile_data, "stats": stats, "current_page": "profile"},
    )


@login_required
def my_events(request):
    registrations = list(
        Registration.objects.filter(user=request.user).select_related("event", "team")
    )

    event_ids = [reg.event_id for reg in registrations]
    membership_by_event = {
        m.team.event_id: m
        for m in TeamMembership.objects.filter(
            user=request.user,
            team__event_id__in=event_ids,
            team__is_deleted=False,
        ).select_related("team")
    }

    events = [
        {
            "id": reg.event.pk,
            "title": reg.event.title,
            "category": reg.event.get_category_display(),
            "mode": reg.event.get_mode_display(),
            "date": reg.event.event_start,
            "status": reg.get_status_display(),
            "reg_id": reg.pk,
            "reg_status_raw": reg.status,
            "team": membership_by_event[reg.event_id].team.name
            if reg.event_id in membership_by_event
            else None,
            "role": membership_by_event[reg.event_id].get_role_display()
            if reg.event_id in membership_by_event
            else None,
        }
        for reg in registrations
    ]

    return render(
        request,
        "dashboard/my_events.html",
        {"events": events, "current_page": "events"},
    )


@login_required
def my_teams(request):
    memberships = list(
        TeamMembership.objects.filter(
            user=request.user, team__is_deleted=False
        ).select_related("team", "team__event")
    )

    if not memberships:
        return render(request, "dashboard/my_teams.html", {"teams": [], "current_page": "teams"})

    team_ids = [m.team_id for m in memberships]
    co_members: dict = defaultdict(list)
    for cm in TeamMembership.objects.filter(team_id__in=team_ids).select_related("user"):
        co_members[cm.team_id].append(cm.user.get_full_name() or cm.user.username)

    teams = [
        {
            "id": m.team.pk,
            "name": m.team.name,
            "event": m.team.event.title,
            "event_id": m.team.event_id,
            "role": m.get_role_display(),
            "members": co_members[m.team_id],
            "is_leader": m.team.leader_id == request.user.id,
        }
        for m in memberships
    ]

    return render(
        request,
        "dashboard/my_teams.html",
        {"teams": teams, "current_page": "teams"},
    )


@login_required
def pending_requests(request):
    led_teams = Team.objects.filter(leader=request.user, is_deleted=False)
    incoming = JoinRequest.objects.filter(
        team__in=led_teams, status=JoinRequestStatus.PENDING
    ).select_related("user", "user__profile", "team", "team__event")

    incoming_data = [
        {
            "id": jr.pk,
            "team_id": jr.team_id,
            "from": jr.user.get_full_name() or jr.user.username,
            "college": getattr(jr.user.profile, "college", "") if hasattr(jr.user, "profile") else "",
            "team": jr.team.name,
            "event": jr.team.event.title,
            "message": jr.message,
            "role": jr.get_role_display(),
        }
        for jr in incoming
    ]

    outgoing = (
        JoinRequest.objects.filter(user=request.user)
        .select_related("team", "team__event")
        .order_by("-created_at")[:20]
    )
    outgoing_data = [
        {
            "team": jr.team.name,
            "event": jr.team.event.title,
            "status": jr.get_status_display(),
            "created_at": jr.created_at,
        }
        for jr in outgoing
    ]

    return render(
        request,
        "dashboard/pending_requests.html",
        {
            "incoming": incoming_data,
            "outgoing": outgoing_data,
            "current_page": "requests",
        },
    )


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:30]
    return render(
        request,
        "dashboard/notifications.html",
        {"notifications": notifications, "current_page": "notifications"},
    )


@login_required
@require_POST
def mark_all_read(request):
    """Mark all of the current user's notifications as read."""
    updated = Notification.objects.filter(user=request.user, read=False).update(read=True)
    return JsonResponse({"ok": True, "updated": updated})


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

    return render(
        request,
        "dashboard/settings.html",
        {"current_page": "settings", "profile": profile},
    )


@login_required
def find_teammates(request):
    """Show users who are registered and looking for a team across all open events."""
    looking = (
        Registration.objects.filter(
            looking_for_team=True,
            status__in=[RegistrationStatus.CONFIRMED, RegistrationStatus.SUBMITTED],
        )
        .select_related("user", "user__profile", "event")
        .order_by("-registered_at")[:50]
    )

    return render(
        request,
        "dashboard/find_teammates.html",
        {"current_page": "find_teammates", "looking_users": looking},
    )


@login_required
@require_http_methods(["GET", "POST"])
def edit_profile(request):
    profile = _get_profile(request.user)

    if request.method == "POST":
        profile.phone = request.POST.get("phone", "").strip()
        profile.github = request.POST.get("github", "").strip()
        profile.linkedin = request.POST.get("linkedin", "").strip()
        profile.portfolio = request.POST.get("portfolio", "").strip()
        profile.bio = request.POST.get("bio", "").strip()
        profile.college = request.POST.get("college", "").strip()
        profile.branch = request.POST.get("branch", "").strip()

        if "profile_photo" in request.FILES:
            profile.profile_picture = request.FILES["profile_photo"]

        year_val = request.POST.get("year", "").strip()
        if year_val:
            try:
                year_int = int(year_val)
                if 1 <= year_int <= 6:
                    profile.year = year_int
                else:
                    messages.error(request, "Year must be between 1 and 6.")
                    return render(
                        request,
                        "dashboard/edit_profile.html",
                        {"profile": profile, "current_page": "profile"},
                    )
            except ValueError:
                messages.error(request, "Year must be a number.")
                return render(
                    request,
                    "dashboard/edit_profile.html",
                    {"profile": profile, "current_page": "profile"},
                )
        else:
            profile.year = None

        skills = request.POST.get("skills", "").strip()
        if skills:
            profile.skills = skills

        profile.save()
        messages.success(request, "Profile updated successfully!")
        return redirect("dashboard:my_profile")

    return render(
        request,
        "dashboard/edit_profile.html",
        {"profile": profile, "current_page": "profile"},
    )
