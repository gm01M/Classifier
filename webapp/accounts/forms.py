"""Server-rendered forms for the HTMX UI."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

# Profile fields collected at onboarding and editable later on the profile page.
PROFILE_FIELDS = (
    "full_name",
    "age",
    "place_of_living",
    "gender",
    "country_of_origin",
    "description",
)


class EmailAuthenticationForm(AuthenticationForm):
    """Login form keyed on email (USERNAME_FIELD = email)."""

    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autofocus": True}))


class RegisterForm(forms.ModelForm):
    """Onboarding: account credentials + full profile metadata in one step."""

    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    password_confirm = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", *PROFILE_FIELDS)
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Profile metadata is required at onboarding (per the brief).
        for name in ("full_name", "age", "place_of_living", "gender", "country_of_origin"):
            self.fields[name].required = True

    def clean_password(self):
        pw = self.cleaned_data["password"]
        validate_password(pw)
        return pw

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password_confirm"):
            self.add_error("password_confirm", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """Edit the onboarding profile later; future submissions snapshot the latest."""

    class Meta:
        model = User
        fields = PROFILE_FIELDS
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("full_name", "age", "place_of_living", "gender", "country_of_origin"):
            self.fields[name].required = True
