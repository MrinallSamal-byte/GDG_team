from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import UserProfile


class CampusArenaSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Ensure social-auth users have an app profile on first login."""

    def _sync_profile(self, sociallogin):
        user = getattr(sociallogin, "user", None)
        if not user or not user.pk:
            return None

        profile, _ = UserProfile.objects.get_or_create(user=user)
        email_addresses = getattr(sociallogin, "email_addresses", [])
        has_verified_email = any(
            getattr(email_address, "verified", False)
            for email_address in email_addresses
        )
        if has_verified_email and not profile.email_verified:
            profile.email_verified = True
            profile.save(update_fields=["email_verified"])
        return profile

    def pre_social_login(self, request, sociallogin):
        super().pre_social_login(request, sociallogin)
        if getattr(sociallogin, "is_existing", False):
            self._sync_profile(sociallogin)

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        self._sync_profile(sociallogin)
        return user
