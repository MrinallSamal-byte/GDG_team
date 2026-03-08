from django.test import Client, TestCase
from django.urls import reverse


class EventsViewTest(TestCase):
    """Tests for the events app views."""

    def setUp(self):
        self.client = Client()

    def test_home_page_renders(self):
        resp = self.client.get(reverse('events:home'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'CampusArena')
        self.assertContains(resp, 'HackFest 2026')

    def test_home_has_featured_events(self):
        resp = self.client.get(reverse('events:home'))
        self.assertContains(resp, 'Featured Event')

    def test_home_has_event_grid(self):
        resp = self.client.get(reverse('events:home'))
        self.assertContains(resp, 'Browse All Events')

    def test_event_detail_renders(self):
        resp = self.client.get(reverse('events:event_detail', args=[1]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'HackFest 2026')

    def test_event_detail_has_tabs(self):
        resp = self.client.get(reverse('events:event_detail', args=[1]))
        self.assertContains(resp, 'About')
        self.assertContains(resp, 'Timeline')
        self.assertContains(resp, 'Prizes')

    def test_event_detail_different_id(self):
        resp = self.client.get(reverse('events:event_detail', args=[999]))
        self.assertEqual(resp.status_code, 200)
