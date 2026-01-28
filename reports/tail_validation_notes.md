# Tail Validation Notes

## Definitions used
- Baseline window: k in [-14, -1], baseline_value = median(metric) in this window.
- Lift %: 100 * (metric(k) - baseline_value) / baseline_value (baseline_value > 0).
- Peak window: k in [0, +6], peak_lift_pct = max lift_pct, peak_abs_uplift = max(metric - baseline).
- Decay day: smallest k in [0, +14] where metric(k) <= baseline_value; censored at 14 if never returns.

## Sample sizes
- No summary generated (missing required metric).

## Key findings
- Not generated (missing required metric).

## Caveats
- baseline_value == 0 events: 0 (excluded from % lift; included for absolute uplift when possible).
- ERROR: Required metric column not found. Expected 'metric_daily_units' or 'metric_daily_revenue' in event dataset. Provide raw metric to compute baseline and absolute uplift.