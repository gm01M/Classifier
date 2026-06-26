"""Idempotently create the demo admin from env vars (skipped if already present).

For local/demo convenience only — production should create admins out-of-band.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create a superuser from DJANGO_SUPERUSER_EMAIL/PASSWORD if missing."

    def handle(self, *args, **options):
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if not email or not password:
            self.stdout.write("No DJANGO_SUPERUSER_* env vars set; skipping.")
            return
        if User.objects.filter(email=email).exists():
            self.stdout.write(f"Admin {email} already exists; skipping.")
            return
        User.objects.create_superuser(email=email, password=password, full_name="Administrator")
        self.stdout.write(self.style.SUCCESS(f"Created admin {email}"))
