import pytest
from batch.curate import (
    group_by_day,
    cluster_by_time,
    select_journal_photos,
    select_hero_photo,
    arrange_chronologically,
)


def _photo(time: str, quality: int, category: str = "sightseeing", by: str = "Kevin"):
    return {
        "type": "photo",
        "url": f"processed/large/{time.replace(':', '')}.jpg",
        "thumb": f"processed/thumb/{time.replace(':', '')}.jpg",
        "caption": f"Photo at {time}",
        "alt": f"Photo at {time}",
        "by": by,
        "time": time,
        "location": "London",
        "category": category,
        "quality": quality,
    }


def _quote(time: str, by: str = "Kevin"):
    return {
        "type": "quote",
        "text": f"Message at {time}",
        "by": by,
        "time": time,
    }


class TestGroupByDay:
    def test_groups_items_by_day_number(self):
        items = [
            {"day": 1, **_photo("09:00", 7)},
            {"day": 1, **_photo("14:00", 8)},
            {"day": 2, **_photo("10:00", 6)},
        ]
        grouped = group_by_day(items)
        assert len(grouped[1]) == 2
        assert len(grouped[2]) == 1

    def test_empty_input(self):
        assert group_by_day([]) == {}


class TestClusterByTime:
    def test_clusters_close_times(self):
        items = [
            _photo("09:00", 7),
            _photo("09:15", 6),
            _photo("09:20", 8),
            _photo("14:00", 5),
            _photo("14:10", 7),
        ]
        clusters = cluster_by_time(items, gap_minutes=60)
        assert len(clusters) == 2
        assert len(clusters[0]) == 3
        assert len(clusters[1]) == 2


class TestSelectJournalPhotos:
    def test_selects_top_photos_per_cluster(self):
        cluster = [
            _photo("09:00", 5),
            _photo("09:15", 9),
            _photo("09:20", 7),
            _photo("09:25", 3),
            _photo("09:30", 8, category="food"),
        ]
        selected = select_journal_photos(cluster, max_per_cluster=3)
        assert len(selected) == 3
        qualities = [p["quality"] for p in selected]
        assert 9 in qualities
        assert 8 in qualities

    def test_prioritizes_variety_in_category(self):
        cluster = [
            _photo("09:00", 9, category="sightseeing"),
            _photo("09:15", 8, category="sightseeing"),
            _photo("09:20", 7, category="food"),
            _photo("09:25", 6, category="group"),
        ]
        selected = select_journal_photos(cluster, max_per_cluster=3)
        categories = [p["category"] for p in selected]
        assert len(set(categories)) >= 2


class TestSelectHeroPhoto:
    def test_selects_highest_quality(self):
        photos = [
            _photo("09:00", 5),
            _photo("10:00", 9),
            _photo("14:00", 7),
        ]
        hero = select_hero_photo(photos)
        assert hero["quality"] == 9

    def test_empty_list_returns_none(self):
        assert select_hero_photo([]) is None


class TestArrangeChronologically:
    def test_sorts_by_time(self):
        items = [
            _photo("14:00", 7),
            _quote("10:30"),
            _photo("09:00", 8),
        ]
        arranged = arrange_chronologically(items)
        times = [i["time"] for i in arranged]
        assert times == ["09:00", "10:30", "14:00"]
