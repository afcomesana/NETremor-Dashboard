from django.urls import path

from . import views

app_name = "endpoint"
urlpatterns = [
    path("ambulatory/", views.save_record, name="ambulatory"),
    path("ambulatory", views.save_record, name="ambulatory"),
    path("continuous/", views.save_record, name="continuous"),
    path("continuous", views.save_record, name="continuous"),
]