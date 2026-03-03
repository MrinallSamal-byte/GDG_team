from django.shortcuts import render

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
		},
	)
