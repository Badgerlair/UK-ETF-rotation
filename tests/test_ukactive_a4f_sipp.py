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
    "UKACTIVE_A4F_SIPP_SECONDARY_REGIME_DIAGNOSTICS.csv",
    "UKACTIVE_A4F_SIPP_REGIME_EPISODE_LEDGER.csv",
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
    "UKACTIVE_A4F_SIPP_POLICY_DECISION_LEDGER.csv",
    # Robustness (4)
    "UKACTIVE_A4F_SIPP_YEAR_EXCLUSION_RESULTS.csv",
    "UKACTIVE_A4F_SIPP_FAMILY_INFLUENCE.csv",
    "UKACTIVE_A4F_SIPP_THRESHOLD_SENSITIVITY.csv",
    "UKACTIVE_A4F_SIPP_COST_STRESS.csv",
    "UKACTIVE_A4F_SIPP_RANDOM_SELECTION_CONTROL.csv",
    "UKACTIVE_A4F_SIPP_HOLDING_SPELL_LEDGER.csv",
    "UKACTIVE_A4F_SIPP_HOLDING_SPELL_INFLUENCE.csv",
    "UKACTIVE_A4F_SIPP_WINNER_FALSE_LEADER_COMPARISON.csv",
    "UKACTIVE_A4F_SIPP_LONGER_CORE_ONLY_RESULTS.csv",
    "UKACTIVE_A4F_SIPP_POLICY_INFERENCE.csv",
    "UKACTIVE_A4F_SIPP_CORRECTNESS_TESTS.json",
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


def test_common_window_has_complete_valid_observation_regime_coverage() -> None:
    ledger = pd.read_csv(
        STAGE_ROOT / "UKACTIVE_A4F_SIPP_MONTHLY_REGIME_LEDGER.csv",
        parse_dates=["decision_date"],
    )
    # 2017-02-28 is the formation decision whose next-session execution starts
    # the common executable portfolio chain on 2017-03-01.
    common = ledger.loc[ledger["decision_date"].ge(pd.Timestamp("2017-02-28"))]
    assert len(common) > 0
    assert common["global_vol_63"].notna().all()
    assert common["risk_score"].notna().all()
    assert common["regime"].ne("REGIME_UNAVAILABLE").all()

    decisions = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_POLICY_DECISION_LEDGER.csv")
    counts = decisions.groupby(["policy_id", "switch_mode"]).size()
    assert len(counts) == 12
    assert counts.eq(len(common)).all()


def test_all_required_34_outputs_and_16_charts_exist() -> None:
    names = {path.name for path in STAGE_ROOT.iterdir() if path.is_file()}
    assert len(REQUIRED_OUTPUTS) == 44
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


def test_selected_static_m2_strategy_passes_family_gate() -> None:
    selected = _json(STAGE_ROOT / "UKACTIVE_A4F_SIPP_SELECTED_STRATEGY.json")
    if selected["switch_mode"] != "STATIC_MONTHLY" or selected["allocations"]["m2_weight"] <= 0:
        pytest.skip("Selected strategy is not a static M2 blend")
    incremental = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_M2_INCREMENTAL_VALUE.csv")
    rows = incremental.loc[
        incremental["candidate_id"].eq(selected["strategy_id"])
        & incremental["window_id"].eq("FULL_COMMON_HISTORY")
    ]
    assert len(rows) == 1
    assert rows.iloc[0]["family_exclusion_status"] == "STATIC_FAMILY_GATE_PASS"


def test_selected_strategy_embeds_exact_frozen_m2_operating_rule() -> None:
    selected = _json(STAGE_ROOT / "UKACTIVE_A4F_SIPP_SELECTED_STRATEGY.json")
    spec = selected["m2_specification"]
    assert spec["signal_id"] == "M2_BASE"
    assert spec["relative_strength_weights"] == EXPECTED_M2_WEIGHTS
    assert spec["breadth"] == 7
    assert spec["within_sleeve_weighting"] == "EQUAL_WEIGHT"
    assert "POINT_IN_TIME" in spec["point_in_time_universe"]
    assert "TOP7" in spec["replacement_rule"]
    assert selected["current_operational_fallback"]["strategy_id"] == "GLOBAL_75_CASH25"


