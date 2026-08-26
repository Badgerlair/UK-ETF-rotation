# UKACTIVE-A5C-SIPP freeze declaration

Stage: **UKACTIVE-A5C-SIPP — Frozen M2 Specification, Implementation Amendment, 10% Pilot Readiness and Prospective Launch**  
Evidence grade: **E2_DEVELOPMENTAL**  
Historical evidence cutoff: **2026-08-21**  
Branch: `research/ukactive-a5c-sipp-frozen-prospective`

## Scientific boundary

This stage freezes and operationalises the already-developed M2 model. It is not a historical model search and does not claim independently confirmed alpha. No observation after 2026-08-21 may alter the signal, breadth, cadence, weights, cash rule, universe, execution timing, or allocation size.

`M2_HISTORICAL_MODEL_DEVELOPMENT_CLOSED`

The pre-existing A5 shadow comparison remains immutable and unstarted. A5C uses a separate append-only lineage: `UKACTIVE-A5C-M2-FROZEN-PROSPECTIVE`.

## Frozen active model

- Universe: accepted point-in-time 27-family `INDUSTRY_PLUS_THEME` research universe, with existing economic-family duplicate suppression.
- Signal: `M2_BASE`.
- Composite: RS21 10%; RS42 15%; RS63 25%; RS126 30%; RS252 20%.
- Selection: TOP7 economic-exposure families.
- Weighting: equal weight, exactly 1/7 of the M2 sleeve per available selected family.
- Cash rule: `CASH0_ALWAYS_INVESTED`; cash arises only from a data, implementation, execution, or cost suspension.
- Review: final valid XLON session of each calendar month.
- Execution: first valid following XLON session, within three valid XLON sessions.
- No same-close execution, leverage, shorting, inverse instruments, discretionary substitution, or automatic broker execution.
- Regime fields are telemetry only and cannot alter allocation.

## Frozen whole-SIPP pilot target

- 65% SWDA/global developed equity core.
- 10% frozen M2 TOP7 sleeve.
- 25% defensive sleeve.
- Each selected M2 family targets 1.428571% of the whole SIPP.
- Total active/thematic exposure, including legacy and discretionary tilts, may not exceed 25%.
- A5C authorises no live M2 allocation above 10%.

## Frozen cost assumptions

- Market-price execution.
- 20 basis points one-way implementation friction.
- II Plus: £3.99 per paid ETF leg, one monthly trade credit, £14.99 monthly subscription.
- II Premium: £2.99 per paid ETF leg, two monthly trade credits, £39.99 monthly subscription.
- Monthly credits do not carry forward.
- Broker FX fee is zero for preferred GBP/GBX lines.
- TER and live-ETF tracking economics are not deducted twice.
- Subscription, plan-incremental cost, and M2-attributable cost are reported separately.

## Prospective integrity

The first official A5C decision must be strictly after the commit containing this freeze and at the next eligible month-end. No decision may be backfilled. A prospective record is valid only when written before its first eligible execution-session close is known. No broker instruction may be generated or transmitted.

## Current implementation amendment

- SWDA (`IE00B4L5Y983`) remains the preferred core line.
- RLON is permitted for the strategic defensive sleeve only after its exact held share class, ISIN, and dealing terms are supplied and frozen; they must not be guessed.
- CSH2 (`LU1230136894`, LSE/XLON, GBP/GBX) is permitted for tactical liquidity and suspended M2 slots, subject to current SIPP availability confirmation.
- Direct broker cash is limited to settlement, fees, and residual balances.
- Historical GBP cash remains the accepted historical series and is not replaced by RLON or CSH2.

## Stop condition

This stage stops after freezing the specification, implementation map, cost comparison, holdings-input boundary, transition procedure, empty prospective ledger, and first-month-end operating procedure. It will not create a signal, execution, or order before the next valid post-freeze month-end and explicit user authority.
