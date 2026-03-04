from django.contrib import messages
from django.shortcuts import redirect, render


_REQUIRED_FIELDS = {
    'full_name': 'Full name',
    'email': 'Email',
    'phone': 'Phone',
    'college': 'College',
    'branch': 'Branch / Department',
    'year': 'Year of study',
}

_ROLES = [
    'Frontend Developer',
    'Backend Developer',
    'Full Stack Developer',
    'UI/UX Designer',
    'ML/AI Engineer',
    'DevOps Engineer',
    'Project Manager',
]

_SKILLS = [
    'React', 'Node.js', 'Python', 'Django', 'Flutter',
    'Figma', 'TensorFlow', 'Docker', 'AWS', 'MongoDB',
]

# Stub event data until the Event model is implemented
_STUB_EVENT = {
    'title': 'HackFest 2026',
    'summary': 'Hybrid hackathon with team and individual registration tracks.',
}


def register_event(request, event_id):
    event = dict(_STUB_EVENT, id=event_id)

    if request.method == 'POST':
        reg_type = request.POST.get('type', 'individual')
        errors = []

        # Validate required personal fields
        for field, label in _REQUIRED_FIELDS.items():
            if not request.POST.get(field, '').strip():
                errors.append(f'{label} is required.')

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(
                request,
                'registration/register_event.html',
                {
                    'event': event,
                    'roles': _ROLES,
                    'skills': _SKILLS,
                    'form_data': request.POST,
                },
            )

        # --- Placeholder: save Registration model when implemented ---
        # Registration.objects.create(event_id=event_id, user=request.user, ...)

        messages.success(
            request,
            f'You have successfully registered for {event["title"]}! '
            'Check your email for a confirmation.',
        )
        return redirect('events:home')

    return render(
        request,
        'registration/register_event.html',
        {
            'event': event,
            'roles': _ROLES,
            'skills': _SKILLS,
        },
    )
