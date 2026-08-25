# UKACTIVE-A4F-SIPP correctness repair — valid-observation volatility

This material defect was detected by independent read-only review during the pre-commit audit. No A4F result output had been committed.

## Defect

The first implementation of `GLOBAL_VOL_63` applied a 63-row rolling window to the master-calendar-aligned global-return series. A single invalid daily return therefore made the next 63 master rows unavailable. In the common executable window this left 60 of 115 month-end risk states as `REGIME_UNAVAILABLE`; policy construction skipped those decisions and carried stale targets.

That implementation violated the frozen formula, which requires the previous 63 **valid** global-return observations. It contaminated dynamic regime summaries, policy results, matched-risk controls, transition analysis, threshold sensitivity and the dynamic-policy decision. Static SWDA/M2/cash portfolios were unaffected.

## Repair

- Calculate realised volatility over the last 63 valid global daily returns.
- Map a valid volatility endpoint to the nominal month-end only within the authoritative three-XLON-session tolerance.
- Fail closed after a longer endpoint gap.
- Require every common-window month-end to have a valid risk score and non-unavailable regime.
- Require every policy/switch implementation to record every common-window monthly decision.
- Add automated regression coverage for both conditions.
- Count `annual_strategy_changes` from changes in aggregate SWDA/M2/cash allocations, not from ordinary constituent rebalances; disclose rebalance events separately.
- Resolve matched-average-exposure gate statuses after the frozen gate audit instead of leaving `PENDING_FULL_GATE_AUDIT` labels.
- Where the hierarchy selects a static strategy, state explicitly that regime outputs are telemetry and cannot alter its weights.

## Scientific effect

No formula, threshold, allocation map, cost assumption, universe rule or promotion gate changed. All dynamic results, controls, inference, robustness tests, charts and the final hierarchy are regenerated after this repair. Pre-repair dynamic conclusions are invalid and are not preserved as A4F scientific outputs because they were never committed; this audit note preserves the defect evidence.
