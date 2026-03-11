from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from events.models import Event, EventStatus
from registration.models import (
    Registration,
    RegistrationStatus,
    RegistrationTechStack,
    RegistrationType,
)
from team.models import Team, TeamMembership
from users.models import UserProfile


class TeamManagementViewTest(TestCase):
    """Tests for the team management view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="teamtest",
            password="testpass123",
        )
        now = timezone.now()
        self.event = Event.objects.create(
            title="Team Event",
            slug="team-event",
            description="Test",
            status=EventStatus.REGISTRATION_OPEN,
            registration_start=now - timezone.timedelta(days=1),
            registration_end=now + timezone.timedelta(days=10),
            event_start=now + timezone.timedelta(days=15),
            event_end=now + timezone.timedelta(days=16),
            created_by=self.user,
            max_team_size=4,
        )
        self.team = Team.objects.create(
            event=self.event,
            name="Team Alpha",
            leader=self.user,
        )
        TeamMembership.objects.create(
            team=self.team,
            user=self.user,
            role="backend",
        )
        self.outsider = User.objects.create_user(
            username="outsider",
            password="testpass123",
        )
        self.candidate = User.objects.create_user(
            username="candidate",
            password="testpass123",
            first_name="Cand",
            last_name="Idate",
        )
        UserProfile.objects.create(user=self.candidate, college="MIT")
        self.url = reverse("team:team_management", args=[self.team.pk])

    def test_requires_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login/", resp.url)

    def test_page_renders_authenticated(self):
        self.client.login(username="teamtest", password="testpass123")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Team Alpha")

    def test_chat_post_empty_message(self):
        self.client.login(username="teamtest", password="testpass123")
        resp = self.client.post(self.url, {"action": "send_message", "message": ""})
        self.assertRedirects(resp, self.url)

    def test_chat_post_valid_message(self):
        self.client.login(username="teamtest", password="testpass123")
        resp = self.client.post(
            self.url, {"action": "send_message", "message": "Hello team!"}
        )
        self.assertRedirects(resp, self.url)

    def test_outsider_cannot_access_team_management(self):
        self.client.login(username="outsider", password="testpass123")
        resp = self.client.get(self.url)
        self.assertRedirects(resp, reverse("events:event_detail", args=[self.event.pk]))

    def test_team_leader_sees_suggested_members(self):
        registration = Registration.objects.create(
            event=self.event,
            user=self.candidate,
            type=RegistrationType.INDIVIDUAL,
            status=RegistrationStatus.CONFIRMED,
            looking_for_team=True,
            preferred_role="frontend",
        )
        RegistrationTechStack.objects.create(
            registration=registration, tech_name="React", is_primary=True
        )

        self.client.login(username="teamtest", password="testpass123")
        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Suggested Members")
        self.assertContains(resp, "Cand Idate")
