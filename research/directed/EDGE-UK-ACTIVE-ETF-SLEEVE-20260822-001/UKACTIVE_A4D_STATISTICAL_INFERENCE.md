# UKACTIVE-A4D statistical inference

All inference is E2 developmental. Weekly signal observations and forward returns overlap, so naive independent-observation t-tests are prohibited. `UKACTIVE_A4D_SIGNAL_HAC_INFERENCE.csv` uses a Newey–West long-run variance for each signal/horizon, with the lag tied to the forward horizon. Benjamini–Hochberg q-values are calculated within each evidence-window/metric family.

The representative portfolio uses a paired six-month circular block bootstrap of monthly returns with 5,000 deterministic draws. This is a falsification/uncertainty diagnostic, not independent confirmation.

| comparator_id                 | observed_annualised_excess   | bootstrap_2_5_percentile   | bootstrap_97_5_percentile   | bootstrap_probability_excess_positive   | two_sided_tail_probability   |
|:------------------------------|:-----------------------------|:---------------------------|:----------------------------|:----------------------------------------|:-----------------------------|
| GLOBAL_DEVELOPED_WORLD        | 1.88%                        | -9.04%                     | 16.20%                      | 59.86%                                  | 80.28%                       |
| EQUAL_WEIGHT_OPPORTUNITY_POOL | 2.94%                        | -5.61%                     | 12.73%                      | 73.80%                                  | 52.40%                       |

The full architecture grid is correlated and staged. It is not described as 77 independent hypotheses; the complete accounting is in `UKACTIVE_A4D_MULTIPLE_TESTING_LEDGER.csv`.
