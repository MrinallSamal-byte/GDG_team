from datetime import datetime

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from events.models import EventCategory, EventMode, ParticipationType
from notification.models import Notification

from .models import EventCreationRequest, EventRequestStatus


class OrganizerDashboardTest(TestCase):
    """Tests for the organizer dashboard (requires staff)."""

    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(
            username="staff",
            password="staffpass123",
            is_staff=True,
        )
        self.normal = User.objects.create_user(
            username="normal",
            password="normalpass123",
        )

    def test_redirects_unauthenticated(self):
        resp = self.client.get(reverse("eventManagement:organizer_dashboard"))
        self.assertEqual(resp.status_code, 302)

    def test_redirects_non_staff(self):
        self.client.login(username="normal", password="normalpass123")
        resp = self.client.get(reverse("eventManagement:organizer_dashboard"))
        self.assertEqual(resp.status_code, 302)

    def test_renders_for_staff(self):
        self.client.login(username="staff", password="staffpass123")
        resp = self.client.get(reverse("eventManagement:organizer_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Organizer Dashboard")
        self.assertContains(resp, "User Management")


class CreateEventTest(TestCase):
    """Tests for the create event view."""

    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(
            username="creator",
            password="staffpass123",
            is_staff=True,
        )
        self.url = reverse("eventManagement:create_event")

    def test_create_event_page_renders(self):
        self.client.login(username="creator", password="staffpass123")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Create Event")

    def test_create_event_missing_fields(self):
        self.client.login(username="creator", password="staffpass123")
        resp = self.client.post(self.url, {"title": ""})
        self.assertEqual(resp.status_code, 200)  # re-renders with errors

    def test_create_event_success(self):
        self.client.login(username="creator", password="staffpass123")
        resp = self.client.post(
            self.url,
            {
                "title": "Test Event",
                "category": "hackathon",
                "mode": "online",
                "start_date": "2026-05-01T09:00",
                "end_date": "2026-05-03T17:00",
                "description": "A test event.",
            },
        )
        self.assertRedirects(resp, reverse("eventManagement:organizer_dashboard"))


class EventRequestWorkflowTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="staffpass123",
            is_staff=True,
        )
        self.creator = User.objects.create_user(
            username="creatoruser",
            email="creator@example.com",
            password="creatorpass123",
        )

    def _request_payload(self, title="Creator Event"):
        return {
            "title": title,
            "category": EventCategory.HACKATHON,
            "mode": EventMode.ONLINE,
            "participation_type": ParticipationType.INDIVIDUAL,
            "start_date": "2026-05-10T09:00",
            "end_date": "2026-05-11T18:00",
            "reg_start_date": "2026-05-01T09:00",
            "reg_end_date": "2026-05-09T18:00",
            "description": "Creator-submitted hackathon",
            "venue": "Online",
            "platform_link": "https://example.com/meet",
            "max_participants": "150",
            "min_team_size": "1",
            "max_team_size": "1",
            "registration_fee": "0",
            "rules": "Follow the brief.",
            "contact_info": "creator@example.com",
        }

    def test_creator_can_submit_event_request(self):
        self.client.login(username="creatoruser", password="creatorpass123")
        resp = self.client.post(
            reverse("eventManagement:request_event"),
            self._request_payload(),
        )
        self.assertRedirects(resp, reverse("eventManagement:creator_dashboard"))
        event_request = EventCreationRequest.objects.get(title="Creator Event")
        self.assertEqual(event_request.requested_by, self.creator)
        self.assertEqual(event_request.status, EventRequestStatus.PENDING)
        self.assertTrue(
            Notification.objects.filter(
                user=self.staff,
                type="event_request",
            ).exists()
        )

    def test_staff_can_approve_event_request(self):
        event_request = EventCreationRequest.objects.create(
            requested_by=self.creator,
            title="Approved Event",
            description="Needs approval",
            category=EventCategory.WORKSHOP,
            mode=EventMode.OFFLINE,
            participation_type=ParticipationType.INDIVIDUAL,
            registration_start=timezone.make_aware(datetime(2026, 5, 1, 9, 0)),
            registration_end=timezone.make_aware(datetime(2026, 5, 5, 18, 0)),
            event_start=timezone.make_aware(datetime(2026, 5, 10, 10, 0)),
            event_end=timezone.make_aware(datetime(2026, 5, 10, 18, 0)),
            venue="Main Auditorium",
            capacity=120,
            min_team_size=1,
            max_team_size=1,
            contact_info="creator@example.com",
        )
        self.client.login(username="adminuser", password="staffpass123")
        resp = self.client.post(
            reverse("eventManagement:review_event_request", args=[event_request.pk]),
            {"action": "approve", "review_note": "Looks good."},
        )
        self.assertRedirects(resp, reverse("eventManagement:organizer_dashboard"))
        event_request.refresh_from_db()
        self.assertEqual(event_request.status, EventRequestStatus.APPROVED)
        self.assertIsNotNone(event_request.created_event)
        self.assertEqual(event_request.created_event.title, "Approved Event")
        self.assertTrue(
            Notification.objects.filter(
                user=self.creator,
                type="request_approved",
            ).exists()
        )

    def test_staff_can_block_user_and_reset_password(self):
        self.client.login(username="adminuser", password="staffpass123")

        block_resp = self.client.post(
            reverse("eventManagement:toggle_user_status", args=[self.creator.pk])
        )
        self.assertRedirects(block_resp, reverse("eventManagement:organizer_dashboard"))
        self.creator.refresh_from_db()
        self.assertFalse(self.creator.is_active)

        password_resp = self.client.post(
            reverse("eventManagement:update_user_password", args=[self.creator.pk]),
            {"new_password": "FreshPass@2026"},
        )
        self.assertRedirects(password_resp, reverse("eventManagement:organizer_dashboard"))
        self.creator.refresh_from_db()
        self.assertTrue(self.creator.check_password("FreshPass@2026"))
