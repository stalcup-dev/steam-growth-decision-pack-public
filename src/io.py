from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd
import pyarrow.parquet as pq

from .ingest.io import safe_read_csv
from .normalize import (
    classify_table,
    infer_app_id_from_path,
    infer_column_mapping,
    standardize_player_table,
    standardize_price_table,
)

ALLOWED_EXTS = {".csv", ".tsv", ".txt", ".parquet", ".json", ".jsonl"}


def scan_raw_files(raw_dir: str | Path = "data/raw/mendeley") -> List[Path]:
    base = Path(raw_dir)
    if not base.exists():
        return []
    files = [path for path in base.rglob("*") if path.is_file() and path.suffix.lower() in ALLOWED_EXTS]
    return sorted(files)


def discover_mendeley_files(base_path: str) -> Dict[str, List[Path]]:
    base = Path(base_path)
    result = {
        "player_files_part1": [],
        "player_files_part2": [],
        "price_files": [],
        "metadata_files": [],
    }
    if not base.exists():
        return result

    def _has_part(path: Path, name: str) -> bool:
        target = name.lower()
        return any(part.lower() == target for part in path.parts)

    for path in base.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTS:
            continue
        if _has_part(path, "PlayerCountHistoryPart1"):
            result["player_files_part1"].append(path)
        elif _has_part(path, "PlayerCountHistoryPart2"):
            result["player_files_part2"].append(path)
        elif _has_part(path, "PriceHistory"):
            result["price_files"].append(path)
        else:
            result["metadata_files"].append(path)

    for key in result:
        result[key] = sorted(result[key])
    return result


def _read_parquet_sample(path: Path, nrows: int | None) -> pd.DataFrame:
    if nrows is None:
        return pd.read_parquet(path)
    parquet = pq.ParquetFile(path)
    if parquet.metadata is None or parquet.metadata.num_rows == 0:
        return pd.DataFrame()
    table = parquet.read_row_group(0)
    data = table.to_pandas()
    return data.head(nrows)


def read_table(path: str | Path, nrows: int | None = None) -> pd.DataFrame:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".parquet":
        return _read_parquet_sample(path, nrows)
    if ext in {".csv", ".tsv", ".txt"}:
        sep = "\t" if ext == ".tsv" else "," if ext == ".csv" else None
        return safe_read_csv(path, sep=sep, nrows=nrows)
    if ext in {".json", ".jsonl"}:
        data = pd.read_json(path, lines=(ext == ".jsonl"))
        return data.head(nrows) if nrows is not None else data
    raise ValueError(f"Unsupported file extension: {ext}")


def iter_table_chunks(
    path: str | Path, chunksize: int | None = None, usecols: List[str] | None = None
) -> Iterable[pd.DataFrame]:
    path = Path(path)
    if chunksize is None:
        data = read_table(path, nrows=None)
        data.columns = [str(c).strip().lower() for c in data.columns]
        if usecols is not None:
            data = data.loc[:, usecols]
        yield data
        return
    ext = path.suffix.lower()
    if ext in {".csv", ".tsv", ".txt"}:
        sep = "\t" if ext == ".tsv" else "," if ext == ".csv" else None
        header = safe_read_csv(path, sep=sep, nrows=0)
        header_map = {}
        for raw in header.columns:
            key = str(raw).strip().lower()
            if key not in header_map:
                header_map[key] = raw
        resolved_usecols = None
        if usecols is not None:
            resolved_usecols = [header_map[col] for col in usecols if col in header_map]
            if not resolved_usecols:
                resolved_usecols = None
        for chunk in safe_read_csv(
            path,
            sep=sep,
            chunksize=chunksize,
            usecols=resolved_usecols,
            low_memory=False,
        ):
            chunk.columns = [str(c).strip().lower() for c in chunk.columns]
            yield chunk
        return
    if ext == ".parquet":
        parquet = pq.ParquetFile(path)
        if parquet.metadata is None or parquet.metadata.num_rows == 0:
            return
        resolved_usecols = None
        if usecols is not None:
            schema_map = {}
            for name in parquet.schema.names:
                key = str(name).strip().lower()
                if key not in schema_map:
                    schema_map[key] = name
            resolved_usecols = [schema_map[col] for col in usecols if col in schema_map]
            if not resolved_usecols:
                resolved_usecols = None
        for batch in parquet.iter_batches(batch_size=chunksize, columns=resolved_usecols):
            data = batch.to_pandas()
            data.columns = [str(c).strip().lower() for c in data.columns]
            yield data
        return
    if ext == ".jsonl":
        for chunk in pd.read_json(path, lines=True, chunksize=chunksize):
            chunk.columns = [str(c).strip().lower() for c in chunk.columns]
            if usecols is not None:
                chunk = chunk.loc[:, usecols]
            yield chunk
        return
    if ext == ".json":
        data = pd.read_json(path)
        data.columns = [str(c).strip().lower() for c in data.columns]
        if usecols is not None:
            data = data.loc[:, usecols]
        yield data
        return
    raise ValueError(f"Unsupported file extension: {ext}")


