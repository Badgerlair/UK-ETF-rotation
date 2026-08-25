# UKACTIVE-A4F-SIPP preregistration

## Registration and evidence boundary

`UKACTIVE-A4F-SIPP-20260825-001` is a separately governed E2 developmental stage on branch `research/ukactive-a4f-sipp-regime`. It starts from immutable A4E-SIPP manifest commit `ce6136f52ca646698a56e4ff4bbb8577214a684d` and tag `ukactive-a4e-sipp-v1-20260824`. The historical research cutoff is 2026-08-21. Later data are prohibited from thresholds, comparisons, selection and robustness.

This file and its machine-readable companions are committed before any A4F return or regime outcome is calculated. A1–A5, A4D and A4E-SIPP remain read-only. The current unrelated dirty-worktree files are excluded from every A4F commit.

## Frozen scientific contract

The 27-family point-in-time `INDUSTRY_PLUS_THEME` universe, economic-family duplicate suppression, corrected A2R2 calendar and endpoint-validity policy, GBP total-return accounting, accepted GBP cash series, `GLOBAL_DEVELOPED_WORLD`, next-session execution within three valid XLON sessions, 20 bp plus £3.99 baseline costs, 40 bp plus £7.98 doubled costs, and £250,000 canonical notional remain authoritative.

The only rotation sleeve is `M2_BASE | TOP7 | MONTHLY | CASH0_ALWAYS_INVESTED | EQUAL`, with rank-score weights RS21 10%, RS42 15%, RS63 25%, RS126 30% and RS252 20%. No A4F result may alter its signal, breadth, universe or internal weighting.

Direct comparisons use the common executable chain beginning 2017-02-03, its first review on 2017-02-28 and first possible execution on 2017-03-01. A separate longer core-only table may begin at the accepted global-history start, but it cannot be ranked directly against the shorter rotation chain without the common-window view.

## Phase 0 audit gate

Before policy comparison, reproduce A4E decision-critical values for global 100%, global 75%/cash 25%, M2 TOP7 CASH0, M2 TOP7 CASH1, matched-exposure controls, random-selection and rank-shuffle percentiles, full-history and final-five-year metrics, and costs. Reconcile the common chain and longer core-only window. A material failure stops the stage as `A4F_SIPP_AUDIT_FAIL`.

## Causal risk state

At each valid XLON month-end, compute global 126- and 252-session total returns minus contemporaneous GBP cash returns. Compute annualised volatility from the prior 63 valid global daily returns. The high-volatility boundary is the 75th percentile of prior month-end volatilities only, excluding the current observation and requiring 36 prior monthly values. Accepted pre-rotation global data seed the boundary.

`RISK_SCORE = I(G126 excess <= 0) + I(G252 excess <= 0) + I(vol63 > prior vol75)`. The exact score 0–3 is retained.

## Causal leadership state

For each month-end, leadership spread is mean M2 score of the current TOP7 minus the median score of all eligible families. Persistence is the Spearman correlation of current and preceding-month M2 scores among at least three common eligible families, with average ranks for ties. Absolute support is the number of current TOP7 families whose 252-session return exceeds cash.

The selected set preserves canonical A4D semantics: take the strongest `min(7, current valid count)` and require at least three valid M2 families; no future member is backfilled. Spread and persistence are high only when strictly above their prior-only expanding medians. Accepted causal M2 diagnostics begin 2014-01-31; 37 valid month-ends precede the common chain and the 24-prior-observation mark is reached on 2016-01-29. If fewer than three families or a required prior threshold is unavailable, leadership defaults weak and the reason is retained. Absolute support is high at five or more selected families, so it cannot pass when only three or four are available. Leadership is strong when at least two of the three tests are true; otherwise it is weak. Sensitivity changes the two expanding quantiles jointly to 40%, 50% and 60%, never the candidate 50% definition.

## Four-state map

| State | Frozen rule |
|---|---|
| R1 BROAD_RISK_ON | risk score 0–1 and leadership weak |
| R2 LEADERSHIP_RISK_ON | risk score 0–1 and leadership strong |
| R3 ISOLATED_LEADERSHIP | risk score 2–3 and leadership strong |
| R4 CAPITAL_PRESERVATION | risk score 2–3 and leadership weak |

An episode is a maximal consecutive run of one state. A state needs at least 18 months and three episodes for a strong claim; otherwise it is labelled `INSUFFICIENT_REGIME_SAMPLE`. Forward 1/3/6-month outcomes begin after the decision and are diagnostic only.

