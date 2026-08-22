from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from edge_research.mean_reversion_residual import (
    attach_forward_open_returns,
    build_execution_schedule,
    compute_residual_signals,
    load_french_monthly_factors,
    newey_west_mean_test,
)


def test_french_parser_reads_only_monthly_yyyymm_rows_and_converts_percent(tmp_path) -> None:
    source = tmp_path / "factors.csv"
    source.write_text(
        "header\n,Mkt-RF,SMB,HML,RF\n202501, 1.00, -2.00, 3.00, 0.10\n202502, 2.00, 1.00, -1.00, 0.20\n Annual Factors:\n2025, 10, 20, 30, 1\n",
        encoding="utf-8",
    )
    factors = load_french_monthly_factors(source)
    assert factors["month"].astype(str).tolist() == ["2025-01", "2025-02"]
    assert factors.iloc[0]["mkt_rf"] == pytest.approx(0.01)
    assert factors.iloc[0]["rf"] == pytest.approx(0.001)


def _residual_fixture() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    months = pd.period_range("2023-01", periods=36, freq="M")
    factor_index = np.arange(36, dtype=float)
    factors = pd.DataFrame(
        {
            "month": months,
            "mkt_rf": np.sin(factor_index / 4.0) * 0.02,
            "smb": np.cos(factor_index / 5.0) * 0.01,
            "hml": ((factor_index % 7) - 3.0) * 0.003,
            "rf": 0.001,
        }
    )
    rng = np.random.default_rng(27)
    rows: list[dict] = []
    symbols = [f"S{index:02d}" for index in range(10)]
    shocks = np.linspace(-0.12, 0.12, len(symbols))
    for symbol, shock in zip(symbols, shocks):
        noise = rng.normal(0.0, 0.006, len(months))
        noise[-1] += shock
        returns = 0.002 + 1.1 * factors["mkt_rf"] + 0.3 * factors["smb"] - 0.2 * factors["hml"] + factors["rf"] + noise
        for month, value in zip(months, returns):
            rows.append(
                {
                    "month": month,
                    "formation_date": month.to_timestamp("M"),
                    "symbol": symbol,
                    "raw_formation_close": 20.0,
                    "adjusted_formation_close": 20.0,
                    "monthly_price_return": value,
                }
            )
    pit = pd.DataFrame(
        {
            "ticker": symbols,
            "snapshot_date": pd.Timestamp("2025-12-01"),
            "liquidity_rank": np.arange(1, 11),
            "type": "CS",
            "market": "stocks",
            "locale": "us",
            "currency_name": "usd",
            "is_primary_trading_ticker": True,
        }
    )
    return pd.DataFrame(rows), factors, pit


def test_ff3_signal_uses_36_months_and_selects_source_quintiles() -> None:
    monthly, factors, pit = _residual_fixture()
    result = compute_residual_signals(monthly, factors, pit)
    signals = result.signals
    assert signals["formation_month"].unique().tolist() == ["2025-12"]
    assert signals["regression_observations"].eq(36).all()
    assert signals["portfolio_leg"].eq("LONG").sum() == 2
    assert signals["portfolio_leg"].eq("SHORT").sum() == 2
    assert signals.loc[signals["portfolio_leg"].eq("LONG"), "target_weight"].sum() == pytest.approx(1.0)
    assert signals.loc[signals["portfolio_leg"].eq("SHORT"), "target_weight"].sum() == pytest.approx(-1.0)
    assert signals.iloc[0]["resid_z"] < signals.iloc[-1]["resid_z"]


def test_execution_schedule_distinguishes_first_open_and_skip_one_session() -> None:
    monthly, factors, pit = _residual_fixture()
    signals = compute_residual_signals(monthly, factors, pit).signals
    calendar = pd.DatetimeIndex(["2025-12-31", "2026-01-02", "2026-01-05", "2026-02-02", "2026-02-03"])
    canonical = build_execution_schedule(signals, calendar, "A1_CANONICAL")
    skip = build_execution_schedule(signals, calendar, "A1_SKIP1")
    assert canonical.targets["rebalance_date"].iloc[0] == pd.Timestamp("2026-01-02")
    assert canonical.signals["intended_exit_date"].iloc[0] == pd.Timestamp("2026-02-02")
    assert skip.targets["rebalance_date"].iloc[0] == pd.Timestamp("2026-01-05")
    assert skip.signals["intended_exit_date"].iloc[0] == pd.Timestamp("2026-02-03")


