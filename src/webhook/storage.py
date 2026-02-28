# src/webhook/storage.py
from __future__ import annotations
import logging
import requests
from shared.gcs import upload_blob, build_raw_path

logger = logging.getLogger(__name__)


def download_and_store_media(
    trip_id: str,
    media_url: str,
    content_type: str,
    timestamp: str,
    sender_name: str,
    index: int = 0,
) -> str:
    """Download media from Twilio and store in GCS. Returns the GCS path."""
    ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif"}
    ext = ext_map.get(content_type, ".jpg")
    filename_base = f"{timestamp}_{index}" if index > 0 else timestamp
    gcs_path = build_raw_path(trip_id, filename_base, sender_name.lower(), ext)
    response = requests.get(media_url)
    response.raise_for_status()
    upload_blob(gcs_path, response.content, content_type)
    logger.info("Stored media at %s", gcs_path)
    return gcs_path
