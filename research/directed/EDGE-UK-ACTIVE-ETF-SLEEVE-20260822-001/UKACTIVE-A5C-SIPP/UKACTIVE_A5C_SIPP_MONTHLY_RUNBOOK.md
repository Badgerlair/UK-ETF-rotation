# UKACTIVE-A5C-SIPP monthly runbook

## Before month-end

1. Confirm the frozen code/config hashes and append-only ledger integrity.
2. Confirm the authoritative point-in-time 27-family universe; do not force non-warmed families into the signal.
3. Confirm preferred GBP/GBX lines and only frozen GBP/GBX alternates in the SIPP.
4. Confirm total existing active/thematic exposure will remain at or below 25%.

## Official signal run

Run only after the final valid XLON month-end close is fully ingested and validated, and before the first eligible following XLON session closes. The first possible A5C signal is expected on 2026-08-28, strictly after freeze commit `a8008f7709af3000a889bb234a86f8c520c4ed73`.

1. Validate prices, total returns, GBP cash, XLON calendar, universe and hashes.
2. Calculate RS21/42/63/126/252 using only information through the signal close.
3. Form M2_BASE with weights 10/15/25/30/20.
4. Rank eligible `INDUSTRY_PLUS_THEME` economic families with duplicate suppression.
5. Select TOP7 and assign 1/7 of the M2 sleeve to each.
6. Resolve preferred GBP/GBX implementation; use only a frozen GBP alternate. Put an unavailable slot in CSH2.
7. Append the immutable decision before the execution-session close is known. Regime fields are telemetry only.

## Manual execution pack

1. Resolve the first valid following XLON session within three valid sessions.
2. Reconcile current holdings and active/thematic cap.
3. Prepare a review-only trade list at 65% SWDA / 10% M2 / 25% defensive.
4. Use 20 bp one-way expected friction and the selected ii plan's current-month credits/fee schedule.
5. If quoted one-way friction exceeds 40 bp, suspend that change and hold the slot in CSH2.
6. User approval is mandatory. No code in A5C may transmit an order.

## Suspensions

- Data/hash/calendar/universe failure: create no decision, do not backfill, retain affected capital in CSH2.
- Rank reproducibility failure: suspend M2 and retain the sleeve in CSH2.
- Preferred and frozen GBP alternate unavailable: put only that slot in CSH2.
- Execution not possible within three valid sessions: do not chase; use CSH2.
- Quoted/actual one-way friction above 40 bp: suspend the instrument change and review implementation.
