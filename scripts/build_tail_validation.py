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
    parser.add_argument(
        "--clip_lift_pct",
        nargs=2,
        type=float,
        default=[-90, 500],
        help="Clip lift_pct for plotting only: low high (default -90 500).",
    )
    return parser.parse_args()


def metric_config(metric: str, event_df: pd.DataFrame) -> tuple[str, str, str, float]:
    if metric == "playercount":
        if "players" not in event_df.columns:
            raise SystemExit("ERROR: 'players' column not found for playercount proxy.")
        return "players", "engagement proxy (playercount)", "playercount", 1.0
    if metric == "units":
        if "metric_daily_units" not in event_df.columns:
            raise SystemExit(
                "ERROR: Required metric column 'metric_daily_units' not found. "
                "Provide units in the event dataset."
            )
        return "metric_daily_units", "units", "units", 0.0
    if metric == "revenue":
        if "metric_daily_revenue" not in event_df.columns:
            raise SystemExit(
                "ERROR: Required metric column 'metric_daily_revenue' not found. "
                "Provide revenue in the event dataset."
            )
        return "metric_daily_revenue", "revenue", "revenue", 0.0
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
    return df, ["0-10%", "11-25%", "26-50%", "51%+"]


def compute_decay(event_df: pd.DataFrame, metric_col: str) -> pd.DataFrame:
    def _decay_for_group(g: pd.DataFrame) -> pd.Series:
        baseline = g["baseline_value"].iloc[0]
        post = g[(g["k"] >= 0) & (g["k"] <= 14)].sort_values("k")
        decay_k = post[post[metric_col] <= baseline]["k"]
        if len(decay_k) == 0:
            return pd.Series({"decay_day": 14, "decay_censored": True})
        return pd.Series({"decay_day": int(decay_k.iloc[0]), "decay_censored": False})

    return event_df.groupby("sale_id", as_index=False).apply(_decay_for_group)


def compute_peaks(event_df: pd.DataFrame, metric_col: str, baseline_floor: float) -> pd.DataFrame:
    post = event_df[(event_df["k"] >= 0) & (event_df["k"] <= 6)].copy()
    post["abs_uplift"] = post[metric_col] - post["baseline_value"]
    post["lift_pct"] = np.where(
        post["baseline_value"] >= baseline_floor,
        100 * (post[metric_col] - post["baseline_value"]) / post["baseline_value"],
        np.nan,
    )
    peak_abs = post.groupby("sale_id", as_index=False)["abs_uplift"].max().rename(
        columns={"abs_uplift": "peak_abs_uplift"}
    )
    peak_pct = post.groupby("sale_id", as_index=False)["lift_pct"].max().rename(
        columns={"lift_pct": "peak_lift_pct"})
    return peak_abs.merge(peak_pct, on="sale_id", how="left")


def prep_data(metric: str) -> tuple[pd.DataFrame, pd.DataFrame, str, str, str, float, list[str]]:
    require(EVENT_WINDOW)
    event_df = pd.read_parquet(EVENT_WINDOW)
    metric_col, metric_label, metric_tag, baseline_floor = metric_config(metric, event_df)

    sales_df = pd.read_parquet(SALES) if SALES.exists() else None
    event_df = ensure_discount_tier(event_df, sales_df)

    baseline = compute_baseline(event_df, metric_col)
    event_df = event_df.merge(baseline, on="sale_id", how="left")
    event_df["baseline_zero"] = event_df["baseline_value"] < baseline_floor

    notes: list[str] = []
    event_df["segment"] = assign_segments(event_df["baseline_value"], notes)

    decay = compute_decay(event_df, metric_col)
    peaks = compute_peaks(event_df, metric_col, baseline_floor)

    event_summary = (
        event_df[["sale_id", "discount_tier_bucket", "segment", "baseline_value", "baseline_zero"]]
        .drop_duplicates("sale_id")
        .merge(decay, on="sale_id", how="left")
        .merge(peaks, on="sale_id", how="left")
    )
    return event_df, event_summary, metric_col, metric_label, metric_tag, baseline_floor, notes


def preperiod_bias_check(event_df: pd.DataFrame, metric_col: str, baseline_floor: float) -> list[tuple[str, str, float]]:
    df = event_df[(event_df["k"] >= -14) & (event_df["k"] <= -1)].copy()
    df = df[df["baseline_value"] >= baseline_floor]
    df["lift_pct"] = 100 * (df[metric_col] - df["baseline_value"]) / df["baseline_value"]
    df["lift_pct"] = df["lift_pct"].replace([np.inf, -np.inf], np.nan)
    df = df[df["lift_pct"].notna()]
    if df.empty:
        return []
    med = df.groupby(["segment", "discount_tier_bucket"])["lift_pct"].median()
    flagged = med[med.abs() > 5]
    return [(seg, tier, float(val)) for (seg, tier), val in flagged.items()]


