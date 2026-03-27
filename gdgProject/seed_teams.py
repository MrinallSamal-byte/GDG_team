import os
import random

import django

os.environ["DJANGO_SETTINGS_MODULE"] = "gdgProject.settings.dev"
django.setup()

from django.contrib.auth import get_user_model
from events.models import Event
from registration.models import Registration, RegistrationStatus, RegistrationType
from team.models import MemberRole, Team, TeamMembership, TeamStatus
from users.models import UserProfile

User = get_user_model()

print("Creating 100 users...")
new_users = []
for i in range(1, 101):
    username = f"test_bot_{i}_{random.randint(1000,9999)}"
    email = f"{username}@example.com"
    user = User(username=username, email=email, first_name="Bot", last_name=f"{i}")
    user.set_password("password123")
    user.save()

    UserProfile.objects.get_or_create(
        user=user,
        defaults={
            "phone": f"555-01{i:02d}",
            "college": "Tech University",
            "branch": "Computer Science",
            "year": random.choice([1, 2, 3, 4]),
        },
    )
    new_users.append(user)

print("Fetching team events...")
team_events = list(Event.objects.filter(participation_type__in=["team", "both"]))
if not team_events:
    print("No team events found!")
    exit(1)

print("Creating 100 teams and assigning users...")
for i in range(1, 101):
    event = random.choice(team_events)
    leader = random.choice(new_users)

    # check if user is already registered for this event
    if Registration.objects.filter(user=leader, event=event).exists():
        continue

    team = Team.objects.create(
        event=event,
        name=f"Squad Alpha {i} {random.randint(100,999)}",
        leader=leader,
        status=TeamStatus.OPEN,
    )

    # role string handling based on MemberRole enum/choices
    try:
        r_leader = MemberRole.LEADER
        r_other = MemberRole.OTHER
    except AttributeError:
        r_leader = "frontend"
        r_other = "backend"

    TeamMembership.objects.create(team=team, user=leader, role=r_leader)

    Registration.objects.create(
        event=event,
        user=leader,
        type=RegistrationType.TEAM,
        team=team,
        status=RegistrationStatus.CONFIRMED,
        preferred_role=r_leader,
    )

    # Add 1 to 3 members
    members_to_add = random.randint(1, 3)
    potential_members = [u for u in new_users if u != leader]
    random.shuffle(potential_members)

    added = 0
    for member in potential_members:
        if added >= members_to_add:
            break
        if not Registration.objects.filter(user=member, event=event).exists():
            TeamMembership.objects.create(team=team, user=member, role=r_other)
            Registration.objects.create(
                event=event,
                user=member,
                type=RegistrationType.TEAM,
                team=team,
                status=RegistrationStatus.CONFIRMED,
                preferred_role=r_other,
            )
            added += 1

print("Successfully seeded 100 users and teams!")
