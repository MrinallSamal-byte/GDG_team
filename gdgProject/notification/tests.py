from django.contrib.auth.models import User
from django.test import Client, TestCase


class NotificationApiTest(TestCase):
    """Tests for the notification unread count endpoint."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="notiftest",
            password="testpass123",
        )

    def test_unauthenticated_returns_zero(self):
        resp = self.client.get("/notifications/api/unread-count/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 0)

    def test_authenticated_returns_count(self):
        self.client.login(username="notiftest", password="testpass123")
        resp = self.client.get("/notifications/api/unread-count/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("count", resp.json())

    def test_post_not_allowed(self):
        resp = self.client.post("/notifications/api/unread-count/")
        self.assertEqual(resp.status_code, 405)
