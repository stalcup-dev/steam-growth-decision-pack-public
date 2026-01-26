# Repo State (Phase 0)

## Current structure (tracked)

Root:
- README.md
- client_preview_onepager.md
- decision_memo.md
- playbook_table_public.csv
- PUBLIC_VS_PRIVATE.md
- SERVICE_OFFER_PUBLIC.md
- publish_audit.ps1
- setup_hooks.ps1
- .gitignore

Docs:
- docs/DATA_REQUEST_CLIENT.md
- docs/FAQ.md
- docs/REVENUE_ROI_PACK.md

Reports:
- reports/figures/decay_by_discount_tier.png
- reports/figures/lift_curve_by_discount_tier.png
- reports/figures/lift_curve_overall.png
- reports/figures/lift_curve_seasonal_vs_nonseasonal.png
- reports/figures/lift_vs_discount_scatter.png

Scripts:
- scripts/publish_audit.ps1
- scripts/setup_hooks.ps1

## Safety gate status
- publish_audit.ps1 wrapper present
- scripts/publish_audit.ps1 allowlist present
- setup_hooks.ps1 wrapper present
- .git/hooks/pre-push present
- Audit result: PASS (allowlist)

Allowlist paths:
- README.md
- client_preview_onepager.md
- decision_memo.md
- playbook_table_public.csv
- PUBLIC_VS_PRIVATE.md
- SERVICE_OFFER_PUBLIC.md
- docs/DATA_REQUEST_CLIENT.md
- docs/REVENUE_ROI_PACK.md
- docs/FAQ.md
- publish_audit.ps1
- scripts/publish_audit.ps1
- setup_hooks.ps1
- scripts/setup_hooks.ps1
- .gitignore
- LICENSE
- reports/figures/*.png

## Missing target artifacts
- None detected (all requested artifacts present)

## Risky files present in working tree (not tracked)
- data/ (raw + processed)
- data/processed/*.parquet
- data/raw/*.zip
- .venv/
- src/
- tests/
- __pycache__ under src/ and tests/

Notes:
- No notebooks/ directory detected in this working tree.
