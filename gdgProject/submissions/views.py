import logging

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from events.models import Event

from .models import Submission, SubmissionStatus

logger = logging.getLogger("campusarena.submissions")


def _get_team_for_user(user, event):
    """Return the user's active team for this event, or None."""
    from team.models import TeamMembership

    membership = TeamMembership.objects.filter(
        user=user, team__event=event, team__is_deleted=False
    ).select_related("team").first()
    return membership.team if membership else None


def _get_existing_submission(user, event, team):
    """Return the existing submission for this user/team on this event, or None."""
    if team:
        return Submission.objects.filter(event=event, team=team).first()
    return Submission.objects.filter(event=event, user=user, team__isnull=True).first()


@login_required
@require_http_methods(["GET", "POST"])
def submit_project(request, event_id):
    """Create or update a project submission for an event."""
    event = get_object_or_404(Event, pk=event_id)
    team = _get_team_for_user(request.user, event)

    # Deadline check
    deadline = event.submission_deadline or event.event_end
    if deadline and timezone.now() > deadline:
        messages.error(request, "The submission deadline for this event has passed.")
        return redirect("events:event_detail", event_id=event.pk)

    existing = _get_existing_submission(request.user, event, team)

    if request.method == "GET":
        return render(
            request,
            "submissions/submit.html",
            {"event": event, "team": team, "existing": existing},
        )

    # POST
    title = request.POST.get("title", "").strip()
    description = request.POST.get("description", "").strip()
    project_url = request.POST.get("project_url", "").strip()
    presentation_url = request.POST.get("presentation_url", "").strip()
    is_final = request.POST.get("submit_final") == "1"

    if not title:
        messages.error(request, "Project title is required.")
        return render(
            request,
            "submissions/submit.html",
            {"event": event, "team": team, "existing": existing, "form_data": request.POST},
        )

    if existing:
        existing.title = title
        existing.description = description
        existing.project_url = project_url
        existing.presentation_url = presentation_url
        if "file_upload" in request.FILES:
            existing.file_upload = request.FILES["file_upload"]
        if is_final and existing.status != SubmissionStatus.SUBMITTED:
            existing.status = SubmissionStatus.SUBMITTED
            existing.submitted_at = timezone.now()
        existing.save()
        sub = existing
    else:
        sub = Submission(
            event=event,
            user=request.user,
            team=team,
            title=title,
            description=description,
            project_url=project_url,
            presentation_url=presentation_url,
        )
        if "file_upload" in request.FILES:
            sub.file_upload = request.FILES["file_upload"]
        if is_final:
            sub.status = SubmissionStatus.SUBMITTED
            sub.submitted_at = timezone.now()
        sub.save()

    action = "submitted" if is_final else "saved as draft"
    logger.info(
        "Submission %d %s by user %d for event %d",
        sub.pk, action, request.user.pk, event.pk,
    )
    messages.success(request, f'Project "{title}" {action} successfully.')
    return redirect("submissions:my_submission", event_id=event.pk)


@login_required
@require_GET
def my_submission(request, event_id):
    """View the current user's submission for an event."""
    event = get_object_or_404(Event, pk=event_id)
    team = _get_team_for_user(request.user, event)
    submission = _get_existing_submission(request.user, event, team)

    return render(
        request,
        "submissions/my_submission.html",
        {"event": event, "submission": submission, "team": team},
    )


@staff_member_required
@require_GET
def review_submissions(request, event_id):
    """Organiser view — list all submissions for an event."""
    event = get_object_or_404(Event.all_objects, pk=event_id, created_by=request.user)
    submissions = (
        Submission.objects.filter(event=event)
        .select_related("user", "team")
        .order_by("-submitted_at", "-created_at")
    )

    return render(
        request,
        "submissions/review.html",
        {"event": event, "submissions": submissions},
    )


@staff_member_required
@require_POST
def score_submission(request, submission_id):
    """Organiser scores a submission and adds judge notes."""
    sub = get_object_or_404(
        Submission.objects.select_related("event"),
        pk=submission_id,
    )

    if sub.event.created_by != request.user and not request.user.is_superuser:
        messages.error(request, "Permission denied.")
        return redirect("eventManagement:organizer_dashboard")

    score_raw = request.POST.get("score", "").strip()
    notes = request.POST.get("judge_notes", "").strip()

    try:
        sub.score = float(score_raw) if score_raw else None
    except ValueError:
        messages.error(request, "Score must be a number.")
        return redirect("submissions:review", event_id=sub.event.pk)

    sub.judge_notes = notes
    sub.status = SubmissionStatus.REVIEWED
    sub.save(update_fields=["score", "judge_notes", "status", "updated_at"])

    messages.success(request, f'Submission "{sub.title}" scored.')
    return redirect("submissions:review", event_id=sub.event.pk)
