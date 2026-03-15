import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from events.models import Event
from users.models import UserProfile

from .models import (
    CustomFormField,
    Registration,
    RegistrationResponse,
    RegistrationStatus,
    RegistrationTechStack,
    RegistrationType,
)

logger = logging.getLogger(__name__)

_ROLES = [
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "UI/UX Designer",
    "ML/AI Engineer",
    "DevOps Engineer",
    "Project Manager",
]

_ROLE_VALUE_MAP = {
    "Frontend Developer": "frontend",
    "Backend Developer": "backend",
    "Full Stack Developer": "fullstack",
    "Mobile Developer": "mobile",
    "UI/UX Designer": "uiux",
    "ML/AI Engineer": "ml_ai",
    "Data Scientist": "data",
    "DevOps Engineer": "devops",
    "Project Manager": "pm",
}

_SKILLS = [
    "React", "Node.js", "Python", "Django", "Flutter", "Figma",
    "TensorFlow", "Docker", "AWS", "MongoDB",
]


def _get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def _normalize_registration_choice(post_data):
    raw_type = post_data.get("type", "individual").strip()
    team_action = post_data.get("team_action", "").strip()

    if raw_type == "create_team":
        return RegistrationType.TEAM, "create"
    if raw_type == "join_team":
        return RegistrationType.TEAM, "join"
    if raw_type == RegistrationType.TEAM:
        return RegistrationType.TEAM, team_action
    return RegistrationType.INDIVIDUAL, ""


def _extract_selected_skills(post_data):
    raw_skills = post_data.get("skills", "").strip()
    if not raw_skills:
        return []
    seen = set()
    selected_skills = []
    for skill in [s.strip() for s in raw_skills.split(",") if s.strip()]:
        lowered = skill.lower()
        if lowered not in seen:
            seen.add(lowered)
            selected_skills.append(skill)
    return selected_skills


def _normalize_member_role(selected_role):
    if not selected_role:
        return "other"
    return _ROLE_VALUE_MAP.get(
        selected_role,
        selected_role if selected_role in _ROLE_VALUE_MAP.values() else "other",
    )


def _save_registration_tech_stacks(registration, selected_skills):
    if not selected_skills:
        return
    RegistrationTechStack.objects.bulk_create(
        [
            RegistrationTechStack(
                registration=registration,
                tech_name=skill,
                is_primary=(index < 3),
            )
            for index, skill in enumerate(selected_skills)
        ],
        ignore_conflicts=True,
    )


def _send_confirmation_email(registration):
    try:
        send_mail(
            subject=f"Registration Confirmed — {registration.event.title}",
            message=(
                f"Hi {registration.user.first_name or registration.user.username},\n\n"
                f'You have successfully registered for "{registration.event.title}".\n'
                f"Your Registration ID: {registration.registration_id}\n\n"
                f'Event Date: {registration.event.event_start.strftime("%B %d, %Y")}\n'
                "Good luck!\n\nTeam CampusArena"
            ),
            from_email=None,
            recipient_list=[registration.user.email],
            fail_silently=False,
        )
    except Exception:
        logger.error(
            "Failed to send confirmation email for registration %s",
            registration.registration_id,
            exc_info=True,
        )


def _save_custom_responses(registration, custom_fields, post_data):
    responses = [
        RegistrationResponse(
            registration=registration,
            field=field,
            response_value=post_data.get(f"custom_{field.pk}", "").strip(),
        )
        for field in custom_fields
    ]
    if responses:
        RegistrationResponse.objects.bulk_create(responses, ignore_conflicts=True)


@login_required
@require_http_methods(["GET"])
def registration_confirmation(request, registration_id):
    lookup = {"pk": registration_id}
    if not request.user.is_staff:
        lookup["user"] = request.user
    registration = get_object_or_404(
        Registration.objects.select_related("event", "team"), **lookup
    )
    return render(request, "registration/confirmation.html", {"registration": registration})