def test_selected_state_machine_reconciles_exactly() -> None:
    selected = _json(STAGE_ROOT / "UKACTIVE_A4F_SIPP_SELECTED_STRATEGY.json")
    state_machine = _json(STAGE_ROOT / "UKACTIVE_A4F_SIPP_REGIME_STATE_MACHINE.json")
    rows = state_machine["rows"]
    assert len(rows) == 8
    assert state_machine["selected_strategy"] == selected["strategy_id"]
    assert state_machine["switch_mode"] == selected["switch_mode"]
    expected_regime = {
        (0, "LEADERSHIP_WEAK"): "R1_BROAD_RISK_ON",
        (1, "LEADERSHIP_WEAK"): "R1_BROAD_RISK_ON",
        (0, "LEADERSHIP_STRONG"): "R2_LEADERSHIP_RISK_ON",
        (1, "LEADERSHIP_STRONG"): "R2_LEADERSHIP_RISK_ON",
        (2, "LEADERSHIP_STRONG"): "R3_ISOLATED_LEADERSHIP",
        (3, "LEADERSHIP_STRONG"): "R3_ISOLATED_LEADERSHIP",
        (2, "LEADERSHIP_WEAK"): "R4_CAPITAL_PRESERVATION",
        (3, "LEADERSHIP_WEAK"): "R4_CAPITAL_PRESERVATION",
    }
    allocations = selected["allocations"]
    for row in rows:
        assert row["regime"] == expected_regime[(row["risk_score"], row["leadership_state"])]
        assert row["swda_allocation"] + row["m2_allocation"] + row["cash_allocation"] == pytest.approx(1.0)
        assert min(row["swda_allocation"], row["m2_allocation"], row["cash_allocation"]) >= 0
        if selected["switch_mode"] == "STATIC_MONTHLY":
            assert row["swda_allocation"] == pytest.approx(allocations["global_weight"])
            assert row["m2_allocation"] == pytest.approx(allocations["m2_weight"])
            assert row["cash_allocation"] == pytest.approx(allocations["cash_weight"])


def test_all_generated_scientific_dates_respect_cutoff() -> None:
    observed = 0
    for path in STAGE_ROOT.glob("*.csv"):
        frame = pd.read_csv(path)
        for column in frame.columns:
            if column == "date" or column.endswith("_date"):
                parsed = pd.to_datetime(frame[column], errors="coerce").dropna()
                observed += len(parsed)
                assert parsed.le(CUTOFF).all(), f"{path.name}:{column} exceeds cutoff"
    assert observed > 0


def test_policy_execution_endpoint_evidence_is_complete() -> None:
    decisions = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_POLICY_DECISION_LEDGER.csv")
    assert "execution_total_return_endpoints_gbp_json" in decisions
    executable = decisions.loc[decisions["execution_date"].notna()]
    assert len(executable) > 0
    for row in executable.itertuples(index=False):
        target = json.loads(row.target_weights_json)
        endpoints = json.loads(row.execution_total_return_endpoints_gbp_json)
        risky_families = [family for family, weight in target.items() if float(weight) > 0]
        assert set(risky_families).issubset(endpoints)


def test_holding_spell_and_long_core_audits_are_complete() -> None:
    spells = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_HOLDING_SPELL_LEDGER.csv")
    comparison = pd.read_csv(
        STAGE_ROOT / "UKACTIVE_A4F_SIPP_WINNER_FALSE_LEADER_COMPARISON.csv"
    )
    long_core = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_LONGER_CORE_ONLY_RESULTS.csv")
    assert len(spells) > 0
    assert spells["holding_spell_id"].tolist() == [
        f"SPELL-{index:04d}" for index in range(1, len(spells) + 1)
    ]
    expected_order = spells.sort_values(
        ["normalised_arithmetic_return_contribution", "signal_date", "family", "execution_exit_date"],
        ascending=[False, True, True, True],
        kind="mergesort",
        na_position="last",
    ).reset_index(drop=True)
    pd.testing.assert_frame_equal(spells.reset_index(drop=True), expected_order)
    assert spells["pre_entry_126_valid_observation_return"].notna().any()
    assert spells["held_family_total_return"].notna().all()
    assert spells["entry_timing_diagnostic_status"].eq(
        "EX_POST_MECHANISM_DIAGNOSTIC_NOT_USED_IN_SELECTION"
    ).all()
    assert set(spells["winner_class"]) == {"WINNER", "FALSE_OR_LOSING_LEADER"}
    assert set(comparison["winner_class"]) == set(spells["winner_class"])
    assert comparison["scientific_ranking_basis"].eq(
        "NORMALISED_ARITHMETIC_RETURN_CONTRIBUTION"
    ).all()
    assert len(long_core) == 8
    assert set(long_core["cost_scenario"]) == {"BASE", "DOUBLE"}
    assert long_core["comparison_status"].eq(
        "CORE_ONLY_CONTEXT_NOT_DIRECTLY_RANKED_AGAINST_2017_ROTATION"
    ).all()


