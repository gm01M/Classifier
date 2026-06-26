"""DRF serializers for submissions (validation + documented API shapes)."""

from rest_framework import serializers

from common.image_safety import ImageValidationError, validate_and_sanitize

from .models import Submission


class SubmissionCreateSerializer(serializers.Serializer):
    """Photo-only create: metadata is snapshotted from the user's profile.

    Uses FileField (not ImageField) so ``validate_and_sanitize`` is authoritative
    and HEIC/AVIF uploads are accepted (Django/DRF ImageField would reject them).
    """

    photo = serializers.FileField(write_only=True)

    def validate_photo(self, value):
        # Read once and run the safety pipeline early so bad files 400 cleanly.
        raw = value.read()
        try:
            validate_and_sanitize(raw, getattr(value, "content_type", ""))
        except ImageValidationError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        # Stash raw bytes for the view to hand to the service layer.
        self._raw_photo = raw
        self._declared_type = getattr(value, "content_type", "")
        return value


class SubmissionSerializer(serializers.ModelSerializer):
    """Read serializer; includes a short-lived presigned photo URL."""

    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = (
            "id",
            "name",
            "age",
            "place_of_living",
            "gender",
            "country_of_origin",
            "description",
            "photo_url",
            "status",
            "classification_result",
            "consistency",
            "verification",
            "error_detail",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_photo_url(self, obj) -> str:
        from common.storage import presigned_get_url

        return presigned_get_url(obj.photo_key)
