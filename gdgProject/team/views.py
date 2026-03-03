from django.shortcuts import render

def team_management(request, team_id):
	team = {
		'id': team_id,
		'name': 'Team Alpha',
		'event': 'HackFest 2026',
		'members_count': '3/4',
	}
	members = [
		{'name': 'John', 'leader': True, 'stack': 'React, Node.js', 'role': 'Frontend Dev'},
		{'name': 'Jane', 'leader': False, 'stack': 'Python, Django', 'role': 'Backend Dev'},
		{'name': 'Alex', 'leader': False, 'stack': 'Figma, CSS', 'role': 'UI/UX Designer'},
	]
	requests = [
		{'name': 'Sara', 'stack': 'TensorFlow, PyTorch', 'role': 'ML/AI Engineer'},
		{'name': 'Arjun', 'stack': 'Kubernetes, AWS', 'role': 'DevOps Engineer'},
	]
	coverage = [
		{'label': 'Frontend', 'ok': True},
		{'label': 'Backend', 'ok': True},
		{'label': 'Design', 'ok': True},
		{'label': 'ML/AI', 'ok': False},
		{'label': 'DevOps', 'ok': False},
	]
	return render(
		request,
		'team/team_management.html',
		{
			'team': team,
			'members': members,
			'requests': requests,
			'coverage': coverage,
		},
	)
