"""DRF serializers for accounts — validated registration + profile output."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()

# Profile metadata collected at onboarding (per the brief).
PROFILE_FIELDS = (
    "full_name",
    "age",
    "place_of_living",
    "gender",
    "country_of_origin",
    "description",
)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = ("id", "email", *PROFILE_FIELDS, "password")
        read_only_fields = ("id",)
        extra_kwargs = {
            # Description stays optional; the rest are required at onboarding.
            "full_name": {"required": True},
            "age": {"required": True},
            "place_of_living": {"required": True},
            "gender": {"required": True},
            "country_of_origin": {"required": True},
        }

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class UserSerializer(serializers.ModelSerializer):
    is_admin = serializers.BooleanField(source="is_staff", read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", *PROFILE_FIELDS, "is_admin", "date_joined")
        read_only_fields = fields


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Update the onboarding profile; future submissions snapshot the latest."""

    class Meta:
        model = User
        fields = PROFILE_FIELDS
        extra_kwargs = {
            "full_name": {"required": True},
            "age": {"required": True},
            "place_of_living": {"required": True},
            "gender": {"required": True},
            "country_of_origin": {"required": True},
        }
