from __future__ import annotations

import pandas as pd
import pytest

from edge_research.monthly_long_short import (
    IdentityContinuityError,
    SignedMonthlyRebalancer,
    prepare_signed_market_data,
)


def _events(entry: str = "2026-01-05", exit_date: str = "2026-02-02") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "event_id": "E1",
                "timing_variant": "A1_CANONICAL",
                "formation_date": "2026-01-02",
                "rebalance_date": entry,
                "event_type": "FORMATION_REBALANCE",
            },
            {
                "event_id": "E2",
                "timing_variant": "A1_CANONICAL",
                "formation_date": "2026-01-02",
                "rebalance_date": exit_date,
                "event_type": "LIQUIDATE",
            },
        ]
    )


def _targets(entry: str = "2026-01-05") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"rebalance_date": entry, "symbol": "AAA", "portfolio_leg": "LONG", "target_weight": 1.0},
            {"rebalance_date": entry, "symbol": "BBB", "portfolio_leg": "SHORT", "target_weight": -1.0},
        ]
    )


def _bars() -> pd.DataFrame:
    rows = []
    for date, aaa_open, aaa_close, bbb_open, bbb_close in (
        ("2026-01-02", 100.0, 100.0, 50.0, 50.0),
        ("2026-01-05", 100.0, 100.0, 50.0, 50.0),
        ("2026-02-02", 110.0, 110.0, 45.0, 45.0),
    ):
        rows.extend(
            [
                {"date": date, "symbol": "AAA", "open": aaa_open, "close": aaa_close, "split_factor_at_open": 1.0},
                {"date": date, "symbol": "BBB", "open": bbb_open, "close": bbb_close, "split_factor_at_open": 1.0},
            ]
        )
    return pd.DataFrame(rows)


def test_signed_books_fill_raw_open_and_charge_each_delta_once() -> None:
    result = SignedMonthlyRebalancer(initial_equity=100_000, cost_bps_per_leg=10).simulate(
        _targets(), _events(), _bars()
    )
    assert len(result.executions) == 4
    assert result.executions["cost"].sum() == pytest.approx(400.0)
    assert result.daily_equity.iloc[-1]["equity"] == pytest.approx(119_600.0)
    entry = result.executions[result.executions["intended_rebalance_date"].eq("2026-01-05")]
    assert entry.loc[entry["symbol"].eq("AAA"), "target_quantity"].iloc[0] == pytest.approx(1_000.0)
    assert entry.loc[entry["symbol"].eq("BBB"), "target_quantity"].iloc[0] == pytest.approx(-2_000.0)
    assert result.open_positions.empty
    assert result.pending_targets.empty


def test_same_close_target_is_rejected_as_noncausal() -> None:
    events = _events(entry="2026-01-02")
    with pytest.raises(ValueError, match="strictly after"):
        SignedMonthlyRebalancer().simulate(_targets(entry="2026-01-02"), events, _bars())


def test_split_adjusts_existing_signed_quantity_before_raw_open_exit() -> None:
    bars = _bars()
    mask = (bars["date"].eq("2026-02-02")) & bars["symbol"].eq("AAA")
    bars.loc[mask, ["open", "close", "split_factor_at_open"]] = [55.0, 55.0, 2.0]
    long_target = _targets().loc[lambda frame: frame["symbol"].eq("AAA")]
    result = SignedMonthlyRebalancer(initial_equity=100_000, cost_bps_per_leg=0).simulate(
        long_target, _events(), bars
    )
    exit_fill = result.executions.loc[result.executions["transition"].eq("CLOSE_LONG")].iloc[0]
    assert exit_fill["old_quantity"] == pytest.approx(2_000.0)
    assert exit_fill["fill_raw_open"] == pytest.approx(55.0)
    assert result.daily_equity.iloc[-1]["equity"] == pytest.approx(110_000.0)


