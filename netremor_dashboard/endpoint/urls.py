from django.urls import path

from . import views

app_name = "endpoint"
urlpatterns = [
    path("ambulatory/", views.ambulatory, name="ambulatory"),
    path("ambulatory", views.ambulatory, name="ambulatory"),
    path("continuous/", views.continuous, name="continuous"),
    path("continuous", views.continuous, name="continuous"),
]