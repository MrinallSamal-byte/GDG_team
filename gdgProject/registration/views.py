from django.shortcuts import render

def register_event(request, event_id):
	event = {
		'id': event_id,
		'title': 'HackFest 2026',
		'summary': 'Hybrid hackathon with team and individual registration tracks.',
	}
	roles = [
		'Frontend Developer',
		'Backend Developer',
		'Full Stack Developer',
		'UI/UX Designer',
		'ML/AI Engineer',
		'DevOps Engineer',
		'Project Manager',
	]
	skills = [
		'React',
		'Node.js',
		'Python',
		'Django',
		'Flutter',
		'Figma',
		'TensorFlow',
		'Docker',
		'AWS',
		'MongoDB',
	]
	return render(
		request,
		'registration/register_event.html',
		{
			'event': event,
			'roles': roles,
			'skills': skills,
		},
	)
