# UKACTIVE A3 — Scope and Hypotheses

## Decision boundary

This stage tests whether date-T cross-sectional leadership predicts returns beginning strictly on the next A2 research session. It does not construct a portfolio, optimise a holding count, produce a deployment backtest, or establish historical ISA/SIPP/broker eligibility.

**HISTORICAL ELIGIBILITY REMAINS UNRESOLVED.** Current eligibility is never back-projected.

## Authorised universe

- A2-ready families: 86.
- CORE: 38; EXTENDED: 34; EXPERIMENTAL: 14.
- Primary inference: CORE and CORE+EXTENDED.
- EXPERIMENTAL-only and ALL-A3-ready results are sensitivities and cannot determine the decision.
- Ranking key: `economic_exposure_family_id`; tickers, ISINs and listings are not ranking observations.

## Principal hypothesis

Stronger relative and/or absolute GBP total-return leadership may predict stronger subsequent returns over 1, 5, 21, 42, 63 and 126 canonical sessions. A null or inverted result is retained in the complete ledger.

## Predeclared observation design

- Weekly: canonical Wednesday, using the closest actual XLON research session within the ISO week and choosing the earlier session on a tie.
- Monthly: last canonical XLON research session of the month.
- Tuesday and Thursday weekly schedules are perturbations for diagnostic targets only.
- Signal data end after date-T close; the first forward return is date T+1.
- Every lookback and forward horizon requires all underlying A2 observations to be valid; missing observations are not filled.

## Cohorts

Global, category-neutral, geography, sector/industry, thematic, defensive/diversifier, and a narrower defensive fixed-income/cash cohort are reported. The heterogeneous defensive cohort is explicitly descriptive.

## Scientific guardrails

No proxy series, DeepVue input, current broker status, current eligibility, portfolio weights, rebalance buffers, volatility targets or regime filters enter signal construction.
