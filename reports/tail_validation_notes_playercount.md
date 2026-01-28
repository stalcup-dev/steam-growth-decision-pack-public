# Tail Validation Notes

## Definitions used
- Baseline window: k in [-14, -1], baseline_value = median(metric) in this window.
- Lift %: 100 * (metric(k) - baseline_value) / baseline_value (baseline_value > 0).
- Peak window: k in [0, +6], peak_lift_pct = max lift_pct, peak_abs_uplift = max(metric - baseline).
- Decay day: smallest k in [0, +14] where metric(k) <= baseline_value; censored at 14 if never returns.

## Sample sizes
- Total events in summary: 13498
- tail: 5400
- mid: 5399
- head: 2699

## Key findings
- Tail: highest median peak lift is 135.2% at tier 51-75%.
- Tail: highest median peak absolute uplift is 13.39 (engagement proxy (playercount)) at tier 26-50%.
- All findings are engagement proxy signals (playercount), not sales outcomes.

## Caveats
- baseline_value == 0 events: 202 (excluded from % lift; included for absolute uplift where possible).
- This mode uses engagement proxy (playercount) and does not imply revenue or ROI outcomes.