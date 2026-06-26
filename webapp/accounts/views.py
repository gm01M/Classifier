"""HTMX auth pages: register, login, logout (session-based for the browser UI)."""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View

from .forms import EmailAuthenticationForm, ProfileForm, RegisterForm


class RegisterView(View):
    template_name = "accounts/register.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("submissions:list")
        return render(request, self.template_name, {"form": RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # Straight into identity verification after onboarding.
            return redirect("verify:start")
        return render(request, self.template_name, {"form": form})


class EmailLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


def logout_view(request):
    logout(request)
    return redirect(reverse_lazy("accounts:login"))


@method_decorator(login_required, name="dispatch")
class ProfileView(View):
    """View/edit the onboarding profile. New submissions snapshot the latest values."""

    template_name = "accounts/profile.html"

    def get(self, request):
        return render(request, self.template_name, {"form": ProfileForm(instance=request.user)})

    def post(self, request):
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile")
        return render(request, self.template_name, {"form": form})
