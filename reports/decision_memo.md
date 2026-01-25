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

## Stable playbook excerpt (top 10)
Source: `playbook_table_stable.csv` (filtered with n_sales >= 20; lift capped at 1000 for ranking).

| discount_tier_bucket | popularity_bucket | cadence_bucket | n_sales | median_peak_lift_pct | iqr_peak_lift_pct | median_AUL | median_decay_days_to_baseline | median_lift_per_discount_point | median_peak_lift_pct_capped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 51-75% | Q1 | mid | 650 | 239.071029899926 | 883.1795986543125 | 9.604202304178733 | 4.0 | 3.823199023199023 | 239.071029899926 |
| 76-100% | Q1 | mid | 356 | 228.38399954645405 | 757.8292516412502 | 8.989898989898991 | 4.0 | 2.72380177142082 | 228.38399954645405 |
| 51-75% | Q1 | high | 642 | 224.69512195121948 | 865.220115723131 | 6.854051904146367 | 3.0 | 3.674078194630382 | 224.69512195121948 |
| 76-100% | Q1 | low | 205 | 218.18181818181816 | 709.934065186119 | 10.090909090909092 | 4.0 | 2.5188924592514086 | 218.18181818181816 |
| 51-75% | Q1 | low | 436 | 216.9092310688731 | 584.0138988770126 | 9.634100187608135 | 4.0 | 3.3964533728901065 | 216.9092310688731 |
| 76-100% | Q1 | high | 353 | 158.71961550879627 | 443.9351580466248 | 5.484887595273379 | 3.0 | 1.9323360585902392 | 158.71961550879627 |
| 26-50% | Q1 | low | 267 | 138.2229614998094 | 328.4844012191157 | 4.325668858384738 | 4.0 | 3.171728051947243 | 138.2229614998094 |
| 26-50% | Q1 | mid | 198 | 135.6068709337271 | 323.08441856720367 | 6.801769106342061 | 3.0 | 3.0599199791138 | 135.6068709337271 |
| 11-25% | Q1 | low | 31 | 128.46715328467155 | 656.0044598213651 | 6.248175182481753 | 3.0 | 6.423357664233578 | 128.46715328467155 |
| 76-100% | Q2 | low | 226 | 124.15540050869087 | 144.59918790765045 | 5.242785705656225 | 7.5 | 1.499321983916074 | 124.15540050869087 |

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
- Stable playbook table: `playbook_table_stable.csv`
- Figures: `figures/`
