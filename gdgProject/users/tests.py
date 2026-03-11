from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import UserProfile


class UserProfileModelTest(TestCase):
    """Tests for the UserProfile model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            college="MIT",
            branch="CSE",
            year=3,
            skills="Python,Django,React",
        )

    def test_profile_str(self):
        self.assertIn("Test User", str(self.profile))

    def test_skills_list(self):
        self.assertEqual(self.profile.skills_list, ["Python", "Django", "React"])

    def test_skills_list_empty(self):
        self.profile.skills = ""
        self.assertEqual(self.profile.skills_list, [])

    def test_year_display(self):
        self.assertEqual(self.profile.year_display, "3rd Year")

    def test_year_display_1st(self):
        self.profile.year = 1
        self.assertEqual(self.profile.year_display, "1st Year")

    def test_year_display_4th(self):
        self.profile.year = 4
        self.assertEqual(self.profile.year_display, "4th Year")

    def test_year_display_none(self):
        self.profile.year = None
        self.assertEqual(self.profile.year_display, "")


class LoginViewTest(TestCase):
    """Tests for the login view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="logintest",
            email="login@example.com",
            password="testpass123",
            first_name="Login",
        )
        self.url = reverse("users:login")

    def test_login_page_renders(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Sign In")

    def test_login_success(self):
        resp = self.client.post(
            self.url, {"email": "login@example.com", "password": "testpass123"}
        )
        self.assertRedirects(resp, reverse("dashboard:user_dashboard"))

    def test_login_wrong_password(self):
        resp = self.client.post(
            self.url, {"email": "login@example.com", "password": "wrong"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Invalid email or password")

    def test_login_nonexistent_email(self):
        resp = self.client.post(
            self.url, {"email": "no@example.com", "password": "pass"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Invalid email or password")

    def test_login_empty_fields(self):
        resp = self.client.post(self.url, {"email": "", "password": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Please fill in all required fields")

    def test_login_redirects_if_authenticated(self):
        self.client.login(username="logintest", password="testpass123")
        resp = self.client.get(self.url)
        self.assertRedirects(resp, reverse("dashboard:user_dashboard"))

    def test_login_repopulates_email(self):
        resp = self.client.post(
            self.url, {"email": "test@example.com", "password": "wrong"}
        )
        self.assertContains(resp, 'value="test@example.com"')


class RegisterViewTest(TestCase):
    """Tests for the registration view."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("users:register")

    def test_register_page_renders(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Create Account")

    def test_register_success(self):
        resp = self.client.post(
            self.url,
            {
                "full_name": "New User",
                "email": "new@example.com",
                "college": "MIT",
                "branch": "CSE",
                "year": "3",
                "password": "securepass123",
                "password_confirm": "securepass123",
            },
        )
        self.assertRedirects(resp, reverse("users:verify_email"))
        # User and profile should exist
        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "User")
        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(user.profile.college, "MIT")
        self.assertEqual(user.profile.branch, "CSE")
        self.assertEqual(user.profile.year, 3)

    def test_register_password_mismatch(self):
        resp = self.client.post(
            self.url,
            {
                "full_name": "New User",
                "email": "new@example.com",
                "college": "MIT",
                "branch": "CSE",
                "year": "3",
                "password": "securepass123",
                "password_confirm": "different123",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Passwords do not match")

    def test_register_short_password(self):
        resp = self.client.post(
            self.url,
            {
                "full_name": "New User",
                "email": "new@example.com",
                "college": "MIT",
                "branch": "CSE",
                "year": "3",
                "password": "123",
                "password_confirm": "123",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "at least 10 characters")

    def test_register_duplicate_email(self):
        User.objects.create_user(
            username="existing", email="dup@example.com", password="pass123"
        )
        resp = self.client.post(
            self.url,
            {
                "full_name": "Dup User",
                "email": "dup@example.com",
                "college": "MIT",
                "branch": "CSE",
                "year": "2",
                "password": "securepass123",
                "password_confirm": "securepass123",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "already exists")

    def test_register_missing_fields(self):
        resp = self.client.post(
            self.url, {"full_name": "", "email": "", "password": ""}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Please fill in all required fields")


class LogoutViewTest(TestCase):
    """Tests for the logout view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="logouttest",
            password="testpass123",
        )
        self.url = reverse("users:logout")

    def test_logout_post(self):
        self.client.login(username="logouttest", password="testpass123")
        resp = self.client.post(self.url)
        self.assertRedirects(resp, reverse("events:home"))

    def test_logout_get_also_works(self):
        self.client.login(username="logouttest", password="testpass123")
        resp = self.client.get(self.url)
        self.assertRedirects(resp, reverse("events:home"))


class ChangePasswordViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="changepass",
            email="change@example.com",
            password="testpass12345",
        )
        self.url = reverse("users:change_password")

    def test_requires_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login/", resp.url)

    def test_page_renders(self):
        self.client.login(username="changepass", password="testpass12345")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Change Password")

    def test_updates_password(self):
        self.client.login(username="changepass", password="testpass12345")
        resp = self.client.post(
            self.url,
            {
                "current_password": "testpass12345",
                "new_password": "updatedpass12345",
                "confirm_password": "updatedpass12345",
            },
        )
        self.assertRedirects(resp, reverse("dashboard:settings"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("updatedpass12345"))


class ForgotPasswordViewTest(TestCase):
    """Tests for the forgot password view."""

    def setUp(self):
        self.url = reverse("users:forgot_password")

    def test_page_renders(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Reset Password")

    def test_submit_always_succeeds(self):
        resp = self.client.post(self.url, {"email": "any@example.com"})
        self.assertRedirects(resp, self.url)

    def test_submit_empty_email(self):
        resp = self.client.post(self.url, {"email": ""})
        self.assertRedirects(resp, self.url)


class EmailVerificationViewTest(TestCase):
    """Tests for email verification."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="verifytest",
            password="testpass123",
        )
        UserProfile.objects.create(user=self.user)
        self.client.login(username="verifytest", password="testpass123")
        self.url = reverse("users:verify_email")

    def test_page_renders(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Email Verification")

    def test_valid_otp(self):
        resp = self.client.post(
            self.url,
            {
                "otp_1": "1",
                "otp_2": "2",
                "otp_3": "3",
                "otp_4": "4",
                "otp_5": "5",
                "otp_6": "6",
            },
        )
        self.assertRedirects(resp, reverse("dashboard:user_dashboard"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile.email_verified)

    def test_invalid_otp(self):
        resp = self.client.post(
            self.url,
            {
                "otp_1": "1",
                "otp_2": "",
                "otp_3": "3",
                "otp_4": "4",
                "otp_5": "5",
                "otp_6": "6",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Invalid or incomplete")

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login/", resp.url)
