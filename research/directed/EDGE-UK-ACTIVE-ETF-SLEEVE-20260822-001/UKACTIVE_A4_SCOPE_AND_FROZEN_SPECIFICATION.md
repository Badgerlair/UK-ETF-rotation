# UKACTIVE-A4 scope and frozen specification

Stage: **UKACTIVE-A4 — Candidate Confirmation, Right-Tail Forensics and Implementation Reconstruction**  
Evidence status: **E2 developmental robustness; not E3 independent confirmation**  
Governing mandate: **Low friction to explore — high friction to claim**

## Frozen A4 primary

`INDUSTRY_PLUS_THEME | MH_LEVEL_3_6_12_REFERENCE | TOP_1 | MONTHLY | EQUAL`

- Economic identity: `economic_exposure_family_id`
- Signal: equal mean of contemporaneous within-pool percentile ranks of 63-, 126-, and 252-session GBP total returns relative to `GLOBAL_DEVELOPED_WORLD`
- Review: final valid XLON session of each calendar month
- Execution: first valid close after the review close, within the authoritative three-XLON-session tolerance
- New exposure first earns the session after execution close
- Costs: existing A3R2 contract; 20 bp one-way base, £3.99 per trade leg at £250,000, separately applicable 0.75% non-GBP FX
- No same-close execution, no proxy history, no stale/filled returns, and no historical eligibility inference

No primary signal, horizon, weight, rank, universe, benchmark, cadence, or execution parameter may change in A4.

## Frozen robustness comparators

1. `INDUSTRY | MH_LEVEL_3_6_12_REFERENCE | TOP_1 | MONTHLY | EQUAL`
2. `INDUSTRY | PAIRWISE_MAJORITY_5H | TOP_1 | MONTHLY | EQUAL`
3. Concentration controls: primary pool/signal/cadence with `TOP_1`, `TOP_2`, and `TOP_3`; equal weight only.

No TOP_4, TOP_5, variable threshold, alternative weight, regime filter, or standalone short-horizon selection system is authorised.

## Frozen forensic estimands

- Every final-five-year monthly rank and decision is retained.
- Contribution uses daily portfolio-wealth changes, with execution-session market P&L attributed to the pre-trade holding and transaction costs separately identified. P&L contributions must exactly reconcile end wealth minus start wealth within `1e-10`.
- Pre-entry and post-exit windows are 63 XLON sessions.
- Capture ratio is positive held log return divided by the sum of positive pre-entry, held, and post-exit log returns. It is ex-post diagnostic only.
- Entry timing: EARLY when the positive pre-entry share is at most one third; MID-TREND through two thirds; otherwise LATE.
- Exit timing: EARLY when the following 63-session return exceeds 5%; LATE when the last 21 held sessions are below -5% and the following return is non-positive; otherwise APPROPRIATELY.
- Primary future-tail horizon is the next frozen monthly execution endpoint. Secondary 21/42/63-session results are descriptive.

## Frozen falsification

- Random-selection placebo: 10,000 paths, seed `20260823`.
- Rank-permutation test: 10,000 paths, seed `20260824`.
- Each retains monthly dates, contemporaneous membership, one holding, execution dates, and the cost contract.
- A path is invalid—not repaired or filled—if its selected family cannot be valued at a frozen interval endpoint.

## Concentration-control interpretation

TOP_2/TOP_3 must retain at least 60% of TOP_1 net excess, remain positive versus the pool and unselected exposures, and materially improve drawdown by 5 percentage points and/or reduce HHI by 0.20. No candidate is selected by CAGR alone.

## Implementation boundary

Historical evidence work is limited to actually selected primary/TOP_2/TOP_3/neighbour families plus current benchmark references. Current ii observations dated 2026-08-23 remain current-only. Missing primary historical evidence remains explicitly uncertain.

## Prospective boundary

If A4 survives, A5 files may be created and committed, but A5 may begin only after its specification commit/tag. No prospective result will be backfilled or generated in A4, and no unattended scheduler will be created.
