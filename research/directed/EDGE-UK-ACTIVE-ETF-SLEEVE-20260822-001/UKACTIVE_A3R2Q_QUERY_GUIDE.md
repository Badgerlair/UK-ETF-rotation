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
