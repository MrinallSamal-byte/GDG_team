import logging

from core.exceptions import AppError
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from events.models import Event
from registration.models import Registration, RegistrationStatus

from .models import (
    ChatMessage,
    JoinRequest,
    JoinRequestStatus,
    MemberRole,
    Team,
    TeamMembership,
    TeamStatus,
)
from .services import TeamJoinRequestService

logger = logging.getLogger(__name__)


def _user_can_access_team(team, user):
    if not user.is_authenticated:
        return False
    return (
        user.is_superuser
        or team.leader_id == user.id
        or team.memberships.filter(user=user).exists()
    )


def _build_coverage(memberships):
    covered_roles = {membership.role for membership in memberships}
    return [
        {"label": label, "ok": role_value in covered_roles}
        for role_value, label in MemberRole.choices
        if role_value != MemberRole.OTHER
    ]


def _build_suggested_members(team):
    memberships = list(team.memberships.select_related("user"))
    role_labels = dict(MemberRole.choices)
    current_user_ids = {membership.user_id for membership in memberships}
    pending_request_user_ids = set(
        team.join_requests.filter(status=JoinRequestStatus.PENDING).values_list("user_id", flat=True)
    )
    covered_roles = {membership.role for membership in memberships}
    team_skill_tokens = {
        token.strip().lower()
        for membership in memberships
        for token in membership.skills.split(",")
        if token.strip()
    }

    candidates = []
    candidate_regs = (
        Registration.objects.filter(
            event=team.event,
            looking_for_team=True,
            status__in=[RegistrationStatus.CONFIRMED, RegistrationStatus.SUBMITTED],
        )
        .exclude(user_id__in=current_user_ids | pending_request_user_ids)
        .select_related("user", "user__profile")
        .prefetch_related("tech_stacks")
    )

    for registration in candidate_regs:
        tech_stack_names = [tech.tech_name for tech in registration.tech_stacks.all()]
        missing_skill_matches = [
            t for t in tech_stack_names if t.strip().lower() not in team_skill_tokens
        ]
        role_match = bool(
            registration.preferred_role
            and registration.preferred_role in MemberRole.values
            and registration.preferred_role not in covered_roles
        )
        score = (3 if role_match else 0) + len(missing_skill_matches)
        if score <= 0 and not tech_stack_names:
            continue

        candidates.append({
            "registration": registration,
            "display_name": registration.user.get_full_name() or registration.user.username,
            "college": getattr(registration.user.profile, "college", ""),
            "preferred_role_label": role_labels.get(registration.preferred_role, registration.preferred_role),
            "tech_stacks": tech_stack_names,
            "match_reasons": missing_skill_matches[:3],
            "score": score,
        })

    return sorted(candidates, key=lambda c: (-c["score"], c["display_name"].lower()))[:5]


def _build_team_context(team, request_user):
    memberships = list(team.memberships.select_related("user").all())
    is_leader = team.leader_id == request_user.id
    join_requests = (
        team.join_requests.filter(status=JoinRequestStatus.PENDING).select_related("user")
        if is_leader
        else JoinRequest.objects.none()
    )
    return {
        "team": team,
        "members": memberships,
        "requests": join_requests,
        "chat_messages": team.messages.filter(is_deleted=False).select_related("sender")[:50],
        "coverage": _build_coverage(memberships),
        "suggested_members": _build_suggested_members(team) if is_leader else [],
        "is_leader": is_leader,
        "member_count": len(memberships),
    }


