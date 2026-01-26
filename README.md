# Steam Promo Decision Pack

Public artifacts for a Steam discount decision pack that turns sale history into a usable 90-day plan.

## What this is

I help Steam devs pick **discount timing + depth + cadence** using lift/decay patterns from historical sale episodes.
You get a **Decision Pack** (one-pager + memo + charts + playbook table) plus a **90-day discount plan** you can execute.
This public preview uses engagement signals only; ROI/profit conclusions require Steamworks exports.

**Preview the deliverable:**
- 👉 [Client Preview One-Pager](./client_preview_onepager.md)
- 👉 [Decision Memo](./decision_memo.md)
- 👉 [Public Playbook Table (Top 30)](./playbook_table_public.csv)
- 👉 [Client Data Request Checklist](./docs/DATA_REQUEST_CLIENT.md)
- 👉 [FAQ](./FAQ.md)
- 👉 [Public vs Private](./PUBLIC_VS_PRIVATE.md)
- 👉 [Service Offer](./SERVICE_OFFER_PUBLIC.md)

**Want this for your game?** Open an issue or message me with your Steam app_id and I'll share the upgrade options.

## What's inside
- `client_preview_onepager.md` (preview deliverable)
- `decision_memo.md` (decision memo)
- `playbook_table_public.csv` (top 30 segments)
- `reports/figures/` (lift/decay charts)
- `docs/DATA_REQUEST_CLIENT.md` (client data checklist)
- `docs/REVENUE_ROI_PACK.md` (ROI upgrade details)
- `FAQ.md` (common questions)
## Public vs Private

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
- Decision memo: `decision_memo.md`
- Public playbook table: `playbook_table_public.csv`

## Publish safety (pre-push guard)

Run once after cloning:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_hooks.ps1
```

This installs a pre-push hook that runs `publish_audit.ps1` and blocks pushes if non-public files are staged. To verify anytime:

```powershell
powershell -ExecutionPolicy Bypass -File .\publish_audit.ps1
```

