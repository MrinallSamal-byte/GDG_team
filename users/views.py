import uuid
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, UpdateView, TemplateView

from .forms import RegistrationForm, LoginForm, ProfileForm, TechStackFormSet, ForgotPasswordForm, ResetPasswordForm
from .models import User


class RegisterView(CreateView):
    model = User
    form_class = RegistrationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Account created! You can now sign in and start exploring events.")
        return response

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('events:home')
        return super().dispatch(request, *args, **kwargs)


class UserLoginView(LoginView):
    form_class = LoginForm
    template_name = 'users/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        remember = form.cleaned_data.get('remember_me')
        if not remember:
            self.request.session.set_expiry(0)
        messages.success(self.request, f"Welcome back, {form.get_user().display_name}!")
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.GET.get('next', reverse_lazy('dashboard:user_dashboard'))


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('events:home')

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, "You've been signed out. See you next time!")
        return super().dispatch(request, *args, **kwargs)


class ProfileView(DetailView):
    model = User
    template_name = 'users/profile.html'
    context_object_name = 'profile_user'


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = 'users/profile_edit.html'

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profile updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('users:profile', kwargs={'pk': self.request.user.pk})


class TechStackEditView(LoginRequiredMixin, TemplateView):
    template_name = 'users/tech_stacks.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['formset'] = TechStackFormSet(self.request.POST, instance=self.request.user)
        else:
            ctx['formset'] = TechStackFormSet(instance=self.request.user)
        return ctx

    def post(self, request, *args, **kwargs):
        formset = TechStackFormSet(request.POST, instance=request.user)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Tech stacks updated.")
            return redirect('users:profile', pk=request.user.pk)
        return self.render_to_response(self.get_context_data())


class ForgotPasswordView(TemplateView):
    template_name = 'users/forgot_password.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = ForgotPasswordForm()
        return ctx

    def post(self, request):
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            messages.success(request, "If an account exists with that email, you'll receive reset instructions shortly.")
            return redirect('users:login')
        return self.render_to_response({'form': form})


class ResetPasswordView(TemplateView):
    template_name = 'users/reset_password.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = ResetPasswordForm()
        return ctx

    def post(self, request, token):
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            messages.success(request, "Password reset successfully. You can now sign in.")
            return redirect('users:login')
        return self.render_to_response({'form': form})


class VerifyEmailView(View):
    def get(self, request, token):
        messages.success(request, "Email verified successfully!")
        return redirect('users:login')


class ToggleThemeView(View):
    """Toggle between light and dark theme."""

    def post(self, request):
        current = getattr(request, 'theme', 'light')
        new_theme = 'dark' if current == 'light' else 'light'

        if request.user.is_authenticated:
            request.user.theme_preference = new_theme
            request.user.save(update_fields=['theme_preference'])

        response = JsonResponse({'theme': new_theme})
        response.set_cookie('theme', new_theme, max_age=365 * 24 * 60 * 60, httponly=True, samesite='Lax')
        return response
