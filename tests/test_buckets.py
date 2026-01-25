import pandas as pd

from src.metrics import add_buckets, build_playbook_table


def test_add_buckets_no_nan_discount_tier():
    sales = pd.DataFrame(
        {
            "sale_id": [1, 2, 3, 4],
            "sale_depth_max": [10, None, 150, -5],
            "baseline_players": [100, 200, 300, 400],
            "sale_share_last_90d": [0.1, 0.2, 0.3, 0.4],
            "peak_lift_pct": [10, 20, 30, 40],
            "AUL": [1.0, 2.0, 3.0, 4.0],
            "decay_days_to_baseline": [1, 2, 3, 4],
        }
    )
    config = {"discount_tiers": [0.10, 0.25, 0.50, 0.75, 0.90], "popularity_quantiles": 4}

    bucketed = add_buckets(sales, config=config)

    assert bucketed["discount_tier_bucket"].isna().sum() == 0
    assert "Unknown" in bucketed["discount_tier_bucket"].values


def test_build_playbook_table_has_no_zero_counts():
    sales = pd.DataFrame(
        {
            "sale_id": [1, 2, 3, 4],
            "sale_depth_max": [10, 20, None, 80],
            "baseline_players": [100, 200, 300, 400],
            "sale_share_last_90d": [0.1, 0.2, 0.3, 0.4],
            "peak_lift_pct": [10, 20, 30, 40],
            "AUL": [1.0, 2.0, 3.0, 4.0],
            "decay_days_to_baseline": [1, 2, 3, 4],
        }
    )
    config = {"discount_tiers": [0.10, 0.25, 0.50, 0.75, 0.90], "popularity_quantiles": 4}

    bucketed = add_buckets(sales, config=config)
    playbook = build_playbook_table(bucketed)

    assert not playbook.empty
    assert playbook["n_sales"].min() >= 1
