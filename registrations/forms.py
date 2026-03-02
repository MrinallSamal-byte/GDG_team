from django import forms
from .models import Registration


class RegistrationForm(forms.ModelForm):
    """Base registration form for events."""

    class Meta:
        model = Registration
        fields = ['registration_type', 'looking_for_team', 'preferred_role']
        widgets = {
            'registration_type': forms.RadioSelect(attrs={'class': 'form-radio'}),
            'preferred_role': forms.Select(attrs={'class': 'form-select'}),
            'looking_for_team': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class TeamRegistrationForm(forms.Form):
    """Additional fields for team creation during registration."""
    team_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Choose a team name'})
    )
    max_members = forms.IntegerField(
        min_value=2, max_value=10, initial=4,
        widget=forms.NumberInput(attrs={'class': 'form-input'})
    )
    open_for_requests = forms.BooleanField(
        required=False, initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )


class TechStackSelectionForm(forms.Form):
    """Tech stack selection for team event registrations."""
    primary_skills = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. React, Python, TensorFlow (comma-separated)'
        }),
        help_text='Your strongest skills (1-3 technologies)'
    )
    secondary_skills = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. Docker, MongoDB, AWS (comma-separated)'
        }),
        help_text='Additional skills you can contribute'
    )
