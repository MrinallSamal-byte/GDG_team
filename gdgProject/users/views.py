from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .models import UserProfile


def _get_or_create_profile(user):
    """Return the UserProfile for *user*, creating one if missing."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:user_dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

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
            return redirect(next_url if next_url else 'dashboard:user_dashboard')
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
        if password and len(password) < 8:
            errors.append('Password must be at least 8 characters.')
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

        # Build a unique username from email prefix
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

        # Create profile with extended data
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
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if not email:
            messages.error(request, 'Please enter your email address.')
        else:
            # Always show success to prevent email enumeration
            messages.success(
                request,
                'If that email is registered, a reset link has been sent. Check your inbox.',
            )
        return redirect('users:forgot_password')

    return render(request, 'users/forgot_password.html')


@login_required
@require_http_methods(['GET', 'POST'])
def email_verification_view(request):
    if request.method == 'POST':
        otp_parts = [request.POST.get(f'otp_{i}', '') for i in range(1, 7)]
        otp = ''.join(otp_parts).strip()
        if len(otp) == 6 and otp.isdigit():
            # Mark profile as verified
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
    """Log the user out. Accepts both GET and POST for compatibility,
    but the template should use POST via a form."""
    logout(request)
    messages.info(request, 'You have been signed out.')
    return redirect('events:home')


# ── Profile editing ───────────────────────────────────────────────────────────

_ALL_SKILLS = [
    'Python', 'Django', 'JavaScript', 'TypeScript', 'React', 'Vue', 'Angular',
    'Node.js', 'Express', 'FastAPI', 'Flask', 'Java', 'Spring Boot', 'Kotlin',
    'Swift', 'Flutter', 'Dart', 'Go', 'Rust', 'C', 'C++', 'C#', '.NET',
    'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Docker', 'Kubernetes', 'AWS',
    'GCP', 'Azure', 'Linux', 'Figma', 'TensorFlow', 'PyTorch',
]

BRANCHES = ['CSE', 'IT', 'ECE', 'EEE', 'Mechanical', 'Civil', 'Biotech']
YEARS = [1, 2, 3, 4, 5]


@login_required
@require_http_methods(['GET', 'POST'])
def edit_profile(request):
    profile = _get_or_create_profile(request.user)

    if request.method == 'POST':
        # User fields
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()

        if full_name:
            parts = full_name.split(' ', 1)
            request.user.first_name = parts[0]
            request.user.last_name = parts[1] if len(parts) > 1 else ''

        if email and email != request.user.email:
            if User.objects.filter(email=email).exclude(pk=request.user.pk).exists():
                messages.error(request, 'That email is already in use.')
                return redirect('users:edit_profile')
            request.user.email = email

        request.user.save()

        # Profile fields
        profile.phone = request.POST.get('phone', '').strip()
        profile.college = request.POST.get('college', '').strip()
        profile.branch = request.POST.get('branch', '').strip()
        bio = request.POST.get('bio', '').strip()
        profile.bio = bio
        github = request.POST.get('github', '').strip()
        profile.github = github
        linkedin = request.POST.get('linkedin', '').strip()
        profile.linkedin = linkedin
        skills_raw = request.POST.get('skills', '').strip()
        profile.skills = skills_raw
        year_raw = request.POST.get('year', '')
        try:
            profile.year = int(year_raw) if year_raw else None
        except ValueError:
            pass
        profile.save()

        messages.success(request, 'Profile updated successfully!')
        return redirect('dashboard:my_profile')

    context = {
        'profile': profile,
        'user': request.user,
        'skills': _ALL_SKILLS,
        'active_skills': profile.skills_list,
        'branches': BRANCHES,
        'years': YEARS,
        'current_page': 'profile',
    }
    return render(request, 'users/edit_profile.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def change_password(request):
    from django.contrib.auth import update_session_auth_hash

    if request.method == 'POST':
        current = request.POST.get('current_password', '')
        new_pw = request.POST.get('new_password', '')
        confirm = request.POST.get('confirm_password', '')

        if not request.user.check_password(current):
            messages.error(request, 'Current password is incorrect.')
        elif len(new_pw) < 8:
            messages.error(request, 'New password must be at least 8 characters.')
        elif new_pw != confirm:
            messages.error(request, 'New passwords do not match.')
        else:
            request.user.set_password(new_pw)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully!')
            return redirect('dashboard:settings')

    return render(request, 'users/change_password.html', {'current_page': 'settings'})
