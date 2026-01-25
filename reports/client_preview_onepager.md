# Steam Promo ROI Client Preview (One-Pager)

**What this is:** A decision-ready preview using public Steam data (engagement lift) with a clear path to net revenue ROI once Steamworks exports are provided.

## 1) Stable Top Segments (Public v1)
Source: `reports/playbook_table_stable.csv` (n_sales >= 20, non-null tier, lift capped for ranking).

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

## 2) Evidence (Charts)
Overall lift curve:

![Overall lift curve](figures/lift_curve_overall.png)

Lift curve by tier:

![Lift curve by tier](figures/lift_curve_by_discount_tier.png)

Seasonal vs non-seasonal lift:

![Seasonal vs non-seasonal lift](figures/lift_curve_seasonal_vs_nonseasonal.png)

Decay by tier:

![Decay by tier](figures/decay_by_discount_tier.png)

## 3) Actionable Recommendations (Guardrails)
1. **Prioritize mid-depth tiers (51-75%) for top-popularity titles**; these show the strongest median lift in the stable table.
2. **Avoid extreme depths as default**; reserve 76-100% for targeted clearance windows with explicit goals.
3. **Use Steam-aware mechanism tags**: track wishlist-notify eligible sales (>=20% discount heuristic) and seasonal overlap separately.
4. **Set cadence caps** (e.g., no more than one major discount per 60-90 days) to reduce saturation risk.
5. **Predefine success metrics**: lift duration, decay speed, and baseline recovery window before repeating a tier.

## 4) 90-Day Plan (Skeleton)
- **Days 0-15:** Validate data drop, align on KPI definitions, confirm timezone + app_id mapping.
- **Days 16-45:** Build revenue ROI tables by tier/region/cadence; deliver draft promo plan.
- **Days 46-75:** Run 1-2 controlled tier tests; monitor lift and decay; adjust thresholds.
- **Days 76-90:** Finalize ROI-backed playbook + decision memo.

## 5) What I Need From You
Provide the minimum or gold-standard data drop listed here:
- `../docs/DATA_REQUEST_CLIENT.md`

## Upgrade Path: Revenue ROI Pack
Public data shows engagement lift, but ROI requires net revenue exports. The upgrade pack delivers revenue-by-tier ROI, refund-adjusted impact, and region-specific promo guidance:
- `../docs/REVENUE_ROI_PACK.md`
