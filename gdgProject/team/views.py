"""
Team management views.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    ChatMessage,
    JoinRequest,
    JoinRequestStatus,
    Team,
    TeamMembership,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_team_or_404(team_id):
    """Return Team or raise 404."""
    return get_object_or_404(Team, pk=team_id)


def _is_member(team, user):
    return team.memberships.filter(user=user).exists()


def _is_leader(team, user):
    return team.leader == user


# ── Views ─────────────────────────────────────────────────────────────────────

@login_required
def team_management(request, team_id):
    team = _get_team_or_404(team_id)

    if not _is_member(team, request.user):
        messages.error(request, "You are not a member of this team.")
        return redirect("dashboard:home")

    # POST — new chat message
    if request.method == "POST":
        body = request.POST.get("message", "").strip()
        if body:
            ChatMessage.objects.create(team=team, sender=request.user, body=body)
            messages.success(request, "Message sent.")
        return redirect("team:team_management", team_id=team_id)

    # GET
    memberships = team.memberships.select_related("user").order_by("joined_at")
    members = [
        {
            "name": m.user.get_full_name() or m.user.username,
            "leader": m.user == team.leader,
            "role": m.get_role_display(),
            "skills": m.skills,
        }
        for m in memberships
    ]

    pending_reqs = []
    if _is_leader(team, request.user):
        pending_reqs = (
            team.join_requests
            .filter(status=JoinRequestStatus.PENDING)
            .select_related("user")
        )

    join_requests = [
        {
            "id": r.id,
            "name": r.user.get_full_name() or r.user.username,
            "role": r.get_role_display(),
            "skills": r.skills,
            "message": r.message,
        }
        for r in pending_reqs
    ]

    chat_msgs = (
        ChatMessage.objects
        .filter(team=team, is_deleted=False)
        .select_related("sender")
        .order_by("created_at")
    )

    # Coverage: which MemberRole values team has vs lacks
    present_roles = set(memberships.values_list("role", flat=True))
    from .models import MemberRole
    coverage = [
        {"label": label, "ok": val in present_roles}
        for val, label in MemberRole.choices
    ]

    max_size = team.event.max_team_size if hasattr(team.event, "max_team_size") else 4
    members_count = f"{team.member_count}/{max_size}"

    context = {
        "team": {
            "id": team.id,
            "name": team.name,
            "event": team.event.title,
            "members_count": members_count,
            "capacity_pct": int(team.member_count / max_size * 100),
            "member_count": team.member_count,
            "max_size": max_size,
        },
        "members": members,
        "requests": join_requests,
        "coverage": coverage,
        "chat_messages": chat_msgs,
        "is_leader": _is_leader(team, request.user),
        "user_is_leader": _is_leader(team, request.user),
    }
    return render(request, "team/team_management.html", context)


@login_required
@require_POST
def approve_request(request, team_id, request_id):
    team = _get_team_or_404(team_id)
    if not _is_leader(team, request.user):
        messages.error(request, "Only the team leader can approve requests.")
        return redirect("team:team_management", team_id=team_id)

    join_req = get_object_or_404(
        JoinRequest, pk=request_id, team=team, status=JoinRequestStatus.PENDING
    )

    if team.is_full:
        messages.error(request, "Team is already full.")
        return redirect("team:team_management", team_id=team_id)

    join_req.status = JoinRequestStatus.APPROVED
    join_req.reviewed_by = request.user
    join_req.reviewed_at = timezone.now()
    join_req.save()

    TeamMembership.objects.get_or_create(
        team=team,
        user=join_req.user,
        defaults={"role": join_req.role, "skills": join_req.skills},
    )

    messages.success(request, f"{join_req.user.get_full_name() or join_req.user.username} added to team.")
    return redirect("team:team_management", team_id=team_id)


@login_required
@require_POST
def decline_request(request, team_id, request_id):
    team = _get_team_or_404(team_id)
    if not _is_leader(team, request.user):
        messages.error(request, "Only the team leader can decline requests.")
        return redirect("team:team_management", team_id=team_id)

    join_req = get_object_or_404(
        JoinRequest, pk=request_id, team=team, status=JoinRequestStatus.PENDING
    )
    join_req.status = JoinRequestStatus.DECLINED
    join_req.reviewed_by = request.user
    join_req.reviewed_at = timezone.now()
    join_req.save()

    messages.info(request, "Join request declined.")
    return redirect("team:team_management", team_id=team_id)


@login_required
@require_POST
def leave_team(request, team_id):
    team = _get_team_or_404(team_id)

    if _is_leader(team, request.user):
        messages.error(request, "Team leader cannot leave. Transfer leadership or disband the team first.")
        return redirect("team:team_management", team_id=team_id)

    membership = TeamMembership.objects.filter(team=team, user=request.user).first()
    if membership:
        membership.delete()
        messages.success(request, f"You have left {team.name}.")
    else:
        messages.warning(request, "You are not a member of this team.")

    return redirect("dashboard:my_teams")
