"""
build_tail_validation.py

Dual-mode Tail Validation (proxy vs sales).

Modes:
- --metric=playercount (public proxy)
- --metric=units (requires metric_daily_units)
- --metric=revenue (requires metric_daily_revenue)

Outputs:
- reports/figures/tail_lift_curve_<metric>.png
- reports/figures/tail_decay_by_tier_<metric>.png
- reports/figures/lift_curve_by_discount_tier_segmented_<metric>.png
- reports/figures/tail_absolute_uplift_by_tier_<metric>.png
- reports/tail_validation_summary_<metric>.csv
- reports/tail_validation_notes_<metric>.md
"""

from __future__ import annotations

import argparse
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tail validation segmentation.")
    parser.add_argument(
        "--metric",
        choices=["playercount", "units", "revenue"],
        default="playercount",
        help="Metric to use: playercount (proxy), units, or revenue.",
    )
    return parser.parse_args()


def metric_config(metric: str, event_df: pd.DataFrame) -> tuple[str, str, str]:
    if metric == "playercount":
        if "players" not in event_df.columns:
            raise SystemExit("ERROR: 'players' column not found for playercount proxy.")
        return "players", "engagement proxy (playercount)", "playercount"
    if metric == "units":
        if "metric_daily_units" not in event_df.columns:
            raise SystemExit(
                "ERROR: Required metric column 'metric_daily_units' not found. "
                "Provide units in the event dataset."
            )
        return "metric_daily_units", "units", "units"
    if metric == "revenue":
        if "metric_daily_revenue" not in event_df.columns:
            raise SystemExit(
                "ERROR: Required metric column 'metric_daily_revenue' not found. "
                "Provide revenue in the event dataset."
            )
        return "metric_daily_revenue", "revenue", "revenue"
    raise SystemExit("ERROR: Unknown metric selection.")


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
        return df.merge(sales_df[["sale_id", "discount_tier_bucket"]], on="sale_id", how="left")
    raise SystemExit("ERROR: Missing discount tier. Provide 'discount_tier_bucket' or 'discount_pct'.")


def compute_baseline(event_df: pd.DataFrame, metric_col: str) -> pd.DataFrame:
    pre = event_df[(event_df["k"] >= -14) & (event_df["k"] <= -1)]
    baseline = pre.groupby("sale_id", as_index=False)[metric_col].median()
    baseline = baseline.rename(columns={metric_col: "baseline_value"})
    return baseline


def assign_segments(baseline: pd.Series, notes: list[str]) -> pd.Series:
    n_events = baseline.notna().sum()
    if n_events < 200:
        quantiles = [0, 1 / 3, 2 / 3, 1]
        notes.append("Total events <200: used terciles (33/33/34).")
    else:
        quantiles = [0, 0.4, 0.8, 1]

    clean = baseline.replace([np.inf, -np.inf], np.nan)
    try:
        segments = pd.qcut(clean, q=quantiles, labels=SEGMENT_ORDER, duplicates="drop")
    except Exception:
        pct = clean.rank(method="average", pct=True)
        segments = pd.cut(pct, bins=quantiles, labels=SEGMENT_ORDER, include_lowest=True)

    seg_counts = segments.value_counts(dropna=True)
    if seg_counts.min() < MIN_SEGMENT_N:
        notes.append("Segment count <25: widened tail to bottom 50%.")
        quantiles = [0, 0.5, 0.8, 1]
        try:
            segments = pd.qcut(clean, q=quantiles, labels=SEGMENT_ORDER, duplicates="drop")
        except Exception:
            pct = clean.rank(method="average", pct=True)
            segments = pd.cut(pct, bins=quantiles, labels=SEGMENT_ORDER, include_lowest=True)
        seg_counts = segments.value_counts(dropna=True)
        if seg_counts.min() < MIN_SEGMENT_N:
            notes.append("Insufficient sample size: at least one segment <25 even after widening tail.")
    return segments.astype(str)


def collapse_tiers_for_segment(df: pd.DataFrame, segment: str, notes: list[str]) -> tuple[pd.DataFrame, list[str]]:
    sub = df[df["segment"] == segment].copy()
    counts = sub["discount_tier_bucket"].value_counts()
    if counts.min() >= MIN_TIER_N:
        return df, DISCOUNT_TIER_ORDER

    df = df.copy()
    df.loc[
        (df["segment"] == segment)
        & (df["discount_tier_bucket"].isin(["51-75%", "76-100%"])),
        "discount_tier_bucket",
    ] = "51%+"
    notes.append(f"Collapsed tiers to '51%+' for segment '{segment}' due to low N (<{MIN_TIER_N}).")
    tier_order = ["0-10%", "11-25%", "26-50%", "51%+"]
    return df, tier_order


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


