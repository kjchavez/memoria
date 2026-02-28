"""Batch processor — nightly pipeline that processes trip messages into a curated manifest."""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import date, timedelta
from pathlib import Path

from shared.config import load_trip_config
from shared.gcs import download_blob, upload_blob, build_processed_path
from shared.firestore import get_unprocessed_messages, mark_message_processed, get_trip_config_doc
from shared.models import TripConfig

from batch.exif import extract_exif
from batch.resize import resize_image
from batch.analyze import analyze_photo, analyze_text_message
from batch.curate import (
    group_by_day,
    cluster_by_time,
    select_journal_photos,
    select_hero_photo,
    arrange_chronologically,
)
from batch.manifest import build_manifest, build_day_entry
from batch.dedup import find_duplicates

logger = logging.getLogger(__name__)


def process_trip_batch(
    trip_id: str,
    config_path: str | None = None,
    dry_run: bool = False,
) -> dict | None:
    """Run the full nightly batch pipeline for a trip.

    Returns the manifest dict, or None if there were no messages to process.
    """
    # 1. Load trip config
    if config_path:
        config = load_trip_config(Path(config_path))
    else:
        config_data = get_trip_config_doc(trip_id)
        if config_data is None:
            logger.error("No config found for trip %s", trip_id)
            return None
        config = TripConfig.from_dict(config_data)

    # 2. Get unprocessed messages
    messages = get_unprocessed_messages(trip_id)
    if not messages:
        logger.info("No unprocessed messages for trip %s", trip_id)
        return None

    logger.info("Processing %d messages for trip %s", len(messages), trip_id)

    all_items: list[dict] = []

    # 3 & 4. Process each message
    for msg in messages:
        if msg.media_urls:
            # Photo message
            for media_url in msg.media_urls:
                try:
                    item = _process_photo(msg, media_url, config, dry_run)
                    if item:
                        all_items.append(item)
                except Exception:
                    logger.exception("Failed to process photo %s from message %s", media_url, msg.id)
        elif msg.text:
            # Text-only message
            try:
                item = _process_text(msg, config)
                if item:
                    all_items.append(item)
            except Exception:
                logger.exception("Failed to process text message %s", msg.id)

    if not all_items:
        logger.info("No items produced for trip %s", trip_id)
        return None

    # 5. Group all items by day
    days_grouped = group_by_day(all_items)

    # 6. Curate each day
    day_entries: list[dict] = []
    for day_number in sorted(days_grouped.keys()):
        day_items = days_grouped[day_number]
        day_date = config.start_date + timedelta(days=day_number - 1)

        # Cluster by time
        clusters = cluster_by_time(day_items)

        # Select journal photos (top per cluster)
        journal_items: list[dict] = []
        for cluster in clusters:
            journal_items.extend(select_journal_photos(cluster))

        # Also include text items in journal
        text_items = [item for item in day_items if item.get("type") != "photo"]
        journal_items.extend(text_items)

        # Select hero photo from all day photos
        day_photos = [item for item in day_items if item.get("type") == "photo"]
        hero = select_hero_photo(day_photos)

        # Generate day summary via Claude (skip in dry_run)
        summary = ""
        title = f"Day {day_number}"
        if not dry_run and day_photos:
            # For now, use a simple title; could call Claude for a richer summary
            title = f"Day {day_number}"
            summary = f"Day {day_number} of the trip."

        # Arrange chronologically
        journal_items = arrange_chronologically(journal_items)
        scrapbook_items = arrange_chronologically(day_items)

        day_entry = build_day_entry(
            day_date=day_date,
            day_number=day_number,
            title=title,
            summary=summary,
            journal=journal_items,
            scrapbook=scrapbook_items,
        )
        if hero:
            day_entry["hero"] = hero
        day_entries.append(day_entry)

    # 7. Build manifest
    manifest = build_manifest(config, day_entries)

    # 8. Upload manifest.json to GCS (if not dry_run)
    if not dry_run:
        manifest_path = f"{trip_id}/manifest.json"
        upload_blob(manifest_path, json.dumps(manifest, indent=2).encode(), "application/json")
        logger.info("Uploaded manifest to %s", manifest_path)

    # 9. Mark all messages as processed (if not dry_run)
    if not dry_run:
        for msg in messages:
            mark_message_processed(trip_id, msg.id)
        logger.info("Marked %d messages as processed", len(messages))

    return manifest


