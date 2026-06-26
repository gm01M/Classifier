from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "full_name",
        "is_verified",
        "verification_attempts",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = ("is_verified", "is_staff", "is_active")
    search_fields = ("email", "full_name")
    actions = ("reset_verification", "mark_verified")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Profile",
            {
                "fields": (
                    "full_name",
                    "age",
                    "gender",
                    "place_of_living",
                    "country_of_origin",
                    "description",
                )
            },
        ),
        ("Verification", {"fields": ("is_verified", "verification_attempts")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "full_name", "password1", "password2")}),
    )

    @admin.action(description="Reset verification (unlock, clear attempts)")
    def reset_verification(self, request, queryset):
        n = queryset.update(verification_attempts=0, is_verified=False)
        self.message_user(request, f"Reset verification for {n} user(s).")

    @admin.action(description="Mark as verified")
    def mark_verified(self, request, queryset):
        n = queryset.update(is_verified=True)
        self.message_user(request, f"Marked {n} user(s) verified.")
