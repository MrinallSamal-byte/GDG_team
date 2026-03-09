from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect, render
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_GET, require_http_methods

from .models import UserProfile


def _get_or_create_profile(user):
    """Return the UserProfile for *user*, creating one if missing."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('eventManagement:organizer_dashboard')
        return redirect('dashboard:user_dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        role = request.POST.get('roleLogin', 'student')

        if not email or not password:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'users/login.html', {'email': email})

        user = None
        try:
            db_user = User.objects.get(email=email)
            user = authenticate(request, username=db_user.username, password=password)
        except User.DoesNotExist:
            pass

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            next_url = request.GET.get('next', '')
            if next_url:
                return redirect(next_url)
            if role == 'admin' or user.is_staff:
                return redirect('eventManagement:organizer_dashboard')
            return redirect('dashboard:user_dashboard')
        else:
            messages.error(request, 'Invalid email or password. Please try again.')
            return render(request, 'users/login.html', {'email': email})

    return render(request, 'users/login.html')


@require_http_methods(['GET', 'POST'])
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:user_dashboard')

    branches = ['CSE', 'IT', 'ECE', 'EEE', 'Mechanical', 'Civil', 'Biotech']
    years = [1, 2, 3, 4, 5]

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        college = request.POST.get('college', '').strip()
        branch = request.POST.get('branch', '').strip()
        year = request.POST.get('year', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        skills = request.POST.get('skills', '').strip()

        errors = []
        if not all([full_name, email, college, branch, year, password]):
            errors.append('Please fill in all required fields.')
        if password and password_confirm and password != password_confirm:
            errors.append('Passwords do not match.')
        if password and len(password) < 10:
            errors.append('Password must be at least 10 characters.')
        if email and User.objects.filter(email=email).exists():
            errors.append('An account with this email already exists. Try logging in.')

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'users/register.html', {
                'branches': branches,
                'years': years,
                'form_data': request.POST,
            })

        base_username = email.split('@')[0]
        username = base_username
        i = 1
        while User.objects.filter(username=username).exists():
            username = f'{base_username}{i}'
            i += 1

        name_parts = full_name.split(' ', 1)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=name_parts[0],
            last_name=name_parts[1] if len(name_parts) > 1 else '',
        )

        year_int = None
        try:
            year_int = int(year)
        except (ValueError, TypeError):
            pass

        UserProfile.objects.create(
            user=user,
            phone=phone,
            college=college,
            branch=branch,
            year=year_int,
            skills=skills,
        )

        login(request, user)
        messages.success(
            request,
            f'Welcome to CampusArena, {user.first_name}! '
            'Verify your email to get started.',
        )
        return redirect('users:verify_email')

    return render(request, 'users/register.html', {'branches': branches, 'years': years})


@require_http_methods(['GET', 'POST'])
def forgot_password_view(request):
    """Send a password reset link to the user's email."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if not email:
            messages.error(request, 'Please enter your email address.')
            return redirect('users:forgot_password')

        try:
            user = User.objects.get(email=email)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = request.build_absolute_uri(f'/auth/reset-password/{uid}/{token}/')
            from django.core.mail import send_mail
            try:
                send_mail(
                    subject='CampusArena — Password Reset',
                    message=(
                        f'Hi {user.first_name or user.username},\n\n'
                        f'Click the link below to reset your password:\n{reset_url}\n\n'
                        'This link will expire in 24 hours.\n\n'
                        'If you did not request this, you can ignore this email.\n\n'
                        'Team CampusArena'
                    ),
                    from_email=None,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception:
                import logging
                logging.getLogger(__name__).error(
                    "Failed to send password reset email to %s", email, exc_info=True
                )
        except User.DoesNotExist:
            pass  # Don't reveal whether the email exists

        messages.success(
            request,
            'If that email is registered, a reset link has been sent. Check your inbox.',
        )
        return redirect('users:forgot_password')

    return render(request, 'users/forgot_password.html')


@require_http_methods(['GET', 'POST'])
def reset_password_view(request, uidb64, token):
    """Reset password using the token from the email link."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, 'This password reset link is invalid or has expired.')
        return redirect('users:forgot_password')

    if request.method == 'POST':
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        if not password or not password_confirm:
            messages.error(request, 'Please fill in both password fields.')
            return render(request, 'users/reset_password.html', {'valid_link': True})

        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'users/reset_password.html', {'valid_link': True})

        if len(password) < 10:
            messages.error(request, 'Password must be at least 10 characters.')
            return render(request, 'users/reset_password.html', {'valid_link': True})

        user.set_password(password)
        user.save()
        messages.success(request, 'Your password has been reset. You can now log in.')
        return redirect('users:login')

    return render(request, 'users/reset_password.html', {'valid_link': True})


@login_required
@require_http_methods(['GET', 'POST'])
def email_verification_view(request):
    if request.method == 'POST':
        otp_parts = [request.POST.get(f'otp_{i}', '') for i in range(1, 7)]
        otp = ''.join(otp_parts).strip()
        if len(otp) == 6 and otp.isdigit():
            profile = _get_or_create_profile(request.user)
            profile.email_verified = True
            profile.save(update_fields=['email_verified'])
            messages.success(request, 'Email verified! Welcome aboard.')
            return redirect('dashboard:user_dashboard')
        else:
            messages.error(request, 'Invalid or incomplete code. Please try again.')

    return render(request, 'users/email_verification.html')


@require_http_methods(['GET', 'POST'])
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been signed out.')
    return redirect('events:home')