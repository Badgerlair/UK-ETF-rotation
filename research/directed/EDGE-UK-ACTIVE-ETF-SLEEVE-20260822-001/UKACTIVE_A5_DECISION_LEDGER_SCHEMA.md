# UKACTIVE-A5 decision-ledger schema

One immutable row is permitted per prospective review date.

Required fields:

| Field | Meaning |
|---|---|
| `specification_id` | Frozen A5 lineage identifier. |
| `model_freeze_git_tag` / `model_freeze_git_commit` | Source-control identity resolved at run time. |
| `signal_date` | Final valid XLON session of the review month. |
| `recorded_at_utc` | Time the shadow decision was generated. |
| `input_feature_panel_path` / `input_feature_panel_sha256` | Exact feature input. |
| `current_implementation_path` / `current_implementation_sha256` | Exact current implementation input. |
| `eligible_family_count` | Contemporaneous families with complete frozen score. |
| `rank_1_family` | Economic exposure selected before implementation checks. |
| `rank_1_score` | Frozen equal 3/6/12 percentile-rank composite. |
| `rank_rs_63` / `rank_rs_126` / `rank_rs_252` | Frozen components. |
| `score_reconstruction_difference` | Stored score minus independently reconstructed score. |
| `preferred_ticker` / `preferred_isin` | Current implementation line from the supplied versioned table. |
| `ii_current_status` / `ii_observation_date` | Current-only ii evidence. |
| `shadow_execution_state` | Confirmed, ii-unchecked, or unresolved state. |
| `rank_2_family` / `rank_3_family` | Audit context only; never substitutes for rank 1. |
| `benchmark_family_id` | `GLOBAL_DEVELOPED_WORLD`. |
| `global_trend_regime`, `volatility_regime`, `dispersion_regime`, `breadth_regime`, `rotation_intensity_regime`, `us_technology_dominance` | Frozen descriptive A3R2 regimes; never filters. |
| `backfill` | Must be `NO`. |
| `orders_or_scheduler` | Must be `NONE`. |

The runner refuses to append a duplicate date, any date at or before the historical cutoff, any date before the tagged prospective boundary, or any date absent from the monthly feature panel.
