from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods


_STUB_TEAM = {
    'name': 'Team Alpha',
    'event': 'HackFest 2026',
    'members_count': '3/4',
}

_MEMBERS = [
    {'name': 'John', 'leader': True, 'stack': 'React, Node.js', 'role': 'Frontend Dev'},
    {'name': 'Jane', 'leader': False, 'stack': 'Python, Django', 'role': 'Backend Dev'},
    {'name': 'Alex', 'leader': False, 'stack': 'Figma, CSS', 'role': 'UI/UX Designer'},
]

_JOIN_REQUESTS = [
    {'name': 'Sara', 'stack': 'TensorFlow, PyTorch', 'role': 'ML/AI Engineer'},
    {'name': 'Arjun', 'stack': 'Kubernetes, AWS', 'role': 'DevOps Engineer'},
]

_COVERAGE = [
    {'label': 'Frontend', 'ok': True},
    {'label': 'Backend', 'ok': True},
    {'label': 'Design', 'ok': True},
    {'label': 'ML/AI', 'ok': False},
    {'label': 'DevOps', 'ok': False},
]


def _context(team_id):
    return {
        'team': dict(_STUB_TEAM, id=team_id),
        'members': _MEMBERS,
        'requests': _JOIN_REQUESTS,
        'coverage': _COVERAGE,
    }


@login_required
@require_http_methods(['GET', 'POST'])
def team_management(request, team_id):
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()

        if not message:
            messages.error(request, 'Message cannot be empty.')
        else:
            # --- Placeholder: save ChatMessage model when implemented ---
            # ChatMessage.objects.create(team_id=team_id, user=request.user, body=message)
            # JS already appends the bubble client-side; server just persists it.
            messages.success(request, 'Message sent.')

        return redirect('team:team_management', team_id=team_id)

    return render(request, 'team/team_management.html', _context(team_id))