def profile_files(files: List[Path], sample_rows: int = 1000) -> List[Dict[str, object]]:
    profiles: List[Dict[str, object]] = []
    for path in files:
        profile: Dict[str, object] = {
            "path": str(path),
            "columns": [],
            "mapping": {},
            "classification": "unknown",
            "sample_rows": 0,
            "missingness": {},
            "error": None,
        }
        try:
            sample = read_table(path, nrows=sample_rows)
            profile["sample_rows"] = int(len(sample))
            profile["columns"] = list(sample.columns)
            mapping, _ = infer_column_mapping(sample)
            profile["mapping"] = mapping
            profile["classification"] = classify_table(mapping)
            if not sample.empty:
                missing = sample.isna().mean().round(3)
                profile["missingness"] = missing.to_dict()
        except Exception as exc:
            profile["error"] = str(exc)
        profiles.append(profile)
    return profiles


def _load_tables(
    raw_dir: str | Path,
    want: Tuple[str, ...],
) -> Tuple[pd.DataFrame, List[Dict[str, object]], List[str]]:
    files = scan_raw_files(raw_dir)
    profiles = profile_files(files)
    frames: List[pd.DataFrame] = []
    used_profiles: List[Dict[str, object]] = []
    errors: List[str] = []

    for profile in profiles:
        if profile["classification"] not in want:
            continue
        path = Path(profile["path"])
        try:
            data = read_table(path, nrows=None)
            mapping, _ = infer_column_mapping(data)
            if "app_id" not in mapping:
                inferred_id = infer_app_id_from_path(path)
                if inferred_id is None:
                    raise ValueError("Missing app_id column and cannot infer from filename")
                profile["app_id_inferred"] = True
            else:
                profile["app_id_inferred"] = False
            if "player" in want:
                standardized = standardize_player_table(data, mapping, path)
            else:
                standardized = standardize_price_table(data, mapping, path)
            frames.append(standardized)
            used_profiles.append(profile)
        except Exception as exc:
            errors.append(f"{path}: {exc}")

    if frames:
        combined = pd.concat(frames, ignore_index=True)
    else:
        combined = pd.DataFrame()

    return combined, used_profiles, errors


