# UKACTIVE-A3R0 — Scope and method

## Decision boundary

This stage validates and restructures the retained A0A1/A2 universe for later relative-strength rotation research. It does **not** run a strategy, calculate portfolio returns, optimise signals, choose holdings, or authorise A3R1.

All 99 original `economic_exposure_family_id` values are retained without deletion or renumbering. Ticker, ISIN, share class and listing remain implementation identities only.

## Dynamic admission

The fixed 504-session A3 gate is removed. Each 21/42/63/126/252-session model receives its own earliest admission date after that many valid A2 observations. Invalid, stale, missing and proxy rows never count. A3R1 must still validate the complete inputs on every actual signal date; admission is not permission to fill gaps. Current eligibility is never back-projected.

Raw A2 observation count alone is insufficient: 14 histories are blocked because their selected implementations do not match the economic family. The four histories below 504 observations were reconsidered; 3 pass short-horizon admission and `US_AEROSPACE_DEFENCE` is blocked because its A2 history is global rather than US-specific.

## Research architecture

`ECONOMIC EXPOSURE FAMILY → ROTATION ROLE → COMPETITION POOL → FUTURE SIGNAL → SELECTED ECONOMIC EXPOSURE → CURRENT IMPLEMENTATION`.

DeepVue remains descriptive metadata only. Defensive assets and benchmark references do not enter the primary equity tournament. Parent/child overlap is not duplicate equivalence.

## Current public evidence

The current public layer preserves three separate states: LSE status, retail-disclosure status, and public ISA-rules status. During the FCA CCI transition a product summary, KID, KIID or another permitted disclosure route can be valid; the filename `KID` is not required. ISA status is carried from A0A1 evidence and current HMRC structural rules, never inferred from LSE listing. All IBKR fields remain `NOT_CHECKED`.

## Scientific result

The structure is generated, but the stage decision is `UKACTIVE_A3R0_FAIL` because material A0A1/A2 economic-lineage defects prevent a clean full geography/sector/theme tournament. No A3R1 execution is authorised.

CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY
