from django.urls import path

from . import views

app_name = "certificates"

urlpatterns = [
    path("", views.my_certificates, name="my_certificates"),
    path("download/<int:certificate_id>/", views.download_certificate, name="download"),
    path("verify/<uuid:token>/", views.verify_certificate, name="verify"),
    path("issue/<int:registration_id>/", views.issue_certificate, name="issue"),
]
