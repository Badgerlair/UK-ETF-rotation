# UKACTIVE-A3R1R1 statistical inference

This is the unchanged preregistered A3R1 experiment rerun after A2R2 data remediation. The primary estimand remains the weekly date-level equal-weight top-three forward-return advantage versus GLOBAL_DEVELOPED_WORLD. Newey–West/HAC, circular block bootstrap, Benjamini–Hochberg scope, minimum observations and promotion thresholds are unchanged.

The primary FDR family contains 180 cells; 180 meet the preregistered formal-inference minimum. 0 survive q ≤ 0.10 and 0 have a positive 95% block-bootstrap lower bound.

The complete ledger retains 9,336 executed rows. Failed, negative and sub-minimum cells are preserved.

## Signal-level support

| signal_id                   |   mean_advantage_across_primary_cells |   positive_cell_fraction |   raw_p_le_0_10_count |   fdr_q_le_0_10_count |   bootstrap_positive_count |   cell_count |   support_sort_score |
|:----------------------------|--------------------------------------:|-------------------------:|----------------------:|----------------------:|---------------------------:|-------------:|---------------------:|
| MH_LEVEL_EQ                 |                           -0.00135062 |                     0.35 |                     4 |                     0 |                          0 |           20 |                 0.55 |
| PAIRWISE_MAJORITY_5H        |                           -0.00146981 |                     0.25 |                     6 |                     0 |                          0 |           20 |                 0.55 |
| MH_LEVEL_3_6_12_REFERENCE   |                           -0.00107202 |                     0.3  |                     4 |                     0 |                          0 |           20 |                 0.5  |
| MH_LEVEL_60D_CENTERED       |                           -0.00142346 |                     0.25 |                     5 |                     0 |                          0 |           20 |                 0.5  |
| RRG_TRANSPARENT_LEVEL       |                           -0.00167099 |                     0.2  |                     5 |                     0 |                          0 |           20 |                 0.45 |
| MH_LEVEL_RECENCY_TILT       |                           -0.00164281 |                     0.2  |                     4 |                     0 |                          0 |           20 |                 0.4  |
| SHORT_MINUS_LONG_RS         |                           -0.0037899  |                     0.1  |                     6 |                     0 |                          0 |           20 |                 0.4  |
| ACCEL_FAST_COMPOSITE        |                           -0.00236444 |                     0.2  |                     3 |                     0 |                          0 |           20 |                 0.35 |
| DISCRETE_RECENT_CONSISTENCY |                           -0.00168207 |                     0.15 |                     3 |                     0 |                          0 |           20 |                 0.3  |

This is signal research, not an historically verified UK-investable strategy or deployment result.
