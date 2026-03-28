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

    def test_home_paginates_at_sixteen_events_per_page(self):
        now = timezone.now()
        for index in range(20):
            Event.objects.create(
                title=f"Event {index:02d}",
                slug=f"event-{index:02d}",
                description="Paginated event",
                status=EventStatus.REGISTRATION_OPEN,
                registration_start=now - timezone.timedelta(days=1),
                registration_end=now + timezone.timedelta(days=10),
                event_start=now + timezone.timedelta(days=20 + index),
                event_end=now + timezone.timedelta(days=21 + index),
                created_by=self.user,
            )

        resp = self.client.get(reverse("events:home"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["event_page"].paginator.per_page, 16)
        self.assertTrue(resp.context["event_page"].has_next())

        next_resp = self.client.get(reverse("events:home"), {"page": 2})
        self.assertEqual(next_resp.status_code, 200)
        self.assertEqual(next_resp.context["event_page"].number, 2)
        self.assertNotContains(next_resp, "Next 16 Events")

    def test_dedicated_events_page_renders(self):
        resp = self.client.get(reverse("events:events_page"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "All Public Events")
        self.assertContains(resp, "Browse every live event from one dedicated page")
        self.assertContains(resp, "HackFest 2026")

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
