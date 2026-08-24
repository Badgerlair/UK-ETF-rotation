"""Causal portfolio primitives for UKACTIVE-A4D.

This module reuses the corrected A2R2 endpoint chain and the accepted
INDUSTRY_PLUS_THEME economic-family universe.  It adds only the preregistered
A4D signal, breadth, cadence and cash-state transformations.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import ukactive_a3r2_portfolio as a3p
import ukactive_a4b_core as a4b
from ukactive_a3r1_core import percentile_rank


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = PROGRAMME_ROOT / "config" / "UKACTIVE_A4D_POLICY_v1.json"
WARNING = "HISTORICAL UK RETAIL, ISA, ACCOUNT AND BROKER ELIGIBILITY REMAIN PARTLY UNRESOLVED"
HORIZONS = [21, 42, 63, 126, 252]
FORWARD_HORIZONS = [21, 42, 63]
SIGNALS = ["M1_EQUAL_5H", "M2_INTERMEDIATE_5H", "M3_STRUCTURAL_DETERIORATION"]


@dataclass
class A4DData:
    policy: dict[str, Any]
    base: a4b.A4BData
    members: list[str]
    daily_features: pd.DataFrame
    cash_return_252: pd.Series
    global_confirmation: pd.Series


@dataclass
class PlannedResult:
    simulation: a4b.A4BSimulation
    target_records: pd.DataFrame
    skipped_pending: pd.DataFrame


def read_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def schedule_dates(calendar: pd.DatetimeIndex, frequency: str) -> pd.DatetimeIndex:
    if frequency == "DAILY":
        return pd.DatetimeIndex(calendar)
    if frequency in {"WEEKLY", "MONTHLY"}:
        return pd.DatetimeIndex(calendar[a3p.schedule_positions(calendar, frequency)])
    raise ValueError(f"Unknown A4D frequency: {frequency}")


def _flat(matrix: pd.DataFrame, calendar: pd.DatetimeIndex, members: list[str]) -> np.ndarray:
    return matrix.reindex(index=calendar, columns=members).to_numpy(float).reshape(-1)


def _same_segment_sma(level: pd.Series, segment: pd.Series, window: int) -> pd.Series:
    complete = level.notna().rolling(window, min_periods=window).sum().eq(window)
    same = segment.eq(segment.shift(window - 1))
    return level.rolling(window, min_periods=window).mean().where(complete & same)


def build_daily_features(base: a4b.A4BData, policy: dict[str, Any]) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    research = base.research
    calendar = research.calendar
    members = base.members
    size = len(calendar) * len(members)
    frame = pd.DataFrame(
        {
            "date": np.repeat(calendar.to_numpy(), len(members)),
            "economic_exposure_family_id": np.tile(np.asarray(members, dtype=object), len(calendar)),
        }
    )
    if len(frame) != size:
        raise AssertionError("Daily feature identity construction failed")

    rank_matrices: dict[int, pd.DataFrame] = {}
    for horizon in HORIZONS:
        rs = research.matrices.relative_strength[horizon].reindex(index=calendar, columns=members)
        ranks = percentile_rank(rs, minimum_count=3)
        rank_matrices[horizon] = ranks
        frame[f"RS_{horizon}"] = _flat(rs, calendar, members)
        frame[f"RANK_RS_{horizon}"] = _flat(ranks, calendar, members)

    m1 = policy["signals"]["M1_EQUAL_5H"]
    m2 = policy["signals"]["M2_INTERMEDIATE_5H"]
    frame["M1_EQUAL_5H"] = sum(float(m1[f"RS_{h}"]) * frame[f"RANK_RS_{h}"] for h in HORIZONS)
    frame["M2_INTERMEDIATE_5H"] = sum(float(m2[f"RS_{h}"]) * frame[f"RANK_RS_{h}"] for h in HORIZONS)

    m3 = policy["signals"]["M3_STRUCTURAL_DETERIORATION"]
    structural = sum(float(m3["structural"][f"RS_{h}"]) * frame[f"RANK_RS_{h}"] for h in [63, 126, 252])
    fast = sum(float(m3["fast"][f"RS_{h}"]) * frame[f"RANK_RS_{h}"] for h in [21, 42])
    gap = fast - structural
    frame["FAST_LEVEL"] = fast
    frame["STRUCTURAL_LEVEL"] = structural
    frame["FAST_MINUS_STRUCTURAL"] = gap
    raw_m3 = (
        structural
        + float(m3["acceleration_coefficient"]) * gap.clip(lower=0.0)
        - float(m3["deterioration_penalty_coefficient"]) * (-gap).clip(lower=0.0)
    )
    frame["M3_STRUCTURAL_DETERIORATION"] = raw_m3.clip(*[float(v) for v in m3["clip"]])

    for signal in SIGNALS:
        frame[f"{signal}_CHANGE_21"] = frame.groupby("economic_exposure_family_id", sort=False)[signal].diff(21)
        frame[f"{signal}_ORDINAL_RANK"] = frame.groupby("date", sort=False)[signal].rank(method="first", ascending=False)
        valid_count = frame.groupby("date", sort=False)[signal].transform("count")
        frame[f"{signal}_VALID_COUNT"] = valid_count.astype(int)
        frame[f"{signal}_TOP_QUINTILE"] = frame[f"{signal}_ORDINAL_RANK"].le(np.ceil(valid_count * 0.20)) & frame[signal].notna()

    accrued = research.matrices.accrued_valid.reindex(index=calendar, columns=members)
    frame["ACCRUED_VALID_ENDPOINTS"] = _flat(accrued, calendar, members)
    frame["RESEARCH_MATURITY"] = np.select(
        [frame["ACCRUED_VALID_ENDPOINTS"].ge(1260), frame["ACCRUED_VALID_ENDPOINTS"].ge(504)],
        ["MATURE", "DEVELOPING"],
        default="NEW",
    )
    asset_252 = research.matrices.cumulative_returns[252].reindex(index=calendar, columns=members)
    frame["ASSET_RETURN_252"] = _flat(asset_252, calendar, members)

    cash_index = base.cash_index.reindex(calendar).astype(float)
    cash_return_252 = cash_index / cash_index.shift(252) - 1.0
    frame["CASH_RETURN_252"] = np.repeat(cash_return_252.to_numpy(float), len(members))
    above_cash_valid = frame["ASSET_RETURN_252"].notna() & frame["CASH_RETURN_252"].notna()
    frame["ABOVE_CASH_252"] = np.where(
        above_cash_valid,
        frame["ASSET_RETURN_252"].gt(frame["CASH_RETURN_252"]).astype(float),
        np.nan,
    )
    frame["POOL_ABOVE_CASH_BREADTH"] = frame.groupby("date", sort=False)["ABOVE_CASH_252"].transform("mean")

    global_return_252 = research.matrices.cumulative_returns[252]["GLOBAL_DEVELOPED_WORLD"].reindex(calendar)
    global_level = research.wealth["GLOBAL_DEVELOPED_WORLD"].reindex(calendar)
    global_segment = research.segment["GLOBAL_DEVELOPED_WORLD"].reindex(calendar)
    global_sma_200 = _same_segment_sma(global_level, global_segment, 200)
    global_confirmation = (
        global_return_252.notna()
        & cash_return_252.notna()
        & global_sma_200.notna()
        & global_return_252.gt(cash_return_252)
        & global_level.gt(global_sma_200)
    )
    frame["GLOBAL_RETURN_252"] = np.repeat(global_return_252.to_numpy(float), len(members))
    frame["GLOBAL_ABOVE_CASH_252"] = np.repeat(global_return_252.gt(cash_return_252).to_numpy(bool), len(members))
    frame["GLOBAL_ABOVE_SMA_200"] = np.repeat(global_level.gt(global_sma_200).to_numpy(bool), len(members))
    frame["GLOBAL_CONFIRMATION"] = np.repeat(global_confirmation.to_numpy(bool), len(members))

    states = policy["leadership_states"]
    change = frame["M3_STRUCTURAL_DETERIORATION_CHANGE_21"]
    new = (
        frame["FAST_LEVEL"].ge(float(states["new"]["fast_min"]))
        & frame["STRUCTURAL_LEVEL"].ge(float(states["new"]["structural_min"]))
        & frame["FAST_MINUS_STRUCTURAL"].ge(float(states["new"]["fast_minus_structural_min"]))
        & change.ge(float(states["new"]["score_change_21_min"]))
    )
    established = (
        frame["STRUCTURAL_LEVEL"].ge(float(states["established"]["structural_min"]))
        & frame["FAST_LEVEL"].ge(float(states["established"]["fast_min"]))
        & frame["RS_63"].gt(0)
    )
    mature = frame["STRUCTURAL_LEVEL"].ge(float(states["mature_decelerating"]["structural_min"])) & (
        frame["FAST_LEVEL"].lt(float(states["mature_decelerating"]["fast_below"]))
        | frame["FAST_MINUS_STRUCTURAL"].le(float(states["mature_decelerating"]["fast_minus_structural_max"]))
        | change.le(float(states["mature_decelerating"]["score_change_21_max"]))
    )
    failed = (
        frame["STRUCTURAL_LEVEL"].lt(float(states["failed"]["structural_below"]))
        & frame["FAST_LEVEL"].lt(float(states["failed"]["fast_below"]))
    ) | (frame["RS_63"].le(0) & frame["RS_126"].le(0))
    frame["LEADERSHIP_STATE"] = np.select(
        [failed, mature, new, established],
        ["FAILED_LEADERSHIP", "MATURE_DECELERATING", "NEW_LEADERSHIP", "ESTABLISHED_LEADERSHIP"],
        default="TRANSITIONAL",
    )
    frame["WARNING"] = WARNING
    return frame.sort_values(["date", "economic_exposure_family_id"]).reset_index(drop=True), cash_return_252, global_confirmation


def load_data() -> A4DData:
    policy = read_policy()
    base = a4b.load_a4b_data()
    daily, cash_return, global_confirmation = build_daily_features(base, policy)
    return A4DData(policy, base, list(base.members), daily, cash_return, global_confirmation)


def sample_features(data: A4DData, frequency: str) -> pd.DataFrame:
    dates = set(schedule_dates(data.base.research.calendar, frequency))
    return data.daily_features.loc[data.daily_features["date"].isin(dates)].copy()


def _window_mask(dates: pd.Series, window_id: str, policy: dict[str, Any]) -> pd.Series:
    windows = policy["windows"]
    if window_id == "FULL_HISTORY":
        return dates.le(pd.Timestamp(windows["CUTOFF"]))
    if window_id == "PRE_2020":
        return dates.le(pd.Timestamp(windows["PRE_2020_END"]))
    if window_id == "POST_2020":
        return dates.between(pd.Timestamp(windows["POST_2020_START"]), pd.Timestamp(windows["CUTOFF"]))
    if window_id == "LATEST_5Y":
        return dates.between(pd.Timestamp(windows["LATEST_5Y_START"]), pd.Timestamp(windows["CUTOFF"]))
    if window_id == "LATEST_3Y":
        return dates.between(pd.Timestamp(windows["LATEST_3Y_START"]), pd.Timestamp(windows["CUTOFF"]))
    raise ValueError(window_id)


def signal_diagnostics(data: A4DData) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    weekly = sample_features(data, "WEEKLY")
    calendar = data.base.research.calendar
    members = data.members
    forward_long: dict[int, pd.DataFrame] = {}
    for horizon in FORWARD_HORIZONS:
        matrix = data.base.research.matrices.forward_returns[horizon].reindex(index=calendar, columns=members)
        frame = pd.DataFrame(
            {
                "date": np.repeat(calendar.to_numpy(), len(members)),
                "economic_exposure_family_id": np.tile(np.asarray(members, dtype=object), len(calendar)),
                "forward_return": matrix.to_numpy(float).reshape(-1),
            }
        )
        forward_long[horizon] = frame.loc[frame["date"].isin(set(weekly["date"]))]

    rows: list[dict[str, Any]] = []
    date_rows: list[dict[str, Any]] = []
    windows = ["FULL_HISTORY", "PRE_2020", "POST_2020", "LATEST_5Y", "LATEST_3Y"]
    for signal in SIGNALS:
        for horizon in FORWARD_HORIZONS:
            joined = weekly.merge(forward_long[horizon], on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
            local: list[dict[str, Any]] = []
            for date, group in joined.groupby("date", sort=True):
                valid = group.loc[group[signal].notna() & group["forward_return"].notna()].copy()
                if len(valid) < 5:
                    continue
                valid = valid.sort_values([signal, "economic_exposure_family_id"], ascending=[False, True])
                ic = float(spearmanr(valid[signal], valid["forward_return"], nan_policy="omit").statistic)
                top_count = max(1, int(math.ceil(len(valid) * 0.20)))
                top_return = float(valid.head(top_count)["forward_return"].mean())
                pool_return = float(valid["forward_return"].mean())
                rank1 = float(valid.iloc[0]["forward_return"])
                item = {
                    "signal_id": signal,
                    "forward_horizon_sessions": horizon,
                    "date": pd.Timestamp(date),
                    "valid_family_count": len(valid),
                    "ic": ic,
                    "top_quintile_return": top_return,
                    "pool_return": pool_return,
                    "top_quintile_advantage": top_return - pool_return,
                    "rank1_advantage": rank1 - pool_return,
                }
                local.append(item)
                date_rows.append(item)
            local_frame = pd.DataFrame(local)
            for window_id in windows:
                subset = local_frame.loc[_window_mask(local_frame["date"], window_id, data.policy)] if len(local_frame) else local_frame
                rows.append(
                    {
                        "signal_id": signal,
                        "forward_horizon_sessions": horizon,
                        "window_id": window_id,
                        "date_count": len(subset),
                        "mean_ic": subset["ic"].mean() if len(subset) else np.nan,
                        "median_ic": subset["ic"].median() if len(subset) else np.nan,
                        "positive_ic_frequency": subset["ic"].gt(0).mean() if len(subset) else np.nan,
                        "mean_top_quintile_advantage": subset["top_quintile_advantage"].mean() if len(subset) else np.nan,
                        "positive_top_quintile_advantage_frequency": subset["top_quintile_advantage"].gt(0).mean() if len(subset) else np.nan,
                        "mean_rank1_advantage": subset["rank1_advantage"].mean() if len(subset) else np.nan,
                        "warning": WARNING,
                    }
                )

    state_rows: list[dict[str, Any]] = []
    state_source = weekly.merge(forward_long[42], on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    for (window_id, state), group in pd.concat(
        [state_source.loc[_window_mask(state_source["date"], window_id, data.policy)].assign(window_id=window_id) for window_id in windows]
    ).groupby(["window_id", "LEADERSHIP_STATE"], sort=True):
        valid = group["forward_return"].dropna()
        state_rows.append(
            {
                "window_id": window_id,
                "leadership_state": state,
                "observation_count": len(valid),
                "mean_forward_return_42": valid.mean() if len(valid) else np.nan,
                "median_forward_return_42": valid.median() if len(valid) else np.nan,
                "positive_frequency": valid.gt(0).mean() if len(valid) else np.nan,
                "warning": WARNING,
            }
        )

    age_rows: list[dict[str, Any]] = []
    age = weekly.sort_values(["economic_exposure_family_id", "date"]).copy()
    top = age["M3_STRUCTURAL_DETERIORATION_TOP_QUINTILE"].fillna(False)
    block = (~top).groupby(age["economic_exposure_family_id"]).cumsum()
    age["TOP_QUINTILE_AGE"] = top.astype(int).groupby([age["economic_exposure_family_id"], block]).cumsum()
    age["AGE_BUCKET"] = np.select(
        [age["TOP_QUINTILE_AGE"].eq(1), age["TOP_QUINTILE_AGE"].eq(2), age["TOP_QUINTILE_AGE"].between(3, 5), age["TOP_QUINTILE_AGE"].ge(6)],
        ["NEW_ENTRY", "ONE_PRIOR_REVIEW", "SEVERAL_REVIEWS", "LONG_ESTABLISHED"],
        default="NOT_TOP_QUINTILE",
    )
    age = age.merge(forward_long[42], on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    for (window_id, bucket), group in pd.concat(
        [age.loc[_window_mask(age["date"], window_id, data.policy)].assign(window_id=window_id) for window_id in windows]
    ).groupby(["window_id", "AGE_BUCKET"], sort=True):
        valid = group["forward_return"].dropna()
        age_rows.append(
            {
                "window_id": window_id,
                "age_bucket": bucket,
                "observation_count": len(valid),
                "mean_forward_return_42": valid.mean() if len(valid) else np.nan,
                "median_forward_return_42": valid.median() if len(valid) else np.nan,
                "positive_frequency": valid.gt(0).mean() if len(valid) else np.nan,
                "warning": WARNING,
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(date_rows), pd.DataFrame(state_rows), pd.DataFrame(age_rows)


def select_stage_b_signals(diagnostics: pd.DataFrame, policy: dict[str, Any]) -> tuple[list[str], pd.DataFrame]:
    full = diagnostics.loc[diagnostics["window_id"].eq("FULL_HISTORY")]
    gate_rows = []
    for signal in SIGNALS:
        group = full.loc[full["signal_id"].eq(signal)]
        positive_ic = int(group["mean_ic"].gt(0).sum())
        positive_top = int(group["mean_top_quintile_advantage"].gt(0).sum())
        minimum_top = float(group["mean_top_quintile_advantage"].min()) if len(group) else np.nan
        gate_rows.append(
            {
                "signal_id": signal,
                "positive_ic_horizons": positive_ic,
                "positive_top_quintile_horizons": positive_top,
                "minimum_top_quintile_advantage": minimum_top,
                "passes_gate": positive_ic >= int(policy["stage_a_gate"]["minimum_positive_ic_horizons"]) and positive_top >= int(policy["stage_a_gate"]["minimum_positive_top_quintile_horizons"]),
            }
        )
    gates = pd.DataFrame(gate_rows)
    anchor = str(policy["stage_a_gate"]["anchor_signal"])
    choices = gates.loc[gates["signal_id"].ne(anchor) & gates["passes_gate"]].sort_values(
        ["minimum_top_quintile_advantage", "signal_id"], ascending=[False, True]
    )
    selected = [anchor]
    if len(choices) and int(policy["stage_a_gate"]["maximum_carried_signals"]) > 1:
        selected.append(str(choices.iloc[0]["signal_id"]))
    gates["carried_to_stage_b"] = gates["signal_id"].isin(selected)
    gates["warning"] = WARNING
    return selected, gates


def _base_weights(count: int, method: str) -> np.ndarray:
    if count <= 0:
        return np.asarray([], dtype=float)
    if method == "W0_EQUAL":
        return np.repeat(1.0 / count, count)
    if method == "W1_RANK_DECAY":
        raw = 1.0 / np.arange(1, count + 1, dtype=float)
        return raw / raw.sum()
    if method == "W2_FIXED_TOP_HEAVY":
        if count >= 4:
            return np.asarray([0.30, 0.22, 0.16] + [0.32 / (count - 3)] * (count - 3), dtype=float)
        raw = np.asarray([0.30, 0.22, 0.16][:count], dtype=float)
        return raw / raw.sum()
    raise ValueError(method)


def target_weights(
    data: A4DData,
    *,
    signal_id: str,
    breadth: int,
    frequency: str,
    cash_architecture: str = "CASH_0_ALWAYS_INVESTED",
    weighting_method: str = "W0_EQUAL",
    maturity_scope: str = "DYNAMIC_POINT_IN_TIME",
    excluded_families: set[str] | None = None,
) -> tuple[dict[pd.Timestamp, dict[str, float]], pd.DataFrame]:
    features = sample_features(data, frequency)
    exclusions = excluded_families or set()
    targets: dict[pd.Timestamp, dict[str, float]] = {}
    records: list[dict[str, Any]] = []
    cash_policy = data.policy["cash_architectures"]
    chain_start = pd.Timestamp(data.policy["windows"]["COMMON_CAUSAL_CHAIN_START"])
    features = features.loc[features["date"].ge(chain_start)]
    for date, source in features.groupby("date", sort=True):
        frame = source.loc[source[signal_id].notna()].copy()
        if exclusions:
            frame = frame.loc[~frame["economic_exposure_family_id"].isin(exclusions)]
        if maturity_scope == "MATURE_ONLY":
            frame = frame.loc[frame["RESEARCH_MATURITY"].eq("MATURE")]
        elif maturity_scope == "MATURE_PLUS_DEVELOPING":
            frame = frame.loc[frame["RESEARCH_MATURITY"].isin(["MATURE", "DEVELOPING"])]
        elif maturity_scope != "DYNAMIC_POINT_IN_TIME":
            raise ValueError(maturity_scope)
        frame = frame.sort_values([signal_id, "economic_exposure_family_id"], ascending=[False, True]).reset_index(drop=True)
        if len(frame) < 3:
            continue
        selected = frame.head(min(int(breadth), len(frame))).copy()
        selected["selection_rank"] = np.arange(1, len(selected) + 1)
        base_weights = _base_weights(len(selected), weighting_method)
        final = base_weights.copy()
        breadth_value = float(frame["ABOVE_CASH_252"].mean()) if frame["ABOVE_CASH_252"].notna().any() else np.nan
        breadth_multiplier = 1.0 if breadth_value >= float(cash_policy["CASH_2_POOL_BREADTH"]["full_risk_min"]) else (0.5 if breadth_value >= float(cash_policy["CASH_2_POOL_BREADTH"]["half_risk_min"]) else 0.0)
        global_ok = bool(frame["GLOBAL_CONFIRMATION"].iloc[0])
        individual = selected["ABOVE_CASH_252"].eq(1.0).to_numpy(float)
        if cash_architecture == "CASH_0_ALWAYS_INVESTED":
            pass
        elif cash_architecture == "CASH_1_INDIVIDUAL_ABOVE_CASH_252":
            final *= individual
        elif cash_architecture == "CASH_2_POOL_BREADTH":
            final *= breadth_multiplier
        elif cash_architecture == "CASH_3_GLOBAL_CONFIRMATION":
            final *= 1.0 if global_ok else 0.0
        elif cash_architecture == "CASH_4_PARSIMONIOUS_COMBINED":
            final *= individual * breadth_multiplier * (1.0 if global_ok else 0.0)
        else:
            raise ValueError(cash_architecture)
        target = {
            str(family): float(weight)
            for family, weight in zip(selected["economic_exposure_family_id"], final)
            if float(weight) > 1e-12
        }
        targets[pd.Timestamp(date)] = target
        records.append(
            {
                "review_date": pd.Timestamp(date),
                "signal_id": signal_id,
                "breadth": int(breadth),
                "frequency": frequency,
                "cash_architecture": cash_architecture,
                "weighting_method": weighting_method,
                "maturity_scope": maturity_scope,
                "eligible_family_count": int(len(frame)),
                "selected_family_count_before_cash": int(len(selected)),
                "selected_risky_family_count": int(len(target)),
                "selected_families_rank_order": ";".join(selected["economic_exposure_family_id"]),
                "selected_scores": ";".join(f"{value:.12g}" for value in selected[signal_id]),
                "selected_states": ";".join(selected["LEADERSHIP_STATE"]),
                "target_weights_json": json.dumps(target, sort_keys=True),
                "target_risky_weight": float(sum(target.values())),
                "target_cash_weight": float(1.0 - sum(target.values())),
                "pool_above_cash_breadth": breadth_value,
                "breadth_multiplier": breadth_multiplier,
                "global_confirmation": global_ok,
                "warning": WARNING,
            }
        )
    return targets, pd.DataFrame(records)


def _weights_equal(left: dict[str, float], right: dict[str, float], tolerance: float = 1e-12) -> bool:
    keys = set(left) | set(right)
    return all(abs(float(left.get(key, 0.0)) - float(right.get(key, 0.0))) <= tolerance for key in keys)


def plan_targets(data: A4DData, module_id: str, frequency: str, targets: dict[pd.Timestamp, dict[str, float]], records: pd.DataFrame) -> tuple[a4b.PlannedPortfolio, pd.DataFrame]:
    calendar = data.base.research.calendar
    date_position = {pd.Timestamp(date): index for index, date in enumerate(calendar)}
    wealth = data.base.research.wealth
    segment = data.base.research.segment
    cash_index = data.base.cash_index
    current_target: dict[str, float] = {}
    entry_segment: dict[str, Any] = {}
    events: list[dict[str, Any]] = []
    cancelled: list[dict[str, Any]] = []
    pending: dict[str, Any] | None = None
    started = False
    skipped: list[dict[str, Any]] = []
    accepted_targets: dict[pd.Timestamp, dict[str, float]] = {}

    for review_date, requested in sorted(targets.items()):
        review_date = pd.Timestamp(review_date)
        review_position = date_position[review_date]
        if pending is not None and int(pending["execution_position"]) <= review_position:
            old_members = set(current_target)
            current_target = dict(pending["target"])
            for family in old_members - set(current_target):
                entry_segment.pop(family, None)
            for family in set(current_target) - old_members:
                entry_segment[family] = segment.iloc[int(pending["execution_position"])][family]
            pending = None
            started = True
        if pending is not None:
            skipped.append({"review_date": review_date, "reason": "SKIPPED_PENDING_EXECUTION", "pending_execution_date": pending["execution_date"], "warning": WARNING})
            continue
        clean = {str(k): float(v) for k, v in requested.items() if float(v) > 1e-12}
        accepted_targets[review_date] = clean
        if started and _weights_equal(clean, current_target):
            continue
        union = set(current_target) | set(clean)
        execution_position = None
        for lag in range(1, int(data.policy["execution"]["maximum_lag_xlon_sessions"]) + 1):
            candidate = review_position + lag
            if candidate >= len(calendar):
                break
            valid = bool(pd.notna(cash_index.iloc[candidate]))
            for family in union:
                valid &= bool(pd.notna(wealth.iloc[candidate][family]))
                if family in current_target and family in entry_segment:
                    valid &= segment.iloc[candidate][family] == entry_segment[family]
            if valid:
                execution_position = candidate
                break
        if execution_position is None:
            cancelled.append(
                {
                    "module_id": module_id,
                    "review_date": review_date,
                    "execution_date": pd.NaT,
                    "execution_position": np.nan,
                    "execution_lag_xlon_sessions": np.nan,
                    "execution_status": "CANCELLED_NO_COMMON_VALID_ENDPOINT_WITHIN_3_XLON_SESSIONS",
                    "target": clean,
                    "reason": "A4D_TARGET_CHANGE",
                }
            )
            continue
        pending = {
            "module_id": module_id,
            "review_date": review_date,
            "execution_date": pd.Timestamp(calendar[execution_position]),
            "execution_position": int(execution_position),
            "execution_lag_xlon_sessions": int(execution_position - review_position),
            "execution_status": "PLANNED",
            "target": clean,
            "reason": "A4D_TARGET_CHANGE",
        }
        events.append(pending)

    plan = a4b.PlannedPortfolio(
        module_id=module_id,
        management_frequency=frequency,
        targets=accepted_targets,
        events=events,
        cancelled_events=cancelled,
        decisions=records.copy(),
        actions=pd.DataFrame(),
    )
    return plan, pd.DataFrame(skipped)


def simulate_specification(
    data: A4DData,
    *,
    module_id: str,
    signal_id: str,
    breadth: int,
    frequency: str,
    cash_architecture: str = "CASH_0_ALWAYS_INVESTED",
    weighting_method: str = "W0_EQUAL",
    maturity_scope: str = "DYNAMIC_POINT_IN_TIME",
    excluded_families: set[str] | None = None,
    friction_bps: float | None = None,
    fixed_fee_gbp: float | None = None,
) -> PlannedResult:
    targets, records = target_weights(
        data,
        signal_id=signal_id,
        breadth=breadth,
        frequency=frequency,
        cash_architecture=cash_architecture,
        weighting_method=weighting_method,
        maturity_scope=maturity_scope,
        excluded_families=excluded_families,
    )
    plan, skipped = plan_targets(data, module_id, frequency, targets, records)
    simulation = a4b.simulate_planned_portfolio(
        plan,
        data.base,
        friction_bps=friction_bps,
        fixed_fee_gbp=fixed_fee_gbp,
        sleeve_size_gbp=float(data.policy["costs"]["canonical_sleeve_size_gbp"]),
        non_gbp_families=set(),
        fx_rate=float(data.policy["costs"]["non_gbp_fx_rate"]),
    )
    return PlannedResult(simulation, records, skipped)


def pool_benchmark(data: A4DData, frequency: str) -> a4b.A4BSimulation:
    features = sample_features(data, frequency)
    chain_start = pd.Timestamp(data.policy["windows"]["COMMON_CAUSAL_CHAIN_START"])
    features = features.loc[features["date"].ge(chain_start)]
    targets: dict[pd.Timestamp, dict[str, float]] = {}
    for date, group in features.groupby("date", sort=True):
        families = sorted(group.loc[group["M1_EQUAL_5H"].notna(), "economic_exposure_family_id"].unique())
        if len(families) >= 3:
            targets[pd.Timestamp(date)] = {family: 1.0 / len(families) for family in families}
    result = a3p.simulate_equal_weight_benchmark(
        targets,
        calendar=data.base.research.calendar,
        daily_returns=data.base.research.daily_returns,
    )
    curve = result.curve.copy()
    if len(curve):
        curve["gross_return_before_cost"] = curve["portfolio_value"].pct_change(fill_method=None).fillna(0.0)
        curve["net_return"] = curve["gross_return_before_cost"]
        curve["cash_return_contribution"] = 0.0
        curve["cumulative_cash_return_contribution"] = 0.0
        curve["transaction_cost_return"] = 0.0
        curve["cumulative_transaction_cost_value"] = 0.0
        curve["cash_value"] = 0.0
        curve["weights_json"] = "{}"
        curve["family_values_json"] = "{}"
        curve["family_market_pnl_json"] = "{}"
        curve["execution_event"] = False
        curve["data_valid"] = True
    trades = result.trades.copy()
    return a4b.A4BSimulation(f"EQUAL_POOL_{frequency}", curve, trades, result.targets, pd.DataFrame(), pd.DataFrame())


def index_benchmark(data: A4DData, family: str, module_id: str) -> a4b.A4BSimulation:
    level = data.base.research.wealth[family].dropna().astype(float)
    value = level / level.iloc[0]
    curve = pd.DataFrame({"date": value.index, "portfolio_value": value.to_numpy(float)})
    curve["gross_return_before_cost"] = value.pct_change(fill_method=None).fillna(0.0).to_numpy(float)
    curve["net_return"] = curve["gross_return_before_cost"]
    curve["cash_return_contribution"] = 0.0
    curve["cumulative_cash_return_contribution"] = 0.0
    curve["transaction_cost_return"] = 0.0
    curve["cumulative_transaction_cost_value"] = 0.0
    curve["invested_fraction"] = 1.0 if family != "ACTUAL_GBP_CASH" else 0.0
    curve["cash_fraction"] = 0.0 if family != "ACTUAL_GBP_CASH" else 1.0
    curve["cash_value"] = 0.0
    curve["holding_count"] = 1
    curve["concentration_hhi"] = 1.0
    curve["holdings"] = family
    curve["weights_json"] = "{}"
    curve["family_values_json"] = "{}"
    curve["family_market_pnl_json"] = "{}"
    curve["execution_event"] = False
    curve["decision_review_date"] = pd.NaT
    curve["data_valid"] = True
    return a4b.A4BSimulation(module_id, curve, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())


def cash_benchmark(data: A4DData) -> a4b.A4BSimulation:
    level = data.base.cash_index.dropna().astype(float)
    value = level / level.iloc[0]
    curve = pd.DataFrame({"date": value.index, "portfolio_value": value.to_numpy(float)})
    curve["gross_return_before_cost"] = value.pct_change(fill_method=None).fillna(0.0).to_numpy(float)
    curve["net_return"] = curve["gross_return_before_cost"]
    curve["cash_return_contribution"] = curve["net_return"]
    curve["cumulative_cash_return_contribution"] = curve["cash_return_contribution"].cumsum()
    curve["transaction_cost_return"] = 0.0
    curve["cumulative_transaction_cost_value"] = 0.0
    curve["invested_fraction"] = 0.0
    curve["cash_fraction"] = 1.0
    curve["cash_value"] = value.to_numpy(float)
    curve["holding_count"] = 0
    curve["concentration_hhi"] = 0.0
    curve["holdings"] = "ACTUAL_GBP_CASH"
    curve["weights_json"] = "{}"
    curve["family_values_json"] = "{}"
    curve["family_market_pnl_json"] = "{}"
    curve["execution_event"] = False
    curve["decision_review_date"] = pd.NaT
    curve["data_valid"] = True
    return a4b.A4BSimulation("ACTUAL_GBP_CASH", curve, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())


def window_bounds(policy: dict[str, Any]) -> dict[str, tuple[pd.Timestamp | None, pd.Timestamp | None]]:
    w = policy["windows"]
    chain_start = pd.Timestamp(w["COMMON_CAUSAL_CHAIN_START"])
    return {
        "FULL_HISTORY": (chain_start, pd.Timestamp(w["CUTOFF"])),
        "PRE_2020": (chain_start, pd.Timestamp(w["PRE_2020_END"])),
        "POST_2020": (pd.Timestamp(w["POST_2020_START"]), pd.Timestamp(w["CUTOFF"])),
        "LATEST_5Y": (pd.Timestamp(w["LATEST_5Y_START"]), pd.Timestamp(w["CUTOFF"])),
        "LATEST_3Y": (pd.Timestamp(w["LATEST_3Y_START"]), pd.Timestamp(w["CUTOFF"])),
    }


def _common_window(simulations: Iterable[a4b.A4BSimulation], start: pd.Timestamp | None, end: pd.Timestamp | None) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    first = [pd.Timestamp(sim.curve["date"].min()) for sim in simulations if len(sim.curve)]
    last = [pd.Timestamp(sim.curve["date"].max()) for sim in simulations if len(sim.curve)]
    if not first or not last:
        return start, end
    actual_start = max(first + ([pd.Timestamp(start)] if start is not None else []))
    actual_end = min(last + ([pd.Timestamp(end)] if end is not None else []))
    return actual_start, actual_end


def rolling_excess_rows(
    specification_id: str,
    selected: a4b.A4BSimulation,
    comparator: a4b.A4BSimulation,
    comparator_id: str,
    months: int,
) -> list[dict[str, Any]]:
    left = selected.curve.set_index("date")["portfolio_value"].rename("selected")
    right = comparator.curve.set_index("date")["portfolio_value"].rename("comparator")
    joined = pd.concat([left, right], axis=1, join="inner").dropna()
    if joined.empty:
        return []
    month = joined.groupby([joined.index.year, joined.index.month]).last()
    selected_return = month["selected"] / month["selected"].shift(months) - 1.0
    comparator_return = month["comparator"] / month["comparator"].shift(months) - 1.0
    rows = []
    for index in month.index:
        s = selected_return.loc[index]
        c = comparator_return.loc[index]
        if pd.isna(s) or pd.isna(c):
            continue
        rows.append(
            {
                "specification_id": specification_id,
                "comparator_id": comparator_id,
                "rolling_months": months,
                "end_year": int(index[0]),
                "end_month": int(index[1]),
                "selected_return": float(s),
                "comparator_return": float(c),
                "excess_return": float(s - c),
                "warning": WARNING,
            }
        )
    return rows


def evaluate(
    specification_id: str,
    selected: a4b.A4BSimulation,
    global_benchmark: a4b.A4BSimulation,
    pool: a4b.A4BSimulation,
    policy: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    result_rows = []
    rolling_rows: list[dict[str, Any]] = []
    for window_id, (start, end) in window_bounds(policy).items():
        actual_start, actual_end = _common_window([selected, global_benchmark, pool], start, end)
        selected_metrics = a4b.enhanced_performance_metrics(selected, start=actual_start, end=actual_end)
        global_metrics = a4b.enhanced_performance_metrics(global_benchmark, start=actual_start, end=actual_end)
        pool_metrics = a4b.enhanced_performance_metrics(pool, start=actual_start, end=actual_end)
        row = {"specification_id": specification_id, "window_id": window_id, "window_start": actual_start, "window_end": actual_end}
        row.update(selected_metrics)
        row["global_benchmark_cagr"] = global_metrics.get("net_cagr", np.nan)
        row["equal_pool_cagr"] = pool_metrics.get("net_cagr", np.nan)
        row["net_excess_vs_global"] = row.get("net_cagr", np.nan) - row["global_benchmark_cagr"]
        row["net_excess_vs_equal_pool"] = row.get("net_cagr", np.nan) - row["equal_pool_cagr"]
        row["cost_drag_cagr"] = row.get("gross_cagr", np.nan) - row.get("net_cagr", np.nan)
        row["drawdown_efficiency_excess_vs_pool"] = row["net_excess_vs_equal_pool"] / abs(row.get("maximum_drawdown", np.nan)) if row.get("maximum_drawdown", 0) < 0 else np.nan
        row["terminal_wealth_per_100k"] = 100000.0 * (1.0 + row.get("net_cagr", np.nan)) ** row.get("calendar_years", np.nan) if pd.notna(row.get("net_cagr")) else np.nan
        subset = selected.curve.loc[selected.curve["date"].between(actual_start, actual_end)] if actual_start is not None and actual_end is not None else selected.curve
        row["percentage_time_100_cash"] = subset["cash_fraction"].ge(1.0 - 1e-10).mean() if len(subset) else np.nan
        row["percentage_time_partially_invested"] = ((subset["cash_fraction"] > 1e-10) & (subset["cash_fraction"] < 1.0 - 1e-10)).mean() if len(subset) else np.nan
        month = selected.curve.set_index("date")["portfolio_value"].loc[actual_start:actual_end].groupby(lambda value: (value.year, value.month)).last()
        monthly_returns = month.pct_change(fill_method=None).dropna()
        row["worst_calendar_year"] = np.nan
        if len(monthly_returns):
            by_year = (1.0 + monthly_returns).groupby([index[0] for index in monthly_returns.index]).prod() - 1.0
            row["worst_calendar_year"] = float(by_year.min()) if len(by_year) else np.nan
        result_rows.append(row)
    for months in policy["rolling_months"]:
        rolling_rows.extend(rolling_excess_rows(specification_id, selected, global_benchmark, "GLOBAL_DEVELOPED_WORLD", int(months)))
        rolling_rows.extend(rolling_excess_rows(specification_id, selected, pool, "EQUAL_POOL", int(months)))
    return pd.DataFrame(result_rows), pd.DataFrame(rolling_rows)


def capture_delay_sessions(data: A4DData, records: pd.DataFrame, signal_id: str, breadth: int) -> float:
    daily = data.daily_features.loc[data.daily_features[signal_id].notna(), ["date", "economic_exposure_family_id", f"{signal_id}_ORDINAL_RANK"]].copy()
    daily["in_top"] = daily[f"{signal_id}_ORDINAL_RANK"].le(int(breadth))
    daily = daily.sort_values(["economic_exposure_family_id", "date"])
    daily["entry"] = daily["in_top"] & ~daily.groupby("economic_exposure_family_id", sort=False)["in_top"].shift(1).fillna(False)
    calendar_position = pd.Series(np.arange(len(data.base.research.calendar)), index=data.base.research.calendar)
    delays = []
    for row in records.itertuples(index=False):
        for family in str(row.selected_families_rank_order).split(";"):
            history = daily.loc[(daily["economic_exposure_family_id"].eq(family)) & daily["entry"] & daily["date"].le(row.review_date)]
            if history.empty:
                continue
            entry_date = pd.Timestamp(history.iloc[-1]["date"])
            delays.append(float(calendar_position.loc[pd.Timestamp(row.review_date)] - calendar_position.loc[entry_date]))
    return float(np.mean(delays)) if delays else np.nan


def drawdown_response_days(simulation: a4b.A4BSimulation, threshold: float = -0.05) -> float:
    if simulation.curve.empty:
        return np.nan
    value = simulation.curve.set_index("date")["portfolio_value"].astype(float)
    drawdown = value / value.cummax() - 1.0
    onset = drawdown.le(threshold) & ~drawdown.shift(1).fillna(False).astype(bool)
    trades = pd.to_datetime(simulation.trades.loc[simulation.trades.get("execution_status", pd.Series(dtype=str)).eq("EXECUTED"), "execution_date"]).sort_values()
    delays = []
    for date in drawdown.index[onset]:
        later = trades.loc[trades.gt(pd.Timestamp(date))]
        if len(later):
            delays.append((later.iloc[0] - pd.Timestamp(date)).days)
    return float(np.mean(delays)) if delays else np.nan


def contribution_tables(result: PlannedResult) -> tuple[pd.DataFrame, pd.DataFrame]:
    curve = result.simulation.curve
    records = result.target_records.set_index("review_date") if len(result.target_records) else pd.DataFrame()
    family_pnl: dict[str, float] = {}
    rank_pnl: dict[str, float] = {"RANK_1": 0.0, "RANK_2_3": 0.0, "RANK_4_5": 0.0, "RANK_6_10": 0.0}
    current_review = pd.NaT
    for row in curve.itertuples(index=False):
        pnl = json.loads(row.family_market_pnl_json) if isinstance(row.family_market_pnl_json, str) and row.family_market_pnl_json else {}
        if pd.notna(row.decision_review_date):
            current_review = pd.Timestamp(row.decision_review_date)
        review = current_review
        rank_map: dict[str, int] = {}
        if pd.notna(review) and not records.empty and review in records.index:
            selected = str(records.loc[review, "selected_families_rank_order"]).split(";")
            rank_map = {family: index + 1 for index, family in enumerate(selected) if family}
        for family, value in pnl.items():
            family_pnl[family] = family_pnl.get(family, 0.0) + float(value)
            rank = rank_map.get(family)
            if rank == 1:
                rank_pnl["RANK_1"] += float(value)
            elif rank is not None and rank <= 3:
                rank_pnl["RANK_2_3"] += float(value)
            elif rank is not None and rank <= 5:
                rank_pnl["RANK_4_5"] += float(value)
            elif rank is not None and rank <= 10:
                rank_pnl["RANK_6_10"] += float(value)
    family = pd.DataFrame([{"economic_exposure_family_id": key, "gross_market_pnl_return_units": value} for key, value in family_pnl.items()]).sort_values("gross_market_pnl_return_units", ascending=False)
    rank = pd.DataFrame([{"rank_bucket": key, "gross_market_pnl_return_units": value} for key, value in rank_pnl.items()])
    total = family["gross_market_pnl_return_units"].sum() if len(family) else np.nan
    family["share_of_gross_family_market_pnl"] = family["gross_market_pnl_return_units"] / total if total else np.nan
    rank["share_of_gross_family_market_pnl"] = rank["gross_market_pnl_return_units"] / total if total else np.nan
    family["warning"] = WARNING
    rank["warning"] = WARNING
    return family, rank
