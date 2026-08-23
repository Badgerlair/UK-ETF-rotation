from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest


REPO = Path(__file__).resolve().parents[1]
PROGRAMME = REPO / "research" / "directed" / "EDGE-UK-ACTIVE-ETF-SLEEVE-20260822-001"
sys.path.insert(0, str(PROGRAMME / "code"))

import ukactive_a5_shadow_core as a5  # noqa: E402


def test_setup_correctness_artifact_all_pass() -> None:
    result = pd.read_csv(PROGRAMME / "UKACTIVE_A5_SETUP_CORRECTNESS_TESTS.csv")
    assert len(result) == 25
    assert result["result"].eq("PASS").all()


def test_setup_created_no_prospective_event() -> None:
    counts = a5.ledger_counts()
    for key in ["run", "decision", "execution", "position", "cash", "cost", "nav", "benchmark", "telemetry_csv", "warnings", "amendment"]:
        assert counts[key] == 0


def test_frozen_model_and_first_calendar_boundary() -> None:
    config = json.loads((PROGRAMME / "config" / "ukactive_a5_shadow_comparison_v1.json").read_text())
    assert config["model_a"]["horizons_xlon_sessions"] == [63, 126, 252]
    assert config["model_a"]["target_active_weight"] == 1.0
    assert config["model_b"]["target_active_weight"] == 0.5
    assert config["model_b"]["target_core_weight"] == 0.5
    calendar = pd.read_csv(PROGRAMME / "UKACTIVE_A5_OPERATING_CALENDAR.csv")
    assert calendar.iloc[0]["expected_final_valid_xlon_signal_date"] == "2026-08-28"
    assert calendar.iloc[0]["expected_next_eligible_execution_date"] == "2026-09-01"


def test_active_map_is_25_of_25_and_core_is_one_open_check() -> None:
    implementation = pd.read_csv(PROGRAMME / "UKACTIVE_A5_IMPLEMENTATION_MAP.csv", dtype=str)
    active = implementation.loc[implementation["implementation_scope"].eq("ACTIVE_SIGNAL_READY")]
    core = implementation.loc[implementation["implementation_scope"].eq("GLOBAL_CORE_REFERENCE")]
    assert len(active) == 25
    assert active["ii_current_tradable"].eq("CONFIRMED_BY_USER").all()
    assert len(core) == 1
    assert core.iloc[0]["preferred_ticker"] == "SWDA"
    assert core.iloc[0]["preferred_isin"] == "IE00B4L5Y983"
    assert core.iloc[0]["ii_current_tradable"] == "TO_CHECK"


def test_runner_has_no_order_dependency() -> None:
    source = (PROGRAMME / "code" / "ukactive_a5_shadow_core.py").read_text(encoding="utf-8")
    for forbidden in ["ib_insync", "placeOrder", "place_order", "submit_order", "preview_order"]:
        assert forbidden not in source


def test_weekly_telemetry_uses_completed_xlon_week() -> None:
    bundle = a5.DataBundle.load()
    assert not a5.telemetry_due(bundle, pd.Timestamp("2026-08-25"))
    assert a5.telemetry_due(bundle, pd.Timestamp("2026-08-28"))


def test_missed_month_end_is_discovered_for_late_diagnosis() -> None:
    dates = a5.due_unrecorded_signal_dates(pd.Timestamp("2026-09-01"))
    assert dates == [pd.Timestamp("2026-08-28")]


def test_preferred_then_verified_alternate_is_deterministic() -> None:
    preferred = {
        "ii_current_tradable": "CONFIRMED_BY_USER",
        "preferred_ticker": "GBP1",
        "preferred_isin": "ISIN1",
        "alternate_ii_current_tradable": "CONFIRMED_BY_USER",
        "alternate_ticker": "USD1",
        "alternate_isin": "ISIN1",
        "alternate_listing_id": "ALT",
        "alternate_currency": "USD",
        "alternate_price_unit": "USD",
    }
    assert a5.resolved_implementation(preferred)["preferred_ticker"] == "GBP1"
    preferred["ii_current_tradable"] = "NO_LONGER_AVAILABLE"
    resolved = a5.resolved_implementation(preferred)
    assert resolved["preferred_ticker"] == "USD1"
    assert resolved["resolved_line"] == "PREDECLARED_VERIFIED_ALTERNATE"
    preferred["alternate_ii_current_tradable"] = "TO_CHECK"
    assert a5.resolved_implementation(preferred) is None


