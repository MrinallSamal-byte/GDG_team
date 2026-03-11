"""
Baseline tests — unit, integration, and permission.

Deliverable #6: Three test archetypes demonstrating the test pyramid strategy.
"""

from unittest.mock import MagicMock, patch

from core.exceptions import ConflictError, ValidationError
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone
from events.models import Event, EventRound, EventStatus


# ═══════════════════════════════════════════════════════════════════════════════
# 1. UNIT TEST — Service layer in isolation (mocked repository)
# ═══════════════════════════════════════════════════════════════════════════════
class TestTeamJoinRequestServiceUnit(TestCase):
    """
    Unit test for TeamJoinRequestService.create_join_request.
    Repository is mocked — no DB hits, fast execution.
    """

    def setUp(self):
        self.user = MagicMock()
        self.user.id = 99
        self.user.get_full_name.return_value = "Test User"

        self.team = MagicMock()
        self.team.id = 1
        self.team.name = "Team Alpha"
        self.team.leader_id = 50  # different from user
        self.team.event_id = 10
        self.team.event.is_registration_open = True
        self.team.status = "open"
        self.team.is_full = False

        self.join_request = MagicMock()
        self.join_request.id = 777
        self.join_request.user = self.user

    @patch("team.services.TeamRepository")
    def test_create_request_success(self, MockRepo):
        from team.services import TeamJoinRequestService

        repo = MockRepo.return_value
        repo.get_team_with_event.return_value = self.team
        repo.user_has_team_for_event.return_value = False
        repo.create_join_request.return_value = self.join_request

        service = TeamJoinRequestService(repo=repo)
        result = service.create_join_request(
            team_id=1, user=self.user, role="backend", skills="Python,Django"
        )

        self.assertEqual(result.status, "pending")
        self.assertEqual(result.request_id, 777)
        repo.create_join_request.assert_called_once()

    @patch("team.services.TeamRepository")
    def test_create_request_team_full_raises(self, MockRepo):
        from team.services import TeamJoinRequestService

        self.team.is_full = True
        repo = MockRepo.return_value
        repo.get_team_with_event.return_value = self.team
        repo.user_has_team_for_event.return_value = False

        service = TeamJoinRequestService(repo=repo)
        with self.assertRaises(ValidationError) as ctx:
            service.create_join_request(team_id=1, user=self.user, role="backend")
        self.assertIn("full", ctx.exception.message.lower())

    @patch("team.services.TeamRepository")
    def test_create_request_already_in_team_raises(self, MockRepo):
        from team.services import TeamJoinRequestService

        repo = MockRepo.return_value
        repo.get_team_with_event.return_value = self.team
        repo.user_has_team_for_event.return_value = True

        service = TeamJoinRequestService(repo=repo)
        with self.assertRaises(ConflictError):
            service.create_join_request(team_id=1, user=self.user, role="frontend")

    @patch("team.services.TeamRepository")
    def test_leader_cannot_join_own_team(self, MockRepo):
        from team.services import TeamJoinRequestService

        self.team.leader_id = self.user.id  # same user
        repo = MockRepo.return_value
        repo.get_team_with_event.return_value = self.team
        repo.user_has_team_for_event.return_value = False

        service = TeamJoinRequestService(repo=repo)
        with self.assertRaises(ValidationError):
            service.create_join_request(team_id=1, user=self.user, role="backend")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. INTEGRATION TEST — Full request/response cycle through Django
# ═══════════════════════════════════════════════════════════════════════════════
class TestEventDetailIntegration(TestCase):
    """
    Integration test for the event detail view.
    Exercises URL routing → view → template rendering.
    Currently tests the stub view; will evolve as models are wired.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="detailuser", password="pass1234")
        now = timezone.now()
        self.event = Event.objects.create(
            title="HackFest 2026",
            slug="hackfest-2026-baseline",
            description="A great hackathon",
            status=EventStatus.REGISTRATION_OPEN,
            registration_start=now - timezone.timedelta(days=1),
            registration_end=now + timezone.timedelta(days=10),
            event_start=now + timezone.timedelta(days=15),
            event_end=now + timezone.timedelta(days=16),
            created_by=self.user,
        )
        EventRound.objects.create(
            event=self.event,
            name="Round 1",
            order=1,
            start_date=now + timezone.timedelta(days=15),
            end_date=now + timezone.timedelta(days=16),
        )

    def test_event_detail_returns_200(self):
        resp = self.client.get(f"/events/{self.event.pk}/")
        self.assertEqual(resp.status_code, 200)

    def test_event_detail_contains_event_data(self):
        resp = self.client.get(f"/events/{self.event.pk}/")
        self.assertContains(resp, "HackFest 2026")

    def test_event_detail_context_has_rounds(self):
        resp = self.client.get(f"/events/{self.event.pk}/")
        self.assertIn("rounds", resp.context)
        self.assertTrue(len(resp.context["rounds"]) > 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PERMISSION TEST — RBAC enforcement
# ═══════════════════════════════════════════════════════════════════════════════
class TestOrganizerPermissions(TestCase):
    """
    Permission test ensuring RBAC enforcement on organizer endpoints.
    Verifies: unauthenticated, non-staff, and staff access patterns.
    """

    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username="organizer", password="pass1234!!", is_staff=True
        )
        self.normal_user = User.objects.create_user(
            username="participant", password="pass1234!!"
        )

    def test_unauthenticated_redirected_from_organizer_dashboard(self):
        resp = self.client.get("/organizer/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url.lower())

    def test_non_staff_redirected_from_organizer_dashboard(self):
        self.client.login(username="participant", password="pass1234!!")
        resp = self.client.get("/organizer/")
        self.assertEqual(resp.status_code, 302)

    def test_staff_can_access_organizer_dashboard(self):
        self.client.login(username="organizer", password="pass1234!!")
        resp = self.client.get("/organizer/")
        self.assertEqual(resp.status_code, 200)

    def test_unauthenticated_redirected_from_create_event(self):
        resp = self.client.get("/organizer/create/")
        self.assertEqual(resp.status_code, 302)

    def test_non_staff_redirected_from_create_event(self):
        self.client.login(username="participant", password="pass1234!!")
        resp = self.client.get("/organizer/create/")
        self.assertEqual(resp.status_code, 302)

    def test_staff_can_access_create_event(self):
        self.client.login(username="organizer", password="pass1234!!")
        resp = self.client.get("/organizer/create/")
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_requires_login(self):
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url.lower())

    def test_dashboard_accessible_when_logged_in(self):
        self.client.login(username="participant", password="pass1234!!")
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 200)
