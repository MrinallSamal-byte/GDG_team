from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from events.models import Event, EventStatus
from registration.models import Registration, RegistrationTechStack, RegistrationType
from team.models import Team, TeamMembership
from users.models import UserProfile


class RegistrationViewTest(TestCase):
    """Tests for the event registration view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="regtest",
            password="testpass123",
        )
        UserProfile.objects.create(user=self.user)
        now = timezone.now()
        self.event = Event.objects.create(
            title="Test Event",
            slug="test-event",
            description="Test",
            status=EventStatus.REGISTRATION_OPEN,
            registration_start=now - timezone.timedelta(days=1),
            registration_end=now + timezone.timedelta(days=10),
            event_start=now + timezone.timedelta(days=15),
            event_end=now + timezone.timedelta(days=16),
            created_by=self.user,
        )
        self.url = reverse("registration:register_event", args=[self.event.pk])

    def test_requires_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login/", resp.url)

    def test_page_renders_authenticated(self):
        self.client.login(username="regtest", password="testpass123")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_submit_missing_fields(self):
        self.client.login(username="regtest", password="testpass123")
        resp = self.client.post(self.url, {"type": "individual"})
        self.assertEqual(resp.status_code, 200)  # re-renders with errors

    def test_submit_success(self):
        self.client.login(username="regtest", password="testpass123")
        resp = self.client.post(
            self.url,
            {
                "type": "individual",
                "full_name": "Test User",
                "email": "test@example.com",
                "phone": "1234567890",
                "college": "MIT",
                "branch": "CSE",
                "year": "3",
                "preferred_role": "Backend Developer",
                "looking_for_team": "on",
                "skills": "Python,Django",
            },
        )
        registration = Registration.objects.get(event=self.event, user=self.user)
        self.assertRedirects(
            resp, reverse("registration:confirmation", args=[registration.pk])
        )
        self.assertEqual(registration.type, RegistrationType.INDIVIDUAL)
        self.assertEqual(registration.preferred_role, "backend")
        self.assertTrue(registration.looking_for_team)
        self.assertCountEqual(
            RegistrationTechStack.objects.filter(registration=registration).values_list(
                "tech_name", flat=True
            ),
            ["Python", "Django"],
        )

    def test_create_team_choice_creates_team_registration(self):
        self.event.participation_type = "both"
        self.event.save(update_fields=["participation_type"])

        self.client.login(username="regtest", password="testpass123")
        resp = self.client.post(
            self.url,
            {
                "type": "create_team",
                "full_name": "Test User",
                "email": "test@example.com",
                "phone": "1234567890",
                "college": "MIT",
                "branch": "CSE",
                "year": "3",
                "preferred_role": "Backend Developer",
                "team_name": "CodeCrafters",
                "skills": "Python,Django",
            },
        )

        team = Team.objects.get(event=self.event, name="CodeCrafters")
        self.assertTrue(
            TeamMembership.objects.filter(
                team=team, user=self.user, role="backend"
            ).exists()
        )
        registration = Registration.objects.get(event=self.event, user=self.user)
        self.assertRedirects(
            resp, reverse("registration:confirmation", args=[registration.pk])
        )
        self.assertEqual(registration.team, team)
        self.assertCountEqual(
            RegistrationTechStack.objects.filter(registration=registration).values_list(
                "tech_name", flat=True
            ),
            ["Python", "Django"],
        )

    def test_confirmation_requires_owning_user(self):
        registration = Registration.objects.create(
            event=self.event,
            user=self.user,
            type=RegistrationType.INDIVIDUAL,
            status="confirmed",
        )
        self.client.login(username="regtest", password="testpass123")
        resp = self.client.get(
            reverse("registration:confirmation", args=[registration.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, registration.registration_id)
