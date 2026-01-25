from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

CANDIDATES = {
    "app_id": ["app_id", "appid", "steam_appid", "id"],
    "timestamp": ["time", "timestamp", "date_time", "datetime", "ts", "utc_time"],
    "date": ["date", "day"],
    "player_count": ["playercount", "players", "ccu", "concurrent_players", "player_count"],
    "price": ["finalprice", "final_price", "price", "sale_price", "current_price"],
    "list_price": ["initialprice", "base_price", "list_price", "original_price"],
    "discount_pct": ["discount", "discount_pct", "discount_percent", "pct_discount"],
    "app_name": ["app_name", "name", "title"],
    "release_date": ["release_date", "released", "launch_date"],
    "genres": ["genres", "genre", "tags", "tag"],
}


def normalize_column_name(name: str) -> str:
    text = name.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def infer_column_mapping(df: pd.DataFrame) -> Tuple[Dict[str, str], Dict[str, str]]:
    df.columns = [str(c).strip().lower() for c in df.columns]
    normalized = {}
    for col in df.columns:
        norm = normalize_column_name(str(col))
        if norm and norm not in normalized:
            normalized[norm] = col

    mapping: Dict[str, str] = {}
    for canonical, candidates in CANDIDATES.items():
        for candidate in candidates:
            norm = normalize_column_name(candidate)
            if norm in normalized:
                mapping[canonical] = normalized[norm]
                break

    return mapping, normalized


def classify_table(mapping: Dict[str, str]) -> str:
    has_date = "timestamp" in mapping or "date" in mapping
    has_player = "player_count" in mapping
    has_price = any(key in mapping for key in ("price", "list_price", "discount_pct"))

    if has_date and has_player and has_price:
        return "both"
    if has_date and has_player:
        return "player"
    if has_date and has_price:
        return "price"
    return "unknown"


def infer_app_id_from_path(path: str | Path | None) -> int | None:
    if path is None:
        return None
    path = Path(path)
    stem = path.stem
    if stem.isdigit():
        return int(stem)
    candidates = list(re.finditer(r"\d+", stem))
    if not candidates:
        return None
    candidates.sort(key=lambda match: (-len(match.group(0)), match.start()))
    return int(candidates[0].group(0))


def _parse_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce")


def _parse_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce").dt.date


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def discount_to_pct(series: pd.Series) -> pd.Series:
    values = _to_numeric(series)
    non_null = values.dropna()
    if non_null.empty:
        return values
    if non_null.max() <= 1.0 and non_null.min() >= 0:
        values = values * 100
    values = values.clip(lower=0, upper=100)
    return values


def standardize_player_table(
    df: pd.DataFrame, mapping: Dict[str, str], file_path: str | Path | None = None
) -> pd.DataFrame:
    data = df.copy()

    if "app_id" in mapping:
        data["app_id"] = _to_numeric(data[mapping["app_id"]])
    else:
        inferred = infer_app_id_from_path(file_path)
        if inferred is None:
            raise ValueError("Missing app_id column and cannot infer from filename")
        data["app_id"] = inferred

    if "timestamp" in mapping:
        data["timestamp"] = _parse_datetime(data[mapping["timestamp"]])
    elif "date" in mapping:
        data["date"] = _parse_date(data[mapping["date"]])
    else:
        raise ValueError("Missing timestamp/date column for player table")

    if "player_count" not in mapping:
        raise ValueError("Missing player_count column for player table")
    data["player_count"] = _to_numeric(data[mapping["player_count"]])

    if "app_name" in mapping:
        data["app_name"] = data[mapping["app_name"]].astype(str)
    if "release_date" in mapping:
        data["release_date"] = _parse_date(data[mapping["release_date"]])
    if "genres" in mapping:
        data["genres"] = data[mapping["genres"]].astype(str)

    keep = ["app_id", "player_count"]
    if "timestamp" in data.columns:
        keep.append("timestamp")
    if "date" in data.columns:
        keep.append("date")
    for optional in ("app_name", "release_date", "genres"):
        if optional in data.columns:
            keep.append(optional)

    return data[keep]


def standardize_price_table(
    df: pd.DataFrame, mapping: Dict[str, str], file_path: str | Path | None = None
) -> pd.DataFrame:
    data = df.copy()

    if "app_id" in mapping:
        data["app_id"] = _to_numeric(data[mapping["app_id"]])
    else:
        inferred = infer_app_id_from_path(file_path)
        if inferred is None:
            raise ValueError("Missing app_id column and cannot infer from filename")
        data["app_id"] = inferred

    if "timestamp" in mapping:
        data["timestamp"] = _parse_datetime(data[mapping["timestamp"]])
    elif "date" in mapping:
        data["date"] = _parse_date(data[mapping["date"]])
    else:
        raise ValueError("Missing timestamp/date column for price table")

    if "price" in mapping:
        data["price"] = _to_numeric(data[mapping["price"]])
    else:
        data["price"] = np.nan

    if "list_price" in mapping:
        data["list_price"] = _to_numeric(data[mapping["list_price"]])
    else:
        data["list_price"] = np.nan

    if "discount_pct" in mapping:
        data["discount_pct"] = discount_to_pct(data[mapping["discount_pct"]])
    else:
        data["discount_pct"] = np.nan

    if data["price"].notna().any() and data["list_price"].notna().any():
        denom = data["list_price"].replace({0: np.nan})
        computed = (1 - (data["price"] / denom)) * 100
        computed = computed.clip(lower=0, upper=100)
        data["discount_pct"] = data["discount_pct"].where(data["discount_pct"].notna(), computed)

    keep = ["app_id", "price", "list_price", "discount_pct"]
    if "timestamp" in data.columns:
        keep.append("timestamp")
    if "date" in data.columns:
        keep.append("date")

    return data[keep]