def prep_data(metric: str) -> tuple[pd.DataFrame, pd.DataFrame, str, str, list[str]]:
    require(EVENT_WINDOW)
    event_df = pd.read_parquet(EVENT_WINDOW)
    metric_col, metric_label, metric_tag = metric_config(metric, event_df)

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
    return event_df, event_summary, metric_col, metric_label, notes


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
    for (segment, tier), val in flagged.items():
        warnings.append(f"Pre-period median lift not near 0 for {segment}/{tier}: {val:.1f}%")
    return warnings


def plot_tail_lift_curve(event_df: pd.DataFrame, metric_col: str, metric_label: str, metric_tag: str, notes: list[str]) -> None:
    df = event_df[(event_df["segment"] == "tail") & (event_df["baseline_value"] > 0)].copy()
    df["lift_pct"] = 100 * (df[metric_col] - df["baseline_value"]) / df["baseline_value"]
    df["lift_pct"] = df["lift_pct"].replace([np.inf, -np.inf], np.nan)
    df = df[df["lift_pct"].notna()]

    df, tier_order = collapse_tiers_for_segment(df, "tail", notes)
    agg = df.groupby(["discount_tier_bucket", "k"], as_index=False)["lift_pct"].median()

    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(7, 4))
    for tier in tier_order:
        sub = agg[agg["discount_tier_bucket"] == tier]
        if not sub.empty:
            ax.plot(sub["k"], sub["lift_pct"], label=tier)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.axhline(0, color="black", linewidth=0.6)
    n_events = df["sale_id"].nunique()
    title = f"Tail: Lift Curve by Discount Tier (N={n_events})"
    if metric_tag == "playercount":
        title += " — engagement proxy (playercount)"
    ax.set_title(title)
    ax.set_xlabel("Days from sale start (k)")
    ax.set_ylabel("Lift vs baseline (%)")
    ax.set_xlim(-14, 14)
    ax.legend(title="Discount tier", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"tail_lift_curve_{metric_tag}.png", dpi=150)
    plt.close(fig)


def plot_tail_decay(event_summary: pd.DataFrame, metric_tag: str, notes: list[str]) -> None:
    df = event_summary[event_summary["segment"] == "tail"].copy()
    df, tier_order = collapse_tiers_for_segment(df, "tail", notes)

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
    title = "Tail: Decay to Baseline by Discount Tier"
    if metric_tag == "playercount":
        title += " — engagement proxy (playercount)"
    ax.set_title(title)
    ax.set_xlabel(subtitle if subtitle else "Discount tier")
    ax.set_ylabel("Days to baseline")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"tail_decay_by_tier_{metric_tag}.png", dpi=150)
    plt.close(fig)


def plot_segmented_lift(event_df: pd.DataFrame, metric_col: str, metric_tag: str, notes: list[str]) -> None:
    df = event_df[event_df["baseline_value"] > 0].copy()
    df["lift_pct"] = 100 * (df[metric_col] - df["baseline_value"]) / df["baseline_value"]
    df["lift_pct"] = df["lift_pct"].replace([np.inf, -np.inf], np.nan)
    df = df[df["lift_pct"].notna()]

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)

    for idx, segment in enumerate(SEGMENT_ORDER):
        sub = df[df["segment"] == segment].copy()
        sub, tier_order = collapse_tiers_for_segment(sub, segment, notes)
        agg = sub.groupby(["discount_tier_bucket", "k"], as_index=False)["lift_pct"].median()

        ax = axes[idx]
        for tier in tier_order:
            s = agg[agg["discount_tier_bucket"] == tier]
            if not s.empty:
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
    title = "Lift Curve by Discount Tier (Tail vs Mid vs Head)"
    if metric_tag == "playercount":
        title += " — engagement proxy (playercount)"
    fig.suptitle(title, y=1.02)
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"lift_curve_by_discount_tier_segmented_{metric_tag}.png", dpi=150)
    plt.close(fig)