def test_immutable_snapshot_collision_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    assert a5.write_immutable_json(path, {"value": 1})
    assert not a5.write_immutable_json(path, {"value": 1})
    with pytest.raises(RuntimeError, match="Immutable artifact collision"):
        a5.write_immutable_json(path, {"value": 2})


def test_setup_report_is_complete_and_explicitly_provisional() -> None:
    report = (PROGRAMME / "UKACTIVE_A5_LATEST_RUN_REPORT.md").read_text(encoding="utf-8")
    for required in [
        "CURRENT PROVISIONAL SLOW LEADER",
        "NOT AN OFFICIAL A5 DECISION",
        "Running scorecard",
        "Longer-history statistics",
        "PROVISIONAL TELEMETRY — DOES NOT ALTER A5 PORTFOLIOS",
        "E3 CONFIRMATION NOT YET AVAILABLE",
    ]:
        assert required in report


def test_two_shadow_accounting_engines_and_idempotence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    temporary_paths = {
        key: tmp_path / path.name for key, path in a5.LEDGER_PATHS.items()
    }
    monkeypatch.setattr(a5, "LEDGER_PATHS", temporary_paths)
    monkeypatch.setattr(a5, "INPUT_SNAPSHOT_ROOT", tmp_path / "inputs")
    a5.initialise_empty_ledgers()

    bundle = a5.DataBundle.load()
    for family in ["GLOBAL_SEMICONDUCTORS", "GLOBAL_DEVELOPED_WORLD"]:
        mask = bundle.implementation["economic_exposure_family_id"].eq(family)
        bundle.implementation.loc[mask, "ii_current_tradable"] = "CONFIRMED_BY_USER"
        bundle.implementation.loc[mask, "ii_observation_date"] = "2026-07-01"
    decision = {
        "decision_event_id": "A5DEC-SYNTHETIC",
        "signal_date": "2026-07-31",
        "selected_family_id": "GLOBAL_SEMICONDUCTORS",
        "action": "INITIAL_ENTRY",
    }
    targets = a5._target_sets(bundle, decision)
    execution_date = pd.Timestamp("2026-08-03")
    assert a5._book_target(
        bundle, model_id=a5.MODEL_A, target=targets[a5.MODEL_A], decision=decision,
        execution_date=execution_date, logging_classification="EXECUTION_LOGGED_ON_TIME",
    )
    assert a5._book_target(
        bundle, model_id=a5.MODEL_B, target=targets[a5.MODEL_B], decision=decision,
        execution_date=execution_date, logging_classification="EXECUTION_LOGGED_ON_TIME",
    )
    assert not a5._book_target(
        bundle, model_id=a5.MODEL_A, target=targets[a5.MODEL_A], decision=decision,
        execution_date=execution_date, logging_classification="EXECUTION_LOGGED_ON_TIME",
    )

    a_value = a5.value_model_at(bundle, a5.MODEL_A, execution_date)
    b_value = a5.value_model_at(bundle, a5.MODEL_B, execution_date)
    assert a_value["nav_gbp"] == pytest.approx(249_496.01)
    assert b_value["nav_gbp"] == pytest.approx(249_492.02)
    assert set(a_value["holdings"]) == {"GLOBAL_SEMICONDUCTORS"}
    assert set(b_value["holdings"]) == {"GLOBAL_SEMICONDUCTORS", "GLOBAL_DEVELOPED_WORLD"}
    assert b_value["holdings"]["GLOBAL_SEMICONDUCTORS"] == pytest.approx(
        b_value["holdings"]["GLOBAL_DEVELOPED_WORLD"]
    )

    first_added = a5.mark_to_market(bundle, pd.Timestamp("2026-08-21"))
    second_added = a5.mark_to_market(bundle, pd.Timestamp("2026-08-21"))
    assert first_added > 0
    assert second_added == 0
    nav = pd.read_csv(temporary_paths["nav"])
    assert not nav.duplicated(["nav_event_id"]).any()
    assert len(list((tmp_path / "inputs").glob("A5EXE-*.json"))) == 2
