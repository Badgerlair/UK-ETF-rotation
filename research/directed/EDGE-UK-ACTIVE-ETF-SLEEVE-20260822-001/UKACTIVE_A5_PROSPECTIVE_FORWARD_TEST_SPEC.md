# UKACTIVE-A5 prospective shadow forward test specification

Status: **FROZEN_NOT_STARTED**  
Evidence target: **E3 — prospective confirmation**  
Historical development cutoff: **2026-08-21**

## Frozen model

The shadow model is `INDUSTRY_PLUS_THEME | MH_LEVEL_3_6_12_REFERENCE | TOP_1 | MONTHLY`. The score is the equal average of contemporaneous percentile ranks for 63-, 126- and 252-session global-relative strength. The ranking unit is `economic_exposure_family_id`; ties use ascending family ID. The signal forms after the final valid XLON session close of each calendar month. Execution is first valid close on or after the next XLON session, within the frozen three-session tolerance. Same-close execution is prohibited.

The benchmark is `GLOBAL_DEVELOPED_WORLD`. The equal-weight comparator is the contemporaneously eligible industry-plus-theme pool. The canonical friction is 20 bp one way plus £3.99 per actual trade leg at a £250,000 sleeve; 10/20/40 bp and £100k/£250k/£500k remain reporting sensitivities. A non-GBP preferred line incurs the frozen 0.75% FX assumption.

## Prospective boundary

The specification is frozen by tag `ukactive-a5-frozen-candidate-v1-20260823`. The first permissible signal is the first final valid XLON month-end session after the tag exists and after the 2026-08-21 historical cutoff; the precomputed earliest possible date is 2026-08-28. No historical date may be recorded as A5. No A5 result has been generated in A4.

## Implementation rule

Economic TOP_1 is determined before implementation checks. The runner then checks the versioned current implementation table:

- `CURRENT_II_CONFIRMED` → `SHADOW_EXECUTABLE_CURRENT_II_CONFIRMED`;
- public UK eligibility with ii unchecked → `SHADOW_NOT_EXECUTABLE_II_UNCHECKED`;
- unresolved current implementation → `SHADOW_NOT_EXECUTABLE_IMPLEMENTATION_UNRESOLVED`.

An unconfirmed winner is not replaced by rank 2 and the pool is not reranked. The shadow ledger therefore tests the economic signal without disguising an implementation failure.

## Governance

This runner places no orders, queries no broker, and creates no scheduler. Any change to the universe policy, score, horizons, weights, pool, cadence, TOP_1 rule, timing, cost model, implementation rule, or benchmark terminates this confirmation lineage and requires a new version. Regime fields are recorded but never used as filters in v1.

The primary review occurs only after 24 completed monthly decisions. Interim monitoring is limited to data and execution integrity; it cannot promote an efficacy claim or trigger a performance-based early stop. The primary effect is net frozen-candidate return minus the contemporaneous equal-weight pool. Net excess versus global developed equities, selected-versus-unselected return, rank-1 future-tail frequency, drawdown and turnover are secondary. Data/timing defects or any frozen-policy change terminate the v1 lineage.

The executable configuration is `config/ukactive_a5_frozen_candidate.json`; the ledger contract is documented in `UKACTIVE_A5_DECISION_LEDGER_SCHEMA.md`.
