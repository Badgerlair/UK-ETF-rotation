"""Causal primitives for UKACTIVE-A4F-SIPP regime research.

This module is intentionally a thin layer over the immutable A4D and A4E-SIPP
engines.  It implements only the A4F preregistered, prior-only regime state,
static target maps, bounded dynamic policies, and matched-static controls.  It
does not write research outputs and it does not select a strategy.

Timing contract
---------------
Signals are observed after a valid XLON month-end close.  Portfolio targets are
passed to the accepted A4D/A4E planner, which executes at the first common valid
endpoint one to three XLON sessions later.  The signal date therefore never
earns its own close-to-close return.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

import ukactive_a4b_core as a4b
import ukactive_a4d_core as a4d
import ukactive_a4e_sipp_core as a4e


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
STAGE_ROOT = PROGRAMME_ROOT / "UKACTIVE-A4F-SIPP-REGIME"
PREREGISTRATION_PATH = STAGE_ROOT / "UKACTIVE_A4F_SIPP_PREREGISTRATION.json"

AUTHORITATIVE_CUTOFF = pd.Timestamp("2026-08-21")
COMMON_CAUSAL_CHAIN_START = pd.Timestamp("2017-02-03")
GLOBAL_SEED_START = pd.Timestamp("2010-01-08")
M2_DIAGNOSTIC_SEED_START = pd.Timestamp("2014-01-31")
M2_WEIGHTS = {
    "RS21": 0.10,
    "RS42": 0.15,
    "RS63": 0.25,
    "RS126": 0.30,
    "RS252": 0.20,
}
M2_BREADTH = 7
ROTATION_BREADTH = 7
GLOBAL_FAMILY = "GLOBAL_DEVELOPED_WORLD"
WARNING = "E2 DEVELOPMENTAL; A4F THRESHOLDS ARE PRIOR-ONLY; NO E3 CONFIRMATION"

RISK_MAPS: dict[str, tuple[float, float, float, float]] = {
    "RISK_ALWAYS_100": (1.00, 1.00, 1.00, 1.00),
    "RISK_FIXED_75": (0.75, 0.75, 0.75, 0.75),
    "RISK_SCORE_25": (1.00, 0.75, 0.50, 0.25),
    "RISK_SCORE_33": (1.00, 0.67, 0.33, 0.00),
}

ALPHA_MAPS: dict[str, tuple[float, float]] = {
    # (weak-leadership M2 fraction of risky capital, strong-leadership fraction)
    "ALPHA_0": (0.00, 0.00),
    "ALPHA_25": (0.00, 0.25),
    "ALPHA_50_DIAGNOSTIC": (0.00, 0.50),
}

POLICY_MAP: dict[str, tuple[str, str]] = {
    "POLICY_0_STATIC_DEFENSIVE_CONTROL": ("RISK_FIXED_75", "ALPHA_0"),
    "POLICY_1_RISK_TIMING_ONLY": ("RISK_SCORE_25", "ALPHA_0"),
    "POLICY_2_ALPHA_TIMING_ONLY": ("RISK_ALWAYS_100", "ALPHA_25"),
    "POLICY_3_BALANCED_REGIME_STRATEGY": ("RISK_SCORE_25", "ALPHA_25"),
    "POLICY_4_DEFENSIVE_REGIME_STRATEGY": ("RISK_SCORE_33", "ALPHA_25"),
    "POLICY_5_HIGHER_ALPHA_DIAGNOSTIC": ("RISK_SCORE_25", "ALPHA_50_DIAGNOSTIC"),
}

SWITCH_MODES = {"SWITCH_IMMEDIATE_MONTHLY", "SWITCH_ASYMMETRIC_HYSTERESIS"}


@dataclass
class HysteresisState:
    """Mutable state for the frozen asymmetric switch rule."""

    initialised: bool = False
    applied_risky: float = 0.0
    applied_m2_fraction: float = 0.0
    prior_desired_risky: float | None = None
    re_risk_streak: int = 0
    strong_streak: int = 0


def read_preregistration() -> dict[str, Any]:
    """Read the protocol committed before any A4F result calculation."""

    return json.loads(PREREGISTRATION_PATH.read_text(encoding="utf-8"))


def load_data() -> a4d.A4DData:
    """Load immutable A4D/A4E data and enforce the A4F evidence cutoff.

    The returned object is the accepted :class:`ukactive_a4d_core.A4DData`, so
    all existing portfolio and attribution helpers remain usable.
    """

    data = a4e.load_data()
    maxima = {
        "calendar": pd.Timestamp(data.base.research.calendar.max()),
        "daily_features": pd.Timestamp(data.daily_features["date"].max()),
        "cash": pd.Timestamp(data.base.cash_index.dropna().index.max()),
    }
    offenders = {name: value for name, value in maxima.items() if value > AUTHORITATIVE_CUTOFF}
    if offenders:
        raise AssertionError(f"A4F post-cutoff input detected: {offenders}")
    if tuple(a4e.SIGNAL_WEIGHTS["M2_BASE"]) != tuple(M2_WEIGHTS.values()):
        raise AssertionError("Frozen M2 weights differ from the A4F protocol")
    return data


def prior_only_quantile(
    values: pd.Series,
    quantile: float,
    minimum_prior: int | None = None,
    current_position: int | None = None,
    min_prior: int | None = None,
) -> pd.Series | float | None:
    """Return a prior-only quantile series or one value at ``current_position``.

    The scalar form exists for focused correctness tests; the production
    ledger uses the vector form.  Both strictly exclude the current row.
    """

    if not 0.0 <= float(quantile) <= 1.0:
        raise ValueError("quantile must be in [0, 1]")
    minimum = int(minimum_prior if minimum_prior is not None else min_prior or 0)
    if minimum < 1:
        raise ValueError("minimum_prior must be positive")
    numeric = pd.to_numeric(values, errors="coerce")
    if current_position is not None:
        prior = numeric.iloc[: int(current_position)].dropna()
        if len(prior) < minimum:
            return None
        return float(prior.quantile(float(quantile)))
    return numeric.shift(1).expanding(min_periods=minimum).quantile(float(quantile))


def risk_score(
    global_126_excess: float,
    global_252_excess: float,
    global_vol_63: float,
    high_vol_threshold: float,
) -> int | None:
    """Calculate the frozen 0--3 A4F risk score with exact tie semantics.

    Non-positive global excess is adverse (``<= 0``).  Volatility is adverse
    only when it is strictly greater than its prior-only threshold (``>``).
    Missing inputs return ``None`` rather than being silently treated as safe.
    """

    values = [global_126_excess, global_252_excess, global_vol_63, high_vol_threshold]
    if any(pd.isna(value) for value in values):
        return None
    return int(global_126_excess <= 0.0) + int(global_252_excess <= 0.0) + int(global_vol_63 > high_vol_threshold)


def regime_for(score: int | None, leadership_strong: bool | None) -> str:
    """Map the risk score and leadership flag to the frozen four-state regime."""

    if score is None or pd.isna(score) or leadership_strong is None or pd.isna(leadership_strong):
        return "REGIME_UNAVAILABLE"
    score = int(score)
    if score not in {0, 1, 2, 3}:
        raise ValueError(f"risk score outside 0--3: {score}")
    if score <= 1:
        return "R2_LEADERSHIP_RISK_ON" if bool(leadership_strong) else "R1_BROAD_RISK_ON"
    return "R3_ISOLATED_LEADERSHIP" if bool(leadership_strong) else "R4_CAPITAL_PRESERVATION"


def policy_target(*args: Any, **kwargs: Any) -> dict[str, float]:
    """Return aggregate SWDA/M2/cash weights for one immediate policy decision."""

    if args and isinstance(args[0], str):
        policy_id = str(args[0])
        score = kwargs.pop("risk_score", args[1] if len(args) > 1 else None)
        leadership_value = kwargs.pop("leadership_state", args[2] if len(args) > 2 else None)
    else:
        score = args[0] if args else kwargs.pop("score", kwargs.pop("risk_score", None))
        leadership_value = args[1] if len(args) > 1 else kwargs.pop("leadership_strong", kwargs.pop("leadership_state", None))
        policy_id = str(args[2] if len(args) > 2 else kwargs.pop("policy_id"))
    leadership_strong = (
        str(leadership_value).upper() == "LEADERSHIP_STRONG"
        if isinstance(leadership_value, str)
        else bool(leadership_value)
    )

    if policy_id not in POLICY_MAP:
        raise ValueError(f"Unknown A4F policy: {policy_id}")
    score = int(score)
    if score not in {0, 1, 2, 3}:
        raise ValueError("A policy target requires a valid risk score")
    risk_rule, alpha_rule = POLICY_MAP[policy_id]
    risky = float(RISK_MAPS[risk_rule][score])
    weak_fraction, strong_fraction = ALPHA_MAPS[alpha_rule]
    m2_fraction = float(strong_fraction if bool(leadership_strong) else weak_fraction)
    m2_weight = risky * m2_fraction
    global_weight = risky - m2_weight
    return {
        "global": global_weight,
        "m2": m2_weight,
        "cash": 1.0 - risky,
        "global_weight": global_weight,
        "m2_weight": m2_weight,
        "cash_weight": 1.0 - risky,
        "risky_weight": risky,
        "m2_fraction_of_risky": m2_fraction,
    }


def classify_leadership(
    spread_high: bool,
    persistence_high: bool,
    absolute_support_high: bool,
    threshold_history_available: bool,
    current_valid_family_count: int = 7,
) -> str:
    """Pure frozen leadership vote used by tests and the ledger builder."""

    ready = bool(threshold_history_available) and int(current_valid_family_count) >= 3
    strong = ready and sum(map(bool, (spread_high, persistence_high, absolute_support_high))) >= 2
    return "LEADERSHIP_STRONG" if strong else "LEADERSHIP_WEAK"


def classify_regime(score: int | None, leadership_state: str | bool | None) -> str:
    """String-friendly wrapper around :func:`regime_for`."""

    flag = (
        str(leadership_state).upper() == "LEADERSHIP_STRONG"
        if isinstance(leadership_state, str)
        else leadership_state
    )
    return regime_for(score, flag)


def calculate_risk_score(
    g126_excess: float,
    g252_excess: float,
    vol63: float,
    prior_vol_threshold: float,
) -> int | None:
    """Keyword-compatible alias for the frozen risk-score formula."""

    return risk_score(g126_excess, g252_excess, vol63, prior_vol_threshold)


def resolve_next_execution_date(
    calendar: pd.DatetimeIndex,
    review_date: pd.Timestamp,
) -> pd.Timestamp:
    """Resolve the first valid XLON session strictly after a review date."""

    index = pd.DatetimeIndex(calendar)
    candidates = index[index > pd.Timestamp(review_date)]
    if len(candidates) == 0:
        return pd.NaT
    return pd.Timestamp(candidates[0])


def _monthly_schedule(data: a4d.A4DData) -> pd.DatetimeIndex:
    dates = a4d.schedule_dates(data.base.research.calendar, "MONTHLY")
    return pd.DatetimeIndex(dates[dates <= AUTHORITATIVE_CUTOFF])


def _daily_trailing_volatility(data: a4d.A4DData) -> pd.Series:
    returns = data.base.research.daily_returns[GLOBAL_FAMILY].reindex(data.base.research.calendar).astype(float)
    # The A2R2 validity contract defines lookbacks by valid observations, not by
    # gap-free master-calendar rows.  Compute volatility over the last 63 valid
    # global return observations, then make that causal endpoint available for
    # at most the frozen three-session endpoint tolerance.  A longer gap fails
    # closed instead of carrying volatility indefinitely.
    valid = returns.dropna()
    valid_volatility = valid.rolling(63, min_periods=63).std(ddof=1) * math.sqrt(252.0)
    return valid_volatility.reindex(data.base.research.calendar, method="ffill", limit=3)


def _same_month_rank_persistence(current: pd.DataFrame, previous: pd.DataFrame | None) -> tuple[float, int]:
    if previous is None or current.empty or previous.empty:
        return np.nan, 0
    current_rank = current.set_index("economic_exposure_family_id")["m2_rank"]
    prior_rank = previous.set_index("economic_exposure_family_id")["m2_rank"]
    common = current_rank.index.intersection(prior_rank.index)
    if len(common) < 3:
        return np.nan, int(len(common))
    correlation = current_rank.loc[common].corr(prior_rank.loc[common], method="pearson")
    return (float(correlation) if pd.notna(correlation) else np.nan), int(len(common))


def _secondary_diagnostics(
    data: a4d.A4DData,
    date: pd.Timestamp,
    frame: pd.DataFrame,
    selected_families: set[str],
    prior_selected_families: set[str] | None,
) -> dict[str, float]:
    """Calculate preregistered descriptive variables; never used in allocation."""

    scores = frame["M2_INTERMEDIATE_5H"].dropna().astype(float)
    score_iqr = float(scores.quantile(0.75) - scores.quantile(0.25)) if len(scores) else np.nan
    rs63 = frame["RS_63"].dropna().astype(float)
    rs126 = frame["RS_126"].dropna().astype(float)
    retention = (
        len(selected_families & prior_selected_families) / float(ROTATION_BREADTH)
        if prior_selected_families is not None
        else np.nan
    )

    calendar = data.base.research.calendar
    position = int(calendar.get_loc(pd.Timestamp(date)))
    left = max(0, position - 125)
    eligible = sorted(frame["economic_exposure_family_id"].astype(str).unique())
    trailing = data.base.research.daily_returns.loc[calendar[left : position + 1], eligible].astype(float)
    valid_columns = trailing.columns[trailing.notna().sum().ge(63)]
    trailing = trailing[valid_columns]
    average_pairwise = np.nan
    pc1_share = np.nan
    if trailing.shape[1] >= 3:
        correlation = trailing.corr(min_periods=63)
        upper = correlation.to_numpy(float)[np.triu_indices(len(correlation), k=1)]
        finite_upper = upper[np.isfinite(upper)]
        if len(finite_upper):
            average_pairwise = float(finite_upper.mean())
        complete = trailing.dropna(axis=0, how="any")
        if complete.shape[0] >= 63:
            covariance = np.cov(complete.to_numpy(float), rowvar=False, ddof=1)
            eigenvalues = np.linalg.eigvalsh(covariance)
            denominator = float(np.clip(eigenvalues, 0.0, None).sum())
            if denominator > 0.0:
                pc1_share = float(max(eigenvalues[-1], 0.0) / denominator)

    global_level = data.base.research.wealth[GLOBAL_FAMILY].reindex(calendar).astype(float)
    trailing_global = global_level.iloc[max(0, position - 251) : position + 1].dropna()
    global_drawdown = (
        float(trailing_global.iloc[-1] / trailing_global.max() - 1.0)
        if len(trailing_global)
        else np.nan
    )
    return {
        "m2_score_cross_section_std": float(scores.std(ddof=0)) if len(scores) else np.nan,
        "m2_score_cross_section_iqr": score_iqr,
        "family_return_63_iqr": float(rs63.quantile(0.75) - rs63.quantile(0.25)) if len(rs63) else np.nan,
        "family_return_126_iqr": float(rs126.quantile(0.75) - rs126.quantile(0.25)) if len(rs126) else np.nan,
        "average_pairwise_126_return_correlation": average_pairwise,
        "first_principal_component_variance_share": pc1_share,
        "percentage_families_above_cash": float(frame["ABOVE_CASH_252"].dropna().mean()) if frame["ABOVE_CASH_252"].notna().any() else np.nan,
        "percentage_families_above_global": float(frame["RS_252"].dropna().gt(0).mean()) if frame["RS_252"].notna().any() else np.nan,
        "top7_membership_retention": retention,
        "global_drawdown_from_trailing_252_high": global_drawdown,
    }


def build_monthly_regime_ledger(
    data: a4d.A4DData,
    volatility_quantile: float = 0.75,
    leadership_quantile: float = 0.50,
) -> pd.DataFrame:
    """Build the causal A4F month-end risk/leadership regime ledger.

    All thresholds are expanding and strictly prior-only.  Global volatility
    has at least 36 prior month-end observations.  Leadership thresholds have
    at least 24 prior valid diagnostics and may use the preregistered, accepted
    pre-2017 M2 diagnostic seed beginning 2014-01-31.
    """

    if pd.Timestamp(data.base.research.calendar.max()) > AUTHORITATIVE_CUTOFF:
        raise AssertionError("Post-cutoff calendar row detected")
    monthly_dates = _monthly_schedule(data)
    feature = a4e.monthly_features(data)
    feature = feature.loc[feature["date"].isin(monthly_dates)].copy()

    global_return_126 = data.base.research.matrices.cumulative_returns[126][GLOBAL_FAMILY].reindex(monthly_dates)
    global_return_252 = data.base.research.matrices.cumulative_returns[252][GLOBAL_FAMILY].reindex(monthly_dates)
    cash = data.base.cash_index.reindex(data.base.research.calendar).astype(float)
    cash_return_126 = (cash / cash.shift(126) - 1.0).reindex(monthly_dates)
    cash_return_252 = (cash / cash.shift(252) - 1.0).reindex(monthly_dates)
    global_vol_63 = _daily_trailing_volatility(data).reindex(monthly_dates)

    rows: list[dict[str, Any]] = []
    prior_frame: pd.DataFrame | None = None
    prior_selected: set[str] | None = None
    for date in monthly_dates:
        source = feature.loc[feature["date"].eq(date) & feature["M2_INTERMEDIATE_5H"].notna()].copy()
        source = source.sort_values(
            ["M2_INTERMEDIATE_5H", "economic_exposure_family_id"],
            ascending=[False, True],
        ).reset_index(drop=True)
        # Average ranks implement exact Spearman tie semantics; family ID is
        # used only for deterministic TOP7 ordering when tied.
        source["m2_rank"] = source["M2_INTERMEDIATE_5H"].rank(method="average", ascending=False)
        selected = source.head(min(ROTATION_BREADTH, len(source))) if len(source) >= 3 else source.iloc[0:0]
        selected_families = set(selected["economic_exposure_family_id"].astype(str))
        leadership_spread = (
            float(selected["M2_INTERMEDIATE_5H"].mean() - source["M2_INTERMEDIATE_5H"].median())
            if len(source) >= 3
            else np.nan
        )
        persistence, common_count = _same_month_rank_persistence(source, prior_frame)
        support = int(selected["ABOVE_CASH_252"].eq(1.0).sum()) if len(source) >= 3 else 0
        secondary = _secondary_diagnostics(data, pd.Timestamp(date), source, selected_families, prior_selected)
        position = int(data.base.research.calendar.get_loc(pd.Timestamp(date)))
        next_session = (
            pd.Timestamp(data.base.research.calendar[position + 1])
            if position + 1 < len(data.base.research.calendar)
            else pd.NaT
        )
        rows.append(
            {
                "decision_date": pd.Timestamp(date),
                "scheduled_next_xlon_session": next_session,
                "data_cutoff": AUTHORITATIVE_CUTOFF,
                "eligible_family_count": int(len(source)),
                "eligible_families_json": json.dumps(sorted(source["economic_exposure_family_id"].astype(str))),
                "top7_family_count": int(len(selected)),
                "top7_families_rank_order": ";".join(selected["economic_exposure_family_id"].astype(str)),
                "top7_scores": ";".join(f"{float(value):.12g}" for value in selected["M2_INTERMEDIATE_5H"]),
                "global_return_126": float(global_return_126.loc[date]) if pd.notna(global_return_126.loc[date]) else np.nan,
                "cash_return_126": float(cash_return_126.loc[date]) if pd.notna(cash_return_126.loc[date]) else np.nan,
                "global_126_excess": float(global_return_126.loc[date] - cash_return_126.loc[date]) if pd.notna(global_return_126.loc[date]) and pd.notna(cash_return_126.loc[date]) else np.nan,
                "global_return_252": float(global_return_252.loc[date]) if pd.notna(global_return_252.loc[date]) else np.nan,
                "cash_return_252": float(cash_return_252.loc[date]) if pd.notna(cash_return_252.loc[date]) else np.nan,
                "global_252_excess": float(global_return_252.loc[date] - cash_return_252.loc[date]) if pd.notna(global_return_252.loc[date]) and pd.notna(cash_return_252.loc[date]) else np.nan,
                "global_vol_63": float(global_vol_63.loc[date]) if pd.notna(global_vol_63.loc[date]) else np.nan,
                "leadership_spread": leadership_spread,
                "rank_persistence": persistence,
                "rank_persistence_common_family_count": common_count,
                "absolute_leadership_support": support,
                **secondary,
            }
        )
        prior_frame = source[["economic_exposure_family_id", "m2_rank"]].copy()
        prior_selected = selected_families

    ledger = pd.DataFrame(rows).sort_values("decision_date").reset_index(drop=True)
    ledger["volatility_threshold"] = prior_only_quantile(ledger["global_vol_63"], volatility_quantile, 36)
    leadership_seed_mask = ledger["decision_date"].ge(M2_DIAGNOSTIC_SEED_START)
    spread_for_threshold = ledger["leadership_spread"].where(leadership_seed_mask)
    persistence_for_threshold = ledger["rank_persistence"].where(leadership_seed_mask)
    ledger["leadership_spread_threshold"] = prior_only_quantile(spread_for_threshold, leadership_quantile, 24)
    ledger["rank_persistence_threshold"] = prior_only_quantile(persistence_for_threshold, leadership_quantile, 24)
    ledger["volatility_prior_observation_count"] = ledger["global_vol_63"].notna().shift(1, fill_value=False).cumsum()
    ledger["spread_prior_observation_count"] = spread_for_threshold.notna().shift(1, fill_value=False).cumsum()
    ledger["persistence_prior_observation_count"] = persistence_for_threshold.notna().shift(1, fill_value=False).cumsum()
    ledger["global_126_adverse"] = ledger["global_126_excess"].le(0) & ledger["global_126_excess"].notna()
    ledger["global_252_adverse"] = ledger["global_252_excess"].le(0) & ledger["global_252_excess"].notna()
    ledger["high_volatility"] = ledger["global_vol_63"].gt(ledger["volatility_threshold"])
    ledger["risk_score"] = [
        risk_score(g126, g252, vol, threshold)
        for g126, g252, vol, threshold in ledger[
            ["global_126_excess", "global_252_excess", "global_vol_63", "volatility_threshold"]
        ].itertuples(index=False, name=None)
    ]
    ledger["spread_high"] = ledger["leadership_spread"].gt(ledger["leadership_spread_threshold"])
    ledger["persistence_high"] = ledger["rank_persistence"].gt(ledger["rank_persistence_threshold"])
    ledger["absolute_support_high"] = ledger["absolute_leadership_support"].ge(5)
    threshold_ready = (
        ledger["eligible_family_count"].ge(3)
        & ledger["leadership_spread_threshold"].notna()
        & ledger["rank_persistence_threshold"].notna()
    )
    votes = ledger[["spread_high", "persistence_high", "absolute_support_high"]].sum(axis=1)
    ledger["leadership_strong"] = threshold_ready & votes.ge(2)
    ledger["leadership_state"] = np.where(ledger["leadership_strong"], "LEADERSHIP_STRONG", "LEADERSHIP_WEAK")
    ledger["threshold_history_status"] = np.select(
        [ledger["eligible_family_count"].lt(3), ledger["leadership_spread_threshold"].isna(), ledger["rank_persistence_threshold"].isna()],
        ["FEWER_THAN_3_M2_VALID_FAMILIES", "SPREAD_THRESHOLD_NOT_READY", "PERSISTENCE_THRESHOLD_NOT_READY"],
        default="PRIOR_ONLY_THRESHOLDS_READY",
    )
    ledger["regime"] = [
        regime_for(None if pd.isna(score) else int(score), bool(strong))
        for score, strong in ledger[["risk_score", "leadership_strong"]].itertuples(index=False, name=None)
    ]
    ledger["volatility_quantile"] = float(volatility_quantile)
    ledger["leadership_quantile"] = float(leadership_quantile)
    ledger["warning"] = WARNING
    if ledger["decision_date"].max() > AUTHORITATIVE_CUTOFF:
        raise AssertionError("A4F ledger exceeds the authoritative cutoff")
    return ledger


# Alias used by the output and correctness-test layers.
build_regime_ledger = build_monthly_regime_ledger


def _rotation_targets(data: a4d.A4DData) -> tuple[dict[pd.Timestamp, dict[str, float]], pd.DataFrame]:
    targets, records = a4e.rotation_targets(data, "M2_BASE", ROTATION_BREADTH, cash1=False)
    targets = {pd.Timestamp(date): target for date, target in targets.items() if pd.Timestamp(date) <= AUTHORITATIVE_CUTOFF}
    records = records.loc[records["review_date"].le(AUTHORITATIVE_CUTOFF)].copy()
    return targets, records


def _blend_map(
    rotation: Mapping[pd.Timestamp, Mapping[str, float]],
    global_weight: float,
    m2_weight: float,
) -> dict[pd.Timestamp, dict[str, float]]:
    if global_weight < 0 or m2_weight < 0 or global_weight + m2_weight > 1.0 + 1e-12:
        raise ValueError("Invalid static allocation")
    result: dict[pd.Timestamp, dict[str, float]] = {}
    for date, m2_target in sorted(rotation.items()):
        target = {str(family): float(weight) * float(m2_weight) for family, weight in m2_target.items()}
        if global_weight > 1e-12:
            target[GLOBAL_FAMILY] = float(global_weight)
        result[pd.Timestamp(date)] = {family: weight for family, weight in target.items() if weight > 1e-12}
    return result


def static_target_maps(data: a4d.A4DData) -> dict[str, dict[pd.Timestamp, dict[str, float]]]:
    """Return every preregistered static frontier map on the common window."""

    rotation, _ = _rotation_targets(data)
    specifications = {
        "GLOBAL_25_CASH75": (0.25, 0.00),
        "GLOBAL_50_CASH50": (0.50, 0.00),
        "GLOBAL_75_CASH25": (0.75, 0.00),
        "GLOBAL_100": (1.00, 0.00),
        "M2_TOP7_CASH0_25_CASH75": (0.00, 0.25),
        "M2_TOP7_CASH0_50_CASH50": (0.00, 0.50),
        "M2_TOP7_CASH0_75_CASH25": (0.00, 0.75),
        "M2_TOP7_CASH0_100": (0.00, 1.00),
        "GLOBAL_90_M2_10": (0.90, 0.10),
        "GLOBAL_75_M2_25": (0.75, 0.25),
        "GLOBAL_50_M2_50": (0.50, 0.50),
        "GLOBAL_0_M2_100": (0.00, 1.00),
        "GLOBAL_50_M2_25_CASH25": (0.50, 0.25),
        "GLOBAL_75_M2_10_CASH15": (0.75, 0.10),
    }
    return {strategy_id: _blend_map(rotation, global_weight, m2_weight) for strategy_id, (global_weight, m2_weight) in specifications.items()}


def apply_hysteresis(
    desired_risky: float,
    desired_m2_fraction: float,
    leadership_strong: bool,
    state: HysteresisState | None = None,
) -> tuple[float, float, HysteresisState, str]:
    """Apply the frozen asymmetric monthly confirmation rule.

    The first valid pre-common-window observation seeds state without creating
    a trade.  Thereafter defensive moves and M2 removal are immediate.  A risk
    increase requires two consecutive desired allocations at the same or a
    less-defensive level; adding M2 requires two consecutive strong readings.
    """

    state = state or HysteresisState()
    desired_risky = float(desired_risky)
    desired_m2_fraction = float(desired_m2_fraction)
    if not 0.0 <= desired_risky <= 1.0 or not 0.0 <= desired_m2_fraction <= 1.0:
        raise ValueError("Hysteresis inputs must be weights in [0, 1]")
    if not state.initialised:
        state.initialised = True
        state.applied_risky = desired_risky
        state.applied_m2_fraction = desired_m2_fraction
        state.prior_desired_risky = desired_risky
        state.re_risk_streak = 0
        state.strong_streak = 1 if leadership_strong else 0
        return state.applied_risky, state.applied_m2_fraction, state, "STATE_SEEDED_BEFORE_COMMON_WINDOW"

    reasons: list[str] = []
    state.strong_streak = state.strong_streak + 1 if leadership_strong else 0

    if desired_risky < state.applied_risky - 1e-12:
        state.applied_risky = desired_risky
        state.re_risk_streak = 0
        reasons.append("DEFENSIVE_CHANGE_IMMEDIATE")
    elif desired_risky > state.applied_risky + 1e-12:
        qualifies = (
            state.prior_desired_risky is not None
            and state.prior_desired_risky > state.applied_risky + 1e-12
            and desired_risky >= state.prior_desired_risky - 1e-12
        )
        state.re_risk_streak = state.re_risk_streak + 1 if qualifies else 1
        if state.re_risk_streak >= 2:
            state.applied_risky = desired_risky
            state.re_risk_streak = 0
            reasons.append("RISK_INCREASE_AFTER_TWO_CONFIRMATIONS")
        else:
            reasons.append("RISK_INCREASE_PENDING_CONFIRMATION")
    else:
        state.re_risk_streak = 0

    if desired_m2_fraction < state.applied_m2_fraction - 1e-12:
        state.applied_m2_fraction = desired_m2_fraction
        reasons.append("M2_REMOVAL_IMMEDIATE")
    elif desired_m2_fraction > state.applied_m2_fraction + 1e-12:
        if leadership_strong and state.strong_streak >= 2:
            state.applied_m2_fraction = desired_m2_fraction
            reasons.append("M2_ADDED_AFTER_TWO_CONFIRMATIONS")
        else:
            reasons.append("M2_ADDITION_PENDING_CONFIRMATION")

    state.prior_desired_risky = desired_risky
    return state.applied_risky, state.applied_m2_fraction, state, ";".join(reasons) or "NO_TARGET_CHANGE"


def apply_asymmetric_hysteresis(
    previous_target: Mapping[str, float],
    proposed_target: Mapping[str, float],
    risk_confirmation_count: int,
    leadership_strong_streak: int,
) -> dict[str, float]:
    """Pure allocation-level form of the frozen asymmetric rule.

    This helper is intentionally side-effect free.  The stateful production
    implementation remains :func:`apply_hysteresis`.
    """

    def value(target: Mapping[str, float], *names: str) -> float:
        return float(next((target[name] for name in names if name in target), 0.0))

    prior_global = value(previous_target, "global", "global_weight", "swda")
    prior_m2 = value(previous_target, "m2", "m2_weight", "rotation")
    prior_cash = value(previous_target, "cash", "cash_weight")
    new_global = value(proposed_target, "global", "global_weight", "swda")
    new_m2 = value(proposed_target, "m2", "m2_weight", "rotation")
    new_cash = value(proposed_target, "cash", "cash_weight")
    prior_risky = prior_global + prior_m2
    new_risky = new_global + new_m2

    if new_risky < prior_risky - 1e-12:
        applied_risky = new_risky
    elif new_risky > prior_risky + 1e-12 and int(risk_confirmation_count) < 2:
        applied_risky = prior_risky
    else:
        applied_risky = new_risky

    if new_m2 < prior_m2 - 1e-12:
        applied_m2 = new_m2
    elif new_m2 > prior_m2 + 1e-12 and int(leadership_strong_streak) < 2:
        applied_m2 = prior_m2
    else:
        applied_m2 = new_m2
    applied_m2 = min(applied_m2, applied_risky)
    proposed_global_share = new_global / new_risky if new_risky > 0 else 1.0
    applied_global = max(0.0, applied_risky - applied_m2)
    if applied_m2 == 0.0 and applied_risky > 0.0:
        applied_global = applied_risky
    elif applied_m2 > 0.0 and new_risky > 0.0 and applied_m2 == prior_m2 and applied_risky != new_risky:
        applied_global = max(0.0, applied_risky - applied_m2)
    result = {"global": applied_global, "m2": applied_m2, "cash": 1.0 - applied_risky}
    if any(weight < -1e-12 for weight in result.values()) or abs(sum(result.values()) - 1.0) > 1e-10:
        raise AssertionError("Invalid pure hysteresis allocation")
    return result


def policy_target_map(
    data: a4d.A4DData,
    ledger: pd.DataFrame,
    policy_id: str,
    switch_mode: str,
) -> tuple[dict[pd.Timestamp, dict[str, float]], pd.DataFrame]:
    """Construct a policy's constituent targets and auditable decision rows."""

    if policy_id not in POLICY_MAP:
        raise ValueError(policy_id)
    if switch_mode not in SWITCH_MODES:
        raise ValueError(switch_mode)
    rotation, _ = _rotation_targets(data)
    state = HysteresisState()
    targets: dict[pd.Timestamp, dict[str, float]] = {}
    records: list[dict[str, Any]] = []
    previous_target: dict[str, float] = {}
    for row in ledger.sort_values("decision_date").itertuples(index=False):
        date = pd.Timestamp(row.decision_date)
        if pd.isna(row.risk_score):
            continue
        immediate = policy_target(int(row.risk_score), bool(row.leadership_strong), policy_id)
        desired_risky = float(immediate["risky_weight"])
        desired_fraction = float(immediate["m2_fraction_of_risky"])
        if switch_mode == "SWITCH_ASYMMETRIC_HYSTERESIS":
            applied_risky, applied_fraction, state, reason = apply_hysteresis(
                desired_risky, desired_fraction, bool(row.leadership_strong), state
            )
        else:
            state.initialised = True
            state.applied_risky = desired_risky
            state.applied_m2_fraction = desired_fraction
            state.prior_desired_risky = desired_risky
            state.strong_streak = state.strong_streak + 1 if bool(row.leadership_strong) else 0
            applied_risky, applied_fraction, reason = desired_risky, desired_fraction, "IMMEDIATE_MONTHLY"

        # Pre-common rows seed expanding state but do not create an executable
        # rotation portfolio.  The M2 target itself remains the frozen TOP7.
        if date not in rotation:
            continue
        m2_weight = applied_risky * applied_fraction
        global_weight = applied_risky - m2_weight
        target = {
            str(family): float(weight) * m2_weight
            for family, weight in rotation[date].items()
            if float(weight) * m2_weight > 1e-12
        }
        if global_weight > 1e-12:
            target[GLOBAL_FAMILY] = global_weight
        if sum(target.values()) > 1.0 + 1e-12:
            raise AssertionError("Policy target exceeds 100%")
        targets[date] = target
        records.append(
            {
                "review_date": date,
                "policy_id": policy_id,
                "switch_mode": switch_mode,
                "risk_score": int(row.risk_score),
                "leadership_state": row.leadership_state,
                "regime": row.regime,
                "desired_risky_weight": desired_risky,
                "desired_m2_fraction_of_risky": desired_fraction,
                "desired_m2_weight": desired_risky * desired_fraction,
                "desired_global_weight": desired_risky * (1.0 - desired_fraction),
                "desired_cash_weight": 1.0 - desired_risky,
                "applied_risky_weight": applied_risky,
                "applied_global_weight": global_weight,
                "applied_m2_weight": m2_weight,
                "applied_cash_weight": 1.0 - applied_risky,
                "risk_confirmation_count": int(state.re_risk_streak),
                "leadership_confirmation_count": int(state.strong_streak),
                "previous_target_weights_json": json.dumps(previous_target, sort_keys=True),
                "target_weights_json": json.dumps(target, sort_keys=True),
                "switch_decision": reason,
                "warning": WARNING,
            }
        )
        previous_target = dict(target)
    return targets, pd.DataFrame(records)


