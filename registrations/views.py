from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, TemplateView

from events.models import Event
from notifications.models import Notification
from teams.models import Team, TeamMember
from .forms import RegistrationForm, TeamRegistrationForm, TechStackSelectionForm
from .models import Registration, RegistrationTechStack


class RegisterForEventView(LoginRequiredMixin, TemplateView):
    """Multi-step event registration."""
    template_name = 'registrations/register.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = get_object_or_404(Event, pk=self.kwargs['event_id'])
        ctx['event'] = event
        ctx['reg_form'] = RegistrationForm()
        ctx['team_form'] = TeamRegistrationForm()
        ctx['tech_form'] = TechStackSelectionForm()
        ctx['open_teams'] = event.teams.filter(is_open=True) if event.is_team_event else []
        ctx['custom_fields'] = event.custom_fields.all()

        # Check if user already registered
        existing = Registration.objects.filter(event=event, user=self.request.user).first()
        if existing:
            ctx['existing_registration'] = existing
        return ctx

    def post(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)

        # Check if already registered
        if Registration.objects.filter(event=event, user=request.user).exists():
            messages.warning(request, "You're already registered for this event.")
            return redirect('events:event_detail', pk=event.pk)

        # Check capacity
        if event.is_full:
            messages.error(request, "Sorry, this event has reached full capacity.")
            return redirect('events:event_detail', pk=event.pk)

        reg_form = RegistrationForm(request.POST)
        if not reg_form.is_valid():
            return self.render_to_response(self.get_context_data())

        registration = reg_form.save(commit=False)
        registration.event = event
        registration.user = request.user

        reg_type = request.POST.get('registration_type', 'individual')

        # Handle team creation
        if reg_type == 'team' and request.POST.get('action') == 'create_team':
            team_form = TeamRegistrationForm(request.POST)
            if team_form.is_valid():
                team = Team.objects.create(
                    event=event,
                    team_name=team_form.cleaned_data['team_name'],
                    leader=request.user,
                    max_members=team_form.cleaned_data['max_members'],
                    is_open=team_form.cleaned_data['open_for_requests'],
                )
                TeamMember.objects.create(team=team, user=request.user, role_in_team=registration.preferred_role)
                registration.team = team
                registration.registration_type = 'team'

        registration.save()

        # Save tech stacks
        tech_form = TechStackSelectionForm(request.POST)
        if tech_form.is_valid():
            primary = [s.strip() for s in tech_form.cleaned_data['primary_skills'].split(',') if s.strip()]
            secondary = [s.strip() for s in tech_form.cleaned_data.get('secondary_skills', '').split(',') if s.strip()]
            for skill in primary:
                RegistrationTechStack.objects.create(registration=registration, tech_name=skill, is_primary=True)
            for skill in secondary:
                RegistrationTechStack.objects.create(registration=registration, tech_name=skill, is_primary=False)

        # Create notification
        Notification.create_notification(
            user=request.user,
            title=f'Registration confirmed for {event.title}',
            message=f'Your registration ID is {registration.registration_id}. Get ready!',
            notification_type='registration',
            reference_id=event.pk,
            reference_type='event',
        )

        messages.success(request, f"You're in! Registration ID: {registration.registration_id}")
        return redirect('registrations:confirmation', pk=registration.pk)


class RegistrationConfirmationView(LoginRequiredMixin, DetailView):
    model = Registration
    template_name = 'registrations/confirmation.html'
    context_object_name = 'registration'

    def get_queryset(self):
        return Registration.objects.filter(user=self.request.user)


class CancelRegistrationView(LoginRequiredMixin, View):
    def post(self, request, pk):
        reg = get_object_or_404(Registration, pk=pk, user=request.user)
        reg.status = 'cancelled'
        reg.save()
        messages.info(request, "Registration cancelled.")
        return redirect('dashboard:user_dashboard')


class DownloadCalendarView(LoginRequiredMixin, View):
    """Generate .ics calendar file for an event."""

    def get(self, request, pk):
        reg = get_object_or_404(Registration, pk=pk, user=request.user)
        event = reg.event

        try:
            from icalendar import Calendar, Event as ICalEvent
            cal = Calendar()
            cal.add('prodid', '-//CampusArena//EN')
            cal.add('version', '2.0')

            ical_event = ICalEvent()
            ical_event.add('summary', event.title)
            ical_event.add('dtstart', event.event_start)
            ical_event.add('dtend', event.event_end)
            ical_event.add('description', event.description[:500])
            if event.venue:
                ical_event.add('location', event.venue)
            cal.add_component(ical_event)

            response = HttpResponse(cal.to_ical(), content_type='text/calendar')
            response['Content-Disposition'] = f'attachment; filename="{event.title}.ics"'
            return response
        except ImportError:
            messages.error(request, "Calendar download not available.")
            return redirect('registrations:confirmation', pk=pk)
