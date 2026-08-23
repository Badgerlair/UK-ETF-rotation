# UKACTIVE-A4 research director review

Generated: 2026-08-23T09:12:53+00:00  
Decision: **UKACTIVE_A4_REGIME_CONDITIONAL_ONLY**  
Evidence level: **E2 developmental; no E3 evidence exists**

## A. Empirical summary

The frozen A4_PRIMARY contract was not changed. Over the contemporary five-year window it delivered 24.86% net CAGR versus 10.99% for the contemporaneous equal-weight pool and 11.52% for global developed equities. Net excess was +13.87 pp versus the pool and +13.34 pp versus global; selected-versus-unselected spread was +17.13 pp. Maximum drawdown was -30.90%, zero-cash-hurdle Sharpe 0.67, annual traded-notional turnover 8.25x and trade legs 41.

The result is highly right-tailed. GLOBAL_SILVER_MINERS contributed 52.86% of net wealth gain. The top three contributed 90.45%; the top five 112.45%. Values above 100% occur because losing families offset part of the gain. Removing the actual top three contributors changes net excess versus the pool to -12.97 pp and drawdown to -55.43%.

Rank 1 nevertheless shows repeated cross-sectional information across 59 evaluable decisions: future top-decile probability 20.34%, top-quintile 35.59%, pool-median beat rate 61.02%, global beat rate 54.24%, and equal-pool beat rate 57.63%. Holding-episode returns have skewness 2.19; the best episode supplied 44.79% of the arithmetic episode-return sum.

## B. Benchmarks and conventional-method context

A4 compares the candidate with global developed equities, the contemporaneously eligible equal-weight industry/theme pool, the unselected pool, TOP_2/TOP_3 concentration controls, two frozen structural neighbours, 10,000 random-selection paths and 10,000 within-date rank permutations. These are stronger controls than a single passive benchmark because they separate industry/theme beta from selection information.

The economic mechanism is consistent with the established cross-sectional and industry-momentum literature, including Jegadeesh–Titman (1993) and Moskowitz–Grinblatt (1999), but A4 is not a replication and those papers cannot confirm this UK ETF implementation. The literature also documents momentum crashes and weak findings under alternative inference, so positive skew and regime dependence are treated as risks rather than proof.

References: https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1993.tb04702.x ; https://onlinelibrary.wiley.com/doi/full/10.1111/0022-1082.00146 ; https://www.sciencedirect.com/journal/journal-of-financial-economics/vol/122/issue/2 ; https://doi.org/10.1016%2Fj.jfineco.2019.08.004

## C. Economic and causal explanations

The leading explanation is gradual capital migration across industries/themes: a 3/6/12 rank can identify an exposure after leadership becomes persistent but before a large trend is exhausted. The three major contributors were generally entered mid-trend, not at inception. Their episode capture diagnostics are:

- GLOBAL_SILVER_MINERS: EP-019 63.44% (MID_TREND).
- EUROPE_BANKS: EP-007 41.17% (MID_TREND), EP-012 5.04% (LATE), EP-016 7.19% (MID_TREND), EP-018 42.16% (EARLY).
- GLOBAL_SEMICONDUCTORS: EP-003 0.00% (LATE), EP-008 26.29% (MID_TREND), EP-011 19.35% (MID_TREND), EP-013 0.00% (LATE), EP-021 36.99% (MID_TREND).

Competing explanations remain credible: the richer post-2020 ETF opportunity set, launch-cohort effects, survivor incompleteness, and ordinary sample luck. Pre-2020 net excess versus the pool was -6.85 pp, while post-2020 it was +13.33 pp. This is too large a structural break to call unconditional alpha.

## D. Falsification and robustness

The candidate sits at the 96.06% percentile of valid random-selection paths and the 96.10% percentile of valid within-date rank permutations. Those percentiles are conditional on fully valid paths: only 5462/10,000 placebo and 5487/10,000 permutation paths remained valid under the frozen endpoint rules. Invalid paths were never filled.

The date-level selected-minus-unselected mean is 1.70% per monthly interval (Newey-West t=1.94, p=0.052); the block-bootstrap 95% interval is [-0.12%, 3.52%], crossing zero. No multiple-testing-adjusted broad edge was established in A3R2.

TOP_2 retains 63.92% of TOP_1 excess but improves drawdown by only +0.64 pp. TOP_3 retains 55.52% and improves drawdown by +4.56 pp. Neither resolves top-three-family dependence.

## E. Friction and executability

At the frozen 20 bp/£250k convention, net CAGR is 24.86%. At 40 bp/£250k it remains 22.85%, +11.86 pp above the pool. This is a modelled friction sensitivity, not realised historical spread evidence. NEXT_OPEN is unreported because no validated open-price execution route exists.

Historical implementation identities are exact and return-valid. Across 21 primary holding episodes, retail evidence is {"HISTORICALLY_PROBABLE_UK_RETAIL": 20, "HISTORICALLY_VERIFIED_UK_RETAIL": 1} and ISA evidence is {"HISTORICALLY_PROBABLE_ISA_ELIGIBLE": 21}; historical platform evidence is zero verified. Current ii confirmation covers 2/27 pool families and 1/25 currently signal-eligible families. This blocks deployment.

## F. Evidence classification

- E1: causal/regime interpretation and short-horizon transition diagnostics.
- E2: all frozen historical returns, concentration tests, falsification, costs, and implementation reconstruction.
- E3: none. Historical rolling, leave-one-year-out and walk-forward-style diagnostics are not independent confirmation.

## G. Recommended next experiment

Proceed only to **UKACTIVE-A5 — prospective shadow forward test**, not deployment. The v1 model, universe policy, calculation, month-end review, TOP_1 rule, timing, benchmark, costs and post-rank implementation check are frozen in `config/ukactive_a5_frozen_candidate.json`. The first possible signal is 2026-08-28, after the model tag; nothing is backfilled. Primary review requires 24 completed monthly decisions. Unconfirmed ii implementation is logged as non-executable and never causes rank substitution. Any rule change terminates the v1 confirmation lineage.
