# UKACTIVE-A4F-SIPP mandate-coverage repair — 2026-08-25

This post-preregistration repair changes audit completeness and presentation only. It does not alter any frozen signal, portfolio, regime formula, threshold, policy allocation, cost assumption, execution rule, promotion gate, or historical return chain.

Repairs applied:

- expanded family exclusions to every permitted static M2 portfolio;
- ranked family and holding-spell contributors by prior-NAV-normalised arithmetic return contribution, retaining nominal currency P&L as audit-only metadata;
- added standalone M2, selected static blend, and both Policy 3 switch-mode holding-spell exclusions;
- added separate 10,000-path CASH0 random-selection and monthly-rank-shuffle diagnostics;
- completed exact risk-score 0–3 summaries, secondary-regime sign diagnostics, Policy 5 diagnostic controls, annual policy/switch matrices, matched-risk controls, and cost-drag fields;
- made the state-machine, suspension rules, current operating rule, and shadow research selection explicit and non-ambiguous;
- corrected the oracle to include the first partial common-window month and annualised event counts by elapsed calendar years.

Scientific disposition remains unchanged:

- no dynamic policy passes all frozen gates;
- regime switching is not promoted;
- `GLOBAL_50_M2_50` remains the E2 research/shadow selection under the frozen hierarchy;
- current operating capital remains the separate static `GLOBAL_75_CASH25` continuity rule;
- no broker order or live allocation is authorised.
