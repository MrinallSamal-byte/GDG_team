from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("initiate/<int:registration_id>/", views.initiate_payment, name="initiate"),
    path("callback/", views.payment_callback, name="callback"),
    path("success/<int:registration_id>/", views.payment_success, name="success"),
    path("failed/<int:registration_id>/", views.payment_failed, name="failed"),
]
