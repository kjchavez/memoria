"""GCS helper utilities for uploading, downloading, and building blob paths."""

from __future__ import annotations

import os

from google.cloud import storage

_bucket = None


def get_bucket() -> storage.Bucket:
    """Return a cached GCS bucket instance, creating it on first call."""
    global _bucket
    if _bucket is None:
        client = storage.Client()
        bucket_name = os.environ["GCS_BUCKET_NAME"]
        _bucket = client.bucket(bucket_name)
    return _bucket


def upload_blob(path: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """Upload bytes to a GCS blob."""
    blob = get_bucket().blob(path)
    blob.upload_from_string(data, content_type=content_type)


def download_blob(path: str) -> bytes:
    """Download a GCS blob as bytes."""
    blob = get_bucket().blob(path)
    return blob.download_as_bytes()


def build_raw_path(trip_id: str, timestamp: str, sender: str, ext: str) -> str:
    """Build the GCS path for a raw media upload."""
    return f"{trip_id}/raw/{timestamp}_{sender}{ext}"


def build_processed_path(trip_id: str, filename: str, size: str) -> str:
    """Build the GCS path for a processed/resized image."""
    return f"{trip_id}/processed/{size}/{filename}"
