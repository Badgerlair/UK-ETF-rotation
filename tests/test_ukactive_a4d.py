"""Correctness controls for the separately registered UKACTIVE-A4D stage."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


PROGRAMME_ROOT = Path(__file__).resolve().parents[1] / "research" / "directed" / "EDGE-UK-ACTIVE-ETF-SLEEVE-20260822-001"
sys.path.insert(0, str(PROGRAMME_ROOT / "code"))

import ukactive_a4d_core as a4d  # noqa: E402


@pytest.fixture(scope="module")
def data() -> a4d.A4DData:
    return a4d.load_data()


def test_universe_and_identity_are_frozen(data: a4d.A4DData) -> None:
    assert len(data.members) == 27
    assert not data.daily_features[["date", "economic_exposure_family_id"]].duplicated().any()
    assert set(data.members) == set(data.base.members)


def test_m1_and_m2_exact_frozen_weights(data: a4d.A4DData) -> None:
    sample = data.daily_features.dropna(subset=["M1_EQUAL_5H", "M2_INTERMEDIATE_5H"]).sample(250, random_state=42)
    expected_m1 = sample[[f"RANK_RS_{h}" for h in a4d.HORIZONS]].mean(axis=1)
    m2 = data.policy["signals"]["M2_INTERMEDIATE_5H"]
    expected_m2 = sum(float(m2[f"RS_{h}"]) * sample[f"RANK_RS_{h}"] for h in a4d.HORIZONS)
    np.testing.assert_allclose(sample["M1_EQUAL_5H"], expected_m1, atol=1e-12)
    np.testing.assert_allclose(sample["M2_INTERMEDIATE_5H"], expected_m2, atol=1e-12)


def test_structural_deterioration_is_bounded_and_current_only(data: a4d.A4DData) -> None:
    frame = data.daily_features.dropna(subset=["M3_STRUCTURAL_DETERIORATION"])
    assert frame["M3_STRUCTURAL_DETERIORATION"].between(0.0, 1.0).all()
    policy = data.policy["signals"]["M3_STRUCTURAL_DETERIORATION"]
    gap = frame["FAST_LEVEL"] - frame["STRUCTURAL_LEVEL"]
    rebuilt = (
        frame["STRUCTURAL_LEVEL"]
        + float(policy["acceleration_coefficient"]) * gap.clip(lower=0)
        - float(policy["deterioration_penalty_coefficient"]) * (-gap).clip(lower=0)
    ).clip(*policy["clip"])
    np.testing.assert_allclose(frame["M3_STRUCTURAL_DETERIORATION"], rebuilt, atol=1e-12)


def test_dynamic_point_in_time_targets_and_common_chain_start(data: a4d.A4DData) -> None:
    targets, records = a4d.target_weights(data, signal_id="M1_EQUAL_5H", breadth=6, frequency="WEEKLY")
    assert min(targets) >= pd.Timestamp(data.policy["windows"]["COMMON_CAUSAL_CHAIN_START"])
    features = data.daily_features.set_index(["date", "economic_exposure_family_id"])
    for row in records.iloc[:: max(len(records) // 20, 1)].itertuples(index=False):
        for family in row.selected_families_rank_order.split(";"):
            assert pd.notna(features.loc[(row.review_date, family), "M1_EQUAL_5H"])


def test_next_session_execution_and_no_leverage(data: a4d.A4DData) -> None:
    result = a4d.simulate_specification(
        data,
        module_id="A4D_TEST_WEEKLY_TOP6",
        signal_id="M1_EQUAL_5H",
        breadth=6,
        frequency="WEEKLY",
    )
    trades = result.simulation.trades.loc[result.simulation.trades["execution_status"].eq("EXECUTED")]
    assert (pd.to_datetime(trades["execution_date"]) > pd.to_datetime(trades["review_date"])).all()
    assert trades["execution_lag_xlon_sessions"].between(1, 3).all()
    assert result.simulation.curve["invested_fraction"].le(1 + 1e-10).all()
    assert result.simulation.curve["cash_fraction"].ge(-1e-10).all()


def test_cash_is_real_and_unqualified_slots_are_not_refilled(data: a4d.A4DData) -> None:
    targets, records = a4d.target_weights(
        data,
        signal_id="M1_EQUAL_5H",
        breadth=6,
        frequency="MONTHLY",
        cash_architecture="CASH_1_INDIVIDUAL_ABOVE_CASH_252",
    )
    assert (records["target_risky_weight"] <= 1 + 1e-12).all()
    assert records["target_cash_weight"].ge(0).all()
    reduced = records.loc[records["selected_risky_family_count"] < records["selected_family_count_before_cash"]]
    if len(reduced):
        assert reduced["target_cash_weight"].gt(0).all()
        for row in reduced.itertuples(index=False):
            assert len(targets[row.review_date]) == row.selected_risky_family_count


def test_daily_weekly_monthly_schedules_are_deterministic(data: a4d.A4DData) -> None:
    calendar = data.base.research.calendar
    daily = a4d.schedule_dates(calendar, "DAILY")
    weekly = a4d.schedule_dates(calendar, "WEEKLY")
    monthly = a4d.schedule_dates(calendar, "MONTHLY")
    assert daily.equals(calendar)
    assert weekly.is_monotonic_increasing and monthly.is_monotonic_increasing
    assert len(daily) > len(weekly) > len(monthly)
    assert not weekly.duplicated().any() and not monthly.duplicated().any()


def test_policy_has_no_optimizer_or_same_close() -> None:
    policy = json.loads((PROGRAMME_ROOT / "config" / "UKACTIVE_A4D_POLICY_v1.json").read_text(encoding="utf-8"))
    assert policy["execution"]["same_close"] is False
    assert policy["breadths"] == list(range(3, 11))
    assert policy["frequencies"] == ["DAILY", "WEEKLY", "MONTHLY"]
    assert set(policy["weighting"]) == {"W0_EQUAL", "W1_RANK_DECAY", "W2_FIXED_TOP_HEAVY"}
