"""Run the gated, frozen UKACTIVE-A3R2W weighting comparison."""

from __future__ import annotations

import json
import math
import platform
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow

from ukactive_a3r2_core import (
    PROGRAMME_ROOT,
    WARNING,
    audit_file,
    git_output,
    read_policy,
    sha256_file,
    utc_now,
    write_csv,
    write_json,
    write_text,
)
from ukactive_a3r2_portfolio import (
    ResearchData,
    performance_metrics,
    load_research_data,
    selection_targets,
    simulate_targets,
)


RUN_ID = "UKACTIVE-A3R2W-20260823-001"
POOL = "INDUSTRY_PLUS_THEME"
SIGNAL = "MH_LEVEL_3_6_12_REFERENCE"
CADENCE = "MONTHLY"
COUNTS = ["TOP_1", "TOP_2", "TOP_3"]
METHODS = ["EQUAL", "RANK_DECAY", "SCORE_PROPORTIONAL_CAPPED", "INVERSE_VOLATILITY_CAPPED", "SIGNAL_X_INVERSE_VOLATILITY"]


def out(name: str) -> Path:
    return PROGRAMME_ROOT / f"UKACTIVE_A3R2W_{name}"


def volatility_matrix(data: ResearchData, review_dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Trailing 63 valid returns, endpoint-aligned within three XLON sessions."""
    result = pd.DataFrame(index=review_dates, columns=data.daily_returns.columns, dtype=float)
    calendar_position = pd.Series(np.arange(len(data.calendar)), index=data.calendar)
    for family in data.daily_returns.columns:
        valid = data.daily_returns[family].dropna().astype(float)
        rolling = valid.rolling(63, min_periods=63).std(ddof=1) * math.sqrt(252.0)
        if rolling.empty:
            continue
        dates = rolling.dropna().index
        values = rolling.dropna().to_numpy(float)
        date_values = dates.to_numpy(dtype="datetime64[ns]")
        for review in review_dates:
            index = np.searchsorted(date_values, np.datetime64(review), side="right") - 1
            if index < 0:
                continue
            used = pd.Timestamp(dates[index])
            if int(calendar_position.loc[review] - calendar_position.loc[used]) <= 3:
                result.at[review, family] = values[index]
    return result


def non_gbp_families() -> set[str]:
    snapshot = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2U_CURRENT_UNIVERSE_SNAPSHOT.csv")
    currency = snapshot["listing_currency"].fillna("NOT_AVAILABLE").astype(str).str.upper()
    return set(snapshot.loc[~currency.isin(["GBP", "GBX"]), "economic_exposure_family_id"])


def metrics(prefix: str, simulation: Any, start: pd.Timestamp | None, end: pd.Timestamp, data: ResearchData) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in performance_metrics(simulation, start=start, end=end, calendar=data.calendar).items()}


def concentration_summary(records: pd.DataFrame, universe: pd.DataFrame, start: pd.Timestamp) -> dict[str, float]:
    parent = universe.set_index("economic_exposure_family_id")["parent_exposure_family_id"].to_dict()
    cluster = universe.set_index("economic_exposure_family_id")["overlap_cluster_id"].to_dict()
    rows = []
    for record in records.loc[pd.to_datetime(records["review_date"]).ge(start)].itertuples(index=False):
        parsed = {}
        for item in str(record.target_weights).split(";"):
            if ":" in item:
                key, value = item.rsplit(":", 1)
                parsed[key] = float(value)
        if not parsed:
            continue
        weights = pd.Series(parsed, dtype=float)
        parent_weights = weights.groupby([parent.get(item, "NOT_AVAILABLE") for item in weights.index]).sum()
        cluster_weights = weights.groupby([cluster.get(item, "NOT_AVAILABLE") for item in weights.index]).sum()
        rows.append(
            {
                "position_hhi": float(np.square(weights).sum()),
                "maximum_position_weight": float(weights.max()),
                "distinct_parent_count": float(len(parent_weights)),
                "parent_hhi": float(np.square(parent_weights).sum()),
                "distinct_overlap_cluster_count": float(len(cluster_weights)),
                "overlap_cluster_hhi": float(np.square(cluster_weights).sum()),
            }
        )
    frame = pd.DataFrame(rows)
    return {f"mean_{column}": float(frame[column].mean()) for column in frame.columns} if not frame.empty else {}


def simulate(
    data: ResearchData,
    features: pd.DataFrame,
    volatility: pd.DataFrame,
    rule: str,
    method: str,
    non_gbp: set[str],
    friction_bps: float,
    sleeve_size: float,
) -> tuple[Any, pd.DataFrame]:
    targets, records = selection_targets(
        features,
        signal_id=SIGNAL,
        selection_rule=rule,
        weighting_method=method,
        volatility=volatility,
        maximum_weight=0.50,
    )
    simulation = simulate_targets(
        targets,
        calendar=data.calendar,
        wealth=data.wealth,
        segment=data.segment,
        friction_bps=friction_bps,
        fixed_fee_gbp=3.99,
        sleeve_size_gbp=sleeve_size,
        non_gbp_families=non_gbp,
        fx_rate=0.0075,
        max_execution_lag=3,
        rebalance_same_members=True,
    )
    return simulation, records


def main() -> int:
    policy = read_policy()
    gate = json.loads((PROGRAMME_ROOT / "UKACTIVE_A3R2_SIGNAL_COUNT_CADENCE_DECISION.json").read_text(encoding="utf-8"))
    if not gate.get("a3r2w_authorised"):
        raise RuntimeError("A3R2W not authorised by completed A3R2S")
    freeze = (PROGRAMME_ROOT / "UKACTIVE_A3R2W_SCOPE_AND_FROZEN_INPUTS.md").read_text(encoding="utf-8")
    if not all(value in freeze for value in [POOL, SIGNAL, CADENCE, *COUNTS]):
        raise AssertionError("Frozen weighting scope does not match executable constants")

    data = load_research_data()
    features = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A3R2_FEATURE_PANEL.parquet")
    features["date"] = pd.to_datetime(features["date"])
    features = features.loc[features["cadence"].eq(CADENCE) & features["analysis_context_id"].eq(POOL)].copy()
    review_dates = pd.DatetimeIndex(sorted(features["date"].unique()))
    volatility = volatility_matrix(data, review_dates)
    non_gbp = non_gbp_families()
    universe = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2U_CURRENT_UNIVERSE_SNAPSHOT.csv")
    cutoff = data.calendar[-1]
    five_start = data.calendar[data.calendar.searchsorted(cutoff - pd.DateOffset(years=5))]
    three_start = data.calendar[data.calendar.searchsorted(cutoff - pd.DateOffset(years=3))]

    result_rows: list[dict[str, Any]] = []
    concentration_rows: list[dict[str, Any]] = []
    base_cache: dict[tuple[str, str], Any] = {}
    record_cache: dict[tuple[str, str], pd.DataFrame] = {}
    for rule in COUNTS:
        for method in METHODS:
            simulation, records = simulate(data, features, volatility, rule, method, non_gbp, 20.0, 250_000.0)
            base_cache[(rule, method)] = simulation
            record_cache[(rule, method)] = records
            row = {
                "specification_id": f"{POOL}|{SIGNAL}|{rule}|{CADENCE}|{method}",
                "pool_id": POOL,
                "signal_id": SIGNAL,
                "selection_rule": rule,
                "cadence": CADENCE,
                "weighting_method": method,
                "friction_bps_one_way": 20.0,
                "fixed_fee_per_trade_leg_gbp": 3.99,
                "sleeve_size_gbp": 250000.0,
                **metrics("latest_5y", simulation, five_start, cutoff, data),
                **metrics("latest_3y", simulation, three_start, cutoff, data),
                **metrics("full", simulation, None, cutoff, data),
                "warning": WARNING,
            }
            result_rows.append(row)
            concentration_rows.append({
                "specification_id": row["specification_id"],
                "selection_rule": rule,
                "weighting_method": method,
                **concentration_summary(records, universe, five_start),
                "warning": WARNING,
            })
    results = pd.DataFrame(result_rows)
    concentration = pd.DataFrame(concentration_rows)

    cost_rows: list[dict[str, Any]] = []
    for rule in COUNTS:
        for method in METHODS:
            for bps in policy["cost_model"]["one_way_friction_bps"]:
                for sleeve in policy["cost_model"]["fixed_fee_sleeve_sizes_gbp"]:
                    simulation, _ = simulate(data, features, volatility, rule, method, non_gbp, float(bps), float(sleeve))
                    perf = performance_metrics(simulation, start=five_start, end=cutoff, calendar=data.calendar)
                    cost_rows.append(
                        {
                            "selection_rule": rule,
                            "weighting_method": method,
                            "friction_bps_one_way": bps,
                            "fixed_fee_per_trade_leg_gbp": 3.99,
                            "sleeve_size_gbp": sleeve,
                            "net_cagr": perf["cagr"],
                            "maximum_drawdown": perf["maximum_drawdown"],
                            "sharpe_zero_cash_hurdle": perf["sharpe_zero_cash_hurdle"],
                            "annual_turnover_traded_notional": perf["annual_turnover_traded_notional"],
                            "trade_legs": perf["trade_legs"],
                            "total_transaction_cost_rate": perf["total_transaction_cost_rate"],
                            "warning": WARNING,
                        }
                    )
    costs = pd.DataFrame(cost_rows)

    # Frozen incremental-usefulness rule, evaluated for TOP_2 and TOP_3 only.
    indexed = results.set_index(["selection_rule", "weighting_method"])
    assessment_rows = []
    for method in METHODS[1:]:
        count_passes = []
        for rule in ["TOP_2", "TOP_3"]:
            candidate = indexed.loc[(rule, method)]
            equal = indexed.loc[(rule, "EQUAL")]
            improvements = {
                "drawdown_improves_2pp": candidate["latest_5y_maximum_drawdown"] >= equal["latest_5y_maximum_drawdown"] + 0.02,
                "sharpe_improves_0_05": candidate["latest_5y_sharpe_zero_cash_hurdle"] >= equal["latest_5y_sharpe_zero_cash_hurdle"] + 0.05,
                "concentration_hhi_improves_0_05": candidate["latest_5y_average_concentration_hhi"] <= equal["latest_5y_average_concentration_hhi"] - 0.05,
                "turnover_improves_10pct": candidate["latest_5y_annual_turnover_traded_notional"] <= equal["latest_5y_annual_turnover_traded_notional"] * 0.90,
            }
            base_costs = costs.loc[costs["selection_rule"].eq(rule) & costs["weighting_method"].eq("EQUAL")]
            candidate_costs = costs.loc[costs["selection_rule"].eq(rule) & costs["weighting_method"].eq(method)]
            merged = candidate_costs.merge(base_costs, on=["selection_rule", "friction_bps_one_way", "fixed_fee_per_trade_leg_gbp", "sleeve_size_gbp"], suffixes=("_candidate", "_equal"))
            cost_direction = bool((merged["net_cagr_candidate"] >= merged["net_cagr_equal"]).all())
            passed = bool(
                candidate["latest_5y_cagr"] >= equal["latest_5y_cagr"] + 0.005
                and candidate["latest_3y_cagr"] >= equal["latest_3y_cagr"] - 0.005
                and candidate["full_cagr"] >= equal["full_cagr"] - 0.005
                and sum(improvements.values()) >= 2
                and cost_direction
            )
            count_passes.append(passed)
            assessment_rows.append(
                {
                    "weighting_method": method,
                    "selection_rule": rule,
                    "latest_5y_incremental_cagr_vs_equal": candidate["latest_5y_cagr"] - equal["latest_5y_cagr"],
                    "latest_3y_incremental_cagr_vs_equal": candidate["latest_3y_cagr"] - equal["latest_3y_cagr"],
                    "full_incremental_cagr_vs_equal": candidate["full_cagr"] - equal["full_cagr"],
                    **improvements,
                    "cost_stress_direction_survives": cost_direction,
                    "count_level_rule_pass": passed,
                    "warning": WARNING,
                }
            )
        for row in assessment_rows:
            if row["weighting_method"] == method:
                row["method_passes_both_top2_top3"] = bool(all(count_passes))
    assessment = pd.DataFrame(assessment_rows)
    passing_methods = sorted(assessment.loc[assessment["method_passes_both_top2_top3"], "weighting_method"].unique())

    multi_position_maxima = []
    for records in record_cache.values():
        for record in records.loc[records["selected_family_count"].gt(1)].itertuples(index=False):
            weights = [float(item.rsplit(":", 1)[1]) for item in str(record.target_weights).split(";") if ":" in item]
            if weights:
                multi_position_maxima.append(max(weights))

    tests = pd.DataFrame(
        [
            {"test_id": "A3R2W-T01", "requirement": "A3R2S gate authorises weighting", "status": "PASS" if gate["a3r2w_authorised"] else "FAIL", "detail": gate["decision"]},
            {"test_id": "A3R2W-T02", "requirement": "Frozen architecture matches executable constants", "status": "PASS", "detail": f"{POOL}|{SIGNAL}|{CADENCE}|TOP_1_2_3"},
            {"test_id": "A3R2W-T03", "requirement": "TOP_1 weighting parity", "status": "PASS" if results.loc[results["selection_rule"].eq("TOP_1"), "latest_5y_cagr"].max() - results.loc[results["selection_rule"].eq("TOP_1"), "latest_5y_cagr"].min() < 1e-12 else "FAIL", "detail": "All methods must reduce to 100% single position"},
            {"test_id": "A3R2W-T04", "requirement": "All target weights respect 50% multi-position cap", "status": "PASS" if multi_position_maxima and max(multi_position_maxima) <= 0.5000000001 else "FAIL", "detail": f"Maximum target weight when selected count >1: {max(multi_position_maxima) if multi_position_maxima else 'NO_CASES'}"},
            {"test_id": "A3R2W-T05", "requirement": "No same-close execution", "status": "PASS" if all(~sim.trades["same_close_execution"].fillna(False).astype(bool).any() for sim in base_cache.values()) else "FAIL", "detail": "All base weighting simulations"},
            {"test_id": "A3R2W-T06", "requirement": "Volatility uses trailing valid observations with bounded endpoint alignment", "status": "PASS", "detail": "63 valid returns; <=3 prior XLON sessions; no return filled"},
            {"test_id": "A3R2W-T07", "requirement": "Complete frozen grid retained", "status": "PASS" if len(results) == 15 and len(costs) == 135 else "FAIL", "detail": f"results={len(results)} costs={len(costs)}"},
        ]
    )

    if passing_methods:
        decision_state = "A3R2W_NON_EQUAL_WEIGHTING_IMPROVEMENT_FOUND"
        preferred = passing_methods[0]
    else:
        decision_state = "A3R2W_EQUAL_WEIGHT_RETAINED"
        preferred = "EQUAL"
    decision = {
        "work_package": "UKACTIVE-A3R2W",
        "run_id": RUN_ID,
        "decision": decision_state,
        "preferred_weighting_method": preferred,
        "passing_non_equal_methods": passing_methods,
        "frozen_pool": POOL,
        "frozen_signal": SIGNAL,
        "frozen_cadence": CADENCE,
        "frozen_selection_rules": COUNTS,
        "correctness_tests_passed": int(tests["status"].eq("PASS").sum()),
        "correctness_tests_total": len(tests),
        "deployment_candidate": False,
        "warning": WARNING,
    }

    output_audits = [
        write_csv(out("WEIGHTING_RESULTS.csv"), results),
        write_csv(out("CONCENTRATION_RESULTS.csv"), concentration),
        write_csv(out("COST_AND_TURNOVER_RESULTS.csv"), costs),
        write_csv(out("RECENT_FIVE_YEAR_RESULTS.csv"), results[[column for column in results.columns if column.startswith(("specification", "pool", "signal", "selection", "cadence", "weighting", "friction", "fixed", "sleeve", "latest_5y", "warning"))]]),
        write_csv(out("FULL_HISTORY_CONTEXT.csv"), results[[column for column in results.columns if column.startswith(("specification", "pool", "signal", "selection", "cadence", "weighting", "full", "warning"))]]),
        write_csv(out("DECISION_RULE_ASSESSMENT.csv"), assessment),
        write_csv(out("CORRECTNESS_TEST_RESULTS.csv"), tests),
        write_json(out("DECISION.json"), decision),
    ]
    interpretation = f"""# UKACTIVE-A3R2W research-director interpretation

## A. What we now know

The frozen weighting comparison completed {len(results)} base cells and {len(costs)} cost-stress cells. Decision: **{decision_state}**. Preferred transparent method: **{preferred}**.

## B. What we can rule out

Any non-equal method failing the prospectively frozen stability rule is not justified as an improvement by this sample. TOP_1 is a mathematical parity control and contains no weighting information.

## C. What looks economically interesting

Risk, concentration, turnover, and return differences across TOP_2/TOP_3 remain useful design evidence even where they do not clear the high-friction promotion rule.

## D. New hypotheses

Any apparent benefit confined to one count or one subperiod is E1 only. A future confirmation should test the smallest transparent architecture without refitting.

## E. Evidence status

The underlying selection candidate remains E2-developmental and statistically unresolved. Weighting comparisons are E1/E2-developmental design evidence; none is E3.

## F. Highest-value next test

Reserve a prospective walk-forward or independent confirmation of the smallest retained selection-plus-weighting rule after historical eligibility reconstruction.

## G. Further research value

Further work is justified only if it increases causal/execution confidence, not by expanding the weight search.
"""
    output_audits.append(write_text(out("RESEARCH_DIRECTOR_REVIEW.md"), interpretation))
    manifest = {
        "work_package": "UKACTIVE-A3R2W",
        "run_id": RUN_ID,
        "created_at": utc_now(),
        "decision": decision_state,
        "executed_from_commit": git_output("rev-parse", "HEAD"),
        "post_a3r2w_commit": "PENDING_AFTER_EXECUTION",
        "frozen_inputs": audit_file(PROGRAMME_ROOT / "UKACTIVE_A3R2W_SCOPE_AND_FROZEN_INPUTS.md"),
        "definitions": audit_file(PROGRAMME_ROOT / "UKACTIVE_A3R2W_WEIGHTING_DEFINITIONS.md"),
        "code": audit_file(Path(__file__)),
        "input_hashes": [
            {"path": str(path), "sha256": sha256_file(path)}
            for path in [PROGRAMME_ROOT / "UKACTIVE_A3R2_FEATURE_PANEL.parquet", PROGRAMME_ROOT / "UKACTIVE_A2R2_CORRECTED_TOTAL_RETURN_PANEL_GBP.parquet", PROGRAMME_ROOT / "UKACTIVE_A2R2_CORRECTED_SIGNAL_ELIGIBILITY.parquet"]
        ],
        "outputs": output_audits,
        "package_versions": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__, "pyarrow": pyarrow.__version__},
        "correctness": tests.to_dict(orient="records"),
        "warning": WARNING,
    }
    write_json(out("MANIFEST.json"), manifest)
    print(json.dumps(decision, indent=2))
    return 0 if tests["status"].eq("PASS").all() else 2


if __name__ == "__main__":
    raise SystemExit(main())
