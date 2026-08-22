# UKACTIVE A3 — Statistical Inference

## Estimands

The primary estimand is the date-level Spearman cross-sectional information coefficient. Bucket returns and top-minus-bottom spreads are diagnostics, not long-short strategy returns.

## Serial correlation and overlap

All formal means use a Bartlett/Newey-West heteroskedasticity-and-autocorrelation-consistent standard error. The lag is `max(1, ceil(forward horizon / expected observation spacing) - 1)`, with five sessions for weekly observations and 21 for monthly observations. Each output explicitly marks whether forward observations overlap.

Circular block-bootstrap 95% confidence intervals use 2000 deterministic replications and seed 20260822 for diagnostic targets. Block length is `max(5, HAC lag + 1)`.

## Multiple testing

Benjamini-Hochberg correction is applied to the 84 predeclared CORE+EXTENDED/global headline IC tests: 14 primary definitions × two frequencies × three forward horizons. Neighbourhood, cohort, subperiod, regime, dependency and EXPERIMENTAL results are labelled secondary diagnostics and are not silently promoted because of a nominal p-value.

Headline FDR survivors across all primary signals: 0.

## Changing membership

Signals and ranks use only families with valid contemporaneous A2 observations and complete lookbacks. Date-level aggregation accommodates changing cross-sectional membership; no unavailable exposure receives a zero signal or return.

## Interpretation boundary

Statistical evidence in this stage concerns predictive ranking information. It is not evidence of a historically verified UK-investable strategy, because historical retail/account eligibility remains unresolved.
