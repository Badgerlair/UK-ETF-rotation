# UKACTIVE-A3R2W weighting definitions and decision rule

This file was frozen after A3R2S authorised weighting research and before any A3R2W result was calculated.

## Methods

- `EQUAL`: equal target weights.
- `RANK_DECAY`: weights proportional to 1/rank.
- `SCORE_PROPORTIONAL_CAPPED`: weights proportional to positive score distance above the weakest selected score, subject to the 50% cap.
- `INVERSE_VOLATILITY_CAPPED`: weights proportional to inverse trailing 63-valid-observation realised volatility, subject to the 50% cap.
- `SIGNAL_X_INVERSE_VOLATILITY`: score conviction multiplied by inverse trailing volatility, subject to the same cap.

For multiple positions the maximum target weight is 50%. One selected exposure may be 100%. The volatility estimate uses only the 63 most recent valid corrected daily returns available at the review close. A computed volatility endpoint may be aligned from the nearest prior valid XLON session within the authoritative three-session A2R2 tolerance; no return or price is filled.

All methods rebalance to target weights on the frozen monthly schedule. Execution is at the first valid eligible close after the review close under the existing three-session rule, and the new weights first earn the following session's return.

## Frozen usefulness rule

A non-equal method is considered a stable incremental improvement only if, relative to equal weight for the same selection count:

1. final-five-year net CAGR improves by at least 50 basis points;
2. final-three-year and full-history net CAGR are each no worse by more than 50 basis points;
3. at least two of the following improve: maximum drawdown by 2 percentage points, Sharpe by 0.05, mean concentration HHI by 0.05, or turnover by 10%;
4. the direction survives both TOP_2 and TOP_3, rather than appearing in one count only; and
5. the improvement is not erased by the registered 10/20/40 bp cost stresses.

TOP_1 is a parity control and cannot distinguish weighting methods. If no method passes the rule, equal weight remains the transparent baseline. This rule is developmental and does not confer deployment status.
