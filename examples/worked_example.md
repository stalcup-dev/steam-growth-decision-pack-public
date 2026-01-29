# Worked Example (Synthetic Indie Case — Public Preview)

This is a realistic but synthetic case study. No proprietary or real game data is used.

## Situation
- **Stage:** Live (post-launch), steady baseline
- **Genre/shape:** Single-player indie (1–2h sessions), update-driven spikes
- **Current price:** $14.99 USD
- **Wishlist range:** ~8k–15k total wishlists (Steamworks-reported; not public)
- **Upcoming beat date:** Planned “major update” (exact date in paid pack)
- **Constraints / cooldowns (assumed):**
  - A discount ran recently, so the next promo must wait for Steam cooldown eligibility (confirm exact dates in Steamworks).
  - Avoid stacking a discount too close to the update if you want clean measurement of update vs discount lift.
  - Keep a minimum cooldown between promos to avoid training “wait for sale” behavior.

## Decision (Public Preview — redacted)
**Goal:** Convert wishlists and re-activate lapsed interest without damaging price integrity.

- **Recommended discount band:** **Moderate tier (exact band in paid pack)**
- **Timing window:** **Ahead of the beat**, after cooldown eligibility (exact window in paid pack).
- **Duration guidance:** **Short window** sized to capture a weekend + 1–2 weekdays (exact duration in paid pack).

## Schedule (90-day promo calendar starter — redacted)
Use this as a starter calendar; adjust once you confirm cooldown eligibility and your build readiness.

| Window (relative) | Action | Offer | Primary goal | What to measure |
| --- | --- | --- | --- | --- |
| Week 0–1 | No discount; prep update | None | Build demand | Wishlist adds, follower adds, review velocity |
| Week 2 | Promo window | Moderate tier (exact band in paid pack) | Convert wishlists | Store traffic, conversion rate (Steamworks), units |
| Week 3 | Cooldown / measurement | None | Isolate effect | Baseline playercount, refund rate (Steamworks), review delta |
| Week 4 | Beat: major update | None | Reactivation | DAU/CCU, review velocity, wishlist adds |
| Week 5–8 | Follow-through + checkpoint | Light tier (optional) | Sustain interest | Retention proxy (playtime), store page CTR, wishlist-to-purchase lag |

## Expected outcome (directional, not guaranteed)
**What you should expect (hypothesis):**
- A **meaningful conversion bump** during the promo window (relative to your baseline), without needing a deep discount.
- Less “hangover” (post-sale drop-off) than a deeper discount, because you haven’t reset reference price as aggressively.
- Cleaner attribution: discount window lift vs update lift, because they’re not fully stacked.

**Metrics to watch**
- **Without Steamworks exports (public proxies):** playercount trend, review velocity, price/discount history, follower deltas (where available).
- **With Steamworks exports:** wishlists (adds + conversions), units, net revenue, refund-adjusted impact, regional split, channel mix.

## Risks + mitigations
- **Risk: Under-discounting (offer feels “meh”).**  
  Mitigation: tighten timing (closer to peak interest) and use a pre-defined trigger for deepening the offer.

- **Risk: Over-discounting (training wait-for-sale).**  
  Mitigation: cap depth, space promos, and use the update as a non-discount conversion beat.

- **Risk: Cooldown eligibility mismatch.**  
  Mitigation: confirm eligibility dates in Steamworks first; if blocked, shift the promo earlier and keep the update clean.

- **Risk: Misreading Day 1 spike as success.**  
  Mitigation: evaluate over 14–30 days; watch post-window decay and baseline shift, not just launch-day lift.

## Data used (public vs Steamworks-required)
**Public signals (usable without exports):**
- Price + discount history (timing, depth, frequency)
- Engagement proxy (playercount trend where available)
- Review velocity and rating movement

**Steamworks exports required (to size net impact):**
- Units sold and net revenue (incl. taxes/fees)
- Refunds/chargebacks
- Wishlists (adds + conversions) and store traffic funnel
- Region/currency/channel mix
