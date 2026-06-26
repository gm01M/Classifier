from django.contrib import admin

from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "age",
        "gender",
        "country_of_origin",
        "place_of_living",
        "status",
        "consistency",
        "created_at",
    )
    list_filter = ("status", "consistency", "gender", "country_of_origin")
    search_fields = ("name", "description", "country_of_origin", "place_of_living")
    readonly_fields = (
        "id",
        "photo_key",
        "classification_result",
        "consistency",
        "verification",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"
