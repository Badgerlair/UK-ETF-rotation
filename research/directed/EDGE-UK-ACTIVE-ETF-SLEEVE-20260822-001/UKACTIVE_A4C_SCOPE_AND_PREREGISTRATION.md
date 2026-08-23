# UKACTIVE-A4C — Scope and preregistration

Run ID: `UKACTIVE-A4C-20260823-001`  
Evidence ceiling: `E2_DEVELOPMENTAL`; mechanism diagnostics are `E1_EXPLORATORY`  
Mandate: **LOW FRICTION TO EXPLORE — HIGH FRICTION TO CLAIM**

## Frozen source edge

The source edge is unchanged: `INDUSTRY_PLUS_THEME | MH_LEVEL_3_6_12_REFERENCE | TOP_1 | MONTHLY`. `SLOW_RS` remains the equal average of contemporaneous cross-sectional percentile ranks for RS63, RS126 and RS252. Reviews use the final valid XLON session of each month and executions begin on the first common valid endpoint after the review, never the same close.

The authoritative A2R2 GBP total-return panel, point-in-time admission, family identities, global benchmark, cash series, costs and no-forward-fill controls remain frozen. A4C does not add exposures, signals, horizons, leverage, shorts, macro data, news, fundamentals, discretionary overrides or machine learning.

## Bounded adjacency review before computation

The specified experiment already covers the economically material omitted mechanisms: early access to emerging leadership, delayed trend failure, risk-budget mismatch across volatile exposures, and strategic portfolio interaction with a global core. The appropriate counterfactuals are the frozen incumbent, actual GBP cash, and `GLOBAL_DEVELOPED_WORLD`. Gap risk is measured only where validated open data exist; no close-to-close jump will be labelled an executable opening gap without such evidence. Re-entry, partial profit harvesting and regime scaling are not reopened because A4B already tested and rejected the relevant coarse mechanisms.

## Frozen A4C definitions

`FAST_RS` is the equal average of RS21/42/63 percentile ranks. `SLOW_RS` is the equal average of RS63/126/252 percentile ranks. Primary crossover requires FAST_RS ≥ 90th percentile, FAST−SLOW ≥ 15 points, four-week FAST improvement ≥ 10 points, positive RS63 and positive 42-session relative slope. Exactly one looser and one tighter neighbourhood are retained.

Absolute trend uses the validated GBP total-return index rather than unadjusted local close, avoiding false dividend and FX discontinuities. EMA spans are 21/50/200 sessions, `adjust=False`, with a full-span minimum. Relative trend is the exposure GBP total-return index divided by the validated global-developed GBP total-return index. Realised volatility is trailing 63-session annualised volatility; a 5% floor is a numerical safeguard and no leverage is permitted.

The early ladders, four exit rules, 10%/12.5%/15% volatility targets, 25%/50%/75%/100% active-core weights and transaction-cost stresses are exactly those recorded in `config/UKACTIVE_A4C_POLICY_v1.json`. No result-dependent threshold amendment is permitted.

For `EARLY_C`, a challenger whose crossover fails before it records two consecutive weekly slow-rank improvements is removed; capital returns to the valid incumbent or cash. After that confirmation, the highest achieved ladder weight is retained until the frozen monthly review resolves the handover. This clarification was frozen before any A4C result was computed.

## Sequential gates

1. Exact A4 baseline reproduction.
2. Drawdown root-cause and warning-clock forensics.
3. Migration/conversion study before any early-portfolio result.
4. Independent evaluation of early participation, exits, volatility sizing and fixed core-satellite blends.
5. Controlled combinations only from independently qualifying modules.
6. Robustness, correctness, research-director review and decision.

All outputs retain the warning that historical UK retail, ISA, account and broker eligibility remain partly unresolved. A4C does not start A5.
