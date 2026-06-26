"""HTMX auth page routes mounted under /accounts/."""

from django.urls import path

from .views import EmailLoginView, ProfileView, RegisterView, logout_view

app_name = "accounts"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", EmailLoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
]