def test_strategy_switch_counts_and_matched_gate_labels_are_resolved() -> None:
    dynamic = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_DYNAMIC_POLICY_RESULTS.csv")
    fixed = dynamic.loc[
        dynamic["policy_id"].eq("POLICY_0_STATIC_DEFENSIVE_CONTROL")
        & dynamic["window_id"].eq("FULL_COMMON_HISTORY")
        & dynamic["cost_scenario"].eq("BASE")
    ]
    assert len(fixed) == 2
    assert fixed["annual_strategy_changes"].eq(0.0).all()
    assert fixed["annual_rebalance_events"].gt(0.0).all()

    matched = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_MATCHED_RISK_CONTROLS.csv")
    assert not matched["matched_risk_gate_status"].str.contains("PENDING", na=False).any()
    primary = matched.loc[
        matched["control_type"].eq("MATCHED_AVERAGE_EXPOSURE")
        & matched["switch_mode"].isin(
            {"SWITCH_IMMEDIATE_MONTHLY", "SWITCH_ASYMMETRIC_HYSTERESIS"}
        )
        & ~matched["policy_id"].eq("POLICY_5_HIGHER_ALPHA_DIAGNOSTIC")
    ]
    assert primary["matched_risk_gate_status"].isin(
        {"MATCHED_RISK_GATE_PASS", "MATCHED_RISK_GATE_FAIL"}
    ).all()

    selected = _json(STAGE_ROOT / "UKACTIVE_A4F_SIPP_SELECTED_STRATEGY.json")
    if selected["switch_mode"] == "STATIC_MONTHLY":
        runbook = (STAGE_ROOT / "UKACTIVE_A4F_SIPP_MONTHLY_RUNBOOK.md").read_text(
            encoding="utf-8"
        )
        assert "Regime fields are recorded as telemetry only" in runbook


def test_transition_ledger_uses_prior_episode_duration_and_real_cash_comparison() -> None:
    transitions = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_REGIME_TRANSITIONS.csv")
    assert transitions["average_prior_duration_months"].gt(0).all()
    assert transitions["risky_minus_cash_1m"].notna().all()
    fixed = transitions.loc[
        transitions["policy_id"].eq("POLICY_0_STATIC_DEFENSIVE_CONTROL")
    ]
    assert len(fixed) > 0
    assert fixed["allocation_switch_count"].eq(0).all()
    assert fixed["transition_classification"].eq("NO_ALLOCATION_SWITCH").all()

    ledger = pd.read_csv(
        STAGE_ROOT / "UKACTIVE_A4F_SIPP_MONTHLY_REGIME_LEDGER.csv",
        parse_dates=["decision_date"],
    )
    ordered = ledger.loc[
        ledger["decision_date"].ge(pd.Timestamp("2017-02-28"))
        & ledger["regime"].ne("REGIME_UNAVAILABLE")
    ].sort_values("decision_date").reset_index(drop=True)
    ordered["prior_regime"] = ordered["regime"].shift()
    ordered["episode"] = ordered["regime"].ne(ordered["regime"].shift()).cumsum()
    ordered["position"] = ordered.groupby("episode").cumcount() + 1
    ordered["expected_prior_duration"] = ordered["position"].shift(1)
    events = ordered.loc[
        ordered["regime"].ne(ordered["prior_regime"])
        & ordered["prior_regime"].notna()
    ]
    expected = (
        events.groupby(["prior_regime", "regime"])["expected_prior_duration"]
        .mean()
        .rename("expected")
    )
    observed = fixed.set_index(["prior_regime", "new_regime"])[
        "average_prior_duration_months"
    ]
    pd.testing.assert_series_equal(
        observed.sort_index(), expected.reindex(observed.index).sort_index(), check_names=False
    )