def clip_for_plot(series: pd.Series, clip_lift_pct: tuple[float, float]) -> tuple[pd.Series, bool]:
    lo, hi = clip_lift_pct
    clipped = series.clip(lo, hi)
    clipped_any = (series != clipped).any()
    return clipped, bool(clipped_any)


def warning_banner(ax: plt.Axes, warnings: list[tuple[str, str, float]], segment: str | None = None) -> None:
    if segment:
        warnings = [w for w in warnings if w[0] == segment]
    if not warnings:
        return
    text = "WARNING: pre-period median lift >5% for " + ", ".join(
        [f"{seg}/{tier} ({val:.1f}%)" for seg, tier, val in warnings]
    )
    ax.text(
        0.5,
        1.03,
        text,
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=8,
        color="darkred",
        bbox=dict(boxstyle="round,pad=0.2", facecolor="#fff1f1", edgecolor="darkred"),
    )


def plot_tail_lift_curve(
    event_df: pd.DataFrame,
    metric_col: str,
    metric_label: str,
    metric_tag: str,
    baseline_floor: float,
    clip_lift_pct: tuple[float, float],
    warnings: list[tuple[str, str, float]],
    notes: list[str],
) -> None:
    df = event_df[(event_df["segment"] == "tail") & (event_df["baseline_value"] >= baseline_floor)].copy()
    df["lift_pct"] = 100 * (df[metric_col] - df["baseline_value"]) / df["baseline_value"]
    df["lift_pct"] = df["lift_pct"].replace([np.inf, -np.inf], np.nan)
    df = df[df["lift_pct"].notna()]

    df, tier_order = collapse_tiers_for_segment(df, "tail", notes)
    agg = df.groupby(["discount_tier_bucket", "k"], as_index=False)["lift_pct"].median()
    agg["lift_plot"], clipped_any = clip_for_plot(agg["lift_pct"], clip_lift_pct)

    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(7, 4))
    for tier in tier_order:
        sub = agg[agg["discount_tier_bucket"] == tier]
        if not sub.empty:
            ax.plot(sub["k"], sub["lift_plot"], label=tier)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.axhline(0, color="black", linewidth=0.6)
    n_events = df["sale_id"].nunique()
    title = f"Tail: Lift Curve by Discount Tier (N={n_events}) — Engagement proxy (playercount)" if metric_tag == "playercount" else f"Tail: Lift Curve by Discount Tier (N={n_events})"
    ax.set_title(title)
    ax.set_xlabel("Days from sale start (k)")
    ylab = "Lift vs baseline (%) — engagement proxy" if metric_tag == "playercount" else "Lift vs baseline (%)"
    ax.set_ylabel(ylab)
    ax.set_xlim(-14, 14)
    ax.legend(title="Discount tier", fontsize=8)
    if clipped_any:
        ax.text(0.02, 0.02, f"Clipped to [{clip_lift_pct[0]}, {clip_lift_pct[1]}] for readability", transform=ax.transAxes, fontsize=7)
    warning_banner(ax, warnings, "tail")
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"tail_lift_curve_{metric_tag}.png", dpi=150)
    plt.close(fig)


def plot_tail_decay(event_summary: pd.DataFrame, metric_tag: str, warnings: list[tuple[str, str, float]], notes: list[str]) -> None:
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
    n_events = df["sale_id"].nunique()
    title = f"Tail: Decay to Baseline by Discount Tier (N={n_events})"
    if metric_tag == "playercount":
        title += " — Engagement proxy (playercount)"
    ax.set_title(title)
    ax.set_xlabel(subtitle if subtitle else "Discount tier")
    ax.set_ylabel("Days to baseline")
    ax.tick_params(axis="x", rotation=35)
    warning_banner(ax, warnings, "tail")
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"tail_decay_by_tier_{metric_tag}.png", dpi=150)
    plt.close(fig)


