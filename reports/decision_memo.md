# Decision Memo (Engagement Lift -> Revenue ROI)

## Objective
Summarize sale strategy options using public engagement signals, while clearly gating all ROI claims on partner revenue data.

## Dataset
- Source: Mendeley Steam dataset
- Coverage: [fill in]
- Notes: [fill in]

## What we can infer from public data
- Engagement lift patterns by discount tier, popularity, and cadence.
- Relative lift stability across segments (after minimum sample thresholds).
- Which tiers show consistent playercount response (engagement proxy, not revenue).
- Mechanism tags: wishlist-notify eligibility (>=20% discount heuristic) and seasonal overlap (major sale windows).

## What requires partner data
- Units sold, net revenue, and margin impact by tier/region/channel.
- Refund/chargeback effects and true net vs gross impact.
- Retention and long-term value effects beyond short-term lift.

## Public playbook excerpt (top 10)
Source: `playbook_table_public.csv` (top 30 rows by median lift; rounded for public share).

| discount_tier_bucket | popularity_bucket | cadence_bucket | n_sales | median_peak_lift_pct | median_AUL | median_decay_days_to_baseline |
| --- | --- | --- | --- | --- | --- | --- |
| 51-75% | Q1 | mid | 650 | 239.1 | 9.6 | 4.0 |
| 76-100% | Q1 | mid | 356 | 228.4 | 8.99 | 4.0 |
| 51-75% | Q1 | high | 642 | 224.7 | 6.85 | 3.0 |
| 76-100% | Q1 | low | 205 | 218.2 | 10.09 | 4.0 |
| 51-75% | Q1 | low | 436 | 216.9 | 9.63 | 4.0 |
| 76-100% | Q1 | high | 353 | 158.7 | 5.48 | 3.0 |
| 26-50% | Q1 | low | 267 | 138.2 | 4.33 | 4.0 |
| 26-50% | Q1 | mid | 198 | 135.6 | 6.8 | 3.0 |
| 11-25% | Q1 | low | 31 | 128.5 | 6.25 | 3.0 |
| 76-100% | Q2 | low | 226 | 124.2 | 5.24 | 7.5 |

## Revenue levers translation (framing only)
- Engagement lift -> potential units proxy hypothesis (higher lift may correlate with units sold).
- Depth and cadence tiers -> candidate levers for pricing strategy experiments.
- These are directional signals only until validated with net revenue exports.
- Mechanism tags are hypothesis labels, not causal proof; validate with partner exports.

## Net vs gross disclaimer
Public data cannot calculate revenue or profit. Any ROI claim must be validated with partner exports that include net revenue, taxes/fees, and refunds. Treat all lift-based statements as hypotheses until confirmed.

## Recommended Actions
- [Action 1]
- [Action 2]

## Risks and Caveats
- Engagement lift is not revenue; conversion and price elasticity are unobserved.
- Segment performance may shift by region, store events, or macro conditions.

## Appendix
- Public playbook table: `playbook_table_public.csv`
- Figures: `figures/`
