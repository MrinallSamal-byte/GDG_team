"""
Tests for new features added in the audit sprint.

Covers:
- UserTechStack model
- RegistrationTechStack model
- Team leave/toggle/remove views
- Password reset flow
- Notification creation from team service
"""
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone

from events.models import Event, EventStatus
from notification.models import Notification
from registration.models import Registration, RegistrationTechStack, RegistrationType
from team.models import (
    JoinRequest,
    JoinRequestStatus,
    MemberRole,
    Team,
    TeamMembership,
    TeamStatus,
)
from team.services import TeamJoinRequestService
from users.models import Proficiency, UserProfile, UserTechStack


# ═══════════════════════════════════════════════════════════════════════════════
# UserTechStack Model Tests
# ═══════════════════════════════════════════════════════════════════════════════
class TestUserTechStack(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='techuser', password='pass1234!!')

    def test_create_tech_stack(self):
        ts = UserTechStack.objects.create(
            user=self.user, tech_name='Python', proficiency=Proficiency.ADVANCED, is_primary=True,
        )
        self.assertEqual(str(ts), 'techuser — Python (Advanced)')

    def test_unique_constraint(self):
        UserTechStack.objects.create(user=self.user, tech_name='React')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            UserTechStack.objects.create(user=self.user, tech_name='React')


# ═══════════════════════════════════════════════════════════════════════════════
# RegistrationTechStack Model Tests
# ═══════════════════════════════════════════════════════════════════════════════
class TestRegistrationTechStack(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='reguser', password='pass1234!!')
        now = timezone.now()
        self.event = Event.objects.create(
            title='Test Event', slug='test-evt-ts', description='Desc',
            status=EventStatus.REGISTRATION_OPEN,
            registration_start=now - timezone.timedelta(days=1),
            registration_end=now + timezone.timedelta(days=10),
            event_start=now + timezone.timedelta(days=15),
            event_end=now + timezone.timedelta(days=16),
            created_by=self.user,
        )
        self.reg = Registration.objects.create(
            event=self.event, user=self.user, type=RegistrationType.INDIVIDUAL, status='confirmed',
        )

    def test_create_registration_tech_stack(self):
        rts = RegistrationTechStack.objects.create(
            registration=self.reg, tech_name='Django', is_primary=True,
        )
        self.assertIn('Django', str(rts))

    def test_unique_constraint(self):
        RegistrationTechStack.objects.create(registration=self.reg, tech_name='Flask')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            RegistrationTechStack.objects.create(registration=self.reg, tech_name='Flask')


