"""Server-rendered submission form for the HTMX UI (photo-only)."""

from django import forms

from common.image_safety import ImageValidationError, validate_and_sanitize


class SubmissionForm(forms.Form):
    """A submission only needs a photo; metadata is snapshotted from the profile.

    Uses FileField (not ImageField) so our own ``validate_and_sanitize`` is the
    single source of truth — it gives clear messages and accepts HEIC/AVIF, which
    Django's stock ImageField rejects.
    """

    photo = forms.FileField(
        widget=forms.ClearableFileInput(attrs={"accept": "image/*,.heic,.heif"})
    )

    def clean_photo(self):
        photo = self.cleaned_data["photo"]
        raw = photo.read()
        try:
            validate_and_sanitize(raw, getattr(photo, "content_type", ""))
        except ImageValidationError as exc:
            raise forms.ValidationError(str(exc)) from exc
        self._raw_photo = raw
        self._declared_type = getattr(photo, "content_type", "")
        return photo
