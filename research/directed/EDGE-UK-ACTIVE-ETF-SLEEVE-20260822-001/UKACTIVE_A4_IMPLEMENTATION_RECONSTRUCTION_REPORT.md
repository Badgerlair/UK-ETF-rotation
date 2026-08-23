# UKACTIVE-A4 implementation reconstruction

Generated: 2026-08-23T09:00:01+00:00

## Scope and result

The reconstruction covers all 22 families selected by A4_PRIMARY, TOP_2, TOP_3 and the two frozen neighbours during the contemporary window. It uses the exact A2R2 share-class/listing IDs at each execution date. It does not substitute the current preferred line retrospectively.

The primary model has 60 executed monthly decisions, which form 21 holding episodes across 10 distinct executed families. Historical UK-retail episode states are {"HISTORICALLY_PROBABLE_UK_RETAIL": 20, "HISTORICALLY_VERIFIED_UK_RETAIL": 1}. Historical ISA episode states are {"HISTORICALLY_PROBABLE_ISA_ELIGIBLE": 21}. Account/platform history remains HISTORICALLY_UNCERTAIN throughout.

## Current implementability

The frozen industry-plus-theme pool contains 27 families, of which 25 have a current 3/6/12 score. User-confirmed current ii coverage is 2/27 families (EBIG; SEAL). Among currently signal-eligible families, 1 are ii-confirmed, 5 have complete public rules/disclosure support but remain ii-unchecked, and 19 remain unresolved.

This is not sufficient for deployment. It does not prevent an economic-signal shadow test, provided any unconfirmed selection is recorded as non-executable rather than silently substituted or reranked.

## Execution and costs

The only reported execution result uses the frozen next-eligible-session endpoint contract. NEXT_OPEN is not reported because the raw open field has not passed an execution-price validation chain. No current spread is represented as a historical realised spread. The 10/20/40 bp and £100k/£250k/£500k tables are sensitivities; the £3.99 charge and 0.75% non-GBP FX assumption are sourced from the current ii tariff and are not claims about historical charges.

## Evidence boundary

An exact instrument’s validated price lineage proves neither historical retail-document availability nor ISA/platform eligibility. A dated exact-ISIN KIID supports one verified retail episode route (URNP after the document date); the remaining exact primary routes are classified probable rather than verified. ISA classifications are probable where exact UCITS structure plus recognised-exchange admission and HMRC rules align, but no account-specific history was found. Current ii observations remain dated 2026-08-23 only.
