import logging
import secrets
import time
from contextlib import suppress

from allauth.socialaccount.adapter import get_adapter
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    password_validation,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils.encoding import force_bytes, force_str

# from django.utils.http import urlsafe_base64_decode, urlsafe
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_http_methods

from .models import UserProfile
from .services import EmailDeliveryResult, send_plaintext_email

logger = logging.getLogger(__name__)


def _social_provider_is_configured(request, provider_id: str) -> bool:
    try:
        provider = get_adapter(request).get_provider(request, provider_id)
    except Exception:
        return False

    app = getattr(provider, "app", None)
    if app is None:
        return True
    return bool(getattr(app, "client_id", "") and getattr(app, "secret", ""))


def _login_context(request, **extra):
    context = {
        "google_oauth_enabled": _social_provider_is_configured(request, "google"),
    }
    context.update(extra)
    return context


def _get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def _absolute_auth_url(request, path: str) -> str:
    site_url = str(getattr(settings, "SITE_URL", "") or "").strip().rstrip("/")
    if site_url.startswith(("http://", "https://")):
        return f"{site_url}{path}"
    return request.build_absolute_uri(path)


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("eventManagement:organizer_dashboard")
        return redirect("dashboard:user_dashboard")

    if request.method == "POST":
        action = request.POST.get("action", "login")

        if action == "signup":
            email = request.POST.get("email", "").strip().lower()
            password = request.POST.get("password", "")

            if not email or not password:
                messages.error(request, "Email and password are required.")
                return render(
                    request,
                    "users/login.html",
                    _login_context(request, show_signup=True),
                )

            if len(password) < 10:
                messages.error(request, "Password must be at least 10 characters.")
                return render(
                    request,
                    "users/login.html",
                    _login_context(request, show_signup=True),
                )

            if User.objects.filter(email__iexact=email).exists():
                messages.error(
                    request,
                    "An account with this email already exists. Please log in.",
                )
                return render(
                    request,
                    "users/login.html",
                    _login_context(request, show_signup=False),
                )

            try:
                password_validation.validate_password(password)
            except ValidationError as exc:
                for err in exc.messages:
                    messages.error(request, err)
                return render(
                    request,
                    "users/login.html",
                    _login_context(request, show_signup=True),
                )

            base_username = email.split("@")[0]
            username = base_username
            i = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{i}"
                i += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
            )
            UserProfile.objects.create(user=user)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            logger.info("Quick signup completed for user %d (%s)", user.pk, email)
            messages.success(
                request,
                "Account created! Complete your profile to get started.",
            )
            return redirect("users:verify_email")

        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        role = request.POST.get("roleLogin", "student")

        if not email or not password:
            messages.error(request, "Please fill in all required fields.")
            return render(
                request,
                "users/login.html",
                _login_context(request, email=email),
            )

        user = None
        try:
            db_user = User.objects.get(email__iexact=email)
            user = authenticate(request, username=db_user.username, password=password)
        except User.DoesNotExist:
            pass

        if user is not None:
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            if request.POST.get("remember"):
                request.session.set_expiry(60 * 60 * 24 * 30)
            else:
                request.session.set_expiry(0)
            messages.success(
                request, f"Welcome back, {user.first_name or user.username}!"
            )
            next_url = request.GET.get("next", "")
            if next_url:
                return redirect(next_url)
            if role == "admin" or user.is_staff:
                return redirect("eventManagement:organizer_dashboard")
            return redirect("dashboard:user_dashboard")
        else:
            messages.error(request, "Invalid email or password. Please try again.")
            return render(
                request,
                "users/login.html",
                _login_context(request, email=email),
            )

    return render(request, "users/login.html", _login_context(request))


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:user_dashboard")

    branches = ["CSE", "IT", "ECE", "EEE", "Mechanical", "Civil", "Biotech"]
    years = [1, 2, 3, 4, 5]

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        college = request.POST.get("college", "").strip()
        branch = request.POST.get("branch", "").strip()
        year = request.POST.get("year", "").strip()
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")
        skills = request.POST.get("skills", "").strip()

        errors = []
        if not all([full_name, email, college, branch, year, password]):
            errors.append("Please fill in all required fields.")
        if password and password_confirm and password != password_confirm:
            errors.append("Passwords do not match.")
        if email and User.objects.filter(email__iexact=email).exists():
            errors.append("An account with this email already exists. Try logging in.")
        if password and not errors:
            try:
                password_validation.validate_password(password)
            except ValidationError as exc:
                errors.extend(exc.messages)

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(
                request,
                "users/register.html",
                {
                    "branches": branches,
                    "years": years,
                    "form_data": request.POST,
                },
            )

        base_username = email.split("@")[0]
        username = base_username
        i = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{i}"
            i += 1

        name_parts = full_name.split(" ", 1)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=name_parts[0],
            last_name=name_parts[1] if len(name_parts) > 1 else "",
        )

        year_int = None
        with suppress(ValueError, TypeError):
            year_int = int(year)

        # UserProfile.objects.create(
        #     user=user,
        #     phone=phone,
        #     college=college,
        #     branch=branch,
        #     year=year_int,
        #     skills=skills,
        # )

        # login(request, user)

        UserProfile.objects.create(
            user=user,
            phone=phone,
            college=college,
            branch=branch,
            year=year_int,
            skills=skills,
        )

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")

        messages.success(
            request,
            f"Welcome to CampusArena, {user.first_name}! "
            "Verify your email to get started.",
        )
        return redirect("users:verify_email")

    return render(
        request, "users/register.html", {"branches": branches, "years": years}
    )