def test_missing_intended_open_carries_fixed_notional_to_next_session() -> None:
    bars = _bars()
    bars = bars.loc[~((bars["date"].eq("2026-01-05")) & bars["symbol"].eq("AAA"))].copy()
    bars = pd.concat(
        [
            bars,
            pd.DataFrame(
                [
                    {"date": "2026-01-06", "symbol": "AAA", "open": 80.0, "close": 80.0, "split_factor_at_open": 1.0},
                    {"date": "2026-01-06", "symbol": "BBB", "open": 50.0, "close": 50.0, "split_factor_at_open": 1.0},
                ]
            ),
        ],
        ignore_index=True,
    )
    calendar = pd.DatetimeIndex(["2026-01-02", "2026-01-05", "2026-01-06", "2026-02-02"])
    prepared = prepare_signed_market_data(bars, calendar=calendar)
    result = SignedMonthlyRebalancer(initial_equity=100_000, cost_bps_per_leg=0).simulate(_targets(), _events(), prepared)
    fill = result.executions.loc[(result.executions["symbol"].eq("AAA")) & result.executions["transition"].eq("OPEN_LONG")].iloc[0]
    assert fill["fill_date"] == "2026-01-06"
    assert fill["target_notional"] == pytest.approx(100_000.0)
    assert fill["target_quantity"] == pytest.approx(1_250.0)
    assert fill["carry_sessions"] == 1


def test_target_quantity_cannot_depend_on_same_session_close() -> None:
    low = _bars()
    high = _bars()
    high.loc[(high["date"].eq("2026-01-05")) & high["symbol"].eq("AAA"), "close"] = 10_000.0
    simulator = SignedMonthlyRebalancer(initial_equity=100_000, cost_bps_per_leg=0)
    low_result = simulator.simulate(_targets(), _events(), low)
    high_result = simulator.simulate(_targets(), _events(), high)
    low_quantity = low_result.executions.loc[
        (low_result.executions["symbol"].eq("AAA")) & low_result.executions["transition"].eq("OPEN_LONG"), "target_quantity"
    ].iloc[0]
    high_quantity = high_result.executions.loc[
        (high_result.executions["symbol"].eq("AAA")) & high_result.executions["transition"].eq("OPEN_LONG"), "target_quantity"
    ].iloc[0]
    assert high_quantity == pytest.approx(low_quantity)


def test_terminal_proxy_settles_holding_but_cannot_open_one() -> None:
    bars = _bars()
    terminal = pd.DataFrame(
        [
            {
                "date": "2026-01-06",
                "symbol": "AAA",
                "open": 95.0,
                "close": 95.0,
                "split_factor_at_open": 1.0,
                "terminal_proxy_only": True,
            }
        ]
    )
    bars = pd.concat([bars, terminal], ignore_index=True)
    calendar = pd.DatetimeIndex(["2026-01-02", "2026-01-05", "2026-01-06", "2026-02-02"])
    result = SignedMonthlyRebalancer(initial_equity=100_000, cost_bps_per_leg=0).simulate(
        _targets().loc[lambda frame: frame["symbol"].eq("AAA")],
        _events(),
        prepare_signed_market_data(bars, calendar=calendar),
    )
    terminal_fill = result.executions.loc[result.executions["terminal_proxy_fill"]].iloc[0]
    assert terminal_fill["transition"] == "CLOSE_LONG"
    assert terminal_fill["fill_raw_open"] == pytest.approx(95.0)
    assert "terminal_proxy_settlement" in set(result.diagnostics["event_type"])


def test_monthly_position_cannot_scan_unbounded_for_reused_ticker() -> None:
    bars = _bars().loc[lambda frame: ~((frame["symbol"].eq("AAA")) & frame["date"].eq("2026-02-02"))]
    calendar = pd.bdate_range("2026-01-02", "2026-02-20")
    with pytest.raises(IdentityContinuityError, match="TERMINAL_OR_IDENTITY_EVENT_REQUIRES_RESOLUTION"):
        SignedMonthlyRebalancer(
            initial_equity=100_000,
            cost_bps_per_leg=0,
            maximum_carry_sessions=20,
        ).simulate(
            _targets().loc[lambda frame: frame["symbol"].eq("AAA")],
            _events(),
            prepare_signed_market_data(bars, calendar=calendar),
        )
