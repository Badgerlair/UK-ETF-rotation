# UKACTIVE-A4B regime-state definitions

The A3R2 categorical regime inputs are reused without changing their expanding/prior thresholds.

Regime score adds one point for each of: global benchmark above its 200-session trend, dispersion HIGH, breadth MEDIUM, rotation intensity HIGH and US technology NOT dominant. It subtracts one point for volatility HIGH.

State precedence:

1. `HOSTILE`: score ≤ 0, or global trend below/equal 200 while volatility is HIGH.
2. `DETERIORATING`: the shifted prior-eight-week maximum reached at least 4 and current score is at least two points below it.
3. `MATURE`: the shifted prior-eight-week maximum reached at least 4 and current score is one point below it.
4. `STRONG`: current score ≥ 4.
5. `POSITIVE`: every other non-hostile observation.

A regime peak is detected at time T only when T-1 equalled the trailing eight-week maximum available through T-1 and score at T has declined by at least one. The reported peak date is T-1 and the actionable detection date is T; no future market high is used.

Multipliers are frozen as control 1.00; binary HOSTILE 0.00; gradual STRONG/POSITIVE 1.00, MATURE 0.75, DETERIORATING 0.50, HOSTILE 0.00; and the single authorised sensitivity with HOSTILE 0.25.