@login_required
@require_http_methods(["GET", "POST"])
def team_management(request, team_id):
    team = get_object_or_404(
        Team.objects.select_related("event", "leader").annotate(current_members=Count("memberships")),
        pk=team_id,
    )

    if not _user_can_access_team(team, request.user):
        logger.warning("Unauthorized team access attempt", extra={"team_id": team.pk, "user_id": request.user.pk})
        messages.error(request, "Only team members can access this team workspace.")
        return redirect("events:event_detail", event_id=team.event.pk)

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "send_message":
            body = request.POST.get("message", "").strip()
            if not body:
                messages.error(request, "Message cannot be empty.")
            else:
                ChatMessage.objects.create(team=team, sender=request.user, body=body)
                messages.success(request, "Message sent.")

        elif action == "approve_request":
            if team.leader_id != request.user.id:
                messages.error(request, "Only the team leader can approve requests.")
                return redirect("team:team_management", team_id=team_id)
            req_id = request.POST.get("request_id")
            try:
                join_req = JoinRequest.objects.get(pk=req_id, team=team)
                TeamJoinRequestService().approve_request(
                    team_id=team.pk, requester_user_id=join_req.user_id, approver=request.user,
                )
                messages.success(request, f"Approved {join_req.user.get_full_name() or join_req.user.username}.")
            except JoinRequest.DoesNotExist:
                messages.error(request, "Request not found.")
            except AppError as exc:
                messages.error(request, exc.message)
            except Exception:
                logger.error("Unexpected error approving join request", exc_info=True)
                messages.error(request, "Unable to approve the join request right now.")

        elif action == "decline_request":
            if team.leader_id != request.user.id:
                messages.error(request, "Only the team leader can decline requests.")
                return redirect("team:team_management", team_id=team_id)
            req_id = request.POST.get("request_id")
            try:
                join_req = JoinRequest.objects.get(pk=req_id, team=team)
                TeamJoinRequestService().decline_request(
                    team_id=team.pk, requester_user_id=join_req.user_id, decliner=request.user,
                )
                messages.success(request, f"Declined {join_req.user.get_full_name() or join_req.user.username}.")
            except JoinRequest.DoesNotExist:
                messages.error(request, "Request not found.")
            except AppError as exc:
                messages.error(request, exc.message)
            except Exception:
                logger.error("Unexpected error declining join request", exc_info=True)
                messages.error(request, "Unable to decline the join request right now.")

        return redirect("team:team_management", team_id=team_id)

    return render(request, "team/team_management.html", _build_team_context(team, request.user))


