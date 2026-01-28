# Worked Example (Synthetic Indie Case)

This is a realistic but synthetic case study. No proprietary or real game data is used.

## Situation
- **Stage:** Live (post-launch), steady baseline
- **Genre/shape:** Single-player indie (1–2h sessions), update-driven spikes
- **Current price:** $14.99 USD
- **Wishlist range:** ~8k–15k total wishlists (Steamworks-reported; not public)
- **Upcoming beat date:** 2026-03-12 (planned “major update”)
- **Constraints / cooldowns (assumed):**
  - A discount ran recently, so another promo must wait for Steam discount cooldown eligibility (confirm exact dates in Steamworks).
  - Avoid stacking a discount too close to the update if you want clean measurement of update vs discount lift.
  - Keep a minimum cooldown between promos to avoid training “wait for sale” behavior.

## Decision
**Goal:** Convert wishlists and re-activate lapsed interest without damaging price integrity.

- **Recommended discount band:** **20–30%**
- **Timing window:** **7–14 days before the beat date**, assuming cooldown eligibility (so players who notice the update can still convert during/after).
- **Duration guidance:** **5–7 days**
  - Long enough to capture weekend traffic + a couple weekdays.
  - Short enough to limit post-sale decay and protect future pricing flexibility.

## Schedule (90-day promo calendar starter)
Use this as a starter calendar; adjust once you confirm cooldown eligibility and your build readiness.

| Window (date range) | Action | Offer | Primary goal | What to measure |
| --- | --- | --- | --- | --- |
| 2026-02-10 → 2026-02-23 | No discount; prep update | None | Build demand | Wishlist adds, follower adds, review velocity |
| 2026-02-24 → 2026-03-02 | Promo window | 20–30% for 5–7 days | Convert wishlists | Store traffic, conversion rate (Steamworks), units |
| 2026-03-03 → 2026-03-11 | Cooldown / measurement | None | Isolate effect | Baseline playercount, refund rate (Steamworks), review delta |
| 2026-03-12 → 2026-03-18 | Beat: major update | No discount (preferred) | Reactivation | DAU/CCU, review velocity, wishlist adds |
| 2026-03-19 → 2026-04-02 | Follow-through | None | Sustain interest | Retention proxy (playtime), store page CTR, wishlist-to-purchase lag |
| 2026-04-03 → 2026-04-15 | Decision checkpoint | Decide next promo | Avoid randoming | Compare post-window decay vs expectations |
| 2026-04-16 → 2026-05-10 | Optional second window | Small (10–20%) or none | Keep price clean | Same metrics; watch frequency creep |

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
  Mitigation: tighten timing (closer to peak interest) and keep duration short; only deepen discount if prior windows show weak conversion at 20–30%.

- **Risk: Over-discounting (training wait-for-sale).**  
  Mitigation: cap depth (start 20–30%), space promos, and use the update as a non-discount conversion beat.

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
