from __future__ import annotations

import pandas as pd
import pytest

from edge_research.daily_portfolio import DailyPortfolioSimulator


def _config(cost_bps: float = 0.0) -> dict:
    return {
        "strategy": {"name": "mr_qp_p1_platform_replication", "timeframe": "1d", "direction": "long"},
        "portfolio": {
            "initial_cash": 100_000,
            "max_positions": 10,
            "position_size_pct": 10,
            "max_strategy_exposure_pct": 100,
            "max_total_exposure_pct": 100,
            "allow_overlap": False,
            "allow_reentry": True,
            "require_not_held_at_signal": True,
        },
        "execution_model": {
            "mode": "backtest",
            "entry_timing": "next_open",
            "exit_timing": "same_close",
            "slippage_bps": cost_bps,
            "commission_model": "zero",
            "missing_next_open_policy": "carry_to_next_available_open",
            "end_of_data_position_policy": "leave_open_mark_to_market",
        },
        "risk": {
            "initial_stop": {"type": "none", "value": None},
            "trailing_stop": {"type": "none", "value": None},
            "time_stop_bars": None,
        },
    }


def _order(signal_date: str = "2026-01-02", entry_date: str = "2026-01-05") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "order_id": "P1-1",
                "strategy_name": "mr_qp_p1_platform_replication",
                "symbol": "AAA",
                "direction": "long",
                "signal_date": signal_date,
                "intended_entry_date": entry_date,
                "stop_price": pd.NA,
                "target_price": pd.NA,
                "rank": 1,
            }
        ]
    )


def _exit(signal_date: str = "2026-01-05", exit_date: str = "2026-01-06") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "exit_order_id": "X-1",
                "strategy_name": "mr_qp_p1_platform_replication",
                "symbol": "AAA",
                "signal_date": signal_date,
                "intended_exit_date": exit_date,
                "reason": "adjusted_close_above_previous_adjusted_high",
            }
        ]
    )


def _bars() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"date": "2026-01-02", "symbol": "AAA", "open": 90.0, "high": 96.0, "low": 89.0, "close": 95.0, "volume": 1_000},
            {"date": "2026-01-05", "symbol": "AAA", "open": 100.0, "high": 106.0, "low": 99.0, "close": 105.0, "volume": 1_000},
            {"date": "2026-01-06", "symbol": "AAA", "open": 110.0, "high": 112.0, "low": 108.0, "close": 111.0, "volume": 1_000},
        ]
    )


def test_close_signal_cannot_fill_same_session_or_see_same_open() -> None:
    invalid = _order(signal_date="2026-01-02", entry_date="2026-01-02")
    with pytest.raises(ValueError, match="strictly after"):
        DailyPortfolioSimulator(_config()).simulate(invalid, _bars())


def test_existing_same_close_mode_still_coexists_with_next_open_capability() -> None:
    config = _config()
    config["execution_model"]["entry_timing"] = "same_close"
    config["execution_model"]["end_of_data_position_policy"] = "close_same_close"
    order = _order(signal_date="2026-01-02", entry_date="2026-01-02")
    result = DailyPortfolioSimulator(config).simulate(order, _bars())
    trade = result.trades.iloc[0]
    assert trade["entry_date"] == "2026-01-02"
    assert trade["entry_reference_price"] == pytest.approx(95.0)


