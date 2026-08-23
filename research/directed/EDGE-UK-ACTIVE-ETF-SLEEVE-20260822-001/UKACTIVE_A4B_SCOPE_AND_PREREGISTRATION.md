# UKACTIVE-A4B — Scope and preregistration

Run ID: `UKACTIVE-A4B-20260823-001`  
Evidence: portfolio results are `E2_DEVELOPMENTAL`; mechanism diagnostics are `E1_EXPLORATORY`; no historical result can be E3.  
Governing mandate: **low friction to explore; high friction to claim**.

## Frozen source edge

The economic-family universe, corrected A2R2 XLON clock, point-in-time admission, GBP total-return accounting, `INDUSTRY_PLUS_THEME` pool, global benchmark, and monthly `MH_LEVEL_3_6_12_REFERENCE` rank are unchanged. The A4 baseline is `TOP_1`, 100% risky, monthly review, next-eligible-session execution and the existing 20 bp/£3.99 cost convention.

The original prospective file and tag remain `A5_BASELINE_V1_NOT_STARTED`. A4B does not alter, start, backfill or schedule that lineage.

## Registered delta

A4B tests only position lifecycle and total-risk management:

1. weekly versus monthly management of the frozen monthly leader;
2. two fixed starter ladders driven by predeclared fast/slow states;
3. four coarse exit/profit-lock modules tested separately;
4. three frozen regime-scaling variants plus a no-scaling control;
5. a sequentially gated combination and ablation, never an unrestricted Cartesian search;
6. explicit GBP cash accounting and counterfactual monetisation/de-risk ledgers.

All thresholds, state precedence, lockout behaviour, regime score, multipliers, gates, costs and evidence windows are frozen in `config/UKACTIVE_A4B_POLICY_v1.json` before portfolio outcomes are calculated.

## Bounded adjacency review

The cheap, decision-relevant omissions are covered: starter dilution, incumbent/challenger handover, fast failure, partial harvesting, MFE give-back, regime exposure, cash, costs, right-tail retention and counterfactual avoided-loss/foregone-upside attribution. Intraday stops, new horizons, new families, leverage, shorting, news, fundamentals, machine learning, macro forecasts, tax and discretionary overrides remain excluded.

## Gates and interpretation

Maximum drawdown worse than -25% fails the desired risk standard; better than -15% is preferred. A promoted lifecycle should normally retain positive pool excess, positive selected-versus-unselected spread, at least 70% of baseline pool excess and at least 70% of baseline top-three contribution. Profit modules additionally require positive net monetisation value. Regime modules require positive net de-risk value and more than one coherent event.

Outcome exposure after this commit cannot amend this preregistration. Failed variants remain in the registry and outputs.

## Permanent warnings

`HISTORICAL UK RETAIL, ISA, ACCOUNT AND BROKER ELIGIBILITY REMAIN PARTLY UNRESOLVED`

`A4B IS DEVELOPMENTAL RESEARCH, NOT A DEPLOYMENT OR INVESTMENT RECOMMENDATION`
