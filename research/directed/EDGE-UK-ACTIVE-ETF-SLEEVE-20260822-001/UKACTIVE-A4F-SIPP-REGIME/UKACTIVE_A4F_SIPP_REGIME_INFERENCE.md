# UKACTIVE-A4F-SIPP regime inference

Paired monthly policy-minus-matched-control returns use Newey–West HAC lag 3 and a deterministic 10,000-replication moving-block bootstrap with six-month blocks (seed 20260825). Benjamini–Hochberg adjustment covers the ten selectable policy/switch tests. These statistics are contextual; the preregistered economic gates remain primary.

Adequately sampled four-state regimes: R2_LEADERSHIP_RISK_ON. Exact risk-score 0/1/2/3 substates are reported separately in the same summary/ranking outputs. Sparse states remain `INSUFFICIENT_REGIME_SAMPLE` and cannot support strong regime claims.

The ten frozen secondary variables are evaluated in UKACTIVE_A4F_SIPP_SECONDARY_REGIME_DIAGNOSTICS.csv. Each value is observed at decision time; HIGH/LOW uses a current-excluded prior-only expanding median with at least 24 observations; the outcome is the next executable interval's M2-minus-global return. These E1 associations report empirical sign, HAC and block-bootstrap context but are not policy inputs and cannot affect selection.