def plot_segmented_lift(
    event_df: pd.DataFrame,
    metric_col: str,
    metric_tag: str,
    baseline_floor: float,
    clip_lift_pct: tuple[float, float],
    warnings: list[tuple[str, str, float]],
    notes: list[str],
) -> None:
    df = event_df[event_df["baseline_value"] >= baseline_floor].copy()
    df["lift_pct"] = 100 * (df[metric_col] - df["baseline_value"]) / df["baseline_value"]
    df["lift_pct"] = df["lift_pct"].replace([np.inf, -np.inf], np.nan)
    df = df[df["lift_pct"].notna()]

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
    clipped_any = False

    for idx, segment in enumerate(SEGMENT_ORDER):
        sub = df[df["segment"] == segment].copy()
        sub, tier_order = collapse_tiers_for_segment(sub, segment, notes)
        agg = sub.groupby(["discount_tier_bucket", "k"], as_index=False)["lift_pct"].median()
        agg["lift_plot"], seg_clipped = clip_for_plot(agg["lift_pct"], clip_lift_pct)
        clipped_any = clipped_any or seg_clipped

        ax = axes[idx]
        for tier in tier_order:
            s = agg[agg["discount_tier_bucket"] == tier]
            if not s.empty:
                ax.plot(s["k"], s["lift_plot"], label=tier)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.axhline(0, color="black", linewidth=0.6)
        n_events = sub["sale_id"].nunique()
        ax.set_title(f"{segment.capitalize()} (N={n_events})")
        ax.set_xlabel("k")
        if idx == 0:
            ylab = "Lift vs baseline (%) — engagement proxy" if metric_tag == "playercount" else "Lift vs baseline (%)"
            ax.set_ylabel(ylab)
        ax.set_xlim(-14, 14)
        warning_banner(ax, warnings, segment)

    axes[-1].legend(title="Discount tier", fontsize=8)
    title = "Lift Curve by Discount Tier (Tail vs Mid vs Head)"
    if metric_tag == "playercount":
        title += " — Engagement proxy (playercount)"
    fig.suptitle(title, y=1.02)
    if clipped_any:
        fig.text(0.01, 0.01, f"Clipped to [{clip_lift_pct[0]}, {clip_lift_pct[1]}] for readability", fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"lift_curve_by_discount_tier_segmented_{metric_tag}.png", dpi=150)
    plt.close(fig)


def plot_tail_absolute_uplift(
    event_summary: pd.DataFrame,
    metric_label: str,
    metric_tag: str,
    notes: list[str],
) -> None:
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
    n_events = df["sale_id"].nunique()
    title = f"Tail: Peak Absolute Uplift by Discount Tier (N={n_events})"
    if metric_tag == "playercount":
        title += " — Engagement proxy (playercount)"
    ax.set_title(title)
    ax.set_xlabel("Discount tier")
    ylab = "Δ playercount vs baseline" if metric_tag == "playercount" else f"Δ {metric_label} vs baseline"
    ax.set_ylabel(ylab)
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
    warnings: list[tuple[str, str, float]],
    baseline_below_floor_count: int,
    baseline_floor: float,
) -> None:
    out = REPORTS_DIR / f"tail_validation_notes_{metric_tag}.md"
    lines: list[str] = []
    lines.append("# Tail Validation Notes")
    lines.append("")
    lines.append("## Definitions used")
    lines.append("- Baseline window: k in [-14, -1], baseline_value = median(metric) in this window.")
    lines.append("- Lift %: 100 * (metric(k) - baseline_value) / baseline_value (baseline_value >= baseline floor).")
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
        f"- baseline_value < {baseline_floor} events: {baseline_below_floor_count} (excluded from % lift; included for absolute uplift and decay)."
    )
    for n in notes:
        lines.append(f"- {n}")
    for seg, tier, val in warnings:
        lines.append(f"- WARNING: pre-period median lift not near 0 for {seg}/{tier}: {val:.1f}%")
    if metric_tag == "playercount":
        lines.append("- This mode uses engagement proxy (playercount) and does not imply revenue or ROI outcomes.")
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        event_df, event_summary, metric_col, metric_label, metric_tag, baseline_floor, notes = prep_data(args.metric)
    except SystemExit as e:
        write_notes(None, args.metric, args.metric, [str(e)], [], baseline_below_floor_count=0, baseline_floor=0)
        raise

    warnings = preperiod_bias_check(event_df, metric_col, baseline_floor)
    baseline_below_floor_count = int((event_summary["baseline_zero"] == True).sum())

    clip_range = (args.clip_lift_pct[0], args.clip_lift_pct[1])

    plot_tail_lift_curve(
        event_df,
        metric_col,
        metric_label,
        metric_tag,
        baseline_floor,
        clip_range,
        warnings,
        notes,
    )
    plot_tail_decay(event_summary, metric_tag, warnings, notes)
    plot_segmented_lift(event_df, metric_col, metric_tag, baseline_floor, clip_range, warnings, notes)
    plot_tail_absolute_uplift(event_summary, metric_label, metric_tag, notes)

    summary = write_summary(event_summary, metric_tag)
    write_notes(
        summary,
        metric_tag,
        metric_label,
        notes,
        warnings,
        baseline_below_floor_count,
        baseline_floor,
    )

    print("Saved figures to reports/figures/")
    print(f"Saved summary table to reports/tail_validation_summary_{metric_tag}.csv")
    print(f"Saved notes to reports/tail_validation_notes_{metric_tag}.md")


if __name__ == "__main__":
    main()
