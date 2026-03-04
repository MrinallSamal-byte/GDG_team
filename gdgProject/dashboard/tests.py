from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from users.models import UserProfile


class DashboardAuthTest(TestCase):
    """Verify all dashboard views require authentication."""

    def setUp(self):
        self.client = Client()
        self.urls = [
            reverse('dashboard:user_dashboard'),
            reverse('dashboard:my_profile'),
            reverse('dashboard:my_events'),
            reverse('dashboard:my_teams'),
            reverse('dashboard:pending_requests'),
            reverse('dashboard:notifications'),
            reverse('dashboard:settings'),
        ]

    def test_redirects_unauthenticated(self):
        for url in self.urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, f'{url} should redirect unauthenticated users')
            self.assertIn('/auth/login/', resp.url)


class DashboardViewsTest(TestCase):
    """Verify dashboard pages render for authenticated users."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='dashtest', email='dash@example.com',
            password='testpass123', first_name='Dash', last_name='Test',
        )
        UserProfile.objects.create(
            user=self.user, college='MIT', branch='CSE', year=3,
        )
        self.client.login(username='dashtest', password='testpass123')

    def test_dashboard_overview(self):
        resp = self.client.get(reverse('dashboard:user_dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Welcome back')
        self.assertContains(resp, 'Dash')

    def test_profile_uses_real_data(self):
        resp = self.client.get(reverse('dashboard:my_profile'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Dash Test')
        self.assertContains(resp, 'MIT')

    def test_my_events(self):
        resp = self.client.get(reverse('dashboard:my_events'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'My Events')

    def test_my_teams(self):
        resp = self.client.get(reverse('dashboard:my_teams'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'My Teams')

    def test_pending_requests(self):
        resp = self.client.get(reverse('dashboard:pending_requests'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Pending Requests')

    def test_notifications(self):
        resp = self.client.get(reverse('dashboard:notifications'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Notifications')

    def test_settings_get(self):
        resp = self.client.get(reverse('dashboard:settings'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Settings')

    def test_settings_post_saves(self):
        resp = self.client.post(reverse('dashboard:settings'), {
            'display_name': 'Updated Name',
            'email': 'new@example.com',
        })
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
        self.assertEqual(self.user.email, 'new@example.com')

    def test_sidebar_shows_user_data(self):
        resp = self.client.get(reverse('dashboard:user_dashboard'))
        self.assertContains(resp, 'Dash Test')
        self.assertContains(resp, 'CSE')
