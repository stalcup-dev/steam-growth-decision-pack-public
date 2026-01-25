from __future__ import annotations

from datetime import timedelta
from typing import Dict

import numpy as np
import pandas as pd

from .config import load_config


def compute_lift_ratio(players: pd.Series, baseline: pd.Series) -> pd.Series:
    return players / baseline


def compute_lift_pct(players: pd.Series, baseline: pd.Series) -> pd.Series:
    return (compute_lift_ratio(players, baseline) - 1) * 100


def build_event_window(
    panel: pd.DataFrame,
    sales: pd.DataFrame,
    config: Dict | None = None,
    player_metric: str | None = None,
) -> pd.DataFrame:
    if config is None:
        config = load_config()
    if player_metric is None:
        player_metric = config.get("daily_player_metric", "players_avg")

    if player_metric not in panel.columns:
        raise ValueError(f"Panel is missing player metric '{player_metric}'")

    if player_metric not in panel.columns:
        raise ValueError(f"Panel is missing player metric '{player_metric}'")

    pre = int(config.get("event_window_pre_days", 14))
    post = int(config.get("event_window_post_days", 14))

    panel_data = panel.copy()
    panel_data["date"] = pd.to_datetime(panel_data["date"], utc=True, errors="coerce").dt.date

    records = []
    for _, sale in sales.iterrows():
        for k in range(-pre, post + 1):
            event_date = sale["sale_start_date"] + timedelta(days=k)
            records.append(
                {
                    "sale_id": sale["sale_id"],
                    "app_id": sale["app_id"],
                    "k": k,
                    "date": event_date,
                    "baseline_players": sale["baseline_players"],
                    "sale_start_date": sale["sale_start_date"],
                    "sale_end_date": sale["sale_end_date"],
                }
            )

    event_window = pd.DataFrame(records)
    if event_window.empty:
        return event_window

    merged = event_window.merge(
        panel_data[["app_id", "date", player_metric]], on=["app_id", "date"], how="left"
    )
    merged = merged.rename(columns={player_metric: "players"})
    merged["lift_ratio"] = compute_lift_ratio(merged["players"], merged["baseline_players"])
    merged["lift_pct"] = (merged["lift_ratio"] - 1) * 100
    merged["in_sale"] = (merged["date"] >= merged["sale_start_date"]) & (
        merged["date"] <= merged["sale_end_date"]
    )

    return merged[[
        "sale_id",
        "app_id",
        "k",
        "date",
        "players",
        "baseline_players",
        "lift_ratio",
        "lift_pct",
        "in_sale",
        "sale_start_date",
        "sale_end_date",
    ]]


def compute_aul(event_window: pd.DataFrame) -> float:
    if event_window.empty:
        return float("nan")
    values = event_window.loc[event_window["in_sale"], "lift_ratio"] - 1
    values = values.clip(lower=0)
    return float(values.sum())


def compute_decay_days_to_baseline(
    sale_row: pd.Series,
    panel: pd.DataFrame,
    config: Dict,
    player_metric: str,
) -> float | None:
    baseline = sale_row.get("baseline_players")
    if baseline is None or pd.isna(baseline):
        return None

    decay_window = int(config.get("decay_window_days", 14))
    roll = int(config.get("decay_roll_days", 3))
    tolerance = float(config.get("decay_tolerance", 0.05))

    start_date = sale_row["sale_end_date"] + timedelta(days=1)
    end_date = sale_row["sale_end_date"] + timedelta(days=decay_window)

    subset = panel[
        (panel["app_id"] == sale_row["app_id"]) & (panel["date"] >= start_date) & (panel["date"] <= end_date)
    ].copy()

    if subset.empty:
        return None

    subset = subset.sort_values("date")
    series = pd.to_numeric(subset[player_metric], errors="coerce")
    rolling = series.rolling(window=roll, min_periods=1).median()

    threshold = baseline * (1 + tolerance)
    for idx, value in enumerate(rolling):
        if pd.notna(value) and value <= threshold:
            return float((subset.iloc[idx]["date"] - sale_row["sale_end_date"]).days)

    return None


