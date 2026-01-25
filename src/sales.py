from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from .config import load_config

# Heuristic windows for major Steam seasonal sales (approximate, by month/day).
SEASONAL_WINDOWS = [
    ("Spring", (3, 15), (3, 31)),
    ("Summer", (6, 15), (7, 15)),
    ("Autumn", (11, 15), (11, 30)),
    ("Winter", (12, 15), (1, 10)),
]


def _coerce_date(value) -> date | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return pd.to_datetime(value).date()
    except (TypeError, ValueError):
        return None


def _seasonal_overlap(start: date | None, end: date | None) -> bool:
    if start is None or end is None:
        return False
    years = {start.year - 1, start.year, end.year}
    for year in years:
        for _, start_md, end_md in SEASONAL_WINDOWS:
            window_start = date(year, start_md[0], start_md[1])
            end_year = year if (end_md[0], end_md[1]) >= (start_md[0], start_md[1]) else year + 1
            window_end = date(end_year, end_md[0], end_md[1])
            if start <= window_end and end >= window_start:
                return True
    return False


def add_mechanism_tags(sales: pd.DataFrame, config: Dict | None = None) -> pd.DataFrame:
    if config is None:
        config = load_config()
    if sales.empty:
        return sales

    threshold = float(config.get("wishlist_notify_discount_pct", 20))
    tagged = sales.copy()
    tagged["wishlist_notify_eligible"] = (
        pd.to_numeric(tagged["sale_depth_max"], errors="coerce") >= threshold
    )
    start_dates = tagged["sale_start_date"].apply(_coerce_date)
    end_dates = tagged["sale_end_date"].apply(_coerce_date)
    tagged["seasonal_overlap"] = [
        _seasonal_overlap(start, end) for start, end in zip(start_dates, end_dates)
    ]
    return tagged


def _mode(series: pd.Series):
    values = series.dropna()
    if values.empty:
        return np.nan
    return values.value_counts().idxmax()


def _build_sale_episodes(app_df: pd.DataFrame) -> pd.DataFrame:
    sale_days = app_df[app_df["is_sale_day"]].copy()
    if sale_days.empty:
        return pd.DataFrame()

    sale_days = sale_days.sort_values("date")
    sale_days["date_diff"] = sale_days["date"].diff().dt.days
    sale_days["episode_id"] = (sale_days["date_diff"].isna() | (sale_days["date_diff"] > 1)).cumsum()

    episodes = (
        sale_days.groupby("episode_id", as_index=False)
        .agg(
            sale_start_date=("date", "min"),
            sale_end_date=("date", "max"),
            sale_duration_days=("date", "size"),
            sale_depth_max=("discount_pct", "max"),
            sale_depth_mode=("discount_pct", _mode),
        )
        .reset_index(drop=True)
    )
    return episodes


def detect_sales(
    panel: pd.DataFrame,
    config: Dict | None = None,
    player_metric: str | None = None,
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    if config is None:
        config = load_config()

    if player_metric is None:
        player_metric = config.get("daily_player_metric", "players_avg")

    if player_metric not in panel.columns:
        raise ValueError(f"Panel is missing player metric '{player_metric}'")

    if "discount_pct" not in panel.columns:
        raise ValueError("Panel is missing discount_pct; price data is required for sale detection")

    if panel["discount_pct"].notna().sum() == 0:
        raise ValueError("Price/discount data not found; sale detection requires price data")

    data = panel.copy()
    data["date"] = pd.to_datetime(data["date"], utc=True, errors="coerce")
    data["discount_pct"] = pd.to_numeric(data["discount_pct"], errors="coerce")
    data["is_sale_day"] = data["discount_pct"].fillna(0) > 0

    baseline_pre_days = int(config.get("baseline_pre_days", 14))
    baseline_exclude_days = int(config.get("baseline_exclude_days", 1))
    lookback_days = int(config.get("cadence_lookback_days", 90))

    results = []
    excluded = 0

    cadence_cache = {}

    for app_id, app_df in data.groupby("app_id"):
        app_df = app_df.sort_values("date")
        episodes = _build_sale_episodes(app_df)
        if episodes.empty:
            continue
        episodes["app_id"] = app_id

        sale_days_dates = app_df[app_df["is_sale_day"]]["date"].dt.date.tolist()
        cadence_cache[app_id] = {
            "episodes": episodes,
            "sale_days": sale_days_dates,
        }

        for _, row in episodes.iterrows():
            start = row["sale_start_date"]
            baseline_start = (start - timedelta(days=baseline_pre_days)).date()
            baseline_end = (start - timedelta(days=baseline_exclude_days)).date()

            baseline_slice = app_df[
                (app_df["date"].dt.date >= baseline_start)
                & (app_df["date"].dt.date <= baseline_end)
            ]
            baseline_players = baseline_slice[player_metric].median()
            baseline_days = baseline_slice[player_metric].dropna().shape[0]

            if baseline_days < 7:
                excluded += 1
                continue

            results.append(
                {
                    "sale_id": f"{int(app_id)}_{start.date().isoformat()}",
                    "app_id": int(app_id),
                    "sale_start_date": start.date(),
                    "sale_end_date": row["sale_end_date"].date(),
                    "sale_duration_days": int((row["sale_end_date"] - row["sale_start_date"]).days) + 1,
                    "sale_depth_max": float(row["sale_depth_max"]),
                    "sale_depth_mode": row["sale_depth_mode"],
                    "baseline_players": float(baseline_players),
                }
            )

    sales = pd.DataFrame(results)
    if sales.empty:
        return sales, {"excluded": excluded}

    sales = sales.sort_values(["app_id", "sale_start_date"]).reset_index(drop=True)
    sales["days_since_last_sale"] = pd.NA

    for app_id, group in sales.groupby("app_id"):
        group = group.sort_values("sale_start_date")
        prev_end = None
        for idx in group.index:
            if prev_end is not None:
                delta = (group.loc[idx, "sale_start_date"] - prev_end).days
                sales.at[idx, "days_since_last_sale"] = int(delta)
            prev_end = group.loc[idx, "sale_end_date"]

    sales["sales_count_last_90d"] = 0
    sales["sale_days_last_90d"] = 0
    sales["sale_share_last_90d"] = 0.0

    for idx, row in sales.iterrows():
        app_id = row["app_id"]
        cache = cadence_cache.get(app_id)
        if cache is None:
            continue
        window_start = row["sale_start_date"] - timedelta(days=lookback_days)
        window_end = row["sale_start_date"] - timedelta(days=1)

        episodes = cache["episodes"]
        overlap = episodes[
            (episodes["sale_start_date"].dt.date <= window_end)
            & (episodes["sale_end_date"].dt.date >= window_start)
        ]
        sales.at[idx, "sales_count_last_90d"] = int(len(overlap))

        sale_days = cache["sale_days"]
        sale_days_count = sum(window_start <= day <= window_end for day in sale_days)
        sales.at[idx, "sale_days_last_90d"] = int(sale_days_count)
        sales.at[idx, "sale_share_last_90d"] = float(sale_days_count) / float(lookback_days)

    sales = add_mechanism_tags(sales, config=config)
    return sales, {"excluded": excluded}
