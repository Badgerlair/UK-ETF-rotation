# UKACTIVE-A0A1 — Next-Stage Design

> CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY

Stage outcome: `UKACTIVE_A0A1_PASS_WITH_OPEN_ITEMS`. Ready to recommend A2: `YES`.

## Recommended next stage (do not execute automatically)

`UKACTIVE-A2 — POINT-IN-TIME UNIVERSE AND TOTAL-RETURN DATA CONSTRUCTION`

A2 should:

1. Reconstruct, by date, fund/share-class/listing existence and eligible UK retail implementations, including closures, mergers, ticker/venue changes, KID/KIID availability and account restrictions.
2. Build identity-resolved daily histories at listing and share-class level, with explicit GBP/GBX normalization.
3. Validate cash distributions, splits, corporate actions, NAVs, adjusted closes and benchmark total-return indices.
4. Convert every candidate into GBP total return using documented FX close/timestamp conventions; keep hedged and unhedged economics separate.
5. Measure history length, stale observations, spreads/volume where available, missingness, and survivorship coverage.
6. Create point-in-time implementation sets underneath each economic family so implementation count cannot influence the future signal.
7. Re-run the A0A1 identity and duplicate tests on every historical snapshot.

A2 must fail if it silently projects the current 2026-08-22 survivor universe backward, cannot reconcile distributions, or confuses GBP with GBX.

## Only after A2 passes

Recommend `UKACTIVE-A3 — SIMPLE SIGNAL DISCOVERY`. A3 should begin with simple, economically defensible hypotheses for persistent leadership across geography, conventional sector/industry, coherent themes and defensive assets. It must not import the legacy ETF-rotation formula, and it must rank one economic family once before choosing an eligible implementation.

No A2 or A3 work has been executed by this run.
