from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Count
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView

from .models import Event, EventAnnouncement
from .forms import EventForm, AnnouncementForm, PrizeFormSet, RoundFormSet


class HomeView(TemplateView):
    """Landing page with featured events, search, and filtered listings."""
    template_name = 'events/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        published = Event.objects.filter(status='published', is_archived=False)

        ctx['featured_events'] = published.filter(is_featured=True)[:6]
        ctx['upcoming_events'] = published.filter(event_start__gte=now).order_by('event_start')[:9]
        ctx['total_events'] = published.count()
        ctx['total_registrations'] = sum(e.registration_count for e in published[:50])

        # Category counts for filter
        ctx['categories'] = Event.CATEGORY_CHOICES
        return ctx


class EventListView(ListView):
    """Browse all events with filters and search."""
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    paginate_by = 12

    def get_queryset(self):
        qs = Event.objects.filter(status='published', is_archived=False)

        # Search
        q = self.request.GET.get('q', '')
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

        # Filters
        category = self.request.GET.get('category')
        if category:
            qs = qs.filter(category=category)

        mode = self.request.GET.get('mode')
        if mode:
            qs = qs.filter(mode=mode)

        status_filter = self.request.GET.get('status')
        now = timezone.now()
        if status_filter == 'open':
            qs = qs.filter(registration_start__lte=now, registration_end__gte=now)
        elif status_filter == 'ongoing':
            qs = qs.filter(event_start__lte=now, event_end__gte=now)
        elif status_filter == 'completed':
            qs = qs.filter(event_end__lt=now)

        fee = self.request.GET.get('fee')
        if fee == 'free':
            qs = qs.filter(registration_fee=0)
        elif fee == 'paid':
            qs = qs.filter(registration_fee__gt=0)

        # Sort
        sort = self.request.GET.get('sort', 'newest')
        if sort == 'deadline':
            qs = qs.filter(registration_end__gte=now).order_by('registration_end')
        elif sort == 'popular':
            qs = qs.annotate(reg_count=Count('registrations')).order_by('-reg_count')
        else:
            qs = qs.order_by('-created_at')

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = Event.CATEGORY_CHOICES
        ctx['current_filters'] = {
            'q': self.request.GET.get('q', ''),
            'category': self.request.GET.get('category', ''),
            'mode': self.request.GET.get('mode', ''),
            'status': self.request.GET.get('status', ''),
            'fee': self.request.GET.get('fee', ''),
            'sort': self.request.GET.get('sort', 'newest'),
        }
        return ctx


class EventDetailView(DetailView):
    """Event detail page with tabbed content."""
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'

    def get_queryset(self):
        return Event.objects.filter(is_archived=False)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = self.object
        ctx['prizes'] = event.prizes.all()
        ctx['rounds'] = event.rounds.all()
        ctx['faqs'] = event.faqs.all()
        ctx['judges'] = event.judges.all()
        ctx['sponsors'] = event.sponsors.all()
        ctx['announcements'] = event.announcements.all()[:5]

        if self.request.user.is_authenticated:
            ctx['user_registration'] = event.registrations.filter(user=self.request.user).first()
            ctx['user_team'] = None
            reg = ctx['user_registration']
            if reg and reg.team:
                ctx['user_team'] = reg.team

        # Participants
        ctx['registrations'] = event.registrations.filter(status='confirmed').select_related('user', 'team')[:50]
        ctx['teams'] = event.teams.all().prefetch_related('members__user')
        ctx['looking_for_team'] = event.registrations.filter(
            status='confirmed', looking_for_team=True, team__isnull=True
        ).select_related('user')
        ctx['open_teams'] = event.teams.filter(is_open=True)

        return ctx


class OrganizerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_organizer


class EventCreateView(OrganizerRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['prize_formset'] = PrizeFormSet(self.request.POST, prefix='prizes')
            ctx['round_formset'] = RoundFormSet(self.request.POST, prefix='rounds')
        else:
            ctx['prize_formset'] = PrizeFormSet(prefix='prizes')
            ctx['round_formset'] = RoundFormSet(prefix='rounds')
        ctx['form_title'] = 'Create Event'
        return ctx

    def form_valid(self, form):
        form.instance.organizer = self.request.user
        ctx = self.get_context_data()
        prize_fs = ctx['prize_formset']
        round_fs = ctx['round_formset']

        if prize_fs.is_valid() and round_fs.is_valid():
            self.object = form.save()
            prize_fs.instance = self.object
            prize_fs.save()
            round_fs.instance = self.object
            round_fs.save()
            messages.success(self.request, f'"{self.object.title}" has been created. Publish it when you\'re ready.')
            return redirect(self.object.get_absolute_url())
        return self.form_invalid(form)


class EventEditView(OrganizerRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['prize_formset'] = PrizeFormSet(self.request.POST, instance=self.object, prefix='prizes')
            ctx['round_formset'] = RoundFormSet(self.request.POST, instance=self.object, prefix='rounds')
        else:
            ctx['prize_formset'] = PrizeFormSet(instance=self.object, prefix='prizes')
            ctx['round_formset'] = RoundFormSet(instance=self.object, prefix='rounds')
        ctx['form_title'] = 'Edit Event'
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        prize_fs = ctx['prize_formset']
        round_fs = ctx['round_formset']

        if prize_fs.is_valid() and round_fs.is_valid():
            self.object = form.save()
            prize_fs.save()
            round_fs.save()
            messages.success(self.request, 'Event updated successfully.')
            return redirect(self.object.get_absolute_url())
        return self.form_invalid(form)

    def test_func(self):
        event = self.get_object()
        return self.request.user == event.organizer or self.request.user.is_admin


class EventDeleteView(OrganizerRequiredMixin, DeleteView):
    model = Event
    template_name = 'events/event_confirm_delete.html'
    success_url = reverse_lazy('events:home')

    def form_valid(self, form):
        self.object.is_archived = True
        self.object.save()
        messages.success(self.request, 'Event archived successfully.')
        return redirect(self.success_url)

    def test_func(self):
        event = self.get_object()
        return self.request.user == event.organizer or self.request.user.is_admin


class AnnouncementCreateView(OrganizerRequiredMixin, CreateView):
    model = EventAnnouncement
    form_class = AnnouncementForm
    template_name = 'events/announcement_form.html'

    def form_valid(self, form):
        event = get_object_or_404(Event, pk=self.kwargs['pk'])
        form.instance.event = event
        messages.success(self.request, 'Announcement posted.')
        response = super().form_valid(form)
        # Create notifications for registered participants
        from notifications.models import Notification
        for reg in event.registrations.filter(status='confirmed').select_related('user'):
            Notification.create_notification(
                user=reg.user,
                title=f'New announcement: {form.instance.title}',
                message=form.instance.content[:200],
                notification_type='announcement',
                reference_id=event.pk,
                reference_type='event',
            )
        return response

    def get_success_url(self):
        return reverse_lazy('events:event_detail', kwargs={'pk': self.kwargs['pk']})

    def test_func(self):
        event = get_object_or_404(Event, pk=self.kwargs['pk'])
        return self.request.user == event.organizer or self.request.user.is_admin
