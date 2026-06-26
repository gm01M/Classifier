"""Custom user model — email is the login identifier (no username).

``is_staff`` doubles as the admin-role flag that gates the admin panel and the
admin API (RBAC, safety rule #5).
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from common.choices import AGE_VALIDATORS, Gender


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra.get("is_staff") is not True or extra.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_staff=is_superuser=True")
        return self._create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=150, blank=True)

    # Profile metadata collected at onboarding. Each photo submission snapshots
    # these onto the submission record (so admin filtering stays per-submission).
    # Nullable/blank so superusers can be created without a full profile.
    age = models.PositiveSmallIntegerField(null=True, blank=True, validators=AGE_VALIDATORS)
    place_of_living = models.CharField(max_length=120, blank=True)
    gender = models.CharField(max_length=12, choices=Gender.choices, blank=True)
    country_of_origin = models.CharField(max_length=80, blank=True)
    description = models.TextField(max_length=2000, blank=True)

    is_active = models.BooleanField(default=True)
    # Admin-role flag — gates admin panel + admin API.
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    @property
    def has_profile(self) -> bool:
        """True once the onboarding profile is filled in (age + gender set)."""
        return self.age is not None and bool(self.gender)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    def __str__(self) -> str:
        return self.email
