CANDIDATE_COLUMNS = [
    "as_of_date", "symbol", "strategy_name", "direction", "timeframe", "signal_date",
    "intended_entry_date", "intended_entry_timing", "rank", "score", "close", "reason",
    "stop_reference", "target_reference", "data_warnings",
]

ORDER_COLUMNS = [
    "order_id", "strategy_name", "symbol", "asset_class", "timeframe", "direction", "signal_date",
    "intended_entry_date", "order_type", "entry_reference_price", "stop_price", "target_price",
    "sizing_model", "status", "notes",
]

FORWARD_SIGNAL_COLUMNS = [
    "signal_id", "generated_at", "strategy_name", "symbol", "asset_class", "timeframe", "direction",
    "signal_date", "intended_entry_time", "intended_entry_type", "entry_reference_price", "stop_price",
    "target_price", "position_size_model", "max_risk_amount", "order_type_placeholder", "broker_status", "notes",
]

TRADE_COLUMNS = [
    "trade_id", "strategy_name", "symbol", "direction", "entry_signal_date", "entry_date",
    "entry_price", "exit_date", "exit_price", "exit_reason", "quantity", "gross_pnl",
    "commission", "slippage", "net_pnl", "R", "bars_held", "initial_stop",
    "final_stop", "target_price", "notes", "entry_reference_price",
    "exit_reference_price", "dividend_income",
]

EXIT_ORDER_COLUMNS = [
    "exit_order_id", "strategy_name", "symbol", "signal_date",
    "signal_observation_time", "earliest_information_availability",
    "order_submission_time", "intended_exit_date", "order_type",
    "assumed_fill_time", "fill_price_field", "reason", "notes",
]

DAILY_EQUITY_COLUMNS = [
    "date", "cash", "realised_pnl", "unrealised_pnl", "equity", "gross_exposure",
    "net_exposure", "number_open_positions", "drawdown", "daily_return",
]

DIAGNOSTIC_COLUMNS = ["date", "strategy_name", "symbol", "event_type", "severity", "message"]

REJECTED_ORDER_COLUMNS = [
    "date", "order_id", "strategy_name", "symbol", "direction", "signal_date",
    "intended_entry_date", "rank", "reason", "projected_notional", "current_equity",
    "active_exposure_cap_pct",
]

