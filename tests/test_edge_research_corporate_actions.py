from __future__ import annotations

import pandas as pd
import pytest

from edge_research.corporate_actions import apply_split_event_corrections, build_adjusted_signal_panel


def _bars(prices: list[float]) -> pd.DataFrame:
    dates = pd.bdate_range("2026-01-02", periods=len(prices))
    return pd.DataFrame(
        {
            "date": dates,
            "symbol": "AAA",
            "open": prices,
            "high": [value * 1.01 for value in prices],
            "low": [value * 0.99 for value in prices],
            "close": prices,
            "volume": 1_000.0,
        }
    )


def test_ordinary_session_keeps_raw_fills_and_signal_prices_identical() -> None:
    result = build_adjusted_signal_panel(_bars([100.0, 101.0, 102.0]))
    assert result.panel["open"].tolist() == [100.0, 101.0, 102.0]
    assert result.panel["adjusted_close"].tolist() == [100.0, 101.0, 102.0]
    assert result.diagnostics.empty


def test_forward_split_back_adjusts_signals_but_preserves_raw_open() -> None:
    bars = _bars([100.0, 50.0, 51.0])
    splits = pd.DataFrame([{"ticker": "AAA", "execution_date": bars.iloc[1]["date"], "split_factor": 2.0}])
    panel = build_adjusted_signal_panel(bars, splits).panel
    assert panel.loc[0, "adjusted_close"] == pytest.approx(50.0)
    assert panel.loc[1, "adjusted_close"] == pytest.approx(50.0)
    assert panel.loc[1, "open"] == pytest.approx(50.0)
    assert panel.loc[1, "split_factor_at_open"] == pytest.approx(2.0)


def test_reverse_split_is_supported_on_the_same_bridge() -> None:
    bars = _bars([10.0, 50.0, 52.0])
    splits = pd.DataFrame([{"ticker": "AAA", "execution_date": bars.iloc[1]["date"], "split_factor": 0.2}])
    panel = build_adjusted_signal_panel(bars, splits).panel
    assert panel.loc[0, "adjusted_close"] == pytest.approx(50.0)
    assert panel.loc[1, "adjusted_close"] == pytest.approx(50.0)
    assert panel.loc[1, "split_factor_at_open"] == pytest.approx(0.2)


def test_dividend_adjustment_creates_total_return_continuity_without_changing_fill() -> None:
    bars = _bars([100.0, 99.0, 100.0])
    dividends = pd.DataFrame([{"ticker": "AAA", "ex_dividend_date": bars.iloc[1]["date"], "cash_amount": 1.0}])
    panel = build_adjusted_signal_panel(bars, dividend_events=dividends).panel
    assert panel.loc[0, "adjusted_close"] == pytest.approx(99.0)
    assert panel.loc[1, "adjusted_close"] == pytest.approx(99.0)
    assert panel.loc[1, "open"] == pytest.approx(99.0)
    assert panel.loc[1, "cash_dividend_per_share"] == pytest.approx(1.0)


def test_missing_split_factor_is_flagged_and_not_fabricated() -> None:
    splits = pd.DataFrame([{"ticker": "AAA", "execution_date": "2026-01-05", "split_factor": None}])
    result = build_adjusted_signal_panel(_bars([100.0, 50.0]), splits)
    assert result.panel["split_factor_at_open"].eq(1.0).all()
    assert "missing_split_adjustment_factor" in set(result.diagnostics["event_type"])


def test_later_split_does_not_change_pre_event_scale_invariant_return_information() -> None:
    bars = _bars([100.0, 102.0, 101.0, 50.5])
    split_date = bars.iloc[3]["date"]
    adjusted = build_adjusted_signal_panel(
        bars,
        pd.DataFrame([{"ticker": "AAA", "execution_date": split_date, "split_factor": 2.0}]),
    ).panel
    raw_pre_event_return = bars.loc[2, "close"] / bars.loc[0, "close"] - 1.0
    adjusted_pre_event_return = adjusted.loc[2, "adjusted_close"] / adjusted.loc[0, "adjusted_close"] - 1.0
    assert adjusted_pre_event_return == pytest.approx(raw_pre_event_return)


def test_source_bound_split_corrections_replace_hbi_and_add_wll() -> None:
    archive = pd.DataFrame(
        [
            {"ticker": "HBI", "execution_date": "2015-02-05", "split_factor": 4.0},
        ]
    )
    corrections = pd.DataFrame(
        [
            {
                "correction_id": "HBI-20150304",
                "operation": "REPLACE",
                "ticker": "HBI",
                "existing_execution_date": "2015-02-05",
                "corrected_execution_date": "2015-03-04",
                "split_factor": 4.0,
                "source": "SEC-HBI",
            },
            {
                "correction_id": "WLL-20171109",
                "operation": "ADD",
                "ticker": "WLL",
                "existing_execution_date": None,
                "corrected_execution_date": "2017-11-09",
                "split_factor": 0.25,
                "source": "SEC-WLL",
            },
        ]
    )
    corrected, audit = apply_split_event_corrections(archive, corrections)
    observed = {
        (row.ticker, str(pd.Timestamp(row.execution_date).date())): row.split_factor
        for row in corrected.itertuples(index=False)
    }
    assert ("HBI", "2015-02-05") not in observed
    assert observed[("HBI", "2015-03-04")] == pytest.approx(4.0)
    assert observed[("WLL", "2017-11-09")] == pytest.approx(0.25)
    assert audit["status"].eq("APPLIED").all()

