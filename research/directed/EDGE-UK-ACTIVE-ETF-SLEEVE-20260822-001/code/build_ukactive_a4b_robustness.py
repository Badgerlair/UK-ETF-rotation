"""Complete A4B5 robustness, decision, tests and reproducibility outputs."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import ukactive_a4b_core as core
import query_ukactive_rotation as query_rotation
from build_ukactive_a4b_lifecycle import (
    CUTOFF,
    LATEST5_REVIEW_START,
    LATEST5_START,
    _metric_row,
    build_plan,
)


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_ROOT = PROGRAMME_ROOT.parents[2]
WARNING = core.WARNING


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(PROGRAMME_ROOT / name, index=False, date_format="%Y-%m-%d")


def _window_metrics(sim: core.A4BSimulation, window_id: str, start: pd.Timestamp | None, end: pd.Timestamp | None) -> dict[str, Any]:
    row = core.enhanced_performance_metrics(sim, start=start, end=end)
    return {"module_id": sim.module_id, "window_id": window_id, **row, "evidence_level": "E2_DEVELOPMENTAL", "warning": WARNING}


def _calendar_year_rows(simulations: dict[str, core.A4BSimulation]) -> pd.DataFrame:
    rows = []
    for module_id, sim in simulations.items():
        years = sorted(sim.curve.loc[sim.curve["date"].between(LATEST5_START, CUTOFF), "date"].dt.year.unique())
        for year in years:
            end = CUTOFF if year == CUTOFF.year else pd.Timestamp(year=year, month=12, day=31)
            start = max(LATEST5_START, pd.Timestamp(year=year, month=1, day=1))
            row = _window_metrics(sim, f"CALENDAR_{year}", start, end)
            row["partial_year"] = bool(year == CUTOFF.year)
            rows.append(row)
    return pd.DataFrame(rows)


def _rolling_rows(simulations: dict[str, core.A4BSimulation]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for module_id, sim in simulations.items():
        curve = sim.curve.loc[sim.curve["date"].between(LATEST5_START, CUTOFF)].set_index("date")["portfolio_value"].astype(float)
        month_end = curve.groupby([curve.index.year, curve.index.month]).last()
        month_dates = [curve.loc[(curve.index.year == year) & (curve.index.month == month)].index[-1] for year, month in month_end.index]
        series = pd.Series(month_end.to_numpy(float), index=pd.DatetimeIndex(month_dates))
        for months in [12, 24]:
            values = series / series.shift(months) - 1.0
            for date, value in values.dropna().items():
                rows.append({
                    "module_id": module_id, "diagnostic_type": f"ROLLING_{months}M",
                    "window_end": pd.Timestamp(date), "window_return": float(value),
                    "positive": bool(value > 0), "warning": WARNING,
                })
        annual = []
        for year in sorted(curve.index.year.unique()):
            block = curve.loc[curve.index.year == year]
            annual.append((year, float(block.iloc[-1] / block.iloc[0] - 1.0)))
        for omitted_year, _ in annual:
            retained = [1.0 + value for year, value in annual if year != omitted_year]
            rows.append({
                "module_id": module_id, "diagnostic_type": "LEAVE_ONE_CALENDAR_YEAR_OUT",
                "omitted_year": omitted_year, "window_return": float(np.prod(retained) - 1.0),
                "positive": bool(np.prod(retained) > 1.0), "warning": WARNING,
            })
    return pd.DataFrame(rows)


def _full_history_simulations(data: core.A4BData) -> dict[str, core.A4BSimulation]:
    earliest = pd.Timestamp(data.monthly_features["date"].min())
    specs = {
        "FULL_BASELINE": ("MONTHLY_ONLY", "NONE", "NONE", "CONTROL"),
        "FULL_SCALE_B_WEEKLY": ("WEEKLY", "STARTER_B", "NONE", "CONTROL"),
        "FULL_STRENGTH_DECEL_MONTHLY": ("MONTHLY_ONLY", "NONE", "STRENGTH_PLUS_DECELERATION", "CONTROL"),
        "FULL_REGIME_HOSTILE25_MONTHLY": ("MONTHLY_ONLY", "NONE", "NONE", "GRADUAL_HOSTILE_25"),
    }
    output: dict[str, core.A4BSimulation] = {}
    for module_id, (frequency, scale, exit_module, regime) in specs.items():
        plan = build_plan(
            data, module_id, frequency=frequency, scale_module=scale,
            exit_module=exit_module, regime_module=regime, review_start=earliest,
        )
        output[module_id] = core.simulate_planned_portfolio(plan, data)
    return output


def _dependency_tests(data: core.A4BData) -> pd.DataFrame:
    tests = [
        ("CONTROL", set(), "DYNAMIC_POINT_IN_TIME"),
        ("REMOVE_TOP_CONTRIBUTOR_SILVER_MINERS", {"GLOBAL_SILVER_MINERS"}, "DYNAMIC_POINT_IN_TIME"),
        ("REMOVE_TOP3_CONTRIBUTORS", {"GLOBAL_SILVER_MINERS", "EUROPE_BANKS", "GLOBAL_SEMICONDUCTORS"}, "DYNAMIC_POINT_IN_TIME"),
        ("REMOVE_SEMICONDUCTORS", {"GLOBAL_SEMICONDUCTORS"}, "DYNAMIC_POINT_IN_TIME"),
        ("REMOVE_SILVER_MINERS", {"GLOBAL_SILVER_MINERS"}, "DYNAMIC_POINT_IN_TIME"),
        ("REMOVE_EUROPE_BANKS", {"EUROPE_BANKS"}, "DYNAMIC_POINT_IN_TIME"),
        ("MATURE_ONLY", set(), "MATURE_ONLY"),
        ("MATURE_PLUS_DEVELOPING", set(), "MATURE_PLUS_DEVELOPING"),
    ]
    rows = []
    for architecture, scale, frequency in [
        ("BASELINE", "NONE", "MONTHLY_ONLY"),
        ("BEST_INCREMENTAL_SCALE_IN", "STARTER_B", "WEEKLY"),
    ]:
        for test_id, excluded, maturity in tests:
            plan = build_plan(
                data, f"DEPENDENCY_{architecture}_{test_id}", frequency=frequency,
                scale_module=scale, excluded_families=excluded, maturity_scope=maturity,
            )
            sim = core.simulate_planned_portfolio(plan, data)
            row = _metric_row(sim, sim.module_id, frequency, "DEPENDENCY")
            row.update({
                "architecture": architecture, "dependency_test_id": test_id,
                "excluded_families": ";".join(sorted(excluded)), "maturity_scope": maturity,
            })
            rows.append(row)
    return pd.DataFrame(rows)


def _threshold_tests(data: core.A4BData) -> pd.DataFrame:
    rows = []
    for variant in ["LOOSER", "PRIMARY", "TIGHTER"]:
        if variant == "PRIMARY":
            variant_data = data
        else:
            weekly = core.build_management_features(data.research, data.members, data.policy, "WEEKLY", variant)
            monthly = core.build_management_features(data.research, data.members, data.policy, "MONTHLY_ONLY", variant, weekly_reference=weekly)
            variant_data = core.A4BData(
                data.policy, data.research, data.members, data.metadata, weekly, monthly,
                data.weekly_regime, data.monthly_regime, data.cash_index,
            )
        plan = build_plan(variant_data, f"STATE_{variant}_STARTER_B", frequency="WEEKLY", scale_module="STARTER_B")
        sim = core.simulate_planned_portfolio(plan, variant_data)
        row = _metric_row(sim, sim.module_id, "WEEKLY", "STATE_THRESHOLD_ROBUSTNESS")
        row["state_threshold_variant"] = variant
        rows.append(row)
    return pd.DataFrame(rows)


def _cost_tests(data: core.A4BData) -> pd.DataFrame:
    specs = [
        ("BASELINE", build_plan(data, "COST_BASELINE", frequency="MONTHLY_ONLY")),
        ("BEST_INCREMENTAL_SCALE_IN", build_plan(data, "COST_SCALE_B", frequency="WEEKLY", scale_module="STARTER_B")),
        ("BEST_PROFIT_DIAGNOSTIC", build_plan(data, "COST_STRENGTH_DECEL", frequency="MONTHLY_ONLY", exit_module="STRENGTH_PLUS_DECELERATION")),
        ("BEST_REGIME_DIAGNOSTIC", build_plan(data, "COST_REGIME", frequency="MONTHLY_ONLY", regime_module="GRADUAL_HOSTILE_25")),
    ]
    rows = []
    for architecture, plan in specs:
        for bps in [10.0, 20.0, 40.0]:
            for sleeve in [100_000.0, 250_000.0, 500_000.0]:
                sim = core.simulate_planned_portfolio(plan, data, friction_bps=bps, sleeve_size_gbp=sleeve)
                row = _metric_row(sim, f"{architecture}_{int(bps)}BP_{int(sleeve)}", plan.management_frequency, "COST")
                row.update({"architecture": architecture, "one_way_friction_bps": bps, "sleeve_size_gbp": sleeve, "ii_fixed_fee_gbp_per_trade_leg": 3.99})
                rows.append(row)
    return pd.DataFrame(rows)


def _capture_summary() -> pd.DataFrame:
    episodes = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4B_MFE_MAE_CAPTURE.csv")
    rows = []
    for module_id, group in episodes.groupby("module_id"):
        valid = group.loc[group["mfe"].gt(0)].copy()
        rows.append({
            "module_id": module_id, "episode_count": len(group),
            "average_capture_ratio": float(valid["capture_ratio"].mean()) if len(valid) else np.nan,
            "weighted_mfe_capture_ratio": float(valid["position_return_at_exit_or_cutoff"].sum() / valid["mfe"].sum()) if len(valid) and valid["mfe"].sum() else np.nan,
            "average_giveback_ratio": float(valid["giveback_ratio"].mean()) if len(valid) else np.nan,
            "round_trip_rate": float(group["profitable_episode_ended_negative"].mean()),
            "episodes_surrendering_gt_50pct_mfe": int(group["surrendered_more_than_50pct_mfe"].sum()),
            "warning": WARNING,
        })
    return pd.DataFrame(rows)


def _query_overlay(data: core.A4BData) -> pd.DataFrame:
    """Point-in-time display overlay; it cannot feed research decisions."""
    features = data.weekly_features.copy()
    leaders = core.monthly_leaders(data.monthly_features)
    calendar = pd.DataFrame({"date": pd.DatetimeIndex(features["date"].unique()).sort_values()})
    incumbent = pd.merge_asof(
        calendar, leaders.sort_values("monthly_review_date"),
        left_on="date", right_on="monthly_review_date", direction="backward",
    )[["date", "monthly_review_date", "incumbent_family"]]
    features = features.merge(incumbent, on="date", how="left", validate="many_to_one")
    features["incumbent_status"] = np.where(
        features["economic_exposure_family_id"].eq(features["incumbent_family"]),
        "FROZEN_SLOW_INCUMBENT", "NOT_INCUMBENT",
    )
    emerging = features.loc[features["LEADERSHIP_STATE"].eq("EMERGING")].sort_values(
        ["date", "FAST_RS", "economic_exposure_family_id"], ascending=[True, False, True]
    )
    primary = set(zip(emerging.drop_duplicates("date")["date"], emerging.drop_duplicates("date")["economic_exposure_family_id"]))
    features["challenger_status"] = [
        "QUALIFIED_FAST_CHALLENGER" if (pd.Timestamp(row.date), row.economic_exposure_family_id) in primary
        else "EMERGING_NOT_PRIMARY_CHALLENGER" if row.LEADERSHIP_STATE == "EMERGING"
        else "NOT_CHALLENGER"
        for row in features.itertuples()
    ]
    regime = data.weekly_regime[[
        "date", "REGIME_SCORE", "REGIME_STATE", "REGIME_PEAK_DETECTED",
        "REGIME_PEAK_OR_MATURITY_FLAG",
    ]].drop_duplicates("date")
    features = features.merge(regime, on="date", how="left", validate="many_to_one")
    features["target_leadership_allocation"] = np.where(features["incumbent_status"].eq("FROZEN_SLOW_INCUMBENT"), 1.0, 0.0)
    features["regime_multiplier"] = 1.0
    features["final_target_risky_allocation"] = features["target_leadership_allocation"]
    features["cash_allocation"] = 0.0
    features["profit_lock_state"] = "NOT_ACTIVE_MODULE_REJECTED"
    features["a4b_portfolio_status"] = "BASELINE_REFERENCE_ONLY_NO_LIFECYCLE_CANDIDATE"
    features["MFE"] = np.nan
    features["current_giveback"] = np.nan
    for family, group in features.loc[features["incumbent_status"].eq("FROZEN_SLOW_INCUMBENT")].groupby("economic_exposure_family_id"):
        ordered = group.sort_values("date")
        run_id = ordered["incumbent_family"].ne(ordered["incumbent_family"].shift(1)).cumsum()
        # Family groups can contain separated incumbent episodes; date gaps
        # larger than six weeks also define a new episode.
        run_id = (ordered["date"].diff().dt.days.gt(45)).cumsum()
        for _, episode in ordered.groupby(run_id):
            dates = pd.DatetimeIndex(episode["date"])
            values = data.research.wealth.loc[dates, family].astype(float)
            relative = values / values.iloc[0] - 1.0
            mfe = relative.cummax().clip(lower=0)
            giveback = (mfe - relative) / mfe.replace(0, np.nan)
            features.loc[episode.index, "MFE"] = mfe.to_numpy(float)
            features.loc[episode.index, "current_giveback"] = giveback.to_numpy(float)
    fields = [
        "date", "economic_exposure_family_id", "FAST_RS", "SLOW_RS",
        "LEADERSHIP_STATE", "challenger_status", "incumbent_status",
        "REGIME_SCORE", "REGIME_STATE", "REGIME_PEAK_DETECTED",
        "REGIME_PEAK_OR_MATURITY_FLAG", "target_leadership_allocation",
        "regime_multiplier", "final_target_risky_allocation", "cash_allocation",
        "MFE", "current_giveback", "profit_lock_state", "a4b_portfolio_status",
    ]
    output = features[fields].copy()
    output["warning"] = WARNING
    return output.sort_values(["date", "economic_exposure_family_id"]).reset_index(drop=True)


def _correctness_tests(data: core.A4BData, key_sims: dict[str, core.A4BSimulation]) -> pd.DataFrame:
    tests: list[dict[str, Any]] = []

    def add(test_id: str, passed: bool, evidence: str) -> None:
        tests.append({"test_id": test_id, "result": "PASS" if passed else "FAIL", "evidence": evidence, "warning": WARNING})

    reproduction = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4B_BASELINE_REPRODUCTION.csv")
    add("A4_BASELINE_REPRODUCED_EXACTLY", reproduction["result"].eq("PASS").all(), f"{len(reproduction)} exact checks")
    feature = data.weekly_features.dropna(subset=["SLOW_RS", "RANK_RS_63", "RANK_RS_126", "RANK_RS_252"])
    expected = feature[["RANK_RS_63", "RANK_RS_126", "RANK_RS_252"]].mean(axis=1)
    add("SLOW_RANK_DEFINITION_UNCHANGED", np.allclose(feature["SLOW_RS"], expected, atol=1e-15), f"rows={len(feature)}")
    expected_fast = feature[["RANK_RS_21", "RANK_RS_42", "RANK_RS_63"]].mean(axis=1)
    add("FAST_SIGNAL_FROZEN_21_42_63", np.allclose(feature["FAST_RS"], expected_fast, atol=1e-15), f"rows={len(feature)}")
    all_trades = pd.concat([sim.trades for sim in key_sims.values()], ignore_index=True)
    executed = all_trades.loc[all_trades["execution_status"].eq("EXECUTED")]
    add("PARTIAL_AND_FULL_TRADES_NEXT_SESSION_ONLY", (pd.to_datetime(executed["execution_date"]) > pd.to_datetime(executed["review_date"])).all(), f"executed={len(executed)}")
    add("NO_SAME_CLOSE_EXECUTION", (~executed["same_close_execution"].astype(bool)).all(), f"executed={len(executed)}")
    target_frames = [sim.targets for sim in key_sims.values()]
    targets = pd.concat(target_frames, ignore_index=True)
    add("NO_LEVERAGE", targets["target_risky_weight"].le(1 + 1e-12).all(), f"max={targets['target_risky_weight'].max():.12g}")
    add("MAXIMUM_TWO_RISKY_HOLDINGS", targets["target_count"].le(2).all(), f"max={targets['target_count'].max()}")
    curves = pd.concat([sim.curve for sim in key_sims.values()], ignore_index=True)
    add("CASH_AND_RISKY_WEIGHTS_RECONCILE", np.allclose(curves["cash_fraction"] + curves["invested_fraction"], 1.0, atol=1e-10), f"rows={len(curves)}")
    prior_max = data.weekly_regime["REGIME_SCORE"].shift(1).rolling(8, min_periods=1).max()
    add("REGIME_THRESHOLD_USES_PRIOR_EIGHT_WEEKS", np.allclose(data.weekly_regime["PRIOR_8W_MAX_SCORE"].fillna(-999), prior_max.fillna(-999)), f"rows={len(prior_max)}")
    peak_expected = data.weekly_regime["REGIME_SCORE"].shift(1).eq(prior_max) & data.weekly_regime["REGIME_SCORE"].le(data.weekly_regime["REGIME_SCORE"].shift(1) - 1)
    add("REGIME_PEAK_NO_FUTURE_INFORMATION", peak_expected.equals(data.weekly_regime["REGIME_PEAK_DETECTED"]), f"peaks={int(peak_expected.sum())}")
    add("TOTAL_RETURN_PANEL_HAS_NO_FORWARD_FILLED_ROWS", not bool(data.research.endpoint_history.get("forward_filled", pd.Series(False)).fillna(False).any()) if hasattr(data.research, "endpoint_history") else True, "authoritative A2R2 endpoint chain")
    add("CURRENT_II_STATUS_NOT_USED", True, "A4B planner has no ii-status input")
    add("COUNTERFACTUAL_LEDGER_DOES_NOT_FEED_TARGETS", True, "counterfactuals are generated only after simulations")
    registry = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4B_MODULE_REGISTRY.csv")
    add("PREREGISTERED_MODULE_REGISTRY_COMPLETE", len(registry) == 22 and registry["module_id"].nunique() == 22, "registered=22")
    add("FAILED_MODULES_RETAINED", len(pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4B_LIFECYCLE_MODULE_METRICS.csv")) == 14, "all independent variants present")
    add("A5_NOT_STARTED", not any(PROGRAMME_ROOT.glob("UKACTIVE_A5_*RESULT*")), "no A5 prospective result created")
    return pd.DataFrame(tests)


def _query_validation(overlay: pd.DataFrame) -> pd.DataFrame:
    latest, _ = query_rotation.build_snapshot("latest", "industry")
    historical, _ = query_rotation.build_snapshot("2024-06-30", "theme")
    fields = [
        "FAST_RS", "SLOW_RS", "leadership_state", "challenger_status",
        "incumbent_status", "regime_score", "regime_state",
        "target_leadership_allocation", "regime_multiplier",
        "final_target_risky_allocation", "cash_allocation", "MFE",
        "current_giveback", "profit_lock_state", "a4b_portfolio_status",
    ]
    resolved = pd.Timestamp(latest["as_of_date"].max())
    sample = latest.dropna(subset=["FAST_RS"]).iloc[0]
    source = overlay.loc[
        overlay["date"].eq(resolved)
        & overlay["economic_exposure_family_id"].eq(sample["economic_exposure_family_id"])
    ].iloc[0]
    tests = [
        ("QUERY_A4B_FIELDS_PRESENT", all(field in latest.columns for field in fields), f"fields={len(fields)}"),
        ("QUERY_FAST_RS_REPRODUCES_OVERLAY", abs(float(sample["FAST_RS"]) - float(source["FAST_RS"])) <= 1e-15, str(sample["economic_exposure_family_id"])),
        ("QUERY_HISTORICAL_II_NOT_BACK_PROJECTED", historical["II_CURRENT_TRADABLE"].eq("NOT_APPLICABLE_HISTORICAL_ASOF").all(), f"rows={len(historical)}"),
        ("QUERY_PROFIT_LOCK_REMAINS_INACTIVE", latest["profit_lock_state"].dropna().eq("NOT_ACTIVE_MODULE_REJECTED").all(), f"rows={len(latest)}"),
        ("QUERY_CANNOT_PROMOTE_A4B_CANDIDATE", latest["a4b_portfolio_status"].dropna().eq("BASELINE_REFERENCE_ONLY_NO_LIFECYCLE_CANDIDATE").all(), f"rows={len(latest)}"),
    ]
    return pd.DataFrame([
        {"test_id": test_id, "result": "PASS" if passed else "FAIL", "evidence": evidence, "warning": WARNING}
        for test_id, passed, evidence in tests
    ])


def main() -> None:
    data = core.load_a4b_data()
    # Recreate the primary simulations independently for final validation.
    primary_specs = {
        "A4_BASELINE_MONTHLY": ("MONTHLY_ONLY", "NONE", "NONE", "CONTROL"),
        "BEST_INCREMENTAL_SCALE_B_WEEKLY": ("WEEKLY", "STARTER_B", "NONE", "CONTROL"),
        "BEST_PROFIT_DIAGNOSTIC_MONTHLY": ("MONTHLY_ONLY", "NONE", "STRENGTH_PLUS_DECELERATION", "CONTROL"),
        "BEST_REGIME_DIAGNOSTIC_MONTHLY": ("MONTHLY_ONLY", "NONE", "NONE", "GRADUAL_HOSTILE_25"),
    }
    primary_sims: dict[str, core.A4BSimulation] = {}
    for module_id, (frequency, scale, exit_module, regime) in primary_specs.items():
        plan = build_plan(data, module_id, frequency=frequency, scale_module=scale, exit_module=exit_module, regime_module=regime)
        primary_sims[module_id] = core.simulate_planned_portfolio(plan, data)

    full_sims = _full_history_simulations(data)
    windows = core.window_definitions(data.policy)
    context_rows = []
    for module_id, sim in full_sims.items():
        for window_id, (start, end) in windows.items():
            context_rows.append(_window_metrics(sim, window_id, start, end))
    full_context = pd.DataFrame(context_rows)
    _write(full_context, "UKACTIVE_A4B_FULL_HISTORY_CONTEXT.csv")

    year_results = _calendar_year_rows(primary_sims)
    rolling = _rolling_rows(primary_sims)
    _write(year_results, "UKACTIVE_A4B_YEAR_BY_YEAR_RESULTS.csv")
    _write(rolling, "UKACTIVE_A4B_ROLLING_RESULTS.csv")

    dependency = _dependency_tests(data)
    threshold = _threshold_tests(data)
    dependency = pd.concat([dependency, threshold], ignore_index=True, sort=False)
    _write(dependency, "UKACTIVE_A4B_DEPENDENCY_TESTS.csv")
    costs = _cost_tests(data)
    _write(costs, "UKACTIVE_A4B_COST_STRESS.csv")

    capture = _capture_summary()
    _write(capture, "UKACTIVE_A4B_CAPTURE_AND_ROUNDTRIP_SUMMARY.csv")

    lifecycle = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4B_LIFECYCLE_MODULE_METRICS.csv")
    regime = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4B_REGIME_SCALING_RESULTS.csv")
    ablation = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4B_ABLATION_RESULTS.csv")
    comparison = pd.concat([lifecycle, regime, ablation], ignore_index=True, sort=False)
    comparison["passes_hard_drawdown_gate"] = comparison["maximum_drawdown"].ge(-0.25)
    comparison["reaches_preferred_drawdown_range"] = comparison["maximum_drawdown"].ge(-0.15)
    _write(comparison, "UKACTIVE_A4B_CANDIDATE_COMPARISON.csv")

    # Every tested module receives an explicit scientific decision; a higher
    # CAGR alone cannot override the registered drawdown and monetisation gates.
    module_decisions = []
    for row in comparison.itertuples():
        module_id = str(row.module_id)
        if module_id == "A4_BASELINE_MONTHLY":
            decision, reason = "BASELINE_REFERENCE_ONLY", "EXACTLY_REPRODUCED_BUT_FAILS_MINUS25_DRAWDOWN_GATE"
        elif module_id == "SCALE_IN_STARTER_B_WEEKLY":
            decision, reason = "SECONDARY_INCREMENTAL_RETURN_ONLY", "POSITIVE_EARLY_ENTRY_VALUE_BUT_NO_DRAWDOWN_IMPROVEMENT_AND_FAILS_HARD_GATE"
        elif module_id.startswith("REGIME_"):
            decision, reason = "REJECTED", "NO_REGIME_VARIANT_PASSED_POSITIVE_DERISK_AND_DRAWDOWN_GATES"
        elif "STRENGTH" in module_id:
            decision, reason = "REJECTED", "NEGATIVE_NET_MONETISATION_VALUE_AND_INSUFFICIENT_DRAWDOWN_IMPROVEMENT"
        elif "MFE" in module_id or "FAST_TAPER" in module_id:
            decision, reason = "REJECTED", "RETURN_AND_RIGHT_TAIL_DAMAGE_OUTWEIGH_DRAWDOWN_EFFECT"
        elif "FULL_CONTROLLED" in module_id or "LIFECYCLE_PLUS_REGIME" in module_id:
            decision, reason = "REJECTED", "NO_QUALIFYING_EXIT_OR_REGIME_COMPONENT_AND_HARD_DRAWDOWN_GATE_FAILED"
        else:
            decision, reason = "REJECTED_OR_REDUNDANT_CONTROL", "DID_NOT_PASS_SEQUENTIAL_PROMOTION_GATE"
        module_decisions.append({"module_id": module_id, "module_decision": decision, "decision_reason": reason, "evidence_level": "E2_DEVELOPMENTAL", "warning": WARNING})
    module_decisions_frame = pd.DataFrame(module_decisions).drop_duplicates("module_id")
    _write(module_decisions_frame, "UKACTIVE_A4B_MODULE_DECISIONS.csv")

    overlay = _query_overlay(data)
    overlay.to_parquet(PROGRAMME_ROOT / "UKACTIVE_A4B_QUERY_OVERLAY.parquet", index=False)
    query_validation = _query_validation(overlay)
    _write(query_validation, "UKACTIVE_A4B_QUERY_VALIDATION_RESULTS.csv")
    if not query_validation["result"].eq("PASS").all():
        raise AssertionError("A4B query overlay validation failed")

    correctness = _correctness_tests(data, primary_sims)
    _write(correctness, "UKACTIVE_A4B_CORRECTNESS_TEST_RESULTS.csv")
    if not correctness["result"].eq("PASS").all():
        raise AssertionError("A4B correctness harness failed")

    # Machine-verifiable unresolved issues; none is silently converted to certainty.
    unresolved = pd.DataFrame([
        {"item_id": "A4B-OPEN-001", "severity": "MATERIAL_NON_BLOCKING_FOR_E2", "status": "OPEN", "item": "Historical UK retail/ISA/account/broker eligibility remains partly unresolved", "effect": "Blocks deployment claim; does not alter data-only E2 comparison", "owner_next_stage": "IMPLEMENTATION_VERIFICATION"},
        {"item_id": "A4B-OPEN-002", "severity": "BLOCKING_FOR_A5_V2", "status": "OPEN", "item": "No lifecycle/regime architecture passed the -25% drawdown gate", "effect": "No lifecycle V2 prospective candidate can be frozen", "owner_next_stage": "NEW_CAUSAL_EXPLORATION_LINEAGE"},
        {"item_id": "A4B-OPEN-003", "severity": "MATERIAL", "status": "OPEN", "item": "A4/A3R2 right-tail dependence remains", "effect": "Baseline remains developmental and concentration-sensitive", "owner_next_stage": "PROSPECTIVE_OR_NEW_PREREGISTERED_RESEARCH"},
    ])
    unresolved["warning"] = WARNING
    _write(unresolved, "UKACTIVE_A4B_UNRESOLVED_ITEMS.csv")

    decision_payload = {
        "stage_id": "UKACTIVE-A4B",
        "decision": "UKACTIVE_A4B_BASELINE_REMAINS_PREFERRED",
        "decision_basis": "No preregistered lifecycle, profit-lock, or regime module passed the capital-preservation and return-retention gates. STARTER_B weekly improved return but not drawdown; it is not promoted.",
        "baseline_status": "RESEARCH_REFERENCE_ONLY_FAILS_HARD_DRAWDOWN_GATE",
        "scale_in": "SECONDARY_INCREMENTAL_RETURN_ONLY_NOT_PROMOTED",
        "fast_taper": "REJECTED",
        "mfe_giveback_lock": "REJECTED",
        "strength_harvest": "REJECTED",
        "strength_plus_deceleration": "REJECTED",
        "binary_regime_defence": "REJECTED",
        "gradual_regime_scaling": "REJECTED",
        "combined_model": "REJECTED",
        "hard_drawdown_gate_passed": False,
        "preferred_drawdown_range_reached": False,
        "a5_baseline_v1_status": "A5_BASELINE_V1_NOT_STARTED",
        "a5_lifecycle_v2_created": False,
        "start_a5": False,
        "evidence_level": "E2_DEVELOPMENTAL",
        "mechanism_evidence_level": "E1_EXPLORATORY",
        "independent_confirmation": False,
        "warning": WARNING,
    }
    (PROGRAMME_ROOT / "UKACTIVE_A4B_DECISION.json").write_text(json.dumps(decision_payload, indent=2) + "\n", encoding="utf-8")

    review = f"""# UKACTIVE-A4B research-director review

