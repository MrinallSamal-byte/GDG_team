from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class TeamManagementViewTest(TestCase):
    """Tests for the team management view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='teamtest', password='testpass123',
        )
        self.url = reverse('team:team_management', args=[1])

    def test_requires_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/auth/login/', resp.url)

    def test_page_renders_authenticated(self):
        self.client.login(username='teamtest', password='testpass123')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Team Alpha')

    def test_chat_post_empty_message(self):
        self.client.login(username='teamtest', password='testpass123')
        resp = self.client.post(self.url, {'message': ''})
        self.assertRedirects(resp, self.url)

    def test_chat_post_valid_message(self):
        self.client.login(username='teamtest', password='testpass123')
        resp = self.client.post(self.url, {'message': 'Hello team!'})
        self.assertRedirects(resp, self.url)
