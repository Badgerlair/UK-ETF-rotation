from __future__ import annotations

import json
import math
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow
import scipy

import build_ukactive_a3r1 as a3
from ukactive_a2r2_core import same_segment_complete_window, sha256_file, utc_now


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_ROOT = PROGRAMME_ROOT.parents[2]
PREFIX = "UKACTIVE_A3R1R1"
STAGE_ID = "UKACTIVE-A3R1R1"
RUN_ID = "UKACTIVE-A3R1R1-20260823-001"
A2R2_COMMIT = "0a5d32896e777c806dd3485650da1cd4d7660832"
WARNING = a3.WARNING


def output_path(suffix: str) -> Path:
    return PROGRAMME_ROOT / f"{PREFIX}_{suffix}"


def load_inputs() -> a3.Inputs:
    base = a3.load_inputs()
    panel = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A2R2_CORRECTED_TOTAL_RETURN_PANEL_GBP.parquet")
    panel["date"] = pd.to_datetime(panel["date"])
    calendar_frame = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A2R2_XLON_RESEARCH_CALENDAR.csv")
    calendar_frame["date"] = pd.to_datetime(calendar_frame["date"])
    calendar = pd.DatetimeIndex(
        calendar_frame.loc[calendar_frame["a2r2_official_xlon_session"].astype(str).str.lower().eq("true"), "date"]
    ).sort_values()
    return a3.Inputs(
        base.policy,
        base.registry,
        panel,
        calendar,
        base.roles,
        base.pools,
        base.parent_map,
        base.overlap,
        base.global_map,
        base.dynamic,
        base.selectable,
    )


def _pivot(eligibility: pd.DataFrame, column: str, calendar: pd.DatetimeIndex, all_needed: list[str]) -> pd.DataFrame:
    return eligibility.pivot(index="date", columns="economic_exposure_family_id", values=column).reindex(index=calendar, columns=all_needed)


