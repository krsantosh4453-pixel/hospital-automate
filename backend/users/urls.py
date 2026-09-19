from django.urls import path

from .views import google_login


urlpatterns = [
    path("google/", google_login, name="google-login"),
]