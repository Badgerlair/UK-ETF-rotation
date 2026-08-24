"""Correctness controls for the separately governed UKACTIVE-A4E-SIPP stage."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


PROGRAMME_ROOT = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "directed"
    / "EDGE-UK-ACTIVE-ETF-SLEEVE-20260822-001"
)
STAGE_ROOT = PROGRAMME_ROOT / "UKACTIVE-A4E-SIPP"
sys.path.insert(0, str(PROGRAMME_ROOT / "code"))

import ukactive_a4e_sipp_core as a4e  # noqa: E402


@pytest.fixture(scope="module")
def data():
    return a4e.load_data()


def test_preregistration_is_frozen_to_a4d_parent_and_cutoff() -> None:
    protocol = json.loads(
        (STAGE_ROOT / "UKACTIVE_A4E_SIPP_PREREGISTRATION.json").read_text(
            encoding="utf-8"
        )
    )
    assert protocol["parent"]["commit"] == "48cb69ffbaae25eb0dccc3226f47f5a7491e8bd7"
    assert protocol["authoritative_cutoff"] == "2026-08-21"
    assert protocol["evidence_ceiling"] == "E2_DEVELOPMENTAL"


def test_signal_family_is_exact_and_bounded(data) -> None:
    assert a4e.SIGNAL_WEIGHTS == {
        "M2_BASE": [0.10, 0.15, 0.25, 0.30, 0.20],
        "M2_N1": [0.10, 0.15, 0.25, 0.25, 0.25],
        "M2_N2": [0.10, 0.10, 0.25, 0.30, 0.25],
        "M2_N3": [0.15, 0.15, 0.25, 0.25, 0.20],
        "M1_EQUAL_CONTROL": [0.20, 0.20, 0.20, 0.20, 0.20],
    }
    sample = data.daily_features.dropna(subset=["A4E_M2_N1"]).sample(
        200, random_state=20260824
    )
    rebuilt = sum(
        weight * sample[f"RANK_RS_{horizon}"]
        for horizon, weight in zip(a4e.HORIZONS, a4e.SIGNAL_WEIGHTS["M2_N1"])
    )
    np.testing.assert_allclose(sample["A4E_M2_N1"], rebuilt, atol=1e-12)


def test_exact_cash1_keeps_failed_slots_in_cash(data) -> None:
    targets, records = a4e.rotation_targets(data, "M2_BASE", 7, cash1=True)
    assert max(targets) <= pd.Timestamp("2026-08-21")
    assert records["target_risky_weight"].le(1.0 + 1e-12).all()
    reduced = records.loc[
        records["selected_risky_family_count"]
        < records["selected_family_count_before_cash"]
    ]
    assert len(reduced) > 0
    assert reduced["target_cash_weight"].gt(0).all()


def test_representative_rotation_uses_next_session_and_no_leverage(data) -> None:
    result = a4e.simulate_rotation(data, "M2_BASE", 7, True)
    trades = result.simulation.trades.loc[
        result.simulation.trades["execution_status"].eq("EXECUTED")
    ]
    assert (pd.to_datetime(trades["execution_date"]) > pd.to_datetime(trades["review_date"])).all()
    assert trades["execution_lag_xlon_sessions"].between(1, 3).all()
    curve = result.simulation.curve
    assert curve["invested_fraction"].le(1.0 + 1e-10).all()
    np.testing.assert_allclose(
        curve["invested_fraction"] + curve["cash_fraction"], 1.0, atol=1e-10
    )


def test_a4d_reproduction_has_no_unexplained_difference() -> None:
    audit = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4E_SIPP_METRIC_RECONCILIATION.csv")
    assert len(audit) == 720
    assert audit["status"].eq("PASS").all()
    assert audit["difference"].abs().max() <= 1e-10


def test_selected_strategy_is_operational_fallback_not_a_falsification_control() -> None:
    selected = json.loads(
        (STAGE_ROOT / "UKACTIVE_A4E_SIPP_SELECTED_STRATEGY.json").read_text(
            encoding="utf-8"
        )
    )
    strategy = selected["best_available_whole_sipp_strategy"]
    assert strategy["strategy_id"] == "GLOBAL_CASH_75_25"
    assert strategy["portfolio_sleeves"] == [
        {
            "instrument": "SWDA|IE00B4L5Y983",
            "sleeve": "GLOBAL_CORE",
            "target_weight": 0.75,
        },
        {
            "instrument": "II_SIPP_GBP_BROKER_CASH",
            "sleeve": "GBP_CASH",
            "target_weight": 0.25,
        },
    ]
    assert selected["deployment_tier"] == "CORE_ONLY"
    assert selected["active_rotation_sleeve"]["allocation"] == 0.0


def test_all_required_outputs_exist_and_csv_files_are_parseable() -> None:
    required = {
        "UKACTIVE_A4E_SIPP_MANIFEST.json",
        "UKACTIVE_A4E_SIPP_REPRODUCTION_AUDIT.md",
        "UKACTIVE_A4E_SIPP_SIGNAL_STABILITY.csv",
        "UKACTIVE_A4E_SIPP_CASH1_CONFIRMATION.csv",
        "UKACTIVE_A4E_SIPP_MATCHED_EXPOSURE_CONTROLS.csv",
        "UKACTIVE_A4E_SIPP_VOLATILITY_CONTROL.csv",
        "UKACTIVE_A4E_SIPP_CORE_SATELLITE_FRONTIER.csv",
        "UKACTIVE_A4E_SIPP_PARETO_FRONTIER.csv",
        "UKACTIVE_A4E_SIPP_LIVE_INSTRUMENT_MAP.csv",
        "UKACTIVE_A4E_SIPP_LIVE_COSTS.csv",
        "UKACTIVE_A4E_SIPP_FINAL_DECISION_REPORT.md",
        "UKACTIVE_A4E_SIPP_SELECTED_STRATEGY.json",
    }
    assert required.issubset({path.name for path in STAGE_ROOT.iterdir()})
    for path in STAGE_ROOT.glob("*.csv"):
        pd.read_csv(path)


def test_falsification_controls_are_reproducible_and_not_selection_claims() -> None:
    random = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4E_SIPP_RANDOM_SELECTION_CONTROL.csv")
    assert set(random["seed"]) == {20260824, 20260825}
    assert random["simulation_count"].eq(5000).all()
    frontier = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4E_SIPP_PARETO_FRONTIER.csv")
    assert not frontier["strategy_id"].str.startswith(
        "ROTATION_STATIC_SAME_AVERAGE_EXPOSURE"
    ).any()
    assert not frontier["strategy_id"].str.startswith(
        "ROTATION_MATCHED_VOLATILITY"
    ).any()


def test_current_implementation_metadata_is_not_historical_evidence() -> None:
    instruments = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4E_SIPP_LIVE_INSTRUMENT_MAP.csv")
    active = instruments.loc[
        ~instruments["economic_exposure_family_id"].isin(
            ["GLOBAL_DEVELOPED_WORLD", "LIVE_GBP_CASH"]
        )
    ]
    assert active["broker_availability"].eq("CONFIRMED_BY_USER").all()
    assert active["sipp_availability"].eq("TO_CHECK_SIPP_SPECIFIC_ACCOUNT").all()
    core = instruments.loc[
        instruments["economic_exposure_family_id"].eq("GLOBAL_DEVELOPED_WORLD")
    ].iloc[0]
    assert core["ticker"] == "SWDA"
    assert core["isin"] == "IE00B4L5Y983"


def test_generated_correctness_registry_is_clean() -> None:
    registry = json.loads(
        (STAGE_ROOT / "UKACTIVE_A4E_SIPP_CORRECTNESS_TESTS.json").read_text(
            encoding="utf-8"
        )
    )
    assert registry["summary"]["FAIL"] == 0
    assert all(test["status"] == "PASS" for test in registry["tests"])
