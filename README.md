# Steam Discount Decision Pack (Public Preview)

Public artifacts for a Steam discount decision pack that turns historical sale patterns into a usable 90-day plan.

## What this is
I help Steam devs pick **discount timing + depth + cadence** using lift/decay patterns from historical sale episodes.

You get a **Decision Pack** (one-pager + memo + proof charts + playbook table) plus a **90-day plan** you can execute.

**This public preview uses engagement signals only** (playercount + price history). **ROI/profit conclusions require Steamworks exports.**

### Preview the deliverable
- 👉 [Client Preview One-Pager](./client_preview_onepager.md)
- 👉 [Decision Memo](./decision_memo.md)
- 👉 [Public Playbook Table (Top 30)](./playbook_table_public.csv)
- 👉 [Client Data Request Checklist](./docs/DATA_REQUEST_CLIENT.md)
- 👉 [FAQ](./FAQ.md)
- 👉 [Public vs Private](./PUBLIC_VS_PRIVATE.md)
- 👉 [Service Offer](./SERVICE_OFFER_PUBLIC.md)

**Want this for your game?** Open an issue or message me with your Steam `app_id`.

## What's inside
- `client_preview_onepager.md` (preview deliverable)
- `decision_memo.md` (decision memo)
- `playbook_table_public.csv` (top 30 segments)
- `reports/figures/` (lift/decay charts)
- `docs/DATA_REQUEST_CLIENT.md` (client data checklist)
- `docs/REVENUE_ROI_PACK.md` (ROI upgrade details)
- `FAQ.md` (common questions)

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

## Publish safety (pre-push guard)
After cloning, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_hooks.ps1
```

Verify:

```powershell
powershell -ExecutionPolicy Bypass -File .\publish_audit.ps1
```

This repo is allowlist-protected and blocks accidental commits of private engine/data.

---

# ✅ CI PASS Check (what to do right now)
CA is correct: we need to confirm the workflow is green **once** before the final release commit.

### Option A: GitHub UI
GitHub → **Actions** tab → **publish-audit** → confirm latest run on `main` is ✅ green

### Option B: CLI (if you have gh installed)
```bash
gh run list --workflow publish-audit.yml -L 3
```

✅ Final Ticket (after CI is green)
TCK-SGB-012 — Final release commit

Commit message:
release: public decision pack v1

This should be a no-change commit only if needed, otherwise bundle it with the README cleanup if you want fewer commits.
