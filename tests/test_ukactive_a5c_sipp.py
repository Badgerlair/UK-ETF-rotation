from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
PROGRAMME_ROOT = REPO_ROOT / "research" / "directed" / "EDGE-UK-ACTIVE-ETF-SLEEVE-20260822-001"
CODE_ROOT = PROGRAMME_ROOT / "code"
STAGE_ROOT = PROGRAMME_ROOT / "UKACTIVE-A5C-SIPP"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

import ukactive_a5c_sipp_core as core  # noqa: E402
import build_ukactive_a5c_sipp as builder  # noqa: E402


def test_frozen_spec_exact_and_model_search_closed() -> None:
    spec = core.frozen_spec()
    assert spec["historical_cutoff"] == "2026-08-21"
    assert spec["model_development_status"] == "M2_HISTORICAL_MODEL_DEVELOPMENT_CLOSED"
    assert spec["m2"]["relative_strength_weights"] == core.M2_WEIGHTS
    assert spec["m2"]["breadth"] == 7
    assert spec["m2"]["cash_rule"] == "CASH0_ALWAYS_INVESTED_EXCEPT_SUSPENDED_SLOTS"
    assert spec["m2"]["regime_telemetry_changes_allocation"] is False


def test_data_and_targets_remain_causal_and_point_in_time() -> None:
    data = core.load_data()
    assert pd.Timestamp(data.base.research.calendar.max()) == core.AUTHORITATIVE_CUTOFF
    targets, records = core.frozen_rotation_targets(data)
    assert max(targets) <= core.AUTHORITATIVE_CUTOFF
    assert records["review_date"].max() <= core.AUTHORITATIVE_CUTOFF
    for target in targets.values():
        assert 3 <= len(target) <= 7
        assert sum(target.values()) == pytest.approx(1.0)
        assert all(weight == pytest.approx(1.0 / len(target)) for weight in target.values())


def test_whole_sipp_states_and_caps_are_exact() -> None:
    spec = core.frozen_spec()
    pilot = spec["whole_sipp_states"]["initial_pilot_target"]
    assert pilot["strategy_id"] == "GLOBAL_65_M2_10_DEFENSIVE_25"
    assert {key: pilot[key] for key in ["swda", "m2", "defensive", "whole_sipp_weight_per_m2_family"]} == pytest.approx(
        {"swda": 0.65, "m2": 0.10, "defensive": 0.25, "whole_sipp_weight_per_m2_family": 0.10 / 7.0}
    )
    assert spec["maximum_total_active_and_thematic_allocation"] == pytest.approx(0.25)
    assert spec["maximum_live_m2_allocation"] == pytest.approx(0.10)
    for allocation in core.PLAN_SPECS.values():
        assert sum(allocation.values()) == pytest.approx(1.0)


def test_fee_schedules_are_frozen_and_credits_do_not_carry() -> None:
    assert core.II_PLANS["II_PLUS"] == {
        "fee_per_paid_leg_gbp": 3.99,
        "monthly_free_credits": 1,
        "monthly_subscription_gbp": 14.99,
    }
    assert core.II_PLANS["II_PREMIUM"] == {
        "fee_per_paid_leg_gbp": 2.99,
        "monthly_free_credits": 2,
        "monthly_subscription_gbp": 39.99,
    }
    costs = pd.read_csv(STAGE_ROOT / "UKACTIVE_A5C_SIPP_II_PLAN_COST_COMPARISON.csv")
    m2_plus = costs.loc[
        costs.strategy_id.eq("M2_100_DIAGNOSTIC")
        & costs.ii_plan.eq("II_PLUS")
        & costs.notional_gbp.eq(563000.0)
    ].iloc[0]
    m2_premium = costs.loc[
        costs.strategy_id.eq("M2_100_DIAGNOSTIC")
        & costs.ii_plan.eq("II_PREMIUM")
        & costs.notional_gbp.eq(563000.0)
    ].iloc[0]
    assert int(m2_plus.trade_legs) == 865
    assert int(m2_plus.free_trade_legs) == 99
    assert int(m2_plus.paid_trade_legs) == 766
    assert int(m2_premium.free_trade_legs) == 198
    assert int(m2_premium.paid_trade_legs) == 667