def build_matrices(inputs: a3.Inputs, metadata: pd.DataFrame) -> tuple[a3.Matrices, pd.DataFrame]:
    eligibility = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A2R2_CORRECTED_SIGNAL_ELIGIBILITY.parquet")
    eligibility["date"] = pd.to_datetime(eligibility["date"])
    all_needed = sorted(
        set(metadata["economic_exposure_family_id"])
        | set(metadata["effective_parent_benchmark_family_id"])
        | {"GLOBAL_DEVELOPED_WORLD", "GLOBAL_ALL_WORLD"}
    )
    eligibility = eligibility.loc[eligibility["economic_exposure_family_id"].isin(all_needed)].copy()
    if eligibility.duplicated(["date", "economic_exposure_family_id"]).any():
        raise AssertionError("A2R2 signal endpoint history is not unique by family/date")

    returns = _pivot(eligibility, "return_since_prior_valid_endpoint", inputs.calendar, all_needed).astype(float)
    valid = _pivot(eligibility, "endpoint_valid", inputs.calendar, all_needed).fillna(False).astype(bool)
    accrued_valid = valid.cumsum()
    level = _pivot(eligibility, "signal_wealth_index_gbp", inputs.calendar, all_needed).astype(float)
    segment = _pivot(eligibility, "continuity_segment_id", inputs.calendar, all_needed).astype(float)
    cumulative_returns = {
        horizon: _pivot(eligibility, f"formation_return_{horizon}", inputs.calendar, all_needed).astype(float)
        for horizon in a3.ALL_FORMATION_HORIZONS
    }
    relative_strength = {
        horizon: a3.relative_return(cumulative_returns[horizon], cumulative_returns[horizon]["GLOBAL_DEVELOPED_WORLD"])
        for horizon in a3.ALL_FORMATION_HORIZONS
    }
    raw_segments = {
        "REL_SEG_0_1M": cumulative_returns[21],
        "REL_SEG_1_2M": (1.0 + cumulative_returns[42]) / (1.0 + cumulative_returns[21]) - 1.0,
        "REL_SEG_2_3M": (1.0 + cumulative_returns[63]) / (1.0 + cumulative_returns[42]) - 1.0,
        "REL_SEG_3_6M": (1.0 + cumulative_returns[126]) / (1.0 + cumulative_returns[63]) - 1.0,
        "REL_SEG_6_12M": (1.0 + cumulative_returns[252]) / (1.0 + cumulative_returns[126]) - 1.0,
    }
    segments = {key: a3.relative_return(frame, frame["GLOBAL_DEVELOPED_WORLD"]) for key, frame in raw_segments.items()}
    forward_returns = {
        horizon: _pivot(eligibility, f"forward_return_{horizon}", inputs.calendar, all_needed).astype(float)
        for horizon in a3.FORWARD_HORIZONS
    }
    global_forward = {horizon: frame["GLOBAL_DEVELOPED_WORLD"] for horizon, frame in forward_returns.items()}

    benchmark_level = level["GLOBAL_DEVELOPED_WORLD"]
    benchmark_segment = segment["GLOBAL_DEVELOPED_WORLD"]
    relative_log = np.log(level).sub(np.log(benchmark_level), axis=0)
    relative_valid = level.notna().mul(benchmark_level.notna(), axis=0)
    relative_features: dict[str, pd.DataFrame] = {}
    for window in [21, 42, 63]:
        slope, r_squared = a3.rolling_ols_slope_r2(relative_log, window)
        complete = same_segment_complete_window(relative_valid, segment, window)
        benchmark_complete = same_segment_complete_window(
            benchmark_level.notna().to_frame("GLOBAL_DEVELOPED_WORLD"),
            benchmark_segment.to_frame("GLOBAL_DEVELOPED_WORLD"),
            window,
        )["GLOBAL_DEVELOPED_WORLD"]
        complete = complete.mul(benchmark_complete, axis=0)
        relative_features[f"REL_SLOPE_{window}"] = slope.where(complete)
        relative_features[f"REL_R2_{window}"] = r_squared.where(complete)
    relative_features["RELATIVE_SLOPE_CHANGE"] = relative_features["REL_SLOPE_21"] - relative_features["REL_SLOPE_21"].shift(21)
    relative_index = np.exp(relative_log.clip(-30, 30))
    for window in [21, 50]:
        complete = same_segment_complete_window(relative_valid, segment, window)
        benchmark_complete = same_segment_complete_window(
            benchmark_level.notna().to_frame("GLOBAL_DEVELOPED_WORLD"),
            benchmark_segment.to_frame("GLOBAL_DEVELOPED_WORLD"),
            window,
        )["GLOBAL_DEVELOPED_WORLD"]
        complete = complete.mul(benchmark_complete, axis=0)
        relative_features[f"REL_DISTANCE_MA_{window}"] = (
            relative_index / relative_index.rolling(window, min_periods=window).mean() - 1.0
        ).where(complete)
    complete63 = same_segment_complete_window(relative_valid, segment, 63)
    benchmark_complete63 = same_segment_complete_window(
        benchmark_level.notna().to_frame("GLOBAL_DEVELOPED_WORLD"),
        benchmark_segment.to_frame("GLOBAL_DEVELOPED_WORLD"),
        63,
    )["GLOBAL_DEVELOPED_WORLD"]
    complete63 = complete63.mul(benchmark_complete63, axis=0)
    relative_features["REL_DISTANCE_HIGH_63"] = (
        relative_index / relative_index.rolling(63, min_periods=63).max() - 1.0
    ).where(complete63)

    log_level = np.log(level)
    log_slope_63, log_r2_63 = a3.rolling_ols_slope_r2(log_level, 63)
    price_complete63 = same_segment_complete_window(level.notna(), segment, 63)
    price_features = {
        "LOG_PRICE_SLOPE_63": log_slope_63.where(price_complete63),
        "LOG_PRICE_R2_63": log_r2_63.where(price_complete63),
        "REALISED_VOL_63": returns.rolling(63, min_periods=63).std(ddof=1).mul(math.sqrt(252)).where(price_complete63),
        "PRICE_DISTANCE_HIGH_63": (level / level.rolling(63, min_periods=63).max() - 1.0).where(price_complete63),
    }
    weekly_positions_array = a3.weekly_last_positions(inputs.calendar)
    weekly_dates = inputs.calendar[weekly_positions_array]
    return (
        a3.Matrices(
            returns, valid, accrued_valid, cumulative_returns, relative_strength, segments,
            forward_returns, global_forward, relative_features, price_features,
            weekly_positions_array, weekly_dates,
        ),
        eligibility,
    )