def test_year_scorecard_has_true_sleeve_weights_and_selected_exclusions() -> None:
    score = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_YEAR_BY_YEAR_SCORECARD.csv")
    global_rows = score.loc[score["strategy_id"].eq("GLOBAL_100")]
    assert global_rows["average_swda_weight"].eq(1.0).all()
    assert global_rows["average_m2_weight"].eq(0.0).all()
    assert global_rows["average_cash_weight"].eq(0.0).all()
    risk_rows = score.loc[
        score["policy_id"].eq("POLICY_1_RISK_TIMING_ONLY")
        & score["switch_mode"].eq("SWITCH_IMMEDIATE_MONTHLY")
    ]
    assert risk_rows["average_cash_weight"].round(8).nunique() > 1

    selected = _json(STAGE_ROOT / "UKACTIVE_A4F_SIPP_SELECTED_STRATEGY.json")
    exclusions = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_YEAR_EXCLUSION_RESULTS.csv")
    rows = exclusions.loc[
        exclusions["policy_id"].eq(selected["strategy_id"])
        & exclusions["switch_mode"].eq(selected["switch_mode"])
    ]
    if selected["allocations"]["m2_weight"] > 0:
        assert len(rows) == 13
        assert {"EXCLUDE_2025", "EXCLUDE_2020", "EXCLUDE_2020_AND_2025"}.issubset(
            set(rows["excluded_period"])
        )
        assert rows["excluded_period"].str.startswith("LEAVE_").sum() == 10


def test_switch_attribution_is_scoped_to_actual_allocation_events() -> None:
    attribution = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_SWITCH_ATTRIBUTION.csv")
    assert attribution["counterfactual_scope"].eq(
        "ONE_MONTH_AFTER_ACTUAL_ALLOCATION_SWITCH_VS_STATIC_MATCHED_CONTROL;NOT_DRAWDOWN_ATTRIBUTION"
    ).all()
    fixed = attribution.loc[
        attribution["policy_id"].eq("POLICY_0_STATIC_DEFENSIVE_CONTROL")
    ]
    assert fixed["switch_event_count"].eq(0).all()
    assert fixed["switching_gain"].abs().le(1e-12).all()


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


def test_complete_annual_policy_switch_matrix_and_state_attribution() -> None:
    score = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_YEAR_BY_YEAR_SCORECARD.csv")
    attribution = pd.read_csv(
        STAGE_ROOT / "UKACTIVE_A4F_SIPP_YEAR_BY_YEAR_ATTRIBUTION.csv"
    )
    dynamic = score.loc[score["policy_id"].str.startswith("POLICY_", na=False)]
    assert len(dynamic) == 6 * 2 * 10
    assert not dynamic.duplicated(["policy_id", "switch_mode", "year"]).any()
    assert set(dynamic["year"]) == set(range(2017, 2027))
    state_columns = [
        *[f"months_risk_score_{score_id}" for score_id in range(4)],
        "months_R1_BROAD_RISK_ON",
        "months_R2_LEADERSHIP_RISK_ON",
        "months_R3_ISOLATED_LEADERSHIP",
        "months_R4_CAPITAL_PRESERVATION",
    ]
    assert dynamic[state_columns].notna().all().all()
    dynamic_attr = attribution.loc[
        attribution["policy_id"].str.startswith("POLICY_", na=False)
    ]
    assert len(dynamic_attr) == len(dynamic)
    assert dynamic_attr[state_columns + ["strategy_switches"]].notna().all().all()
    assert dynamic_attr[
        [
            "risk_timing_contribution",
            "m2_selection_contribution",
            "interaction_contribution",
            "cash_yield_contribution",
            "cost_contribution",
        ]
    ].notna().all().all()


def test_exact_risk_score_substates_and_differentials_are_complete() -> None:
    summary = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_REGIME_SUMMARY.csv")
    rankings = pd.read_csv(
        STAGE_ROOT / "UKACTIVE_A4F_SIPP_REGIME_STRATEGY_RANKINGS.csv"
    )
    risk = summary.loc[summary["summary_level"].eq("EXACT_RISK_SCORE_SUBSTATE")]
    assert set(risk["risk_score_substate"].astype(int)) == {0, 1, 2, 3}
    strategy_count = summary.loc[
        summary["summary_level"].eq("FOUR_STATE_REGIME"), "strategy_id"
    ].nunique()
    assert len(risk) == strategy_count * 4
    assert risk[["m2_minus_global", "cash_minus_risky"]].notna().all().all()
    risk_rankings = rankings.loc[
        rankings["summary_level"].eq("EXACT_RISK_SCORE_SUBSTATE")
    ]
    assert len(risk_rankings) == len(risk)