@require_http_methods(["GET", "POST"])
def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        if not email:
            messages.error(request, "Please enter your email address.")
            return redirect("users:forgot_password")

        user = User.objects.filter(email__iexact=email).first()
        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = _absolute_auth_url(
                request,
                f"/auth/reset-password/{uid}/{token}/",
            )
            delivery = send_plaintext_email(
                subject="CampusArena — Password Reset",
                body=(
                    f"Hi {user.first_name or user.username},\n\n"
                    f"Click the link below to reset your password:\n{reset_url}\n\n"
                    "This link will expire in 24 hours.\n\n"
                    "If you did not request this, you can ignore this email.\n\n"
                    "Team CampusArena"
                ),
                recipients=[user.email],
                log_context=f"password-reset user_id={user.pk}",
            )
            if not delivery.sent:
                messages.error(request, delivery.error_message)
                return redirect("users:forgot_password")

        messages.success(
            request,
            "If that email is registered, a reset link has been sent. Check your inbox.",
        )
        return redirect("users:forgot_password")

    return render(request, "users/forgot_password.html")


@require_http_methods(["GET", "POST"])
def reset_password_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "This password reset link is invalid or has expired.")
        return redirect("users:forgot_password")

    if request.method == "POST":
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")

        if not password or not password_confirm:
            messages.error(request, "Please fill in both password fields.")
            return render(request, "users/reset_password.html", {"valid_link": True})

        if password != password_confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, "users/reset_password.html", {"valid_link": True})

        try:
            password_validation.validate_password(password, user)
        except ValidationError as exc:
            for err in exc.messages:
                messages.error(request, err)
            return render(request, "users/reset_password.html", {"valid_link": True})

        user.set_password(password)
        user.save()
        messages.success(request, "Your password has been reset. You can now log in.")
        return redirect("users:login")

    return render(request, "users/reset_password.html", {"valid_link": True})


_OTP_SESSION_KEY = "email_otp_code"
_OTP_UID_KEY = "email_otp_uid"
_OTP_CREATED_KEY = "email_otp_created_at"


def _send_otp_email(user, otp: str) -> EmailDeliveryResult:
    expiry_minutes = getattr(settings, "OTP_EXPIRY_SECONDS", 600) // 60
    return send_plaintext_email(
        subject="CampusArena — Verify your email",
        body=(
            f"Hi {user.first_name or user.username},\n\n"
            f"Your email verification code is: {otp}\n\n"
            f"This code is valid for {expiry_minutes} minutes.\n"
            "If you did not request this, please ignore this email.\n\n"
            "Team CampusArena"
        ),
        recipients=[user.email],
        log_context=f"email-verification user_id={user.pk}",
    )


def _issue_otp(request) -> EmailDeliveryResult:
    """Generate a fresh OTP, send it, then persist it in session on success."""
    otp = f"{secrets.randbelow(1_000_000):06d}"
    delivery = _send_otp_email(request.user, otp)
    if not delivery.sent:
        return delivery

    request.session[_OTP_SESSION_KEY] = otp
    request.session[_OTP_UID_KEY] = request.user.pk
    request.session[_OTP_CREATED_KEY] = time.time()
    return delivery


def _otp_is_expired(request) -> bool:
    created_at = request.session.get(_OTP_CREATED_KEY)
    if created_at is None:
        return True
    expiry = getattr(settings, "OTP_EXPIRY_SECONDS", 600)
    return (time.time() - created_at) > expiry


@login_required
@require_http_methods(["GET", "POST"])
def email_verification_view(request):
    profile = _get_or_create_profile(request.user)

    if profile.email_verified:
        return redirect("dashboard:user_dashboard")

    if request.method == "POST":
        action = request.POST.get("action", "verify")

        if action == "resend":
            delivery = _issue_otp(request)
            if delivery.sent:
                messages.success(request, "A new code has been sent to your email.")
            else:
                messages.error(request, delivery.error_message)
            return redirect("users:verify_email")

        otp_parts = [request.POST.get(f"otp_{i}", "") for i in range(1, 7)]
        submitted = "".join(otp_parts).strip()
        stored_otp = request.session.get(_OTP_SESSION_KEY)
        stored_uid = request.session.get(_OTP_UID_KEY)

        if _otp_is_expired(request):
            messages.error(
                request,
                "This code has expired. Click 'Resend' to get a new one.",
            )
            return render(request, "users/email_verification.html", {"expired": True})

        if (
            len(submitted) == 6
            and submitted.isdigit()
            and stored_otp is not None
            and secrets.compare_digest(submitted, stored_otp)
            and stored_uid == request.user.pk
        ):
            profile.email_verified = True
            profile.save(update_fields=["email_verified"])
            for key in (_OTP_SESSION_KEY, _OTP_UID_KEY, _OTP_CREATED_KEY):
                request.session.pop(key, None)
            messages.success(request, "Email verified! Welcome aboard.")
            return redirect("dashboard:user_dashboard")
        else:
            messages.error(request, "Invalid or incomplete code. Please try again.")
            return render(request, "users/email_verification.html")

    # GET — issue OTP only if none exists or the stored one belongs to a different user
    if (
        request.session.get(_OTP_UID_KEY) != request.user.pk
        or _OTP_SESSION_KEY not in request.session
    ):
        delivery = _issue_otp(request)
        if not delivery.sent:
            messages.error(request, delivery.error_message)

    return render(request, "users/email_verification.html")


