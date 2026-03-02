from django import forms
from .models import Event, EventPrize, EventRound, EventFAQ, EventJudge, EventSponsor, EventAnnouncement, CustomFormField


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'category', 'banner_image', 'mode',
            'venue', 'platform_link', 'registration_start', 'registration_end',
            'event_start', 'event_end', 'submission_deadline', 'participation_type',
            'min_team_size', 'max_team_size', 'allow_team_creation', 'allow_join_requests',
            'eligibility', 'prize_pool_total', 'has_participation_certificate',
            'has_merit_certificate', 'max_participants', 'registration_fee',
            'contact_email', 'contact_phone', 'rules', 'status',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Give your event a compelling title'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 6, 'placeholder': 'Describe what participants can expect...'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'mode': forms.Select(attrs={'class': 'form-select'}),
            'venue': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Physical venue address'}),
            'platform_link': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'Online meeting link'}),
            'registration_start': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'registration_end': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'event_start': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'event_end': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'submission_deadline': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'participation_type': forms.Select(attrs={'class': 'form-select'}),
            'min_team_size': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '2'}),
            'max_team_size': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '5'}),
            'eligibility': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Who can participate?'}),
            'prize_pool_total': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0'}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Leave blank for unlimited'}),
            'registration_fee': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0 for free'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'organizer@college.edu'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 ...'}),
            'rules': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 5, 'placeholder': 'Rules and guidelines...'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class EventPrizeForm(forms.ModelForm):
    class Meta:
        model = EventPrize
        fields = ['position', 'prize_amount', 'prize_description']
        widgets = {
            'position': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '1st Place'}),
            'prize_amount': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '10000'}),
            'prize_description': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Cash + goodies'}),
        }


class EventRoundForm(forms.ModelForm):
    class Meta:
        model = EventRound
        fields = ['round_number', 'round_name', 'description', 'start_date', 'end_date', 'elimination_criteria']
        widgets = {
            'round_number': forms.NumberInput(attrs={'class': 'form-input'}),
            'round_name': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'elimination_criteria': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
        }


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = EventAnnouncement
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Announcement title'}),
            'content': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'placeholder': 'What would you like to share?'}),
        }


class CustomFormFieldForm(forms.ModelForm):
    class Meta:
        model = CustomFormField
        fields = ['field_label', 'field_type', 'field_options', 'is_required', 'display_order', 'placeholder']
        widgets = {
            'field_label': forms.TextInput(attrs={'class': 'form-input'}),
            'field_type': forms.Select(attrs={'class': 'form-select'}),
            'field_options': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': '["Option 1", "Option 2"]'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-input'}),
            'placeholder': forms.TextInput(attrs={'class': 'form-input'}),
        }


PrizeFormSet = forms.inlineformset_factory(Event, EventPrize, form=EventPrizeForm, extra=3, can_delete=True)
RoundFormSet = forms.inlineformset_factory(Event, EventRound, form=EventRoundForm, extra=2, can_delete=True)
FAQFormSet = forms.inlineformset_factory(Event, EventFAQ, extra=2, can_delete=True, fields=['question', 'answer', 'display_order'])
CustomFieldFormSet = forms.inlineformset_factory(Event, CustomFormField, form=CustomFormFieldForm, extra=2, can_delete=True)
