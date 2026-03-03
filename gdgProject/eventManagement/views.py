from django.shortcuts import render

def organizer_dashboard(request):
	analytics = {
		'total_registrations': 1248,
		'team_vs_solo': '68% Team / 32% Solo',
		'top_stack': 'Python, React, Figma',
		'active_events': 12,
	}
	participants = [
		{'name': 'Priya Verma', 'event': 'HackFest 2026', 'status': 'Confirmed'},
		{'name': 'Aman Patel', 'event': 'CloudSprint Workshop', 'status': 'Pending'},
		{'name': 'Ritika Das', 'event': 'Design Jam Pro', 'status': 'Confirmed'},
	]
	return render(
		request,
		'eventManagement/organizer_dashboard.html',
		{
			'analytics': analytics,
			'participants': participants,
		},
	)


def create_event(request):
	return render(request, 'eventManagement/create_event.html')
