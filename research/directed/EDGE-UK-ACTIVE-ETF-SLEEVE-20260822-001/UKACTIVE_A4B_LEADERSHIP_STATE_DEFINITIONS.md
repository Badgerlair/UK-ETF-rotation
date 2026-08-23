# UKACTIVE-A4B leadership-state definitions

Primary precedence is `FAILED → WEAKENING → EXTENDED → ESTABLISHED → CONFIRMING → EMERGING → OTHER`.

* `EMERGING`: FAST_RS ≥ 0.90; RS63 > 0; four-week FAST change ≥ +0.10; SLOW_RS < 0.80.
* `CONFIRMING`: FAST_RS ≥ 0.80; SLOW_RS ≥ 0.60; four-week SLOW change > 0; RS63 > 0.
* `ESTABLISHED`: frozen slow ordinal rank 1; FAST_RS ≥ 0.50; RS63 > 0; relative slope 42 ≥ 0.
* `EXTENDED`: ESTABLISHED and RS63 exceeds its shifted, expanding prior 90th percentile.
* `WEAKENING`: slow ordinal rank ≤ 3 and any of FAST_RS < 0.50, four-week FAST change ≤ -0.20, or relative slope 42 < 0.
* `STRONGER_WEAKENING`: FAST_RS < 0.25, or negative relative slope 42 with a second consecutive WEAKENING observation.
* `FAILED`: slow ordinal rank > 5 with FAST_RS < 0.50, or RS63 ≤ 0 with negative relative slope 42.

Only one primary state is assigned. The looser/tighter robustness neighbourhoods are frozen in the policy; they do not create additional primary specifications.

Starter allocation is fixed at 25% for EMERGING, 50% for CONFIRMING, 75% for weekly slow top three and 100% for weekly slow rank 1. A challenger failing all four progression conditions is removed. At most one incumbent and one challenger may be risky at once.
