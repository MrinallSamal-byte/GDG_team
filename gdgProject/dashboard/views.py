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
			'current_page': 'overview',
		},
	)


def my_profile(request):
	profile = {
		'name': 'Student User',
		'email': 'student@campusarena.in',
		'phone': '+91 98765 43210',
		'college': 'VIT Vellore',
		'branch': 'CSE',
		'year': '3rd Year',
		'github': 'github.com/studentuser',
		'linkedin': 'linkedin.com/in/studentuser',
		'bio': 'Passionate full-stack developer and hackathon enthusiast. Love building products that solve real problems.',
		'skills': ['React', 'Python', 'Django', 'Figma', 'AWS'],
	}
	stats = {
		'events_joined': 8,
		'teams': 3,
		'certificates': 5,
	}
	return render(request, 'dashboard/my_profile.html', {
		'profile': profile,
		'stats': stats,
		'current_page': 'profile',
	})


def my_events(request):
	events = [
		{'id': 1, 'title': 'HackFest 2026', 'category': 'Hackathon', 'mode': 'Hybrid', 'date': 'Apr 15–17, 2026', 'status': 'Registered', 'team': 'Team Alpha', 'role': 'Frontend Dev'},
		{'id': 2, 'title': 'Design Jam Pro', 'category': 'Design', 'mode': 'Online', 'date': 'May 5, 2026', 'status': 'Team Pending', 'team': 'PixelSmiths', 'role': 'UI/UX'},
		{'id': 3, 'title': 'QuizMania', 'category': 'Quiz', 'mode': 'Offline', 'date': 'Mar 20, 2026', 'status': 'Completed', 'team': None, 'role': None},
		{'id': 1, 'title': 'CloudSprint Workshop', 'category': 'Workshop', 'mode': 'Online', 'date': 'Jun 10, 2026', 'status': 'Registered', 'team': None, 'role': None},
	]
	return render(request, 'dashboard/my_events.html', {
		'events': events,
		'current_page': 'events',
	})


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


def settings_view(request):
	return render(request, 'dashboard/settings.html', {
		'current_page': 'settings',
	})
