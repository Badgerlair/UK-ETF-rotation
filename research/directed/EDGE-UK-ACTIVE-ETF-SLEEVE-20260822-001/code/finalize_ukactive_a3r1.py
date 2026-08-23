"""Apply post-run scientific QA gates to completed A3R1 outputs.

This applies the preregistered formal-inference minimum and audits whether the
principal signal families retain the requested modern-subperiod coverage.  It
does not change a signal or parameter, fill missing data, or rerun selection.
The initial artifact hashes are preserved in UKACTIVE_A3R1_METHOD_CORRECTIONS.csv.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import build_ukactive_a3r1 as stage


ROOT = Path(__file__).resolve().parents[1]


LONG_HORIZON_DEPENDENT_SIGNALS = {
    "MH_LEVEL_EQ",
    "MH_LEVEL_RECENCY_TILT",
    "MH_LEVEL_60D_CENTERED",
    "MH_LEVEL_3_6_12_REFERENCE",
    "SHORT_MINUS_LONG_RS",
    "PAIRWISE_MAJORITY_5H",
}


def corrected_primary_inference(top_tail: pd.DataFrame, policy: dict) -> pd.DataFrame:
    result = top_tail.copy()
    primary = (
        result["analysis_context_type"].eq("ROLE_GROUP")
        & result["signal_id"].isin(stage.PRIMARY_SIGNALS)
        & result["maturity_scope"].eq("FULL_DYNAMIC")
        & result["top_tail_definition"].eq("TOP_3")
        & result["forward_horizon_sessions"].isin(stage.CENTRAL_HORIZONS)
    )
    minimum = int(policy["minimum_cross_section"]["formal_date_observations"])
    formal = primary & result["advantage_vs_global_observation_count"].ge(minimum)
    result["primary_fdr_family"] = np.where(primary, "YES", "NO")
    result["formal_inference_minimum_date_observations"] = minimum
    result["formal_inference_eligible"] = np.where(formal, "YES", "NO")
    result["advantage_vs_global_bh_q_value"] = np.nan
    result.loc[formal, "advantage_vs_global_bh_q_value"] = stage.benjamini_hochberg(
        result.loc[formal, "advantage_vs_global_hac_p_value"].to_numpy(float)
    )
    bootstrap_columns = [
        "bootstrap_count",
        "bootstrap_block_length",
        "bootstrap_replications",
        "advantage_vs_global_bootstrap_ci_low",
        "advantage_vs_global_bootstrap_ci_high",
    ]
    for column in bootstrap_columns:
        result.loc[primary & ~formal, column] = np.nan
    return result


def build_horizon_coverage_audit(
    top_tail: pd.DataFrame,
    multi_horizon: pd.DataFrame,
) -> tuple[pd.DataFrame, bool, list[str]]:
    """Audit whether preregistered principal signals cover the requested modern subperiods.

    This does not relax A2R validity.  Missing A2R daily returns remain missing; the
    audit detects the resulting loss of long-horizon signal coverage.
    """
    rows: list[dict[str, object]] = []
    primary = top_tail.loc[
        top_tail["analysis_context_type"].eq("ROLE_GROUP")
        & top_tail["signal_id"].isin(stage.PRIMARY_SIGNALS)
        & top_tail["maturity_scope"].eq("FULL_DYNAMIC")
        & top_tail["top_tail_definition"].eq("TOP_3")
        & top_tail["forward_horizon_sessions"].isin(stage.CENTRAL_HORIZONS)
    ].copy()
    for signal_id, frame in primary.groupby("signal_id", sort=True):
        first = pd.to_datetime(frame["first_signal_date"], errors="coerce").min()
        last = pd.to_datetime(frame["last_signal_date"], errors="coerce").max()
        long_dependent = signal_id in LONG_HORIZON_DEPENDENT_SIGNALS
        post_2020 = bool(pd.notna(last) and last >= pd.Timestamp("2020-01-01"))
        status = "PASS" if (not long_dependent or post_2020) else "FAIL"
        rows.append(
            {
                "record_type": "PRIMARY_SIGNAL_COVERAGE",
                "feature_or_signal_id": signal_id,
                "requires_252_session_input": "YES" if long_dependent else "NO",
                "first_valid_observation_date": first.date().isoformat() if pd.notna(first) else None,
                "last_valid_observation_date": last.date().isoformat() if pd.notna(last) else None,
                "covers_2020_onward": "YES" if post_2020 else "NO",
                "covers_latest_five_years": "YES" if bool(pd.notna(last) and last >= pd.Timestamp("2021-04-17")) else "NO",
                "covers_latest_three_years": "YES" if bool(pd.notna(last) and last >= pd.Timestamp("2023-04-17")) else "NO",
                "role_group_count": int(frame["analysis_context_id"].nunique()),
                "central_forward_cell_count": int(len(frame)),
                "scientific_coverage_gate": status,
                "detail": (
                    "Principal signal lacks post-2020 evidence because strict A2R-valid 252-session windows cease after recurring invalid/missing rows."
                    if status == "FAIL"
                    else "Signal retains post-2020 descriptive coverage or does not require a 252-session input."
                ),
            }
        )
    for feature in ["RS_21", "RS_42", "RS_63", "RS_126", "RS_252", "MH_LEVEL_EQ"]:
        valid = multi_horizon.loc[multi_horizon[feature].notna(), "date"]
        first = pd.to_datetime(valid, errors="coerce").min()
        last = pd.to_datetime(valid, errors="coerce").max()
        rows.append(
            {
                "record_type": "FEATURE_COVERAGE",
                "feature_or_signal_id": feature,
                "requires_252_session_input": "YES" if feature in {"RS_252", "MH_LEVEL_EQ"} else "NO",
                "first_valid_observation_date": first.date().isoformat() if pd.notna(first) else None,
                "last_valid_observation_date": last.date().isoformat() if pd.notna(last) else None,
                "covers_2020_onward": "YES" if bool(pd.notna(last) and last >= pd.Timestamp("2020-01-01")) else "NO",
                "covers_latest_five_years": "YES" if bool(pd.notna(last) and last >= pd.Timestamp("2021-04-17")) else "NO",
                "covers_latest_three_years": "YES" if bool(pd.notna(last) and last >= pd.Timestamp("2023-04-17")) else "NO",
                "role_group_count": np.nan,
                "central_forward_cell_count": int(multi_horizon[feature].notna().sum()),
                "scientific_coverage_gate": "DIAGNOSTIC",
                "detail": "Strict rolling feature uses only A2R-valid daily total-return rows and never bridges an invalid observation.",
            }
        )
    audit = pd.DataFrame(rows)
    blocked = audit.loc[
        audit["record_type"].eq("PRIMARY_SIGNAL_COVERAGE")
        & audit["scientific_coverage_gate"].eq("FAIL"),
        "feature_or_signal_id",
    ].astype(str).tolist()
    return audit, bool(blocked), blocked


def write_data_method_warning(audit: pd.DataFrame, blocked: list[str]) -> Path:
    feature = audit.loc[audit["record_type"].eq("FEATURE_COVERAGE")].set_index("feature_or_signal_id")
    rs252_last = feature.loc["RS_252", "last_valid_observation_date"]
    mh_last = feature.loc["MH_LEVEL_EQ", "last_valid_observation_date"]
    lines = [
        "# UKACTIVE-A3R1 data and method warning",
        "",
        "## Blocking finding A3R1-DQ-001",
        "",
        "The strict A2R-valid 252-session relative-strength feature has no observation after "
        f"{rs252_last}; the equal five-horizon composite has no observation after {mh_last}. "
        "Consequently, six preregistered principal signals have no post-2020 evidence: "
        + ", ".join(blocked)
        + ".",
        "",
        "The immediate cause is recurring A2/A2R invalid/missing daily return rows. A3R1 correctly did not fill, bridge, or reinterpret them. "
        "That conservative treatment makes a contiguous 252-session window unavailable after 2017 and prevents the requested modern-subperiod comparison of 1/2/3-month information against 6/12-month momentum.",
        "",
        "Shorter-horizon acceleration, discrete consistency and transparent RRG-like diagnostics do extend into 2026, but they cannot repair the missing evidence for the stage's principal multi-horizon and pairwise models. "
        "All generated effect estimates remain auditable diagnostics; none is promoted.",
        "",
        "Resolution requires a controlled A2/A2R session-calendar and missing-return remediation, followed by a fresh A3R1 run. No invalid row or proxy was introduced during this stage.",
        "",
        stage.WARNING,
    ]
    path = ROOT / "UKACTIVE_A3R1_DATA_AND_METHOD_WARNINGS.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def update_decision(
    old: dict,
    top_tail: pd.DataFrame,
    support: pd.DataFrame,
    assessment: pd.DataFrame,
    dependencies: pd.DataFrame,
    tests: pd.DataFrame,
    ledger: pd.DataFrame,
    coverage_blocked: bool,
    blocked_signals: list[str],
) -> dict:
    decision = dict(old)
    descriptive_best_signal = str(support.iloc[0]["signal_id"])
    unblocked_support = support.loc[~support["signal_id"].isin(blocked_signals)]
    descriptive_best_unblocked = (
        str(unblocked_support.iloc[0]["signal_id"]) if len(unblocked_support) else "NOT_ESTABLISHED"
    )
    multi = support.loc[support["signal_id"].str.startswith("MH_LEVEL_")]
    descriptive_best_weight = str(multi.iloc[0]["signal_id"]) if len(multi) else "NOT_ESTABLISHED"
    decision["decision"] = (
        "UKACTIVE_A3R1_FAIL_DATA_OR_METHOD"
        if coverage_blocked
        else stage.decision_state(assessment, top_tail, tests)
    )
    decision["decision_timestamp"] = stage.utc_now()
    decision["best_supported_signal_id"] = "NOT_ESTABLISHED" if coverage_blocked else descriptive_best_signal
    decision["descriptive_best_signal_id"] = descriptive_best_signal
    decision["descriptive_best_unblocked_signal_id"] = descriptive_best_unblocked
    decision["best_multi_horizon_weighting_id"] = "NOT_ESTABLISHED" if coverage_blocked else descriptive_best_weight
    decision["descriptive_best_multi_horizon_weighting_id"] = descriptive_best_weight
    decision["specifications_tested"] = int(len(ledger))
    decision["correctness_tests_passed"] = int(tests["status"].eq("PASS").sum())
    decision["correctness_tests_total"] = int(len(tests))
    decision["signal_classifications"] = assessment.to_dict(orient="records")
    decision["candidate_signal_ids"] = assessment.loc[
        assessment["classification"].eq("A3R1_RESEARCH_CANDIDATE"), "signal_id"
    ].tolist()
    decision["rejected_signal_ids"] = assessment.loc[assessment["classification"].eq("REJECTED"), "signal_id"].tolist()
    decision["method_blocked_signal_ids"] = blocked_signals
    decision["data_quality_issue_ids"] = ["A3R1-DQ-001"] if coverage_blocked else []
    decision["scientific_coverage_gate"] = "FAIL" if coverage_blocked else "PASS"
    decision["scientific_coverage_gate_detail"] = (
        "Six 252-session-dependent principal signals have no post-2020 evidence; the five-horizon composite ends in 2017."
        if coverage_blocked
        else "Principal signals retain the required modern-subperiod coverage."
    )
    decision["primary_fdr_cell_count"] = int(top_tail["primary_fdr_family"].eq("YES").sum())
    decision["formal_inference_eligible_primary_cell_count"] = int(
        top_tail["formal_inference_eligible"].eq("YES").sum()
    )
    decision["primary_fdr_surviving_cell_count"] = int(
        (top_tail["formal_inference_eligible"].eq("YES") & top_tail["advantage_vs_global_bh_q_value"].le(0.10)).sum()
    )
    decision["primary_bootstrap_positive_cell_count"] = int(
        (top_tail["formal_inference_eligible"].eq("YES") & top_tail["advantage_vs_global_bootstrap_ci_low"].gt(0)).sum()
    )

    primary = top_tail.loc[
        top_tail["signal_id"].eq(descriptive_best_signal)
        & top_tail["analysis_context_type"].eq("ROLE_GROUP")
        & top_tail["maturity_scope"].eq("FULL_DYNAMIC")
        & top_tail["top_tail_definition"].eq("TOP_3")
        & top_tail["forward_horizon_sessions"].isin(stage.CENTRAL_HORIZONS)
    ]
    group_results = []
    for context_id, frame in primary.groupby("analysis_context_id", sort=True):
        best = frame.loc[frame["advantage_vs_global_mean"].idxmax()]
        group_results.append(
            {
                "group_id": context_id,
                "positive_central_horizon_count": int((frame["advantage_vs_global_mean"] > 0).sum()),
                "mean_advantage_across_central_horizons": float(frame["advantage_vs_global_mean"].mean()),
                "best_forward_horizon_sessions": int(best["forward_horizon_sessions"]),
                "best_mean_advantage_vs_global": float(best["advantage_vs_global_mean"]),
                "best_hac_p_value": float(best["advantage_vs_global_hac_p_value"]),
                "best_bh_q_value": float(best["advantage_vs_global_bh_q_value"]) if np.isfinite(best["advantage_vs_global_bh_q_value"]) else None,
                "best_formal_inference_eligible": str(best["formal_inference_eligible"]),
                "best_observation_count": int(best["advantage_vs_global_observation_count"]),
            }
        )
    decision["group_results"] = group_results
    horizon_mean = primary.groupby("forward_horizon_sessions")["advantage_vs_global_mean"].mean()
    best_horizon = int(horizon_mean.idxmax()) if len(horizon_mean) else None
    decision["best_forward_holding_horizon_sessions"] = None if coverage_blocked else best_horizon
    decision["descriptive_least_negative_forward_horizon_sessions"] = best_horizon
    tails = {}
    for tail in ["RANK_1", "TOP_3", "TOP_5"]:
        frame = top_tail.loc[
            top_tail["signal_id"].eq(descriptive_best_signal)
            & top_tail["analysis_context_type"].eq("ROLE_GROUP")
            & top_tail["maturity_scope"].eq("FULL_DYNAMIC")
            & top_tail["top_tail_definition"].eq(tail)
            & top_tail["forward_horizon_sessions"].eq(best_horizon)
        ]
        tails[tail] = {
            "mean_advantage_vs_global": float(frame["advantage_vs_global_mean"].mean()) if len(frame) else None,
            "mean_positive_frequency": float(frame["advantage_vs_global_positive_frequency"].mean()) if len(frame) else None,
            "group_count": len(frame),
        }
    decision["top_tail_results_at_best_horizon"] = tails
    decision["top_tail_results_status"] = "DESCRIPTIVE_ONLY_DATA_COVERAGE_BLOCKER" if coverage_blocked else "SCIENTIFICALLY_ADMISSIBLE"
    mature = dependencies.loc[
        dependencies["dependency_scenario"].eq("MATURE_ONLY") & dependencies["signal_id"].eq(descriptive_best_signal)
    ]
    decision["mature_only_sensitivity"] = {
        "best_signal_mean_top3_advantage_vs_global": float(mature["mean_top3_advantage_vs_global"].mean()) if len(mature) else None,
        "positive_horizon_count": int((mature["mean_top3_advantage_vs_global"] > 0).sum()) if len(mature) else 0,
    }
    supported = decision["decision"] in [
        "UKACTIVE_A3R1_STRONG_ROTATION_SIGNAL",
        "UKACTIVE_A3R1_RESEARCH_CANDIDATE_FOUND",
    ]
    decision["a3r2_scientifically_supported"] = supported
    decision["a3r2_executed"] = False
    decision["method_correction_ids"] = ["A3R1-MC-001"]
    decision["post_a3r1_result_commit"] = "PENDING_GIT_COMMIT"
    return decision


def main() -> None:
    inputs = stage.load_inputs()
    top_tail = pd.read_csv(ROOT / "UKACTIVE_A3R1_TOP_TAIL_RESULTS.csv")
    top_tail = corrected_primary_inference(top_tail, inputs.policy)
    multi_horizon = pd.read_parquet(ROOT / "UKACTIVE_A3R1_MULTI_HORIZON_RS.parquet")
    coverage_audit, coverage_blocked, blocked_signals = build_horizon_coverage_audit(top_tail, multi_horizon)
    support = stage.score_primary_support(top_tail)
    group_results = pd.read_csv(ROOT / "UKACTIVE_A3R1_GROUP_RESULTS.csv")
    subperiods = pd.read_csv(ROOT / "UKACTIVE_A3R1_SUBPERIOD_RESULTS.csv")
    dependencies = pd.read_csv(ROOT / "UKACTIVE_A3R1_DEPENDENCY_TESTS.csv")
    robustness = pd.read_csv(ROOT / "UKACTIVE_A3R1_PARAMETER_ROBUSTNESS.csv")
    persistence = pd.read_csv(ROOT / "UKACTIVE_A3R1_LEADERSHIP_PERSISTENCE.csv")
    tests = pd.read_csv(ROOT / "UKACTIVE_A3R1_CORRECTNESS_TEST_RESULTS.csv")
    ledger = stage.build_multiple_testing_ledger(
        top_tail, group_results, subperiods, dependencies, robustness, inputs.registry
    )
    ineligible = top_tail.loc[
        top_tail["primary_fdr_family"].eq("YES") & top_tail["formal_inference_eligible"].eq("NO")
    ]
    passed = (
        ineligible["advantage_vs_global_bh_q_value"].isna().all()
        and ineligible["advantage_vs_global_bootstrap_ci_low"].isna().all()
        and ineligible["advantage_vs_global_bootstrap_ci_high"].isna().all()
    )
    tests = tests.loc[tests["test_id"].ne("A3R1-T21")].copy()
    tests = pd.concat(
        [
            tests,
            pd.DataFrame(
                [
                    {
                        "test_id": "A3R1-T21",
                        "requirement": "Formal inference requires the preregistered minimum of 24 date observations",
                        "status": "PASS" if passed else "FAIL",
                        "detail": f"{len(ineligible)} sub-minimum primary cells retain descriptive effects but have no BH/bootstrap label",
                        "critical": "YES",
                        "executed_at": stage.utc_now(),
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    assessment = stage.build_candidate_assessment(
        top_tail, subperiods, dependencies, persistence, robustness, tests["status"].eq("PASS").all()
    )
    assessment["coverage_status"] = np.where(
        assessment["signal_id"].isin(blocked_signals),
        "METHOD_BLOCKED_POST_2017_COVERAGE",
        "SHORT_HORIZON_DIAGNOSTIC_ONLY",
    )
    assessment.loc[assessment["signal_id"].isin(blocked_signals), "classification"] = "METHOD_BLOCKED"
    assessment.loc[assessment["signal_id"].isin(blocked_signals), "qualifying_group_ids"] = "NOT_ASSESSED_DUE_TO_COVERAGE"
    old_decision = json.loads((ROOT / "UKACTIVE_A3R1_DECISION.json").read_text(encoding="utf-8"))
    decision = update_decision(
        old_decision, top_tail, support, assessment, dependencies, tests, ledger,
        coverage_blocked, blocked_signals,
    )

    stage.write_csv(ROOT / "UKACTIVE_A3R1_TOP_TAIL_RESULTS.csv", top_tail)
    stage.write_csv(ROOT / "UKACTIVE_A3R1_SIGNAL_SUPPORT_SUMMARY.csv", support)
    stage.write_csv(ROOT / "UKACTIVE_A3R1_MULTIPLE_TESTING_LEDGER.csv", ledger)
    stage.write_csv(ROOT / "UKACTIVE_A3R1_CORRECTNESS_TEST_RESULTS.csv", tests)
    stage.write_csv(ROOT / "UKACTIVE_A3R1_SIGNAL_ASSESSMENT.csv", assessment)
    stage.write_csv(ROOT / "UKACTIVE_A3R1_HORIZON_COVERAGE_AUDIT.csv", coverage_audit)
    warning_path = write_data_method_warning(coverage_audit, blocked_signals)
    inference_path = stage.write_statistical_inference(top_tail, ledger, support)
    candidate_path = stage.write_candidate_report(assessment, decision)
    coverage_prefix = (
        "# Blocking coverage qualification\n\n"
        "A3R1-DQ-001 forces `UKACTIVE_A3R1_FAIL_DATA_OR_METHOD`: the strict A2R-valid 252-session feature and all six dependent principal signals have no post-2020 evidence. "
        "The statistics below are retained as descriptive diagnostics and cannot support promotion. See `UKACTIVE_A3R1_DATA_AND_METHOD_WARNINGS.md`.\n\n"
    )
    inference_path.write_text(coverage_prefix + inference_path.read_text(encoding="utf-8"), encoding="utf-8")
    candidate_path.write_text(coverage_prefix + candidate_path.read_text(encoding="utf-8"), encoding="utf-8")
    stage.write_json(ROOT / "UKACTIVE_A3R1_DECISION.json", decision)

    artifacts = [
        path for path in ROOT.glob("UKACTIVE_A3R1_*")
        if path.is_file() and path.name != "UKACTIVE_A3R1_MANIFEST.json"
    ]
    output_audit = [stage.audit_existing(path) for path in sorted(artifacts)]
    manifest = stage.build_manifest(inputs, decision, output_audit, tests, ledger)
    manifest["method_corrections"] = pd.read_csv(ROOT / "UKACTIVE_A3R1_METHOD_CORRECTIONS.csv").to_dict(orient="records")
    manifest["initial_run_artifact_hashes"] = {
        "UKACTIVE_A3R1_DECISION.json": "4EA76D8AF3EFAA4CAC925DD66704978FF86C56A1E32F408CFD78E02A8A985869",
        "UKACTIVE_A3R1_TOP_TAIL_RESULTS.csv": "55FCB0E2E1A6CC5E66AE92AD7640CA180BB3B12237832FF24F2C8F14D9DA9B63",
    }
    manifest["formal_inference_eligible_primary_cell_count"] = decision["formal_inference_eligible_primary_cell_count"]
    manifest["scientific_coverage_gate"] = decision["scientific_coverage_gate"]
    manifest["data_quality_issues"] = [
        {
            "issue_id": "A3R1-DQ-001",
            "status": "BLOCKING",
            "affected_signal_ids": blocked_signals,
            "audit_path": str(ROOT / "UKACTIVE_A3R1_HORIZON_COVERAGE_AUDIT.csv"),
            "warning_path": str(warning_path),
        }
    ] if coverage_blocked else []
    manifest["command_lines"].append(f"{stage.sys.executable} {Path(__file__)}")
    stage.write_json(ROOT / "UKACTIVE_A3R1_MANIFEST.json", manifest)
    print(
        json.dumps(
            {
                "decision": decision["decision"],
                "formal_primary_cells": decision["formal_inference_eligible_primary_cell_count"],
                "fdr_survivors": decision["primary_fdr_surviving_cell_count"],
                "correctness": f"{decision['correctness_tests_passed']}/{decision['correctness_tests_total']}",
                "best_signal": decision["best_supported_signal_id"],
                "descriptive_best_signal": decision["descriptive_best_signal_id"],
                "candidates": decision["candidate_signal_ids"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
