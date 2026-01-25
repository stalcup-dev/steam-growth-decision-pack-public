from datetime import date

import pandas as pd

from src.config import load_config
from src.metrics import compute_aul, compute_decay_days_to_baseline, compute_lift_pct


def test_lift_pct():
    players = pd.Series([150.0])
    baseline = pd.Series([100.0])
    lift = compute_lift_pct(players, baseline)
    assert round(lift.iloc[0], 2) == 50.0


def test_aul_clamps_negative():
    event_window = pd.DataFrame(
        {
            "lift_ratio": [0.8, 1.2, 1.5],
            "in_sale": [True, True, True],
        }
    )
    aul = compute_aul(event_window)
    assert round(aul, 3) == 0.7


def test_decay_days_to_baseline():
    config = load_config()
    panel = pd.DataFrame(
        {
            "app_id": [1, 1, 1, 1],
            "date": [
                date(2020, 1, 11),
                date(2020, 1, 12),
                date(2020, 1, 13),
                date(2020, 1, 14),
            ],
            "players_avg": [150.0, 120.0, 105.0, 100.0],
        }
    )
    sale_row = pd.Series(
        {
            "app_id": 1,
            "sale_end_date": date(2020, 1, 10),
            "baseline_players": 100.0,
        }
    )
    decay = compute_decay_days_to_baseline(sale_row, panel, config, "players_avg")
    assert decay == 4.0
