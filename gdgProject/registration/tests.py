from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class RegistrationViewTest(TestCase):
    """Tests for the event registration view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='regtest', password='testpass123',
        )
        self.url = reverse('registration:register_event', args=[1])

    def test_requires_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/auth/login/', resp.url)

    def test_page_renders_authenticated(self):
        self.client.login(username='regtest', password='testpass123')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Event Registration')

    def test_submit_missing_fields(self):
        self.client.login(username='regtest', password='testpass123')
        resp = self.client.post(self.url, {'type': 'individual'})
        self.assertEqual(resp.status_code, 200)  # re-renders with errors

    def test_submit_success(self):
        self.client.login(username='regtest', password='testpass123')
        resp = self.client.post(self.url, {
            'type': 'individual',
            'full_name': 'Test User',
            'email': 'test@example.com',
            'phone': '1234567890',
            'college': 'MIT',
            'branch': 'CSE',
            'year': '3',
        })
        self.assertRedirects(resp, reverse('events:home'))
