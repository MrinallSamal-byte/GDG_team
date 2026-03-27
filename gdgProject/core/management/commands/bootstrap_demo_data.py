import random

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, call_command

from events.models import Event, EventStatus, ParticipationType
from notification.models import Notification
from registration.models import Registration, RegistrationStatus, RegistrationType
from team.models import ChatMessage, JoinRequest, MemberRole, Team, TeamMembership, TeamStatus
from users.models import UserProfile

User = get_user_model()

DEMO_PASSWORD = "DemoUser@2026"
DEMO_USERS = [
    {
        "username": "demo_ava",
        "email": "demo.ava@campusarena.dev",
        "first_name": "Ava",
        "last_name": "Sharma",
        "college": "IIT Delhi",
        "branch": "CSE",
        "year": 3,
        "skills": "React,Node.js,Figma",
    },
    {
        "username": "demo_rahul",
        "email": "demo.rahul@campusarena.dev",
        "first_name": "Rahul",
        "last_name": "Verma",
        "college": "NIT Trichy",
        "branch": "IT",
        "year": 4,
        "skills": "Python,Django,Docker",
    },
    {
        "username": "demo_priya",
        "email": "demo.priya@campusarena.dev",
        "first_name": "Priya",
        "last_name": "Nair",
        "college": "VIT Vellore",
        "branch": "ECE",
        "year": 2,
        "skills": "Flutter,Firebase,UI/UX",
    },
    {
        "username": "demo_arjun",
        "email": "demo.arjun@campusarena.dev",
        "first_name": "Arjun",
        "last_name": "Reddy",
        "college": "BITS Pilani",
        "branch": "CSE",
        "year": 4,
        "skills": "AWS,DevOps,Go",
    },
    {
        "username": "demo_sana",
        "email": "demo.sana@campusarena.dev",
        "first_name": "Sana",
        "last_name": "Khan",
        "college": "IIIT Hyderabad",
        "branch": "CSE",
        "year": 3,
        "skills": "TensorFlow,Python,Data Science",
    },
    {
        "username": "demo_ishaan",
        "email": "demo.ishaan@campusarena.dev",
        "first_name": "Ishaan",
        "last_name": "Mehta",
        "college": "DTU",
        "branch": "Mechanical",
        "year": 2,
        "skills": "C++,DSA,Competitive Programming",
    },
    {
        "username": "demo_meera",
        "email": "demo.meera@campusarena.dev",
        "first_name": "Meera",
        "last_name": "Iyer",
        "college": "SRM University",
        "branch": "Biotech",
        "year": 1,
        "skills": "Research,Presentations,Canva",
    },
    {
        "username": "demo_kabir",
        "email": "demo.kabir@campusarena.dev",
        "first_name": "Kabir",
        "last_name": "Singh",
        "college": "Manipal University",
        "branch": "CSE",
        "year": 3,
        "skills": "Java,Spring Boot,SQL",
    },
    {
        "username": "demo_nisha",
        "email": "demo.nisha@campusarena.dev",
        "first_name": "Nisha",
        "last_name": "Patel",
        "college": "PES University",
        "branch": "EEE",
        "year": 4,
        "skills": "Product,Operations,Public Speaking",
    },
    {
        "username": "demo_vihaan",
        "email": "demo.vihaan@campusarena.dev",
        "first_name": "Vihaan",
        "last_name": "Gupta",
        "college": "Amity University",
        "branch": "IT",
        "year": 2,
        "skills": "Next.js,TypeScript,Tailwind",
    },
]

TEAM_BLUEPRINTS = [
    {
        "name": "Demo Builders",
        "member_indexes": [0, 1, 2],
        "roles": [MemberRole.FULLSTACK, MemberRole.BACKEND, MemberRole.UIUX],
    },
    {
        "name": "Hackwave",
        "member_indexes": [3, 4, 5],
        "roles": [MemberRole.DEVOPS, MemberRole.ML_AI, MemberRole.FRONTEND],
    },
    {
        "name": "Pixel Sprint",
        "member_indexes": [6, 7, 8],
        "roles": [MemberRole.PM, MemberRole.BACKEND, MemberRole.OTHER],
    },
]