@login_required
@require_http_methods(["POST"])
def create_team(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if not event.allow_team_creation:
        messages.error(request, "Team creation is not allowed for this event.")
        return redirect("events:event_detail", event_id=event.pk)
    name = request.POST.get("team_name", "").strip()
    if not name:
        messages.error(request, "Team name is required.")
        return redirect("events:event_detail", event_id=event.pk)
    try:
        team = Team.objects.create(event=event, name=name, leader=request.user, status=TeamStatus.OPEN)
        TeamMembership.objects.create(team=team, user=request.user, role=MemberRole.OTHER)
        messages.success(request, f'Team "{name}" created successfully!')
        return redirect("team:team_management", team_id=team.pk)
    except IntegrityError:
        messages.error(request, "A team with that name already exists, or you already lead a team.")
        return redirect("events:event_detail", event_id=event.pk)


@login_required
@require_http_methods(["POST"])
def request_join(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    if not team.event.allow_join_requests:
        messages.error(request, "Join requests are not allowed for this event.")
        return redirect("events:event_detail", event_id=team.event.pk)
    if team.is_full:
        messages.error(request, "This team is already full.")
        return redirect("events:event_detail", event_id=team.event.pk)
    role = request.POST.get("role", MemberRole.OTHER)
    try:
        TeamJoinRequestService().create_join_request(
            team_id=team.pk,
            user=request.user,
            role=role if role in MemberRole.values else MemberRole.OTHER,
            skills=request.POST.get("skills", "").strip(),
            message=request.POST.get("message", "").strip(),
        )
        messages.success(request, f'Join request sent to team "{team.name}".')
    except Exception as e:
        messages.error(request, str(e))
    return redirect("events:event_detail", event_id=team.event.pk)


@login_required
@require_http_methods(["POST"])
def leave_team(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    if team.leader == request.user:
        messages.error(request, "Team leaders cannot leave their own team. Disband the team instead.")
        return redirect("team:team_management", team_id=team.pk)
    membership = TeamMembership.objects.filter(team=team, user=request.user).first()
    if not membership:
        messages.error(request, "You are not a member of this team.")
        return redirect("events:event_detail", event_id=team.event.pk)
    membership.delete()
    if team.status == TeamStatus.CLOSED and not team.is_full:
        team.status = TeamStatus.OPEN
        team.save(update_fields=["status", "updated_at"])
    messages.success(request, f'You have left team "{team.name}".')
    return redirect("events:event_detail", event_id=team.event.pk)


@login_required
@require_http_methods(["POST"])
def toggle_team_status(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    if team.leader != request.user:
        messages.error(request, "Only the team leader can change team status.")
        return redirect("team:team_management", team_id=team.pk)
    if team.status == TeamStatus.OPEN:
        team.status = TeamStatus.CLOSED
        msg = f'Team "{team.name}" is now closed for new members.'
    elif team.status == TeamStatus.CLOSED:
        team.status = TeamStatus.OPEN
        msg = f'Team "{team.name}" is now open for new members.'
    else:
        messages.error(request, "Cannot change status of a disbanded team.")
        return redirect("team:team_management", team_id=team.pk)
    team.save(update_fields=["status", "updated_at"])
    messages.success(request, msg)
    return redirect("team:team_management", team_id=team.pk)


@login_required
@require_http_methods(["POST"])
def remove_member(request, team_id, user_id):
    team = get_object_or_404(Team, pk=team_id)
    if team.leader != request.user:
        messages.error(request, "Only the team leader can remove members.")
        return redirect("team:team_management", team_id=team.pk)
    if team.leader_id == user_id:
        messages.error(request, "You cannot remove yourself as team leader.")
        return redirect("team:team_management", team_id=team.pk)
    membership = TeamMembership.objects.filter(team=team, user_id=user_id).first()
    if not membership:
        messages.error(request, "User is not a member of this team.")
        return redirect("team:team_management", team_id=team.pk)
    removed = membership.user.get_full_name() or membership.user.username
    membership.delete()
    if team.status == TeamStatus.CLOSED and not team.is_full:
        team.status = TeamStatus.OPEN
        team.save(update_fields=["status", "updated_at"])
    messages.success(request, f"{removed} has been removed from the team.")
    return redirect("team:team_management", team_id=team.pk)


@login_required
@require_http_methods(["POST"])
def approve_request(request, team_id, request_id):
    try:
        join_req = JoinRequest.objects.select_related("team").get(pk=request_id, team_id=team_id)
    except JoinRequest.DoesNotExist:
        messages.error(request, "Join request not found.")
        return redirect("dashboard:pending_requests")
    if join_req.team.leader_id != request.user.id:
        messages.error(request, "Only the team leader can approve requests.")
        return redirect("dashboard:pending_requests")
    try:
        TeamJoinRequestService().approve_request(
            team_id=team_id, requester_user_id=join_req.user_id, approver=request.user,
        )
        messages.success(request, f"Approved {join_req.user.get_full_name() or join_req.user.username}.")
    except AppError as exc:
        messages.error(request, exc.message)
    except Exception:
        logger.error("Unexpected error approving join request", exc_info=True)
        messages.error(request, "Unable to approve the request right now.")
    return redirect("dashboard:pending_requests")


@login_required
@require_http_methods(["POST"])
def decline_request(request, team_id, request_id):
    try:
        join_req = JoinRequest.objects.select_related("team").get(pk=request_id, team_id=team_id)
    except JoinRequest.DoesNotExist:
        messages.error(request, "Join request not found.")
        return redirect("dashboard:pending_requests")
    if join_req.team.leader_id != request.user.id:
        messages.error(request, "Only the team leader can decline requests.")
        return redirect("dashboard:pending_requests")
    try:
        TeamJoinRequestService().decline_request(
            team_id=team_id, requester_user_id=join_req.user_id, decliner=request.user,
        )
        messages.success(request, "Request declined.")
    except AppError as exc:
        messages.error(request, exc.message)
    except Exception:
        logger.error("Unexpected error declining join request", exc_info=True)
        messages.error(request, "Unable to decline the request right now.")
    return redirect("dashboard:pending_requests")


@login_required
def find_teammates(request):
    return redirect("dashboard:find_teammates")


# ── [E15] AI-Powered Team Matching ────────────────────────────────────────────

@login_required
@require_GET
def ai_team_matches(request, event_id):
    """
    Show AI-ranked open teams for the current user on a given event.
    Accessible at: GET /teams/match/<event_id>/
    """
    event = get_object_or_404(Event, pk=event_id)

    from .ai_matching import get_team_recommendations
    matches = get_team_recommendations(user=request.user, event_id=event.pk, top_n=10)

    return render(
        request,
        "team/ai_matches.html",
        {
            "event": event,
            "matches": matches,
        },
    )
