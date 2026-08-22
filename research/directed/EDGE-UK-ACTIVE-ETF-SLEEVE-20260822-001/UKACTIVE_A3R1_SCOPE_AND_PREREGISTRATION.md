# UKACTIVE-A3R1 — Scope and preregistration

Policy: `UKACTIVE-A3R1-POLICY-v1.0.0`  
Declared: 2026-08-23 00:37:35 Europe/London  
Pre-research checkpoint: `2c26ad3639e4e025477d9415f4f7b707e9856b55`  
Checkpoint tag: `ukactive-a3r1-preflight-20260823`

## Scientific boundary

A3R1 tests whether short/intermediate benchmark-relative strength, acceleration, recent-period consistency, head-to-head dominance and a transparent level/momentum state contain forward-return information at the economic-exposure-family level. It is signal discovery only. It does not establish historical UK retail, ISA, SIPP or broker availability; it does not construct or optimise a portfolio; and it does not authorise A3R2 or deployment.

Only corrected A2R implementation histories are admissible. `GLOBAL_BANKS` has no valid history and cannot rank. `US_AEROSPACE_DEFENCE` cannot enter before its corrected post-mandate history and exact signal warm-up permit. No proxy, stale, missing, pre-inception, rejected-route or pre-remediation history may enter.

## Frozen research design

The weekly observation is the final canonical XLON research session in each calendar week. A signal forms after that close. Forward return starts on the next eligible session, so date-T return is never earned by a date-T signal.

The common research benchmark is `GLOBAL_DEVELOPED_WORLD`; `GLOBAL_ALL_WORLD` is a recognisable comparator. A common benchmark does not change the cross-sectional order at a single horizon. Its economic role here is qualification, consistency, acceleration, relative-line analysis, parent/global decomposition and forward relative-performance measurement.

Primary group tournaments are geography, country, sector, industry and theme. The all-equity tournament is secondary. A2R fine competition pools are also reported, but a pool with fewer than three contemporaneously valid members receives coverage diagnostics only. Defensive assets are excluded from the primary equity contest.

Cumulative horizons are 21, 42, 63, 126 and 252 sessions. Non-overlapping segments are 0–21, 22–42, 43–63, 64–126 and 127–252 sessions. Formation and forward windows require every canonical-session return to be valid; unavailable families are excluded, never filled or zeroed.

The four multi-horizon structures are frozen before outcome calculation:

| Structure | 21 | 42 | 63 | 126 | 252 |
|---|---:|---:|---:|---:|---:|
| Equal | 20% | 20% | 20% | 20% | 20% |
| Recency tilt | 30% | 25% | 20% | 15% | 10% |
| 60-day centred | 10% | 25% | 35% | 20% | 10% |
| 3/6/12 reference | 0% | 0% | 33.33% | 33.33% | 33.33% |

No continuous weight optimiser is authorised. Neighbourhood tests are limited to 32/42/52, 50/63/75 and two whole-structure perturbations declared in the policy.

Top-tail tests are primary: rank 1, top 2, top 3, top 5, top 10% and top quintile where cohort size permits. Group aggregation is equal weight solely as a neutral signal diagnostic. `PORTFOLIO_WEIGHTING_NOT_OPTIMISED`.

Forward horizons are 5, 10, 21, 42, 63 and 126 sessions, with 10/21/42/63 central to the rotation question. Full-rank IC and top-minus-bottom statistics remain secondary. HAC and circular block-bootstrap inference address serial correlation and overlapping returns. Benjamini–Hochberg adjustment is applied to the predeclared primary top-3/global-benchmark family; raw economic magnitudes and intervals remain visible.

Maturity is contemporaneous in the sense that admission depends only on accrued valid history. Sensitivities use the A2R labels `MATURE`, `DEVELOPING` and `NEW`, without using future returns or future age to decide historical availability.

## Interpretation guardrails

- DeepVue labels have no quantitative role.
- Listing, ticker, ISIN and provider count cannot alter ranking probability.
- Parent/child overlap is diagnostic, not duplicate suppression or a concentration rule.
- RRG-like states are transparent independent definitions, not proprietary JdK formulas.
- Pairwise comparison is a majority of five declared horizon comparisons, not a proprietary Dorsey Wright rule.
- Trend quality is a tercile diagnostic among leaders and is not in the selection score.
- No hysteresis, holding period, rebalance buffer, top-N portfolio, portfolio weight or regime filter is optimised.
- Historical eligibility remains unresolved and current eligibility is never back-projected.

The complete machine-readable policy is `config/UKACTIVE_A3R1_POLICY_v1.json`; the frozen signal-level registry is `UKACTIVE_A3R1_SIGNAL_REGISTRY.csv`. All executed evaluation cells, including failures, will be written to the multiple-testing ledger.
