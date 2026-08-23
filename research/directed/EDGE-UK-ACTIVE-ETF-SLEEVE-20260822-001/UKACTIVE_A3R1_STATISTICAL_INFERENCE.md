# Blocking coverage qualification

A3R1-DQ-001 forces `UKACTIVE_A3R1_FAIL_DATA_OR_METHOD`: the strict A2R-valid 252-session feature and all six dependent principal signals have no post-2020 evidence. The statistics below are retained as descriptive diagnostics and cannot support promotion. See `UKACTIVE_A3R1_DATA_AND_METHOD_WARNINGS.md`.

# UKACTIVE-A3R1 statistical inference

A3R1's primary estimand is the date-level equal-weight top-three forward-return advantage versus `GLOBAL_DEVELOPED_WORLD`, not a portfolio return. Weekly observations overlap at 10/21/42/63-session forward horizons. Bartlett/Newey–West HAC standard errors use `max(1, ceil(h/5)-1)` lags. The predeclared primary cells also receive a 2,000-replication circular block-bootstrap interval with deterministic seeds.

The Benjamini–Hochberg registry contains 180 primary-predeclared cells: nine primary signals × five primary role groups × four central forward horizons. The preregistered minimum is 24 date observations; 174 cells meet it and receive formal BH/block-bootstrap inference. 16 eligible cells survive q ≤ 0.10; 6 have a positive 95% block-bootstrap lower bound. Sub-minimum cells retain descriptive effect sizes only.

The complete ledger contains 7,563 executed specification/diagnostic rows. Correlated horizons, tails and subperiods are not described as independent hypotheses. Failed and non-positive cells remain in the ledger.

## Signal-level primary support summary

| signal_id                   |   mean_advantage_across_primary_cells |   positive_cell_fraction |   raw_p_le_0_10_count |   fdr_q_le_0_10_count |   bootstrap_positive_count |   cell_count |   support_sort_score |
|:----------------------------|--------------------------------------:|-------------------------:|----------------------:|----------------------:|---------------------------:|-------------:|---------------------:|
| MH_LEVEL_60D_CENTERED       |                          -0.00587173  |                 0.157895 |                     7 |                     3 |                          1 |           19 |             0.894737 |
| MH_LEVEL_EQ                 |                          -0.0063637   |                 0.157895 |                     7 |                     3 |                          1 |           19 |             0.894737 |
| MH_LEVEL_3_6_12_REFERENCE   |                          -0.00641011  |                 0.157895 |                     7 |                     3 |                          1 |           19 |             0.894737 |
| PAIRWISE_MAJORITY_5H        |                          -0.00657231  |                 0.157895 |                     7 |                     3 |                          1 |           19 |             0.894737 |
| SHORT_MINUS_LONG_RS         |                          -0.00561156  |                 0.210526 |                     7 |                     2 |                          1 |           19 |             0.842105 |
| MH_LEVEL_RECENCY_TILT       |                          -0.00626304  |                 0.157895 |                     7 |                     2 |                          1 |           19 |             0.789474 |
| ACCEL_FAST_COMPOSITE        |                          -0.00298164  |                 0.45     |                     3 |                     0 |                          0 |           20 |             0.6      |
| DISCRETE_RECENT_CONSISTENCY |                          -6.20224e-05 |                 0.4      |                     1 |                     0 |                          0 |           20 |             0.45     |
| RRG_TRANSPARENT_LEVEL       |                          -0.00664148  |                 0        |                     3 |                     0 |                          0 |           20 |             0.15     |

Effect sizes, confidence intervals and hit rates are reported alongside p/q values. A small p-value alone cannot promote a signal. Historical eligibility remains unresolved, so no result is a verified UK-investable strategy or deployment claim.