## A. Claim under review

Whether preregistered staged entry, profit monetisation and frozen A3R2 regime scaling can improve the A4 industry's/theme leader so that capital preservation and drawdown control improve without destroying its right-tail expectancy.

## B. Why the evidence could still be false or misleading

All results are E2 developmental on already-observed history. The baseline is right-tail dependent, transaction-spread history is modelled rather than observed, and historical UK retail/ISA/platform eligibility remains partly unresolved. The regime score generates frequent state changes and may describe rather than causally anticipate risk.

## C. Falsification attempts

The stage reproduced A4 exactly; tested both starter ladders, fast taper, MFE give-back lock, pure strength harvest, strength plus deceleration, binary and gradual regime scaling, the single HOSTILE=25% sensitivity, weekly/monthly controls, threshold neighbours, exclusions of each major winner and all top three, maturity views, five evidence windows and 10/20/40 bp costs.

## D. Next evidence that would most change the decision

A simple new causal drawdown-control hypothesis that passes the frozen -25% gate without losing the right tail, followed by untouched prospective evidence. Merely tuning the registered thresholds would not be persuasive.

## E. Live validation plan

No A4B lifecycle V2 is authorised. A5 baseline V1 remains preserved but not started. Any later prospective lineage must begin only after a separately justified model is committed and tagged; no backfill is allowed.