def test_next_open_sizing_cannot_use_the_future_session_close() -> None:
    orders = pd.concat(
        [
            _order(signal_date="2026-01-02", entry_date="2026-01-05").assign(symbol="AAA", order_id="P1-A"),
            _order(signal_date="2026-01-05", entry_date="2026-01-06").assign(symbol="BBB", order_id="P1-B"),
        ],
        ignore_index=True,
    )

    def bars(aaa_close: float) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"date": "2026-01-02", "symbol": "AAA", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1_000},
                {"date": "2026-01-02", "symbol": "BBB", "open": 50.0, "high": 51.0, "low": 49.0, "close": 50.0, "volume": 1_000},
                {"date": "2026-01-05", "symbol": "AAA", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1_000},
                {"date": "2026-01-05", "symbol": "BBB", "open": 50.0, "high": 51.0, "low": 49.0, "close": 50.0, "volume": 1_000},
                {"date": "2026-01-06", "symbol": "AAA", "open": 100.0, "high": max(101.0, aaa_close), "low": min(99.0, aaa_close), "close": aaa_close, "volume": 1_000},
                {"date": "2026-01-06", "symbol": "BBB", "open": 50.0, "high": 51.0, "low": 49.0, "close": 50.0, "volume": 1_000},
            ]
        )

    close_at_end_config = _config()
    close_at_end_config["execution_model"]["end_of_data_position_policy"] = "close_same_close"
    low_close = DailyPortfolioSimulator(close_at_end_config).simulate(orders, bars(10.0))
    high_close = DailyPortfolioSimulator(close_at_end_config).simulate(orders, bars(10_000.0))
    low_quantity = float(low_close.trades.loc[low_close.trades["symbol"].eq("BBB"), "quantity"].iloc[0])
    high_quantity = float(high_close.trades.loc[high_close.trades["symbol"].eq("BBB"), "quantity"].iloc[0])
    assert low_quantity == pytest.approx(200.0)
    assert high_quantity == pytest.approx(low_quantity)


def test_qp_end_of_data_marks_open_positions_without_fabricating_same_close_exit() -> None:
    result = DailyPortfolioSimulator(_config()).simulate(_order(), _bars())
    assert result.trades.empty
    assert len(result.open_positions) == 1
    assert result.open_positions.iloc[0]["symbol"] == "AAA"
    assert int(result.daily_equity.iloc[-1]["number_open_positions"]) == 1


def test_entry_and_exit_fill_exactly_at_next_session_open_across_weekend() -> None:
    result = DailyPortfolioSimulator(_config()).simulate(_order(), _bars(), exit_orders=_exit())
    trade = result.trades.iloc[0]
    assert trade["entry_date"] == "2026-01-05"
    assert trade["entry_reference_price"] == pytest.approx(100.0)
    assert trade["exit_date"] == "2026-01-06"
    assert trade["exit_reference_price"] == pytest.approx(110.0)


def test_cash_and_position_state_are_unchanged_before_fill() -> None:
    result = DailyPortfolioSimulator(_config()).simulate(_order(), _bars(), exit_orders=_exit())
    signal_state = result.daily_equity.set_index("date").loc["2026-01-02"]
    fill_state = result.daily_equity.set_index("date").loc["2026-01-05"]
    assert signal_state["cash"] == pytest.approx(100_000.0)
    assert int(signal_state["number_open_positions"]) == 0
    assert fill_state["cash"] == pytest.approx(100_000.0)
    assert int(fill_state["number_open_positions"]) == 1


def test_missing_intended_bar_carries_deterministically_to_next_available_open() -> None:
    bars = _bars()
    other = pd.DataFrame(
        [{"date": "2026-01-05", "symbol": "BBB", "open": 50.0, "high": 51.0, "low": 49.0, "close": 50.0, "volume": 1_000}]
    )
    bars = pd.concat([bars[bars["date"].ne("2026-01-05")], other], ignore_index=True)
    delayed_exit = _exit(signal_date="2026-01-06", exit_date="2026-01-07")
    bars = pd.concat(
        [bars, pd.DataFrame([{"date": "2026-01-07", "symbol": "AAA", "open": 112.0, "high": 113.0, "low": 111.0, "close": 112.0, "volume": 1_000}])],
        ignore_index=True,
    )
    result = DailyPortfolioSimulator(_config()).simulate(_order(), bars, exit_orders=delayed_exit)
    trade = result.trades.iloc[0]
    assert trade["entry_date"] == "2026-01-06"
    assert trade["entry_reference_price"] == pytest.approx(110.0)
    assert "next_open_entry_carried" in set(result.diagnostics["event_type"])


