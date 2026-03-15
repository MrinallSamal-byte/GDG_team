"""
Team Join-Request Service — service-layer implementation.

Pattern: Controller → Service → Repository → Model
- Atomic transactions
- Permission checks
- Business rule validation
- Notification side-effects deferred via transaction.on_commit
- Structured logging
"""

import logging
from dataclasses import dataclass

from core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from django.db import IntegrityError, transaction
from django.utils import timezone

logger = logging.getLogger("campusarena.team")


@dataclass(frozen=True)
class JoinRequestResult:
    request_id: int
    team_name: str
    status: str
    message: str


class TeamRepository:
    @staticmethod
    def get_team_with_event(team_id: int):
        from team.models import Team

        try:
            return Team.objects.select_related("event", "leader").get(id=team_id)
        except Team.DoesNotExist:
            raise NotFoundError(f"Team {team_id} not found")

    @staticmethod
    def get_pending_request(team_id: int, user_id: int):
        from team.models import JoinRequest, JoinRequestStatus

        try:
            return JoinRequest.objects.select_related("team", "user").get(
                team_id=team_id,
                user_id=user_id,
                status=JoinRequestStatus.PENDING,
            )
        except JoinRequest.DoesNotExist:
            raise NotFoundError("No pending join request found")

    @staticmethod
    def user_has_team_for_event(user_id: int, event_id: int) -> bool:
        from team.models import TeamMembership

        return TeamMembership.objects.filter(
            user_id=user_id,
            team__event_id=event_id,
        ).exists()

    @staticmethod
    def create_join_request(team, user, role: str, skills: str, message: str):
        from team.models import JoinRequest

        return JoinRequest.objects.create(
            team=team,
            user=user,
            role=role,
            skills=skills,
            message=message,
        )

    @staticmethod
    def create_membership(team, user, role: str, skills: str):
        from team.models import TeamMembership

        return TeamMembership.objects.create(
            team=team,
            user=user,
            role=role,
            skills=skills,
        )


class TeamJoinRequestService:
    def __init__(self, repo: TeamRepository | None = None):
        self.repo = repo or TeamRepository()

    @transaction.atomic
    def create_join_request(
        self,
        *,
        team_id: int,
        user,
        role: str,
        skills: str = "",
        message: str = "",
    ) -> JoinRequestResult:
        from team.models import TeamStatus

        team = self.repo.get_team_with_event(team_id)

        if team.status != TeamStatus.OPEN:
            raise ValidationError("This team is not accepting new members.")
        if not team.event.is_registration_open:
            raise ValidationError("Event registration is closed.")
        if self.repo.user_has_team_for_event(user.id, team.event_id):
            raise ConflictError("You are already in a team for this event.")
        if team.leader_id == user.id:
            raise ValidationError("You cannot request to join your own team.")
        if team.is_full:
            raise ValidationError("This team is full.")

        try:
            join_request = self.repo.create_join_request(
                team=team, user=user, role=role, skills=skills, message=message
            )
        except IntegrityError:
            raise ConflictError("You already have a pending request for this team.")

        logger.info(
            "join_request_created",
            extra={
                "team_id": team.id,
                "user_id": user.id,
                "request_id": join_request.id,
                "event_id": team.event_id,
            },
        )

        # Defer notification to after transaction commit so it never rolls back
        # if the notification itself fails.
        team_id_captured = team.id
        leader_id = team.leader_id
        requester_id = user.id
        team_name = team.name
        requester_name = user.get_full_name() or user.username

        transaction.on_commit(
            lambda: _notify_leader_async(
                team_id=team_id_captured,
                leader_id=leader_id,
                requester_id=requester_id,
                team_name=team_name,
                requester_name=requester_name,
            )
        )

        return JoinRequestResult(
            request_id=join_request.id,
            team_name=team.name,
            status="pending",
            message=f"Join request sent to {team.name}.",
        )

    @transaction.atomic
    def approve_request(
        self,
        *,
        team_id: int,
        requester_user_id: int,
        approver,
    ) -> JoinRequestResult:
        from team.models import JoinRequestStatus, TeamStatus

        team = self.repo.get_team_with_event(team_id)

        if team.leader_id != approver.id:
            raise PermissionDeniedError("Only the team leader can approve requests.")

        join_request = self.repo.get_pending_request(team_id, requester_user_id)

        if team.is_full:
            raise ValidationError("Team is already full. Cannot approve.")

        if self.repo.user_has_team_for_event(requester_user_id, team.event_id):
            join_request.status = JoinRequestStatus.DECLINED
            join_request.reviewed_by = approver
            join_request.reviewed_at = timezone.now()
            join_request.save(
                update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"]
            )
            raise ConflictError("Requester has already joined another team.")

        join_request.status = JoinRequestStatus.APPROVED
        join_request.reviewed_by = approver
        join_request.reviewed_at = timezone.now()
        join_request.save(
            update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"]
        )

        self.repo.create_membership(
            team=team,
            user=join_request.user,
            role=join_request.role,
            skills=join_request.skills,
        )

        from registration.models import Registration, RegistrationStatus, RegistrationType

        Registration.objects.get_or_create(
            event=team.event,
            user=join_request.user,
            defaults={
                "type": RegistrationType.TEAM,
                "team": team,
                "preferred_role": join_request.role,
                "status": RegistrationStatus.CONFIRMED,
            },
        )

        if team.is_full:
            team.status = TeamStatus.CLOSED
            team.save(update_fields=["status", "updated_at"])

        logger.info(
            "join_request_approved",
            extra={
                "team_id": team.id,
                "user_id": requester_user_id,
                "approver_id": approver.id,
                "request_id": join_request.id,
            },
        )

        requester = join_request.user
        team_name = team.name
        event_title = team.event.title
        leader = approver

        transaction.on_commit(
            lambda: _notify_requester_approved_async(
                requester_id=requester.id,
                team_name=team_name,
                event_title=event_title,
                leader_id=leader.id,
            )
        )

        # Push WebSocket update to requester
        transaction.on_commit(
            lambda: _push_ws_notification(
                user_id=requester.id,
                title=f"Join request approved — {team_name}",
                body=f"You have been added to team \"{team_name}\".",
                notif_type="request_approved",
            )
        )

        return JoinRequestResult(
            request_id=join_request.id,
            team_name=team.name,
            status="approved",
            message=f"{requester.get_full_name()} added to {team.name}.",
        )

    @transaction.atomic
    def decline_request(
        self,
        *,
        team_id: int,
        requester_user_id: int,
        decliner,
    ) -> JoinRequestResult:
        from team.models import JoinRequestStatus

        team = self.repo.get_team_with_event(team_id)

        if team.leader_id != decliner.id:
            raise PermissionDeniedError("Only the team leader can decline requests.")

        join_request = self.repo.get_pending_request(team_id, requester_user_id)

        join_request.status = JoinRequestStatus.DECLINED
        join_request.reviewed_by = decliner
        join_request.reviewed_at = timezone.now()
        join_request.save(
            update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"]
        )

        logger.info(
            "join_request_declined",
            extra={
                "team_id": team.id,
                "user_id": requester_user_id,
                "request_id": join_request.id,
            },
        )

        requester = join_request.user
        team_name = team.name
        leader = decliner

        transaction.on_commit(
            lambda: _notify_requester_declined_async(
                requester_id=requester.id,
                team_name=team_name,
                leader_id=leader.id,
            )
        )

        return JoinRequestResult(
            request_id=join_request.id,
            team_name=team.name,
            status="declined",
            message="Join request declined.",
        )


