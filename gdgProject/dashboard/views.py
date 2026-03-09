from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from events.models import Event
from notification.models import Notification
from registration.models import Registration
from team.models import JoinRequest, JoinRequestStatus, Team, TeamMembership
from users.models import UserProfile


def _get_profile(user):
    """Return UserProfile, creating one if missing."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@login_required
def user_dashboard(request):
    # Recent registrations
    my_regs = Registration.objects.filter(user=request.user).select_related('event')[:5]
    my_events = [
        {
            'title': reg.event.title,
            'status': reg.get_status_display(),
            'id': reg.event.pk,
        }
        for reg in my_regs
    ]

    # Teams
    my_memberships = TeamMembership.objects.filter(
        user=request.user, team__is_deleted=False,
    ).select_related('team', 'team__event')[:5]
    my_teams = [
        {
            'name': m.team.name,
            'event': m.team.event.title,
            'role': m.get_role_display(),
            'id': m.team.pk,
        }
        for m in my_memberships
    ]

    # Recent notifications
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]

    return render(
        request,
        'dashboard/user_dashboard.html',
        {
            'my_events': my_events,
            'my_teams': my_teams,
            'notifications': notifications,
            'current_page': 'overview',
        },
    )


@login_required
def my_profile(request):
    profile = _get_profile(request.user)
    user = request.user

    profile_data = {
        'name': user.get_full_name() or user.username,
        'email': user.email,
        'phone': profile.phone or 'Not set',
        'college': profile.college or 'Not set',
        'branch': profile.branch or 'Not set',
        'year': profile.year_display or 'Not set',
        'github': profile.github or 'Not set',
        'linkedin': profile.linkedin or 'Not set',
        'bio': profile.bio or 'No bio yet. Click Edit Profile to add one.',
        'skills': profile.skills_list or [],
    }
    stats = {
        'events_joined': Registration.objects.filter(user=user).count(),
        'teams': TeamMembership.objects.filter(user=user, team__is_deleted=False).count(),
        'certificates': 0,
    }
    return render(request, 'dashboard/my_profile.html', {
        'profile': profile_data,
        'stats': stats,
        'current_page': 'profile',
    })


@login_required
def my_events(request):
    registrations = Registration.objects.filter(
        user=request.user
    ).select_related('event', 'team')

    events = []
    for reg in registrations:
        membership = TeamMembership.objects.filter(
            user=request.user, team__event=reg.event, team__is_deleted=False,
        ).select_related('team').first()

        events.append({
            'id': reg.event.pk,
            'title': reg.event.title,
            'category': reg.event.get_category_display(),
            'mode': reg.event.get_mode_display(),
            'date': reg.event.event_start,
            'status': reg.get_status_display(),
            'team': membership.team.name if membership else None,
            'role': membership.get_role_display() if membership else None,
        })

    return render(request, 'dashboard/my_events.html', {
        'events': events,
        'current_page': 'events',
    })


@login_required
def my_teams(request):
    memberships = TeamMembership.objects.filter(
        user=request.user, team__is_deleted=False,
    ).select_related('team', 'team__event')

    teams = []
    for m in memberships:
        members = TeamMembership.objects.filter(
            team=m.team
        ).select_related('user')
        teams.append({
            'id': m.team.pk,
            'name': m.team.name,
            'event': m.team.event.title,
            'role': m.get_role_display(),
            'members': [
                mem.user.get_full_name() or mem.user.username
                for mem in members
            ],
        })

    return render(request, 'dashboard/my_teams.html', {
        'teams': teams,
        'current_page': 'teams',
    })


@login_required
def pending_requests(request):
    # Incoming: requests to teams the user leads
    led_teams = Team.objects.filter(leader=request.user, is_deleted=False)
    incoming = JoinRequest.objects.filter(
        team__in=led_teams,
        status=JoinRequestStatus.PENDING,
    ).select_related('user', 'team', 'team__event')

    incoming_data = [
        {
            'id': jr.pk,
            'from': jr.user.get_full_name() or jr.user.username,
            'team': jr.team.name,
            'event': jr.team.event.title,
        }
        for jr in incoming
    ]

    # Outgoing: requests the user has sent
    outgoing = JoinRequest.objects.filter(
        user=request.user,
    ).select_related('team', 'team__event').order_by('-created_at')[:20]

    outgoing_data = [
        {
            'team': jr.team.name,
            'event': jr.team.event.title,
            'status': jr.get_status_display(),
        }
        for jr in outgoing
    ]

    return render(request, 'dashboard/pending_requests.html', {
        'incoming': incoming_data,
        'outgoing': outgoing_data,
        'current_page': 'requests',
    })


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:30]

    return render(request, 'dashboard/notifications.html', {
        'notifications': notifications,
        'current_page': 'notifications',
    })


@login_required
@require_http_methods(['GET', 'POST'])
def settings_view(request):
    profile = _get_profile(request.user)

    if request.method == 'POST':
        display_name = request.POST.get('display_name', '').strip()
        email = request.POST.get('email', '').strip()

        if display_name:
            parts = display_name.split(' ', 1)
            request.user.first_name = parts[0]
            request.user.last_name = parts[1] if len(parts) > 1 else ''
            request.user.save(update_fields=['first_name', 'last_name'])

        if email and email != request.user.email:
            from django.contrib.auth.models import User
            if User.objects.filter(email=email).exclude(pk=request.user.pk).exists():
                messages.error(request, 'That email is already in use by another account.')
            else:
                request.user.email = email
                request.user.save(update_fields=['email'])

        messages.success(request, 'Settings saved successfully!')
        return render(request, 'dashboard/settings.html', {
            'current_page': 'settings',
            'profile': profile,
        })

    return render(request, 'dashboard/settings.html', {
        'current_page': 'settings',
        'profile': profile,
    })

<<<<<<< HEAD
def find_teammates(request):
    return render(request, "dashboard/find_teammates.html", {
        "current_page": "find_teammates"
    })

=======

@login_required
def find_teammates(request):
    # Find users looking for teams
    looking = Registration.objects.filter(
        looking_for_team=True,
    ).select_related('user', 'user__profile', 'event')[:50]

    return render(request, "dashboard/find_teammates.html", {
        "current_page": "find_teammates",
        "looking_users": looking,
    })


>>>>>>> 53c2e5801508465340b5156bfa0cf9c7a645481a
@login_required
@require_http_methods(["GET", "POST"])
def edit_profile(request):
    profile = _get_profile(request.user)

    if request.method == "POST":
<<<<<<< HEAD
        profile.phone = request.POST.get("phone")
        profile.github = request.POST.get("github")
        profile.linkedin = request.POST.get("linkedin")
        profile.bio = request.POST.get("bio")
        profile.college = request.POST.get("college")
        profile.branch = request.POST.get("branch")
        profile.year = request.POST.get("year")
=======
        profile.phone = request.POST.get("phone", "").strip()
        profile.github = request.POST.get("github", "").strip()
        profile.linkedin = request.POST.get("linkedin", "").strip()
        profile.bio = request.POST.get("bio", "").strip()
        profile.college = request.POST.get("college", "").strip()
        profile.branch = request.POST.get("branch", "").strip()

        year_val = request.POST.get("year", "").strip()
        if year_val:
            try:
                year_int = int(year_val)
                if 1 <= year_int <= 6:
                    profile.year = year_int
                else:
                    messages.error(request, "Year must be between 1 and 6.")
                    return render(request, "dashboard/edit_profile.html", {
                        "profile": profile,
                        "current_page": "profile",
                    })
            except ValueError:
                messages.error(request, "Year must be a number.")
                return render(request, "dashboard/edit_profile.html", {
                    "profile": profile,
                    "current_page": "profile",
                })
        else:
            profile.year = None

        skills = request.POST.get("skills", "").strip()
        if skills:
            profile.skills = skills
>>>>>>> 53c2e5801508465340b5156bfa0cf9c7a645481a

        profile.save()

        messages.success(request, "Profile updated successfully!")
        return redirect("dashboard:my_profile")

    return render(request, "dashboard/edit_profile.html", {
        "profile": profile,
<<<<<<< HEAD
        "current_page": "profile"
=======
        "current_page": "profile",
>>>>>>> 53c2e5801508465340b5156bfa0cf9c7a645481a
    })