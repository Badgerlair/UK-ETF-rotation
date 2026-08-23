# UKACTIVE-A3R2Q query guide

Latest frozen weekly market-data observation: **2026-08-21**. Historical dates resolve to the final frozen weekly XLON session on or before the requested date. This is explicit in `as_of_date`; no future family or current ii metadata is exposed to a historical query.

```powershell
python code\query_ukactive_rotation.py --asof latest --pool geography --top 20
python code\query_ukactive_rotation.py --asof latest --pool theme --top 20
python code\query_ukactive_rotation.py --asof 2026-08-21 --family JAPAN
python code\query_ukactive_rotation.py --asof latest --pool industry --show-regime
python code\query_ukactive_rotation.py --asof latest --pool theme --sort-by 3_6_12_composite --format json
python code\refresh_ukactive_current_snapshot.py --asof latest
```

The refresh command preserves a date-versioned snapshot under `snapshots/` and refuses to rewrite that date with different bytes. Current alias files are refreshed only from the requested frozen data cutoff. Ranks are research intelligence, not deployment instructions. Historical UK retail/account/broker eligibility remains unresolved.

## A4B lifecycle overlay

The query also displays FAST_RS, SLOW_RS, frozen leadership and incumbent/challenger state, the A4B regime score/state, target risky/cash allocation, incumbent MFE/give-back and profit-lock state. These fields are display-only. A4B found no qualifying lifecycle/regime candidate, so the overlay reports `BASELINE_REFERENCE_ONLY_NO_LIFECYCLE_CANDIDATE` and cannot alter historical research decisions.

## A4C early-rotation and risk overlay

The A4C display-only overlay adds FAST/SLOW ordinal ranks, the FAST-minus-SLOW gap, one- and four-week FAST-rank changes, the frozen crossover state and persistence count, historically estimated eight-week migration probabilities, absolute 21/50-EMA state, trailing 63-session realised volatility, and the implied unlevered 10%/12.5%/15% risk weights.

For the latest snapshot only, it also identifies the promoted E2 research construction (`CORE_ACTIVE_50`) and its 50% active / 50% global-developed-core / 0% cash strategic allocation. Historical as-of queries deliberately return these post-hoc A4C allocation fields as not applicable; they do not rewrite any historical decision. This is a research display, not an allocation instruction or deployment claim.
