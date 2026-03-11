import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from events.models import Event
from users.models import UserProfile

from .models import (
    CustomFormField,
    Registration,
    RegistrationResponse,
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
    "React",
    "Node.js",
    "Python",
    "Django",
    "Flutter",
    "Figma",
    "TensorFlow",
    "Docker",
    "AWS",
    "MongoDB",
]


def _get_or_create_profile(user):
    """Return the user's profile, creating it if necessary."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def _normalize_registration_choice(post_data):
    """Map template radio values to the normalized registration type and action."""
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
    """Return a de-duplicated, ordered list of selected skills from the form."""
    raw_skills = post_data.get("skills", "").strip()
    if not raw_skills:
        return []

    seen = set()
    selected_skills = []
    for skill in [item.strip() for item in raw_skills.split(",") if item.strip()]:
        lowered = skill.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        selected_skills.append(skill)
    return selected_skills


def _normalize_member_role(selected_role):
    """Convert a submitted role label into the team role enum value."""
    if not selected_role:
        return "other"
    return _ROLE_VALUE_MAP.get(
        selected_role,
        selected_role if selected_role in _ROLE_VALUE_MAP.values() else "other",
    )


def _save_registration_tech_stacks(registration, selected_skills):
    """Persist per-event tech stacks for the registration."""
    if not selected_skills:
        return

    RegistrationTechStack.objects.bulk_create(
        [
            RegistrationTechStack(
                registration=registration,
                tech_name=skill,
                is_primary=index < 3,
            )
            for index, skill in enumerate(selected_skills)
        ],
        ignore_conflicts=True,
    )


def _send_confirmation_email(registration):
    """Send a registration confirmation email; errors are logged, not re-raised."""
    try:
        send_mail(
            subject=f"Registration Confirmed — {registration.event.title}",
            message=(
                f"Hi {registration.user.first_name or registration.user.username},\n\n"
                f'You have successfully registered for "{registration.event.title}".\n'
                f"Your Registration ID: {registration.registration_id}\n\n"
                f'Event Date: {registration.event.event_start.strftime("%B %d, %Y")}\n'
                f"Good luck!\n\nTeam CampusArena"
            ),
            from_email=None,  # uses DEFAULT_FROM_EMAIL
            recipient_list=[registration.user.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error(
            "Failed to send confirmation email for registration %s: %s",
            registration.registration_id,
            exc,
            exc_info=True,
        )


def _save_custom_responses(registration, custom_fields, post_data):
    """Persist RegistrationResponse objects for organizer-defined fields."""
    responses = []
    for field in custom_fields:
        key = f"custom_{field.pk}"
        value = post_data.get(key, "").strip()
        responses.append(
            RegistrationResponse(
                registration=registration,
                field=field,
                response_value=value,
            )
        )
    if responses:
        RegistrationResponse.objects.bulk_create(responses, ignore_conflicts=True)


@login_required
@require_http_methods(["GET"])
def registration_confirmation(request, registration_id):
    """Render the post-registration confirmation page for the owning user."""
    registrations = Registration.objects.select_related("event", "team")
    lookup = {"pk": registration_id}
    if not request.user.is_staff:
        lookup["user"] = request.user

    registration = get_object_or_404(registrations, **lookup)
    return render(
        request,
        "registration/confirmation.html",
        {
            "registration": registration,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def register_event(request, event_id):
    """Register the current user for an event (solo or team)."""
    event = get_object_or_404(Event, pk=event_id)

    # Block if already registered
    existing = Registration.objects.filter(event=event, user=request.user).first()
    if existing:
        messages.info(request, "You are already registered for this event.")
        return redirect("events:event_detail", event_id=event.pk)

    # Block if registration is not open
    if not event.is_registration_open:
        messages.warning(request, "Registration is not currently open for this event.")
        return redirect("events:event_detail", event_id=event.pk)

    custom_fields = CustomFormField.objects.filter(event=event).order_by(
        "display_order"
    )

    # Open teams for team events (used for "join a team" option)
    open_teams = []
    if event.participation_type in ("team", "both"):
        from django.db.models import Count

        open_teams = (
            event.teams.filter(
                status="open",
                is_deleted=False,
            )
            .annotate(current_members=Count("memberships"))
            .select_related("leader")
        )

    if request.method == "POST":
        reg_type, team_action = _normalize_registration_choice(request.POST)
        team_id = request.POST.get("team_id", "").strip()
        preferred_role = request.POST.get("preferred_role", "").strip()
        normalized_role = _normalize_member_role(preferred_role)
        looking_for_team = request.POST.get("looking_for_team") == "on"
        team_name = request.POST.get("team_name", "").strip()
        selected_skills = _extract_selected_skills(request.POST)

        if (
            event.participation_type == "individual"
            and reg_type == RegistrationType.TEAM
        ):
            messages.error(request, "This event only allows individual registrations.")
            return redirect("events:event_detail", event_id=event.pk)
        if (
            event.participation_type == "team"
            and reg_type == RegistrationType.INDIVIDUAL
        ):
            messages.error(request, "This event requires team-based registration.")
            return redirect("events:event_detail", event_id=event.pk)

        # Update profile if provided
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

        # Validate required custom fields
        for field in custom_fields:
            if field.is_required:
                key = f"custom_{field.pk}"
                val = request.POST.get(key, "").strip()
                if not val:
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

        # ── Individual registration ────────────────────────────────────────
        if reg_type == RegistrationType.INDIVIDUAL:
            try:
                with transaction.atomic():
                    registration = Registration.objects.create(
                        event=event,
                        user=request.user,
                        type=RegistrationType.INDIVIDUAL,
                        preferred_role=normalized_role,
                        looking_for_team=looking_for_team,
                        status="confirmed",
                    )
                    _save_custom_responses(registration, custom_fields, request.POST)
                    _save_registration_tech_stacks(registration, selected_skills)
            except IntegrityError:
                messages.info(request, "You are already registered for this event.")
                return redirect("events:event_detail", event_id=event.pk)

            _send_confirmation_email(registration)
            logger.info(
                "Individual registration %s created for event %d by user %d",
                registration.registration_id,
                event.pk,
                request.user.pk,
            )
            messages.success(
                request,
                f"Registered for {event.title}! ID: {registration.registration_id}.",
            )
            return redirect(
                "registration:confirmation", registration_id=registration.pk
            )

        # ── Create a new team ──────────────────────────────────────────────
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
                        role=(
                            normalized_role
                            if normalized_role in MemberRole.values
                            else MemberRole.OTHER
                        ),
                    )
                    registration = Registration.objects.create(
                        event=event,
                        user=request.user,
                        type=RegistrationType.TEAM,
                        team=team,
                        preferred_role=normalized_role,
                        status="confirmed",
                    )
                    _save_custom_responses(registration, custom_fields, request.POST)
                    _save_registration_tech_stacks(registration, selected_skills)
            except IntegrityError:
                messages.error(
                    request,
                    "A team with that name already exists, or you are already registered.",
                )
                return redirect("events:event_detail", event_id=event.pk)

            _send_confirmation_email(registration)
            logger.info(
                "Team '%s' created + registration %s for event %d by user %d",
                team_name,
                registration.registration_id,
                event.pk,
                request.user.pk,
            )
            messages.success(
                request,
                f'Team "{team_name}" created and you are registered! ID: {registration.registration_id}.',
            )
            return redirect(
                "registration:confirmation", registration_id=registration.pk
            )

        # ── Send join request to an existing team ─────────────────────────
        if reg_type == RegistrationType.TEAM and team_action == "join" and team_id:
            from core.exceptions import ConflictError
            from core.exceptions import ValidationError as AppValidationError
            from team.models import Team
            from team.services import TeamJoinRequestService

            target_team = Team.objects.filter(pk=team_id, event=event).first()
            if not target_team:
                messages.error(request, "Team not found.")
                return redirect("events:event_detail", event_id=event.pk)

            msg = request.POST.get("message", "").strip()
            skills = request.POST.get("skills", "").strip()

            try:
                svc = TeamJoinRequestService()
                svc.create_join_request(
                    team_id=target_team.pk,
                    user=request.user,
                    role=normalized_role,
                    skills=skills,
                    message=msg,
                )
                messages.success(
                    request,
                    f'Join request sent to team "{target_team.name}". '
                    "You will be notified when the team leader responds.",
                )
            except (AppValidationError, ConflictError) as exc:
                messages.error(request, str(exc))

            return redirect("events:event_detail", event_id=event.pk)

        # Fallback — should not normally be reached
        messages.error(request, "Invalid registration type.")
        return redirect("events:event_detail", event_id=event.pk)

    return render(
        request,
        "registration/register_event.html",
        {
            "event": event,
            "roles": _ROLES,
            "skills": _SKILLS,
            "custom_fields": custom_fields,
            "open_teams": open_teams,
            "form_data": request.POST,
        },
    )