def test_cash0_falsification_is_reproducible_and_has_no_cash1_filter() -> None:
    random = pd.read_csv(
        STAGE_ROOT / "UKACTIVE_A4F_SIPP_RANDOM_SELECTION_CONTROL.csv"
    )
    assert set(random["control_id"]) == {
        "RANDOM_SELECTION_SAME_RISKY_COUNT",
        "MONTHLY_RANK_SHUFFLE",
    }
    assert dict(zip(random["control_id"], random["seed"])) == {
        "RANDOM_SELECTION_SAME_RISKY_COUNT": 20260824,
        "MONTHLY_RANK_SHUFFLE": 20260825,
    }
    assert random["simulation_count"].eq(10_000).all()
    assert random["candidate_id"].eq("M2_TOP7_CASH0_100").all()
    assert random["eligibility_rule"].eq(
        "ALL_POINT_IN_TIME_SIGNAL_ELIGIBLE_FAMILIES;NO_ABOVE_CASH_FILTER"
    ).all()


def test_all_static_m2_family_and_direct_incremental_audits_are_complete() -> None:
    direct = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_M2_INCREMENTAL_VALUE.csv")
    influence = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_FAMILY_INFLUENCE.csv")
    assert direct["candidate_id"].nunique() == 9
    assert len(direct) == 9 * 5
    assert direct[
        [
            "exclude_2025_incremental_cagr",
            "double_cost_incremental_cagr",
            "leave_one_family_minimum_incremental_cagr",
            "exclude_top_1_family_incremental_cagr",
            "exclude_top_3_family_incremental_cagr",
            "exclude_top_5_family_incremental_cagr",
        ]
    ].notna().all().all()
    for strategy_id in direct["candidate_id"].unique():
        rows = influence.loc[
            influence["policy_id"].eq(strategy_id)
            & influence["switch_mode"].eq("STATIC_MONTHLY")
        ]
        assert rows["exclusion_type"].eq("LEAVE_ONE_FAMILY_OUT").sum() > 0
        assert {
            "EXCLUDE_TOP_1_FAMILY_CONTRIBUTORS",
            "EXCLUDE_TOP_3_FAMILY_CONTRIBUTORS",
            "EXCLUDE_TOP_5_FAMILY_CONTRIBUTORS",
        }.issubset(set(rows["exclusion_type"]))


def test_holding_spell_influence_covers_raw_selected_and_p3_both_modes() -> None:
    influence = pd.read_csv(
        STAGE_ROOT / "UKACTIVE_A4F_SIPP_HOLDING_SPELL_INFLUENCE.csv"
    )
    expected = {
        ("M2_TOP7_CASH0_100", "STATIC_MONTHLY"),
        ("GLOBAL_50_M2_50", "STATIC_MONTHLY"),
        ("POLICY_3_BALANCED_REGIME_STRATEGY", "SWITCH_IMMEDIATE_MONTHLY"),
        (
            "POLICY_3_BALANCED_REGIME_STRATEGY",
            "SWITCH_ASYMMETRIC_HYSTERESIS",
        ),
    }
    assert set(zip(influence["policy_id"], influence["switch_mode"])) == expected
    assert influence.groupby(["policy_id", "switch_mode"])["exclusion_count"].apply(
        lambda values: set(values) == {1, 3, 5}
    ).all()
    assert influence["exclusion_ranking_field"].eq(
        "normalised_arithmetic_return_contribution"
    ).all()


