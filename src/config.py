from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

DEFAULT_CONFIG: Dict[str, Any] = {
    "tz": "UTC",
    "daily_player_metric": "players_avg",
    "event_window_pre_days": 14,
    "event_window_post_days": 14,
    "baseline_pre_days": 14,
    "baseline_exclude_days": 1,
    "peak_window_days": 7,
    "decay_window_days": 14,
    "decay_tolerance": 0.05,
    "decay_roll_days": 3,
    "discount_tiers": [0.10, 0.25, 0.50, 0.75, 0.90],
    "popularity_quantiles": 4,
    "cadence_lookback_days": 90,
}


def load_config(path: str | Path | None = None) -> Dict[str, Any]:
    if path is None:
        path = Path(__file__).resolve().parents[1] / "config.yaml"
    else:
        path = Path(path)

    config = DEFAULT_CONFIG.copy()
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        if not isinstance(loaded, dict):
            raise ValueError("config.yaml must contain a mapping at the top level")
        config.update(loaded)

    return config


def get_config() -> Dict[str, Any]:
    return load_config()