def _records_for_targets(strategy_id: str, targets: Mapping[pd.Timestamp, Mapping[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "review_date": pd.Timestamp(date),
                "strategy_id": strategy_id,
                "target_weights_json": json.dumps(dict(target), sort_keys=True),
                "target_risky_weight": float(sum(target.values())),
                "target_cash_weight": float(1.0 - sum(target.values())),
                "warning": WARNING,
            }
            for date, target in sorted(targets.items())
        ]
    )


def simulate_target_map(
    data: a4d.A4DData,
    targets: Mapping[pd.Timestamp, Mapping[str, float]] | tuple[Mapping[pd.Timestamp, Mapping[str, float]], pd.DataFrame],
    strategy_id: str,
    cost_scenario: str = "BASE",
    force_every_review: bool = True,
) -> a4e.StrategyResult:
    """Run a target map through the canonical next-session A4E accounting engine."""

    if isinstance(targets, tuple):
        target_map, records = targets
    else:
        target_map = targets
        records = _records_for_targets(strategy_id, target_map)
    scenario_alias = {"BASELINE": "BASE", "DOUBLED": "DOUBLE", "DOUBLE": "DOUBLE", "BASE": "BASE"}
    if cost_scenario not in scenario_alias:
        raise ValueError(cost_scenario)
    clean = {
        pd.Timestamp(date): {str(family): float(weight) for family, weight in target.items() if float(weight) > 1e-12}
        for date, target in target_map.items()
        if pd.Timestamp(date) <= AUTHORITATIVE_CUTOFF
    }
    if any(sum(target.values()) > 1.0 + 1e-12 for target in clean.values()):
        raise AssertionError("No-leverage constraint violated")
    result = a4e.simulate_targets(
        data,
        strategy_id,
        clean,
        records.copy(),
        cost_scenario=scenario_alias[cost_scenario],
        force_every_review=bool(force_every_review),
    )
    if len(result.simulation.curve) and pd.Timestamp(result.simulation.curve["date"].max()) > AUTHORITATIVE_CUTOFF:
        raise AssertionError("Simulation exceeded the A4F cutoff")
    if len(result.simulation.trades) and bool(result.simulation.trades["same_close_execution"].fillna(False).any()):
        raise AssertionError("Same-close execution detected")
    return result


