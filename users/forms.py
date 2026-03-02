from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, UserTechStack


class RegistrationForm(UserCreationForm):
    """Multi-field registration form for new users."""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'you@college.edu', 'class': 'form-input'})
    )
    first_name = forms.CharField(
        max_length=50, widget=forms.TextInput(attrs={'placeholder': 'First name', 'class': 'form-input'})
    )
    last_name = forms.CharField(
        max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Last name', 'class': 'form-input'})
    )
    phone = forms.CharField(
        max_length=15, required=False,
        widget=forms.TextInput(attrs={'placeholder': '+91 98765 43210', 'class': 'form-input'})
    )
    college_name = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Your college or university', 'class': 'form-input'})
    )
    branch = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Computer Science', 'class': 'form-input'})
    )
    year_of_study = forms.ChoiceField(
        choices=[('', 'Select your year')] + User.YEAR_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone',
                  'college_name', 'branch', 'year_of_study', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Choose a username', 'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'placeholder': 'Create a strong password', 'class': 'form-input'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm your password', 'class': 'form-input'})


class LoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Username or email', 'class': 'form-input'})
        self.fields['password'].widget.attrs.update({'placeholder': 'Password', 'class': 'form-input'})


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'college_name', 'branch',
                  'year_of_study', 'bio', 'profile_picture', 'github_url',
                  'linkedin_url', 'portfolio_url']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'college_name': forms.TextInput(attrs={'class': 'form-input'}),
            'branch': forms.TextInput(attrs={'class': 'form-input'}),
            'year_of_study': forms.Select(attrs={'class': 'form-select'}),
            'bio': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'placeholder': 'Tell us about yourself...'}),
            'github_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://github.com/you'}),
            'linkedin_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://linkedin.com/in/you'}),
            'portfolio_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://yourportfolio.com'}),
        }


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Enter your registered email', 'class': 'form-input'}))


class ResetPasswordForm(forms.Form):
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'New password', 'class': 'form-input'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm new password', 'class': 'form-input'}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password1') != cleaned.get('password2'):
            raise forms.ValidationError("Passwords don't match.")
        return cleaned


class TechStackForm(forms.ModelForm):
    class Meta:
        model = UserTechStack
        fields = ['tech_name', 'proficiency', 'is_primary']
        widgets = {
            'tech_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. React, Python, Figma'}),
            'proficiency': forms.Select(attrs={'class': 'form-select'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

TechStackFormSet = forms.inlineformset_factory(
    User, UserTechStack, form=TechStackForm,
    extra=3, can_delete=True, max_num=15
)
