"""
Team Join-Request Service — reference service-layer implementation.

Demonstrates the Controller → Service → Repository → Model pattern with:
- Atomic transactions
- Permission checks
- Business rule validation
- Notification side-effects
- Idempotency handling
- Structured logging
"""
import logging
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.utils import timezone

logger = logging.getLogger("campusarena.team")


# ─── Exceptions (from core.exceptions taxonomy) ─────────────────────────────
from core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)


# ─── Data Transfer Objects ──────────────────────────────────────────────────
@dataclass(frozen=True)
class JoinRequestResult:
    request_id: int
    team_name: str
    status: str
    message: str


# ─── Repository Layer ────────────────────────────────────────────────────────
class TeamRepository:
    """Encapsulates all Team/JoinRequest DB queries."""

    @staticmethod
    def get_team_with_event(team_id: int):
        from team.models import Team

        try:
            return Team.objects.select_related("event", "leader").get(
                id=team_id
            )
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


# ─── Service Layer ───────────────────────────────────────────────────────────
class TeamJoinRequestService:
    """
    Business logic for the team join-request workflow.

    Handles: create request, approve, decline, cancel.
    All methods are atomic and raise typed exceptions.
    """

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
        """
        A user requests to join a team.

        Business rules:
        1. Team must exist and be open.
        2. Event registration must be open.
        3. User cannot already be in a team for this event.
        4. User cannot be the team leader (they are already a member).
        5. Team must not be full.
        6. No duplicate pending request.
        """
        team = self.repo.get_team_with_event(team_id)

        # Rule 1: Team open
        from team.models import TeamStatus
        if team.status != TeamStatus.OPEN:
            raise ValidationError("This team is not accepting new members.")

        # Rule 2: Registration open
        if not team.event.is_registration_open:
            raise ValidationError("Event registration is closed.")

        # Rule 3: Not already in a team
        if self.repo.user_has_team_for_event(user.id, team.event_id):
            raise ConflictError("You are already in a team for this event.")

        # Rule 4: Not the leader
        if team.leader_id == user.id:
            raise ValidationError("You cannot request to join your own team.")

        # Rule 5: Team capacity
        if team.is_full:
            raise ValidationError("This team is full.")

        # Rule 6: Idempotency — no duplicate pending request
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

        # Side effect: notify team leader
        self._notify_leader(team, user, join_request)

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
        """
        Team leader approves a join request.

        Business rules:
        1. Only the team leader can approve.
        2. Request must be pending.
        3. Team must still have capacity.
        4. Requester must not already be in another team for this event.
        """
        from team.models import JoinRequestStatus, TeamStatus

        team = self.repo.get_team_with_event(team_id)

        # Rule 1: Permission
        if team.leader_id != approver.id:
            raise PermissionDeniedError("Only the team leader can approve requests.")

        # Rule 2: Pending request
        join_request = self.repo.get_pending_request(team_id, requester_user_id)

        # Rule 3: Capacity (re-check under transaction)
        if team.is_full:
            raise ValidationError("Team is already full. Cannot approve.")

        # Rule 4: Requester hasn't joined another team meanwhile
        if self.repo.user_has_team_for_event(requester_user_id, team.event_id):
            join_request.status = JoinRequestStatus.DECLINED
            join_request.reviewed_by = approver
            join_request.reviewed_at = timezone.now()
            join_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
            raise ConflictError("Requester has already joined another team.")

        # Approve
        join_request.status = JoinRequestStatus.APPROVED
        join_request.reviewed_by = approver
        join_request.reviewed_at = timezone.now()
        join_request.save(
            update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"]
        )

        # Create membership
        self.repo.create_membership(
            team=team,
            user=join_request.user,
            role=join_request.role,
            skills=join_request.skills,
        )

        # Auto-close team if full
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

        # Side effect: notify requester
        self._notify_requester_approved(team, join_request.user)

        return JoinRequestResult(
            request_id=join_request.id,
            team_name=team.name,
            status="approved",
            message=f"{join_request.user.get_full_name()} added to {team.name}.",
        )

    @transaction.atomic
    def decline_request(
        self,
        *,
        team_id: int,
        requester_user_id: int,
        decliner,
    ) -> JoinRequestResult:
        """Team leader declines a join request."""
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

        self._notify_requester_declined(team, join_request.user)

        return JoinRequestResult(
            request_id=join_request.id,
            team_name=team.name,
            status="declined",
            message="Join request declined.",
        )

    # ─── Notification Helpers ────────────────────────────────────────────
    @staticmethod
    def _notify_leader(team, requester, join_request):
        """Create an in-app notification for the team leader about a new join request."""
        try:
            from notification.models import Notification
            Notification.objects.create(
                user=team.leader,
                type='join_request',
                title=f'New join request for {team.name}',
                body=f'{requester.get_full_name() or requester.username} wants to join your team "{team.name}".',
                actor=requester,
            )
        except Exception:
            logger.error(
                "Failed to create join_request notification for leader %d",
                team.leader_id, exc_info=True,
            )

    @staticmethod
    def _notify_requester_approved(team, requester):
        """Notify the requester that their join request was approved."""
        try:
            from notification.models import Notification
            Notification.objects.create(
                user=requester,
                type='request_approved',
                title=f'Join request approved — {team.name}',
                body=f'You have been added to team "{team.name}" for {team.event.title}.',
                actor=team.leader,
            )
        except Exception:
            logger.error(
                "Failed to create approval notification for user %d",
                requester.id, exc_info=True,
            )

    @staticmethod
    def _notify_requester_declined(team, requester):
        """Notify the requester that their join request was declined."""
        try:
            from notification.models import Notification
            Notification.objects.create(
                user=requester,
                type='request_declined',
                title=f'Join request declined — {team.name}',
                body=f'Your request to join team "{team.name}" was declined.',
                actor=team.leader,
            )
        except Exception:
            logger.error(
                "Failed to create decline notification for user %d",
                requester.id, exc_info=True,
            )