def metrics(
    simulation: a4e.StrategyResult | a4b.A4BSimulation,
    start: pd.Timestamp | str | None = None,
    end: pd.Timestamp | str | None = None,
) -> dict[str, Any]:
    """Return the accepted enhanced metric pack over an explicit common window."""

    sim = simulation.simulation if isinstance(simulation, a4e.StrategyResult) else simulation
    if sim.curve.empty:
        return {}
    first = max(pd.Timestamp(start or COMMON_CAUSAL_CHAIN_START), pd.Timestamp(sim.curve["date"].min()))
    last = min(pd.Timestamp(end or AUTHORITATIVE_CUTOFF), pd.Timestamp(sim.curve["date"].max()), AUTHORITATIVE_CUTOFF)
    return a4e.metric_pack(sim, first, last)


def _as_sim(value: a4e.StrategyResult | a4b.A4BSimulation) -> a4b.A4BSimulation:
    return value.simulation if isinstance(value, a4e.StrategyResult) else value


def monthly_interval_returns(
    ledger: pd.DataFrame,
    simulation: a4e.StrategyResult | a4b.A4BSimulation,
) -> pd.DataFrame:
    """Link each month-end state to the following executable holding interval."""

    sim = _as_sim(simulation)
    value = sim.curve.set_index("date")["portfolio_value"].astype(float).sort_index()
    calendar = pd.DatetimeIndex(sorted(value.index.unique()))
    rows: list[dict[str, Any]] = []
    decisions = ledger.loc[ledger["decision_date"].ge(COMMON_CAUSAL_CHAIN_START)].sort_values("decision_date")
    for index, row in enumerate(decisions.itertuples(index=False)):
        date = pd.Timestamp(row.decision_date)
        start_candidates = calendar[calendar > date]
        if len(start_candidates) == 0:
            continue
        start_date = pd.Timestamp(start_candidates[0])
        if index + 1 < len(decisions):
            next_decision = pd.Timestamp(decisions.iloc[index + 1]["decision_date"])
            end_candidates = calendar[calendar > next_decision]
            end_date = pd.Timestamp(end_candidates[0]) if len(end_candidates) else pd.Timestamp(calendar[-1])
        else:
            end_date = pd.Timestamp(calendar[-1])
        if start_date not in value.index or end_date not in value.index or end_date <= start_date:
            continue
        rows.append(
            {
                "decision_date": date,
                "interval_start": start_date,
                "interval_end": end_date,
                "regime": row.regime,
                "risk_score": row.risk_score,
                "leadership_state": row.leadership_state,
                "interval_return": float(value.loc[end_date] / value.loc[start_date] - 1.0),
            }
        )
    return pd.DataFrame(rows)


