from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from notification.models import Notification
from users.models import UserProfile


class DashboardAuthTest(TestCase):
    """Verify all dashboard views require authentication."""

    def setUp(self):
        self.client = Client()
        self.urls = [
            reverse("dashboard:user_dashboard"),
            reverse("dashboard:my_profile"),
            reverse("dashboard:my_events"),
            reverse("dashboard:my_teams"),
            reverse("dashboard:pending_requests"),
            reverse("dashboard:notifications"),
            reverse("dashboard:settings"),
        ]

    def test_redirects_unauthenticated(self):
        for url in self.urls:
            resp = self.client.get(url)
            self.assertEqual(
                resp.status_code, 302, f"{url} should redirect unauthenticated users"
            )
            self.assertIn("/auth/login/", resp.url)


class DashboardViewsTest(TestCase):
    """Verify dashboard pages render for authenticated users."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="dashtest",
            email="dash@example.com",
            password="testpass123",
            first_name="Dash",
            last_name="Test",
        )
        UserProfile.objects.create(
            user=self.user,
            college="MIT",
            branch="CSE",
            year=3,
            github="https://github.com/dash",
            linkedin="https://linkedin.com/in/dash",
            leetcode="https://leetcode.com/u/dash",
            portfolio="https://dash.dev",
        )
        self.client.login(username="dashtest", password="testpass123")

    def test_dashboard_overview(self):
        resp = self.client.get(reverse("dashboard:user_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Welcome back")
        self.assertContains(resp, "Dash")

    def test_profile_uses_real_data(self):
        resp = self.client.get(reverse("dashboard:my_profile"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Dash Test")
        self.assertContains(resp, "MIT")
        self.assertContains(resp, "#leetcode")
        self.assertContains(resp, "#portfolio")

    def test_edit_profile_renders(self):
        resp = self.client.get(reverse("dashboard:edit_profile"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Edit Profile")
        self.assertContains(resp, "Save Changes")

    def test_edit_profile_post_updates_details(self):
        resp = self.client.post(
            reverse("dashboard:edit_profile"),
            {
                "phone": "9876543210",
                "college": "Stanford",
                "branch": "AI",
                "year": "2",
                "github": "https://github.com/updated",
                "linkedin": "https://linkedin.com/in/updated",
                "leetcode": "https://leetcode.com/u/updated",
                "portfolio": "https://updated.dev",
                "bio": "Updated bio",
                "skills": "React,Python",
            },
            follow=True,
        )
        self.assertRedirects(resp, reverse("dashboard:my_profile"))
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.phone, "9876543210")
        self.assertEqual(profile.college, "Stanford")
        self.assertEqual(profile.branch, "AI")
        self.assertEqual(profile.year, 2)
        self.assertEqual(profile.skills, "React,Python")
        self.assertContains(resp, "Profile updated successfully.")

    def test_edit_profile_post_uploads_photo(self):
        photo = SimpleUploadedFile(
            "avatar.gif",
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )
        resp = self.client.post(
            reverse("dashboard:edit_profile"),
            {
                "phone": "555",
                "college": "MIT",
                "branch": "CSE",
                "year": "3",
                "github": "https://github.com/dash",
                "linkedin": "https://linkedin.com/in/dash",
                "leetcode": "https://leetcode.com/u/dash",
                "portfolio": "https://dash.dev",
                "bio": "Bio",
                "skills": "Django",
                "profile_photo": photo,
            },
            follow=True,
        )
        self.assertRedirects(resp, reverse("dashboard:my_profile"))
        profile = UserProfile.objects.get(user=self.user)
        self.assertTrue(profile.profile_picture.name.startswith("profiles/avatars/"))

    def test_edit_profile_rejects_invalid_photo_file(self):
        photo = SimpleUploadedFile(
            "avatar.png",
            b"not really an image",
            content_type="image/png",
        )
        resp = self.client.post(
            reverse("dashboard:edit_profile"),
            {
                "phone": "555",
                "college": "MIT",
                "branch": "CSE",
                "year": "3",
                "github": "https://github.com/dash",
                "linkedin": "https://linkedin.com/in/dash",
                "leetcode": "https://leetcode.com/u/dash",
                "portfolio": "https://dash.dev",
                "bio": "Bio",
                "skills": "Django",
                "profile_photo": photo,
            },
            follow=True,
        )
        self.assertRedirects(resp, reverse("dashboard:edit_profile"))
        self.assertContains(resp, "Profile photo must be a valid image file.")

    def test_edit_profile_photo_failure_keeps_text_changes(self):
        photo = SimpleUploadedFile(
            "avatar.gif",
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )
        with patch("dashboard.views._save_profile_photo", side_effect=OSError("disk full")):
            resp = self.client.post(
                reverse("dashboard:edit_profile"),
                {
                    "phone": "1112223333",
                    "college": "IIIT",
                    "branch": "ECE",
                    "year": "4",
                    "github": "https://github.com/dash",
                    "linkedin": "https://linkedin.com/in/dash",
                    "leetcode": "https://leetcode.com/u/dash",
                    "portfolio": "https://dash.dev",
                    "bio": "Still saved",
                    "skills": "MongoDB",
                    "profile_photo": photo,
                },
                follow=True,
            )

        self.assertRedirects(resp, reverse("dashboard:edit_profile"))
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.college, "IIIT")
        self.assertEqual(profile.branch, "ECE")
        self.assertEqual(profile.skills, "MongoDB")
        self.assertContains(resp, "The server could not store the uploaded file.")

    def test_my_events(self):
        resp = self.client.get(reverse("dashboard:my_events"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "My Events")

    def test_my_teams(self):
        resp = self.client.get(reverse("dashboard:my_teams"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "My Teams")

    def test_pending_requests(self):
        resp = self.client.get(reverse("dashboard:pending_requests"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Pending Requests")

    def test_notifications(self):
        resp = self.client.get(reverse("dashboard:notifications"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Notifications")

    def test_settings_get(self):
        resp = self.client.get(reverse("dashboard:settings"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Settings")

    def test_settings_post_saves(self):
        resp = self.client.post(
            reverse("dashboard:settings"),
            {
                "display_name": "Updated Name",
                "email": "new@example.com",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.last_name, "Name")
        self.assertEqual(self.user.email, "new@example.com")

    def test_sidebar_shows_user_data(self):
        resp = self.client.get(reverse("dashboard:user_dashboard"))
        self.assertContains(resp, "Dash Test")
        self.assertContains(resp, "CSE")

    def test_mark_all_read_marks_notifications(self):
        Notification.objects.create(
            user=self.user, title="Ping", body="Unread notification"
        )
        resp = self.client.post(
            reverse("dashboard:mark_all_read"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content, {"ok": True, "updated": 1})
