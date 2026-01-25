from datetime import date

import pandas as pd

from src.config import load_config
from src.sales import detect_sales


def _make_panel(discounts):
    dates = pd.date_range("2020-01-01", periods=len(discounts), freq="D")
    data = pd.DataFrame(
        {
            "app_id": 1,
            "date": dates.date,
            "players_avg": 100.0,
            "players_peak": 120.0,
            "discount_pct": discounts,
        }
    )
    return data


def test_contiguous_sale_days_one_episode():
    discounts = [0] * 14 + [10, 10] + [0] * 4
    panel = _make_panel(discounts)
    sales, info = detect_sales(panel, config=load_config())
    assert info["excluded"] == 0
    assert len(sales) == 1
    assert sales.iloc[0]["sale_start_date"] == date(2020, 1, 15)
    assert sales.iloc[0]["sale_end_date"] == date(2020, 1, 16)


def test_gap_breaks_episode():
    discounts = [0] * 14 + [10, 10, 0, 10, 10] + [0] * 2
    panel = _make_panel(discounts)
    sales, info = detect_sales(panel, config=load_config())
    assert info["excluded"] == 0
    assert len(sales) == 2


def test_zero_discount_not_sale():
    discounts = [0] * 20
    panel = _make_panel(discounts)
    sales, _ = detect_sales(panel, config=load_config())
    assert sales.empty
