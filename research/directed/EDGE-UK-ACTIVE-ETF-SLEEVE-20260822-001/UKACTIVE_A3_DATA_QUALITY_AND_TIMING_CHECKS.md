# UKACTIVE A3 — Data Quality and Timing Checks

## Result

- Automated tests passed: 35/35.
- Critical failures: 0.
- Authorised families: 86.
- Valid A2 returns admitted: 260080.
- Proxy observations admitted: 0.
- Duplicate family/date ranking rows: 0.
- A2 next-session mapping mismatches: 0.

## Timing

Lookbacks end at date-T close. Forward returns compound date T+1 through T+h. The A2 `next_execution_eligible_date` mapping is preserved. Missing, stale, rejected, pre-inception and proxy observations are unavailable; none is filled.

## Identity and experimental controls

All matrices contain one column per economic exposure family. Implementation identifiers cannot enter ranks. CORE+EXTENDED results are computed on a tier-filtered matrix that is independent of EXPERIMENTAL values.

## Eligibility warning

**HISTORICAL ELIGIBILITY REMAINS UNRESOLVED.** A3 status is research-only and does not establish contemporaneous retail, ISA, SIPP or IBKR availability.

## Failed checks

None.
