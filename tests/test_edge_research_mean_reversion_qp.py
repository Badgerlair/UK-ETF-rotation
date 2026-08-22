from __future__ import annotations

import pandas as pd
import pytest

from edge_research.mean_reversion_qp import (
    ExtremeMoveProbabilityConfig,
    ExtremeMoveProbabilityQP,
    extreme_move_probability,
    prepare_qp_indicators,
)


def _bars(closes: list[float], symbol: str = "AAA", dates: pd.DatetimeIndex | None = None) -> pd.DataFrame:
    dates = dates if dates is not None else pd.bdate_range("2025-01-02", periods=len(closes))
    return pd.DataFrame(
        {
            "date": dates,
            "symbol": symbol,
            "open": closes,
            "high": [value + 1 for value in closes],
            "low": [value - 1 for value in closes],
            "close": closes,
            "volume": [1_000_000 + index * 1000 for index in range(len(closes))],
            "adjusted_close": closes,
            "adjusted_high": [value + 1 for value in closes],
        }
    )


def test_negative_qp_uses_prior_negative_inclusive_tail_only():
    values = pd.Series([-0.01, -0.02, 0.03, -0.04, -0.03])
    qp = extreme_move_probability(values, history_sessions=4, minimum_history_sessions=4)
    assert qp.iloc[-1] == pytest.approx(100 / 3)


def test_positive_qp_uses_prior_positive_inclusive_tail_only():
    values = pd.Series([-0.01, 0.01, 0.03, 0.02, 0.015])
    qp = extreme_move_probability(values, history_sessions=4, minimum_history_sessions=4)
    assert qp.iloc[-1] == pytest.approx(200 / 3)


def test_current_return_is_excluded_and_ties_are_inclusive():
    values = pd.Series([-0.03, -0.03, -0.02, 0.01, -0.03])
    qp = extreme_move_probability(values, history_sessions=4, minimum_history_sessions=4)
    assert qp.iloc[-1] == pytest.approx(200 / 3)


def test_prepare_requires_explicit_adjusted_signal_fields():
    frame = _bars([100, 101, 99])
    with pytest.raises(ValueError, match="adjusted signal"):
        prepare_qp_indicators(frame.drop(columns="adjusted_high"), ExtremeMoveProbabilityConfig(history_sessions=1, minimum_history_sessions=1))


def test_next_session_is_global_calendar_not_next_symbol_bar():
    dates = pd.bdate_range("2025-01-02", periods=3)
    a = _bars([100, 99], "AAA", dates[[0, 2]])
    b = _bars([100, 100, 100], "BBB", dates)
    prepared = prepare_qp_indicators(
        pd.concat([a, b], ignore_index=True),
        ExtremeMoveProbabilityConfig(return_window=1, history_sessions=1, minimum_history_sessions=1, trend_sma=1),
    )
    first_a = prepared[prepared["symbol"].eq("AAA")].iloc[0]
    assert pd.Timestamp(first_a["next_session_date"]) == dates[1]


def test_entry_and_exit_intents_are_strictly_next_open():
    config = {
        "signals": {
            "parameters": {
                "return_window": 1,
                "history_sessions": 3,
                "minimum_history_sessions": 3,
                "qp_threshold": 99.9,
                "trend_sma": 5,
                "liquidity_definition": "LIQ_A",
                "liquidity_window": 2,
            }
        }
    }
    module = ExtremeMoveProbabilityQP()
    prepared = module.prepare_indicators(_bars([80, 82, 84, 86, 88, 120, 115, 110, 112]), config)
    candidates = module.generate_candidates(prepared, config)
    assert not candidates.empty
    assert (pd.to_datetime(candidates["intended_entry_date"]) > pd.to_datetime(candidates["signal_date"])).all()
    assert candidates["intended_entry_timing"].eq("next_open").all()
    exits = module.generate_exit_signals(prepared, config)
    assert not exits.empty
    assert (pd.to_datetime(exits["intended_exit_date"]) > pd.to_datetime(exits["signal_date"])).all()
    assert exits["assumed_fill_time"].eq("Open(t+1)").all()
    assert exits["fill_price_field"].eq("open").all()


def test_liquidity_rank_is_descending_and_ticker_is_tie_break():
    module = ExtremeMoveProbabilityQP()
    candidates = pd.DataFrame(
        [
            {"signal_date": "2025-01-10", "symbol": "BBB", "score": 100.0},
            {"signal_date": "2025-01-10", "symbol": "CCC", "score": 200.0},
            {"signal_date": "2025-01-10", "symbol": "AAA", "score": 100.0},
        ]
    )
    for column in [
        "as_of_date", "strategy_name", "direction", "timeframe", "intended_entry_date",
        "intended_entry_timing", "rank", "close", "reason", "stop_reference",
        "target_reference", "data_warnings",
    ]:
        candidates[column] = ""
    ranked = module.rank_candidates(candidates, {})
    assert ranked["symbol"].tolist() == ["CCC", "AAA", "BBB"]
    assert ranked["rank"].tolist() == [1, 2, 3]