def test_forward_raw_open_return_applies_intervening_split_once() -> None:
    signals = pd.DataFrame(
        [
            {
                "symbol": "AAA",
                "intended_entry_date": "2026-01-05",
                "intended_exit_date": "2026-02-02",
            }
        ]
    )
    market = pd.DataFrame(
        [
            {"date": "2026-01-05", "symbol": "AAA", "open": 100.0, "split_factor_at_open": 1.0},
            {"date": "2026-01-20", "symbol": "AAA", "open": 50.0, "split_factor_at_open": 2.0},
            {"date": "2026-02-02", "symbol": "AAA", "open": 55.0, "split_factor_at_open": 1.0},
        ]
    )
    outcome = attach_forward_open_returns(
        signals,
        market,
        calendar=pd.DatetimeIndex(["2026-01-05", "2026-01-20", "2026-02-02"]),
    ).iloc[0]
    assert outcome["intervening_split_factor"] == pytest.approx(2.0)
    assert outcome["forward_open_return"] == pytest.approx(0.10)


def test_forward_outcome_flags_cross_month_ticker_gap_as_unresolved_identity() -> None:
    signals = pd.DataFrame(
        [
            {
                "symbol": "OLD",
                "intended_entry_date": "2011-01-03",
                "intended_exit_date": "2011-02-01",
            }
        ]
    )
    market = pd.DataFrame(
        [
            {"date": "2011-01-03", "symbol": "OLD", "open": 63.15, "split_factor_at_open": 1.0},
            {"date": "2011-01-27", "symbol": "OLD", "open": 63.48, "split_factor_at_open": 1.0},
            {"date": "2026-02-11", "symbol": "OLD", "open": 24.92, "split_factor_at_open": 1.0},
        ]
    )
    calendar = pd.bdate_range("2011-01-03", "2026-02-11")
    outcome = attach_forward_open_returns(signals, market, calendar=calendar).iloc[0]
    assert bool(outcome["exit_month_boundary_breach"])
    assert bool(outcome["security_identity_continuity_unresolved"])
    assert outcome["exit_carry_sessions"] > 3_000


def test_forward_outcome_uses_explicit_terminal_bound_before_scheduled_exit() -> None:
    signals = pd.DataFrame(
        [{"symbol": "OLD", "intended_entry_date": "2011-01-03", "intended_exit_date": "2011-02-01"}]
    )
    market = pd.DataFrame(
        [
            {"date": "2011-01-03", "symbol": "OLD", "open": 63.15, "split_factor_at_open": 1.0},
            {"date": "2011-01-28", "symbol": "OLD", "open": 63.50, "split_factor_at_open": 1.0, "terminal_proxy_only": True},
        ]
    )
    outcome = attach_forward_open_returns(
        signals,
        market,
        calendar=pd.bdate_range("2011-01-03", "2011-02-01"),
    ).iloc[0]
    assert outcome["actual_exit_date"] == pd.Timestamp("2011-01-28")
    assert outcome["forward_open_return"] == pytest.approx(63.50 / 63.15 - 1.0)
    assert bool(outcome["terminal_proxy_exit"])
    assert not bool(outcome["security_identity_continuity_unresolved"])


def test_newey_west_mean_test_is_deterministic_and_directional() -> None:
    positive = newey_west_mean_test([0.01, 0.02, 0.01, 0.03, 0.02], lags=1)
    negative = newey_west_mean_test([-0.01, -0.02, -0.01, -0.03, -0.02], lags=1)
    assert positive["mean"] == pytest.approx(0.018)
    assert positive["t_stat"] > 0
    assert negative["t_stat"] == pytest.approx(-positive["t_stat"])
