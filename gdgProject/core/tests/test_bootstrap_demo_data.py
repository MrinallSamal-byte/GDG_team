from django.core.management import call_command
from django.test import TestCase

from events.models import Event
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