def test_matched_control_matrix_includes_p5_and_static_m2_diagnostic() -> None:
    matched = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_MATCHED_RISK_CONTROLS.csv")
    dynamic = matched.loc[matched["policy_id"].str.startswith("POLICY_", na=False)]
    assert len(dynamic) == 6 * 2 * 4 * 5
    assert not dynamic.duplicated(
        ["policy_id", "switch_mode", "control_type", "window_id"]
    ).any()
    p5 = dynamic.loc[dynamic["policy_id"].eq("POLICY_5_HIGHER_ALPHA_DIAGNOSTIC")]
    assert len(p5) == 2 * 4 * 5
    assert p5["matched_risk_gate_status"].eq(
        "DIAGNOSTIC_NOT_ELIGIBLE_FOR_SELECTION"
    ).all()
    static_m2 = matched.loc[
        matched["policy_id"].eq("M2_TOP7_CASH0_100")
        & matched["switch_mode"].eq("STATIC_MONTHLY")
    ]
    assert len(static_m2) == 4 * 5
    assert static_m2["matched_risk_gate_status"].eq(
        "STATIC_M2_DIAGNOSTIC_NOT_DYNAMIC_PROMOTION_GATE"
    ).all()


def test_secondary_diagnostics_oracle_and_cost_outputs_are_complete() -> None:
    secondary = pd.read_csv(
        STAGE_ROOT / "UKACTIVE_A4F_SIPP_SECONDARY_REGIME_DIAGNOSTICS.csv"
    )
    assert len(secondary) == 10
    assert secondary["threshold_rule"].eq(
        "PRIOR_ONLY_EXPANDING_MEDIAN;CURRENT_EXCLUDED"
    ).all()
    assert secondary["evidence_class"].eq(
        "E1_SECONDARY_DESCRIPTIVE_NOT_POLICY_INPUT"
    ).all()
    oracle = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_ORACLE_DIAGNOSTICS.csv")
    monthly_oracle = oracle.loc[oracle["oracle_type"].eq("MONTHLY_ORACLE")]
    assert monthly_oracle.iloc[0]["period_id"] == "2017-03"
    costs = pd.read_csv(STAGE_ROOT / "UKACTIVE_A4F_SIPP_COST_STRESS.csv")
    assert len(costs) == 6 * 2 * 5 * 2
    assert costs[["gross_cagr", "net_cagr", "cost_drag"]].notna().all().all()


def test_selected_state_machine_is_self_contained_and_capital_status_unambiguous() -> None:
    selected = _json(STAGE_ROOT / "UKACTIVE_A4F_SIPP_SELECTED_STRATEGY.json")
    decision = _json(STAGE_ROOT / "UKACTIVE_A4F_SIPP_DECISION.json")
    state = _json(STAGE_ROOT / "UKACTIVE_A4F_SIPP_REGIME_STATE_MACHINE.json")
    assert selected["research_selection"]["status"] == "SHADOW_ONLY"
    assert selected["capital_authorised_for_research_selection"] is False
    assert selected["current_operational_whole_sipp"] == {
        "strategy_id": "GLOBAL_75_CASH25",
        "status": "CURRENT_OPERATING_RULE_WHILE_RESEARCH_SELECTION_IS_SHADOW_ONLY",
        "swda_weight": 0.75,
        "m2_weight": 0.0,
        "cash_weight": 0.25,
        "review": "MONTHLY",
    }
    assert decision["research_selection"]["capital_authorised"] is False
    for key in (
        "risk_state_definition",
        "leadership_state_definition",
        "regime_map",
        "decision_timestamp",
        "execution_contract",
        "instrument_map",
        "costs",
        "suspension_rules",
    ):
        assert key in state
    assert len(state["suspension_rules"]) >= 7


def test_final_report_contains_all_mandated_sections_and_direct_answers() -> None:
    report = (STAGE_ROOT / "UKACTIVE_A4F_SIPP_FINAL_DECISION_REPORT.md").read_text(
        encoding="utf-8"
    )
    for heading in (
        "## YEAR-BY-YEAR CONCLUSION",
        "## REGIME CONCLUSION",
        "## ALPHA-ALLOCATION CONCLUSION",
        "## RISK-ALLOCATION CONCLUSION",
        "## BEST AVAILABLE WHOLE-SIPP STRATEGY",
        "## REGIME STATE MACHINE",
        "## EXPECTED OPERATING CHARACTERISTICS",
        "## CURRENT EVIDENCE GRADE",
        "## DEPLOYMENT TIER",
        "## MONTHLY OPERATING RULE",
        "## FAILURE MODES",
        "## SUSPENSION RULES",
        "## REMAINING EVIDENCE GAP",
    ):
        assert heading in report
    for number in range(1, 26):
        assert f"{number}. **" in report
    assert "GLOBAL_50_M2_50" in report
    assert "75% SWDA / 25% GBP cash" in report
    assert "no pension capital is authorised" in report
