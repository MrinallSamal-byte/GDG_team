from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, TemplateView

from notifications.models import Notification
from .models import Team, TeamMember, TeamJoinRequest, Message


class TeamDetailView(DetailView):
    model = Team
    template_name = 'teams/team_detail.html'
    context_object_name = 'team'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        team = self.object
        ctx['members'] = team.members.select_related('user').all()
        ctx['is_leader'] = self.request.user == team.leader if self.request.user.is_authenticated else False
        ctx['is_member'] = team.members.filter(user=self.request.user).exists() if self.request.user.is_authenticated else False
        return ctx


class TeamDashboardView(LoginRequiredMixin, DetailView):
    """Team leader dashboard for managing team."""
    model = Team
    template_name = 'teams/team_dashboard.html'
    context_object_name = 'team'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        team = self.object
        ctx['members'] = team.members.select_related('user').all()
        ctx['pending_requests'] = team.join_requests.filter(status='pending').select_related('user')
        ctx['tech_stacks'] = team.tech_stacks_covered
        ctx['recent_messages'] = team.messages.select_related('sender').order_by('-created_at')[:20]

        # Suggested members based on missing tech stacks
        covered = set(team.tech_stacks_covered)
        all_roles = {'Frontend', 'Backend', 'ML/AI', 'Design', 'DevOps', 'Mobile'}
        needed = all_roles - covered
        ctx['needed_skills'] = needed

        return ctx

    def dispatch(self, request, *args, **kwargs):
        team = self.get_object()
        if request.user != team.leader:
            messages.error(request, "Only the team leader can access the team dashboard.")
            return redirect('teams:team_detail', pk=team.pk)
        return super().dispatch(request, *args, **kwargs)


class CreateTeamView(LoginRequiredMixin, View):
    """Create a new team for a team event (used via AJAX or form POST)."""

    def post(self, request, event_id):
        from events.models import Event
        event = get_object_or_404(Event, pk=event_id)

        if not event.is_team_event:
            messages.error(request, "This event doesn't support team participation.")
            return redirect('events:event_detail', pk=event.pk)

        team_name = request.POST.get('team_name', '').strip()
        if not team_name:
            messages.error(request, "Please provide a team name.")
            return redirect('events:event_detail', pk=event.pk)

        if Team.objects.filter(event=event, team_name=team_name).exists():
            messages.error(request, "A team with that name already exists for this event.")
            return redirect('events:event_detail', pk=event.pk)

        team = Team.objects.create(
            event=event,
            team_name=team_name,
            leader=request.user,
            max_members=event.max_team_size or 4,
            is_open=True,
        )
        TeamMember.objects.create(team=team, user=request.user, role_in_team=request.POST.get('role', ''))
        messages.success(request, f'Team "{team_name}" created successfully!')
        return redirect('teams:team_dashboard', pk=team.pk)


class JoinRequestView(LoginRequiredMixin, View):
    def post(self, request, pk):
        team = get_object_or_404(Team, pk=pk)

        if not team.is_open:
            messages.error(request, "This team is no longer accepting requests.")
            return redirect('teams:team_detail', pk=team.pk)

        if team.members.filter(user=request.user).exists():
            messages.info(request, "You're already a member of this team.")
            return redirect('teams:team_detail', pk=team.pk)

        if TeamJoinRequest.objects.filter(team=team, user=request.user, status='pending').exists():
            messages.info(request, "You already have a pending request for this team.")
            return redirect('teams:team_detail', pk=team.pk)

        TeamJoinRequest.objects.create(
            team=team,
            user=request.user,
            message=request.POST.get('message', ''),
        )

        # Notify team leader
        Notification.create_notification(
            user=team.leader,
            title=f'{request.user.display_name} wants to join {team.team_name}',
            message=f'New join request for your team. Review it in your team dashboard.',
            notification_type='join_request',
            reference_id=team.pk,
            reference_type='team',
        )

        messages.success(request, "Join request sent! The team leader will review it.")
        return redirect('teams:team_detail', pk=team.pk)