@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("events:home")


@login_required
@require_http_methods(["GET", "POST"])
def edit_profile(request):
    profile = _get_or_create_profile(request.user)
    branches = ["CSE", "IT", "ECE", "EEE", "Mechanical", "Civil", "Biotech"]
    years = [1, 2, 3, 4, 5]
    skills = [
        "React",
        "Node.js",
        "Python",
        "Django",
        "Flutter",
        "Figma",
        "TensorFlow",
        "Docker",
        "AWS",
        "MongoDB",
    ]

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip().lower()

        if (
            email
            and User.objects.filter(email__iexact=email)
            .exclude(pk=request.user.pk)
            .exists()
        ):
            messages.error(request, "That email is already in use by another account.")
            return render(
                request,
                "users/edit_profile.html",
                {
                    "profile": profile,
                    "branches": branches,
                    "years": years,
                    "skills": skills,
                    "active_skills": profile.skills_list,
                },
            )

        if full_name:
            parts = full_name.split(" ", 1)
            request.user.first_name = parts[0]
            request.user.last_name = parts[1] if len(parts) > 1 else ""
        if email:
            request.user.email = email
        request.user.save(update_fields=["first_name", "last_name", "email"])

        profile.phone = request.POST.get("phone", "").strip()
        profile.college = request.POST.get("college", "").strip()
        profile.branch = request.POST.get("branch", "").strip()
        profile.github = request.POST.get("github", "").strip()
        profile.linkedin = request.POST.get("linkedin", "").strip()
        profile.leetcode = request.POST.get("leetcode", "").strip()
        profile.portfolio = request.POST.get("portfolio", "").strip()
        profile.bio = request.POST.get("bio", "").strip()
        profile.skills = request.POST.get("skills", "").strip()
        if "profile_photo" in request.FILES:
            profile.profile_picture = request.FILES["profile_photo"]

        year = request.POST.get("year", "").strip()
        try:
            profile.year = int(year) if year else None
        except ValueError:
            profile.year = None

        profile.save()
        messages.success(request, "Your profile has been updated successfully.")
        return redirect("dashboard:my_profile")

    return render(
        request,
        "users/edit_profile.html",
        {
            "profile": profile,
            "branches": branches,
            "years": years,
            "skills": skills,
            "active_skills": profile.skills_list,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def change_password(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password", "")
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not request.user.check_password(current_password):
            messages.error(request, "Your current password is incorrect.")
            return render(request, "users/change_password.html")

        if new_password != confirm_password:
            messages.error(request, "New password and confirmation do not match.")
            return render(request, "users/change_password.html")

        try:
            password_validation.validate_password(new_password, request.user)
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            return render(request, "users/change_password.html")

        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])
        update_session_auth_hash(request, request.user)
        messages.success(request, "Your password has been updated successfully.")
        return redirect("dashboard:settings")

    return render(request, "users/change_password.html")


def public_profile(request, username):
    """Public read-only profile view matching dashboard design."""
    from django.shortcuts import get_object_or_404, render
    from django.contrib.auth import get_user_model
    from users.models import UserProfile
    from registration.models import Registration
    from team.models import TeamMembership
    from certificates.models import Certificate

    User = get_user_model()
    profile_user = get_object_or_404(User, username=username)
    profile, _ = UserProfile.objects.get_or_create(user=profile_user)

    cert_count = Certificate.objects.filter(user=profile_user).count()

    profile_data = {
        "name": profile_user.get_full_name() or profile_user.username,
        "email": profile_user.email,
        "phone": profile.phone or "Not set",
        "college": profile.college or "Not set",
        "branch": profile.branch or "Not set",
        "year": profile.year_display or "Not set",
        "github": profile.github or "",
        "linkedin": profile.linkedin or "",
        "leetcode": profile.leetcode or "",
        "portfolio": profile.portfolio or "",
        "bio": profile.bio or "No bio available.",
        "skills": profile.skills_list or [],
        "profile_picture_url": profile.profile_picture.url if profile.profile_picture else None,
    }

    stats = {
        "events_joined": Registration.objects.filter(user=profile_user).count(),
        "teams": TeamMembership.objects.filter(user=profile_user, team__is_deleted=False).count(),
        "certificates": cert_count,
    }

    return render(request, "users/public_profile.html", {
        "profile": profile_data,
        "stats": stats,
    })
