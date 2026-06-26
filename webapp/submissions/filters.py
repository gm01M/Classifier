"""Filters powering the admin search/filter (age range, gender, location, country)."""

import django_filters

from .models import Gender, Submission


class SubmissionFilter(django_filters.FilterSet):
    age_min = django_filters.NumberFilter(field_name="age", lookup_expr="gte")
    age_max = django_filters.NumberFilter(field_name="age", lookup_expr="lte")
    gender = django_filters.ChoiceFilter(choices=Gender.choices)
    # `location` maps to place_of_living; case-insensitive contains.
    location = django_filters.CharFilter(field_name="place_of_living", lookup_expr="icontains")
    country = django_filters.CharFilter(field_name="country_of_origin", lookup_expr="icontains")
    # Free-text search across name + description.
    q = django_filters.CharFilter(method="filter_q")
    status = django_filters.CharFilter(field_name="status")

    class Meta:
        model = Submission
        fields = ["age_min", "age_max", "gender", "location", "country", "status", "q"]

    def filter_q(self, queryset, name, value):
        from django.db.models import Q

        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))
