from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Event, EventRound, EventStatus


class EventsViewTest(TestCase):
    """Tests for the events app views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="evtuser", password="pass1234")
        now = timezone.now()
        self.event = Event.objects.create(
            title="HackFest 2026",
            slug="hackfest-2026",
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

    def test_home_page_renders(self):
        resp = self.client.get(reverse("events:home"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "CampusArena")
        self.assertContains(resp, "HackFest 2026")

    def test_home_has_featured_events(self):
        resp = self.client.get(reverse("events:home"))
        self.assertContains(resp, "Featured Event")

    def test_home_has_event_grid(self):
        resp = self.client.get(reverse("events:home"))
        self.assertContains(resp, "Browse All Events")

    def test_event_detail_renders(self):
        resp = self.client.get(reverse("events:event_detail", args=[self.event.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "HackFest 2026")

    def test_event_detail_has_tabs(self):
        resp = self.client.get(reverse("events:event_detail", args=[self.event.pk]))
        self.assertContains(resp, "About")
        self.assertContains(resp, "Timeline")
        self.assertContains(resp, "Prizes")

    def test_event_detail_different_id(self):
        resp = self.client.get(reverse("events:event_detail", args=[999]))
        self.assertEqual(resp.status_code, 404)