def test_cost_restatement_uses_window_specific_fee_and_friction_summaries() -> None:
    costs = pd.read_csv(STAGE_ROOT / "UKACTIVE_A5C_SIPP_COST_RESTATEMENT.csv")
    rows = costs.loc[
        costs.strategy_id.eq("GLOBAL_65_M2_10_DEFENSIVE_25")
        & costs.ii_plan.eq("II_PLUS")
        & costs.notional_gbp.eq(563000.0)
    ].set_index("window_id")
    full = rows.loc["FULL_HISTORY"]
    recent = rows.loc["LATEST_FIVE_YEARS"]
    assert int(full.free_trade_legs + full.paid_trade_legs) == int(full.trade_legs)
    assert int(recent.free_trade_legs + recent.paid_trade_legs) == int(recent.trade_legs)
    assert (int(recent.trade_legs), int(recent.free_trade_legs), int(recent.paid_trade_legs)) == (597, 60, 537)
    assert int(full.started_calendar_months) == 114
    assert int(recent.started_calendar_months) == 60
    assert recent.total_subscription_gbp == pytest.approx(899.40)
    assert recent.annual_dealing_charges_gbp == pytest.approx(431.1732990495868, rel=1e-10)
    assert recent.annual_dealing_charges_gbp != pytest.approx(full.annual_dealing_charges_gbp)
    assert recent.historical_average_annual_market_friction_gbp == pytest.approx(1489.3577304227729, rel=1e-10)
    assert recent.historical_average_annual_market_friction_gbp != pytest.approx(full.historical_average_annual_market_friction_gbp)
    assert recent.current_scale_annual_market_friction_gbp == pytest.approx(
        recent.annual_turnover * 563000.0 * 20.0 / 10_000.0,
        rel=5e-5,
    )


def test_regret_outputs_disclose_plan_notional_and_subscription_treatment() -> None:
    regret = pd.read_csv(STAGE_ROOT / "UKACTIVE_A5C_SIPP_RELATIVE_REGRET.csv")
    drag = pd.read_csv(STAGE_ROOT / "UKACTIVE_A5C_SIPP_WHOLE_PORTFOLIO_DRAG.csv")
    for frame in [regret, drag]:
        assert set(frame.ii_plan) == {"II_PLUS"}
        assert set(frame.notional_gbp) == {563000.0}
        assert set(frame.subscription_treatment) == {"SUBSCRIPTION_REPORTED_SEPARATELY"}


def test_holdings_input_template_is_create_once_and_never_overwritten(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builder, "OUT", tmp_path)
    template = pd.DataFrame([{"instrument": "RLON", "quantity": ""}])
    assert builder.write_csv_if_absent("holdings.csv", template) is True
    supplied = pd.DataFrame([{"instrument": "RLON", "quantity": "12345.67"}])
    supplied.to_csv(tmp_path / "holdings.csv", index=False, lineterminator="\n")
    assert builder.write_csv_if_absent("holdings.csv", template) is False
    preserved = pd.read_csv(tmp_path / "holdings.csv", dtype=str, keep_default_na=False)
    assert preserved.to_dict("records") == supplied.to_dict("records")


def test_execution_costs_reconcile_between_audit_trades_and_nav() -> None:
    data = core.load_data()
    targets = core.target_maps(data)["GLOBAL_65_M2_10_DEFENSIVE_25"]
    result = core.simulate_plan(
        data,
        "GLOBAL_65_M2_10_DEFENSIVE_25",
        targets,
        "II_PLUS",
        563000.0,
        include_full_subscription=False,
    )
    execution_cost = float(
        (result.fee_audit.market_friction_gbp + result.fee_audit.dealing_fee_gbp).sum() / result.notional_gbp
    )
    assert float(result.simulation.trades.transaction_cost_value.sum()) == pytest.approx(execution_cost)
    assert float(result.simulation.curve.cumulative_transaction_cost_value.iloc[-1]) == pytest.approx(execution_cost)
    performance = core.a4b.enhanced_performance_metrics(
        result.simulation,
        start=core.COMMON_START,
        end=core.AUTHORITATIVE_CUTOFF,
    )
    assert performance["total_transaction_cost_value"] == pytest.approx(execution_cost)


