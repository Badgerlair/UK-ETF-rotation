# UKACTIVE-A4E-SIPP — preregistration

Stage: `UKACTIVE-A4E-SIPP`  
Run: `UKACTIVE-A4E-SIPP-20260824-001`  
Parent: immutable `UKACTIVE-A4D` commit `48cb69ffbaae25eb0dccc3226f47f5a7491e8bd7`, tag `ukactive-a4d-v1-20260824`  
Evidence ceiling: `E2_DEVELOPMENTAL`  
Authoritative cutoff: `2026-08-21`

## Objective and evidence boundary

A4E-SIPP selects the best available causal, executable whole-SIPP ruleset from a bounded family of rotation, cash, global-core and static global/cash architectures. It must deliver one operational strategy even if the active-rotation claim fails. It does not use observations after 2026-08-21 for any selection, robustness or gate calculation, and it cannot create E3 evidence.

Existing A1–A5 and A4D outputs are read-only. Economic-family identity, the 27-family structural `INDUSTRY_PLUS_THEME` pool, dynamic admission, A2R2 endpoint validity, deterministic XLON calendar, duplicate suppression, GBP total-return accounting, accepted GBP cash series, `GLOBAL_DEVELOPED_WORLD`, next-session execution and the A4D cost model remain frozen.

## Phase 0 — reproduction gate

The first empirical action must reproduce A4D M2 TOP6–TOP9 monthly CASH0/CASH1 results under baseline and doubled costs, including full history, pre-2020, post-2020, latest five years, latest three years, calendar years and contribution sensitivities. The audit reconciles CAGR-difference excess, arithmetic annualised excess, bootstrap excess, turnover windows, the 2017-02-03 common-chain boundary, the first executable monthly portfolio date, cash accrual, distributions, FX, missing observations and partial 2017/2026.

Material reproduction failure is defined as an unexplained absolute metric difference greater than `1e-10` for deterministic values or a changed family/rank sequence. Such failure stops the stage with `A4E_SIPP_AUDIT_FAIL`.

## Phase 1 — signal stability

Only the following frozen weights are tested at monthly review, next-session execution, equal weight and TOP6–TOP9:

| Signal | RS21 | RS42 | RS63 | RS126 | RS252 |
|---|---:|---:|---:|---:|---:|
| M2_BASE | 10% | 15% | 25% | 30% | 20% |
| M2_N1 | 10% | 15% | 25% | 25% | 25% |
| M2_N2 | 10% | 10% | 25% | 30% | 25% |
| M2_N3 | 15% | 15% | 25% | 25% | 20% |
| M1_EQUAL_CONTROL | 20% | 20% | 20% | 20% | 20% |

This is a stability audit, not a new optimiser. Only `M2_BASE` may enter the final active strategy unless a correctness defect invalidates it.

## Phase 2 — exact CASH1 and falsification

`CASH_1_INDIVIDUAL_ABOVE_CASH_252` retains each original 1/N slot only when that family’s causal 252-session total return exceeds contemporaneous GBP-cash 252-session return. Unqualified slots earn accepted GBP cash. The rule is not changed.

CASH1 remains serious when the TOP6–TOP9 regional medians satisfy all ten advancement conditions in the user protocol: full-history and latest-five-year CAGR retention ≥95%; MDD benefit ≥3 percentage points or Ulcer reduction ≥15%; Calmar improvement ≥15%; positive baseline pool excess; non-negative doubled-cost pool excess; positive drawdown benefit excluding 2025; benefit in multiple defensive episodes; no worse six-month loss; and no one-family/year dependence.

Falsification controls are fixed: CASH0 at CASH1 average exposure, global equity at CASH1 average exposure, CASH0/global scaled without leverage to CASH1 realised volatility, and static global/cash at 25/75, 50/50, 75/25 and 100/0. A timing/selection benefit requires CASH1 to improve terminal wealth at comparable exposure, volatility or drawdown rather than merely holding less equity.

## Phase 3 — limited turnover control

