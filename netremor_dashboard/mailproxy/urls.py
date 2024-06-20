from django.urls import path

from . import views

app_name = "mailproxy"
urlpatterns = [
    path("", views.index, name="index"),
]