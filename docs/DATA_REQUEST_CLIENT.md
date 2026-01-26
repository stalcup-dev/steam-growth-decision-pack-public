[Request a Decision Pack (2 minutes)](https://docs.google.com/forms/d/e/1FAIpQLSfHMP8RZxLca6Tv56k1vsuSPZeAESdGoMzrz-VKMipNI1SO1g/viewform) (if you haven't requested the pack yet).

# Client Data Request (Minimum vs Gold Standard)

This checklist defines the minimum viable drop and the gold-standard drop needed to compute revenue ROI. Daily data with `app_id` is required.

## Minimum viable data drop
Send the following daily exports:
- Sales/Units: `app_id`, `date`, `units_sold`
- Revenue: `app_id`, `date`, `gross_revenue`, `net_revenue`
- Refunds: `app_id`, `date`, `refund_units`, `refund_amount`
- Prices/Discounts: `app_id`, `date`, `list_price`, `final_price`, `discount_pct`
- App metadata: `app_id`, `app_name`, `release_date`

## Gold standard drop (preferred)
Everything in minimum drop, plus:
- Region/currency splits: add `region`, `currency` to sales/revenue/refunds
- Marketing calendar: `campaign_name`, `start_date`, `end_date`, `channel`, `spend`, `notes`
- Store event tags or feature flags (if applicable)
- Wishlists and conversions (if available)

## Sample export instructions & file naming
Please export as CSV/Parquet with UTF-8 encoding and include the date range in the filename.

Suggested filenames:
- `steamworks_sales_daily_YYYYMMDD_YYYYMMDD.csv`
- `steamworks_revenue_daily_YYYYMMDD_YYYYMMDD.csv`
- `steamworks_refunds_daily_YYYYMMDD_YYYYMMDD.csv`
- `steamworks_prices_daily_YYYYMMDD_YYYYMMDD.csv`
- `steamworks_app_metadata.csv`
- `marketing_calendar_YYYYMMDD_YYYYMMDD.csv` (optional)

## Required fields by file
Sales (units):
- `app_id`, `date`, `units_sold`

Revenue:
- `app_id`, `date`, `gross_revenue`, `net_revenue`

Refunds:
- `app_id`, `date`, `refund_units`, `refund_amount`

Prices/Discounts:
- `app_id`, `date`, `list_price`, `final_price`, `discount_pct`

App metadata:
- `app_id`, `app_name`, `release_date`

Marketing calendar (optional):
- `campaign_name`, `start_date`, `end_date`, `channel`, `spend`, `notes`

## Timezone + aggregation checklist
- Timezone used in exports: [UTC/PT/Other]
- If not UTC, confirm DST handling.
- Daily aggregation rules: [describe]
- Currency basis: [currency code(s)]

## Delivery
- Zip all files and include a short `README.txt` with date range and timezone.

