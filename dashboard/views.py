import csv
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView, ListView

from events.models import Event, CustomFormField
from events.forms import CustomFieldFormSet
from registrations.models import Registration
from teams.models import Team


class UserDashboardView(LoginRequiredMixin, TemplateView):
    """Personal dashboard for participants."""
    template_name = 'dashboard/user_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['my_registrations'] = Registration.objects.filter(
            user=user, status='confirmed'
        ).select_related('event', 'team').order_by('-created_at')[:10]

        from teams.models import TeamMember
        ctx['my_teams'] = Team.objects.filter(
            members__user=user
        ).select_related('event').distinct()[:10]

        from teams.models import TeamJoinRequest
        ctx['pending_sent'] = TeamJoinRequest.objects.filter(
            user=user, status='pending'
        ).select_related('team__event')
        ctx['pending_received'] = TeamJoinRequest.objects.filter(
            team__leader=user, status='pending'
        ).select_related('user', 'team')

        from notifications.models import Notification
        ctx['recent_notifications'] = Notification.objects.filter(
            user=user
        ).order_by('-created_at')[:5]
        ctx['unread_count'] = Notification.objects.filter(user=user, is_read=False).count()
        return ctx


class MyEventsView(LoginRequiredMixin, ListView):
    template_name = 'dashboard/my_events.html'
    context_object_name = 'registrations'
    paginate_by = 20

    def get_queryset(self):
        return Registration.objects.filter(
            user=self.request.user
        ).select_related('event', 'team').order_by('-created_at')


class MyTeamsView(LoginRequiredMixin, ListView):
    template_name = 'dashboard/my_teams.html'
    context_object_name = 'teams'
    paginate_by = 20

    def get_queryset(self):
        return Team.objects.filter(
            members__user=self.request.user
        ).select_related('event', 'leader').distinct()


class PendingRequestsView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/pending_requests.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from teams.models import TeamJoinRequest
        user = self.request.user
        ctx['sent_requests'] = TeamJoinRequest.objects.filter(
            user=user
        ).select_related('team__event').order_by('-created_at')
        ctx['received_requests'] = TeamJoinRequest.objects.filter(
            team__leader=user, status='pending'
        ).select_related('user', 'team__event').order_by('-created_at')
        return ctx


class OrganizerDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Dashboard for event organizers with analytics."""
    template_name = 'dashboard/organizer_dashboard.html'

    def test_func(self):
        return self.request.user.is_organizer

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        events = Event.objects.filter(organizer=user, is_archived=False)
        ctx['events'] = events.annotate(reg_count=Count('registrations')).order_by('-created_at')
        ctx['total_events'] = events.count()
        ctx['total_registrations'] = Registration.objects.filter(event__organizer=user, status='confirmed').count()
        return ctx


class EventManagementView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'dashboard/event_management.html'

    def test_func(self):
        event = get_object_or_404(Event, pk=self.kwargs['event_id'])
        return self.request.user == event.organizer or self.request.user.is_admin

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = get_object_or_404(Event, pk=self.kwargs['event_id'])
        ctx['event'] = event
        ctx['registrations'] = event.registrations.filter(status='confirmed').select_related('user', 'team')
        ctx['teams'] = event.teams.all().prefetch_related('members__user')
        ctx['reg_count'] = event.registration_count
        return ctx


class ParticipantManagementView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = 'dashboard/participant_management.html'
    context_object_name = 'registrations'
    paginate_by = 50

    def test_func(self):
        event = get_object_or_404(Event, pk=self.kwargs['event_id'])
        return self.request.user == event.organizer or self.request.user.is_admin

    def get_queryset(self):
        event = get_object_or_404(Event, pk=self.kwargs['event_id'])
        qs = event.registrations.select_related('user', 'team')
        q = self.request.GET.get('q', '')
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(user__email__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['event'] = get_object_or_404(Event, pk=self.kwargs['event_id'])
        return ctx


class ExportRegistrationsView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Export event registrations to CSV."""

    def test_func(self):
        event = get_object_or_404(Event, pk=self.kwargs['event_id'])
        return self.request.user == event.organizer or self.request.user.is_admin

    def get(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        registrations = event.registrations.filter(status='confirmed').select_related('user', 'team')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{event.title}_registrations.csv"'

        writer = csv.writer(response)
        writer.writerow(['Registration ID', 'Name', 'Email', 'Phone', 'College', 'Type', 'Team', 'Role', 'Date'])

        for reg in registrations:
            writer.writerow([
                reg.registration_id,
                reg.user.display_name,
                reg.user.email,
                reg.user.phone,
                reg.user.college_name,
                reg.registration_type,
                reg.team.team_name if reg.team else 'N/A',
                reg.preferred_role,
                reg.created_at.strftime('%Y-%m-%d %H:%M'),
            ])

        return response


class FormBuilderView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Custom form builder for event registration."""
    template_name = 'dashboard/form_builder.html'

    def test_func(self):
        event = get_object_or_404(Event, pk=self.kwargs['event_id'])
        return self.request.user == event.organizer or self.request.user.is_admin

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = get_object_or_404(Event, pk=self.kwargs['event_id'])
        ctx['event'] = event
        if self.request.POST:
            ctx['formset'] = CustomFieldFormSet(self.request.POST, instance=event)
        else:
            ctx['formset'] = CustomFieldFormSet(instance=event)
        return ctx

    def post(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        formset = CustomFieldFormSet(request.POST, instance=event)
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Registration form updated.')
            return redirect('dashboard:form_builder', event_id=event_id)
        return self.render_to_response(self.get_context_data())
