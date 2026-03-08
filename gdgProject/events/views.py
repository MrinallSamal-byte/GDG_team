from django.shortcuts import render

def home(request):
	featured_events = [
		{
			'id': 1,
			'title': 'HackFest 2026',
			'category': 'Hackathon',
			'mode': 'Hybrid',
			'date': 'Apr 18-20, 2026',
			'prize': '₹2,50,000',
			'status': 'Open',
			'spots': '124/300',
		},
		{
			'id': 2,
			'title': 'CloudSprint Workshop',
			'category': 'Workshop',
			'mode': 'Online',
			'date': 'Mar 22, 2026',
			'prize': 'Certificates + Swag',
			'status': 'Open',
			'spots': '218/500',
		},
		{
			'id': 3,
			'title': 'Design Jam Pro',
			'category': 'Design Challenge',
			'mode': 'Offline',
			'date': 'Apr 2, 2026',
			'prize': '₹75,000',
			'status': 'Closing Soon',
			'spots': '95/100',
		},
	]

	event_grid = [
		{
			'id': 1,
			'title': 'HackFest 2026',
			'category': 'Hackathon',
			'date': 'Apr 18-20',
			'mode': 'Hybrid',
			'type': 'Team',
			'prize': '₹2,50,000',
			'status': 'Open',
		},
		{
			'id': 2,
			'title': 'AlgoRush',
			'category': 'Coding Contest',
			'date': 'Mar 27',
			'mode': 'Online',
			'type': 'Individual',
			'prize': '₹40,000',
			'status': 'Open',
		},
		{
			'id': 3,
			'title': 'PitchCraft',
			'category': 'Case Study',
			'date': 'Apr 5',
			'mode': 'Offline',
			'type': 'Both',
			'prize': '₹1,00,000',
			'status': 'Open',
		},
		{
			'id': 4,
			'title': 'QuizMania',
			'category': 'Quiz',
			'date': 'Mar 19',
			'mode': 'Online',
			'type': 'Individual',
			'prize': '₹15,000',
			'status': 'Closed',
		},
		{
			'id': 5,
			'title': 'BuildOps Sprint',
			'category': 'Workshop',
			'date': 'Apr 11',
			'mode': 'Hybrid',
			'type': 'Team',
			'prize': 'Goodies + Internship',
			'status': 'Open',
		},
		{
			'id': 6,
			'title': 'VisionX AI Challenge',
			'category': 'Ideathon',
			'date': 'Apr 29',
			'mode': 'Offline',
			'type': 'Team',
			'prize': '₹1,20,000',
			'status': 'Open',
		},
	]
	return render(
		request,
		'events/home.html',
		{
			'featured_events': featured_events,
			'event_grid': event_grid,
		},
	)


def event_detail(request, event_id):
	event = {
		'id': event_id,
		'title': 'HackFest 2026',
		'category': 'Hackathon',
		'mode': 'Hybrid',
		'timeline': 'Apr 18-20, 2026',
		'registration': '124/300 spots filled',
		'countdown': '12d 05h 28m',
		'description': (
			'A 36-hour campus hackathon focused on solving real student-life '
			'and sustainability problems.'
		),
	}
	rounds = [
		{'name': 'Round 1: Idea Screening', 'date': 'Apr 10', 'status': 'Upcoming'},
		{'name': 'Round 2: Prototype Review', 'date': 'Apr 18', 'status': 'Upcoming'},
		{'name': 'Round 3: Final Demo', 'date': 'Apr 20', 'status': 'Upcoming'},
	]
	participants = [
		{'name': 'Priya Verma', 'college': 'NIT Rourkela'},
		{'name': 'Rahul S.', 'college': 'KIIT University'},
		{'name': 'Neha Kulkarni', 'college': 'VIT Chennai'},
	]
	teams_open = [
		{'name': 'Team Alpha', 'members': '3/4', 'needs': 'ML/AI'},
		{'name': 'Binary Builders', 'members': '2/5', 'needs': 'Backend, DevOps'},
	]
	return render(
		request,
		'events/event_detail.html',
		{
			'event': event,
			'rounds': rounds,
			'participants': participants,
			'teams_open': teams_open,
		},
	)