# ─── Deferred notification helpers ───────────────────────────────────────────


def _notify_leader_async(*, team_id, leader_id, requester_id, team_name, requester_name):
    """Create notification for team leader — called after transaction commits."""
    try:
        from django.contrib.auth.models import User
        from notification.models import Notification

        users = {u.pk: u for u in User.objects.filter(pk__in=[leader_id, requester_id])}
        leader = users.get(leader_id)
        requester = users.get(requester_id)
        if not leader:
            return

        Notification.objects.create(
            user=leader,
            type="join_request",
            title=f"New join request for {team_name}",
            body=f'{requester_name} wants to join your team "{team_name}".',
            actor=requester,
        )
        _push_ws_notification(
            user_id=leader_id,
            title=f"New join request for {team_name}",
            body=f"{requester_name} wants to join.",
            notif_type="join_request",
        )
    except Exception:
        logger.error(
            "Failed to notify leader %d for team %s", leader_id, team_name, exc_info=True
        )


def _notify_requester_approved_async(*, requester_id, team_name, event_title, leader_id):
    try:
        from django.contrib.auth.models import User
        from notification.models import Notification

        requester = User.objects.get(pk=requester_id)
        leader = User.objects.get(pk=leader_id)

        Notification.objects.create(
            user=requester,
            type="request_approved",
            title=f"Join request approved — {team_name}",
            body=f'You have been added to team "{team_name}" for {event_title}.',
            actor=leader,
        )
    except Exception:
        logger.error(
            "Failed to notify requester %d of approval", requester_id, exc_info=True
        )


def _notify_requester_declined_async(*, requester_id, team_name, leader_id):
    try:
        from django.contrib.auth.models import User
        from notification.models import Notification

        # Fetch both users in a single query to avoid two round-trips
        users = {u.pk: u for u in User.objects.filter(pk__in=[requester_id, leader_id])}
        requester = users.get(requester_id)
        leader = users.get(leader_id)

        if not requester:
            return

        Notification.objects.create(
            user=requester,
            type="request_declined",
            title=f"Join request declined — {team_name}",
            body=f'Your request to join team "{team_name}" was declined.',
            actor=leader,  # may be None if leader was deleted — model allows NULL
        )
    except Exception:
        logger.error(
            "Failed to notify requester %d of decline", requester_id, exc_info=True
        )


def _push_ws_notification(*, user_id, title, body, notif_type):
    """Push a notification to the user's WebSocket channel asynchronously."""
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        from django.utils import timezone

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}_notifications",
            {
                "type": "notify",
                "title": title,
                "body": body,
                "notif_type": notif_type,
                "timestamp": timezone.now().isoformat(),
            },
        )
    except Exception:
        logger.warning("Failed to push WS notification to user %d", user_id, exc_info=True)