def _episode_ids(regimes: pd.Series) -> pd.Series:
    return regimes.ne(regimes.shift()).cumsum()


def regime_summary(
    ledger: pd.DataFrame,
    static_simulations: Mapping[str, a4e.StrategyResult | a4b.A4BSimulation],
    *,
    global_id: str = "GLOBAL_100",
    pool_id: str | None = None,
) -> pd.DataFrame:
    """Summarise static-strategy performance conditional on each causal regime."""

    intervals = {strategy_id: monthly_interval_returns(ledger, sim) for strategy_id, sim in static_simulations.items()}
    rows: list[dict[str, Any]] = []
    for strategy_id, frame in intervals.items():
        if frame.empty:
            continue
        global_frame = intervals.get(global_id, pd.DataFrame())
        pool_frame = intervals.get(pool_id, pd.DataFrame()) if pool_id else pd.DataFrame()
        joined = frame.rename(columns={"interval_return": "strategy_return"})
        if not global_frame.empty:
            joined = joined.merge(
                global_frame[["decision_date", "interval_return"]].rename(columns={"interval_return": "global_return"}),
                on="decision_date",
                how="left",
            )
        if not pool_frame.empty:
            joined = joined.merge(
                pool_frame[["decision_date", "interval_return"]].rename(columns={"interval_return": "pool_return"}),
                on="decision_date",
                how="left",
            )
        for horizon in (1, 3, 6):
            values = joined["strategy_return"].astype(float).to_numpy()
            forward = np.full(len(values), np.nan, dtype=float)
            for position in range(len(values)):
                sample = values[position : position + horizon]
                if len(sample) == horizon and np.isfinite(sample).all():
                    forward[position] = float(np.prod(1.0 + sample) - 1.0)
            joined[f"subsequent_{horizon}m_return"] = forward
        joined["episode_id"] = _episode_ids(joined["regime"])
        for regime, group in joined.groupby("regime", sort=True):
            returns = group["strategy_return"].dropna().astype(float)
            episode_returns: list[float] = []
            episode_mdds: list[float] = []
            for _, episode in group.groupby("episode_id", sort=True):
                series = episode["strategy_return"].dropna().astype(float)
                if series.empty:
                    continue
                path = (1.0 + series).cumprod()
                episode_returns.append(float(path.iloc[-1] - 1.0))
                episode_mdds.append(float((path / path.cummax() - 1.0).min()))
            count = len(returns)
            annualised = float(np.prod(1.0 + returns) ** (12.0 / count) - 1.0) if count else np.nan
            volatility = float(returns.std(ddof=1) * math.sqrt(12.0)) if count > 1 else np.nan
            rows.append(
                {
                    "strategy_id": strategy_id,
                    "regime": regime,
                    "month_count": count,
                    "episode_count": len(episode_returns),
                    "average_episode_duration_months": count / len(episode_returns) if episode_returns else np.nan,
                    "mean_monthly_return": float(returns.mean()) if count else np.nan,
                    "median_monthly_return": float(returns.median()) if count else np.nan,
                    "annualised_return": annualised,
                    "realised_volatility": volatility,
                    "sharpe_zero_hurdle": float(returns.mean() / returns.std(ddof=1) * math.sqrt(12.0)) if count > 1 and returns.std(ddof=1) > 0 else np.nan,
                    "sortino_zero_hurdle": float(returns.mean() / returns.loc[returns.lt(0)].std(ddof=1) * math.sqrt(12.0)) if returns.lt(0).sum() > 1 and returns.loc[returns.lt(0)].std(ddof=1) > 0 else np.nan,
                    "positive_month_frequency": float(returns.gt(0).mean()) if count else np.nan,
                    "worst_month": float(returns.min()) if count else np.nan,
                    "average_episode_return": float(np.mean(episode_returns)) if episode_returns else np.nan,
                    "worst_episode_return": float(np.min(episode_returns)) if episode_returns else np.nan,
                    "worst_episode_maximum_drawdown": float(np.min(episode_mdds)) if episode_mdds else np.nan,
                    "mean_subsequent_1m_return": float(group["subsequent_1m_return"].mean()),
                    "mean_subsequent_3m_return": float(group["subsequent_3m_return"].mean()),
                    "mean_subsequent_6m_return": float(group["subsequent_6m_return"].mean()),
                    "mean_excess_vs_global": float((group["strategy_return"] - group["global_return"]).mean()) if "global_return" in group else np.nan,
                    "mean_excess_vs_pool": float((group["strategy_return"] - group["pool_return"]).mean()) if "pool_return" in group else np.nan,
                    "claim_status": "REGIME_SAMPLE_SUFFICIENT" if count >= 18 and len(episode_returns) >= 3 else "INSUFFICIENT_REGIME_SAMPLE",
                    "warning": WARNING,
                }
            )
    return pd.DataFrame(rows)


