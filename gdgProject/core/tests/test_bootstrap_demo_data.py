import os
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from events.models import Event, EventCategory, EventMode, EventStatus, ParticipationType
from notification.models import Notification
from registration.models import Registration
from team.models import JoinRequest, Team
from users.models import UserProfile


class BootstrapDemoDataCommandTest(TestCase):
    def test_bootstrap_command_creates_demo_records_idempotently(self):
        call_command("bootstrap_demo_data", verbosity=0)

        first_counts = {
            "events": Event.objects.count(),
            "profiles": UserProfile.objects.count(),
            "teams": Team.objects.count(),
            "registrations": Registration.objects.count(),
            "notifications": Notification.objects.count(),
            "join_requests": JoinRequest.objects.count(),
        }

        self.assertGreaterEqual(first_counts["events"], 100)
        self.assertGreaterEqual(first_counts["profiles"], 10)
        self.assertGreaterEqual(first_counts["teams"], 3)
        self.assertGreaterEqual(first_counts["registrations"], 10)
        self.assertGreaterEqual(first_counts["notifications"], 4)
        self.assertGreaterEqual(first_counts["join_requests"], 1)

        call_command("bootstrap_demo_data", verbosity=0)

        second_counts = {
            "events": Event.objects.count(),
            "profiles": UserProfile.objects.count(),
            "teams": Team.objects.count(),
            "registrations": Registration.objects.count(),
            "notifications": Notification.objects.count(),
            "join_requests": JoinRequest.objects.count(),
        }

        self.assertEqual(first_counts, second_counts)

    def test_bootstrap_seeds_when_only_draft_events_exist(self):
        organizer = User.objects.create_user(
            username="draft-organizer",
            password="testpass123",
        )
        Event.objects.create(
            title="Draft Only Event",
            description="Draft event should not block demo seeding.",
            category=EventCategory.OTHER,
            mode=EventMode.ONLINE,
            participation_type=ParticipationType.INDIVIDUAL,
            status=EventStatus.DRAFT,
            registration_start="2026-01-01T00:00:00Z",
            registration_end="2026-01-02T00:00:00Z",
            event_start="2026-01-03T00:00:00Z",
            event_end="2026-01-04T00:00:00Z",
            created_by=organizer,
        )

        call_command("bootstrap_demo_data", verbosity=0)

        self.assertGreater(
            Event.objects.filter(
                status__in=[
                    EventStatus.PUBLISHED,
                    EventStatus.REGISTRATION_OPEN,
                    EventStatus.REGISTRATION_CLOSED,
                    EventStatus.ONGOING,
                    EventStatus.COMPLETED,
                ]
            ).count(),
            0,
        )

    def test_bootstrap_can_create_configured_admin_user(self):
        with patch.dict(
            os.environ,
            {
                "BOOTSTRAP_ADMIN_EMAIL": "admin234@gmail.com",
                "BOOTSTRAP_ADMIN_PASSWORD": "Mrinall@1123",
                "BOOTSTRAP_ADMIN_NAME": "Campus Arena Admin",
            },
            clear=False,
        ):
            call_command("bootstrap_demo_data", verbosity=0)

        admin_user = User.objects.get(email="admin234@gmail.com")
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.check_password("Mrinall@1123"))
        self.assertEqual(admin_user.first_name, "Campus")