Secondary dispersion, return-dispersion, pairwise-correlation, PCA, breadth, TOP7 retention and global-drawdown fields cannot determine allocations in A4F. Descriptive macro work uses release-lagged official data only; otherwise it is explicitly `MACRO_REGIME_DATA_INSUFFICIENT`.

## Candidate strategies

Static monthly-rebalanced portfolios are restricted to global/cash 25/75, 50/50, 75/25 and 100/0; M2/cash 25/75, 50/50, 75/25 and 100/0; global/M2 100/0, 90/10, 75/25, 50/50 and 0/100; and three-way 50/25/25 plus 75/10/15. Each M2 allocation is compared with an otherwise identical SWDA allocation.

Risk maps are fixed at 75% risky; score-25 `[100%,75%,50%,25%]`; and score-33 `[100%,67%,33%,0%]`. Alpha allocation is 0% M2, 25% of risky allocation when leadership is strong, or the non-live-eligible 50% diagnostic. When leadership is weak, the risky allocation is all global.

Policies are exactly P0 fixed75/A0, P1 score25/A0, P2 risky100/A25, P3 score25/A25, P4 score33/A25 and P5 score25/A50 diagnostic. No other policy is permitted.

## Timing and hysteresis

Signals form after final valid XLON month-end close. Targets execute at the first common valid following XLON session within three sessions; same-close return is impossible. Immediate switching adopts the new target at that execution.

Asymmetric hysteresis makes every risk reduction and M2 removal immediate. Increasing risk requires two consecutive month-ends supporting the same or a less-defensive target. Adding M2 requires leadership strong at two consecutive month-ends. It does not delay further defence.

## Accounting and attribution

Weights drift between monthly executions and rebalance at execution. Cash earns the accepted cash return. Distributions and FX appear once through accepted GBP total-return values. No leverage, shorting or broker action is allowed.

Risk timing is measured against an alpha-zero counterfactual, M2 selection against the same risk path with alpha zero, interaction as the combined linked-P&L residual, cash yield from opening cash weight times cash return, and costs from actual execution legs. Switching value is measured against a static monthly portfolio with matched average weights. All attribution must reconcile to linked portfolio P&L within numerical tolerance.

## Robustness, controls and noncausal ceilings

The fixed candidate is evaluated over full common history, pre-/post-2020, latest five and three years, excluding 2025, excluding 2020, excluding both, leave-one-year-out, baseline and doubled costs, leave-one-family-out, top-family and top-three-family removal, and both switch modes. Volatility sensitivity is restricted to 70/75/80 percentiles; leadership sensitivity to 40/50/60 percentiles.

Every dynamic policy receives matched average-exposure, M2-exposure, volatility and drawdown controls. Monthly, annual and regime oracles use only preregistered static candidates and are labelled `NONCAUSAL_DIAGNOSTIC_ONLY`; they cannot select thresholds or policies.

Paired monthly candidate-minus-control returns receive a Newey–West HAC intercept test with lag three and a 10,000-replication moving-block bootstrap using six-month blocks, 95% intervals and seed 20260825. Benjamini–Hochberg FDR across the ten selectable policy-by-switch incremental-return tests is contextual only; the preregistered economic gates remain primary. Sparse regimes cannot support strong inference.

The builder must fail if any signal, return or selected input exceeds 2026-08-21, or if any expanding threshold includes the current or future observation.

## Selection gates

A selectable dynamic policy must pass correctness; retain at least 90% of global CAGR or beat global; meet the drawdown/Ulcer gate; beat a matched-risk control by one preregistered economic threshold; show positive contribution from at least two regimes and three episodes without one switch explaining most benefit; retain positive incremental value excluding 2025; remain viable at doubled costs; avoid one-family dependence; show coherent neighbouring-threshold results; and survive asymmetric hysteresis. Prefer fewer than six strategy changes annually.

Selection follows: regime strategy with return and risk edge; regime strategy with strong risk edge; static global/M2/cash blend; then static global/cash core. One exact whole-SIPP strategy must be selected, but no active edge will be manufactured.

## Evidence and deployment

All A4F historical results remain E2 developmental. If a policy passes, a new prospective specification may be frozen only after results are final; it cannot alter any A5 lineage or backfill prospective evidence. No automatic broker execution is authorised.