def transition_summary(
    ledger: pd.DataFrame,
    simulations: Mapping[str, a4e.StrategyResult | a4b.A4BSimulation] | None = None,
    *,
    m2_id: str = "M2_TOP7_CASH0_100",
    global_id: str = "GLOBAL_100",
    cash_id: str = "ACTUAL_GBP_CASH",
) -> pd.DataFrame:
    """Return an aggregate transition matrix with optional forward outcomes."""

    ordered = ledger.loc[ledger["regime"].ne("REGIME_UNAVAILABLE")].sort_values("decision_date").reset_index(drop=True)
    ordered["prior_regime"] = ordered["regime"].shift()
    ordered["run_id"] = _episode_ids(ordered["regime"])
    ordered["position_in_run"] = ordered.groupby("run_id").cumcount() + 1
    returns = {key: monthly_interval_returns(ledger, value).set_index("decision_date")["interval_return"] for key, value in (simulations or {}).items()}
    events: list[dict[str, Any]] = []
    for index, row in ordered.iterrows():
        if index == 0 or row["regime"] == row["prior_regime"]:
            continue
        prior_run = int(ordered.iloc[index - 1]["position_in_run"])
        event: dict[str, Any] = {
            "decision_date": pd.Timestamp(row["decision_date"]),
            "from_regime": row["prior_regime"],
            "to_regime": row["regime"],
            "prior_state_duration_months": prior_run,
            "reversal_within_1_month": bool(index + 1 < len(ordered) and ordered.iloc[index + 1]["regime"] == row["prior_regime"]),
            "reversal_within_3_months": bool((ordered.iloc[index + 1 : index + 4]["regime"] == row["prior_regime"]).any()),
        }
        for strategy_id, series in returns.items():
            forward = series.reindex(ordered.iloc[index : index + 6]["decision_date"]).dropna().astype(float)
            event[f"{strategy_id}_return_1m"] = float(forward.iloc[0]) if len(forward) >= 1 else np.nan
            event[f"{strategy_id}_return_3m"] = float(np.prod(1.0 + forward.iloc[:3]) - 1.0) if len(forward) >= 3 else np.nan
            event[f"{strategy_id}_return_6m"] = float(np.prod(1.0 + forward.iloc[:6]) - 1.0) if len(forward) >= 6 else np.nan
        if m2_id in returns and global_id in returns:
            event["m2_minus_global_return_1m"] = event.get(f"{m2_id}_return_1m", np.nan) - event.get(f"{global_id}_return_1m", np.nan)
            event["m2_minus_global_return_3m"] = event.get(f"{m2_id}_return_3m", np.nan) - event.get(f"{global_id}_return_3m", np.nan)
            event["m2_minus_global_return_6m"] = event.get(f"{m2_id}_return_6m", np.nan) - event.get(f"{global_id}_return_6m", np.nan)
        if global_id in returns and cash_id in returns:
            event["risky_minus_cash_return_1m"] = event.get(f"{global_id}_return_1m", np.nan) - event.get(f"{cash_id}_return_1m", np.nan)
        events.append(event)
    detail = pd.DataFrame(events)
    if detail.empty:
        return detail
    numeric = [column for column in detail.columns if column not in {"decision_date", "from_regime", "to_regime"}]
    aggregations: dict[str, tuple[str, str]] = {
        "transition_count": ("decision_date", "count"),
        "average_prior_state_duration_months": ("prior_state_duration_months", "mean"),
        "reversals_within_1_month": ("reversal_within_1_month", "sum"),
        "reversals_within_3_months": ("reversal_within_3_months", "sum"),
    }
    for column in numeric:
        if column in {"prior_state_duration_months", "reversal_within_1_month", "reversal_within_3_months"}:
            continue
        aggregations[f"average_{column}"] = (column, "mean")
    summary = detail.groupby(["from_regime", "to_regime"], sort=True).agg(**aggregations).reset_index()
    summary["warning"] = WARNING
    return summary


