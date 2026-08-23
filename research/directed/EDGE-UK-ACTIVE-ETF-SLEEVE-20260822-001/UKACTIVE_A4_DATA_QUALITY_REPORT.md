# UKACTIVE-A4 data-quality report

Generated: 2026-08-23T09:12:53+00:00

## Result

No new price, return, calendar, lineage, stale-data or lookahead defect was found. A4 consumes the A2R2 corrected XLON endpoint/wealth chain; no price or return was forward-filled. Contribution reconciliation difference is exactly 0.0. The frozen primary contract and regime-history hash passed.

## Controls

- Date-T close never earns date-T return; executable decisions use the next valid XLON session.
- Dynamic point-in-time membership and one-row-per-economic-family ranking remain intact.
- TOP_2/TOP_3 use the same frozen rank sequence.
- Random/permutation paths retain contemporaneous membership; invalid endpoints invalidate a path rather than manufacture a return.
- Exact episode-time listing/share-class IDs are reconstructed from A2R2 endpoint history. FCBR is retained for the 2021 cybersecurity episode rather than current CYSE.
- Current ii observations remain dated 2026-08-23 and never become historical evidence.
- The A5 runner rejects dates at or before 2026-08-21 and contains no broker/order/scheduler route.

## Remaining limitations

- The recent five-year lifecycle census is `RECENT_FIVE_YEAR_CENSUS_SUBSTANTIALLY_COMPLETE`, not complete.
- 4538 placebo and 4513 permutation paths were invalid under strict endpoint continuity. Percentiles are conditional on valid paths.
- Historical retail documentation is verified for only 1 of 21 episodes; the rest are probable. Historical ISA evidence is probable, not verified, for all 21.
- Historical broker/platform availability is unverified.
- Only 2/27 pool families have current user-confirmed ii status; 19 of 25 currently signal-eligible families have incomplete public/ii implementation evidence and 5 more remain ii-unchecked.
- NEXT_OPEN and realised historical spreads are unavailable; only the validated endpoint convention and explicit cost sensitivities are reported.
