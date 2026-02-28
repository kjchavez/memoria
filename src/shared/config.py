from pathlib import Path

import yaml

from shared.models import TripConfig


def load_trip_config(path: Path) -> TripConfig:
    """Load a trip configuration from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return TripConfig.from_dict(data)
