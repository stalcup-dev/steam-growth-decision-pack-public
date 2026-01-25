# Steam Promo ROI Decision Pack

Notebook-first pipeline that turns Steam discount histories into a decision pack: Public v1 shows engagement lift, and the Client upgrade adds revenue inputs to quantify net ROI.
Use this repo to validate lift patterns now, then plug in Steamworks/partner data to move from "what happened" to "what it earned."

## Quick start
1) Place the Mendeley dataset under `data/raw/mendeley/` (any file names; the pipeline scans recursively).
2) Create a virtualenv and install deps:

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
```

3) Run notebooks in order:
- `notebooks/00_data_profile.ipynb`
- `notebooks/01_build_daily_panel.ipynb`
- `notebooks/02_detect_sales.ipynb`
- `notebooks/03_event_study.ipynb`
- `notebooks/04_playbook_tables.ipynb`

## Public v1 (Engagement Lift Pack)
What it does:
- Builds an event window, lift curves, and a playbook of discount segments using public playercount + price history.

Limitations:
- No revenue, refunds, wishlists, or region/channel mix, so you cannot compute net ROI or margin impact.
- Lift is an engagement proxy only.

## Client Upgrade (Revenue ROI Pack)
What it unlocks with Steamworks/partner data:
- Net revenue ROI by discount tier, region, and lifecycle stage.
- Incremental gross margin, refund risk, and long-term retention value.

## Signals map (Public vs Client)
| Signal | Public dataset (Mendeley) | Client data (Steamworks/partner) |
| --- | --- | --- |
| Playercount time series | Yes | Yes |
| Discount + list price history | Yes | Yes |
| Units sold | No | Yes |
| Net revenue + taxes/fees | No | Yes |
| Refunds/chargebacks | No | Yes |
| Wishlists + conversions | No | Yes |
| Regional/channel mix | No | Yes |

## Next steps
- Data request: `docs/DATA_REQUEST_CLIENT.md`
- Decision memo: `reports/decision_memo.md`
- Public playbook table: `reports/playbook_table_public.csv`

## Publish gate
Before publishing: run `scripts/publish_audit.ps1`.


## Outputs
- `data/processed/panel_daily.parquet`
- `data/processed/sales.parquet`
- `data/processed/event_window.parquet`
- `reports/reports/figures/` (PNG charts)
- `reports/playbook_table_public.csv`
- `reports/decision_memo.md` (template)

## Notes
- The pipeline infers column mappings and logs them in the data profile report.
- Discount values are standardized to 0?100 percent.
- Sales detection requires price/discount data. If price data is missing, sale detection fails with a clear error.
Implementation code is maintained privately; this repo is the client-preview decision pack.

## Tests
Run unit tests with:

```bash
pytest -q
```
