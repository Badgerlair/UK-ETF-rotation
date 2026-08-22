from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from edge_research.daily_portfolio import PreparedCloseObservedExitOrders, prepare_daily_market_data


RUNNER_PATH = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "directed"
    / "EDGE-MEAN-REVERSION-20260822-001"
    / "code"
    / "run_qp_parity.py"
)
SPEC = importlib.util.spec_from_file_location("edge_mean_reversion_qp_parity", RUNNER_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_frozen_canonical_configuration() -> None:
    config = runner.strategy_config("LIQ_A")
    parameters = config["signals"]["parameters"]
    assert parameters == {
        "return_window": 3,
        "history_sessions": 1260,
        "minimum_history_sessions": 1260,
        "qp_threshold": 15,
        "trend_sma": 200,
        "liquidity_definition": "LIQ_A",
        "liquidity_window": 20,
    }
    simulation = runner.simulation_config()
    assert simulation["portfolio"]["max_positions"] == 10
    assert simulation["portfolio"]["position_size_pct"] == 10
    assert simulation["execution_model"]["entry_timing"] == "next_open"
    assert simulation["execution_model"]["slippage_bps"] == 10
    assert simulation["execution_model"]["end_of_data_position_policy"] == "leave_open_mark_to_market"


def test_authorised_pit_identity_difference_is_not_a_blocker() -> None:
    pit = pd.DataFrame(
        [
            {
                "snapshot_date": "2025-01-02",
                "liquidity_asof_date": "2024-12-31",
                "ticker": "AAA",
                "issuer_group_id": "I1",
                "liquidity_rank": 1,
                "pit_safe": True,
            },
            {
                "snapshot_date": "2025-02-03",
                "liquidity_asof_date": "2025-01-31",
                "ticker": "BBB",
                "issuer_group_id": "I2",
                "liquidity_rank": 1,
                "pit_safe": True,
            },
        ]
    )
    pit["snapshot_date"] = pd.to_datetime(pit["snapshot_date"])
    pit["liquidity_asof_date"] = pd.to_datetime(pit["liquidity_asof_date"])
    original_files = runner.PIT_FILES
    runner.PIT_FILES = ()
    try:
        evidence = runner.authorised_pit_evidence(pit)
    finally:
        runner.PIT_FILES = original_files
    assert evidence["authorised_causal_integrity_pass"] is True
    assert evidence["canonical_pit_status"] == "AUTHORISED_LAGGED_LIQUIDITY_PIT_TOP500"
    assert evidence["historical_sp500_membership_required"] is False


def test_liquidity_variants_have_frozen_deterministic_ranking() -> None:
    pool = pd.DataFrame(
        [
            {"signal_date": "2025-01-02", "symbol": "AAA", "qp": 12, "dollar_turnover_close": 200, "median_dollar_turnover_20": 100, "reason": "qp"},
            {"signal_date": "2025-01-02", "symbol": "BBB", "qp": 12, "dollar_turnover_close": 100, "median_dollar_turnover_20": 300, "reason": "qp"},
        ]
    )
    assert runner.build_ranked_signals(pool, "LIQ_A")["symbol"].tolist() == ["AAA", "BBB"]
    assert runner.build_ranked_signals(pool, "LIQ_B")["symbol"].tolist() == ["BBB", "AAA"]


def test_terminal_proxy_releases_only_an_existing_position_path() -> None:
    bars = pd.DataFrame(
        [
            {"date": "2026-01-01", "symbol": "AAA", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000},
            {"date": "2026-01-02", "symbol": "AAA", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000},
            {"date": "2026-01-05", "symbol": "BBB", "open": 50.0, "high": 51.0, "low": 49.0, "close": 50.0, "volume": 1000},
        ]
    )
    market = prepare_daily_market_data(bars)
    exits = PreparedCloseObservedExitOrders({}, 0)
    proxy = runner.install_terminal_proxy(market, exits)
    row = proxy.loc[proxy["symbol"].eq("AAA")].iloc[0]
    assert row["settlement_date"] == "2026-01-05"
    assert market.bar_lookup[("2026-01-05", "AAA")].terminal_proxy_only is True


def test_explicit_costs_reconcile_entry_and_exit_once() -> None:
    trades = pd.DataFrame(
        [{
            "quantity": 10.0,
            "entry_reference_price": 100.0,
            "entry_price": 100.1,
            "exit_reference_price": 110.0,
            "exit_price": 109.89,
            "net_pnl": 97.9,
        }]
    )
    explicit = runner.explicit_trade_economics(trades).iloc[0]
    assert explicit["entry_cost"] == pytest.approx(1.0)
    assert explicit["exit_cost"] == pytest.approx(1.1)
    assert explicit["entry_cost"] + explicit["exit_cost"] == pytest.approx(2.1)


def test_frame_comparator_reports_first_semantic_divergence() -> None:
    reference = pd.DataFrame([{"trade_id": "T1", "symbol": "AAA", "quantity": 10.0}])
    platform = pd.DataFrame([{"trade_id": "T1", "symbol": "AAA", "quantity": 11.0}])
    record, first = runner.compare_frames(
        "LIQ_A_trades", platform, reference, key_columns=("trade_id", "symbol")
    )
    assert record["status"] == "FAIL"
    assert first is not None
    assert first["root_cause"] == "POSITION_SIZING"
