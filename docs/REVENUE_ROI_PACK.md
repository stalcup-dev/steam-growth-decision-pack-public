# Revenue ROI Pack (Client Upgrade)

This pack turns engagement lift into revenue ROI by combining Steamworks sales data with your promo calendar. The goal is a decision-ready view of net impact by discount depth, region, and discount frequency.

## Inputs (required exports)
Provide daily files with `app_id` and `date` in every file.

| Dataset | Required fields | Notes |
| --- | --- | --- |
| Sales/Units | `app_id`, `date`, `units_sold` | Daily units by app. Region/currency split preferred. |
| Revenue (gross + net) | `app_id`, `date`, `gross_revenue`, `net_revenue` | Net should reflect taxes/fees. Include `currency` if available. |
| Refunds/Chargebacks | `app_id`, `date`, `refund_units`, `refund_amount` | Net ROI needs refund adjustment. |
| Prices/Discounts | `app_id`, `date`, `list_price`, `final_price`, `discount_pct` | Daily price/discount history. |
| App metadata | `app_id`, `release_date`, `app_name` | Used for lifecycle segmentation. |

### Optional (strongly recommended)
- Region/currency breakdown: add `region`, `currency` columns to sales/revenue.
- Marketing calendar: `campaign_name`, `start_date`, `end_date`, `channel`, `spend`, `notes`.

## Timezone guidance
- Preferred: **UTC** dates for all exports.
- If exports are in **Pacific Time (PT)**, tell us explicitly and include a timezone note in the file name or header.
- If you can, include a `timezone` column or provide the offset rules (DST).

## Required granularity
- Minimum: **daily** by `app_id`.
- Preferred: daily by `app_id` **and** `region`/`currency`.
- If you cannot deliver daily, provide the finest available and state the aggregation rules.

## Outputs you receive
- ROI table by discount depth, discount frequency, and popularity segment.
- Promo plan recommendations (discount depth + discount frequency combos).
- Net impact estimate with sensitivity bands (best/likely/worst).

## Delivery format
- CSV or Parquet, UTF-8.
- Zip the drop and include a short `README.txt` with date range and timezone.