def load_player_daily(
    raw_dir: str | Path = "data/raw/mendeley",
    sample_rows: int = 1000,
    chunksize: int | None = 200_000,
    profiles: List[Dict[str, object]] | None = None,
) -> Tuple[pd.DataFrame, List[Dict[str, object]], List[str]]:
    files = scan_raw_files(raw_dir) if profiles is None else []
    totals: Dict[Tuple[object, object], List[float]] = {}
    used_profiles: List[Dict[str, object]] = []
    errors: List[str] = []

    if profiles is None:
        profiles = profile_files(files, sample_rows=sample_rows)

    for profile in profiles:
        path = Path(profile["path"])
        file_totals: Dict[Tuple[object, object], List[float]] = {}
        try:
            mapping = profile.get("mapping") or {}
            classification = profile.get("classification") or "unknown"
            if not mapping or classification == "unknown":
                sample = read_table(path, nrows=sample_rows)
                mapping, _ = infer_column_mapping(sample)
                classification = classify_table(mapping)
                profile["mapping"] = mapping
                profile["classification"] = classification

            if classification not in {"player", "both"}:
                continue

            if "app_id" not in mapping:
                inferred_id = infer_app_id_from_path(path)
                if inferred_id is None:
                    raise ValueError("Missing app_id column and cannot infer from filename")
                profile["app_id_inferred"] = True
            else:
                profile["app_id_inferred"] = False

            needed_cols: List[str] = []
            if "app_id" in mapping:
                needed_cols.append(mapping["app_id"])
            if "timestamp" in mapping:
                needed_cols.append(mapping["timestamp"])
            elif "date" in mapping:
                needed_cols.append(mapping["date"])
            if "player_count" in mapping:
                needed_cols.append(mapping["player_count"])
            usecols = list(dict.fromkeys(needed_cols)) or None

            for chunk in iter_table_chunks(path, chunksize=chunksize, usecols=usecols):
                if chunk.empty:
                    continue
                standardized = standardize_player_table(chunk, mapping, path)
                if standardized.empty:
                    continue
                if "timestamp" in standardized.columns:
                    dates = standardized["timestamp"].dt.date
                else:
                    dates = standardized["date"]
                chunk_data = pd.DataFrame(
                    {
                        "app_id": standardized["app_id"],
                        "date": dates,
                        "player_count": standardized["player_count"],
                    }
                ).dropna(subset=["app_id", "date", "player_count"])
                if chunk_data.empty:
                    continue
                grouped = chunk_data.groupby(["app_id", "date"], as_index=False)["player_count"].agg(
                    sum="sum", count="count", max="max"
                )
                for row in grouped.itertuples(index=False):
                    key = (row.app_id, row.date)
                    existing = file_totals.get(key)
                    if existing is None:
                        file_totals[key] = [float(row.sum), float(row.count), float(row.max)]
                    else:
                        existing[0] += float(row.sum)
                        existing[1] += float(row.count)
                        existing[2] = max(existing[2], float(row.max))

            for key, values in file_totals.items():
                existing = totals.get(key)
                if existing is None:
                    totals[key] = values
                else:
                    existing[0] += values[0]
                    existing[1] += values[1]
                    existing[2] = max(existing[2], values[2])
            used_profiles.append(profile)
        except Exception as exc:
            profile["error"] = str(exc)
            errors.append(f"{path}: {exc}")

    if totals:
        rows = []
        for (app_id, date), (total_sum, total_count, total_max) in totals.items():
            if total_count:
                rows.append(
                    {
                        "app_id": app_id,
                        "date": date,
                        "player_count": total_sum / total_count,
                        "player_peak": total_max,
                    }
                )
        daily = pd.DataFrame(rows)
    else:
        daily = pd.DataFrame()

    return daily, used_profiles, errors


def load_player_data(raw_dir: str | Path = "data/raw/mendeley") -> Tuple[pd.DataFrame, List[Dict[str, object]], List[str]]:
    return _load_tables(raw_dir, ("player", "both"))


def load_price_data(raw_dir: str | Path = "data/raw/mendeley") -> Tuple[pd.DataFrame, List[Dict[str, object]], List[str]]:
    return _load_tables(raw_dir, ("price", "both"))


def write_data_profile(report_path: str | Path, profiles: List[Dict[str, object]]) -> None:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append("# Data Profile\n")
    if not profiles:
        lines.append("No files discovered under data/raw/mendeley.\n")
    for profile in profiles:
        lines.append(f"## {profile['path']}\n")
        if profile.get("error"):
            lines.append(f"- Error: {profile['error']}\n")
            continue
        lines.append(f"- Classification: {profile['classification']}\n")
        lines.append(f"- Sample rows: {profile['sample_rows']}\n")
        cols = ", ".join([str(c) for c in profile.get("columns", [])])
        lines.append(f"- Columns: {cols}\n")
        mapping = profile.get("mapping", {})
        if mapping:
            lines.append("- Inferred mapping:\n")
            for key, value in mapping.items():
                lines.append(f"  - {key}: {value}\n")
        missing = profile.get("missingness", {})
        if missing:
            lines.append("- Missingness (sample):\n")
            for key, value in list(missing.items())[:12]:
                lines.append(f"  - {key}: {value}\n")
        lines.append("\n")

    path.write_text("".join(lines), encoding="utf-8")