# ═══════════════════════════════════════════════════════════════════════════════
# Team Management Views (leave, toggle, remove)
# ═══════════════════════════════════════════════════════════════════════════════
class TestTeamManagementViews(TestCase):

    def setUp(self):
        self.client = Client()
        now = timezone.now()
        self.leader = User.objects.create_user(username='leader', password='pass1234!!')
        self.member = User.objects.create_user(username='member', password='pass1234!!')
        self.outsider = User.objects.create_user(username='outsider', password='pass1234!!')
        self.event = Event.objects.create(
            title='Team Event', slug='team-evt-mgmt', description='Desc',
            status=EventStatus.REGISTRATION_OPEN,
            participation_type='team', max_team_size=4,
            registration_start=now - timezone.timedelta(days=1),
            registration_end=now + timezone.timedelta(days=10),
            event_start=now + timezone.timedelta(days=15),
            event_end=now + timezone.timedelta(days=16),
            created_by=self.leader,
        )
        self.team = Team.objects.create(
            event=self.event, name='Alpha', leader=self.leader, status=TeamStatus.OPEN,
        )
        TeamMembership.objects.create(team=self.team, user=self.leader, role=MemberRole.BACKEND)
        TeamMembership.objects.create(team=self.team, user=self.member, role=MemberRole.FRONTEND)

    # ── Leave Team ────────────────────────────────────────────────────────
    def test_member_can_leave_team(self):
        self.client.login(username='member', password='pass1234!!')
        resp = self.client.post(f'/teams/{self.team.pk}/leave/')
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(TeamMembership.objects.filter(team=self.team, user=self.member).exists())

    def test_leader_cannot_leave_team(self):
        self.client.login(username='leader', password='pass1234!!')
        resp = self.client.post(f'/teams/{self.team.pk}/leave/')
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(TeamMembership.objects.filter(team=self.team, user=self.leader).exists())

    def test_outsider_cannot_leave_team(self):
        self.client.login(username='outsider', password='pass1234!!')
        resp = self.client.post(f'/teams/{self.team.pk}/leave/')
        self.assertEqual(resp.status_code, 302)

    def test_unauthenticated_leave_redirects(self):
        resp = self.client.post(f'/teams/{self.team.pk}/leave/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('login', resp.url.lower())

    # ── Toggle Team Status ────────────────────────────────────────────────
    def test_leader_can_toggle_team_open_to_closed(self):
        self.client.login(username='leader', password='pass1234!!')
        resp = self.client.post(f'/teams/{self.team.pk}/toggle-status/')
        self.assertEqual(resp.status_code, 302)
        self.team.refresh_from_db()
        self.assertEqual(self.team.status, TeamStatus.CLOSED)

    def test_leader_can_toggle_team_closed_to_open(self):
        self.team.status = TeamStatus.CLOSED
        self.team.save()
        self.client.login(username='leader', password='pass1234!!')
        resp = self.client.post(f'/teams/{self.team.pk}/toggle-status/')
        self.assertEqual(resp.status_code, 302)
        self.team.refresh_from_db()
        self.assertEqual(self.team.status, TeamStatus.OPEN)

    def test_non_leader_cannot_toggle(self):
        self.client.login(username='member', password='pass1234!!')
        resp = self.client.post(f'/teams/{self.team.pk}/toggle-status/')
        self.assertEqual(resp.status_code, 302)
        self.team.refresh_from_db()
        self.assertEqual(self.team.status, TeamStatus.OPEN)  # unchanged

    # ── Remove Member ─────────────────────────────────────────────────────
    def test_leader_can_remove_member(self):
        self.client.login(username='leader', password='pass1234!!')
        resp = self.client.post(f'/teams/{self.team.pk}/remove/{self.member.pk}/')
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(TeamMembership.objects.filter(team=self.team, user=self.member).exists())

    def test_leader_cannot_remove_themselves(self):
        self.client.login(username='leader', password='pass1234!!')
        resp = self.client.post(f'/teams/{self.team.pk}/remove/{self.leader.pk}/')
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(TeamMembership.objects.filter(team=self.team, user=self.leader).exists())

    def test_non_leader_cannot_remove_member(self):
        self.client.login(username='member', password='pass1234!!')
        resp = self.client.post(f'/teams/{self.team.pk}/remove/{self.leader.pk}/')
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(TeamMembership.objects.filter(team=self.team, user=self.leader).exists())


# ═══════════════════════════════════════════════════════════════════════════════
# Password Reset Flow
# ═══════════════════════════════════════════════════════════════════════════════
class TestPasswordReset(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='resetuser', email='reset@example.com', password='oldpassword1!'
        )

    def test_forgot_password_page_renders(self):
        resp = self.client.get('/auth/forgot-password/')
        self.assertEqual(resp.status_code, 200)

    def test_forgot_password_post_with_valid_email(self):
        resp = self.client.post('/auth/forgot-password/', {'email': 'reset@example.com'})
        self.assertEqual(resp.status_code, 302)

    def test_forgot_password_post_with_nonexistent_email(self):
        resp = self.client.post('/auth/forgot-password/', {'email': 'nobody@example.com'})
        self.assertEqual(resp.status_code, 302)  # no error revealed

    def test_reset_password_invalid_token(self):
        resp = self.client.get('/auth/reset-password/abc/invalid-token/')
        self.assertEqual(resp.status_code, 302)

    def test_reset_password_valid_token(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        resp = self.client.get(f'/auth/reset-password/{uid}/{token}/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Reset')

    def test_reset_password_submit(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        resp = self.client.post(f'/auth/reset-password/{uid}/{token}/', {
            'password': 'newpassword123!',
            'password_confirm': 'newpassword123!',
        })
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword123!'))


# ═══════════════════════════════════════════════════════════════════════════════
# Notification Creation from Team Service
# ═══════════════════════════════════════════════════════════════════════════════
class TestNotificationCreation(TestCase):

    def setUp(self):
        now = timezone.now()
        self.leader = User.objects.create_user(username='notif_leader', password='pass1234!!')
        self.requester = User.objects.create_user(username='notif_req', password='pass1234!!')
        self.event = Event.objects.create(
            title='Notif Event', slug='notif-evt', description='Desc',
            status=EventStatus.REGISTRATION_OPEN,
            participation_type='team', max_team_size=4,
            registration_start=now - timezone.timedelta(days=1),
            registration_end=now + timezone.timedelta(days=10),
            event_start=now + timezone.timedelta(days=15),
            event_end=now + timezone.timedelta(days=16),
            created_by=self.leader,
        )
        self.team = Team.objects.create(
            event=self.event, name='NotifTeam', leader=self.leader, status=TeamStatus.OPEN,
        )
        TeamMembership.objects.create(team=self.team, user=self.leader, role=MemberRole.BACKEND)

    def test_join_request_creates_notification_for_leader(self):
        svc = TeamJoinRequestService()
        svc.create_join_request(
            team_id=self.team.pk, user=self.requester, role='frontend',
        )
        notif = Notification.objects.filter(user=self.leader, type='join_request').first()
        self.assertIsNotNone(notif)
        self.assertIn('NotifTeam', notif.title)

    def test_approve_creates_notification_for_requester(self):
        svc = TeamJoinRequestService()
        svc.create_join_request(
            team_id=self.team.pk, user=self.requester, role='frontend',
        )
        svc.approve_request(
            team_id=self.team.pk, requester_user_id=self.requester.pk, approver=self.leader,
        )
        notif = Notification.objects.filter(user=self.requester, type='request_approved').first()
        self.assertIsNotNone(notif)

    def test_decline_creates_notification_for_requester(self):
        svc = TeamJoinRequestService()
        svc.create_join_request(
            team_id=self.team.pk, user=self.requester, role='frontend',
        )
        svc.decline_request(
            team_id=self.team.pk, requester_user_id=self.requester.pk, decliner=self.leader,
        )
        notif = Notification.objects.filter(user=self.requester, type='request_declined').first()
        self.assertIsNotNone(notif)


# ═══════════════════════════════════════════════════════════════════════════════
# UserProfile New Fields
# ═══════════════════════════════════════════════════════════════════════════════
class TestUserProfileNewFields(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='profuser', password='pass1234!!')

    def test_profile_portfolio_field(self):
        profile = UserProfile.objects.create(
            user=self.user, portfolio='https://example.com',
        )
        self.assertEqual(profile.portfolio, 'https://example.com')

    def test_profile_picture_blank_by_default(self):
        profile = UserProfile.objects.create(user=self.user)
        self.assertFalse(profile.profile_picture)
