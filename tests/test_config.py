import pytest
from pathlib import Path
from shared.config import load_trip_config


TRIPS_DIR = Path(__file__).parent.parent / "trips"


class TestLoadTripConfig:
    def test_load_uk_2026(self):
        config = load_trip_config(TRIPS_DIR / "uk-2026" / "trip.yaml")
        assert config.id == "uk-2026"
        assert config.title == "England 2026"
        assert config.destination == "London & Cornwall, England"
        assert config.timezone == "Europe/London"
        assert len(config.locations) >= 10
        assert len(config.participants) == 4
        participant_names = [p.name for p in config.participants]
        assert "Elizabeth" in participant_names
        assert "Kevin" in participant_names

    def test_load_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_trip_config(Path("/nonexistent/trip.yaml"))
