from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns


def plot_overall_lift_curve(event_window, output_path: str | Path) -> None:
    if event_window.empty:
        return
    data = event_window.groupby("k", as_index=False)["lift_pct"].median()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(data["k"], data["lift_pct"], marker="o", linewidth=2)
    ax.axvline(0, color="black", linestyle="--", linewidth=1)
    ax.set_title("Median Lift Curve (Overall)")
    ax.set_xlabel("Event Day (k)")
    ax.set_ylabel("Lift %")
    fig.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_lift_curve_by_discount_tier(event_window, sales, output_path: str | Path) -> None:
    if event_window.empty or sales.empty:
        return
    merged = event_window.merge(sales[["sale_id", "discount_tier_bucket"]], on="sale_id", how="left")
    data = merged.groupby(["discount_tier_bucket", "k"], as_index=False)["lift_pct"].median()

    fig, ax = plt.subplots(figsize=(9, 5))
    for tier, subset in data.groupby("discount_tier_bucket"):
        ax.plot(subset["k"], subset["lift_pct"], marker="o", linewidth=1.5, label=str(tier))
    ax.axvline(0, color="black", linestyle="--", linewidth=1)
    ax.set_title("Median Lift Curve by Discount Tier")
    ax.set_xlabel("Event Day (k)")
    ax.set_ylabel("Lift %")
    ax.legend(title="Discount Tier", fontsize=8)
    fig.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_lift_curve_seasonal_vs_nonseasonal(event_window, sales, output_path: str | Path) -> None:
    if event_window.empty or sales.empty or "seasonal_overlap" not in sales.columns:
        return
    merged = event_window.merge(sales[["sale_id", "seasonal_overlap"]], on="sale_id", how="left")
    merged["seasonal_overlap"] = merged["seasonal_overlap"].fillna(False)
    merged["seasonal_label"] = merged["seasonal_overlap"].map(
        {True: "Seasonal overlap", False: "Non-seasonal"}
    )
    data = merged.groupby(["seasonal_label", "k"], as_index=False)["lift_pct"].median()

    fig, ax = plt.subplots(figsize=(8, 4))
    for label, subset in data.groupby("seasonal_label"):
        ax.plot(subset["k"], subset["lift_pct"], marker="o", linewidth=2, label=label)
    ax.axvline(0, color="black", linestyle="--", linewidth=1)
    ax.set_title("Median Lift Curve: Seasonal vs Non-seasonal")
    ax.set_xlabel("Event Day (k)")
    ax.set_ylabel("Lift %")
    ax.legend(fontsize=8)
    fig.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_decay_by_discount_tier(sales, output_path: str | Path) -> None:
    if sales.empty:
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.boxplot(
        data=sales,
        x="discount_tier_bucket",
        y="decay_days_to_baseline",
        ax=ax,
    )
    ax.set_title("Decay Days to Baseline by Discount Tier")
    ax.set_xlabel("Discount Tier")
    ax.set_ylabel("Decay Days")
    fig.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_lift_vs_discount_scatter(sales, output_path: str | Path) -> None:
    if sales.empty:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.scatterplot(
        data=sales,
        x="sale_depth_max",
        y="peak_lift_pct",
        hue="discount_tier_bucket",
        ax=ax,
    )
    ax.set_title("Peak Lift vs Discount Depth")
    ax.set_xlabel("Sale Depth (discount_pct)")
    ax.set_ylabel("Peak Lift %")
    fig.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
