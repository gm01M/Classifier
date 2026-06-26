"""Shared enums/validators used by both the accounts profile and submissions.

Kept in a neutral module so `accounts` and `submissions` can both import them
without creating a cross-app model import cycle.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"
    UNDISCLOSED = "undisclosed", "Prefer not to say"


AGE_VALIDATORS = [MinValueValidator(0), MaxValueValidator(120)]
