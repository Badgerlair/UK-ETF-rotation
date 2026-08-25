"""Correctness controls for the separately governed UKACTIVE-A4F-SIPP stage.

The tests deliberately cover both the frozen protocol and the generated evidence.
They are not performance-selection tests: their purpose is to make causal timing,
allocation arithmetic, immutable lineage, and output completeness fail closed.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import pytest


PROGRAMME_ROOT = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "directed"
    / "EDGE-UK-ACTIVE-ETF-SLEEVE-20260822-001"
)
STAGE_ROOT = PROGRAMME_ROOT / "UKACTIVE-A4F-SIPP-REGIME"
CODE_ROOT = PROGRAMME_ROOT / "code"
sys.path.insert(0, str(CODE_ROOT))

import ukactive_a4f_sipp_core as a4f  # noqa: E402


CUTOFF = pd.Timestamp("2026-08-21")
EXPECTED_PARENT = {
    "preregistration_commit": "d49ee4748020bce8911244ba98430fe3b25c3366",
    "results_commit": "6eef0e413a2ee269bd5748cb244ce4f19577723a",
    "manifest_commit": "ce6136f52ca646698a56e4ff4bbb8577214a684d",
    "tag": "ukactive-a4e-sipp-v1-20260824",
}
EXPECTED_M2_WEIGHTS = {
    "RS21": 0.10,
    "RS42": 0.15,
    "RS63": 0.25,
    "RS126": 0.30,
    "RS252": 0.20,
}

REQUIRED_OUTPUTS = {
    # Governance (5)
    "UKACTIVE_A4F_SIPP_PREREGISTRATION.md",
    "UKACTIVE_A4F_SIPP_PREREGISTRATION.json",
    "UKACTIVE_A4F_SIPP_MANIFEST.json",
    "UKACTIVE_A4F_SIPP_PROVENANCE.md",
    "UKACTIVE_A4F_SIPP_DATA_CUTOFF_AUDIT.md",
    # Reproduction (2)
    "UKACTIVE_A4F_SIPP_REPRODUCTION_AUDIT.md",
    "UKACTIVE_A4F_SIPP_COMMON_WINDOW_RECONCILIATION.csv",
    # Year by year (3)
    "UKACTIVE_A4F_SIPP_YEAR_BY_YEAR_SCORECARD.csv",
    "UKACTIVE_A4F_SIPP_YEAR_BY_YEAR_ATTRIBUTION.csv",
    "UKACTIVE_A4F_SIPP_YEAR_BY_YEAR_REVIEW.md",
    # Regimes (6)
    "UKACTIVE_A4F_SIPP_MONTHLY_REGIME_LEDGER.csv",
    "UKACTIVE_A4F_SIPP_REGIME_SUMMARY.csv",
    "UKACTIVE_A4F_SIPP_REGIME_STRATEGY_RANKINGS.csv",
    "UKACTIVE_A4F_SIPP_REGIME_TRANSITIONS.csv",
    "UKACTIVE_A4F_SIPP_REGIME_INFERENCE.md",
    "UKACTIVE_A4F_SIPP_MACRO_REGIME_ATTRIBUTION.md",
    # Static frontier (3)
    "UKACTIVE_A4F_SIPP_STATIC_FRONTIER.csv",
    "UKACTIVE_A4F_SIPP_M2_INCREMENTAL_VALUE.csv",
    "UKACTIVE_A4F_SIPP_PARETO_FRONTIER.csv",
    # Dynamic policies (5)
    "UKACTIVE_A4F_SIPP_DYNAMIC_POLICY_RESULTS.csv",
    "UKACTIVE_A4F_SIPP_SWITCH_ATTRIBUTION.csv",
    "UKACTIVE_A4F_SIPP_HYSTERESIS_RESULTS.csv",
    "UKACTIVE_A4F_SIPP_MATCHED_RISK_CONTROLS.csv",
    "UKACTIVE_A4F_SIPP_ORACLE_DIAGNOSTICS.csv",
    # Robustness (4)
    "UKACTIVE_A4F_SIPP_YEAR_EXCLUSION_RESULTS.csv",
    "UKACTIVE_A4F_SIPP_FAMILY_INFLUENCE.csv",
    "UKACTIVE_A4F_SIPP_THRESHOLD_SENSITIVITY.csv",
    "UKACTIVE_A4F_SIPP_COST_STRESS.csv",
    # Final strategy (6)
    "UKACTIVE_A4F_SIPP_FINAL_DECISION_REPORT.md",
    "UKACTIVE_A4F_SIPP_DECISION.json",
    "UKACTIVE_A4F_SIPP_SELECTED_STRATEGY.json",
    "UKACTIVE_A4F_SIPP_REGIME_STATE_MACHINE.json",
    "UKACTIVE_A4F_SIPP_MONTHLY_RUNBOOK.md",
    "UKACTIVE_A4F_SIPP_EXECUTIVE_HANDOFF.md",
}

REQUIRED_CHARTS = {
    "UKACTIVE_A4F_SIPP_ANNUAL_RETURNS.png",
    "UKACTIVE_A4F_SIPP_ANNUAL_EXCESS.png",
    "UKACTIVE_A4F_SIPP_ANNUAL_MAXIMUM_DRAWDOWN.png",
    "UKACTIVE_A4F_SIPP_REGIME_TIMELINE.png",
    "UKACTIVE_A4F_SIPP_RISK_SCORE_TIMELINE.png",
    "UKACTIVE_A4F_SIPP_LEADERSHIP_STATE_TIMELINE.png",
    "UKACTIVE_A4F_SIPP_ALLOCATION_TIMELINE.png",
    "UKACTIVE_A4F_SIPP_REGIME_TRANSITION_DIAGRAM.png",
    "UKACTIVE_A4F_SIPP_DYNAMIC_VS_STATIC_EQUITY_CURVES.png",
    "UKACTIVE_A4F_SIPP_DYNAMIC_VS_STATIC_DRAWDOWN_CURVES.png",
    "UKACTIVE_A4F_SIPP_ROLLING_EXCESS.png",
    "UKACTIVE_A4F_SIPP_MATCHED_RISK_FRONTIER.png",
    "UKACTIVE_A4F_SIPP_2025_INCLUDED_EXCLUDED.png",
    "UKACTIVE_A4F_SIPP_CONTRIBUTION_BY_REGIME.png",
    "UKACTIVE_A4F_SIPP_CONTRIBUTION_BY_YEAR.png",
    "UKACTIVE_A4F_SIPP_SWITCHING_GAIN_OPPORTUNITY_COST.png",
}


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_source(relative_name: str) -> Path:
    direct = PROGRAMME_ROOT / Path(relative_name)
    if direct.is_file():
        return direct
    matches = list(PROGRAMME_ROOT.rglob(Path(relative_name).name))
    assert len(matches) == 1, f"Cannot uniquely resolve frozen input {relative_name}: {matches}"
    return matches[0]


def _callable(*names: str) -> Callable[..., Any]:
    for name in names:
        candidate = getattr(a4f, name, None)
        if callable(candidate):
            return candidate
    pytest.fail(f"A4F core must expose one of these causal helpers: {names}")


def _normalise_weights(value: Any) -> dict[str, float]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if isinstance(value, (tuple, list, np.ndarray)):
        assert len(value) == 3
        return dict(zip(("global", "m2", "cash"), map(float, value)))
    assert isinstance(value, dict), f"Unsupported allocation type: {type(value)!r}"
    aliases = {
        "global": ("global", "swda", "global_weight", "swda_weight"),
        "m2": ("m2", "rotation", "m2_weight", "rotation_weight"),
        "cash": ("cash", "cash_weight"),
    }
    result: dict[str, float] = {}
    lowered = {str(key).lower(): val for key, val in value.items()}
    for canonical, choices in aliases.items():
        for choice in choices:
            if choice in lowered:
                result[canonical] = float(lowered[choice])
                break
    assert set(result) == {"global", "m2", "cash"}, value
    return result


def _parse_family_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if pd.isna(raw):
        return []
    text = str(raw).strip()
    if text.startswith("["):
        return [str(item) for item in json.loads(text)]
    delimiter = "|" if "|" in text else ";" if ";" in text else ","
    return [part.strip() for part in text.split(delimiter) if part.strip()]


def test_protocol_is_frozen_to_exact_parent_cutoff_and_m2() -> None:
    protocol = _json(STAGE_ROOT / "UKACTIVE_A4F_SIPP_PREREGISTRATION.json")
    assert protocol["stage_id"] == "UKACTIVE-A4F-SIPP"
    assert protocol["authoritative_cutoff"] == "2026-08-21"
    assert protocol["evidence_ceiling"] == "E2_DEVELOPMENTAL"
    assert protocol["registered_before_new_results"] is True
    assert protocol["parent"] == {
        "branch": "research/ukactive-a4e-sipp",
        **EXPECTED_PARENT,
    }
    assert protocol["immutable_contract"]["rotation_portfolio"] == (
        "TOP7_MONTHLY_CASH0_ALWAYS_INVESTED_EQUAL_WEIGHT"
    )
    manifest = _json(STAGE_ROOT / "UKACTIVE_A4F_SIPP_CANDIDATE_MANIFESTS.json")
    sleeve = manifest["rotation_sleeve"]
    assert sleeve["signal"] == "M2_BASE"
    assert sleeve["breadth"] == 7
    assert sleeve["cash_architecture"] == "CASH0_ALWAYS_INVESTED"
    assert sleeve["weighting"] == "EQUAL"
    assert sleeve["weights"] == EXPECTED_M2_WEIGHTS


def test_frozen_source_hashes_still_match_preregistration() -> None:
    protocol = _json(STAGE_ROOT / "UKACTIVE_A4F_SIPP_PREREGISTRATION.json")
    assert len(protocol["source_hashes"]) >= 10
    for relative_name, expected_hash in protocol["source_hashes"].items():
        source = _resolve_source(relative_name)
        assert _sha256(source) == expected_hash, f"Frozen parent/input changed: {source}"


def test_core_constants_preserve_cutoff_and_frozen_signal() -> None:
    cutoff = getattr(a4f, "AUTHORITATIVE_CUTOFF", getattr(a4f, "CUTOFF", None))
    assert pd.Timestamp(cutoff) == CUTOFF
    weights = getattr(a4f, "M2_WEIGHTS", getattr(a4f, "SIGNAL_WEIGHTS", None))
    if isinstance(weights, dict) and "M2_BASE" in weights:
        weights = weights["M2_BASE"]
    if isinstance(weights, (tuple, list, np.ndarray)):
        weights = dict(zip(EXPECTED_M2_WEIGHTS, map(float, weights)))
    assert weights == EXPECTED_M2_WEIGHTS
    breadth = getattr(a4f, "M2_BREADTH", getattr(a4f, "ROTATION_BREADTH", None))
    assert int(breadth) == 7


def test_prior_only_threshold_excludes_current_and_future_values() -> None:
    func = _callable("prior_only_quantile", "expanding_prior_quantile")
    values = pd.Series([1.0, 2.0, 3.0, 1000.0, -5000.0])
    try:
        observed = func(values, current_position=3, quantile=0.50, min_prior=3)
        unavailable = func(values, current_position=2, quantile=0.50, min_prior=3)
    except TypeError:
        observed = func(values, 3, 0.50, 3)
        unavailable = func(values, 2, 0.50, 3)
    assert float(observed) == pytest.approx(2.0)
    assert unavailable is None or bool(pd.isna(unavailable))
    mutated = values.copy()
    mutated.iloc[3:] = [9.9e12, -9.9e12]
    try:
        changed = func(mutated, current_position=3, quantile=0.50, min_prior=3)
    except TypeError:
        changed = func(mutated, 3, 0.50, 3)
    assert float(changed) == pytest.approx(float(observed))


@pytest.mark.parametrize(
    ("g126", "g252", "vol63", "vol_threshold", "expected"),
    [
        (0.01, 0.02, 0.10, 0.20, 0),
        (0.00, 0.02, 0.10, 0.20, 1),
        (0.01, 0.00, 0.10, 0.20, 1),
        (0.01, 0.02, 0.20, 0.20, 0),  # volatility test is strictly greater
        (-0.01, 0.00, 0.21, 0.20, 3),
    ],
)
def test_risk_score_is_exact_preregistered_formula(
    g126: float, g252: float, vol63: float, vol_threshold: float, expected: int
) -> None:
    func = _callable("calculate_risk_score", "risk_score")
    try:
        observed = func(
            g126_excess=g126,
            g252_excess=g252,
            vol63=vol63,
            prior_vol_threshold=vol_threshold,
        )
    except TypeError:
        observed = func(g126, g252, vol63, vol_threshold)
    assert int(observed) == expected


@pytest.mark.parametrize(
    ("flags", "history_available", "expected"),
    [
        ((True, True, False), True, "LEADERSHIP_STRONG"),
        ((True, False, True), True, "LEADERSHIP_STRONG"),
        ((False, True, True), True, "LEADERSHIP_STRONG"),
        ((True, False, False), True, "LEADERSHIP_WEAK"),
        ((True, True, True), False, "LEADERSHIP_WEAK"),
    ],
)
def test_leadership_requires_two_current_signals_and_valid_prior_history(
    flags: tuple[bool, bool, bool], history_available: bool, expected: str
) -> None:
    func = _callable("classify_leadership", "leadership_state")
    kwargs = {
        "spread_high": flags[0],
        "persistence_high": flags[1],
        "absolute_support_high": flags[2],
        "threshold_history_available": history_available,
        "current_valid_family_count": 7,
    }
    try:
        observed = func(**kwargs)
    except TypeError:
        observed = func(*flags, history_available)
    assert str(observed).upper() == expected


@pytest.mark.parametrize(
    ("score", "leadership", "expected"),
    [
        (0, "LEADERSHIP_WEAK", "R1_BROAD_RISK_ON"),
        (1, "LEADERSHIP_WEAK", "R1_BROAD_RISK_ON"),
        (0, "LEADERSHIP_STRONG", "R2_LEADERSHIP_RISK_ON"),
        (1, "LEADERSHIP_STRONG", "R2_LEADERSHIP_RISK_ON"),
        (2, "LEADERSHIP_STRONG", "R3_ISOLATED_LEADERSHIP"),
        (3, "LEADERSHIP_STRONG", "R3_ISOLATED_LEADERSHIP"),
        (2, "LEADERSHIP_WEAK", "R4_CAPITAL_PRESERVATION"),
        (3, "LEADERSHIP_WEAK", "R4_CAPITAL_PRESERVATION"),
    ],
)
def test_four_state_regime_mapping_is_exact(score: int, leadership: str, expected: str) -> None:
    func = _callable("classify_regime", "regime_for")
    assert str(func(score, leadership)).upper() == expected


def test_all_policy_allocation_maps_are_exact_and_never_lever_or_short() -> None:
    func = _callable("policy_target", "policy_allocation")
    risk25 = {0: 1.00, 1: 0.75, 2: 0.50, 3: 0.25}
    risk33 = {0: 1.00, 1: 0.67, 2: 0.33, 3: 0.00}
    policies = {
        "POLICY_0_STATIC_DEFENSIVE_CONTROL": (lambda score: 0.75, 0.00),
        "POLICY_1_RISK_TIMING_ONLY": (lambda score: risk25[score], 0.00),
        "POLICY_2_ALPHA_TIMING_ONLY": (lambda score: 1.00, 0.25),
        "POLICY_3_BALANCED_REGIME_STRATEGY": (lambda score: risk25[score], 0.25),
        "POLICY_4_DEFENSIVE_REGIME_STRATEGY": (lambda score: risk33[score], 0.25),
        "POLICY_5_HIGHER_ALPHA_DIAGNOSTIC": (lambda score: risk25[score], 0.50),
    }
    for policy_id, (risk_for, strong_m2_share) in policies.items():
        for score in range(4):
            for leadership in ("LEADERSHIP_WEAK", "LEADERSHIP_STRONG"):
                try:
                    raw = func(policy_id, risk_score=score, leadership_state=leadership)
                except TypeError:
                    raw = func(policy_id, score, leadership)
                target = _normalise_weights(raw)
                risky = float(risk_for(score))
                m2_share = strong_m2_share if leadership.endswith("STRONG") else 0.0
                expected = {
                    "global": risky * (1.0 - m2_share),
                    "m2": risky * m2_share,
                    "cash": 1.0 - risky,
                }
                assert target == pytest.approx(expected, abs=1e-12)
                assert min(target.values()) >= -1e-12
                assert max(target.values()) <= 1.0 + 1e-12
                assert sum(target.values()) == pytest.approx(1.0, abs=1e-12)


def test_asymmetric_hysteresis_never_delays_defence_or_m2_removal() -> None:
    func = _callable("apply_asymmetric_hysteresis", "hysteresis_target")

    def apply(previous, proposed, risk_streak, leadership_streak):
        try:
            value = func(
                previous_target=previous,
                proposed_target=proposed,
                risk_confirmation_count=risk_streak,
                leadership_strong_streak=leadership_streak,
            )
        except TypeError:
            value = func(previous, proposed, risk_streak, leadership_streak)
        return _normalise_weights(value)

    fully_risky = {"global": 0.75, "m2": 0.25, "cash": 0.00}
    defensive = {"global": 0.50, "m2": 0.00, "cash": 0.50}
    assert apply(fully_risky, defensive, 0, 0) == pytest.approx(defensive)

    # One confirming observation cannot add risk or M2.
    one_month = apply(defensive, fully_risky, 1, 1)
    assert one_month["cash"] >= defensive["cash"] - 1e-12
    assert one_month["m2"] == pytest.approx(0.0)

    # Two consecutive confirmations may adopt the full proposed target.
    assert apply(defensive, fully_risky, 2, 2) == pytest.approx(fully_risky)

    # M2 removal is immediate even when total risky exposure is unchanged.
    no_m2 = {"global": 1.00, "m2": 0.00, "cash": 0.00}
    assert apply(fully_risky, no_m2, 0, 0)["m2"] == pytest.approx(0.0)


def test_next_session_execution_is_strictly_after_review_and_earliest() -> None:
    func = _callable("resolve_next_execution_date", "next_execution_date")
    calendar = pd.DatetimeIndex(["2024-03-27", "2024-03-28", "2024-04-02", "2024-04-03"])
    try:
        observed = func(calendar=calendar, review_date=pd.Timestamp("2024-03-28"))
    except TypeError:
        observed = func(calendar, pd.Timestamp("2024-03-28"))
    assert pd.Timestamp(observed) == pd.Timestamp("2024-04-02")


def test_monthly_ledger_uses_current_point_in_time_top7_and_valid_execution() -> None:
    ledger = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_MONTHLY_REGIME_LEDGER.csv")
    assert len(ledger) > 0
    decision_dates = pd.to_datetime(ledger["decision_date"])
    execution_dates = pd.to_datetime(ledger["execution_date"], errors="coerce")
    assert decision_dates.max() <= CUTOFF
    assert execution_dates.dropna().max() <= CUTOFF
    assert (execution_dates.dropna().to_numpy() > decision_dates.loc[execution_dates.notna()].to_numpy()).all()
    for row in ledger.itertuples(index=False):
        families = _parse_family_list(row.top7_families)
        assert len(families) == len(set(families))
        assert len(families) == min(7, int(row.eligible_family_count))
        assert int(row.eligible_family_count) >= 3

    # If the core exposes its accepted daily feature panel, independently verify
    # that every stored TOP7 is exactly the strongest current, not future, set.
    load_data = getattr(a4f, "load_data", None)
    if callable(load_data):
        data = load_data()
        features = getattr(data, "daily_features", None)
        if isinstance(features, pd.DataFrame):
            date_col = "date" if "date" in features else "signal_date"
            family_col = "economic_exposure_family_id"
            score_col = next(
                (name for name in ("M2_BASE", "M2_INTERMEDIATE_5H", "A4E_M2_BASE") if name in features),
                None,
            )
            if score_col is not None and family_col in features:
                check = ledger.iloc[:: max(1, len(ledger) // 24)]
                for row in check.itertuples(index=False):
                    date = pd.Timestamp(row.decision_date)
                    current = features.loc[
                        pd.to_datetime(features[date_col]).eq(date)
                        & features[score_col].notna(),
                        [family_col, score_col],
                    ]
                    expected = (
                        current.sort_values(
                            [score_col, family_col], ascending=[False, True], kind="mergesort"
                        )[family_col]
                        .head(min(7, len(current)))
                        .astype(str)
                        .tolist()
                    )
                    assert _parse_family_list(row.top7_families) == expected


def test_all_required_34_outputs_and_16_charts_exist() -> None:
    names = {path.name for path in STAGE_ROOT.iterdir() if path.is_file()}
    assert len(REQUIRED_OUTPUTS) == 34
    assert len(REQUIRED_CHARTS) == 16
    assert REQUIRED_OUTPUTS.issubset(names), sorted(REQUIRED_OUTPUTS - names)
    assert REQUIRED_CHARTS.issubset(names), sorted(REQUIRED_CHARTS - names)
    for name in REQUIRED_CHARTS:
        assert (STAGE_ROOT / name).stat().st_size > 1_000


def test_every_csv_and_json_is_parseable_and_nonempty() -> None:
    csv_paths = sorted(STAGE_ROOT.glob("*.csv"))
    json_paths = sorted(STAGE_ROOT.glob("*.json"))
    assert csv_paths
    assert json_paths
    for path in csv_paths:
        frame = pd.read_csv(path)
        assert len(frame.columns) > 0, path.name
        assert len(frame) > 0, path.name
    for path in json_paths:
        parsed = _json(path)
        assert isinstance(parsed, dict), path.name
        assert parsed, path.name


def test_correctness_registry_contains_no_failure() -> None:
    registry = _json(STAGE_ROOT / "UKACTIVE_A4F_SIPP_CORRECTNESS_TESTS.json")
    summary = registry.get("summary", registry.get("correctness", {}))
    fail_count = summary.get("FAIL", summary.get("fail", 0))
    assert int(fail_count) == 0
    tests = registry.get("tests", registry.get("checks", []))
    assert tests
    assert all(str(item["status"]).upper() == "PASS" for item in tests)


def test_higher_alpha_diagnostic_is_never_selection_eligible() -> None:
    results = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_DYNAMIC_POLICY_RESULTS.csv")
    diagnostic = results.loc[results["policy_id"].eq("POLICY_5_HIGHER_ALPHA_DIAGNOSTIC")]
    assert len(diagnostic) > 0
    assert not diagnostic["eligible_for_selection"].astype(bool).any()
    assert diagnostic["promotion_status"].eq(
        "NOT_ELIGIBLE_HIGHER_ALPHA_DIAGNOSTIC"
    ).all()
    assert not diagnostic["all_mandatory_gates"].astype(bool).any()


def test_serious_static_m2_candidate_family_gate_is_complete() -> None:
    incremental = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_M2_INCREMENTAL_VALUE.csv")
    serious = incremental.loc[
        incremental["window_id"].eq("FULL_COMMON_HISTORY")
        & incremental["incremental_cagr"].gt(0)
        & incremental["exclude_2025_incremental_cagr"].ge(0)
        & incremental["double_cost_incremental_cagr"].ge(0)
    ]
    assert len(serious) > 0
    assert serious["family_exclusion_status"].isin(
        {"STATIC_FAMILY_GATE_PASS", "STATIC_FAMILY_GATE_FAIL"}
    ).all()
    influence = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_FAMILY_INFLUENCE.csv")
    for strategy_id in serious["candidate_id"].unique():
        rows = influence.loc[influence["policy_id"].eq(strategy_id)]
        assert rows["exclusion_type"].eq("LEAVE_ONE_FAMILY_OUT").any()
        assert rows["exclusion_type"].eq("EXCLUDE_TOP_5_FAMILY_CONTRIBUTORS").any()


def test_manifest_hashes_reproduce_all_listed_outputs() -> None:
    manifest = _json(STAGE_ROOT / "UKACTIVE_A4F_SIPP_MANIFEST.json")
    assert manifest["authoritative_cutoff"] == "2026-08-21"
    listed = manifest["outputs"]
    assert listed
    listed_names = {str(item["path"]) for item in listed}
    # The manifest may omit itself to avoid a recursive hash, but every other
    # required scientific output and every chart must be inventoried.
    assert (REQUIRED_OUTPUTS - {"UKACTIVE_A4F_SIPP_MANIFEST.json"}).issubset(listed_names)
    assert REQUIRED_CHARTS.issubset(listed_names)
    for item in listed:
        path = STAGE_ROOT / item["path"]
        assert path.is_file(), path
        assert int(item["size_bytes"]) == path.stat().st_size
        assert item["sha256"] == _sha256(path)
