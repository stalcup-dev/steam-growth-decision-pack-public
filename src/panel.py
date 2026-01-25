from __future__ import annotations

from typing import Dict, List, Tuple
import json
from pathlib import Path

import pandas as pd

from .config import load_config
from .io import discover_mendeley_files, load_player_daily, load_price_data


def _aggregate_players(players: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    data = players.copy()
    if "timestamp" in data.columns:
        data["date"] = pd.to_datetime(data["timestamp"], utc=True, errors="coerce").dt.date
    elif "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"], utc=True, errors="coerce").dt.date
    else:
        raise ValueError("Player data missing timestamp/date column")

    grouped = data.groupby(["app_id", "date"], as_index=False)
    panel = grouped.agg(
        players_avg=("player_count", "mean"),
        players_peak=("player_count", "max"),
    )

    meta_cols = [col for col in ("app_name", "release_date", "genres") if col in data.columns]
    if meta_cols:
        meta = data[["app_id"] + meta_cols].drop_duplicates().sort_values("app_id")
        meta = meta.groupby("app_id", as_index=False).first()
        panel = panel.merge(meta, on="app_id", how="left")

    return panel, data


def _aggregate_prices(prices: pd.DataFrame) -> pd.DataFrame:
    if prices.empty:
        return pd.DataFrame(columns=["app_id", "date", "price", "list_price", "discount_pct"])

    data = prices.copy()
    if "timestamp" in data.columns:
        data["date"] = pd.to_datetime(data["timestamp"], utc=True, errors="coerce").dt.date
        data = data.sort_values(["app_id", "date", "timestamp"])
    elif "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"], utc=True, errors="coerce").dt.date
        data = data.sort_values(["app_id", "date"])
    else:
        raise ValueError("Price data missing timestamp/date column")

    last_price = data.groupby(["app_id", "date"], as_index=False).tail(1)
    price_daily = last_price[["app_id", "date", "price", "list_price"]]
    discount_daily = data.groupby(["app_id", "date"], as_index=False)["discount_pct"].max()

    merged = price_daily.merge(discount_daily, on=["app_id", "date"], how="left")
    return merged


def _split_error(entry: str) -> Tuple[str, str]:
    parts = entry.rsplit(": ", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return entry, ""


def write_ingestion_audit(
    raw_dir: str | Path, meta: Dict[str, object], output_dir: str | Path = "reports"
) -> Dict[str, object]:
    raw_dir = Path(raw_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    discovered = discover_mendeley_files(str(raw_dir))
    categories = ["player_files_part1", "player_files_part2", "price_files", "metadata_files"]
    category_paths = {name: {str(p) for p in discovered[name]} for name in categories}

    player_errors = meta.get("player_errors") or []
    price_errors = meta.get("price_errors") or []
    error_entries = player_errors + price_errors
    error_items: List[Dict[str, str]] = []
    error_paths = set()
    for entry in error_entries:
        path, reason = _split_error(entry)
        error_items.append({"path": path, "error": reason})
        error_paths.add(path)

    category_stats = {}
    total_attempted = 0
    total_failed = 0
    for name in categories:
        total = len(category_paths[name])
        attempted = total if name != "metadata_files" else 0
        failed = len(error_paths & category_paths[name])
        success = max(attempted - failed, 0)
        category_stats[name] = {
            "total": total,
            "attempted": attempted,
            "success": success,
            "failed": failed,
        }
        total_attempted += attempted
        total_failed += failed

    total_success = max(total_attempted - total_failed, 0)

    inferred_counts = {
        "player_files_part1": 0,
        "player_files_part2": 0,
        "price_files": 0,
        "metadata_files": 0,
    }
    for profile in (meta.get("player_profiles") or []):
        if not profile.get("app_id_inferred"):
            continue
        path = profile.get("path", "")
        for name in ("player_files_part1", "player_files_part2"):
            if path in category_paths[name]:
                inferred_counts[name] += 1
                break
    for profile in (meta.get("price_profiles") or []):
        if not profile.get("app_id_inferred"):
            continue
        path = profile.get("path", "")
        if path in category_paths["price_files"]:
            inferred_counts["price_files"] += 1

    audit = {
        "raw_dir": str(raw_dir),
        "categories": category_stats,
        "totals": {
            "attempted": total_attempted,
            "success": total_success,
            "failed": total_failed,
        },
        "failures": error_items[:20],
        "inferred_app_id_from_filename": inferred_counts,
    }

    json_path = output_dir / "ingestion_audit.json"
    json_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    md_lines = [
        "# Ingestion Audit\n",
        f"- Raw dir: {raw_dir}\n",
        f"- Attempted: {total_attempted}\n",
        f"- Success: {total_success}\n",
        f"- Failed: {total_failed}\n",
        "\n",
        "## Category Summary\n",
    ]
    for name in categories:
        stats = category_stats[name]
        md_lines.append(
            f"- {name}: total={stats['total']} attempted={stats['attempted']} "
            f"success={stats['success']} failed={stats['failed']}\n"
        )

    md_lines.append("\n## Inferred app_id from filename\n")
    for name in categories:
        md_lines.append(f"- {name}: {inferred_counts[name]}\n")

    md_lines.append("\n## Failure examples (top 20)\n")
    if error_items:
        for item in error_items[:20]:
            md_lines.append(f"- {item['path']}: {item['error']}\n")
    else:
        md_lines.append("- None\n")

    md_path = output_dir / "ingestion_audit.md"
    md_path.write_text("".join(md_lines), encoding="utf-8")

    return audit


def build_daily_panel(raw_dir: str = "data/raw/mendeley", config: Dict | None = None):
    if config is None:
        config = load_config()

    players_daily, player_profiles, player_errors = load_player_daily(raw_dir)
    if players_daily.empty:
        raise ValueError("No player count data found under data/raw/mendeley")

    price_df, price_profiles, price_errors = load_price_data(raw_dir)

    panel_players = players_daily.rename(
        columns={"player_count": "players_avg", "player_peak": "players_peak"}
    )
    price_daily = _aggregate_prices(price_df)

    panel = panel_players.merge(price_daily, on=["app_id", "date"], how="left")
    panel["discount_pct"] = pd.to_numeric(panel["discount_pct"], errors="coerce")
    panel["price"] = pd.to_numeric(panel["price"], errors="coerce")
    panel["list_price"] = pd.to_numeric(panel["list_price"], errors="coerce")
    panel["is_sale_day"] = panel["discount_pct"].fillna(0) > 0

    return panel, {
        "player_profiles": player_profiles,
        "price_profiles": price_profiles,
        "player_errors": player_errors,
        "price_errors": price_errors,
    }