def test_per_leg_cost_is_applied_once_at_actual_next_open_fills() -> None:
    result = DailyPortfolioSimulator(_config(cost_bps=10)).simulate(_order(), _bars(), exit_orders=_exit())
    trade = result.trades.iloc[0]
    quantity = float(trade["quantity"])
    expected_gross = (110.0 - 100.0) * quantity
    expected_slippage = (100.0 + 110.0) * quantity * 0.001
    assert trade["gross_pnl"] == pytest.approx(expected_gross)
    assert trade["slippage"] == pytest.approx(expected_slippage)
    assert trade["net_pnl"] == pytest.approx(expected_gross - expected_slippage)


def test_split_between_entry_signal_and_fill_uses_post_split_raw_open_once() -> None:
    bars = _bars()
    bars.loc[bars["date"].eq("2026-01-05"), ["open", "high", "low", "close"]] = [50.0, 53.0, 49.0, 52.5]
    bars.loc[bars["date"].eq("2026-01-06"), ["open", "high", "low", "close"]] = [55.0, 56.0, 54.0, 55.5]
    bars["split_factor_at_open"] = [1.0, 2.0, 1.0]
    result = DailyPortfolioSimulator(_config()).simulate(_order(), bars, exit_orders=_exit())
    trade = result.trades.iloc[0]
    assert trade["entry_reference_price"] == pytest.approx(50.0)
    assert trade["quantity"] == pytest.approx(200.0)
    assert trade["exit_reference_price"] == pytest.approx(55.0)
    assert trade["gross_pnl"] == pytest.approx(1_000.0)


def test_dividend_cash_event_is_accrued_without_changing_raw_fill_price() -> None:
    bars = pd.DataFrame(
        [
            {"date": "2026-01-02", "symbol": "AAA", "open": 95.0, "high": 101.0, "low": 94.0, "close": 100.0, "volume": 1_000, "cash_dividend_per_share": 0.0},
            {"date": "2026-01-05", "symbol": "AAA", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1_000, "cash_dividend_per_share": 0.0},
            {"date": "2026-01-06", "symbol": "AAA", "open": 99.0, "high": 100.0, "low": 98.0, "close": 99.0, "volume": 1_000, "cash_dividend_per_share": 1.0},
            {"date": "2026-01-07", "symbol": "AAA", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1_000, "cash_dividend_per_share": 0.0},
        ]
    )
    exit_order = _exit(signal_date="2026-01-06", exit_date="2026-01-07")
    result = DailyPortfolioSimulator(_config()).simulate(_order(), bars, exit_orders=exit_order)
    trade = result.trades.iloc[0]
    assert trade["entry_reference_price"] == pytest.approx(100.0)
    assert trade["exit_reference_price"] == pytest.approx(100.0)
    assert trade["dividend_income"] == pytest.approx(100.0)
    assert trade["gross_pnl"] == pytest.approx(100.0)


def test_split_between_exit_signal_and_fill_adjusts_holding_before_open() -> None:
    bars = _bars()
    bars.loc[bars["date"].eq("2026-01-06"), ["open", "high", "low", "close"]] = [52.5, 56.0, 51.0, 55.5]
    bars["split_factor_at_open"] = [1.0, 1.0, 2.0]
    result = DailyPortfolioSimulator(_config()).simulate(_order(), bars, exit_orders=_exit())
    trade = result.trades.iloc[0]
    assert trade["quantity"] == pytest.approx(200.0)
    assert trade["entry_reference_price"] == pytest.approx(50.0)
    assert trade["exit_reference_price"] == pytest.approx(52.5)
    assert trade["gross_pnl"] == pytest.approx(500.0)
    assert "position_split_adjustment" in set(result.diagnostics["event_type"])

