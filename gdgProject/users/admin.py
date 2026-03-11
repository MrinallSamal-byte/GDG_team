from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import UserProfile, UserTechStack


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"


class UserTechStackInline(admin.TabularInline):
    model = UserTechStack
    extra = 0


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline, UserTechStackInline)
    list_display = ("username", "email", "first_name", "last_name", "is_staff")
    list_select_related = ("profile",)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
