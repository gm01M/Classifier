"""S3 / MinIO object storage helper.

Photos are stored as objects (never in the database). We persist only the object
key on the model and hand out short-lived presigned GET URLs so buckets stay
private (safety rule #7).
"""

from __future__ import annotations

import functools

import boto3
from botocore.client import Config
from django.conf import settings


@functools.lru_cache(maxsize=2)
def _client(public: bool = False):
    """Return a cached boto3 S3 client.

    ``public=True`` builds URLs against ``S3_PUBLIC_ENDPOINT_URL`` (the host
    address a browser can reach), while the default client talks to the
    in-cluster endpoint for uploads.
    """
    endpoint = settings.S3_PUBLIC_ENDPOINT_URL if public else settings.S3_ENDPOINT_URL
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_bucket() -> None:
    """Create the bucket if it does not yet exist (idempotent)."""
    client = _client()
    existing = {b["Name"] for b in client.list_buckets().get("Buckets", [])}
    if settings.S3_BUCKET not in existing:
        client.create_bucket(Bucket=settings.S3_BUCKET)


def put_object(key: str, data: bytes, content_type: str) -> None:
    _client().put_object(
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def presigned_get_url(key: str, ttl: int | None = None) -> str:
    """Short-lived browser-reachable URL for an object."""
    return _client(public=True).generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=ttl or settings.S3_SIGNED_URL_TTL,
    )


def get_object_bytes(key: str) -> bytes:
    """Download an object's bytes (used by the Celery task to forward to the classifier)."""
    resp = _client().get_object(Bucket=settings.S3_BUCKET, Key=key)
    return resp["Body"].read()
