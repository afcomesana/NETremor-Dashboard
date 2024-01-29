from django.urls import path

from . import views

app_name = "dashboard"
urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout_user, name="logout"),
    path("records/<str:subject_id>/", views.records, name="records"),
    path("record/<int:record_id>/", views.record, name="record"),
    path("verification/", views.verification_form, name="verification_form"),
    path("verification/<int:user_id>/<str:verification_code>/", views.verification_process, name="verification_process"),
]