"""Ensure the object-storage bucket exists (idempotent). Runs on startup."""

from django.core.management.base import BaseCommand

from common.storage import ensure_bucket


class Command(BaseCommand):
    help = "Create the S3/MinIO bucket if it does not exist."

    def handle(self, *args, **options):
        ensure_bucket()
        self.stdout.write(self.style.SUCCESS("Storage bucket ready."))