class Command(BaseCommand):
    help = "Bootstrap idempotent demo data for fresh deployments"

    def handle(self, *args, **options):
        self.stdout.write("[demo] Bootstrapping demo data...")

        if not Event.objects.exists():
            random.seed(2026)
            call_command("seed_events", verbosity=0)
            self.stdout.write("[demo] Seeded sample events.")
        else:
            self.stdout.write("[demo] Events already exist. Skipping event seed.")

        demo_users = self._create_demo_users()
        demo_teams = self._create_demo_teams(demo_users)
        self._create_individual_registrations(demo_users, demo_teams)
        self._create_join_requests(demo_users, demo_teams)
        self._create_notifications(demo_users, demo_teams)

        self.stdout.write(
            self.style.SUCCESS(
                "[demo] Ready: "
                f"{Event.objects.count()} events, "
                f"{User.objects.count()} users, "
                f"{Team.objects.count()} teams, "
                f"{Registration.objects.count()} registrations."
            )
        )
        self.stdout.write(
            "[demo] Demo user password: "
            f"{DEMO_PASSWORD} (for demo_ava, demo_rahul, demo_priya, and others)"
        )

    def _create_demo_users(self):
        users = []
        for index, spec in enumerate(DEMO_USERS, start=1):
            user, created = User.objects.get_or_create(
                username=spec["username"],
                defaults={
                    "email": spec["email"],
                    "first_name": spec["first_name"],
                    "last_name": spec["last_name"],
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save(update_fields=["password"])

            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "phone": f"+91 90000{index:04d}",
                    "college": spec["college"],
                    "branch": spec["branch"],
                    "year": spec["year"],
                    "skills": spec["skills"],
                    "bio": f"{spec['first_name']} is a demo participant on CampusArena.",
                    "email_verified": True,
                },
            )
            updates = []
            if not profile.email_verified:
                profile.email_verified = True
                updates.append("email_verified")
            if not profile.skills:
                profile.skills = spec["skills"]
                updates.append("skills")
            if updates:
                profile.save(update_fields=updates)
            users.append(user)
        return users

    def _get_team_events(self):
        events = list(
            Event.objects.filter(
                participation_type__in=[ParticipationType.TEAM, ParticipationType.BOTH],
                status__in=[
                    EventStatus.PUBLISHED,
                    EventStatus.REGISTRATION_OPEN,
                    EventStatus.ONGOING,
                ],
            ).order_by("event_start")[: len(TEAM_BLUEPRINTS)]
        )
        if len(events) < len(TEAM_BLUEPRINTS):
            events = list(
                Event.objects.filter(
                    participation_type__in=[ParticipationType.TEAM, ParticipationType.BOTH]
                ).order_by("event_start")[: len(TEAM_BLUEPRINTS)]
            )
        return events

    def _create_demo_teams(self, demo_users):
        events = self._get_team_events()
        teams = []
        for blueprint, event in zip(TEAM_BLUEPRINTS, events):
            members = [demo_users[idx] for idx in blueprint["member_indexes"]]
            leader = members[0]
            team, _ = Team.objects.get_or_create(
                event=event,
                leader=leader,
                defaults={"name": blueprint["name"], "status": TeamStatus.OPEN},
            )
            teams.append(team)

            for member, role in zip(members, blueprint["roles"]):
                TeamMembership.objects.get_or_create(
                    team=team,
                    user=member,
                    defaults={"role": role},
                )
                registration, created = Registration.objects.get_or_create(
                    event=event,
                    user=member,
                    defaults={
                        "type": RegistrationType.TEAM,
                        "team": team,
                        "status": RegistrationStatus.CONFIRMED,
                        "preferred_role": role,
                    },
                )
                if not created and registration.team_id != team.id:
                    registration.team = team
                    registration.type = RegistrationType.TEAM
                    registration.status = RegistrationStatus.CONFIRMED
                    registration.preferred_role = role
                    registration.save(
                        update_fields=["team", "type", "status", "preferred_role"]
                    )

            if not ChatMessage.objects.filter(team=team).exists():
                ChatMessage.objects.create(
                    team=team,
                    sender=leader,
                    body=f"Welcome to {team.name}. Let's get our {event.title} plan locked in.",
                )
        return teams

    def _create_individual_registrations(self, demo_users, demo_teams):
        team_event_ids = [team.event_id for team in demo_teams]
        events = list(
            Event.objects.exclude(id__in=team_event_ids)
            .filter(
                status__in=[
                    EventStatus.PUBLISHED,
                    EventStatus.REGISTRATION_OPEN,
                    EventStatus.ONGOING,
                ]
            )
            .order_by("event_start")[:6]
        )
        if not events:
            return

        for offset, user in enumerate(demo_users):
            chosen_events = [events[offset % len(events)], events[(offset + 2) % len(events)]]
            for event in chosen_events:
                looking_for_team = (
                    event.participation_type == ParticipationType.BOTH and offset % 3 == 0
                )
                Registration.objects.get_or_create(
                    event=event,
                    user=user,
                    defaults={
                        "type": RegistrationType.INDIVIDUAL,
                        "status": RegistrationStatus.CONFIRMED,
                        "looking_for_team": looking_for_team,
                        "preferred_role": MemberRole.OTHER,
                    },
                )

    def _create_join_requests(self, demo_users, demo_teams):
        if not demo_teams:
            return
        target_team = demo_teams[0]
        requester = demo_users[-1]
        if requester == target_team.leader:
            return
        JoinRequest.objects.get_or_create(
            team=target_team,
            user=requester,
            status="pending",
            defaults={
                "role": MemberRole.FRONTEND,
                "skills": requester.profile.skills,
                "message": "I can help with frontend polish and final deployment.",
            },
        )

    def _create_notifications(self, demo_users, demo_teams):
        first_team = demo_teams[0] if demo_teams else None
        for user in demo_users[:4]:
            if Notification.objects.filter(user=user).exists():
                continue
            Notification.objects.create(
                user=user,
                actor=None,
                type="system",
                title="Welcome to CampusArena",
                body="Your demo account is ready. Explore events, teams, and submissions.",
            )
            if first_team is not None:
                Notification.objects.create(
                    user=user,
                    actor=first_team.leader,
                    type="reminder",
                    title=f"Upcoming event: {first_team.event.title}",
                    body="Review your registrations and team activity from the dashboard.",
                )