def plot_tail_absolute_uplift(event_summary: pd.DataFrame, metric_label: str, metric_tag: str, notes: list[str]) -> None:
    df = event_summary[event_summary["segment"] == "tail"].copy()
    df, tier_order = collapse_tiers_for_segment(df, "tail", notes)

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
    title = "Tail: Peak Absolute Uplift by Discount Tier"
    if metric_tag == "playercount":
        title += " — engagement proxy (playercount)"
    ax.set_title(title)
    ax.set_xlabel("Discount tier")
    ax.set_ylabel(f"Peak absolute uplift ({metric_label})")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"tail_absolute_uplift_by_tier_{metric_tag}.png", dpi=150)
    plt.close(fig)


def write_summary(event_summary: pd.DataFrame, metric_tag: str) -> pd.DataFrame:
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
    summary = summary.rename(columns={"median_peak_abs_uplift": f"median_peak_abs_uplift_{metric_tag}"})
    summary = summary.sort_values(["segment", "discount_tier_bucket"])
    out = REPORTS_DIR / f"tail_validation_summary_{metric_tag}.csv"
    summary.to_csv(out, index=False)
    return summary


def write_notes(
    summary: pd.DataFrame | None,
    metric_tag: str,
    metric_label: str,
    notes: list[str],
    warnings: list[str],
    baseline_zero_count: int,
) -> None:
    out = REPORTS_DIR / f"tail_validation_notes_{metric_tag}.md"
    lines: list[str] = []
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
        total_events = int(summary["n_events"].sum())
        lines.append(f"- Total events in summary: {total_events}")
        for seg in SEGMENT_ORDER:
            seg_n = int(summary[summary["segment"] == seg]["n_events"].sum())
            lines.append(f"- {seg}: {seg_n}")
    lines.append("")
    lines.append("## Key findings")
    if summary is None or summary.empty:
        lines.append("- Not generated (missing required metric).")
    else:
        tail = summary[summary["segment"] == "tail"].copy()
        if not tail.empty:
            top_lift = tail.sort_values("median_peak_lift_pct", ascending=False).head(1)
            if not top_lift["median_peak_lift_pct"].isna().all():
                tier = top_lift["discount_tier_bucket"].iloc[0]
                val = top_lift["median_peak_lift_pct"].iloc[0]
                lines.append(f"- Tail: highest median peak lift is {val:.1f}% at tier {tier}.")
            uplift_col = f"median_peak_abs_uplift_{metric_tag}"
            if uplift_col in tail.columns:
                top_abs = tail.sort_values(uplift_col, ascending=False).head(1)
                tier = top_abs["discount_tier_bucket"].iloc[0]
                val = top_abs[uplift_col].iloc[0]
                lines.append(f"- Tail: highest median peak absolute uplift is {val:.2f} ({metric_label}) at tier {tier}.")
        if metric_tag == "playercount":
            lines.append("- All findings are engagement proxy signals (playercount), not sales outcomes.")
    lines.append("")
    lines.append("## Caveats")
    lines.append(
        f"- baseline_value == 0 events: {baseline_zero_count} (excluded from % lift; included for absolute uplift where possible)."
    )
    for n in notes:
        lines.append(f"- {n}")
    for w in warnings:
        lines.append(f"- {w}")
    if metric_tag == "playercount":
        lines.append("- This mode uses engagement proxy (playercount) and does not imply revenue or ROI outcomes.")
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        event_df, event_summary, metric_col, metric_label, notes = prep_data(args.metric)
    except SystemExit as e:
        write_notes(None, args.metric, args.metric, [str(e)], [], baseline_zero_count=0)
        raise

    warnings = preperiod_bias_check(event_df, metric_col)
    baseline_zero_count = int((event_summary["baseline_zero"] == True).sum())

    plot_tail_lift_curve(event_df, metric_col, metric_label, args.metric, notes)
    plot_tail_decay(event_summary, args.metric, notes)
    plot_segmented_lift(event_df, metric_col, args.metric, notes)
    plot_tail_absolute_uplift(event_summary, metric_label, args.metric, notes)

    summary = write_summary(event_summary, args.metric)
    write_notes(summary, args.metric, metric_label, notes, warnings, baseline_zero_count)

    print("Saved figures to reports/figures/")
    print(f"Saved summary table to reports/tail_validation_summary_{args.metric}.csv")
    print(f"Saved notes to reports/tail_validation_notes_{args.metric}.md")


if __name__ == "__main__":
    main()
