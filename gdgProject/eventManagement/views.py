from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods


_ANALYTICS = {
    'total_registrations': 1248,
    'team_vs_solo': '68% Team / 32% Solo',
    'top_stack': 'Python, React, Figma',
    'active_events': 12,
}

_PARTICIPANTS = [
    {'name': 'Priya Verma', 'event': 'HackFest 2026', 'status': 'Confirmed'},
    {'name': 'Aman Patel', 'event': 'CloudSprint Workshop', 'status': 'Pending'},
    {'name': 'Ritika Das', 'event': 'Design Jam Pro', 'status': 'Confirmed'},
]


@staff_member_required
def organizer_dashboard(request):
    return render(
        request,
        'eventManagement/organizer_dashboard.html',
        {
            'analytics': _ANALYTICS,
            'participants': _PARTICIPANTS,
        },
    )


@staff_member_required
@require_http_methods(['GET', 'POST'])
def create_event(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', '').strip()
        mode = request.POST.get('mode', '').strip()
        start_date = request.POST.get('start_date', '').strip()
        end_date = request.POST.get('end_date', '').strip()
        description = request.POST.get('description', '').strip()

        errors = []
        if not title:
            errors.append('Event title is required.')
        if not category:
            errors.append('Please select a category.')
        if not mode:
            errors.append('Please select an event mode.')
        if not start_date:
            errors.append('Start date is required.')
        if not end_date:
            errors.append('End date is required.')
        if start_date and end_date and start_date > end_date:
            errors.append('End date must be on or after the start date.')
        if not description:
            errors.append('Event description is required.')

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(
                request,
                'eventManagement/create_event.html',
                {'form_data': request.POST},
            )

        # --- Placeholder: save Event model when implemented ---
        # Event.objects.create(title=title, category=category, ...)

        messages.success(request, f'"{title}" has been created successfully!')
        return redirect('eventManagement:organizer_dashboard')

    return render(request, 'eventManagement/create_event.html')

