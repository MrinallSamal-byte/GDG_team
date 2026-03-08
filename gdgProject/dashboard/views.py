from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from users.models import UserProfile


def _get_profile(user):
    """Return UserProfile, creating one if missing."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@login_required
def user_dashboard(request):
    my_events = [
        {'title': 'HackFest 2026', 'status': 'Registered'},
        {'title': 'Design Jam Pro', 'status': 'Team Pending'},
        {'title': 'QuizMania', 'status': 'Completed'},
    ]
    my_teams = [
        {'name': 'Team Alpha', 'event': 'HackFest 2026', 'role': 'Frontend Dev'},
        {'name': 'PixelSmiths', 'event': 'Design Jam Pro', 'role': 'UI/UX'},
    ]
    notifications = [
        'Your join request to Team Alpha was accepted.',
        'New announcement: HackFest mentor AMA at 6 PM.',
        'Reminder: Registration deadline ends in 12 hours.',
    ]
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
        'events_joined': 8,
        'teams': 3,
        'certificates': 5,
    }
    return render(request, 'dashboard/my_profile.html', {
        'profile': profile_data,
        'stats': stats,
        'current_page': 'profile',
    })


@login_required
def my_events(request):
    events = [
        {'id': 1, 'title': 'HackFest 2026', 'category': 'Hackathon', 'mode': 'Hybrid', 'date': 'Apr 15–17, 2026', 'status': 'Registered', 'team': 'Team Alpha', 'role': 'Frontend Dev'},
        {'id': 2, 'title': 'Design Jam Pro', 'category': 'Design', 'mode': 'Online', 'date': 'May 5, 2026', 'status': 'Team Pending', 'team': 'PixelSmiths', 'role': 'UI/UX'},
        {'id': 3, 'title': 'QuizMania', 'category': 'Quiz', 'mode': 'Offline', 'date': 'Mar 20, 2026', 'status': 'Completed', 'team': None, 'role': None},
        {'id': 4, 'title': 'CloudSprint Workshop', 'category': 'Workshop', 'mode': 'Online', 'date': 'Jun 10, 2026', 'status': 'Registered', 'team': None, 'role': None},
    ]
    return render(request, 'dashboard/my_events.html', {
        'events': events,
        'current_page': 'events',
    })


@login_required
def my_teams(request):
    teams = [
        {
            'name': 'Team Alpha',
            'event': 'HackFest 2026',
            'role': 'Frontend Dev',
            'members': ['Arjun S.', 'Priya V.', 'Rahul M.', 'Student User'],
        },
        {
            'name': 'PixelSmiths',
            'event': 'Design Jam Pro',
            'role': 'UI/UX Lead',
            'members': ['Sneha K.', 'Student User', 'Aman P.'],
        },
        {
            'name': 'CodeCrafters',
            'event': 'CloudSprint Workshop',
            'role': 'Backend Dev',
            'members': ['Student User', 'Divya R.'],
        },
    ]
    return render(request, 'dashboard/my_teams.html', {
        'teams': teams,
        'current_page': 'teams',
    })


@login_required
def pending_requests(request):
    incoming = [
        {'from': 'Kavya Nair', 'team': 'Team Alpha', 'event': 'HackFest 2026'},
        {'from': 'Rohan Gupta', 'team': 'CodeCrafters', 'event': 'CloudSprint Workshop'},
    ]
    outgoing = [
        {'team': 'DevSquad', 'event': 'HackFest 2026', 'status': 'Pending'},
        {'team': 'Team Phoenix', 'event': 'Design Jam Pro', 'status': 'Accepted'},
        {'team': 'ByteBusters', 'event': 'QuizMania', 'status': 'Declined'},
    ]
    return render(request, 'dashboard/pending_requests.html', {
        'incoming': incoming,
        'outgoing': outgoing,
        'current_page': 'requests',
    })


@login_required
def notifications_view(request):
    notifications = [
        {'message': 'Your join request to Team Alpha was accepted.', 'time': '2 minutes ago', 'type': 'success', 'read': False},
        {'message': 'New announcement: HackFest mentor AMA at 6 PM.', 'time': '15 minutes ago', 'type': 'info', 'read': False},
        {'message': 'Reminder: Registration deadline ends in 12 hours.', 'time': '1 hour ago', 'type': 'warning', 'read': False},
        {'message': 'Your team PixelSmiths was created successfully.', 'time': '3 hours ago', 'type': 'success', 'read': True},
        {'message': 'Welcome to CampusArena! Complete your profile to get started.', 'time': '1 day ago', 'type': 'info', 'read': True},
        {'message': 'Rohan Gupta requested to join CodeCrafters.', 'time': '1 day ago', 'type': 'info', 'read': True},
        {'message': 'QuizMania results are out — you ranked #12!', 'time': '2 days ago', 'type': 'success', 'read': True},
    ]
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

def find_teammates(request):
    return render(request, "dashboard/find_teammates.html", {
        "current_page": "find_teammates"
    })

@login_required
@require_http_methods(["GET", "POST"])
def edit_profile(request):
    profile = _get_profile(request.user)

    if request.method == "POST":
        profile.phone = request.POST.get("phone")
        profile.github = request.POST.get("github")
        profile.linkedin = request.POST.get("linkedin")
        profile.bio = request.POST.get("bio")
        profile.college = request.POST.get("college")
        profile.branch = request.POST.get("branch")
        profile.year = request.POST.get("year")

        profile.save()

        messages.success(request, "Profile updated successfully!")
        return redirect("dashboard:my_profile")

    return render(request, "dashboard/edit_profile.html", {
        "profile": profile,
        "current_page": "profile"
    })