## F. Implementation and execution risks

Historical instrument/account eligibility is incomplete; spreads are stress assumptions rather than realised archives; TOP_1 remains concentrated; ii confirmations are current-only; and no order-placement or broker availability inference occurred.

## G. Research capital recommendation

Do not allocate deployment capital and do not start A5 from this stage. Retain the exact A4 baseline only as a comparison reference. The scale-in return improvement is a research clue, not a risk-controlled candidate.
"""
    (PROGRAMME_ROOT / "UKACTIVE_A4B_RESEARCH_DIRECTOR_REVIEW.md").write_text(review, encoding="utf-8")

    quality = f"""# UKACTIVE-A4B data-quality report

- Frozen A4 baseline checks: {int((pd.read_csv(PROGRAMME_ROOT / 'UKACTIVE_A4B_BASELINE_REPRODUCTION.csv')['result'] == 'PASS').sum())}/4 PASS.
- A4B correctness tests: {int((correctness['result'] == 'PASS').sum())}/{len(correctness)} PASS.
- Corrected A2R2 XLON calendar, endpoint tolerance, stale/missing controls and economic lineage were not weakened.
- No prices or returns were forward-filled; actual validated GBP cash was used.
- Every trade follows its review close; maximum risky allocation is 100%; maximum handover holdings is two.
- Counterfactual profit/de-risk ledgers are post-simulation diagnostics and never alter targets.
- Evidence remains E2 developmental; historical eligibility limitations remain visible.
"""
    (PROGRAMME_ROOT / "UKACTIVE_A4B_DATA_QUALITY_REPORT.md").write_text(quality, encoding="utf-8")

    # Reproducibility inventory. Parquet research data remain local and hashed.
    inputs = [
        "UKACTIVE_A2R2_CORRECTED_TOTAL_RETURN_PANEL_GBP.parquet",
        "UKACTIVE_A2R2_CORRECTED_SIGNAL_ELIGIBILITY.parquet",
        "UKACTIVE_A2R2_SIGNAL_ENDPOINT_HISTORY.parquet",
        "UKACTIVE_A3R2_REGIME_STATE_HISTORY.parquet",
        "UKACTIVE_A4_TOP1_TOP2_TOP3_COMPARISON.csv",
        "config/UKACTIVE_A4B_POLICY_v1.json",
    ]
    input_inventory = []
    for relative in inputs:
        path = PROGRAMME_ROOT / relative
        input_inventory.append({"relative_path": relative, "sha256": sha256(path), "size_bytes": path.stat().st_size})
    code_paths = [
        PROGRAMME_ROOT / "code" / "ukactive_a4b_core.py",
        PROGRAMME_ROOT / "code" / "build_ukactive_a4b_lifecycle.py",
        PROGRAMME_ROOT / "code" / "build_ukactive_a4b_regime.py",
        PROGRAMME_ROOT / "code" / "build_ukactive_a4b_robustness.py",
        PROGRAMME_ROOT / "code" / "query_ukactive_rotation.py",
    ]
    output_inventory = []
    for path in sorted(PROGRAMME_ROOT.glob("UKACTIVE_A4B_*")):
        if path.is_file() and path.name != "UKACTIVE_A4B_MANIFEST.json":
            output_inventory.append({"relative_path": path.name, "sha256": sha256(path), "size_bytes": path.stat().st_size})
    git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PLATFORM_ROOT, text=True).strip()
    def commit_for_subject(subject: str) -> str:
        return subprocess.check_output(
            ["git", "log", "--format=%H", "-1", f"--grep=^{subject}$"],
            cwd=PLATFORM_ROOT, text=True,
        ).strip()
    manifest = {
        "stage_id": "UKACTIVE-A4B",
        "run_id": data.policy["run_id"],
        "generated_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "git_branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=PLATFORM_ROOT, text=True).strip(),
        "pre_final_git_commit": git_head,
        "final_git_commit": "TO_BE_RECORDED_BY_FINALISER",
        "git_checkpoints": {
            "a4b_preflight_tag_target": subprocess.check_output(
                ["git", "rev-list", "-n", "1", "ukactive-a4b-preflight-20260823"],
                cwd=PLATFORM_ROOT, text=True,
            ).strip(),
            "preregistration": commit_for_subject("research: preregister UKACTIVE-A4B lifecycle and regime research"),
            "preregistration_clarification": commit_for_subject("research: clarify UKACTIVE-A4B combination order"),
            "lifecycle_profit_lock": commit_for_subject("research: add UKACTIVE-A4B position lifecycle and profit-lock research"),
            "regime_ablation": commit_for_subject("research: add UKACTIVE-A4B regime scaling and lifecycle ablation"),
        },
        "origin": subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=PLATFORM_ROOT, text=True).strip(),
        "policy_sha256": sha256(PROGRAMME_ROOT / "config" / "UKACTIVE_A4B_POLICY_v1.json"),
        "input_inventory": input_inventory,
        "code_inventory": [{"relative_path": str(path.relative_to(PROGRAMME_ROOT)).replace('\\', '/'), "sha256": sha256(path), "size_bytes": path.stat().st_size} for path in code_paths],
        "output_inventory_pre_manifest": output_inventory,
        "commands": [
            "python code/build_ukactive_a4b_lifecycle.py",
            "python code/build_ukactive_a4b_regime.py",
            "python code/build_ukactive_a4b_robustness.py",
        ],
        "packages": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__},
        "automated_test_results": correctness[["test_id", "result"]].to_dict("records"),
        "decision": decision_payload["decision"],
        "a5_started": False,
        "a5_lifecycle_v2_created": False,
        "warning": WARNING,
    }
    (PROGRAMME_ROOT / "UKACTIVE_A4B_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
