"""
build_tail_validation.py

Purpose:
Build Tail/Mid/Head segmentation figures for discount validation:
- Lift curve by discount tier (Tail vs Mid vs Head)
- Decay-to-baseline boxplot by discount tier (Tail vs Mid vs Head)
- Counts table: bucket x discount tier
- Absolute uplift (proxy units) chart for Tail

Notes:
- Uses public signals only (playercount) as a proxy where units/revenue are not available.
- Baseline per event is computed from days -14:-1 in the event window.
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

EVENT_WINDOW = DATA_DIR / "event_window.parquet"
SALES = DATA_DIR / "sales.parquet"

DISCOUNT_TIER_ORDER = ["0-10%", "11-25%", "26-50%", "51-75%", "76-100%"]
BUCKET_ORDER = ["Tail", "Mid", "Head"]


def require(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")


def compute_baseline(event_df: pd.DataFrame) -> pd.DataFrame:
    pre = event_df[(event_df["k"] >= -14) & (event_df["k"] <= -1)]
    baseline = pre.groupby("sale_id", as_index=False)["players"].mean()
    baseline = baseline.rename(columns={"players": "baseline_pre"})
    return baseline


def assign_buckets(baseline_series: pd.Series) -> pd.Series:
    clean = baseline_series.replace([np.inf, -np.inf], np.nan)
    try:
        buckets = pd.qcut(clean, q=3, labels=BUCKET_ORDER, duplicates="drop")
        if buckets.isna().all() or len(getattr(buckets, "cat").categories) < 3:
            raise ValueError("qcut produced too few buckets")
        return buckets
    except Exception:
        pct = clean.rank(method="average", pct=True)
        return pd.cut(pct, bins=[0, 1 / 3, 2 / 3, 1], labels=BUCKET_ORDER, include_lowest=True)


def prep_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    require(EVENT_WINDOW)
    require(SALES)

    event_df = pd.read_parquet(EVENT_WINDOW)
    sales_df = pd.read_parquet(SALES)

    baseline = compute_baseline(event_df)
    sales_df = sales_df.merge(baseline, on="sale_id", how="left")
    sales_df["baseline_pre"] = sales_df["baseline_pre"].fillna(sales_df["baseline_players"])

    sales_df["bucket"] = assign_buckets(sales_df["baseline_pre"])
    sales_df = sales_df[sales_df["bucket"].notna()].copy()
    sales_df["bucket"] = sales_df["bucket"].astype(str)

    event_df = event_df.merge(
        sales_df[["sale_id", "discount_tier_bucket", "bucket", "baseline_pre"]],
        on="sale_id",
        how="inner",
    )
    return event_df, sales_df


def plot_lift_curve(event_df: pd.DataFrame) -> None:
    df = event_df.copy()
    df["lift_pct"] = df["lift_pct"].replace([np.inf, -np.inf], np.nan)
    df = df[df["lift_pct"].notna()]

    agg = (
        df.groupby(["bucket", "discount_tier_bucket", "k"], as_index=False)["lift_pct"]
        .mean()
        .rename(columns={"lift_pct": "mean_lift_pct"})
    )

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)

    for idx, bucket in enumerate(BUCKET_ORDER):
        ax = axes[idx]
        sub = agg[agg["bucket"] == bucket]
        for tier in DISCOUNT_TIER_ORDER:
            s = sub[sub["discount_tier_bucket"] == tier]
            if s.empty:
                continue
            ax.plot(s["k"], s["mean_lift_pct"], label=tier)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_title(f"{bucket}")
        ax.set_xlabel("Days from sale start (k)")
        if idx == 0:
            ax.set_ylabel("Lift vs baseline (%)")
        ax.set_xlim(-14, 14)
    axes[-1].legend(title="Discount tier", fontsize=8)

    out = FIG_DIR / "lift_curve_by_discount_tier_tail_mid_head.png"
    fig.suptitle("Lift Curve by Discount Tier (Tail vs Mid vs Head)", y=1.02)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_decay_boxplot(sales_df: pd.DataFrame) -> None:
    df = sales_df.copy()
    df["decay_days_to_baseline"] = df["decay_days_to_baseline"].replace([np.inf, -np.inf], np.nan)
    df = df[df["decay_days_to_baseline"].notna()]

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)

    for idx, bucket in enumerate(BUCKET_ORDER):
        ax = axes[idx]
        sub = df[df["bucket"] == bucket]
        if sub.empty:
            continue
        sns.boxplot(
            data=sub,
            x="discount_tier_bucket",
            y="decay_days_to_baseline",
            order=DISCOUNT_TIER_ORDER,
            ax=ax,
            showfliers=False,
        )
        ax.set_title(f"{bucket}")
        ax.set_xlabel("Discount tier")
        if idx == 0:
            ax.set_ylabel("Days to baseline")
        ax.tick_params(axis="x", rotation=35)

    out = FIG_DIR / "decay_to_baseline_by_discount_tier_tail_mid_head.png"
    fig.suptitle("Decay to Baseline by Discount Tier (Tail vs Mid vs Head)", y=1.02)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_counts_table(sales_df: pd.DataFrame) -> None:
    counts = pd.crosstab(sales_df["bucket"], sales_df["discount_tier_bucket"])
    counts = counts.reindex(index=BUCKET_ORDER, columns=DISCOUNT_TIER_ORDER, fill_value=0)

    fig, ax = plt.subplots(figsize=(8, 2.5))
    ax.axis("off")
    table = ax.table(
        cellText=counts.values,
        rowLabels=counts.index,
        colLabels=counts.columns,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.4)
    ax.set_title("Event Counts by Bucket x Discount Tier", pad=10)

    out = FIG_DIR / "counts_by_bucket_discount_tier.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_tail_absolute_uplift(event_df: pd.DataFrame) -> None:
    df = event_df.copy()
    df = df[df["in_sale"] == True]
    df["uplift"] = df["players"] - df["baseline_pre"]

    uplift_by_sale = (
        df.groupby(["sale_id", "discount_tier_bucket", "bucket"], as_index=False)["uplift"].sum()
    )
    tail = uplift_by_sale[uplift_by_sale["bucket"] == "Tail"]

    if tail.empty:
        return

    summary = (
        tail.groupby("discount_tier_bucket", as_index=False)["uplift"]
        .median()
        .rename(columns={"uplift": "median_uplift"})
    )
    summary = summary.set_index("discount_tier_bucket").reindex(DISCOUNT_TIER_ORDER).dropna().reset_index()

    fig, ax = plt.subplots(figsize=(7, 4))
    sns.barplot(data=summary, x="discount_tier_bucket", y="median_uplift", ax=ax)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Discount tier")
    ax.set_ylabel("Median absolute uplift (player-days)")
    ax.set_title("Tail: Absolute Uplift by Discount Tier (Proxy Units)")
    ax.tick_params(axis="x", rotation=35)

    out = FIG_DIR / "tail_absolute_uplift_by_discount_tier.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    event_df, sales_df = prep_data()

    plot_lift_curve(event_df)
    plot_decay_boxplot(sales_df)
    plot_counts_table(sales_df)
    plot_tail_absolute_uplift(event_df)

    print("Saved figures to reports/figures/")


if __name__ == "__main__":
    main()
