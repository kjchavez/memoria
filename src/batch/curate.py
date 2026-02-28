from __future__ import annotations
from collections import defaultdict


def group_by_day(items: list[dict]) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = defaultdict(list)
    for item in items:
        grouped[item["day"]].append(item)
    return dict(grouped)


def _time_to_minutes(time_str: str) -> int:
    parts = time_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def cluster_by_time(items: list[dict], gap_minutes: int = 60) -> list[list[dict]]:
    if not items:
        return []
    sorted_items = sorted(items, key=lambda x: x["time"])
    clusters: list[list[dict]] = [[sorted_items[0]]]
    for item in sorted_items[1:]:
        prev_time = _time_to_minutes(clusters[-1][-1]["time"])
        curr_time = _time_to_minutes(item["time"])
        if curr_time - prev_time <= gap_minutes:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    return clusters


def select_journal_photos(cluster: list[dict], max_per_cluster: int = 3) -> list[dict]:
    photos = [item for item in cluster if item.get("type") == "photo"]
    if not photos:
        return []
    if len(photos) <= max_per_cluster:
        return photos
    by_quality = sorted(photos, key=lambda p: p["quality"], reverse=True)
    selected = [by_quality[0]]
    seen_categories = {by_quality[0]["category"]}
    for photo in by_quality[1:]:
        if len(selected) >= max_per_cluster:
            break
        if photo["category"] not in seen_categories:
            selected.append(photo)
            seen_categories.add(photo["category"])
    for photo in by_quality[1:]:
        if len(selected) >= max_per_cluster:
            break
        if photo not in selected:
            selected.append(photo)
    return selected


def select_hero_photo(photos: list[dict]) -> dict | None:
    if not photos:
        return None
    return max(photos, key=lambda p: p.get("quality", 0))


def arrange_chronologically(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda x: x.get("time", ""))
