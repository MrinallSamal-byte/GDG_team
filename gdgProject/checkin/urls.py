from django.urls import path

from . import views

app_name = "checkin"

urlpatterns = [
    path("event/<int:event_id>/qr/", views.my_qr_code, name="my_qr"),
    path("event/<int:event_id>/qr.png", views.qr_image, name="qr_image"),
    path("event/<int:event_id>/dashboard/", views.checkin_dashboard, name="dashboard"),
    path("event/<int:event_id>/bulk-generate/", views.bulk_generate_qr, name="bulk_generate"),
    path("scan/<uuid:token>/", views.scan_qr, name="scan"),
    path("confirm/<uuid:token>/", views.confirm_checkin, name="confirm"),
]