def test_instrument_map_preserves_27_families_and_cash_amendment() -> None:
    frame = pd.read_csv(STAGE_ROOT / "UKACTIVE_A5C_SIPP_LIVE_INSTRUMENT_MAP_V2.csv", dtype=str, keep_default_na=False)
    families = frame.loc[frame.implementation_role.eq("M2_FAMILY")]
    assert len(families) == 27
    assert int(families.signal_status_at_2026_08_21.eq("SIGNAL_READY").sum()) == 25
    assert int(families.signal_status_at_2026_08_21.str.startswith("NOT_SIGNAL_READY").sum()) == 2
    assert frame.historical_back_projection.eq("PROHIBITED").all()
    assert set(families.economic_exposure_family_id).issuperset({"EUROPE_INFRASTRUCTURE", "US_AEROSPACE_DEFENCE"})
    swda = frame.loc[frame.economic_exposure_family_id.eq("GLOBAL_DEVELOPED_WORLD")].iloc[0]
    assert (swda["ticker"], swda["isin"], swda["trading_currency"]) == ("SWDA", "IE00B4L5Y983", "GBP")
    assert swda["alternate_trading_currency"] == "USD"
    assert swda["automatic_alternate_permitted"] == "NO_USD_OR_EUR_LINE"
    europe_infrastructure = frame.loc[frame.economic_exposure_family_id.eq("EUROPE_INFRASTRUCTURE")].iloc[0]
    assert (europe_infrastructure["alternate_ticker"], europe_infrastructure["alternate_trading_currency"]) == ("FTIE", "GBP")
    assert europe_infrastructure["automatic_alternate_permitted"] == "YES_ONLY_AFTER_CURRENT_SIPP_CONFIRMATION"
    us_aerospace_defence = frame.loc[frame.economic_exposure_family_id.eq("US_AEROSPACE_DEFENCE")].iloc[0]
    assert (us_aerospace_defence["alternate_ticker"], us_aerospace_defence["alternate_trading_currency"]) == ("GIJO", "USD")
    assert us_aerospace_defence["automatic_alternate_permitted"] == "NO_USD_OR_EUR_LINE"
    csh2 = frame.loc[frame.economic_exposure_family_id.eq("LIVE_TACTICAL_CSH2")].iloc[0]
    assert (csh2["ticker"], csh2["isin"], csh2["trading_currency"]) == ("CSH2", "LU1230136894", "GBP")
    rlon = frame.loc[frame.economic_exposure_family_id.eq("LIVE_STRATEGIC_RLON")].iloc[0]
    assert rlon["isin"] == "AWAITING_CURRENT_HOLDINGS_INPUT"
    assert "guessed" in rlon.evidence_notes.lower()


def test_prospective_lineage_is_empty_and_old_a5_is_untouched() -> None:
    new_ledger = pd.read_csv(STAGE_ROOT / "UKACTIVE_A5C_SIPP_PROSPECTIVE_LEDGER.csv")
    old_decisions = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A5_DECISION_LEDGER.csv")
    old_executions = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A5_EXECUTION_LEDGER.csv")
    assert new_ledger.empty
    assert old_decisions.empty
    assert old_executions.empty
    state = json.loads((PROGRAMME_ROOT / "UKACTIVE_A5_CURRENT_STATE.json").read_text(encoding="utf-8"))
    assert state["model_status"]["A5A_ACTIVE_BASELINE_V1"] == "PROSPECTIVE_NOT_STARTED"
    assert state["completed_on_time_decision_count"] == 0
    assert state["completed_shadow_execution_count"] == 0


def test_transition_outputs_are_not_orders() -> None:
    transition = pd.read_csv(STAGE_ROOT / "UKACTIVE_A5C_SIPP_TRANSITION_TRADES.csv")
    first = pd.read_csv(STAGE_ROOT / "UKACTIVE_A5C_SIPP_FIRST_MONTH_END_TRADES.csv")
    assert set(transition.side) == {"NONE"}
    assert set(first.side) == {"NONE"}
    assert transition.trade_status.str.contains("AWAITING_CURRENT_HOLDINGS_INPUT").all()
    assert first.trade_status.str.contains("NOT_DUE_NO_PROSPECTIVE_SIGNAL_CREATED").all()


def test_manifest_reports_no_prospective_event_or_order() -> None:
    manifest = json.loads((STAGE_ROOT / "UKACTIVE_A5C_SIPP_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["historical_cutoff"] == "2026-08-21"
    assert manifest["prospective_event_count"] == 0
    assert manifest["broker_order_count"] == 0
    assert manifest["correctness"]["FAIL"] == 0
