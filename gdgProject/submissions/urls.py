from django.urls import path

from . import views

app_name = "submissions"

urlpatterns = [
    path("event/<int:event_id>/submit/", views.submit_project, name="submit"),
    path("event/<int:event_id>/mine/", views.my_submission, name="my_submission"),
    path("event/<int:event_id>/review/", views.review_submissions, name="review"),
    path("<int:submission_id>/score/", views.score_submission, name="score"),
]
