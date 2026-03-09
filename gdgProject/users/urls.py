from django.urls import path

from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.reset_password_view, name='reset_password'),
    path('verify-email/', views.email_verification_view, name='verify_email'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('auth/change-password/', views.change_password, name='change_password'),
]