def run_correctness_tests(
    inputs: a3.Inputs,
    matrices: a3.Matrices,
    metadata: pd.DataFrame,
    group_features: pd.DataFrame,
    retained: pd.DataFrame,
    ledger: pd.DataFrame,
    eligibility: pd.DataFrame,
) -> pd.DataFrame:
    tests = a3.run_correctness_tests(inputs, matrices, metadata, group_features, retained, ledger).copy()

    def replace(test_id: str, passed: bool, detail: str) -> None:
        mask = tests["test_id"].eq(test_id)
        tests.loc[mask, "status"] = "PASS" if passed else "FAIL"
        tests.loc[mask, "detail"] = detail

    endpoint_valid = eligibility["endpoint_valid"].fillna(False).astype(bool)
    stale_missing_proxy = (
        eligibility["stale_flag"].fillna(False).astype(bool)
        | eligibility["missing_flag"].fillna(True).astype(bool)
        | eligibility["proxy_flag"].fillna(False).astype(bool)
    )
    replace(
        "A3R1-T04",
        all(
            not (
                matrices.cumulative_returns[horizon].notna()
                & ~matrices.valid
            ).any().any()
            for horizon in a3.MAIN_FORMATION_HORIZONS
        ),
        "A2R2 endpoint formations require an exact valid signal-date endpoint, a same-segment historical endpoint, and horizon-specific 21/42/63/126/252 history; no 504 gate",
    )
    a2r2_decision = json.loads((PROGRAMME_ROOT / "UKACTIVE_A2R2_DECISION.json").read_text(encoding="utf-8"))
    replace(
        "A3R1-T05",
        a2r2_decision["decision"] == "UKACTIVE_A2R2_PASS",
        "Only A2R2 endpoint history derived from the corrected A2R lineage enters A3R1R1",
    )
    replace(
        "A3R1-T14",
        not bool((endpoint_valid & stale_missing_proxy).any()),
        f"{int(endpoint_valid.sum())} valid A2R2 endpoints exclude every stale, missing and proxy row; daily-return invalidity remains separately represented",
    )
    role_rows = group_features.loc[group_features["analysis_context_type"].eq("ROLE_GROUP")]
    warmup_ok = True
    checked = 0
    for horizon in a3.MAIN_FORMATION_HORIZONS:
        score = f"SIGNAL_RS_{horizon}"
        first_scores = role_rows.loc[role_rows[score].notna()].groupby("economic_exposure_family_id")["date"].min()
        for family, date in first_scores.items():
            checked += 1
            warmup_ok &= pd.notna(matrices.cumulative_returns[horizon].at[date, family])
            warmup_ok &= pd.notna(matrices.cumulative_returns[horizon].at[date, "GLOBAL_DEVELOPED_WORLD"])
            warmup_ok &= bool(matrices.valid.at[date, family])
    replace(
        "A3R1-T16",
        warmup_ok,
        f"{checked} first admissions have a valid contemporaneous endpoint and their exact signal-specific formation return",
    )
    additional = pd.DataFrame(
        [
            {
                "test_id": "A3R1R1-T21",
                "requirement": "A2R2 modern long-horizon coverage enters the frozen rerun",
                "status": "PASS" if matrices.cumulative_returns[252].loc[pd.Timestamp("2026-08-21")].notna().sum() >= 80 else "FAIL",
                "detail": f"{int(matrices.cumulative_returns[252].loc[pd.Timestamp('2026-08-21')].notna().sum())} required-family/benchmark 252-session formations are valid at the latest date",
                "critical": "YES",
                "executed_at": utc_now(),
            },
            {
                "test_id": "A3R1R1-T22",
                "requirement": "Frozen A3R1 policy and registry hashes are unchanged",
                "status": "PASS",
                "detail": f"policy={sha256_file(PROGRAMME_ROOT / 'config' / 'UKACTIVE_A3R1_POLICY_v1.json')}|registry={sha256_file(PROGRAMME_ROOT / 'UKACTIVE_A3R1_SIGNAL_REGISTRY.csv')}",
                "critical": "YES",
                "executed_at": utc_now(),
            },
        ]
    )
    return pd.concat([tests, additional], ignore_index=True)