@login_required
@require_POST
def cancel_registration(request, registration_id):
    """Cancel the current user's registration for an event."""
    registration = get_object_or_404(
        Registration.objects.select_related("event", "team"),
        pk=registration_id,
        user=request.user,
    )

    if registration.status == RegistrationStatus.CANCELLED:
        messages.info(request, "This registration is already cancelled.")
        return redirect("dashboard:my_events")

    if registration.event.event_start <= timezone.now():
        messages.error(request, "You cannot cancel a registration after the event has started.")
        return redirect("dashboard:my_events")

    with transaction.atomic():
        registration.status = RegistrationStatus.CANCELLED
        registration.save(update_fields=["status", "updated_at"])

        if registration.team:
            from team.models import TeamMembership, TeamStatus

            membership = TeamMembership.objects.filter(
                team=registration.team, user=request.user
            ).first()
            if membership:
                if registration.team.leader_id == request.user.id:
                    # Leader cancels — disband the whole team
                    registration.team.status = TeamStatus.DISBANDED
                    registration.team.is_deleted = True
                    registration.team.save(update_fields=["status", "is_deleted", "updated_at"])
                else:
                    membership.delete()
                    team = registration.team
                    if team.status == TeamStatus.CLOSED and not team.is_full:
                        team.status = TeamStatus.OPEN
                        team.save(update_fields=["status", "updated_at"])

    logger.info(
        "Registration %s cancelled by user %d",
        registration.registration_id,
        request.user.pk,
    )
    messages.success(request, f'Your registration for "{registration.event.title}" has been cancelled.')
    return redirect("dashboard:my_events")


