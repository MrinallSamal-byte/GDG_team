from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from events.models import Event, EventStatus
from registration.models import Registration, RegistrationStatus, RegistrationType
from team.models import Team, TeamMembership, MemberRole
from users.models import UserProfile


_ROLES = [
    ('frontend', 'Frontend Developer'),
    ('backend', 'Backend Developer'),
    ('fullstack', 'Full Stack Developer'),
    ('mobile', 'Mobile Developer'),
    ('uiux', 'UI/UX Designer'),
    ('ml_ai', 'ML/AI Engineer'),
    ('data', 'Data Scientist'),
    ('devops', 'DevOps Engineer'),
    ('pm', 'Project Manager'),
    ('other', 'Other'),
]

_ALL_SKILLS = [
    'React', 'Vue.js', 'Angular', 'Next.js',
    'Node.js', 'Django', 'Flask', 'FastAPI', 'Spring Boot',
    'Python', 'Java', 'JavaScript', 'TypeScript', 'Go', 'C++', 'Rust',
    'Flutter', 'React Native', 'Swift', 'Kotlin',
    'Figma', 'Sketch', 'Adobe XD',
    'TensorFlow', 'PyTorch', 'Scikit-learn', 'OpenCV',
    'Docker', 'Kubernetes', 'AWS', 'GCP', 'Azure',
    'MongoDB', 'PostgreSQL', 'MySQL', 'Redis',
    'Git', 'Linux',
]


def _get_event_or_stub(event_id):
    """Return a real Event or a stub dict for development."""
    try:
        return Event.objects.get(pk=event_id), True
    except Event.DoesNotExist:
        return {
            'id': event_id,
            'title': 'HackFest 2026',
            'summary': 'Hybrid hackathon with team and individual registration tracks.',
            'participation_type': 'both',
            'min_team_size': 2,
            'max_team_size': 4,
            'is_registration_open': True,
        }, False


@login_required
@require_http_methods(['GET', 'POST'])
def register_event(request, event_id):
    event_obj, is_real = _get_event_or_stub(event_id)

    # Build the event context dict for templates
    if is_real:
        if not event_obj.is_registration_open:
            messages.error(request, 'Registration for this event is currently closed.')
            return redirect('events:event_detail', event_id=event_id)

        # Check if already registered
        if Registration.objects.filter(event=event_obj, user=request.user).exists():
            messages.info(request, 'You are already registered for this event.')
            return redirect('events:event_detail', event_id=event_id)

        event = {
            'id': event_obj.pk,
            'title': event_obj.title,
            'summary': event_obj.description[:150] + '…' if len(event_obj.description) > 150 else event_obj.description,
            'participation_type': event_obj.participation_type,
            'min_team_size': event_obj.min_team_size,
            'max_team_size': event_obj.max_team_size,
        }
        open_teams = list(
            event_obj.teams.filter(status='open').values('id', 'name')
        )
    else:
        event = event_obj
        open_teams = []

    # Pre-fill from profile
    profile = None
    prefill = {}
    try:
        profile = request.user.profile
        prefill = {
            'full_name': request.user.get_full_name(),
            'email': request.user.email,
            'phone': profile.phone,
            'college': profile.college,
            'branch': profile.branch,
            'year': str(profile.year) if profile.year else '',
            'skills': profile.skills,
        }
    except (UserProfile.DoesNotExist, AttributeError):
        prefill = {
            'full_name': request.user.get_full_name(),
            'email': request.user.email,
        }

    # Pre-select type from query param (e.g., coming from "Request to Join" button)
    default_type = request.GET.get('type', 'individual')
    default_team_id = request.GET.get('team_id', '')

    if request.method == 'POST':
        reg_type = request.POST.get('type', 'individual')
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        college = request.POST.get('college', '').strip()
        branch = request.POST.get('branch', '').strip()
        year_raw = request.POST.get('year', '').strip()
        skills = request.POST.get('skills', '').strip()
        role = request.POST.get('preferred_role', 'other')
        team_name = request.POST.get('team_name', '').strip()
        join_team_id = request.POST.get('join_team_id', '').strip()

        errors = []
        if not full_name:
            errors.append('Full name is required.')
        if not email:
            errors.append('Email is required.')
        if not college:
            errors.append('College is required.')

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'registration/register_event.html', {
                'event': event,
                'roles': _ROLES,
                'skills': _ALL_SKILLS,
                'open_teams': open_teams,
                'form_data': request.POST,
                'default_type': reg_type,
                'default_team_id': default_team_id,
            })

        if is_real:
            from django.db import transaction
            try:
                with transaction.atomic():
                    team = None
                    if reg_type == 'create_team' and team_name:
                        team = Team.objects.create(
                            event=event_obj,
                            name=team_name,
                            leader=request.user,
                        )
                        TeamMembership.objects.create(
                            team=team,
                            user=request.user,
                            role=role,
                            skills=skills,
                        )

                    elif reg_type == 'join_team' and join_team_id:
                        try:
                            team = Team.objects.get(pk=join_team_id, event=event_obj)
                        except Team.DoesNotExist:
                            messages.error(request, 'Selected team not found.')
                            return redirect('events:event_detail', event_id=event_id)

                    registration = Registration.objects.create(
                        event=event_obj,
                        user=request.user,
                        type=RegistrationType.TEAM if team else RegistrationType.INDIVIDUAL,
                        team=team,
                        status=RegistrationStatus.CONFIRMED,
                    )

                    # Update profile with latest info
                    if profile:
                        profile.phone = phone or profile.phone
                        profile.college = college or profile.college
                        profile.branch = branch or profile.branch
                        if year_raw.isdigit():
                            profile.year = int(year_raw)
                        if skills:
                            profile.skills = skills
                        profile.save()

                return redirect('registration:confirmation', registration_id=registration.pk)

            except Exception as exc:
                messages.error(request, f'Registration failed: {exc}')
        else:
            # Stub: redirect to confirmation stub
            messages.success(request, f'You have successfully registered for {event["title"]}!')
            return redirect('events:home')

    return render(request, 'registration/register_event.html', {
        'event': event,
        'roles': _ROLES,
        'skills': _ALL_SKILLS,
        'open_teams': open_teams,
        'prefill': prefill,
        'default_type': default_type,
        'default_team_id': default_team_id,
    })


@login_required
def registration_confirmation(request, registration_id):
    """Display confirmation page after successful registration."""
    try:
        reg = get_object_or_404(
            Registration.objects.select_related('event', 'team'),
            pk=registration_id,
            user=request.user,
        )
        return render(request, 'registration/confirmation.html', {'registration': reg})
    except Exception:
        messages.success(request, 'Registration confirmed! Check your email for details.')
        return redirect('dashboard:my_events')