def write_statistical_inference(top_tail: pd.DataFrame, ledger: pd.DataFrame, support: pd.DataFrame) -> Path:
    primary = top_tail.loc[top_tail["primary_fdr_family"].eq("YES")]
    formal = primary.loc[primary["formal_inference_eligible"].eq("YES")]
    path = output_path("STATISTICAL_INFERENCE.md")
    lines = [
        "# UKACTIVE-A3R1R1 statistical inference",
        "",
        "This is the unchanged preregistered A3R1 experiment rerun after A2R2 data remediation. The primary estimand remains the weekly date-level equal-weight top-three forward-return advantage versus GLOBAL_DEVELOPED_WORLD. Newey–West/HAC, circular block bootstrap, Benjamini–Hochberg scope, minimum observations and promotion thresholds are unchanged.",
        "",
        f"The primary FDR family contains {len(primary)} cells; {len(formal)} meet the preregistered formal-inference minimum. {int((formal['advantage_vs_global_bh_q_value'] <= 0.10).sum())} survive q ≤ 0.10 and {int((formal['advantage_vs_global_bootstrap_ci_low'] > 0).sum())} have a positive 95% block-bootstrap lower bound.",
        "",
        f"The complete ledger retains {len(ledger):,} executed rows. Failed, negative and sub-minimum cells are preserved.",
        "",
        "## Signal-level support",
        "",
        support.to_markdown(index=False),
        "",
        "This is signal research, not an historically verified UK-investable strategy or deployment result.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_candidate_report(candidates: pd.DataFrame, decision: dict[str, Any]) -> Path:
    path = output_path("RESEARCH_CANDIDATES.md")
    display = candidates[
        ["signal_id", "signal_family", "criteria_passed", "criteria_total", "qualifying_group_ids", "fdr_surviving_cell_count", "classification"]
    ]
    lines = [
        "# UKACTIVE-A3R1R1 research candidates",
        "",
        f"Decision: **{decision['decision']}**",
        "",
        display.to_markdown(index=False),
        "",
        "The A3R1 specification is unchanged. `PORTFOLIO_WEIGHTING_NOT_OPTIMISED`. Candidate status is research-only and does not establish historical UK retail/account/broker eligibility.",
        "",
        f"A3R2 scientific authorisation: **{'YES' if decision['a3r2_scientifically_supported'] else 'NO'}**. A3R2 was not executed.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_scope() -> Path:
    path = output_path("SCOPE_AND_FROZEN_SPECIFICATION.md")
    a3_policy = PROGRAMME_ROOT / "config" / "UKACTIVE_A3R1_POLICY_v1.json"
    registry = PROGRAMME_ROOT / "UKACTIVE_A3R1_SIGNAL_REGISTRY.csv"
    lines = [
        "# UKACTIVE-A3R1R1 scope and frozen specification",
        "",
        "A3R1R1 is the exact preregistered A3R1 experiment repeated on the A2R2-remediated formation-history adapter. No signal, weight, horizon, ranking rule, pool, benchmark, weekly schedule, top-tail definition, forward horizon, inference method or promotion criterion changed.",
        "",
        f"Frozen policy SHA-256: `{sha256_file(a3_policy)}`.",
        f"Frozen registry SHA-256: `{sha256_file(registry)}`.",
        f"A2R2 remediation commit: `{A2R2_COMMIT}`.",
        "",
        "The prior A3R1 outputs remain preserved and are invalid for efficacy conclusions because modern long-horizon coverage failed. Historical UK retail/account/broker eligibility remains unresolved. A3R2 is not executed here.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_manifest(
    inputs: a3.Inputs,
    decision: dict[str, Any],
    tests: pd.DataFrame,
    ledger: pd.DataFrame,
    output_audit: list[dict[str, Any]],
) -> dict[str, Any]:
    input_paths = [
        PROGRAMME_ROOT / "UKACTIVE_A2R2_CORRECTED_SIGNAL_ELIGIBILITY.parquet",
        PROGRAMME_ROOT / "UKACTIVE_A2R2_SIGNAL_ENDPOINT_HISTORY.parquet",
        PROGRAMME_ROOT / "UKACTIVE_A2R2_DECISION.json",
        PROGRAMME_ROOT / "UKACTIVE_A2R2_MANIFEST.json",
        PROGRAMME_ROOT / "config" / "UKACTIVE_A3R1_POLICY_v1.json",
        PROGRAMME_ROOT / "UKACTIVE_A3R1_SIGNAL_REGISTRY.csv",
        PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_ROTATION_ROLE_MASTER_POST_A2R.csv",
        PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_PARENT_BENCHMARK_MAP_POST_A2R.csv",
    ]
    code_paths = [
        Path(__file__).resolve(),
        Path(__file__).resolve().with_name("build_ukactive_a3r1.py"),
        Path(__file__).resolve().with_name("ukactive_a3r1_core.py"),
        Path(__file__).resolve().with_name("ukactive_a2r2_core.py"),
    ]
    return {
        "stage_id": STAGE_ID,
        "run_id": RUN_ID,
        "created_at": utc_now(),
        "repository_root": str(PLATFORM_ROOT),
        "git_branch": a3.git_value("branch", "--show-current"),
        "pre_a2r2_checkpoint_commit": "f9597c3d3f95e5de5c55da92721a93771aeeadf6",
        "a2r2_remediation_commit": A2R2_COMMIT,
        "post_a3r1r1_result_commit": "PENDING_AFTER_EXECUTION",
        "remote_count": 0,
        "pushed_to_github": False,
        "rerun_of": "UKACTIVE-A3R1",
        "original_a3r1_decision": json.loads((PROGRAMME_ROOT / "UKACTIVE_A3R1_DECISION.json").read_text(encoding="utf-8"))["decision"],
        "original_a3r1_efficacy_status": "A3R1_PRE_REMEDIATION_INVALID_FOR_EFFICACY_CONCLUSION",
        "specification_frozen": True,
        "frozen_a3r1_policy_sha256": sha256_file(PROGRAMME_ROOT / "config" / "UKACTIVE_A3R1_POLICY_v1.json"),
        "frozen_a3r1_registry_sha256": sha256_file(PROGRAMME_ROOT / "UKACTIVE_A3R1_SIGNAL_REGISTRY.csv"),
        "inputs": [{"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in input_paths],
        "executed_source_hashes": {path.name: sha256_file(path) for path in code_paths},
        "output_artifacts_excluding_self": output_audit,
        "command_lines": [f'{sys.executable} "{Path(__file__).resolve()}"'],
        "signal_registry_rows": int(len(inputs.registry)),
        "complete_specification_ledger_rows": int(len(ledger)),
        "formation_horizons_sessions": a3.MAIN_FORMATION_HORIZONS,
        "forward_horizons_sessions": a3.FORWARD_HORIZONS,
        "multi_horizon_weights": inputs.policy["multi_horizon_weights"],
        "observation_frequency": inputs.policy["calendar_and_timing"]["observation_frequency"],
        "correctness_test_results": tests.to_dict("records"),
        "decision": decision["decision"],
        "package_versions": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "pyarrow": pyarrow.__version__,
        },
        "historical_eligibility_resolved": False,
        "portfolio_research_performed": False,
        "a3r2_executed": False,
        "warning": WARNING,
    }


def main() -> int:
    print("A3R1R1: verifying A2R2 PASS and frozen preregistration", flush=True)
    a2r2_decision = json.loads((PROGRAMME_ROOT / "UKACTIVE_A2R2_DECISION.json").read_text(encoding="utf-8"))
    if a2r2_decision["decision"] != "UKACTIVE_A2R2_PASS" or not a2r2_decision["a3r1r1_authorised"]:
        raise AssertionError("A2R2 did not authorise A3R1R1")
    a2r2_manifest = json.loads((PROGRAMME_ROOT / "UKACTIVE_A2R2_MANIFEST.json").read_text(encoding="utf-8"))
    if sha256_file(PROGRAMME_ROOT / "config" / "UKACTIVE_A3R1_POLICY_v1.json") != a2r2_manifest["frozen_a3r1_policy_sha256"]:
        raise AssertionError("Frozen A3R1 policy changed after A2R2")
    if sha256_file(PROGRAMME_ROOT / "UKACTIVE_A3R1_SIGNAL_REGISTRY.csv") != a2r2_manifest["frozen_a3r1_registry_sha256"]:
        raise AssertionError("Frozen A3R1 registry changed after A2R2")

    inputs = load_inputs()
    metadata = a3.candidate_metadata(inputs)
    if len(metadata) != 82:
        raise AssertionError(f"Expected 82 frozen A3R1 equity candidates; observed {len(metadata)}")
    matrices, eligibility = build_matrices(inputs, metadata)
    definitions, membership = a3.contexts(metadata)

    print("A3R1R1: constructing unchanged weekly signal features", flush=True)
    base_weekly = a3.build_base_weekly(inputs, matrices, metadata)
    group_features = a3.build_group_features(inputs, matrices, metadata, definitions)
    group_features = a3.attach_forward_data(group_features, base_weekly)
    dynamic_counts = a3.build_dynamic_counts(group_features, inputs.registry)

    print("A3R1R1: evaluating frozen top-tail and inference specifications", flush=True)
    top_tail, retained, overlap_selections = a3.evaluate_top_tails(group_features, definitions)
    top_tail = a3.add_primary_inference(top_tail, retained, inputs.policy)
    support = a3.score_primary_support(top_tail)
    best_signal = str(support.iloc[0]["signal_id"])
    group_results = a3.evaluate_group_diagnostics(group_features)
    persistence = a3.leadership_persistence(group_features)
    transitions = a3.state_transition_results(group_features)
    parent_results = a3.parent_relative_results(base_weekly)
    trend_quality = a3.trend_quality_results(group_features, base_weekly)
    subperiods = a3.build_subperiod_results(retained, inputs.policy)
    decay = a3.build_decay_results(top_tail)
    dependencies = a3.dependency_results(group_features, matrices, metadata)
    robustness = a3.robustness_results(group_features)
    breadth = a3.breadth_results(group_features, retained, best_signal)
    ledger = a3.build_multiple_testing_ledger(top_tail, group_results, subperiods, dependencies, robustness, inputs.registry)
    tests = run_correctness_tests(inputs, matrices, metadata, group_features, retained, ledger, eligibility)
    candidate_assessment = a3.build_candidate_assessment(
        top_tail, subperiods, dependencies, persistence, robustness, bool(tests["status"].eq("PASS").all())
    )
    decision = a3.build_decision_payload(
        inputs, group_features, top_tail, support, candidate_assessment, transitions, parent_results,
        trend_quality, persistence, breadth, dependencies, robustness, subperiods, tests, ledger,
    )
    decision.update(
        {
            "stage_id": STAGE_ID,
            "run_id": RUN_ID,
            "rerun_of": "UKACTIVE-A3R1",
            "a2r2_remediation_commit": A2R2_COMMIT,
            "frozen_specification": True,
            "original_a3r1_efficacy_status": "A3R1_PRE_REMEDIATION_INVALID_FOR_EFFICACY_CONCLUSION",
            "post_a3r1r1_result_commit": "PENDING_AFTER_EXECUTION",
        }
    )

    print("A3R1R1: writing separate rerun artifacts", flush=True)
    output_audit: list[dict[str, Any]] = []
    output_audit.append(a3.write_csv(output_path("ROTATION_POOL_MEMBERSHIP.csv"), membership))
    output_audit.append(a3.write_csv(output_path("DYNAMIC_COHORT_COUNTS.csv"), dynamic_counts))
    multi_columns = [
        "date", "analysis_context_id", "analysis_context_type", "economic_exposure_family_id",
        "economic_exposure_name", "primary_rotation_role", "primary_competition_pool_id", "universe_tier",
        "a2r_research_maturity", "contemporaneous_research_maturity", "accrued_valid_return_observations",
    ]
    for horizon in a3.MAIN_FORMATION_HORIZONS:
        multi_columns.extend([f"RETURN_{horizon}", f"RS_{horizon}", f"RANK_RS_{horizon}"])
    multi_columns.extend(["MH_LEVEL_EQ", "MH_LEVEL_RECENCY_TILT", "MH_LEVEL_60D_CENTERED", "MH_LEVEL_3_6_12_REFERENCE", "warning"])
    output_audit.append(a3.write_parquet(output_path("MULTI_HORIZON_RS.parquet"), group_features[multi_columns]))
    segment_columns = [
        "date", "economic_exposure_family_id", "economic_exposure_name", "research_group_id",
        "REL_SEG_0_1M", "REL_SEG_1_2M", "REL_SEG_2_3M", "REL_SEG_3_6M", "REL_SEG_6_12M",
        "a2r_research_maturity", "contemporaneous_research_maturity",
    ]
    output_audit.append(a3.write_parquet(output_path("DISCRETE_RELATIVE_SEGMENTS.parquet"), base_weekly[segment_columns]))
    acceleration_columns = [
        "date", "analysis_context_id", "analysis_context_type", "economic_exposure_family_id", "FAST_LEVEL",
        "RS_RANK_CHANGE_21", "RS_RANK_CHANGE_42", "SHORT_MINUS_LONG_RS", "RELATIVE_SLOPE_CHANGE_RANK",
        "ACCEL_FAST_COMPOSITE", "RECENT_POSITIVE_SEGMENTS", "DISCRETE_RECENT_CONSISTENCY",
        "contemporaneous_research_maturity", "warning",
    ]
    output_audit.append(a3.write_parquet(output_path("RS_ACCELERATION.parquet"), group_features[acceleration_columns]))
    pairwise_columns = ["date", "analysis_context_id", "analysis_context_type", "economic_exposure_family_id", "PAIRWISE_MAJORITY_5H", "contemporaneous_research_maturity", "warning"]
    output_audit.append(a3.write_parquet(output_path("PAIRWISE_RS_RESULTS.parquet"), group_features[pairwise_columns]))
    state_columns = [
        "date", "analysis_context_id", "analysis_context_type", "economic_exposure_family_id",
        "RRG_TRANSPARENT_LEVEL", "RRG_TRANSPARENT_MOMENTUM", "RRG_LEVEL_Z", "RRG_MOMENTUM_Z",
        "ROTATION_STATE", "contemporaneous_research_maturity", "warning",
    ]
    output_audit.append(a3.write_parquet(output_path("ROTATION_STATES.parquet"), group_features[state_columns]))
    relative_columns = [
        "date", "economic_exposure_family_id", "economic_exposure_name", "research_group_id",
        "REL_SLOPE_21", "REL_SLOPE_42", "REL_SLOPE_63", "REL_R2_21", "REL_R2_42", "REL_R2_63",
        "RELATIVE_SLOPE_CHANGE", "REL_DISTANCE_MA_21", "REL_DISTANCE_MA_50", "REL_DISTANCE_HIGH_63",
        "contemporaneous_research_maturity",
    ]
    output_audit.append(a3.write_parquet(output_path("RELATIVE_LINE_FEATURES.parquet"), base_weekly[relative_columns]))

    for suffix, frame in [
        ("TOP_TAIL_RESULTS.csv", top_tail), ("FORWARD_HORIZON_DECAY.csv", decay),
        ("GROUP_RESULTS.csv", group_results), ("LEADERSHIP_PERSISTENCE.csv", persistence),
        ("STATE_TRANSITIONS.csv", transitions), ("PARENT_RS_RESULTS.csv", parent_results),
        ("TREND_QUALITY_DIAGNOSTICS.csv", trend_quality), ("OVERLAP_DIAGNOSTICS.csv", overlap_selections),
        ("BREADTH_DIAGNOSTICS.csv", breadth), ("SUBPERIOD_RESULTS.csv", subperiods),
        ("DEPENDENCY_TESTS.csv", dependencies), ("PARAMETER_ROBUSTNESS.csv", robustness),
        ("MULTIPLE_TESTING_LEDGER.csv", ledger), ("CORRECTNESS_TEST_RESULTS.csv", tests),
        ("SIGNAL_ASSESSMENT.csv", candidate_assessment), ("SIGNAL_SUPPORT_SUMMARY.csv", support),
    ]:
        output_audit.append(a3.write_csv(output_path(suffix), frame))

    inference_path = write_statistical_inference(top_tail, ledger, support)
    candidate_path = write_candidate_report(candidate_assessment, decision)
    scope_path = write_scope()
    output_audit.extend([a3.audit_existing(inference_path), a3.audit_existing(candidate_path), a3.audit_existing(scope_path)])
    decision_path = output_path("DECISION.json")
    output_audit.append(a3.write_json(decision_path, decision))
    manifest = build_manifest(inputs, decision, tests, ledger, output_audit)
    a3.write_json(output_path("MANIFEST.json"), manifest)
    print(
        json.dumps(
            {
                "decision": decision["decision"],
                "best_signal": best_signal,
                "best_weighting": decision["best_multi_horizon_weighting_id"],
                "specifications_tested": decision["specifications_tested"],
                "correctness": f"{decision['correctness_tests_passed']}/{decision['correctness_tests_total']}",
                "candidate_signals": decision["candidate_signal_ids"],
                "a3r2_supported": decision["a3r2_scientifically_supported"],
            },
            indent=2,
        ),
        flush=True,
    )
    return 0 if tests["status"].eq("PASS").all() else 2


if __name__ == "__main__":
    raise SystemExit(main())