class ApproveRequestView(LoginRequiredMixin, View):
    def post(self, request, pk):
        join_req = get_object_or_404(TeamJoinRequest, pk=pk)
        team = join_req.team

        if request.user != team.leader:
            messages.error(request, "Only the team leader can approve requests.")
            return redirect('teams:team_dashboard', pk=team.pk)

        if team.is_full:
            messages.error(request, "Team is already full.")
            return redirect('teams:team_dashboard', pk=team.pk)

        join_req.status = 'approved'
        join_req.responded_at = timezone.now()
        join_req.save()

        TeamMember.objects.get_or_create(
            team=team, user=join_req.user,
            defaults={'role_in_team': ''}
        )

        # Update registration if exists
        from registrations.models import Registration
        reg = Registration.objects.filter(event=team.event, user=join_req.user).first()
        if reg:
            reg.team = team
            reg.registration_type = 'team'
            reg.looking_for_team = False
            reg.save()

        team.auto_close_if_full()

        # Notify the requestor
        Notification.create_notification(
            user=join_req.user,
            title=f'Welcome to {team.team_name}!',
            message=f'Your request to join {team.team_name} has been approved.',
            notification_type='request_approved',
            reference_id=team.pk,
            reference_type='team',
        )

        # System message in chat
        Message.objects.create(
            team=team,
            sender=request.user,
            content=f'{join_req.user.display_name} joined the team.',
            message_type='system',
        )

        messages.success(request, f"{join_req.user.display_name} has been added to the team.")
        return redirect('teams:team_dashboard', pk=team.pk)


class DeclineRequestView(LoginRequiredMixin, View):
    def post(self, request, pk):
        join_req = get_object_or_404(TeamJoinRequest, pk=pk)
        team = join_req.team

        if request.user != team.leader:
            messages.error(request, "Only the team leader can decline requests.")
            return redirect('teams:team_dashboard', pk=team.pk)

        join_req.status = 'declined'
        join_req.responded_at = timezone.now()
        join_req.save()

        Notification.create_notification(
            user=join_req.user,
            title=f'Request for {team.team_name} declined',
            message=f'Your request to join {team.team_name} was not approved. You can try other teams.',
            notification_type='request_declined',
            reference_id=team.pk,
            reference_type='team',
        )

        messages.info(request, f"Request from {join_req.user.display_name} declined.")
        return redirect('teams:team_dashboard', pk=team.pk)


class LeaveTeamView(LoginRequiredMixin, View):
    def post(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        membership = TeamMember.objects.filter(team=team, user=request.user).first()

        if not membership:
            messages.error(request, "You're not a member of this team.")
            return redirect('events:event_detail', pk=team.event.pk)

        if request.user == team.leader:
            messages.error(request, "Team leaders can't leave. Transfer leadership or disband the team.")
            return redirect('teams:team_dashboard', pk=team.pk)

        membership.delete()

        Message.objects.create(
            team=team,
            sender=request.user,
            content=f'{request.user.display_name} left the team.',
            message_type='system',
        )

        if not team.is_full and not team.is_open:
            team.is_open = True
            team.save()

        messages.info(request, f"You've left {team.team_name}.")
        return redirect('dashboard:user_dashboard')


class TeamChatView(LoginRequiredMixin, DetailView):
    model = Team
    template_name = 'teams/team_chat.html'
    context_object_name = 'team'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['messages_list'] = self.object.messages.select_related('sender').order_by('created_at')
        return ctx

    def post(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(team=team, sender=request.user, content=content)
        return redirect('teams:team_chat', pk=pk)

    def dispatch(self, request, *args, **kwargs):
        team = self.get_object()
        if not team.members.filter(user=request.user).exists():
            messages.error(request, "Only team members can access the chat.")
            return redirect('teams:team_detail', pk=team.pk)
        return super().dispatch(request, *args, **kwargs)