def _process_photo(msg, media_url: str, config: TripConfig, dry_run: bool) -> dict | None:
    """Download, resize, analyze, and build a photo item dict."""
    # Download raw image
    image_data = download_blob(media_url)

    # Extract EXIF
    exif = extract_exif(image_data)
    photo_timestamp = exif.get("timestamp", msg.timestamp)
    gps = exif.get("gps")
    location = f"{gps['lat']:.4f}, {gps['lng']:.4f}" if gps else ""

    # Resize to large (1600px) and thumb (400px)
    large_data = resize_image(image_data, max_dimension=1600)
    thumb_data = resize_image(image_data, max_dimension=400)

    # Build GCS paths for processed images
    filename = Path(media_url).stem
    large_path = build_processed_path(config.id, f"{filename}.jpg", "large")
    thumb_path = build_processed_path(config.id, f"{filename}.jpg", "thumb")

    # Upload resized images
    if not dry_run:
        upload_blob(large_path, large_data, "image/jpeg")
        upload_blob(thumb_path, thumb_data, "image/jpeg")

    # Determine day number
    photo_date = photo_timestamp.date() if hasattr(photo_timestamp, "date") else photo_timestamp
    day_number = config.day_number(photo_date)
    if day_number is None:
        logger.warning("Photo date %s outside trip dates, skipping", photo_date)
        return None

    # Analyze with Claude vision
    analysis = analyze_photo(
        image_data=large_data,
        day_number=day_number,
        destination=config.destination,
        planned_locations=[loc.get("name", "") for loc in config.locations],
        time=photo_timestamp.strftime("%H:%M"),
        location=location,
        sender_name=msg.sender_name,
    )

    return {
        "type": "photo",
        "id": f"{msg.id}_{Path(media_url).stem}",
        "url": large_path,
        "thumb": thumb_path,
        "caption": analysis.get("caption", ""),
        "alt": analysis.get("alt", ""),
        "category": analysis.get("category", ""),
        "quality": analysis.get("quality", 5),
        "by": msg.sender_name,
        "time": photo_timestamp.strftime("%H:%M"),
        "day": day_number,
        "location": location,
    }


def _process_text(msg, config: TripConfig) -> dict | None:
    """Classify a text message and build a quote/reaction item dict."""
    classification = analyze_text_message(msg.text)
    text_type = classification.get("type", "quote")

    msg_date = msg.timestamp.date() if hasattr(msg.timestamp, "date") else msg.timestamp
    day_number = config.day_number(msg_date)
    if day_number is None:
        logger.warning("Message date %s outside trip dates, skipping", msg_date)
        return None

    return {
        "type": text_type,
        "id": msg.id,
        "text": msg.text,
        "by": msg.sender_name,
        "time": msg.timestamp.strftime("%H:%M"),
        "day": day_number,
    }


def main():
    parser = argparse.ArgumentParser(description="Run the batch processor for a trip")
    parser.add_argument("--trip-id", required=True, help="Trip ID to process")
    parser.add_argument("--config", default=None, help="Path to trip config YAML file")
    parser.add_argument("--dry-run", action="store_true", help="Skip writes (no GCS uploads, no Firestore updates)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    result = process_trip_batch(
        trip_id=args.trip_id,
        config_path=args.config,
        dry_run=args.dry_run,
    )

    if result:
        logger.info("Batch complete: %d days in manifest", len(result.get("days", [])))
    else:
        logger.info("Batch complete: nothing to process")


if __name__ == "__main__":
    main()
