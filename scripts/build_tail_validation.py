"""
build_tail_validation.py

Purpose:
Tail validation segmentation for discount tiers with strict definitions:
- Tail-only lift/decay curves by discount tier
- Absolute impact for tail (units/revenue uplift, not just % lift)
- Sample size table to prevent misleading conclusions

Requirements:
- Event-level dataset must include:
  - sale_id (or event_id equivalent)
  - k (day offset relative to event start; includes [-14, +14])
  - metric_daily_units OR metric_daily_revenue
  - discount_tier_bucket OR discount_pct

If metric_daily_units / metric_daily_revenue are missing, the script exits with a clear error.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "processed"
FIG_DIR = REPO_ROOT / "reports" / "figures"
REPORTS_DIR = REPO_ROOT / "reports"

EVENT_WINDOW = DATA_DIR / "event_window.parquet"
SALES = DATA_DIR / "sales.parquet"

DISCOUNT_TIER_ORDER = ["0-10%", "11-25%", "26-50%", "51-75%", "76-100%"]
SEGMENT_ORDER = ["tail", "mid", "head"]
MIN_SEGMENT_N = 25
MIN_TIER_N = 10


def require(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")


def detect_metric_column(df: pd.DataFrame) -> tuple[str, str]:
    if "metric_daily_units" in df.columns:
        return "metric_daily_units", "units"
    if "metric_daily_revenue" in df.columns:
        return "metric_daily_revenue", "revenue"
    raise SystemExit(
        "ERROR: Required metric column not found. Expected 'metric_daily_units' or "
        "'metric_daily_revenue' in event dataset. Provide raw metric to compute baseline "
        "and absolute uplift."
    )


def ensure_discount_tier(df: pd.DataFrame, sales_df: pd.DataFrame | None) -> pd.DataFrame:
    if "discount_tier_bucket" in df.columns:
        return df
    if "discount_pct" in df.columns:
        pct = df["discount_pct"].fillna(0)
        bins = [-np.inf, 10, 25, 50, 75, 100]
        labels = DISCOUNT_TIER_ORDER
        df["discount_tier_bucket"] = pd.cut(pct, bins=bins, labels=labels, include_lowest=True)
        return df
    if sales_df is not None and "discount_tier_bucket" in sales_df.columns:
        df = df.merge(sales_df[["sale_id", "discount_tier_bucket"]], on="sale_id", how="left")
        return df
    raise SystemExit(
        "ERROR: Missing discount tier. Provide 'discount_tier_bucket' or 'discount_pct' in event dataset."
    )


def compute_baseline(event_df: pd.DataFrame, metric_col: str) -> pd.DataFrame:
    pre = event_df[(event_df["k"] >= -14) & (event_df["k"] <= -1)]
    baseline = pre.groupby("sale_id", as_index=False)[metric_col].median()
    baseline = baseline.rename(columns={metric_col: "baseline_value"})
    return baseline


def assign_segments(baseline: pd.Series, notes: list[str]) -> pd.Series:
    n_events = baseline.notna().sum()
    if n_events < 200:
        quantiles = [0, 1 / 3, 2 / 3, 1]
        labels = SEGMENT_ORDER
        notes.append("Total events <200: used terciles (33/33/34).")
    else:
        quantiles = [0, 0.4, 0.8, 1]
        labels = SEGMENT_ORDER

    clean = baseline.replace([np.inf, -np.inf], np.nan)
    try:
        segments = pd.qcut(clean, q=quantiles, labels=labels, duplicates="drop")
    except Exception:
        pct = clean.rank(method="average", pct=True)
        segments = pd.cut(pct, bins=quantiles, labels=labels, include_lowest=True)

    seg_counts = segments.value_counts(dropna=True)
    if seg_counts.min() < MIN_SEGMENT_N:
        notes.append("Segment count <25: widened tail to bottom 50%.")
        quantiles = [0, 0.5, 0.8, 1]
        try:
            segments = pd.qcut(clean, q=quantiles, labels=labels, duplicates="drop")
        except Exception:
            pct = clean.rank(method="average", pct=True)
            segments = pd.cut(pct, bins=quantiles, labels=labels, include_lowest=True)
        seg_counts = segments.value_counts(dropna=True)
        if seg_counts.min() < MIN_SEGMENT_N:
            notes.append("Insufficient sample size: at least one segment <25 even after widening tail.")

    return segments.astype(str)


def collapse_tiers(df: pd.DataFrame, segment: str, notes: list[str]) -> pd.DataFrame:
    counts = df[df["segment"] == segment]["discount_tier_bucket"].value_counts()
    low_tiers = counts[counts < MIN_TIER_N].index.tolist()
    if not low_tiers:
        return df
    df = df.copy()
    df.loc[
        (df["segment"] == segment) & (df["discount_tier_bucket"].isin(["51-75%", "76-100%"])),
        "discount_tier_bucket",
    ] = "51%+"
    if "51%+" not in DISCOUNT_TIER_ORDER:
        notes.append(f"Collapsed tiers to '51%+' for segment '{segment}' due to low N (<{MIN_TIER_N}).")
    return df


def compute_decay(event_df: pd.DataFrame, metric_col: str) -> pd.DataFrame:
    def _decay_for_group(g: pd.DataFrame) -> pd.Series:
        baseline = g["baseline_value"].iloc[0]
        post = g[(g["k"] >= 0) & (g["k"] <= 14)].sort_values("k")
        decay_k = post[post[metric_col] <= baseline]["k"]
        if len(decay_k) == 0:
            return pd.Series({"decay_day": 14, "decay_censored": True})
        return pd.Series({"decay_day": int(decay_k.iloc[0]), "decay_censored": False})

    return event_df.groupby("sale_id", as_index=False).apply(_decay_for_group)


def compute_peaks(event_df: pd.DataFrame, metric_col: str) -> pd.DataFrame:
    post = event_df[(event_df["k"] >= 0) & (event_df["k"] <= 6)].copy()
    post["abs_uplift"] = post[metric_col] - post["baseline_value"]
    post["lift_pct"] = np.where(
        post["baseline_value"] > 0,
        100 * (post[metric_col] - post["baseline_value"]) / post["baseline_value"],
        np.nan,
    )
    peak_abs = post.groupby("sale_id", as_index=False)["abs_uplift"].max().rename(
        columns={"abs_uplift": "peak_abs_uplift"}
    )
    peak_pct = post.groupby("sale_id", as_index=False)["lift_pct"].max().rename(
        columns={"lift_pct": "peak_lift_pct"}
    )
    return peak_abs.merge(peak_pct, on="sale_id", how="left")


def prep_data() -> tuple[pd.DataFrame, pd.DataFrame, str, list[str]]:
    require(EVENT_WINDOW)
    event_df = pd.read_parquet(EVENT_WINDOW)

    metric_col, metric_name = detect_metric_column(event_df)
    sales_df = pd.read_parquet(SALES) if SALES.exists() else None
    event_df = ensure_discount_tier(event_df, sales_df)

    baseline = compute_baseline(event_df, metric_col)
    event_df = event_df.merge(baseline, on="sale_id", how="left")
    event_df["baseline_zero"] = event_df["baseline_value"] == 0

    notes: list[str] = []
    event_df["segment"] = assign_segments(event_df["baseline_value"], notes)

    decay = compute_decay(event_df, metric_col)
    peaks = compute_peaks(event_df, metric_col)

    event_summary = (
        event_df[["sale_id", "discount_tier_bucket", "segment", "baseline_value", "baseline_zero"]]
        .drop_duplicates("sale_id")
        .merge(decay, on="sale_id", how="left")
        .merge(peaks, on="sale_id", how="left")
    )

    return event_df, event_summary, metric_name, notes


def plot_tail_lift_curve(event_df: pd.DataFrame, metric_col: str, notes: list[str]) -> None:
    df = event_df.copy()
    df = df[df["segment"] == "tail"]
    df = df[df["baseline_value"] > 0]

    df["lift_pct"] = 100 * (df[metric_col] - df["baseline_value"]) / df["baseline_value"]
    df["lift_pct"] = df["lift_pct"].replace([np.inf, -np.inf], np.nan)
    df = df[df["lift_pct"].notna()]

    df = collapse_tiers(df, "tail", notes)
    tier_order = ["0-10%", "11-25%", "26-50%", "51%+"] if "51%+" in df["discount_tier_bucket"].unique() else DISCOUNT_TIER_ORDER

    agg = df.groupby(["discount_tier_bucket", "k"], as_index=False)["lift_pct"].median()

    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(7, 4))
    for tier in tier_order:
        sub = agg[agg["discount_tier_bucket"] == tier]
        if sub.empty:
            continue
        ax.plot(sub["k"], sub["lift_pct"], label=tier)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.axhline(0, color="black", linewidth=0.6)
    n_events = df["sale_id"].nunique()
    ax.set_title(f"Tail: Lift Curve by Discount Tier (N={n_events})")
    ax.set_xlabel("Days from sale start (k)")
    ax.set_ylabel("Lift vs baseline (%)")
    ax.set_xlim(-14, 14)
    ax.legend(title="Discount tier", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "tail_lift_curve_by_discount_tier.png", dpi=150)
    plt.close(fig)


def plot_tail_decay(event_summary: pd.DataFrame, notes: list[str]) -> None:
    df = event_summary[event_summary["segment"] == "tail"].copy()
    df = collapse_tiers(df, "tail", notes)
    tier_order = ["0-10%", "11-25%", "26-50%", "51%+"] if "51%+" in df["discount_tier_bucket"].unique() else DISCOUNT_TIER_ORDER

    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.boxplot(
        data=df,
        x="discount_tier_bucket",
        y="decay_day",
        order=tier_order,
        ax=ax,
        showfliers=False,
    )
    censored = df[df["decay_censored"] == True]["discount_tier_bucket"].value_counts()
    subtitle = " | ".join([f"{k}: censored {v}" for k, v in censored.items()])
    ax.set_title("Tail: Decay to Baseline by Discount Tier")
    if subtitle:
        ax.set_xlabel(subtitle)
    else:
        ax.set_xlabel("Discount tier")
    ax.set_ylabel("Days to baseline")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "tail_decay_by_discount_tier.png", dpi=150)
    plt.close(fig)


def plot_segmented_lift(event_df: pd.DataFrame, metric_col: str, notes: list[str]) -> None:
    df = event_df[event_df["baseline_value"] > 0].copy()
    df["lift_pct"] = 100 * (df[metric_col] - df["baseline_value"]) / df["baseline_value"]
    df["lift_pct"] = df["lift_pct"].replace([np.inf, -np.inf], np.nan)
    df = df[df["lift_pct"].notna()]

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)

    for idx, segment in enumerate(SEGMENT_ORDER):
        sub = df[df["segment"] == segment]
        sub = collapse_tiers(sub, segment, notes)
        tier_order = ["0-10%", "11-25%", "26-50%", "51%+"] if "51%+" in sub["discount_tier_bucket"].unique() else DISCOUNT_TIER_ORDER
        agg = sub.groupby(["discount_tier_bucket", "k"], as_index=False)["lift_pct"].median()

        ax = axes[idx]
        for tier in tier_order:
            s = agg[agg["discount_tier_bucket"] == tier]
            if s.empty:
                continue
            ax.plot(s["k"], s["lift_pct"], label=tier)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.axhline(0, color="black", linewidth=0.6)
        n_events = sub["sale_id"].nunique()
        ax.set_title(f"{segment.capitalize()} (N={n_events})")
        ax.set_xlabel("k")
        if idx == 0:
            ax.set_ylabel("Lift vs baseline (%)")
        ax.set_xlim(-14, 14)

    axes[-1].legend(title="Discount tier", fontsize=8)
    fig.suptitle("Lift Curve by Discount Tier (Tail vs Mid vs Head)", y=1.02)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "lift_curve_by_discount_tier_segmented.png", dpi=150)
    plt.close(fig)


def plot_tail_absolute_uplift(event_summary: pd.DataFrame, metric_name: str, notes: list[str]) -> str:
    df = event_summary[event_summary["segment"] == "tail"].copy()
    df = collapse_tiers(df, "tail", notes)
    tier_order = ["0-10%", "11-25%", "26-50%", "51%+"] if "51%+" in df["discount_tier_bucket"].unique() else DISCOUNT_TIER_ORDER

    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.boxplot(
        data=df,
        x="discount_tier_bucket",
        y="peak_abs_uplift",
        order=tier_order,
        ax=ax,
        showfliers=False,
    )
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_title("Tail: Peak Absolute Uplift by Discount Tier")
    ax.set_xlabel("Discount tier")
    ylabel = "Peak absolute uplift (units)" if metric_name == "units" else "Peak absolute uplift (revenue)"
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()

    filename = (
        "tail_absolute_uplift_by_tier.png"
        if metric_name == "units"
        else "tail_absolute_uplift_revenue_by_tier.png"
    )
    fig.savefig(FIG_DIR / filename, dpi=150)
    plt.close(fig)
    return filename


def write_summary(event_summary: pd.DataFrame, metric_name: str) -> pd.DataFrame:
    summary = (
        event_summary.groupby(["segment", "discount_tier_bucket"], as_index=False)
        .agg(
            n_events=("sale_id", "nunique"),
            median_baseline_value=("baseline_value", "median"),
            median_peak_lift_pct=("peak_lift_pct", "median"),
            median_peak_abs_uplift=("peak_abs_uplift", "median"),
            median_decay_day=("decay_day", "median"),
            censored_rate=("decay_censored", "mean"),
        )
    )
    summary = summary.rename(columns={"median_peak_abs_uplift": "median_peak_abs_uplift_units"})
    if metric_name != "units":
        summary = summary.rename(columns={"median_peak_abs_uplift_units": "median_peak_abs_uplift_revenue"})
    summary = summary.sort_values(["segment", "discount_tier_bucket"])
    out = REPORTS_DIR / "tail_validation_summary.csv"
    summary.to_csv(out, index=False)
    return summary


def preperiod_bias_check(event_df: pd.DataFrame, metric_col: str) -> list[str]:
    warnings = []
    df = event_df[(event_df["k"] >= -14) & (event_df["k"] <= -1) & (event_df["baseline_value"] > 0)].copy()
    df["lift_pct"] = 100 * (df[metric_col] - df["baseline_value"]) / df["baseline_value"]
    df["lift_pct"] = df["lift_pct"].replace([np.inf, -np.inf], np.nan)
    df = df[df["lift_pct"].notna()]
    if df.empty:
        warnings.append("Pre-period bias check skipped: no baseline>0 events.")
        return warnings
    med = df.groupby(["segment", "discount_tier_bucket"])["lift_pct"].median()
    flagged = med[med.abs() > 5]
    for idx, val in flagged.items():
        segment, tier = idx
        warnings.append(f"Pre-period median lift not near 0 for {segment}/{tier}: {val:.1f}%")
    return warnings


def write_notes(summary: pd.DataFrame | None, metric_name: str | None, notes: list[str], warnings: list[str], baseline_zero_count: int) -> None:
    out = REPORTS_DIR / "tail_validation_notes.md"
    lines = []
    lines.append("# Tail Validation Notes")
    lines.append("")
    lines.append("## Definitions used")
    lines.append("- Baseline window: k in [-14, -1], baseline_value = median(metric) in this window.")
    lines.append("- Lift %: 100 * (metric(k) - baseline_value) / baseline_value (baseline_value > 0).")
    lines.append("- Peak window: k in [0, +6], peak_lift_pct = max lift_pct, peak_abs_uplift = max(metric - baseline).")
    lines.append("- Decay day: smallest k in [0, +14] where metric(k) <= baseline_value; censored at 14 if never returns.")
    lines.append("")
    lines.append("## Sample sizes")
    if summary is None:
        lines.append("- No summary generated (missing required metric).")
    else:
        lines.append(f"- Total events in summary: {int(summary['n_events'].sum())}")
    lines.append("")
    lines.append("## Key findings")
    lines.append("- Not generated (missing required metric).")
    lines.append("")
    lines.append("## Caveats")
    lines.append(f"- baseline_value == 0 events: {baseline_zero_count} (excluded from % lift; included for absolute uplift when possible).")
    for n in notes:
        lines.append(f"- {n}")
    for w in warnings:
        lines.append(f"- {w}")
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        event_df, event_summary, metric_name, notes = prep_data()
    except SystemExit as e:
        # Write notes with the error for buyer-safe reporting
        write_notes(None, None, [str(e)], [], baseline_zero_count=0)
        raise

    metric_col = "metric_daily_units" if metric_name == "units" else "metric_daily_revenue"

    baseline_zero_count = int((event_summary["baseline_zero"] == True).sum())
    warnings = preperiod_bias_check(event_df, metric_col)

    plot_tail_lift_curve(event_df, metric_col, notes)
    plot_tail_decay(event_summary, notes)
    plot_segmented_lift(event_df, metric_col, notes)
    uplifts_filename = plot_tail_absolute_uplift(event_summary, metric_name, notes)

    summary = write_summary(event_summary, metric_name)
    write_notes(summary, metric_name, notes, warnings, baseline_zero_count)

    print("Saved figures to reports/figures/")
    print(f"Saved summary table to reports/tail_validation_summary.csv")
    print(f"Saved notes to reports/tail_validation_notes.md")
    if metric_name != "units":
        print(f"Absolute uplift plot written as {uplifts_filename}")


if __name__ == "__main__":
    main()