- `R0_EXACT_CASH1`: monthly TOP7 CASH1 with no buffer.
- `R1_RANK_HYSTERESIS`: enter TOP7; retain an existing qualifying holding while rank ≤9; remove below rank 9 or on CASH1 failure; fill vacancies monthly by highest-ranked qualifying family.
- `R2_WEEKLY_EXIT_ONLY`: construct monthly exactly as R0; between monthly reviews, an existing holding failing exact CASH1 exits next session to cash; no mid-month replacement.

R1/R2 may replace R0 only if the preregistered advancement gate passes across TOP6–TOP9. If both pass, select the one with the larger full-history median Calmar improvement; differences below 0.05 are resolved by lower turnover, then simplicity order R1 before R2.

## Phase 4/5 — core, blends and volatility

Core candidates are `CORE_0_GLOBAL` and `CORE_1_GLOBAL_ABSOLUTE_MOMENTUM`, where CORE1 owns global developed equities only when its 252-session total return exceeds GBP-cash 252-session return; otherwise cash. Static controls are 25%, 50%, 75% and 100% global with the remainder in cash.

CORE1 is selected over CORE0 only if full-history net CAGR retention is at least 90% and either MDD improves by at least five percentage points or Ulcer Index falls by at least 20%. Otherwise CORE0 remains the core.

Using the selected rotation implementation and selected core, test only 25/75, 50/50, 75/25 and 100/0 rotation/core at monthly sleeve rebalancing. Identify return-maximising, drawdown-minimising and balanced unscaled Pareto candidates. Volatility scaling is then permitted only on those at fixed 10%, 12.5% and 15% targets, using prior 63-session realised portfolio volatility, monthly updates, no leverage and residual GBP cash. Each scaled result is compared with a static same-average-exposure control.

## Strategy-selection hierarchy

1. Eliminate causal, identity, execution, cost or implementation failures.
2. Active edge requires positive full-history equal-pool excess, non-negative equal-pool excess excluding 2025 and under doubled costs, coherent TOP6–TOP9 results, no single-family explanation, and matched-exposure benefit.
3. Risk edge uses the three exact definitions in the governing instruction.
4. Select in order: both return and risk edge; strong risk edge; hybrid core/satellite; global absolute-momentum core; fixed global/cash.
5. The balanced candidate is chosen from the Pareto set by meeting the acceptable SIPP region first, then preferred-region count, then highest net CAGR, then lower Ulcer, turnover and rule complexity. This is not maximum-CAGR selection.

Deployment sizing is evidence-based rather than fitted. No newly selected active model receives the whole SIPP. The permitted tiers are CORE_ONLY, CORE_PLUS_10_PERCENT_ROTATION_PILOT, CORE_PLUS_25_PERCENT_ROTATION_PILOT and SHADOW_ONLY_PENDING_IMPLEMENTATION. A 10% pilot is an explicitly authorised deployment-governance size, not a historically optimised blend.

## Costs, windows and robustness

Baseline costs are 20 bp one way plus £3.99 per leg at £250,000. Doubled costs are 40 bp plus £7.98 per leg. Live-cost estimates at £100k/£250k/£500k/£750k/£1m are implementation diagnostics and cannot alter historical signals.

Windows: full causal chain, pre-2020, post-2020, latest five years from 2021-09-01, latest three years from 2023-08-21, 2025 excluded, leave-one-year-out and partial 2017/2026 disclosed. Robustness includes leave-one-family-out, top 1/3/5 family and holding-spell removals, exclusions of 2020, 2025 and both, random selection and monthly rank shuffling with deterministic seeds.

Long-history indices or proxies may be used only as explicitly labelled stress evidence. No proxy is concatenated to executable ETF history. Retirement diagnostics use no/3%/4% withdrawals; real metrics are reported only if an accepted point-in-time UK inflation series already exists.

## Mandatory final output

The stage ends with one exact whole-SIPP strategy, one active-sleeve deployment tier, one complete defensive fallback, monthly operating rules, monitoring, suspension and research-reopening conditions. No broker order or prospective event is authorised.
