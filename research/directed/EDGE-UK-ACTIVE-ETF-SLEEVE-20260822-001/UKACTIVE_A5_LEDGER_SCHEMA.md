# UKACTIVE-A5 append-only ledger schema

CSV and JSONL ledgers are authoritative. `UKACTIVE_A5_CURRENT_STATE.json` and telemetry Parquet are deterministic mirrors. Prior events are never edited; a correction requires a new amendment/warning event.

## UKACTIVE_A5_DECISION_LEDGER.csv

Primary fields: `decision_event_id`, `specification_id`, `signal_date`, `data_cutoff`, `recorded_at_utc`, `prospective_classification`, `on_time_e3_counted`, `expected_execution_date`, `economic_pool`, `signal_id`, `eligible_family_count`, `selected_family_id`, `selected_display_name`, `preferred_ticker`, `preferred_isin`, `issuer`, `listing_currency`, `deepvue_label`, `rs63`, `rs126`, `rs252`, `rank_rs63`, `rank_rs126`, `rank_rs252`, `composite_score`, `rank_2_family`, `rank_3_family`, `rank_4_family`, `rank_5_family`, `top5_json`, `previous_active_holding`, `action`, `implementation_check_status`, `a5a_target_weight`, `a5a_target_notional_gbp`, `a5b_active_target_weight`, `a5b_core_target_weight`, `a5b_active_target_notional_gbp`, `a5b_core_target_notional_gbp`, `a5b_estimated_rebalance_legs`, `benchmark_family_id`, `global_trend_regime`, `volatility_regime`, `dispersion_regime`, `breadth_regime`, `rotation_intensity_regime`, `us_technology_dominance`, `input_eligibility_path`, `input_eligibility_sha256`, `implementation_map_path`, `implementation_map_sha256`, `universe_version`, `source_git_commit`, `freeze_tag`, `backfill`, `orders_or_scheduler`, `warning`.

## UKACTIVE_A5_EXECUTION_LEDGER.csv

Primary fields: `execution_event_id`, `leg_id`, `model_id`, `decision_event_id`, `signal_date`, `execution_date`, `logged_at_utc`, `logging_classification`, `action`, `family_id`, `ticker`, `isin`, `side`, `target_weight`, `target_notional_gbp`, `execution_close`, `execution_close_unit`, `economic_index_gbp`, `notional_traded_gbp`, `friction_cost_gbp`, `fixed_fee_gbp`, `total_cost_gbp`, `post_trade_units`, `post_trade_notional_gbp`, `residual_cash_gbp`, `units_basis`, `implementation_status`, `input_snapshot_path`, `input_snapshot_sha256`, `source_git_commit`, `shadow_only`, `warning`.

## UKACTIVE_A5_POSITION_LEDGER.csv

Primary fields: `position_event_id`, `execution_event_id`, `model_id`, `effective_date`, `family_id`, `target_weight`, `economic_units`, `economic_index_at_execution`, `continuity_segment_id`, `ticker`, `isin`, `implementation_status`, `source_git_commit`, `warning`.

## UKACTIVE_A5_CASH_LEDGER.csv

Primary fields: `cash_event_id`, `execution_event_id`, `model_id`, `effective_date`, `cash_balance_gbp`, `cash_index_at_event`, `cash_weight`, `source_git_commit`, `warning`.

## UKACTIVE_A5_COST_LEDGER.csv

Primary fields: `cost_event_id`, `execution_event_id`, `leg_id`, `model_id`, `date`, `notional_traded_gbp`, `friction_bps`, `friction_cost_gbp`, `fixed_fee_gbp`, `total_cost_gbp`, `source_git_commit`, `warning`.

## UKACTIVE_A5_NAV_HISTORY.csv

Primary fields: `nav_event_id`, `model_id`, `date`, `nav_gbp`, `cumulative_net_return`, `daily_return`, `position_value_gbp`, `cash_value_gbp`, `cash_weight`, `holdings`, `high_water_mark_gbp`, `drawdown`, `cumulative_costs_gbp`, `traded_notional_turnover`, `trade_legs`, `source_input_hash`, `source_git_commit`, `warning`.

## UKACTIVE_A5_BENCHMARK_HISTORY.csv

Primary fields: `nav_event_id`, `model_id`, `date`, `nav_gbp`, `cumulative_net_return`, `daily_return`, `position_value_gbp`, `cash_value_gbp`, `cash_weight`, `holdings`, `high_water_mark_gbp`, `drawdown`, `cumulative_costs_gbp`, `traded_notional_turnover`, `trade_legs`, `source_input_hash`, `source_git_commit`, `warning`.

## UKACTIVE_A5_TELEMETRY_LEDGER.csv

Primary fields: `telemetry_event_id`, `date`, `pool`, `rank_type`, `rank`, `family_id`, `display_name`, `preferred_ticker`, `rs21`, `rs42`, `rs63`, `rs126`, `rs252`, `fast_score`, `slow_score`, `fast_rank`, `slow_rank`, `fast_slow_gap`, `fast_rank_change_1w`, `fast_rank_change_4w`, `relative_price_slope_63`, `leadership_state`, `global_trend_regime`, `volatility_regime`, `dispersion_regime`, `breadth_regime`, `rotation_intensity_regime`, `us_technology_dominance`, `portfolio_change`, `source_git_commit`, `warning`.

## UKACTIVE_A5_OPERATIONAL_WARNINGS.csv

Primary fields: `warning_event_id`, `date`, `warning_type`, `severity`, `related_event_id`, `message`, `evidence`, `recorded_at_utc`, `source_git_commit`, `resolved_status`.

## UKACTIVE_A5_AMENDMENT_LEDGER.csv

Primary fields: `amendment_event_id`, `original_event_id`, `original_ledger`, `reason`, `field_name`, `old_value`, `new_value`, `evidence`, `recorded_at_utc`, `source_git_commit`, `warning`.

## UKACTIVE_A5_RUN_LEDGER.jsonl

One canonical JSON object per evidence-producing invocation, keyed by deterministic `run_event_id`.

## Amendment policy

A material vendor revision appends `DATA_REVISION_ALERT` to the warnings ledger and preserves the original signal, execution and NAV rows. The telemetry CSV is the Git-tracked append-only authority; `UKACTIVE_A5_TELEMETRY_HISTORY.parquet` is its deterministic local mirror because repository policy excludes Parquet bytes.