@login_required
@require_http_methods(["GET", "POST"])
def register_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    existing = Registration.objects.filter(event=event, user=request.user).first()
    if existing:
        messages.info(request, "You are already registered for this event.")
        return redirect("events:event_detail", event_id=event.pk)

    if not event.is_registration_open:
        messages.warning(request, "Registration is not currently open for this event.")
        return redirect("events:event_detail", event_id=event.pk)

    custom_fields = CustomFormField.objects.filter(event=event).order_by("display_order")

    open_teams = []
    if event.participation_type in ("team", "both"):
        from django.db.models import Count

        open_teams = (
            event.teams.filter(status="open", is_deleted=False)
            .annotate(current_members=Count("memberships"))
            .select_related("leader")
        )

    if request.method == "GET":
        return render(
            request,
            "registration/register_event.html",
            {
                "event": event,
                "roles": _ROLES,
                "skills": _SKILLS,
                "custom_fields": custom_fields,
                "open_teams": open_teams,
                "form_data": {},
            },
        )

    # POST
    reg_type, team_action = _normalize_registration_choice(request.POST)
    team_id = request.POST.get("team_id", "").strip()
    preferred_role = request.POST.get("preferred_role", "").strip()
    normalized_role = _normalize_member_role(preferred_role)
    looking_for_team = request.POST.get("looking_for_team") == "on"
    team_name = request.POST.get("team_name", "").strip()
    selected_skills = _extract_selected_skills(request.POST)

    if event.participation_type == "individual" and reg_type == RegistrationType.TEAM:
        messages.error(request, "This event only allows individual registrations.")
        return redirect("events:event_detail", event_id=event.pk)
    if event.participation_type == "team" and reg_type == RegistrationType.INDIVIDUAL:
        messages.error(request, "This event requires team-based registration.")
        return redirect("events:event_detail", event_id=event.pk)

    profile = _get_or_create_profile(request.user)
    phone = request.POST.get("phone", "").strip()
    college = request.POST.get("college", "").strip()
    branch = request.POST.get("branch", "").strip()
    year = request.POST.get("year", "").strip()

    errors = []
    if not request.user.get_full_name():
        full_name = request.POST.get("full_name", "").strip()
        if not full_name:
            errors.append("Full name is required.")
        else:
            parts = full_name.split(" ", 1)
            request.user.first_name = parts[0]
            request.user.last_name = parts[1] if len(parts) > 1 else ""
            request.user.save(update_fields=["first_name", "last_name"])

    if not profile.phone and not phone:
        errors.append("Phone number is required.")
    if not profile.college and not college:
        errors.append("College is required.")

    for field in custom_fields:
        if field.is_required and not request.POST.get(f"custom_{field.pk}", "").strip():
            errors.append(f'"{field.field_label}" is required.')

    if errors:
        for err in errors:
            messages.error(request, err)
        return render(
            request,
            "registration/register_event.html",
            {
                "event": event,
                "roles": _ROLES,
                "skills": _SKILLS,
                "form_data": request.POST,
                "custom_fields": custom_fields,
                "open_teams": open_teams,
            },
        )

    # Persist profile updates
    if phone:
        profile.phone = phone
    if college:
        profile.college = college
    if branch:
        profile.branch = branch
    if year:
        try:
            profile.year = int(year)
        except ValueError:
            pass
    profile.save()

    # ── Individual registration ──────────────────────────────────────────────
    if reg_type == RegistrationType.INDIVIDUAL:
        try:
            with transaction.atomic():
                registration = Registration.objects.create(
                    event=event,
                    user=request.user,
                    type=RegistrationType.INDIVIDUAL,
                    preferred_role=normalized_role,
                    looking_for_team=looking_for_team,
                    status=RegistrationStatus.CONFIRMED,
                )
                _save_custom_responses(registration, custom_fields, request.POST)
                _save_registration_tech_stacks(registration, selected_skills)
        except IntegrityError:
            messages.info(request, "You are already registered for this event.")
            return redirect("events:event_detail", event_id=event.pk)

        if event.registration_fee and event.registration_fee > 0:
            return redirect("payments:initiate", registration_id=registration.pk)

        _send_confirmation_email(registration)
        messages.success(request, f"Registered for {event.title}! ID: {registration.registration_id}.")
        return redirect("registration:confirmation", registration_id=registration.pk)

    # ── Create a new team ────────────────────────────────────────────────────
    if reg_type == RegistrationType.TEAM and team_action == "create":
        if not team_name:
            messages.error(request, "Team name is required.")
            return render(
                request,
                "registration/register_event.html",
                {
                    "event": event,
                    "roles": _ROLES,
                    "skills": _SKILLS,
                    "form_data": request.POST,
                    "custom_fields": custom_fields,
                    "open_teams": open_teams,
                },
            )

        if not event.allow_team_creation:
            messages.error(request, "Team creation is not enabled for this event.")
            return redirect("events:event_detail", event_id=event.pk)

        from team.models import MemberRole, Team, TeamMembership, TeamStatus

        try:
            with transaction.atomic():
                team = Team.objects.create(
                    event=event,
                    name=team_name,
                    leader=request.user,
                    status=TeamStatus.OPEN,
                )
                TeamMembership.objects.create(
                    team=team,
                    user=request.user,
                    role=normalized_role if normalized_role in MemberRole.values else MemberRole.OTHER,
                )
                registration = Registration.objects.create(
                    event=event,
                    user=request.user,
                    type=RegistrationType.TEAM,
                    team=team,
                    preferred_role=normalized_role,
                    status=RegistrationStatus.CONFIRMED,
                )
                _save_custom_responses(registration, custom_fields, request.POST)
                _save_registration_tech_stacks(registration, selected_skills)
        except IntegrityError:
            messages.error(request, "A team with that name already exists, or you are already registered.")
            return redirect("events:event_detail", event_id=event.pk)

        if event.registration_fee and event.registration_fee > 0:
            return redirect("payments:initiate", registration_id=registration.pk)

        _send_confirmation_email(registration)
        messages.success(request, f'Team "{team_name}" created! ID: {registration.registration_id}.')
        return redirect("registration:confirmation", registration_id=registration.pk)

    # ── Join existing team ───────────────────────────────────────────────────
    if reg_type == RegistrationType.TEAM and team_action == "join" and team_id:
        from core.exceptions import ConflictError
        from core.exceptions import ValidationError as AppValidationError
        from team.models import Team
        from team.services import TeamJoinRequestService

        target_team = Team.objects.filter(pk=team_id, event=event).first()
        if not target_team:
            messages.error(request, "Team not found.")
            return redirect("events:event_detail", event_id=event.pk)

        try:
            TeamJoinRequestService().create_join_request(
                team_id=target_team.pk,
                user=request.user,
                role=normalized_role,
                skills=request.POST.get("skills", "").strip(),
                message=request.POST.get("message", "").strip(),
            )
            messages.success(
                request,
                f'Join request sent to team "{target_team.name}". You will be notified when the leader responds.',
            )
        except (AppValidationError, ConflictError) as exc:
            messages.error(request, str(exc))

        return redirect("events:event_detail", event_id=event.pk)

    messages.error(request, "Invalid registration type.")
    return redirect("events:event_detail", event_id=event.pk)