def add_sale_metrics(
    sales: pd.DataFrame,
    event_window: pd.DataFrame,
    panel: pd.DataFrame,
    config: Dict | None = None,
    player_metric: str | None = None,
) -> pd.DataFrame:
    if config is None:
        config = load_config()
    if player_metric is None:
        player_metric = config.get("daily_player_metric", "players_avg")

    if sales.empty:
        return sales

    sales = sales.copy()
    drop_cols = [
        col
        for col in sales.columns
        if col in ("peak_lift_pct", "AUL") or col.startswith("peak_lift_pct_") or col.startswith("AUL_")
    ]
    if drop_cols:
        sales = sales.drop(columns=drop_cols)

    peak_window = int(config.get("peak_window_days", 7))
    metrics = []

    for sale_id, group in event_window.groupby("sale_id"):
        peak_slice = group[(group["k"] >= 0) & (group["k"] <= peak_window)]
        peak_lift = peak_slice["lift_pct"].max()
        metrics.append({"sale_id": sale_id, "peak_lift_pct": peak_lift, "AUL": compute_aul(group)})

    metrics_df = pd.DataFrame(metrics)
    merged = sales.merge(metrics_df, on="sale_id", how="left")

    panel_data = panel.copy()
    panel_data["date"] = pd.to_datetime(panel_data["date"], utc=True, errors="coerce").dt.date

    decay_values = []
    for _, row in merged.iterrows():
        decay = compute_decay_days_to_baseline(row, panel_data, config, player_metric)
        decay_values.append(decay)
    merged["decay_days_to_baseline"] = decay_values

    return merged


def add_buckets(sales: pd.DataFrame, config: Dict | None = None) -> pd.DataFrame:
    if config is None:
        config = load_config()

    tiers = config.get("discount_tiers", [0.10, 0.25, 0.50, 0.75, 0.90])
    tiers = [t * 100 if t <= 1 else t for t in tiers]
    tiers = sorted(tiers)

    bins = [0, tiers[0], tiers[1], tiers[2], tiers[3], 100]
    labels = [
        f"0-{int(bins[1])}%",
        f"{int(bins[1] + 1)}-{int(bins[2])}%",
        f"{int(bins[2] + 1)}-{int(bins[3])}%",
        f"{int(bins[3] + 1)}-{int(bins[4])}%",
        f"{int(bins[4] + 1)}-{int(bins[5])}%",
    ]

    sales = sales.copy()
    sales["sale_depth_max"] = pd.to_numeric(sales["sale_depth_max"], errors="coerce").clip(lower=0, upper=100)
    sales["discount_tier_bucket"] = pd.cut(
        sales["sale_depth_max"],
        bins=bins,
        labels=labels,
        include_lowest=True,
    )
    sales["discount_tier_bucket"] = (
        sales["discount_tier_bucket"].astype("object").where(sales["discount_tier_bucket"].notna(), "Unknown")
    )

    quantiles = int(config.get("popularity_quantiles", 4))
    if sales["baseline_players"].notna().sum() > 0:
        try:
            sales["popularity_bucket"] = pd.qcut(
                sales["baseline_players"],
                q=quantiles,
                labels=[f"Q{i+1}" for i in range(quantiles)],
                duplicates="drop",
            )
        except ValueError:
            sales["popularity_bucket"] = pd.NA
    else:
        sales["popularity_bucket"] = pd.NA

    if sales["sale_share_last_90d"].notna().sum() > 0:
        try:
            sales["cadence_bucket"] = pd.qcut(
                sales["sale_share_last_90d"], q=3, labels=["low", "mid", "high"], duplicates="drop"
            )
        except ValueError:
            sales["cadence_bucket"] = pd.NA
    else:
        sales["cadence_bucket"] = pd.NA

    return sales


def build_playbook_table(sales: pd.DataFrame) -> pd.DataFrame:
    if sales.empty:
        return sales

    grouped = sales.groupby(
        ["discount_tier_bucket", "popularity_bucket", "cadence_bucket"], dropna=True, observed=True
    )
    table = grouped.agg(
        n_sales=("sale_id", "count"),
        median_peak_lift_pct=("peak_lift_pct", "median"),
        iqr_peak_lift_pct=("peak_lift_pct", lambda x: x.quantile(0.75) - x.quantile(0.25)),
        median_AUL=("AUL", "median"),
        median_decay_days_to_baseline=("decay_days_to_baseline", "median"),
        median_lift_per_discount_point=(
            "peak_lift_pct",
            lambda x: (x / sales.loc[x.index, "sale_depth_max"].replace(0, np.nan)).median(),
        ),
    )

    table = table.reset_index()
    return table[table["n_sales"] > 0]
