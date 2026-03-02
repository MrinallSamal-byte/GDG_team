from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserTechStack


class TechStackInline(admin.TabularInline):
    model = UserTechStack
    extra = 1


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'college_name', 'email_verified']
    list_filter = ['role', 'email_verified', 'year_of_study', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'college_name']
    inlines = [TechStackInline]
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile', {
            'fields': ('phone', 'college_name', 'branch', 'year_of_study', 'bio', 'profile_picture')
        }),
        ('Social Links', {
            'fields': ('github_url', 'linkedin_url', 'portfolio_url')
        }),
        ('Platform', {
            'fields': ('role', 'email_verified', 'theme_preference')
        }),
    )
