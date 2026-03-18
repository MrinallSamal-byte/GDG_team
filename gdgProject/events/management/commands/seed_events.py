"""
Management command to seed 100 diverse sample events into the database.

Usage:
    python manage.py seed_events
    python manage.py seed_events --clear   # delete existing seeded events first
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from events.models import (
    Event,
    EventCategory,
    EventMode,
    EventStatus,
    ParticipationType,
)

# ── Rich event data pools ────────────────────────────────────────────────────

HACKATHON_TITLES = [
    "CodeStorm 2026", "HackNova Spring", "BuildTheWeb Hackathon",
    "DevSprint Summit", "ByteBash 2026", "InnoHack Challenge",
    "PixelForge Hack", "FutureTech Hack", "CloudHack Carnival",
    "BlockChain Blitz", "AIthon Grand Finale", "GreenCode Hackathon",
    "CyberHack Challenge", "HealthTech Hack", "OpenSource Weekend Hack",
]

WORKSHOP_TITLES = [
    "React Masterclass", "Django Deep Dive", "Flutter Bootcamp",
    "AWS Cloud Workshop", "Docker & Kubernetes 101", "ML with Python",
    "Figma Design Sprint", "Data Science Crash Course", "Git & GitHub Essentials",
    "GraphQL Workshop", "Next.js for Beginners", "Rust Programming Basics",
    "Blockchain Fundamentals", "iOS SwiftUI Lab", "DevOps Essentials",
]

CODING_CONTEST_TITLES = [
    "Code Warriors", "Algorithm Arena", "Competitive Coding Cup",
    "DSA Championship", "SpeedCode Challenge", "Binary Battle",
    "Logic Olympiad", "Code Golf Masters", "Recursion Rumble",
    "Graph Theory Grand Prix",
]

QUIZ_TITLES = [
    "TechQuiz Mania", "CS Fundamentals Quiz", "Cybersecurity Quiz Bowl",
    "Cloud Computing Quiz", "OS & Networks Challenge", "Database Derby",
    "AI/ML Quiz Showdown", "Web Standards Quiz", "Programming Trivia Night",
    "FOSS Knowledge Bowl",
]

DESIGN_TITLES = [
    "UI/UX Design Sprint", "Logo Design Clash", "Wireframe Wars",
    "Design Thinking Workshop", "Brand Identity Challenge",
    "Poster Design Jam", "Mobile UI Contest", "Accessibility Design Jam",
]

IDEATHON_TITLES = [
    "GreenTech Ideathon", "Social Impact Ideathon", "EduTech Innovate",
    "SmartCity Ideathon", "FinTech Ideas Challenge", "AgriTech Brainstorm",
    "HealthCare Ideathon", "Sustainability Pitch",
]

PAPER_TITLES = [
    "IEEE Paper Presentation", "ACM Research Symposium",
    "Emerging Tech Paper Fest", "AI Research Showcase",
    "Systems Design Paper Forum",
]

OTHER_TITLES = [
    "Campus Treasure Hunt", "Tech Debate Championship",
    "Open Mic: Tech Edition", "Startup Pitch Night",
    "Resume Building Workshop", "Mock Interview Marathon",
    "Career Fair 2026", "Alumni Tech Talk",
    "Photography Challenge", "Gaming Tournament",
]

CATEGORY_TITLE_MAP = {
    EventCategory.HACKATHON: HACKATHON_TITLES,
    EventCategory.WORKSHOP: WORKSHOP_TITLES,
    EventCategory.CODING_CONTEST: CODING_CONTEST_TITLES,
    EventCategory.QUIZ: QUIZ_TITLES,
    EventCategory.DESIGN_CHALLENGE: DESIGN_TITLES,
    EventCategory.IDEATHON: IDEATHON_TITLES,
    EventCategory.PAPER_PRESENTATION: PAPER_TITLES,
    EventCategory.CASE_STUDY: ["Case Study Showdown", "Business Case Slam", "MBA Case Challenge"],
    EventCategory.CULTURAL: ["Dance Fiesta", "Music Night Live", "Drama Fest", "Art Exhibition"],
    EventCategory.SPORTS: ["Cricket Tournament", "Football League", "Badminton Open", "Chess Championship", "E-Sports Arena"],
    EventCategory.OTHER: OTHER_TITLES,
}

VENUES = [
    "Main Auditorium", "CS Department Lab 3", "Innovation Hub",
    "Open Air Theatre", "Conference Hall A", "Library Seminar Room",
    "Sports Complex", "Startup Incubation Centre", "Virtual (Zoom)",
    "Virtual (Google Meet)", "Engineering Block Seminar Hall",
    "Student Activity Centre", "MBA Department Hall",
]

DESCRIPTIONS = {
    EventCategory.HACKATHON: "Join us for an intense coding marathon where teams will solve real-world problems using cutting-edge technology. Build, ship, and present a working prototype in 24-48 hours. Network with industry mentors and compete for exciting prizes!",
    EventCategory.WORKSHOP: "A hands-on interactive workshop designed for beginners and intermediate learners. Get practical experience with live coding sessions, guided exercises, and expert mentorship. Walk away with real skills and a certificate of completion.",
    EventCategory.CODING_CONTEST: "Put your algorithmic skills to the test in this fast-paced competitive programming contest. Solve challenging problems across difficulty levels. Top coders will be recognized on the campus leaderboard and win exciting prizes.",
    EventCategory.QUIZ: "Think you know your tech? Test your knowledge across multiple rounds covering programming, computer science fundamentals, current tech trends, and more. Form a team or go solo — may the most knowledgeable win!",
    EventCategory.DESIGN_CHALLENGE: "Unleash your creative side in this design-focused challenge. Create stunning UI/UX designs, wireframes, or visual assets under time constraints. Industry designers will judge your work and provide valuable feedback.",
    EventCategory.IDEATHON: "Got a world-changing idea? Pitch your innovative solution to a panel of judges and industry experts. The best ideas win incubation support, mentorship, and seed funding opportunities.",
    EventCategory.PAPER_PRESENTATION: "Present your original research or technical paper to an esteemed panel of academics and industry professionals. A great opportunity to showcase your analytical abilities and get published.",
    EventCategory.CASE_STUDY: "Analyze real-world business cases and present strategic solutions to a panel of judges. Develop your critical thinking and problem-solving abilities in this intellectually stimulating competition.",
    EventCategory.CULTURAL: "Celebrate talent, art, and expression at this vibrant cultural extravaganza. From dance and music to drama and visual arts — there's something for everyone. Come showcase your non-tech side!",
    EventCategory.SPORTS: "Compete in exciting sporting events and represent your department or college. Whether you're a seasoned athlete or a casual player, there's a category for you. Sportsmanship and fun guaranteed!",
    EventCategory.OTHER: "An exciting campus event designed to bring students together. Participate, learn something new, meet amazing people, and create lasting memories. Open to all students!",
}


class Command(BaseCommand):
    help = "Seed the database with 100 diverse sample events"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete ALL existing events before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            count = Event.all_objects.count()
            Event.all_objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {count} existing events."))

        # Get or create an organizer user
        organizer, created = User.objects.get_or_create(
            username="campus_organizer",
            defaults={
                "first_name": "Campus",
                "last_name": "Organizer",
                "email": "organizer@campusarena.dev",
                "is_staff": True,
            },
        )
        if created:
            organizer.set_password("Organizer@2026")
            organizer.save()
            self.stdout.write(self.style.SUCCESS("Created organizer user: campus_organizer"))

        now = timezone.now()
        categories = list(EventCategory.choices)
        modes = list(EventMode.choices)
        participation_types = list(ParticipationType.choices)

        # Distribute categories: ~15 hackathons, ~15 workshops, ~10 coding,
        # ~10 quizzes, ~8 design, ~8 ideathon, ~5 paper, ~5 case study,
        # ~7 cultural, ~7 sports, ~10 other = 100
        distribution = (
            [EventCategory.HACKATHON] * 15
            + [EventCategory.WORKSHOP] * 15
            + [EventCategory.CODING_CONTEST] * 10
            + [EventCategory.QUIZ] * 10
            + [EventCategory.DESIGN_CHALLENGE] * 8
            + [EventCategory.IDEATHON] * 8
            + [EventCategory.PAPER_PRESENTATION] * 5
            + [EventCategory.CASE_STUDY] * 5
            + [EventCategory.CULTURAL] * 7
            + [EventCategory.SPORTS] * 7
            + [EventCategory.OTHER] * 10
        )
        random.shuffle(distribution)

        events_created = 0
        used_titles = set()

        for i, category in enumerate(distribution):
            titles_pool = CATEGORY_TITLE_MAP.get(category, OTHER_TITLES)
            # Cycle through available titles and make them unique
            base_title = titles_pool[i % len(titles_pool)]
            title = base_title
            suffix = 1
            while title in used_titles:
                title = f"{base_title} #{suffix}"
                suffix += 1
            used_titles.add(title)

            # Random dates: some past, some ongoing, most upcoming
            bucket = random.choices(
                ["past", "ongoing", "upcoming"],
                weights=[15, 10, 75],
                k=1,
            )[0]

            if bucket == "past":
                event_start = now - timedelta(days=random.randint(10, 90))
                event_end = event_start + timedelta(hours=random.randint(4, 72))
                reg_start = event_start - timedelta(days=random.randint(14, 30))
                reg_end = event_start - timedelta(days=1)
                status = random.choice([EventStatus.COMPLETED])
            elif bucket == "ongoing":
                event_start = now - timedelta(hours=random.randint(1, 24))
                event_end = now + timedelta(hours=random.randint(4, 48))
                reg_start = event_start - timedelta(days=random.randint(7, 21))
                reg_end = event_start - timedelta(hours=1)
                status = EventStatus.ONGOING
            else:
                event_start = now + timedelta(days=random.randint(3, 120))
                event_end = event_start + timedelta(hours=random.randint(4, 72))
                reg_start = now - timedelta(days=random.randint(0, 7))
                reg_end = event_start - timedelta(days=1)
                status = random.choice([
                    EventStatus.PUBLISHED,
                    EventStatus.REGISTRATION_OPEN,
                    EventStatus.REGISTRATION_OPEN,
                    EventStatus.REGISTRATION_OPEN,
                ])

            mode = random.choice(modes)[0]
            part_type = random.choice(participation_types)[0]

            is_team = part_type in ("team", "both")
            min_team = random.choice([2, 3]) if is_team else 1
            max_team = min_team + random.randint(1, 3) if is_team else 1

            prize_pool = Decimal(random.choice([0, 5000, 10000, 25000, 50000, 100000]))
            fee = Decimal(random.choice([0, 0, 0, 99, 149, 199, 299, 499]))

            venue = random.choice(VENUES) if mode != "online" else ""
            platform = (
                random.choice([
                    "https://meet.google.com/example",
                    "https://zoom.us/j/example",
                    "https://teams.microsoft.com/example",
                    "",
                ])
                if mode != "offline"
                else ""
            )

            description = DESCRIPTIONS.get(category, DESCRIPTIONS[EventCategory.OTHER])
            is_featured = random.random() < 0.12  # ~12% featured

            faqs = [
                {"q": "Who can participate?", "a": "All college students with a valid ID."},
                {"q": "Is there a registration fee?", "a": f"{'Yes, ₹' + str(int(fee)) if fee else 'No, it is free!'}"},
                {"q": "Will certificates be provided?", "a": "Yes, participation and merit certificates will be issued."},
            ]

            event = Event(
                title=title,
                description=description,
                category=category,
                mode=mode,
                participation_type=part_type,
                status=status,
                registration_start=reg_start,
                registration_end=reg_end,
                event_start=event_start,
                event_end=event_end,
                venue=venue,
                platform_link=platform,
                capacity=random.choice([50, 100, 150, 200, 300, 500]),
                min_team_size=min_team,
                max_team_size=max_team,
                allow_team_creation=is_team,
                allow_join_requests=is_team,
                prize_pool=prize_pool,
                prize_1st=f"₹{int(prize_pool * Decimal('0.5'))}" if prize_pool else "",
                prize_2nd=f"₹{int(prize_pool * Decimal('0.3'))}" if prize_pool else "",
                prize_3rd=f"₹{int(prize_pool * Decimal('0.2'))}" if prize_pool else "",
                participation_certificate=True,
                merit_certificate=random.choice([True, False]),
                registration_fee=fee,
                eligibility="Open to all college students",
                rules=f"1. Participants must register before the deadline.\\n2. Plagiarism will result in disqualification.\\n3. Judge's decision is final.",
                faqs=faqs,
                contact_info="events@campusarena.dev | +91 98765 43210",
                is_featured=is_featured,
                created_by=organizer,
            )
            event.save()
            events_created += 1

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Successfully created {events_created} events!")
        )
        self.stdout.write(f"   Organizer: campus_organizer / Organizer@2026")
        self.stdout.write(f"   Featured events: {Event.objects.filter(is_featured=True).count()}")
        self.stdout.write(f"   Open registration: {Event.objects.filter(status=EventStatus.REGISTRATION_OPEN).count()}")