def target_allocation_summary(
    data: a4d.A4DData,
    targets: Mapping[pd.Timestamp, Mapping[str, float]],
) -> dict[str, float]:
    """Return time-average global, M2, risky and cash target weights."""

    rotation_members = set(data.members)
    rows = []
    for target in targets.values():
        global_weight = float(target.get(GLOBAL_FAMILY, 0.0))
        m2_weight = float(sum(weight for family, weight in target.items() if family in rotation_members))
        risky = global_weight + m2_weight
        rows.append((global_weight, m2_weight, risky, 1.0 - risky))
    if not rows:
        return {key: np.nan for key in ["global_weight", "m2_weight", "risky_weight", "cash_weight"]}
    averages = np.asarray(rows, dtype=float).mean(axis=0)
    return dict(zip(["global_weight", "m2_weight", "risky_weight", "cash_weight"], map(float, averages)))


def matched_average_exposure_control(
    data: a4d.A4DData,
    dynamic_targets: Mapping[pd.Timestamp, Mapping[str, float]],
) -> dict[pd.Timestamp, dict[str, float]]:
    """Static SWDA/cash target map with the same mean risky target allocation."""

    averages = target_allocation_summary(data, dynamic_targets)
    return _blend_map(_rotation_targets(data)[0], averages["risky_weight"], 0.0)


def matched_m2_exposure_control(
    data: a4d.A4DData,
    dynamic_targets: Mapping[pd.Timestamp, Mapping[str, float]],
) -> dict[pd.Timestamp, dict[str, float]]:
    """Static SWDA/M2/cash map with matching mean global and M2 targets."""

    averages = target_allocation_summary(data, dynamic_targets)
    return _blend_map(_rotation_targets(data)[0], averages["global_weight"], averages["m2_weight"])


def closest_static_control(
    candidate_metrics: Mapping[str, float],
    static_metrics: Mapping[str, Mapping[str, float]],
    field: str,
) -> str:
    """Identify the static candidate nearest a realised-volatility or MDD field."""

    target = float(candidate_metrics[field])
    valid = {
        strategy_id: values
        for strategy_id, values in static_metrics.items()
        if field in values and pd.notna(values[field])
    }
    if not valid:
        raise ValueError(f"No static metric values for {field}")
    return min(valid, key=lambda strategy_id: (abs(float(valid[strategy_id][field]) - target), strategy_id))


def immutable_hashes(paths: Iterable[Path]) -> dict[str, str]:
    """Return SHA-256 hashes for manifest and cutoff-audit callers."""

    import hashlib

    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
