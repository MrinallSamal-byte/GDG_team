from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class OrganizerDashboardTest(TestCase):
    """Tests for the organizer dashboard (requires staff)."""

    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(
            username='staff', password='staffpass123', is_staff=True,
        )
        self.normal = User.objects.create_user(
            username='normal', password='normalpass123',
        )

    def test_redirects_unauthenticated(self):
        resp = self.client.get(reverse('eventManagement:organizer_dashboard'))
        self.assertEqual(resp.status_code, 302)

    def test_redirects_non_staff(self):
        self.client.login(username='normal', password='normalpass123')
        resp = self.client.get(reverse('eventManagement:organizer_dashboard'))
        self.assertEqual(resp.status_code, 302)

    def test_renders_for_staff(self):
        self.client.login(username='staff', password='staffpass123')
        resp = self.client.get(reverse('eventManagement:organizer_dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Organizer Dashboard')


class CreateEventTest(TestCase):
    """Tests for the create event view."""

    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(
            username='creator', password='staffpass123', is_staff=True,
        )
        self.url = reverse('eventManagement:create_event')

    def test_create_event_page_renders(self):
        self.client.login(username='creator', password='staffpass123')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Create Event')

    def test_create_event_missing_fields(self):
        self.client.login(username='creator', password='staffpass123')
        resp = self.client.post(self.url, {'title': ''})
        self.assertEqual(resp.status_code, 200)  # re-renders with errors

    def test_create_event_success(self):
        self.client.login(username='creator', password='staffpass123')
        resp = self.client.post(self.url, {
            'title': 'Test Event',
            'category': 'hackathon',
            'mode': 'online',
            'start_date': '2026-05-01T09:00',
            'end_date': '2026-05-03T17:00',
            'description': 'A test event.',
        })
        self.assertRedirects(resp, reverse('eventManagement:organizer_dashboard'))
