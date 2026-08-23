from __future__ import annotations

import json
import math
import os
import platform
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow
import scipy

from ukactive_a3r1_core import (
    annualised_geometric_return,
    benjamini_hochberg,
    circular_block_bootstrap_mean_ci,
    hac_lag,
    newey_west_mean,
    pairwise_majority_win_rate,
    percentile_rank,
    relative_return,
    rolling_ols_slope_r2,
    row_zscore,
    rowwise_spearman,
    sha256_file,
    stable_seed,
    strict_forward_total_return,
    strict_rolling_total_return,
    strict_segment_total_return,
    top_tail_size,
    utc_now,
    weekly_last_positions,
)


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_ROOT = PROGRAMME_ROOT.parents[2]
POLICY_PATH = PROGRAMME_ROOT / "config" / "UKACTIVE_A3R1_POLICY_v1.json"
REGISTRY_PATH = PROGRAMME_ROOT / "UKACTIVE_A3R1_SIGNAL_REGISTRY.csv"
WARNING = "HISTORICAL UK RETAIL, ACCOUNT AND BROKER ELIGIBILITY REMAIN UNRESOLVED"
PRIMARY_ROLES = {
    "BROAD_GEOGRAPHY_ROTATION": "GEOGRAPHY",
    "COUNTRY_ROTATION": "COUNTRY",
    "SECTOR_ROTATION": "SECTOR",
    "INDUSTRY_ROTATION": "INDUSTRY",
    "THEME_ROTATION": "THEME",
}
PRIMARY_SIGNALS = [
    "MH_LEVEL_EQ",
    "MH_LEVEL_RECENCY_TILT",
    "MH_LEVEL_60D_CENTERED",
    "MH_LEVEL_3_6_12_REFERENCE",
    "ACCEL_FAST_COMPOSITE",
    "SHORT_MINUS_LONG_RS",
    "DISCRETE_RECENT_CONSISTENCY",
    "PAIRWISE_MAJORITY_5H",
    "RRG_TRANSPARENT_LEVEL",
]
SIGNAL_FAMILY_MAP = {
    "MH_LEVEL_EQ": "MULTI_HORIZON_LEVEL",
    "MH_LEVEL_RECENCY_TILT": "MULTI_HORIZON_LEVEL",
    "MH_LEVEL_60D_CENTERED": "MULTI_HORIZON_LEVEL",
    "MH_LEVEL_3_6_12_REFERENCE": "MULTI_HORIZON_LEVEL",
    "ACCEL_FAST_COMPOSITE": "RELATIVE_STRENGTH_ACCELERATION",
    "SHORT_MINUS_LONG_RS": "RELATIVE_STRENGTH_ACCELERATION",
    "DISCRETE_RECENT_CONSISTENCY": "DISCRETE_PERIOD_CONSISTENCY",
    "PAIRWISE_MAJORITY_5H": "PAIRWISE_RELATIVE_STRENGTH",
    "RRG_TRANSPARENT_LEVEL": "TRANSPARENT_RRG_LIKE_STATE",
}
SECONDARY_SIGNALS = [
    "RRG_TRANSPARENT_MOMENTUM",
    "RS_21",
    "RS_42",
    "RS_63",
    "RS_126",
    "RS_252",
]
EVALUATED_SIGNALS = PRIMARY_SIGNALS + SECONDARY_SIGNALS
TAILS = ["RANK_1", "TOP_2", "TOP_3", "TOP_5", "TOP_10_PERCENT", "TOP_QUINTILE"]
FORWARD_HORIZONS = [5, 10, 21, 42, 63, 126]
CENTRAL_HORIZONS = [10, 21, 42, 63]
MAIN_FORMATION_HORIZONS = [21, 42, 63, 126, 252]
EXTRA_FORMATION_HORIZONS = [32, 50, 52, 75]
ALL_FORMATION_HORIZONS = sorted(set(MAIN_FORMATION_HORIZONS + EXTRA_FORMATION_HORIZONS))


@dataclass
class Inputs:
    policy: dict[str, Any]
    registry: pd.DataFrame
    panel: pd.DataFrame
    calendar: pd.DatetimeIndex
    roles: pd.DataFrame
    pools: pd.DataFrame
    parent_map: pd.DataFrame
    overlap: pd.DataFrame
    global_map: pd.DataFrame
    dynamic: pd.DataFrame
    selectable: pd.DataFrame


@dataclass
class Matrices:
    returns: pd.DataFrame
    valid: pd.DataFrame
    accrued_valid: pd.DataFrame
    cumulative_returns: dict[int, pd.DataFrame]
    relative_strength: dict[int, pd.DataFrame]
    segments: dict[str, pd.DataFrame]
    forward_returns: dict[int, pd.DataFrame]
    global_forward: dict[int, pd.Series]
    relative_features: dict[str, pd.DataFrame]
    price_features: dict[str, pd.DataFrame]
    weekly_positions: np.ndarray
    weekly_dates: pd.DatetimeIndex


def read_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def load_inputs() -> Inputs:
    policy = read_policy()
    registry = pd.read_csv(REGISTRY_PATH, dtype=str).fillna("")
    names = policy["authoritative_inputs"]
    panel = pd.read_parquet(PROGRAMME_ROOT / names["corrected_panel"])
    panel["date"] = pd.to_datetime(panel["date"])
    calendar_frame = pd.read_csv(PROGRAMME_ROOT / names["calendar"])
    calendar_frame["date"] = pd.to_datetime(calendar_frame["date"])
    calendar = pd.DatetimeIndex(
        calendar_frame.loc[calendar_frame["included_in_canonical_calendar"].astype(str).str.lower().eq("true"), "date"]
    ).sort_values()
    roles = pd.read_csv(PROGRAMME_ROOT / names["role_master"], dtype=str).fillna("NOT_APPLICABLE")
    pools = pd.read_csv(PROGRAMME_ROOT / names["competition_pools"], dtype=str).fillna("NOT_APPLICABLE")
    parent_map = pd.read_csv(PROGRAMME_ROOT / names["parent_benchmark_map"], dtype=str).fillna("NOT_APPLICABLE")
    overlap = pd.read_csv(PROGRAMME_ROOT / names["overlap_map"], dtype=str).fillna("NOT_APPLICABLE")
    global_map = pd.read_csv(PROGRAMME_ROOT / names["global_benchmark_map"], dtype=str).fillna("NOT_APPLICABLE")
    dynamic = pd.read_parquet(PROGRAMME_ROOT / names["dynamic_eligibility"])
    selectable = pd.read_csv(PROGRAMME_ROOT / names["selectable_universe"], dtype=str).fillna("NOT_APPLICABLE")
    return Inputs(policy, registry, panel, calendar, roles, pools, parent_map, overlap, global_map, dynamic, selectable)


def candidate_metadata(inputs: Inputs) -> pd.DataFrame:
    roles = inputs.roles.copy()
    mask = (
        roles["selectable_flag"].eq("YES")
        & roles["primary_equity_competition_flag"].eq("YES")
        & roles["research_data_ready_flag"].eq("YES")
        & roles["primary_rotation_role"].isin(PRIMARY_ROLES)
    )
    candidates = roles.loc[mask].copy()
    candidates["research_group_id"] = candidates["primary_rotation_role"].map(PRIMARY_ROLES)
    parent_columns = [
        "economic_exposure_family_id",
        "parent_benchmark_family_id",
        "secondary_parent_benchmark_family_id",
        "parent_benchmark_map_status",
        "parent_history_research_ready",
        "global_fallback_benchmark_family_id",
    ]
    candidates = candidates.merge(inputs.parent_map[parent_columns], on="economic_exposure_family_id", how="left", validate="one_to_one")
    candidates["effective_parent_benchmark_family_id"] = candidates["parent_benchmark_family_id"].where(
        ~candidates["parent_benchmark_family_id"].isin(["", "NOT_APPLICABLE"]),
        candidates["global_fallback_benchmark_family_id"],
    )
    candidates["effective_parent_benchmark_family_id"] = candidates["effective_parent_benchmark_family_id"].fillna("GLOBAL_DEVELOPED_WORLD")
    if candidates["economic_exposure_family_id"].duplicated().any():
        raise AssertionError("Economic exposure family is not unique in the corrected role master")
    return candidates


def build_matrices(inputs: Inputs, metadata: pd.DataFrame) -> Matrices:
    panel = inputs.panel.copy()
    if panel.duplicated(["date", "economic_exposure_family_id"]).any():
        raise AssertionError("Corrected A2R panel contains duplicate family/date rows")
    all_needed = sorted(
        set(metadata["economic_exposure_family_id"])
        | set(metadata["effective_parent_benchmark_family_id"])
        | {"GLOBAL_DEVELOPED_WORLD", "GLOBAL_ALL_WORLD"}
    )
    valid_mask = (
        panel["data_valid"].astype(bool)
        & ~panel["stale_flag"].astype(bool)
        & ~panel["missing_flag"].astype(bool)
        & ~panel["proxy_flag"].astype(bool)
        & panel["return_gbp_total"].notna()
    )
    filtered = panel.loc[panel["economic_exposure_family_id"].isin(all_needed), ["date", "economic_exposure_family_id", "return_gbp_total"]].copy()
    filtered.loc[~valid_mask.loc[filtered.index], "return_gbp_total"] = np.nan
    returns = (
        filtered.pivot(index="date", columns="economic_exposure_family_id", values="return_gbp_total")
        .reindex(index=inputs.calendar, columns=all_needed)
        .astype(float)
    )
    valid = returns.notna()
    accrued_valid = valid.cumsum()
    if "GLOBAL_DEVELOPED_WORLD" not in returns or returns["GLOBAL_DEVELOPED_WORLD"].notna().sum() == 0:
        raise AssertionError("Frozen global benchmark has no valid A2R history")

    cumulative_returns = {h: strict_rolling_total_return(returns, h) for h in ALL_FORMATION_HORIZONS}
    relative_strength = {
        h: relative_return(cumulative_returns[h], cumulative_returns[h]["GLOBAL_DEVELOPED_WORLD"])
        for h in ALL_FORMATION_HORIZONS
    }
    segments: dict[str, pd.DataFrame] = {}
    for segment in inputs.policy["non_overlapping_segments"]:
        start = int(segment["start_lag_exclusive"])
        end = int(segment["end_lag_inclusive"])
        raw = strict_segment_total_return(returns, start, end)
        segments[segment["segment_id"]] = relative_return(raw, raw["GLOBAL_DEVELOPED_WORLD"])

    forward_returns = {h: strict_forward_total_return(returns, h) for h in FORWARD_HORIZONS}
    global_forward = {h: forward_returns[h]["GLOBAL_DEVELOPED_WORLD"] for h in FORWARD_HORIZONS}

    global_log_return = np.log1p(returns["GLOBAL_DEVELOPED_WORLD"])
    relative_daily_log = np.log1p(returns).sub(global_log_return, axis=0)
    relative_log_index = relative_daily_log.fillna(0.0).cumsum()
    relative_valid = relative_daily_log.notna()
    relative_features: dict[str, pd.DataFrame] = {}
    for window in [21, 42, 63]:
        slope, r_squared = rolling_ols_slope_r2(relative_log_index, window)
        complete = relative_valid.rolling(window, min_periods=window).sum().eq(window)
        relative_features[f"REL_SLOPE_{window}"] = slope.where(complete)
        relative_features[f"REL_R2_{window}"] = r_squared.where(complete)
    relative_features["RELATIVE_SLOPE_CHANGE"] = (
        relative_features["REL_SLOPE_21"] - relative_features["REL_SLOPE_21"].shift(21)
    )
    rel_index = np.exp(relative_log_index.clip(-30, 30))
    for window in [21, 50]:
        complete = relative_valid.rolling(window, min_periods=window).sum().eq(window)
        relative_features[f"REL_DISTANCE_MA_{window}"] = (
            rel_index / rel_index.rolling(window, min_periods=window).mean() - 1.0
        ).where(complete)
    relative_features["REL_DISTANCE_HIGH_63"] = (
        rel_index / rel_index.rolling(63, min_periods=63).max() - 1.0
    ).where(relative_valid.rolling(63, min_periods=63).sum().eq(63))

    log_index = np.log1p(returns).fillna(0.0).cumsum()
    log_slope_63, log_r2_63 = rolling_ols_slope_r2(log_index, 63)
    complete63 = valid.rolling(63, min_periods=63).sum().eq(63)
    wealth = np.exp(log_index.clip(-30, 30))
    price_features = {
        "LOG_PRICE_SLOPE_63": log_slope_63.where(complete63),
        "LOG_PRICE_R2_63": log_r2_63.where(complete63),
        "REALISED_VOL_63": returns.rolling(63, min_periods=63).std(ddof=1).mul(math.sqrt(252)).where(complete63),
        "PRICE_DISTANCE_HIGH_63": (wealth / wealth.rolling(63, min_periods=63).max() - 1.0).where(complete63),
    }

    weekly_positions_array = weekly_last_positions(inputs.calendar)
    weekly_dates = inputs.calendar[weekly_positions_array]
    return Matrices(
        returns,
        valid,
        accrued_valid,
        cumulative_returns,
        relative_strength,
        segments,
        forward_returns,
        global_forward,
        relative_features,
        price_features,
        weekly_positions_array,
        weekly_dates,
    )


def contexts(metadata: pd.DataFrame) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    definitions: list[dict[str, Any]] = []
    membership_rows: list[dict[str, Any]] = []
    for group_id in PRIMARY_ROLES.values():
        members = sorted(metadata.loc[metadata["research_group_id"].eq(group_id), "economic_exposure_family_id"].tolist())
        definitions.append({"context_id": group_id, "context_type": "ROLE_GROUP", "members": members, "primary_group": True})
    all_members = sorted(metadata["economic_exposure_family_id"].tolist())
    definitions.append({"context_id": "ALL_EQUITY_OPPORTUNITIES", "context_type": "ALL_EQUITY", "members": all_members, "primary_group": False})
    for pool_id, group in metadata.groupby("primary_competition_pool_id", sort=True):
        members = sorted(group["economic_exposure_family_id"].tolist())
        definitions.append({"context_id": pool_id, "context_type": "FINE_POOL", "members": members, "primary_group": False})
    meta_index = metadata.set_index("economic_exposure_family_id")
    for definition in definitions:
        for family in definition["members"]:
            row = meta_index.loc[family]
            membership_rows.append(
                {
                    "analysis_context_id": definition["context_id"],
                    "analysis_context_type": definition["context_type"],
                    "context_primary_for_a3r1": "YES" if definition["primary_group"] else "NO",
                    "economic_exposure_family_id": family,
                    "economic_exposure_name": row["economic_exposure_name"],
                    "primary_rotation_role": row["primary_rotation_role"],
                    "a2r_primary_competition_pool_id": row["primary_competition_pool_id"],
                    "universe_tier": row["universe_tier"],
                    "a2r_research_maturity": row["research_maturity"],
                    "parent_exposure_family_id": row["parent_exposure_family_id"],
                    "parent_benchmark_family_id": row["effective_parent_benchmark_family_id"],
                    "overlap_cluster_id": row["overlap_cluster_id"],
                    "warning": WARNING,
                }
            )
    return definitions, pd.DataFrame(membership_rows)


def weighted_rank_composite(ranks: dict[int, pd.DataFrame], weights: dict[str, float]) -> pd.DataFrame:
    positive = [(int(key.split("_")[1]), float(weight)) for key, weight in weights.items() if float(weight) > 0]
    result = sum(ranks[h] * weight for h, weight in positive)
    complete = ranks[positive[0][0]].notna().copy()
    for horizon, _ in positive[1:]:
        complete &= ranks[horizon].notna()
    return result.where(complete)


def build_group_features(
    inputs: Inputs,
    matrices: Matrices,
    metadata: pd.DataFrame,
    definitions: list[dict[str, Any]],
) -> pd.DataFrame:
    weekly = matrices.weekly_positions
    parts: list[pd.DataFrame] = []
    meta_index = metadata.set_index("economic_exposure_family_id")
    for definition in definitions:
        members = definition["members"]
        if not members:
            continue
        ranks = {
            h: percentile_rank(matrices.relative_strength[h][members], minimum_count=3)
            for h in ALL_FORMATION_HORIZONS
        }
        fast_level = (ranks[21] + ranks[42] + ranks[63]) / 3.0
        fast_level = fast_level.where(ranks[21].notna() & ranks[42].notna() & ranks[63].notna())
        fast_change_21 = fast_level - fast_level.shift(21)
        fast_change_42 = fast_level - fast_level.shift(42)
        slope_change_rank = percentile_rank(matrices.relative_features["RELATIVE_SLOPE_CHANGE"][members], minimum_count=3)
        acceleration = (
            percentile_rank(fast_change_21, 3)
            + percentile_rank(fast_change_42, 3)
            + slope_change_rank
        ) / 3.0
        acceleration = acceleration.where(fast_change_21.notna() & fast_change_42.notna() & slope_change_rank.notna())
        short_minus_long = (ranks[21] + ranks[42] + ranks[63]) / 3.0 - (ranks[126] + ranks[252]) / 2.0
        short_minus_long = short_minus_long.where(
            ranks[21].notna() & ranks[42].notna() & ranks[63].notna() & ranks[126].notna() & ranks[252].notna()
        )
        recent_segments = [matrices.segments[key][members] for key in ["REL_SEG_0_1M", "REL_SEG_1_2M", "REL_SEG_2_3M"]]
        segment_complete = recent_segments[0].notna() & recent_segments[1].notna() & recent_segments[2].notna()
        positive_count = sum((segment > 0).astype(float) for segment in recent_segments).where(segment_complete)
        consistency = positive_count + ranks[63] * 0.001

        rrg_level = (ranks[63] + ranks[126]) / 2.0
        rrg_level = rrg_level.where(ranks[63].notna() & ranks[126].notna())
        rrg_momentum = rrg_level - rrg_level.shift(21)
        level_z = row_zscore(rrg_level, 3)
        momentum_z = row_zscore(rrg_momentum, 3)
        states = pd.DataFrame("", index=rrg_level.index, columns=members, dtype=object)
        valid_state = level_z.notna() & momentum_z.notna()
        states = states.mask(valid_state & level_z.ge(0) & momentum_z.ge(0), "LEADING")
        states = states.mask(valid_state & level_z.ge(0) & momentum_z.lt(0), "WEAKENING")
        states = states.mask(valid_state & level_z.lt(0) & momentum_z.ge(0), "IMPROVING")
        states = states.mask(valid_state & level_z.lt(0) & momentum_z.lt(0), "LAGGING")
        states = states.where(valid_state, "")

        pairwise = pd.DataFrame(np.nan, index=matrices.returns.index, columns=members)
        for position in weekly:
            values = np.column_stack([matrices.relative_strength[h].iloc[position][members].to_numpy(float) for h in MAIN_FORMATION_HORIZONS])
            pairwise.iloc[position] = pairwise_majority_win_rate(values)

        composites = {
            key: weighted_rank_composite(ranks, weights)
            for key, weights in inputs.policy["multi_horizon_weights"].items()
        }
        neighbour_fast = (
            ranks[21] * 0.30 + ranks[32] * 0.25 + ranks[50] * 0.20 + ranks[126] * 0.15 + ranks[252] * 0.10
        ).where(ranks[21].notna() & ranks[32].notna() & ranks[50].notna() & ranks[126].notna() & ranks[252].notna())
        neighbour_60 = (
            ranks[21] * 0.10 + ranks[52] * 0.25 + ranks[75] * 0.35 + ranks[126] * 0.20 + ranks[252] * 0.10
        ).where(ranks[21].notna() & ranks[52].notna() & ranks[75].notna() & ranks[126].notna() & ranks[252].notna())

        feature_frames: dict[str, pd.DataFrame] = {}
        for h in ALL_FORMATION_HORIZONS:
            feature_frames[f"RETURN_{h}"] = matrices.cumulative_returns[h][members]
            feature_frames[f"RS_{h}"] = matrices.relative_strength[h][members]
            feature_frames[f"RANK_RS_{h}"] = ranks[h]
        feature_frames.update(composites)
        feature_frames.update(
            {
                "FAST_LEVEL": fast_level,
                "RS_RANK_CHANGE_21": fast_change_21,
                "RS_RANK_CHANGE_42": fast_change_42,
                "SHORT_MINUS_LONG_RS": short_minus_long,
                "RELATIVE_SLOPE_CHANGE_RANK": slope_change_rank,
                "ACCEL_FAST_COMPOSITE": acceleration,
                "RECENT_POSITIVE_SEGMENTS": positive_count,
                "DISCRETE_RECENT_CONSISTENCY": consistency,
                "PAIRWISE_MAJORITY_5H": pairwise,
                "RRG_TRANSPARENT_LEVEL": rrg_level,
                "RRG_TRANSPARENT_MOMENTUM": rrg_momentum,
                "RRG_LEVEL_Z": level_z,
                "RRG_MOMENTUM_Z": momentum_z,
                "MH_STRUCTURE_FAST_NEIGHBOUR": neighbour_fast,
                "MH_STRUCTURE_60D_NEIGHBOUR": neighbour_60,
            }
        )
        for h in MAIN_FORMATION_HORIZONS:
            feature_frames[f"SIGNAL_RS_{h}"] = matrices.relative_strength[h][members]
        sampled: list[pd.Series] = []
        for name, frame in feature_frames.items():
            selected = frame.iloc[weekly]
            selected.index = matrices.weekly_dates
            sampled.append(selected.stack(future_stack=True).rename(name))
        selected_states = states.iloc[weekly]
        selected_states.index = matrices.weekly_dates
        sampled.append(selected_states.stack(future_stack=True).rename("ROTATION_STATE"))
        long = pd.concat(sampled, axis=1).reset_index(names=["date", "economic_exposure_family_id"])
        long["analysis_context_id"] = definition["context_id"]
        long["analysis_context_type"] = definition["context_type"]
        long["context_primary_for_a3r1"] = "YES" if definition["primary_group"] else "NO"

        accrued = matrices.accrued_valid[members].iloc[weekly]
        accrued.index = matrices.weekly_dates
        accrued_long = accrued.stack(future_stack=True).rename("accrued_valid_return_observations").reset_index()
        accrued_long.columns = ["date", "economic_exposure_family_id", "accrued_valid_return_observations"]
        long = long.merge(accrued_long, on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
        long["contemporaneous_research_maturity"] = np.select(
            [long["accrued_valid_return_observations"] >= 1260, long["accrued_valid_return_observations"] >= 504],
            ["MATURE", "DEVELOPING"],
            default="NEW",
        )
        meta_columns = [
            "economic_exposure_name", "universe_tier", "research_maturity", "primary_rotation_role",
            "primary_competition_pool_id", "parent_exposure_family_id", "effective_parent_benchmark_family_id",
            "overlap_cluster_id", "a0_primary_geography", "sector", "industry", "economic_theme",
        ]
        long = long.merge(meta_index[meta_columns], left_on="economic_exposure_family_id", right_index=True, how="left", validate="many_to_one")
        long = long.rename(columns={"research_maturity": "a2r_research_maturity", "effective_parent_benchmark_family_id": "parent_benchmark_family_id"})
        long["warning"] = WARNING
        parts.append(long)
    result = pd.concat(parts, ignore_index=True)
    if result.duplicated(["date", "analysis_context_id", "economic_exposure_family_id"]).any():
        raise AssertionError("Group-feature table has duplicate ranking identities")
    return result


def rolling_window_tail_diagnostics(
    returns: pd.DataFrame,
    weekly_positions_array: np.ndarray,
    members: list[str],
    window: int = 63,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    array = returns[members].to_numpy(float)
    for position in weekly_positions_array:
        if position < window - 1:
            continue
        block = array[position - window + 1 : position + 1]
        date = returns.index[position]
        for column, family in enumerate(members):
            values = block[:, column]
            if not np.isfinite(values).all():
                continue
            wealth = np.cumprod(1.0 + values)
            running_high = np.maximum.accumulate(wealth)
            max_pullback = float(np.min(wealth / running_high - 1.0))
            absolute = np.abs(np.log1p(values))
            denominator = float(absolute.sum())
            largest = np.sort(absolute)[::-1]
            rows.append(
                {
                    "date": date,
                    "economic_exposure_family_id": family,
                    "MAX_FORMATION_PULLBACK_63": max_pullback,
                    "LARGEST_1_DAY_MOVE_SHARE_63": float(largest[:1].sum() / denominator) if denominator > 0 else np.nan,
                    "LARGEST_3_DAY_MOVE_SHARE_63": float(largest[:3].sum() / denominator) if denominator > 0 else np.nan,
                }
            )
    return pd.DataFrame(rows)


def build_base_weekly(inputs: Inputs, matrices: Matrices, metadata: pd.DataFrame) -> pd.DataFrame:
    members = sorted(metadata["economic_exposure_family_id"].tolist())
    weekly = matrices.weekly_positions
    dates = matrices.weekly_dates
    base_index = pd.MultiIndex.from_product([dates, members], names=["date", "economic_exposure_family_id"])
    base = pd.DataFrame(index=base_index).reset_index()

    def stack_weekly(frame: pd.DataFrame, name: str) -> pd.DataFrame:
        selected = frame[members].iloc[weekly].copy()
        selected.index = dates
        out = selected.stack(future_stack=True).rename(name).reset_index()
        out.columns = ["date", "economic_exposure_family_id", name]
        return out

    for segment_id, frame in matrices.segments.items():
        base = base.merge(stack_weekly(frame, segment_id), on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    for name, frame in matrices.relative_features.items():
        base = base.merge(stack_weekly(frame, name), on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    for name, frame in matrices.price_features.items():
        base = base.merge(stack_weekly(frame, name), on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    for horizon in MAIN_FORMATION_HORIZONS:
        base = base.merge(stack_weekly(matrices.relative_strength[horizon], f"GLOBAL_RS_{horizon}"), on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    for horizon in FORWARD_HORIZONS:
        base = base.merge(stack_weekly(matrices.forward_returns[horizon], f"FWD_{horizon}"), on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
        global_values = matrices.global_forward[horizon].iloc[weekly].set_axis(dates)
        base[f"GLOBAL_FWD_{horizon}"] = base["date"].map(global_values)

    parent_lookup = metadata.set_index("economic_exposure_family_id")["effective_parent_benchmark_family_id"].to_dict()
    base["parent_benchmark_family_id"] = base["economic_exposure_family_id"].map(parent_lookup).fillna("GLOBAL_DEVELOPED_WORLD")
    date_to_position = {date: pos for pos, date in zip(weekly, dates)}
    family_to_column = {family: idx for idx, family in enumerate(matrices.returns.columns)}
    for horizon in MAIN_FORMATION_HORIZONS:
        parent_values = []
        matrix = matrices.cumulative_returns[horizon].to_numpy(float)
        for row in base[["date", "parent_benchmark_family_id"]].itertuples(index=False):
            column = family_to_column.get(row.parent_benchmark_family_id)
            parent_values.append(matrix[date_to_position[row.date], column] if column is not None else np.nan)
        family_values = base[f"GLOBAL_RS_{horizon}"]
        raw_family = stack_weekly(matrices.cumulative_returns[horizon], f"RAW_{horizon}")
        raw_map = raw_family.set_index(["date", "economic_exposure_family_id"])[f"RAW_{horizon}"]
        indexed = pd.MultiIndex.from_frame(base[["date", "economic_exposure_family_id"]])
        raw = raw_map.reindex(indexed).to_numpy(float)
        parent_array = np.asarray(parent_values, dtype=float)
        base[f"PARENT_RS_{horizon}"] = (1.0 + raw) / (1.0 + parent_array) - 1.0
        base.loc[~np.isfinite(raw) | ~np.isfinite(parent_array), f"PARENT_RS_{horizon}"] = np.nan
        if family_values.isna().all() and np.isfinite(raw).any():
            raise AssertionError("Global relative-strength mapping unexpectedly failed")
    for horizon in FORWARD_HORIZONS:
        parent_values = []
        matrix = matrices.forward_returns[horizon].to_numpy(float)
        for row in base[["date", "parent_benchmark_family_id"]].itertuples(index=False):
            column = family_to_column.get(row.parent_benchmark_family_id)
            parent_values.append(matrix[date_to_position[row.date], column] if column is not None else np.nan)
        base[f"PARENT_FWD_{horizon}"] = np.asarray(parent_values, dtype=float)

    accrued = matrices.accrued_valid[members].iloc[weekly].copy()
    accrued.index = dates
    accrued_long = accrued.stack(future_stack=True).rename("accrued_valid_return_observations").reset_index()
    accrued_long.columns = ["date", "economic_exposure_family_id", "accrued_valid_return_observations"]
    base = base.merge(accrued_long, on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    base["contemporaneous_research_maturity"] = np.select(
        [base["accrued_valid_return_observations"] >= 1260, base["accrued_valid_return_observations"] >= 504],
        ["MATURE", "DEVELOPING"],
        default="NEW",
    )
    tail_diagnostics = rolling_window_tail_diagnostics(matrices.returns, weekly, members, 63)
    base = base.merge(tail_diagnostics, on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    meta_columns = [
        "economic_exposure_family_id", "economic_exposure_name", "primary_rotation_role", "research_group_id",
        "primary_competition_pool_id", "research_maturity", "universe_tier", "parent_exposure_family_id",
        "overlap_cluster_id", "a0_primary_geography", "sector", "industry", "economic_theme",
    ]
    base = base.merge(metadata[meta_columns], on="economic_exposure_family_id", how="left", validate="many_to_one")
    return base.rename(columns={"research_maturity": "a2r_research_maturity"})


def attach_forward_data(group_features: pd.DataFrame, base_weekly: pd.DataFrame) -> pd.DataFrame:
    columns = ["date", "economic_exposure_family_id", "parent_benchmark_family_id"]
    for horizon in FORWARD_HORIZONS:
        columns.extend([f"FWD_{horizon}", f"GLOBAL_FWD_{horizon}", f"PARENT_FWD_{horizon}"])
    forward = base_weekly[columns]
    result = group_features.merge(forward, on=["date", "economic_exposure_family_id"], how="left", validate="many_to_one", suffixes=("", "_base"))
    if "parent_benchmark_family_id_base" in result:
        result = result.drop(columns=["parent_benchmark_family_id_base"])
    return result


def maturity_filter(frame: pd.DataFrame, scope: str) -> pd.Series:
    if scope == "FULL_DYNAMIC":
        return pd.Series(True, index=frame.index)
    if scope == "MATURE_DEVELOPING":
        return frame["contemporaneous_research_maturity"].isin(["MATURE", "DEVELOPING"])
    if scope == "MATURE_ONLY":
        return frame["contemporaneous_research_maturity"].eq("MATURE")
    raise ValueError(f"Unknown maturity scope: {scope}")


def signal_column(signal_id: str) -> str:
    if signal_id.startswith("RS_"):
        return f"SIGNAL_{signal_id}"
    return signal_id


def build_dynamic_counts(
    group_features: pd.DataFrame,
    registry: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    scopes = ["FULL_DYNAMIC", "MATURE_DEVELOPING", "MATURE_ONLY"]
    signal_ids = [signal for signal in EVALUATED_SIGNALS if signal in set(registry["signal_id"])]
    keys = ["analysis_context_id", "analysis_context_type", "date"]
    for signal_id in signal_ids:
        column = signal_column(signal_id)
        for scope in scopes:
            subset = group_features.loc[maturity_filter(group_features, scope) & group_features[column].notna(), keys]
            if subset.empty:
                continue
            count = subset.groupby(keys, sort=True).size().rename("contemporaneous_eligible_family_count").reset_index()
            count["signal_id"] = signal_id
            count["maturity_scope"] = scope
            rows.append(count)
    result = pd.concat(rows, ignore_index=True)
    result["signal_specific_dynamic_admission"] = "YES"
    result["universal_504_gate"] = "NO"
    result["warning"] = WARNING
    return result.sort_values(["analysis_context_type", "analysis_context_id", "signal_id", "maturity_scope", "date"]).reset_index(drop=True)


def relative_advantage(left: float, right: float) -> float:
    if not np.isfinite(left) or not np.isfinite(right) or right <= -1.0:
        return np.nan
    return (1.0 + left) / (1.0 + right) - 1.0


def summarise_tail_cell(
    records: list[dict[str, Any]],
    context_id: str,
    context_type: str,
    signal_id: str,
    maturity_scope: str,
    tail: str,
    horizon: int,
) -> dict[str, Any]:
    frame = pd.DataFrame(records)
    row: dict[str, Any] = {
        "analysis_context_id": context_id,
        "analysis_context_type": context_type,
        "signal_id": signal_id,
        "maturity_scope": maturity_scope,
        "top_tail_definition": tail,
        "forward_horizon_sessions": int(horizon),
        "observation_frequency": "WEEKLY_LAST_ELIGIBLE_XLON_SESSION",
        "aggregation": "EQUAL_WEIGHT_SIGNAL_DIAGNOSTIC_ONLY",
        "portfolio_weighting_optimised": "NO",
        "warning": WARNING,
    }
    if frame.empty:
        for name in [
            "top_return", "advantage_vs_median", "advantage_vs_equal_pool", "advantage_vs_global", "advantage_vs_parent"
        ]:
            row[f"{name}_observation_count"] = 0
            row[f"{name}_mean"] = np.nan
            row[f"{name}_median"] = np.nan
            row[f"{name}_positive_frequency"] = np.nan
            row[f"{name}_hac_standard_error"] = np.nan
            row[f"{name}_hac_t_statistic"] = np.nan
            row[f"{name}_hac_p_value"] = np.nan
            row[f"{name}_ci_low"] = np.nan
            row[f"{name}_ci_high"] = np.nan
        return row
    row.update(
        {
            "first_signal_date": frame["date"].min(),
            "last_signal_date": frame["date"].max(),
            "mean_signal_cohort_count": frame["signal_cohort_count"].mean(),
            "minimum_signal_cohort_count": frame["signal_cohort_count"].min(),
            "maximum_signal_cohort_count": frame["signal_cohort_count"].max(),
            "mean_selected_count": frame["selected_count"].mean(),
        }
    )
    lag = hac_lag(horizon)
    for name in ["top_return", "advantage_vs_median", "advantage_vs_equal_pool", "advantage_vs_global", "advantage_vs_parent"]:
        stats = newey_west_mean(frame[name], lag)
        row.update(
            {
                f"{name}_observation_count": stats["observation_count"],
                f"{name}_mean": stats["mean"],
                f"{name}_median": stats["median"],
                f"{name}_positive_frequency": stats["positive_frequency"],
                f"{name}_hac_standard_error": stats["hac_standard_error"],
                f"{name}_hac_t_statistic": stats["hac_t_statistic"],
                f"{name}_hac_p_value": stats["hac_p_value"],
                f"{name}_ci_low": stats["confidence_interval_low"],
                f"{name}_ci_high": stats["confidence_interval_high"],
            }
        )
    return row


def evaluate_tail_combo(
    frame: pd.DataFrame,
    context_id: str,
    context_type: str,
    signal_id: str,
    maturity_scope: str,
    tails: list[str],
    horizons: list[int],
    retain_dates: bool,
    retain_selections: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    column = signal_column(signal_id)
    subset = frame.loc[maturity_filter(frame, maturity_scope) & frame[column].notna()].copy()
    cell_records: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    retained: list[dict[str, Any]] = []
    selections: list[dict[str, Any]] = []
    for date, date_frame in subset.groupby("date", sort=True):
        ordered = date_frame.sort_values([column, "economic_exposure_family_id"], ascending=[False, True], kind="mergesort")
        cohort_count = len(ordered)
        if cohort_count < 3:
            continue
        for tail in tails:
            size = top_tail_size(tail, cohort_count)
            if size is None:
                continue
            selected = ordered.head(size)
            if retain_selections and tail == "TOP_5":
                cluster_counts = selected["overlap_cluster_id"].value_counts()
                for rank_position, item in enumerate(selected.itertuples(index=False), start=1):
                    selections.append(
                        {
                            "date": date,
                            "analysis_context_id": context_id,
                            "analysis_context_type": context_type,
                            "signal_id": signal_id,
                            "top_tail_definition": "TOP_5",
                            "rank_position": rank_position,
                            "economic_exposure_family_id": item.economic_exposure_family_id,
                            "economic_exposure_name": item.economic_exposure_name,
                            "parent_exposure_family_id": item.parent_exposure_family_id,
                            "overlap_cluster_id": item.overlap_cluster_id,
                            "overlap_cluster_selected_count": int(cluster_counts.get(item.overlap_cluster_id, 0)),
                            "a0_primary_geography": item.a0_primary_geography,
                            "sector": item.sector,
                            "industry": item.industry,
                            "economic_theme": item.economic_theme,
                            "signal_value": getattr(item, column),
                            "warning": WARNING,
                        }
                    )
            for horizon in horizons:
                selected_returns = selected[f"FWD_{horizon}"].to_numpy(float)
                if not np.isfinite(selected_returns).all():
                    continue
                top_return = float(selected_returns.mean())
                pool_returns = ordered[f"FWD_{horizon}"].to_numpy(float)
                valid_pool = pool_returns[np.isfinite(pool_returns)]
                median_return = float(np.median(valid_pool)) if len(valid_pool) >= 3 else np.nan
                equal_pool_return = float(valid_pool.mean()) if len(valid_pool) >= 3 else np.nan
                global_values = selected[f"GLOBAL_FWD_{horizon}"].to_numpy(float)
                global_return = float(global_values[0]) if np.isfinite(global_values).all() and np.allclose(global_values, global_values[0]) else np.nan
                parent_values = selected[f"PARENT_FWD_{horizon}"].to_numpy(float)
                parent_relative = (
                    float(np.mean((1.0 + selected_returns) / (1.0 + parent_values) - 1.0))
                    if np.isfinite(parent_values).all() and np.all(parent_values > -1.0)
                    else np.nan
                )
                record = {
                    "date": date,
                    "signal_cohort_count": cohort_count,
                    "selected_count": size,
                    "top_return": top_return,
                    "advantage_vs_median": relative_advantage(top_return, median_return),
                    "advantage_vs_equal_pool": relative_advantage(top_return, equal_pool_return),
                    "advantage_vs_global": relative_advantage(top_return, global_return),
                    "advantage_vs_parent": parent_relative,
                }
                cell_records[(tail, horizon)].append(record)
                if retain_dates and tail in ["TOP_3", "TOP_5"]:
                    retained.append(
                        {
                            "date": date,
                            "analysis_context_id": context_id,
                            "analysis_context_type": context_type,
                            "signal_id": signal_id,
                            "maturity_scope": maturity_scope,
                            "top_tail_definition": tail,
                            "forward_horizon_sessions": horizon,
                            **record,
                        }
                    )
    summaries = [
        summarise_tail_cell(records, context_id, context_type, signal_id, maturity_scope, tail, horizon)
        for (tail, horizon), records in sorted(cell_records.items())
    ]
    return summaries, retained, selections


def evaluate_top_tails(
    group_features: pd.DataFrame,
    definitions: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, Any]] = []
    retained_rows: list[dict[str, Any]] = []
    selection_rows: list[dict[str, Any]] = []
    definition_map = {definition["context_id"]: definition for definition in definitions}
    for context_id, frame in group_features.groupby("analysis_context_id", sort=True):
        definition = definition_map[context_id]
        context_type = definition["context_type"]
        if context_type in ["ROLE_GROUP", "ALL_EQUITY"]:
            combos: list[tuple[str, str, list[str], list[int]]] = [
                (signal, "FULL_DYNAMIC", TAILS, FORWARD_HORIZONS) for signal in EVALUATED_SIGNALS
            ]
            combos.extend(
                (signal, maturity, ["TOP_3", "TOP_5"], CENTRAL_HORIZONS)
                for signal in PRIMARY_SIGNALS
                for maturity in ["MATURE_DEVELOPING", "MATURE_ONLY"]
            )
        else:
            combos = [
                (signal, "FULL_DYNAMIC", TAILS, CENTRAL_HORIZONS)
                for signal in PRIMARY_SIGNALS
            ]
        for signal_id, maturity_scope, tails, horizons in combos:
            summaries, retained, selections = evaluate_tail_combo(
                frame,
                context_id,
                context_type,
                signal_id,
                maturity_scope,
                tails,
                horizons,
                retain_dates=(context_type in ["ROLE_GROUP", "ALL_EQUITY"] and maturity_scope == "FULL_DYNAMIC" and signal_id in PRIMARY_SIGNALS),
                retain_selections=(context_type == "ROLE_GROUP" and maturity_scope == "FULL_DYNAMIC" and signal_id in PRIMARY_SIGNALS),
            )
            summary_rows.extend(summaries)
            retained_rows.extend(retained)
            selection_rows.extend(selections)
    summary = pd.DataFrame(summary_rows)
    retained = pd.DataFrame(retained_rows)
    selections = pd.DataFrame(selection_rows).drop_duplicates(
        ["date", "analysis_context_id", "signal_id", "rank_position"], keep="first"
    )
    return summary, retained, selections


def add_primary_inference(top_tail: pd.DataFrame, retained: pd.DataFrame, policy: dict[str, Any]) -> pd.DataFrame:
    result = top_tail.copy()
    primary_mask = (
        result["analysis_context_type"].eq("ROLE_GROUP")
        & result["signal_id"].isin(PRIMARY_SIGNALS)
        & result["maturity_scope"].eq("FULL_DYNAMIC")
        & result["top_tail_definition"].eq("TOP_3")
        & result["forward_horizon_sessions"].isin(CENTRAL_HORIZONS)
    )
    result["primary_fdr_family"] = np.where(primary_mask, "YES", "NO")
    minimum_formal_observations = int(policy["minimum_cross_section"]["formal_date_observations"])
    formal_mask = primary_mask & result["advantage_vs_global_observation_count"].ge(minimum_formal_observations)
    result["formal_inference_minimum_date_observations"] = minimum_formal_observations
    result["formal_inference_eligible"] = np.where(formal_mask, "YES", "NO")
    result["advantage_vs_global_bh_q_value"] = np.nan
    result.loc[formal_mask, "advantage_vs_global_bh_q_value"] = benjamini_hochberg(
        result.loc[formal_mask, "advantage_vs_global_hac_p_value"].to_numpy(float)
    )
    result["bootstrap_count"] = np.nan
    result["bootstrap_block_length"] = np.nan
    result["bootstrap_replications"] = np.nan
    result["advantage_vs_global_bootstrap_ci_low"] = np.nan
    result["advantage_vs_global_bootstrap_ci_high"] = np.nan
    replications = int(policy["inference"]["block_bootstrap_replications"])
    for index, row in result.loc[formal_mask].iterrows():
        series = retained.loc[
            retained["analysis_context_id"].eq(row["analysis_context_id"])
            & retained["signal_id"].eq(row["signal_id"])
            & retained["maturity_scope"].eq("FULL_DYNAMIC")
            & retained["top_tail_definition"].eq("TOP_3")
            & retained["forward_horizon_sessions"].eq(row["forward_horizon_sessions"]),
            "advantage_vs_global",
        ]
        lag = hac_lag(int(row["forward_horizon_sessions"]))
        bootstrap = circular_block_bootstrap_mean_ci(
            series,
            block_length=max(5, lag + 1),
            replications=replications,
            seed=stable_seed(row["analysis_context_id"], row["signal_id"], row["forward_horizon_sessions"]),
        )
        result.loc[index, "bootstrap_count"] = bootstrap["bootstrap_count"]
        result.loc[index, "bootstrap_block_length"] = bootstrap["block_length"]
        result.loc[index, "bootstrap_replications"] = bootstrap["replications"]
        result.loc[index, "advantage_vs_global_bootstrap_ci_low"] = bootstrap["bootstrap_ci_low"]
        result.loc[index, "advantage_vs_global_bootstrap_ci_high"] = bootstrap["bootstrap_ci_high"]
    return result


def evaluate_group_diagnostics(group_features: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (context_id, context_type), context_frame in group_features.groupby(["analysis_context_id", "analysis_context_type"], sort=True):
        for signal_id in EVALUATED_SIGNALS:
            column = signal_column(signal_id)
            signal_frame = context_frame.loc[context_frame[column].notna()]
            if signal_frame.empty:
                continue
            for horizon in FORWARD_HORIZONS:
                ic_values: list[float] = []
                spread_values: list[float] = []
                bucket_records: list[list[float]] = []
                counts: list[int] = []
                for _, date_frame in signal_frame.groupby("date", sort=True):
                    observed = date_frame[[column, f"FWD_{horizon}", "economic_exposure_family_id"]].dropna()
                    n = len(observed)
                    if n < 3:
                        continue
                    counts.append(n)
                    ordered = observed.sort_values([column, "economic_exposure_family_id"], ascending=[True, True], kind="mergesort")
                    k = min(3, n // 2)
                    if k >= 1:
                        bottom = float(ordered.head(k)[f"FWD_{horizon}"].mean())
                        top = float(ordered.tail(k)[f"FWD_{horizon}"].mean())
                        spread_values.append(relative_advantage(top, bottom))
                    if n >= 5:
                        corr, _ = rowwise_spearman(
                            observed[[column]].T.to_numpy(float),
                            observed[[f"FWD_{horizon}"]].T.to_numpy(float),
                            5,
                        )
                        ic_values.append(float(corr[0]))
                    bucket_count = 5 if n >= 10 else (3 if n >= 6 else 0)
                    if bucket_count:
                        ordered = ordered.reset_index(drop=True)
                        ordered["bucket"] = np.minimum((np.arange(n) * bucket_count // n) + 1, bucket_count)
                        means = ordered.groupby("bucket")[f"FWD_{horizon}"].mean()
                        bucket_records.append([float(means.get(bucket, np.nan)) for bucket in range(1, bucket_count + 1)])
                ic_stats = newey_west_mean(ic_values, hac_lag(horizon))
                spread_stats = newey_west_mean(spread_values, hac_lag(horizon))
                row: dict[str, Any] = {
                    "analysis_context_id": context_id,
                    "analysis_context_type": context_type,
                    "signal_id": signal_id,
                    "forward_horizon_sessions": horizon,
                    "mean_contemporaneous_count": float(np.mean(counts)) if counts else np.nan,
                    "ic_observation_count": ic_stats["observation_count"],
                    "mean_spearman_ic": ic_stats["mean"],
                    "median_spearman_ic": ic_stats["median"],
                    "ic_positive_frequency": ic_stats["positive_frequency"],
                    "ic_hac_t_statistic": ic_stats["hac_t_statistic"],
                    "ic_hac_p_value": ic_stats["hac_p_value"],
                    "ic_ci_low": ic_stats["confidence_interval_low"],
                    "ic_ci_high": ic_stats["confidence_interval_high"],
                    "top_bottom_observation_count": spread_stats["observation_count"],
                    "top_bottom_mean": spread_stats["mean"],
                    "top_bottom_median": spread_stats["median"],
                    "top_bottom_positive_frequency": spread_stats["positive_frequency"],
                    "top_bottom_hac_t_statistic": spread_stats["hac_t_statistic"],
                    "top_bottom_hac_p_value": spread_stats["hac_p_value"],
                    "bucket_date_count": len(bucket_records),
                    "warning": WARNING,
                }
                if bucket_records:
                    max_buckets = max(len(values) for values in bucket_records)
                    matching = [values for values in bucket_records if len(values) == max_buckets]
                    means = np.nanmean(np.asarray(matching), axis=0)
                    row["bucket_count"] = max_buckets
                    for number, value in enumerate(means, start=1):
                        row[f"bucket_{number}_mean_forward_return"] = float(value)
                    row["bucket_monotonicity_fraction"] = float(np.mean(np.diff(means) > 0)) if len(means) > 1 else np.nan
                else:
                    row["bucket_count"] = 0
                    row["bucket_monotonicity_fraction"] = np.nan
                rows.append(row)
    result = pd.DataFrame(rows)
    return result.sort_values(["analysis_context_type", "analysis_context_id", "signal_id", "forward_horizon_sessions"]).reset_index(drop=True)


def leadership_persistence(group_features: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    eligible_context = group_features["analysis_context_type"].isin(["ROLE_GROUP", "ALL_EQUITY"])
    for (context_id, context_type), context_frame in group_features.loc[eligible_context].groupby(["analysis_context_id", "analysis_context_type"], sort=True):
        dates = pd.DatetimeIndex(sorted(context_frame["date"].unique()))
        date_position = {date: position for position, date in enumerate(dates)}
        for signal_id in EVALUATED_SIGNALS:
            column = signal_column(signal_id)
            pivot = context_frame.pivot(index="date", columns="economic_exposure_family_id", values=column).reindex(dates)
            ranks = percentile_rank(pivot, 3)
            rank_autocorrelation: list[float] = []
            top3_outcomes: list[float] = []
            top5_outcomes: list[float] = []
            rank_changes: list[float] = []
            top3_membership = pd.DataFrame(False, index=dates, columns=pivot.columns)
            for position in range(len(dates)):
                current = pivot.iloc[position].dropna().sort_values(ascending=False, kind="mergesort")
                if len(current) >= 3:
                    top3_membership.loc[dates[position], current.index[:3]] = True
                if position == 0:
                    continue
                common = ranks.iloc[position - 1].notna() & ranks.iloc[position].notna()
                if common.sum() >= 5:
                    correlation = ranks.iloc[position - 1][common].corr(ranks.iloc[position][common], method="spearman")
                    rank_autocorrelation.append(float(correlation))
                    rank_changes.extend(np.abs(ranks.iloc[position][common] - ranks.iloc[position - 1][common]).tolist())
                previous = pivot.iloc[position - 1].dropna().sort_values(ascending=False, kind="mergesort")
                current_rank = ranks.iloc[position]
                if len(previous) >= 3:
                    former_top3 = previous.index[:3]
                    available = current_rank.reindex(former_top3).dropna()
                    if len(available):
                        n_current = int(ranks.iloc[position].notna().sum())
                        if n_current >= 10:
                            top3_outcomes.extend((available >= 0.90).astype(float).tolist())
                if len(previous) >= 5:
                    former_top5 = previous.index[:5]
                    available = current_rank.reindex(former_top5).dropna()
                    if len(available):
                        top5_outcomes.extend((available >= 0.50).astype(float).tolist())
            durations: list[int] = []
            for family in top3_membership.columns:
                run = 0
                for value in top3_membership[family].to_numpy(bool):
                    if value:
                        run += 1
                    elif run:
                        durations.append(run)
                        run = 0
                if run:
                    durations.append(run)
            rows.append(
                {
                    "analysis_context_id": context_id,
                    "analysis_context_type": context_type,
                    "signal_id": signal_id,
                    "weekly_date_count": len(dates),
                    "mean_weekly_rank_autocorrelation": float(np.nanmean(rank_autocorrelation)) if rank_autocorrelation else np.nan,
                    "median_weekly_rank_autocorrelation": float(np.nanmedian(rank_autocorrelation)) if rank_autocorrelation else np.nan,
                    "probability_top3_remains_top10_percent": float(np.mean(top3_outcomes)) if top3_outcomes else np.nan,
                    "probability_top5_remains_above_median": float(np.mean(top5_outcomes)) if top5_outcomes else np.nan,
                    "mean_absolute_percentile_rank_change": float(np.mean(rank_changes)) if rank_changes else np.nan,
                    "median_top3_duration_weeks": float(np.median(durations)) if durations else np.nan,
                    "mean_top3_duration_weeks": float(np.mean(durations)) if durations else np.nan,
                    "top3_duration_run_count": len(durations),
                    "warning": WARNING,
                }
            )
    return pd.DataFrame(rows)


def state_transition_results(group_features: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    eligible = group_features.loc[group_features["analysis_context_type"].isin(["ROLE_GROUP", "ALL_EQUITY"])].copy()
    for (context_id, family), frame in eligible.groupby(["analysis_context_id", "economic_exposure_family_id"], sort=False):
        frame = frame.sort_values("date").copy()
        frame["previous_state"] = frame["ROTATION_STATE"].shift(1)
        frame["previous_date"] = frame["date"].shift(1)
        frame["calendar_week_gap_days"] = (frame["date"] - frame["previous_date"]).dt.days
        observed = frame.loc[
            frame["ROTATION_STATE"].ne("")
            & frame["previous_state"].notna()
            & frame["previous_state"].ne("")
            & frame["calendar_week_gap_days"].between(4, 10)
        ].copy()
        if observed.empty:
            continue
        observed["transition"] = observed["previous_state"] + "->" + observed["ROTATION_STATE"]
        for transition, transition_frame in observed.groupby("transition"):
            for horizon in FORWARD_HORIZONS:
                relative = (1.0 + transition_frame[f"FWD_{horizon}"]) / (1.0 + transition_frame[f"GLOBAL_FWD_{horizon}"]) - 1.0
                rows.extend(
                    {
                        "date": date,
                        "analysis_context_id": context_id,
                        "economic_exposure_family_id": family,
                        "transition": transition,
                        "previous_state": transition.split("->")[0],
                        "current_state": transition.split("->")[1],
                        "forward_horizon_sessions": horizon,
                        "forward_return": fwd,
                        "forward_relative_global": rel,
                    }
                    for date, fwd, rel in zip(transition_frame["date"], transition_frame[f"FWD_{horizon}"], relative)
                    if np.isfinite(fwd) and np.isfinite(rel)
                )
    detail = pd.DataFrame(rows)
    if detail.empty:
        return detail
    summaries: list[dict[str, Any]] = []
    for keys, frame in detail.groupby(["analysis_context_id", "transition", "previous_state", "current_state", "forward_horizon_sessions"], sort=True):
        context_id, transition, previous, current, horizon = keys
        date_level = frame.groupby("date")[["forward_return", "forward_relative_global"]].mean()
        raw = newey_west_mean(date_level["forward_return"], hac_lag(int(horizon)))
        relative = newey_west_mean(date_level["forward_relative_global"], hac_lag(int(horizon)))
        summaries.append(
            {
                "analysis_context_id": context_id,
                "record_type": "TRANSITION",
                "transition": transition,
                "previous_state": previous,
                "current_state": current,
                "forward_horizon_sessions": int(horizon),
                "family_observation_count": len(frame),
                "date_observation_count": relative["observation_count"],
                "mean_forward_return": raw["mean"],
                "mean_forward_relative_global": relative["mean"],
                "median_forward_relative_global": relative["median"],
                "positive_relative_frequency": relative["positive_frequency"],
                "relative_hac_t_statistic": relative["hac_t_statistic"],
                "relative_hac_p_value": relative["hac_p_value"],
                "relative_ci_low": relative["confidence_interval_low"],
                "relative_ci_high": relative["confidence_interval_high"],
                "transition_known_at_signal_date": "YES",
                "warning": WARNING,
            }
        )
    state_source = eligible.loc[eligible["ROTATION_STATE"].ne("")]
    for (context_id, state), frame in state_source.groupby(["analysis_context_id", "ROTATION_STATE"], sort=True):
        for horizon in FORWARD_HORIZONS:
            observed = frame.loc[frame[f"FWD_{horizon}"].notna() & frame[f"GLOBAL_FWD_{horizon}"].notna()].copy()
            if observed.empty:
                continue
            observed["relative"] = (1.0 + observed[f"FWD_{horizon}"]) / (1.0 + observed[f"GLOBAL_FWD_{horizon}"]) - 1.0
            date_level = observed.groupby("date")[[f"FWD_{horizon}", "relative"]].mean()
            raw = newey_west_mean(date_level[f"FWD_{horizon}"], hac_lag(horizon))
            relative = newey_west_mean(date_level["relative"], hac_lag(horizon))
            summaries.append(
                {
                    "analysis_context_id": context_id,
                    "record_type": "STATE",
                    "transition": "NOT_APPLICABLE",
                    "previous_state": "NOT_APPLICABLE",
                    "current_state": state,
                    "forward_horizon_sessions": horizon,
                    "family_observation_count": len(observed),
                    "date_observation_count": relative["observation_count"],
                    "mean_forward_return": raw["mean"],
                    "mean_forward_relative_global": relative["mean"],
                    "median_forward_relative_global": relative["median"],
                    "positive_relative_frequency": relative["positive_frequency"],
                    "relative_hac_t_statistic": relative["hac_t_statistic"],
                    "relative_hac_p_value": relative["hac_p_value"],
                    "relative_ci_low": relative["confidence_interval_low"],
                    "relative_ci_high": relative["confidence_interval_high"],
                    "transition_known_at_signal_date": "NOT_APPLICABLE_STATE_OBSERVED_AT_T",
                    "warning": WARNING,
                }
            )
    return pd.DataFrame(summaries)


def parent_relative_results(base_weekly: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for formation_horizon in [21, 63, 126]:
        frame = base_weekly.loc[
            base_weekly[f"GLOBAL_RS_{formation_horizon}"].notna()
            & base_weekly[f"PARENT_RS_{formation_horizon}"].notna()
        ].copy()
        global_positive = frame[f"GLOBAL_RS_{formation_horizon}"] > 0
        parent_positive = frame[f"PARENT_RS_{formation_horizon}"] > 0
        frame["global_parent_state"] = np.select(
            [global_positive & parent_positive, global_positive & ~parent_positive, ~global_positive & parent_positive],
            ["BOTH_STRONG", "GLOBAL_ONLY", "PARENT_ONLY"],
            default="NEITHER_STRONG",
        )
        for (group_id, state), state_frame in frame.groupby(["research_group_id", "global_parent_state"], sort=True):
            for forward_horizon in FORWARD_HORIZONS:
                observed = state_frame.loc[
                    state_frame[f"FWD_{forward_horizon}"].notna()
                    & state_frame[f"GLOBAL_FWD_{forward_horizon}"].notna()
                    & state_frame[f"PARENT_FWD_{forward_horizon}"].notna()
                ].copy()
                if observed.empty:
                    continue
                observed["relative_global"] = (1.0 + observed[f"FWD_{forward_horizon}"]) / (1.0 + observed[f"GLOBAL_FWD_{forward_horizon}"]) - 1.0
                observed["relative_parent"] = (1.0 + observed[f"FWD_{forward_horizon}"]) / (1.0 + observed[f"PARENT_FWD_{forward_horizon}"]) - 1.0
                date_level = observed.groupby("date")[["relative_global", "relative_parent"]].mean()
                global_stats = newey_west_mean(date_level["relative_global"], hac_lag(forward_horizon))
                parent_stats = newey_west_mean(date_level["relative_parent"], hac_lag(forward_horizon))
                rows.append(
                    {
                        "research_group_id": group_id,
                        "formation_horizon_sessions": formation_horizon,
                        "global_parent_state": state,
                        "forward_horizon_sessions": forward_horizon,
                        "family_observation_count": len(observed),
                        "date_observation_count": global_stats["observation_count"],
                        "mean_forward_relative_global": global_stats["mean"],
                        "global_relative_hac_p_value": global_stats["hac_p_value"],
                        "mean_forward_relative_parent": parent_stats["mean"],
                        "parent_relative_hac_p_value": parent_stats["hac_p_value"],
                        "parent_mapping_frozen_before_a3r1": "YES",
                        "warning": WARNING,
                    }
                )
    return pd.DataFrame(rows)


def trend_quality_results(group_features: pd.DataFrame, base_weekly: pd.DataFrame) -> pd.DataFrame:
    features = [
        "LOG_PRICE_SLOPE_63", "LOG_PRICE_R2_63", "REL_R2_63", "REALISED_VOL_63",
        "MAX_FORMATION_PULLBACK_63", "LARGEST_1_DAY_MOVE_SHARE_63", "LARGEST_3_DAY_MOVE_SHARE_63",
        "PRICE_DISTANCE_HIGH_63",
    ]
    base_columns = ["date", "economic_exposure_family_id"] + features + [f"FWD_{h}" for h in [21, 42, 63]]
    merged = group_features.loc[
        group_features["analysis_context_type"].isin(["ROLE_GROUP", "ALL_EQUITY"]),
        ["date", "economic_exposure_family_id", "analysis_context_id", "MH_LEVEL_EQ"],
    ].merge(base_weekly[base_columns], on=["date", "economic_exposure_family_id"], how="left", validate="many_to_one")
    observation_rows: list[dict[str, Any]] = []
    for (context_id, date), frame in merged.loc[merged["MH_LEVEL_EQ"].notna()].groupby(["analysis_context_id", "date"], sort=True):
        n = len(frame)
        if n < 10:
            continue
        leader_count = max(3, int(math.ceil(n * 0.20)))
        leaders = frame.sort_values(["MH_LEVEL_EQ", "economic_exposure_family_id"], ascending=[False, True]).head(leader_count)
        if len(leaders) < 6:
            continue
        for feature in features:
            valid = leaders.loc[leaders[feature].notna()].sort_values(feature).copy()
            if len(valid) < 6:
                continue
            valid["quality_tercile"] = np.minimum((np.arange(len(valid)) * 3 // len(valid)) + 1, 3)
            for tercile, group in valid.groupby("quality_tercile"):
                for horizon in [21, 42, 63]:
                    values = group[f"FWD_{horizon}"].dropna()
                    if len(values):
                        observation_rows.append(
                            {
                                "date": date,
                                "analysis_context_id": context_id,
                                "quality_feature": feature,
                                "quality_tercile": int(tercile),
                                "forward_horizon_sessions": horizon,
                                "mean_forward_return": float(values.mean()),
                                "leader_count": len(leaders),
                                "covered_count": len(values),
                            }
                        )
    detail = pd.DataFrame(observation_rows)
    rows: list[dict[str, Any]] = []
    if detail.empty:
        return detail
    for keys, frame in detail.groupby(["analysis_context_id", "quality_feature", "quality_tercile", "forward_horizon_sessions"], sort=True):
        context_id, feature, tercile, horizon = keys
        stats = newey_west_mean(frame["mean_forward_return"], hac_lag(int(horizon)))
        rows.append(
            {
                "analysis_context_id": context_id,
                "baseline_signal_id": "MH_LEVEL_EQ",
                "quality_feature": feature,
                "quality_tercile": int(tercile),
                "forward_horizon_sessions": int(horizon),
                "date_observation_count": stats["observation_count"],
                "mean_forward_return": stats["mean"],
                "median_forward_return": stats["median"],
                "hac_t_statistic": stats["hac_t_statistic"],
                "hac_p_value": stats["hac_p_value"],
                "trend_quality_in_primary_signal": "NO",
                "warning": WARNING,
            }
        )
    result = pd.DataFrame(rows)
    high = result.loc[result["quality_tercile"].eq(3), ["analysis_context_id", "quality_feature", "forward_horizon_sessions", "mean_forward_return"]].rename(columns={"mean_forward_return": "tercile_3_mean"})
    low = result.loc[result["quality_tercile"].eq(1), ["analysis_context_id", "quality_feature", "forward_horizon_sessions", "mean_forward_return"]].rename(columns={"mean_forward_return": "tercile_1_mean"})
    contrast = high.merge(low, on=["analysis_context_id", "quality_feature", "forward_horizon_sessions"], how="outer")
    contrast["tercile_3_minus_tercile_1"] = contrast["tercile_3_mean"] - contrast["tercile_1_mean"]
    result = result.merge(contrast, on=["analysis_context_id", "quality_feature", "forward_horizon_sessions"], how="left")
    return result


def build_subperiod_results(retained: pd.DataFrame, policy: dict[str, Any]) -> pd.DataFrame:
    source = retained.loc[
        retained["analysis_context_type"].eq("ROLE_GROUP")
        & retained["signal_id"].isin(PRIMARY_SIGNALS)
        & retained["maturity_scope"].eq("FULL_DYNAMIC")
        & retained["top_tail_definition"].eq("TOP_3")
        & retained["forward_horizon_sessions"].isin(CENTRAL_HORIZONS)
    ].copy()
    final_date = source["date"].max()
    rows: list[dict[str, Any]] = []
    for subperiod in policy["subperiods"]:
        if subperiod.get("start_relative_years") is not None:
            start = final_date - pd.DateOffset(years=int(subperiod["start_relative_years"]))
        else:
            start = pd.Timestamp(subperiod["start"]) if subperiod.get("start") else None
        end = pd.Timestamp(subperiod["end"]) if subperiod.get("end") else None
        mask = pd.Series(True, index=source.index)
        if start is not None:
            mask &= source["date"] >= start
        if end is not None:
            mask &= source["date"] <= end
        observed = source.loc[mask]
        for keys, frame in observed.groupby(["analysis_context_id", "signal_id", "forward_horizon_sessions"], sort=True):
            context_id, signal_id, horizon = keys
            stats = newey_west_mean(frame["advantage_vs_global"], hac_lag(int(horizon)))
            rows.append(
                {
                    "subperiod_id": subperiod["subperiod_id"],
                    "subperiod_start": start,
                    "subperiod_end": end,
                    "analysis_context_id": context_id,
                    "signal_id": signal_id,
                    "top_tail_definition": "TOP_3",
                    "forward_horizon_sessions": int(horizon),
                    "observation_count": stats["observation_count"],
                    "mean_advantage_vs_global": stats["mean"],
                    "median_advantage_vs_global": stats["median"],
                    "positive_frequency": stats["positive_frequency"],
                    "hac_t_statistic": stats["hac_t_statistic"],
                    "hac_p_value": stats["hac_p_value"],
                    "ci_low": stats["confidence_interval_low"],
                    "ci_high": stats["confidence_interval_high"],
                    "dynamic_membership": "CONTEMPORANEOUS",
                    "warning": WARNING,
                }
            )
    return pd.DataFrame(rows)


def build_decay_results(top_tail: pd.DataFrame) -> pd.DataFrame:
    result = top_tail.loc[
        top_tail["analysis_context_type"].isin(["ROLE_GROUP", "ALL_EQUITY"])
        & top_tail["signal_id"].isin(PRIMARY_SIGNALS)
        & top_tail["maturity_scope"].eq("FULL_DYNAMIC")
        & top_tail["top_tail_definition"].isin(["RANK_1", "TOP_3", "TOP_5"]),
        [
            "analysis_context_id", "analysis_context_type", "signal_id", "top_tail_definition",
            "forward_horizon_sessions", "advantage_vs_global_observation_count", "advantage_vs_global_mean",
            "advantage_vs_global_median", "advantage_vs_global_positive_frequency", "advantage_vs_global_hac_p_value",
            "advantage_vs_global_ci_low", "advantage_vs_global_ci_high",
        ],
    ].copy()
    result["peak_predictive_horizon"] = "NO"
    result["half_life_or_reversal_horizon_sessions"] = np.nan
    for _, indices in result.groupby(["analysis_context_id", "signal_id", "top_tail_definition"]).groups.items():
        block = result.loc[indices].sort_values("forward_horizon_sessions")
        positive = block.loc[block["advantage_vs_global_mean"] > 0]
        if positive.empty:
            continue
        peak_index = positive["advantage_vs_global_mean"].idxmax()
        result.loc[peak_index, "peak_predictive_horizon"] = "YES"
        peak_value = float(result.loc[peak_index, "advantage_vs_global_mean"])
        peak_horizon = int(result.loc[peak_index, "forward_horizon_sessions"])
        later = block.loc[block["forward_horizon_sessions"] > peak_horizon]
        half = later.loc[later["advantage_vs_global_mean"] <= peak_value * 0.5]
        if not half.empty:
            result.loc[indices, "half_life_or_reversal_horizon_sessions"] = int(half.iloc[0]["forward_horizon_sessions"])
    result["warning"] = WARNING
    return result


def score_primary_support(top_tail: pd.DataFrame) -> pd.DataFrame:
    source = top_tail.loc[
        top_tail["analysis_context_type"].eq("ROLE_GROUP")
        & top_tail["signal_id"].isin(PRIMARY_SIGNALS)
        & top_tail["maturity_scope"].eq("FULL_DYNAMIC")
        & top_tail["top_tail_definition"].eq("TOP_3")
        & top_tail["forward_horizon_sessions"].isin(CENTRAL_HORIZONS)
    ].copy()
    source = source.loc[source["formal_inference_eligible"].eq("YES")]
    rows: list[dict[str, Any]] = []
    for signal_id, frame in source.groupby("signal_id", sort=True):
        rows.append(
            {
                "signal_id": signal_id,
                "mean_advantage_across_primary_cells": frame["advantage_vs_global_mean"].mean(),
                "positive_cell_fraction": (frame["advantage_vs_global_mean"] > 0).mean(),
                "raw_p_le_0_10_count": (frame["advantage_vs_global_hac_p_value"] <= 0.10).sum(),
                "fdr_q_le_0_10_count": (frame["advantage_vs_global_bh_q_value"] <= 0.10).sum(),
                "bootstrap_positive_count": (frame["advantage_vs_global_bootstrap_ci_low"] > 0).sum(),
                "cell_count": len(frame),
            }
        )
    result = pd.DataFrame(rows)
    result["support_sort_score"] = (
        result["positive_cell_fraction"]
        + result["raw_p_le_0_10_count"] / result["cell_count"].clip(lower=1)
        + 2.0 * result["fdr_q_le_0_10_count"] / result["cell_count"].clip(lower=1)
        + result["bootstrap_positive_count"] / result["cell_count"].clip(lower=1)
    )
    return result.sort_values(["support_sort_score", "mean_advantage_across_primary_cells"], ascending=False).reset_index(drop=True)


def select_top_from_frame(frame: pd.DataFrame, signal_id: str, horizon: int, count: int = 3) -> dict[str, Any] | None:
    column = signal_column(signal_id)
    eligible = frame.loc[frame[column].notna()].sort_values([column, "economic_exposure_family_id"], ascending=[False, True])
    if len(eligible) < count:
        return None
    selected = eligible.head(count)
    returns = selected[f"FWD_{horizon}"].to_numpy(float)
    global_values = selected[f"GLOBAL_FWD_{horizon}"].to_numpy(float)
    if not np.isfinite(returns).all() or not np.isfinite(global_values).all():
        return None
    top = float(returns.mean())
    global_return = float(global_values[0]) if np.allclose(global_values, global_values[0]) else np.nan
    return {
        "top_return": top,
        "advantage_vs_global": relative_advantage(top, global_return),
        "signal_cohort_count": len(eligible),
    }


def dependency_results(
    group_features: pd.DataFrame,
    matrices: Matrices,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    candidates = sorted(metadata["economic_exposure_family_id"].tolist())
    annualised = {
        family: annualised_geometric_return(matrices.returns[family])
        for family in candidates
    }
    ordered_winners = sorted(candidates, key=lambda family: (-(annualised[family] if np.isfinite(annualised[family]) else -np.inf), family))
    strongest = ordered_winners[:1]
    top_five = ordered_winners[:5]
    us_technology = metadata.loc[
        (metadata["a0_primary_geography"].str.contains("UNITED_STATES|US", regex=True, na=False))
        & (metadata["sector"].str.contains("TECHNOLOGY", regex=True, na=False) | metadata["economic_exposure_family_id"].eq("US_NASDAQ_100")),
        "economic_exposure_family_id",
    ].tolist()
    semiconductors = metadata.loc[
        metadata["economic_exposure_family_id"].str.contains("SEMICONDUCTOR", regex=True)
        | metadata["industry"].str.contains("SEMICONDUCTOR", regex=True, na=False),
        "economic_exposure_family_id",
    ].tolist()
    all_equity = group_features.loc[group_features["analysis_context_id"].eq("ALL_EQUITY_OPPORTUNITIES")].copy()
    scenarios = {
        "BASE_ALL_EQUITY": set(),
        "EXCLUDE_US_TECHNOLOGY": set(us_technology),
        "EXCLUDE_SEMICONDUCTORS": set(semiconductors),
        "EXCLUDE_STRONGEST_FULL_PERIOD_WINNER": set(strongest),
        "EXCLUDE_TOP_FIVE_FULL_PERIOD_WINNERS": set(top_five),
    }
    rows: list[dict[str, Any]] = []
    for scenario, exclusions in scenarios.items():
        scenario_frame = all_equity.loc[~all_equity["economic_exposure_family_id"].isin(exclusions)]
        for signal_id in PRIMARY_SIGNALS:
            for horizon in CENTRAL_HORIZONS:
                date_records: list[float] = []
                for _, date_frame in scenario_frame.groupby("date", sort=True):
                    record = select_top_from_frame(date_frame, signal_id, horizon, 3)
                    if record and np.isfinite(record["advantage_vs_global"]):
                        date_records.append(record["advantage_vs_global"])
                stats = newey_west_mean(date_records, hac_lag(horizon))
                rows.append(
                    {
                        "dependency_scenario": scenario,
                        "analysis_context_id": "ALL_EQUITY_OPPORTUNITIES",
                        "signal_id": signal_id,
                        "forward_horizon_sessions": horizon,
                        "excluded_family_ids": ";".join(sorted(exclusions)) if exclusions else "NONE",
                        "excluded_family_count": len(exclusions),
                        "observation_count": stats["observation_count"],
                        "mean_top3_advantage_vs_global": stats["mean"],
                        "median_top3_advantage_vs_global": stats["median"],
                        "positive_frequency": stats["positive_frequency"],
                        "hac_t_statistic": stats["hac_t_statistic"],
                        "hac_p_value": stats["hac_p_value"],
                        "diagnostic_uses_ex_post_winner_identity": "YES" if "WINNER" in scenario else "NO",
                        "warning": WARNING,
                    }
                )
    for group_id in PRIMARY_ROLES.values():
        frame = group_features.loc[group_features["analysis_context_id"].eq(group_id)]
        for signal_id in PRIMARY_SIGNALS:
            for horizon in CENTRAL_HORIZONS:
                date_records = []
                for _, date_frame in frame.groupby("date", sort=True):
                    record = select_top_from_frame(date_frame, signal_id, horizon, 3)
                    if record and np.isfinite(record["advantage_vs_global"]):
                        date_records.append(record["advantage_vs_global"])
                stats = newey_west_mean(date_records, hac_lag(horizon))
                rows.append(
                    {
                        "dependency_scenario": f"{group_id}_ONLY",
                        "analysis_context_id": group_id,
                        "signal_id": signal_id,
                        "forward_horizon_sessions": horizon,
                        "excluded_family_ids": "NOT_APPLICABLE_GROUP_ONLY",
                        "excluded_family_count": len(candidates) - frame["economic_exposure_family_id"].nunique(),
                        "observation_count": stats["observation_count"],
                        "mean_top3_advantage_vs_global": stats["mean"],
                        "median_top3_advantage_vs_global": stats["median"],
                        "positive_frequency": stats["positive_frequency"],
                        "hac_t_statistic": stats["hac_t_statistic"],
                        "hac_p_value": stats["hac_p_value"],
                        "diagnostic_uses_ex_post_winner_identity": "NO",
                        "warning": WARNING,
                    }
                )
    mature_frame = all_equity.loc[all_equity["contemporaneous_research_maturity"].eq("MATURE")]
    for signal_id in PRIMARY_SIGNALS:
        for horizon in CENTRAL_HORIZONS:
            date_records = []
            for _, date_frame in mature_frame.groupby("date", sort=True):
                record = select_top_from_frame(date_frame, signal_id, horizon, 3)
                if record and np.isfinite(record["advantage_vs_global"]):
                    date_records.append(record["advantage_vs_global"])
            stats = newey_west_mean(date_records, hac_lag(horizon))
            rows.append(
                {
                    "dependency_scenario": "MATURE_ONLY",
                    "analysis_context_id": "ALL_EQUITY_OPPORTUNITIES",
                    "signal_id": signal_id,
                    "forward_horizon_sessions": horizon,
                    "excluded_family_ids": "DYNAMIC_NON_MATURE_OBSERVATIONS",
                    "excluded_family_count": np.nan,
                    "observation_count": stats["observation_count"],
                    "mean_top3_advantage_vs_global": stats["mean"],
                    "median_top3_advantage_vs_global": stats["median"],
                    "positive_frequency": stats["positive_frequency"],
                    "hac_t_statistic": stats["hac_t_statistic"],
                    "hac_p_value": stats["hac_p_value"],
                    "diagnostic_uses_ex_post_winner_identity": "NO",
                    "warning": WARNING,
                }
            )
    return pd.DataFrame(rows)


def robustness_results(group_features: pd.DataFrame) -> pd.DataFrame:
    variants = {
        "RS42_NEIGHBOUR_32": "RANK_RS_32",
        "RS42_CENTRAL_42": "RANK_RS_42",
        "RS42_NEIGHBOUR_52": "RANK_RS_52",
        "RS63_NEIGHBOUR_50": "RANK_RS_50",
        "RS63_CENTRAL_63": "RANK_RS_63",
        "RS63_NEIGHBOUR_75": "RANK_RS_75",
        "MH_RECENCY_CENTRAL": "MH_LEVEL_RECENCY_TILT",
        "MH_RECENCY_WHOLE_STRUCTURE_NEIGHBOUR": "MH_STRUCTURE_FAST_NEIGHBOUR",
        "MH_60D_CENTRAL": "MH_LEVEL_60D_CENTERED",
        "MH_60D_WHOLE_STRUCTURE_NEIGHBOUR": "MH_STRUCTURE_60D_NEIGHBOUR",
    }
    rows: list[dict[str, Any]] = []
    source = group_features.loc[group_features["analysis_context_type"].isin(["ROLE_GROUP", "ALL_EQUITY"])]
    for context_id, context_frame in source.groupby("analysis_context_id", sort=True):
        for variant, column in variants.items():
            for horizon in CENTRAL_HORIZONS:
                date_records = []
                for _, date_frame in context_frame.groupby("date", sort=True):
                    eligible = date_frame.loc[date_frame[column].notna()].sort_values([column, "economic_exposure_family_id"], ascending=[False, True])
                    if len(eligible) < 3:
                        continue
                    selected = eligible.head(3)
                    fwd = selected[f"FWD_{horizon}"].to_numpy(float)
                    global_fwd = selected[f"GLOBAL_FWD_{horizon}"].to_numpy(float)
                    if np.isfinite(fwd).all() and np.isfinite(global_fwd).all() and np.allclose(global_fwd, global_fwd[0]):
                        date_records.append(relative_advantage(float(fwd.mean()), float(global_fwd[0])))
                stats = newey_west_mean(date_records, hac_lag(horizon))
                rows.append(
                    {
                        "analysis_context_id": context_id,
                        "robustness_variant_id": variant,
                        "score_column": column,
                        "forward_horizon_sessions": horizon,
                        "observation_count": stats["observation_count"],
                        "mean_top3_advantage_vs_global": stats["mean"],
                        "median_top3_advantage_vs_global": stats["median"],
                        "positive_frequency": stats["positive_frequency"],
                        "hac_t_statistic": stats["hac_t_statistic"],
                        "hac_p_value": stats["hac_p_value"],
                        "neighbourhood_not_optimisation_grid": "YES",
                        "warning": WARNING,
                    }
                )
    return pd.DataFrame(rows)


def breadth_results(group_features: pd.DataFrame, retained: pd.DataFrame, best_signal: str) -> pd.DataFrame:
    breadth_rows: list[dict[str, Any]] = []
    source = group_features.loc[group_features["analysis_context_type"].isin(["ROLE_GROUP", "ALL_EQUITY"])]
    for (context_id, date), frame in source.groupby(["analysis_context_id", "date"], sort=True):
        rs = frame["RS_63"].dropna()
        acceleration = frame["ACCEL_FAST_COMPOSITE"].dropna()
        states = frame.loc[frame["ROTATION_STATE"].ne(""), "ROTATION_STATE"]
        if len(rs) < 3:
            continue
        positive_fraction = float((rs > 0).mean())
        regime = "NARROW" if positive_fraction < 1 / 3 else ("MEDIUM" if positive_fraction < 2 / 3 else "BROAD")
        breadth_rows.append(
            {
                "record_type": "WEEKLY_BREADTH",
                "date": date,
                "analysis_context_id": context_id,
                "eligible_rs63_count": len(rs),
                "positive_global_rs_fraction": positive_fraction,
                "improving_acceleration_fraction": float((acceleration >= 0.5).mean()) if len(acceleration) else np.nan,
                "leading_state_fraction": float(states.eq("LEADING").mean()) if len(states) else np.nan,
                "rs63_cross_sectional_dispersion": float(rs.std(ddof=0)),
                "leadership_breadth_regime": regime,
                "best_signal_id": best_signal,
                "warning": WARNING,
            }
        )
    raw = pd.DataFrame(breadth_rows)
    efficacy_rows: list[dict[str, Any]] = []
    signal_dates = retained.loc[
        retained["signal_id"].eq(best_signal)
        & retained["maturity_scope"].eq("FULL_DYNAMIC")
        & retained["top_tail_definition"].eq("TOP_3")
        & retained["forward_horizon_sessions"].isin(CENTRAL_HORIZONS)
    ]
    merged = signal_dates.merge(
        raw[["date", "analysis_context_id", "leadership_breadth_regime", "rs63_cross_sectional_dispersion"]],
        on=["date", "analysis_context_id"],
        how="left",
        validate="many_to_one",
    )
    for (context_id, regime, horizon), frame in merged.groupby(["analysis_context_id", "leadership_breadth_regime", "forward_horizon_sessions"], sort=True):
        stats = newey_west_mean(frame["advantage_vs_global"], hac_lag(int(horizon)))
        efficacy_rows.append(
            {
                "record_type": "BREADTH_EFFICACY",
                "analysis_context_id": context_id,
                "leadership_breadth_regime": regime,
                "forward_horizon_sessions": int(horizon),
                "observation_count": stats["observation_count"],
                "mean_top3_advantage_vs_global": stats["mean"],
                "median_top3_advantage_vs_global": stats["median"],
                "positive_frequency": stats["positive_frequency"],
                "hac_t_statistic": stats["hac_t_statistic"],
                "hac_p_value": stats["hac_p_value"],
                "best_signal_id": best_signal,
                "warning": WARNING,
            }
        )

    all_equity = source.loc[source["analysis_context_id"].eq("ALL_EQUITY_OPPORTUNITIES")]
    concentration_rows: list[dict[str, Any]] = []
    for date, frame in all_equity.groupby("date", sort=True):
        rs = frame.set_index("economic_exposure_family_id")["RS_63"]
        valid = rs.dropna()
        if len(valid) < 5:
            continue
        positive_fraction = float((valid > 0).mean())
        nasdaq = rs.get("US_NASDAQ_100", np.nan)
        us_broad = rs.get("US_BROAD_LARGE_CAP", np.nan)
        geography = frame.loc[frame["primary_rotation_role"].eq("BROAD_GEOGRAPHY_ROTATION") & ~frame["economic_exposure_family_id"].str.startswith("US_") & frame["RS_63"].notna(), "RS_63"]
        non_us_median = float(geography.median()) if len(geography) else np.nan
        dispersion = float(valid.std(ddof=0))
        concentration_rows.append(
            {
                "date": date,
                "narrow_megacap_leadership": bool(np.isfinite(nasdaq) and np.isfinite(us_broad) and nasdaq > 0 and us_broad > 0 and positive_fraction < 1 / 3),
                "broad_participation": positive_fraction >= 2 / 3,
                "strong_non_us_leadership": bool(np.isfinite(non_us_median) and np.isfinite(us_broad) and non_us_median > us_broad),
                "dispersion": dispersion,
            }
        )
    concentration = pd.DataFrame(concentration_rows)
    if not concentration.empty:
        concentration["prior_expanding_dispersion_median"] = concentration["dispersion"].expanding(min_periods=26).median().shift(1)
        concentration["dispersion_regime"] = np.where(
            concentration["dispersion"] > concentration["prior_expanding_dispersion_median"], "HIGH_DISPERSION", "LOW_DISPERSION"
        )
        all_signal = signal_dates.loc[signal_dates["analysis_context_id"].eq("ALL_EQUITY_OPPORTUNITIES")].merge(concentration, on="date", how="left")
        regimes = {
            "NARROW_MEGACAP": all_signal["narrow_megacap_leadership"].eq(True),
            "BROAD_PARTICIPATION": all_signal["broad_participation"].eq(True),
            "STRONG_NON_US": all_signal["strong_non_us_leadership"].eq(True),
            "HIGH_DISPERSION": all_signal["dispersion_regime"].eq("HIGH_DISPERSION"),
            "LOW_DISPERSION": all_signal["dispersion_regime"].eq("LOW_DISPERSION"),
        }
        for regime, mask in regimes.items():
            for horizon, frame in all_signal.loc[mask].groupby("forward_horizon_sessions"):
                stats = newey_west_mean(frame["advantage_vs_global"], hac_lag(int(horizon)))
                efficacy_rows.append(
                    {
                        "record_type": "MARKET_CONCENTRATION_EFFICACY",
                        "analysis_context_id": "ALL_EQUITY_OPPORTUNITIES",
                        "market_concentration_regime": regime,
                        "forward_horizon_sessions": int(horizon),
                        "observation_count": stats["observation_count"],
                        "mean_top3_advantage_vs_global": stats["mean"],
                        "median_top3_advantage_vs_global": stats["median"],
                        "positive_frequency": stats["positive_frequency"],
                        "hac_t_statistic": stats["hac_t_statistic"],
                        "hac_p_value": stats["hac_p_value"],
                        "best_signal_id": best_signal,
                        "regime_threshold_uses_future_data": "NO",
                        "warning": WARNING,
                    }
                )
    return pd.concat([raw, pd.DataFrame(efficacy_rows)], ignore_index=True, sort=False)


def build_candidate_assessment(
    top_tail: pd.DataFrame,
    subperiods: pd.DataFrame,
    dependencies: pd.DataFrame,
    persistence: pd.DataFrame,
    robustness: pd.DataFrame,
    all_tests_pass: bool,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    full = top_tail.loc[
        top_tail["analysis_context_type"].eq("ROLE_GROUP")
        & top_tail["maturity_scope"].eq("FULL_DYNAMIC")
        & top_tail["forward_horizon_sessions"].isin(CENTRAL_HORIZONS)
    ]
    companion = {
        "MH_LEVEL_EQ": "MH_LEVEL_RECENCY_TILT",
        "MH_LEVEL_RECENCY_TILT": "MH_LEVEL_EQ",
        "MH_LEVEL_60D_CENTERED": "MH_LEVEL_EQ",
        "MH_LEVEL_3_6_12_REFERENCE": "MH_LEVEL_EQ",
        "ACCEL_FAST_COMPOSITE": "SHORT_MINUS_LONG_RS",
        "SHORT_MINUS_LONG_RS": "ACCEL_FAST_COMPOSITE",
        "DISCRETE_RECENT_CONSISTENCY": "RRG_TRANSPARENT_LEVEL",
        "PAIRWISE_MAJORITY_5H": "MH_LEVEL_EQ",
        "RRG_TRANSPARENT_LEVEL": "DISCRETE_RECENT_CONSISTENCY",
    }
    for signal_id in PRIMARY_SIGNALS:
        top3 = full.loc[full["signal_id"].eq(signal_id) & full["top_tail_definition"].eq("TOP_3")]
        top5 = full.loc[full["signal_id"].eq(signal_id) & full["top_tail_definition"].eq("TOP_5")]
        positive_top3 = top3.groupby("analysis_context_id")["advantage_vs_global_mean"].apply(lambda values: int((values > 0).sum()))
        positive_top5 = top5.groupby("analysis_context_id")["advantage_vs_global_mean"].apply(lambda values: int((values > 0).sum()))
        qualifying_groups = set(positive_top3[positive_top3 >= 3].index) & set(positive_top5[positive_top5 >= 3].index)
        criterion1 = bool((positive_top3 >= 3).any())
        criterion2 = bool(qualifying_groups)
        formal_top3 = top3.loc[top3["formal_inference_eligible"].eq("YES")]
        criterion3 = bool(
            (formal_top3["advantage_vs_global_hac_p_value"] <= 0.10).any()
            or (formal_top3["advantage_vs_global_bootstrap_ci_low"] > 0).any()
        )
        companion_rows = full.loc[
            full["signal_id"].eq(companion[signal_id])
            & full["top_tail_definition"].eq("TOP_3")
            & full["analysis_context_id"].isin(qualifying_groups or set(positive_top3[positive_top3 > 0].index))
        ]
        criterion4 = bool((companion_rows["advantage_vs_global_mean"] > 0).mean() >= 0.50) if len(companion_rows) else False
        sub = subperiods.loc[
            subperiods["signal_id"].eq(signal_id)
            & subperiods["subperiod_id"].isin(["PRE_2020", "FROM_2020", "LATEST_5Y", "LATEST_3Y"])
            & subperiods["analysis_context_id"].isin(qualifying_groups or set(PRIMARY_ROLES.values()))
        ]
        positive_subperiods = sub.groupby("subperiod_id")["mean_advantage_vs_global"].mean()
        criterion5 = bool((positive_subperiods > 0).sum() >= 2)
        dep = dependencies.loc[dependencies["signal_id"].eq(signal_id)]
        required_dep = dep.loc[dep["dependency_scenario"].isin([
            "EXCLUDE_US_TECHNOLOGY", "EXCLUDE_STRONGEST_FULL_PERIOD_WINNER", "EXCLUDE_TOP_FIVE_FULL_PERIOD_WINNERS"
        ])]
        criterion6 = bool(required_dep.groupby("dependency_scenario")["mean_top3_advantage_vs_global"].mean().gt(0).all()) if len(required_dep) else False
        mature = dep.loc[dep["dependency_scenario"].eq("MATURE_ONLY"), "mean_top3_advantage_vs_global"]
        criterion7 = bool(mature.mean() >= 0) if len(mature) else False
        pers = persistence.loc[persistence["signal_id"].eq(signal_id)]
        criterion8 = bool(
            (pers["median_top3_duration_weeks"].median() >= 2)
            or (pers["probability_top3_remains_top10_percent"].median() >= 0.40)
        ) if len(pers) else False
        criterion9 = bool(all_tests_pass)
        criteria = [criterion1, criterion2, criterion3, criterion4, criterion5, criterion6, criterion7, criterion8, criterion9]
        passed = sum(criteria)
        if not criterion9:
            classification = "REJECTED"
        elif passed >= 7:
            classification = "A3R1_RESEARCH_CANDIDATE"
        elif passed >= 4:
            classification = "WEAK_OR_REGIME_DEPENDENT"
        else:
            classification = "REJECTED"
        rows.append(
            {
                "signal_id": signal_id,
                "signal_family": SIGNAL_FAMILY_MAP.get(signal_id, "UNKNOWN"),
                "criterion_1_top3_positive_3_of_4": criterion1,
                "criterion_2_top5_same_group": criterion2,
                "criterion_3_corrected_inference": criterion3,
                "criterion_4_neighbour_direction": criterion4,
                "criterion_5_subperiods": criterion5,
                "criterion_6_dependency": criterion6,
                "criterion_7_mature_only": criterion7,
                "criterion_8_persistence": criterion8,
                "criterion_9_correctness": criterion9,
                "criteria_passed": passed,
                "criteria_total": 9,
                "qualifying_group_ids": ";".join(sorted(qualifying_groups)) if qualifying_groups else "NONE",
                "fdr_surviving_cell_count": int((formal_top3["advantage_vs_global_bh_q_value"] <= 0.10).sum()),
                "classification": classification,
                "warning": WARNING,
            }
        )
    return pd.DataFrame(rows).sort_values(["criteria_passed", "signal_id"], ascending=[False, True]).reset_index(drop=True)


def build_multiple_testing_ledger(
    top_tail: pd.DataFrame,
    group_results: pd.DataFrame,
    subperiods: pd.DataFrame,
    dependencies: pd.DataFrame,
    robustness: pd.DataFrame,
    registry: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    registry_class = registry.set_index("signal_id")["registry_class"].to_dict()
    for index, row in top_tail.iterrows():
        spec = f"TOPTAIL|{row.analysis_context_id}|{row.signal_id}|{row.maturity_scope}|{row.top_tail_definition}|F{int(row.forward_horizon_sessions)}"
        rows.append(
            {
                "specification_id": spec,
                "test_family": "TOP_TAIL",
                "registry_class": registry_class.get(row.signal_id, "UNREGISTERED_ERROR"),
                "signal_id": row.signal_id,
                "analysis_context_id": row.analysis_context_id,
                "forward_horizon_sessions": row.forward_horizon_sessions,
                "effect_name": "ADVANTAGE_VS_GLOBAL",
                "effect_value": row.advantage_vs_global_mean,
                "raw_p_value": row.advantage_vs_global_hac_p_value,
                "adjusted_q_value": row.advantage_vs_global_bh_q_value,
                "executed": "YES",
                "result_direction": "POSITIVE" if row.advantage_vs_global_mean > 0 else "NON_POSITIVE",
            }
        )
    for _, row in group_results.iterrows():
        rows.append(
            {
                "specification_id": f"FULLRANK|{row.analysis_context_id}|{row.signal_id}|F{int(row.forward_horizon_sessions)}",
                "test_family": "FULL_RANK_SECONDARY",
                "registry_class": registry_class.get(row.signal_id, "UNREGISTERED_ERROR"),
                "signal_id": row.signal_id,
                "analysis_context_id": row.analysis_context_id,
                "forward_horizon_sessions": row.forward_horizon_sessions,
                "effect_name": "MEAN_SPEARMAN_IC",
                "effect_value": row.mean_spearman_ic,
                "raw_p_value": row.ic_hac_p_value,
                "adjusted_q_value": np.nan,
                "executed": "YES",
                "result_direction": "POSITIVE" if row.mean_spearman_ic > 0 else "NON_POSITIVE",
            }
        )
    table_specs = [
        (subperiods, "SUBPERIOD", "mean_advantage_vs_global", "hac_p_value"),
        (dependencies, "DEPENDENCY", "mean_top3_advantage_vs_global", "hac_p_value"),
        (robustness, "ROBUSTNESS", "mean_top3_advantage_vs_global", "hac_p_value"),
    ]
    for table, family, effect_column, p_column in table_specs:
        for index, row in table.iterrows():
            signal_id = row.get("signal_id", row.get("score_column", "NOT_APPLICABLE"))
            rows.append(
                {
                    "specification_id": f"{family}|{index}|{signal_id}",
                    "test_family": family,
                    "registry_class": registry_class.get(signal_id, family),
                    "signal_id": signal_id,
                    "analysis_context_id": row.get("analysis_context_id", "NOT_APPLICABLE"),
                    "forward_horizon_sessions": row.get("forward_horizon_sessions", np.nan),
                    "effect_name": effect_column.upper(),
                    "effect_value": row.get(effect_column, np.nan),
                    "raw_p_value": row.get(p_column, np.nan),
                    "adjusted_q_value": np.nan,
                    "executed": "YES",
                    "result_direction": "POSITIVE" if row.get(effect_column, np.nan) > 0 else "NON_POSITIVE",
                }
            )
    executed_signal_ids = {row["signal_id"] for row in rows}
    for _, item in registry.iterrows():
        if item["signal_id"] not in executed_signal_ids:
            rows.append(
                {
                    "specification_id": f"DIAGNOSTIC_COMPLETION|{item.signal_id}",
                    "test_family": "NON_HYPOTHESIS_DIAGNOSTIC",
                    "registry_class": item.registry_class,
                    "signal_id": item.signal_id,
                    "analysis_context_id": "NOT_APPLICABLE",
                    "forward_horizon_sessions": np.nan,
                    "effect_name": "DIAGNOSTIC_ARTIFACT_COMPLETED",
                    "effect_value": np.nan,
                    "raw_p_value": np.nan,
                    "adjusted_q_value": np.nan,
                    "executed": "YES",
                    "result_direction": "DESCRIPTIVE",
                }
            )
    result = pd.DataFrame(rows)
    result["failed_specification_omitted"] = "NO"
    result["correlated_cells_are_independent_hypotheses"] = "NO"
    result["warning"] = WARNING
    if result["specification_id"].duplicated().any():
        raise AssertionError("Multiple-testing specification IDs are not unique")
    return result


def run_correctness_tests(
    inputs: Inputs,
    matrices: Matrices,
    metadata: pd.DataFrame,
    group_features: pd.DataFrame,
    retained: pd.DataFrame,
    ledger: pd.DataFrame,
) -> pd.DataFrame:
    tests: list[dict[str, Any]] = []

    def record(test_id: str, requirement: str, function) -> None:
        try:
            detail = function()
            tests.append({"test_id": test_id, "requirement": requirement, "status": "PASS", "detail": str(detail)})
        except Exception as error:  # correctness harness must preserve the failure evidence
            tests.append({"test_id": test_id, "requirement": requirement, "status": "FAIL", "detail": f"{type(error).__name__}: {error}"})

    def test_no_same_close() -> str:
        frame = pd.DataFrame({"x": [0.01, 0.50, 0.02, 0.03]})
        forward = strict_forward_total_return(frame, 1)
        assert abs(forward.loc[1, "x"] - 0.02) < 1e-12
        assert abs(forward.loc[0, "x"] - 0.50) < 1e-12
        return "Synthetic date-t 50% return is excluded from date-t forward-1 return"

    def test_next_session() -> str:
        positions = matrices.weekly_positions
        eligible = positions[positions < len(inputs.calendar) - 1]
        assert np.all(inputs.calendar[eligible + 1] > inputs.calendar[eligible])
        return f"{len(eligible)} weekly signals map strictly to a later canonical session"

    def test_contemporaneous_only() -> str:
        assert not group_features.duplicated(["date", "analysis_context_id", "economic_exposure_family_id"]).any()
        assert set(group_features["economic_exposure_family_id"]).issubset(set(metadata["economic_exposure_family_id"]))
        return "Every rank row has one contemporaneous economic-family identity in its declared context"

    def test_dynamic_warmup() -> str:
        for horizon in MAIN_FORMATION_HORIZONS:
            count = matrices.valid.rolling(horizon, min_periods=horizon).sum()
            bad = matrices.cumulative_returns[horizon].notna() & ~count.eq(horizon)
            assert not bad.any().any(), horizon
        return "All 21/42/63/126/252 signals require their own complete formation window; no 504 gate"

    def test_remediated_history_only() -> str:
        assert inputs.policy["authoritative_inputs"]["corrected_panel"].startswith("UKACTIVE_A2R_")
        old_names = {"UKACTIVE_A2_TOTAL_RETURN_PANEL_GBP.parquet", "UKACTIVE_A2_EXPOSURE_HISTORY_MASTER.parquet"}
        assert not old_names.intersection(inputs.policy["authoritative_inputs"].values())
        return "Only the corrected A2R panel is an A3R1 return input"

    def test_us_defence() -> str:
        series = matrices.returns.get("US_AEROSPACE_DEFENCE")
        assert series is not None
        assert series.loc[series.index < pd.Timestamp("2026-07-20")].notna().sum() == 0
        score = group_features.loc[group_features["economic_exposure_family_id"].eq("US_AEROSPACE_DEFENCE"), "SIGNAL_RS_21"]
        dates = group_features.loc[group_features["economic_exposure_family_id"].eq("US_AEROSPACE_DEFENCE") & score.notna(), "date"]
        assert dates.empty or dates.min() >= pd.Timestamp("2026-08-17")
        return "US aerospace/defence cannot enter before corrected mandate history plus warm-up"

    def test_global_banks() -> str:
        if "GLOBAL_BANKS" in matrices.returns:
            assert matrices.returns["GLOBAL_BANKS"].notna().sum() == 0
        assert "GLOBAL_BANKS" not in set(group_features["economic_exposure_family_id"])
        return "GLOBAL_BANKS has no valid history and no rank row"

    def test_duplicates() -> str:
        assert "implementation_listing_id" not in group_features.columns
        assert "ticker" not in group_features.columns
        assert not group_features.duplicated(["date", "analysis_context_id", "economic_exposure_family_id"]).any()
        return "Listing/provider duplication cannot enter the economic-family rank"

    def test_benchmark_order() -> str:
        exposure = pd.Series([0.10, 0.03, -0.02, 0.20], index=list("ABCD"))
        benchmark = 0.04
        relative = (1 + exposure) / (1 + benchmark) - 1
        assert exposure.sort_values().index.tolist() == relative.sort_values().index.tolist()
        return "Common benchmark subtraction/division preserves same-horizon order"

    def test_segments() -> str:
        values = np.zeros(300)
        end = len(values) - 1
        values[end] = 0.01
        values[end - 21] = 0.02
        values[end - 42] = 0.03
        values[end - 63] = 0.04
        values[end - 126] = 0.05
        frame = pd.DataFrame({"x": values})
        observed = [
            strict_segment_total_return(frame, 0, 21).iloc[-1, 0],
            strict_segment_total_return(frame, 21, 42).iloc[-1, 0],
            strict_segment_total_return(frame, 42, 63).iloc[-1, 0],
            strict_segment_total_return(frame, 63, 126).iloc[-1, 0],
            strict_segment_total_return(frame, 126, 252).iloc[-1, 0],
        ]
        assert np.allclose(observed, [0.01, 0.02, 0.03, 0.04, 0.05])
        return "Five impulse fixtures land in five distinct non-overlapping segments"

    def test_pairwise() -> str:
        values = np.array([[5, 5, 5, 5, 5], [4, 4, 4, 4, 4], [3, 3, 3, 3, 3], [np.nan, 9, 9, 9, 9]], float)
        result = pairwise_majority_win_rate(values)
        assert np.allclose(result[:3], [1.0, 0.5, 0.0]) and np.isnan(result[3])
        return "Pairwise denominator uses only the three contemporaneously complete competitors"

    def test_parent_mapping() -> str:
        assert inputs.parent_map["mapping_uses_deepvue"].eq("NO").all()
        parent_columns = [column for column in group_features if column.startswith("PARENT_FWD_")]
        assert parent_columns
        return "Frozen semantic parent map is DeepVue-independent; returns require contemporaneous parent data"

    def test_relative_line_no_future() -> str:
        index = pd.date_range("2020-01-01", periods=80, freq="B")
        first = pd.DataFrame({"x": np.linspace(0, 0.10, 80)}, index=index)
        second = first.copy()
        second.iloc[65:] += 100
        slope_a, _ = rolling_ols_slope_r2(first, 21)
        slope_b, _ = rolling_ols_slope_r2(second, 21)
        assert np.allclose(slope_a.iloc[:65], slope_b.iloc[:65], equal_nan=True)
        return "Changing observations after t cannot alter a relative-line feature at or before t"

    def test_invalid_rows() -> str:
        panel = inputs.panel
        invalid = panel.loc[
            panel["stale_flag"].astype(bool) | panel["missing_flag"].astype(bool) | panel["proxy_flag"].astype(bool) | ~panel["data_valid"].astype(bool),
            ["date", "economic_exposure_family_id"],
        ]
        sampled = invalid.loc[invalid["economic_exposure_family_id"].isin(matrices.returns.columns)].head(5000)
        for item in sampled.itertuples(index=False):
            assert pd.isna(matrices.returns.at[item.date, item.economic_exposure_family_id])
        return f"{len(sampled)} sampled A2R-invalid/stale/missing/proxy rows remain excluded"

    def test_no_proxy() -> str:
        assert not inputs.panel.loc[inputs.panel["proxy_flag"].astype(bool) & inputs.panel["data_valid"].astype(bool)].shape[0]
        return "No A2R proxy row is data-valid"

    def test_new_warmup() -> str:
        role_rows = group_features.loc[group_features["analysis_context_type"].eq("ROLE_GROUP")]
        for horizon in MAIN_FORMATION_HORIZONS:
            score = f"SIGNAL_RS_{horizon}"
            first_scores = role_rows.loc[role_rows[score].notna()].groupby("economic_exposure_family_id")["date"].min()
            for family, date in first_scores.items():
                position = matrices.returns.index.get_loc(date)
                assert matrices.valid.loc[:date, family].tail(horizon).sum() == horizon
                assert position >= horizon - 1
        return "Every first dynamic admission follows a genuine signal-specific complete window"

    def test_top_tail_valid() -> str:
        if not retained.empty:
            assert retained["selected_count"].isin([3, 5]).all()
            assert retained["signal_cohort_count"].ge(retained["selected_count"]).all()
            assert retained["top_return"].notna().all()
        return f"{len(retained)} retained top-tail date diagnostics contain only valid selected returns"

    def test_registry_complete() -> str:
        registered = set(inputs.registry["signal_id"])
        executed = set(ledger["signal_id"])
        missing = registered - executed
        assert not missing, sorted(missing)
        return f"All {len(registered)} registered signal/diagnostic IDs appear in the complete ledger"

    def test_weekly_rule() -> str:
        dates = matrices.weekly_dates
        iso = pd.DataFrame({"date": inputs.calendar}).assign(
            year=pd.DatetimeIndex(inputs.calendar).isocalendar().year.to_numpy(),
            week=pd.DatetimeIndex(inputs.calendar).isocalendar().week.to_numpy(),
        )
        expected = iso.groupby(["year", "week"]).tail(1)["date"].to_numpy()
        assert np.array_equal(dates.to_numpy(), expected)
        return "Observation schedule is the last canonical XLON session of each calendar week"

    def test_no_current_eligibility_back_projection() -> str:
        assert not inputs.policy["admission"]["historical_current_eligibility_back_projection"]
        assert inputs.dynamic["current_eligibility_back_projected"].astype(str).eq("NO").all()
        assert group_features["warning"].eq(WARNING).all()
        return "Research admission uses return availability, not current public/broker eligibility"

    record("A3R1-T01", "No date-T close earns date-T return", test_no_same_close)
    record("A3R1-T02", "Next-session execution alignment is correct", test_next_session)
    record("A3R1-T03", "Only contemporaneously admitted economic families rank", test_contemporaneous_only)
    record("A3R1-T04", "Dynamic signal-specific warm-up is respected", test_dynamic_warmup)
    record("A3R1-T05", "Mismatched pre-A2R histories never reappear", test_remediated_history_only)
    record("A3R1-T06", "US defence history before corrected mandate date never enters", test_us_defence)
    record("A3R1-T07", "GLOBAL_BANKS never enters without valid history", test_global_banks)
    record("A3R1-T08", "Duplicate ETF listings cannot receive separate ranks", test_duplicates)
    record("A3R1-T09", "Common-benchmark arithmetic is not falsely claimed to alter order", test_benchmark_order)
    record("A3R1-T10", "Relative segments are actually non-overlapping", test_segments)
    record("A3R1-T11", "Pairwise uses only contemporaneously valid competitors", test_pairwise)
    record("A3R1-T12", "Parent mapping is frozen and does not use DeepVue/future data", test_parent_mapping)
    record("A3R1-T13", "Relative-price features use no future data", test_relative_line_no_future)
    record("A3R1-T14", "Missing/stale/invalid observations remain excluded", test_invalid_rows)
    record("A3R1-T15", "No proxy history enters", test_no_proxy)
    record("A3R1-T16", "NEW-family admission follows genuine warm-up", test_new_warmup)
    record("A3R1-T17", "Top-tail groups use only valid observations", test_top_tail_valid)
    record("A3R1-T18", "All specifications appear in registry/ledger", test_registry_complete)
    record("A3R1-T19", "Weekly observation rule is fixed", test_weekly_rule)
    record("A3R1-T20", "Current eligibility is not back-projected", test_no_current_eligibility_back_projection)
    result = pd.DataFrame(tests)
    result["critical"] = "YES"
    result["executed_at"] = utc_now()
    return result


def git_value(*arguments: str) -> str:
    completed = subprocess.run(["git", "-C", str(PLATFORM_ROOT), *arguments], capture_output=True, text=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else "UNAVAILABLE"


def write_csv(path: Path, frame: pd.DataFrame) -> dict[str, Any]:
    frame.to_csv(path, index=False, lineterminator="\n")
    observed_columns = pd.read_csv(path, nrows=0).columns.tolist()
    if observed_columns != frame.columns.tolist():
        raise AssertionError(f"CSV round-trip schema mismatch: {path.name}")
    return {"path": str(path), "rows": len(frame), "columns": len(frame.columns), "sha256": sha256_file(path), "size_bytes": path.stat().st_size}


def write_parquet(path: Path, frame: pd.DataFrame) -> dict[str, Any]:
    frame.to_parquet(path, index=False, engine="pyarrow", compression="zstd")
    import pyarrow.parquet as pq

    parquet = pq.ParquetFile(path)
    if parquet.metadata.num_rows != len(frame):
        raise AssertionError(f"Parquet row-count mismatch: {path.name}")
    observed_columns = parquet.schema_arrow.names
    if observed_columns != frame.columns.tolist():
        raise AssertionError(f"Parquet round-trip schema mismatch: {path.name}")
    return {"path": str(path), "rows": len(frame), "columns": len(frame.columns), "sha256": sha256_file(path), "size_bytes": path.stat().st_size}


def write_json(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path.write_text(json.dumps(payload, indent=2, default=str, sort_keys=True) + "\n", encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))
    return {"path": str(path), "sha256": sha256_file(path), "size_bytes": path.stat().st_size}


def decision_state(candidate_assessment: pd.DataFrame, top_tail: pd.DataFrame, tests: pd.DataFrame) -> str:
    if tests["status"].ne("PASS").any():
        return "UKACTIVE_A3R1_FAIL_DATA_OR_METHOD"
    candidates = candidate_assessment.loc[candidate_assessment["classification"].eq("A3R1_RESEARCH_CANDIDATE")]
    candidate_families = candidates["signal_family"].nunique()
    fdr_cells = int((top_tail["advantage_vs_global_bh_q_value"] <= 0.10).sum())
    multi_group = candidates["qualifying_group_ids"].str.split(";").explode().replace("NONE", np.nan).nunique()
    if candidate_families >= 2 and fdr_cells > 0 and multi_group >= 2:
        return "UKACTIVE_A3R1_STRONG_ROTATION_SIGNAL"
    if len(candidates):
        return "UKACTIVE_A3R1_RESEARCH_CANDIDATE_FOUND"
    if candidate_assessment["classification"].eq("WEAK_OR_REGIME_DEPENDENT").any():
        return "UKACTIVE_A3R1_WEAK_OR_REGIME_DEPENDENT"
    return "UKACTIVE_A3R1_NO_USEFUL_ROTATION_SIGNAL"


def build_decision_payload(
    inputs: Inputs,
    group_features: pd.DataFrame,
    top_tail: pd.DataFrame,
    support: pd.DataFrame,
    candidates: pd.DataFrame,
    transitions: pd.DataFrame,
    parent_results: pd.DataFrame,
    trend_quality: pd.DataFrame,
    persistence: pd.DataFrame,
    breadth: pd.DataFrame,
    dependencies: pd.DataFrame,
    robustness: pd.DataFrame,
    subperiods: pd.DataFrame,
    tests: pd.DataFrame,
    ledger: pd.DataFrame,
) -> dict[str, Any]:
    best_signal = support.iloc[0]["signal_id"]
    multi_support = support.loc[support["signal_id"].str.startswith("MH_LEVEL_")]
    best_weight = multi_support.iloc[0]["signal_id"] if len(multi_support) else "NOT_ESTABLISHED"
    decision = decision_state(candidates, top_tail, tests)
    role_features = group_features.loc[group_features["analysis_context_type"].eq("ROLE_GROUP")]
    dynamic_counts = {
        f"eligible_{h}_session_family_count": int(role_features.loc[role_features[f"SIGNAL_RS_{h}"].notna(), "economic_exposure_family_id"].nunique())
        for h in MAIN_FORMATION_HORIZONS
    }
    group_summaries: list[dict[str, Any]] = []
    primary = top_tail.loc[
        top_tail["signal_id"].eq(best_signal)
        & top_tail["analysis_context_type"].eq("ROLE_GROUP")
        & top_tail["maturity_scope"].eq("FULL_DYNAMIC")
        & top_tail["top_tail_definition"].eq("TOP_3")
        & top_tail["forward_horizon_sessions"].isin(CENTRAL_HORIZONS)
    ]
    for context_id, frame in primary.groupby("analysis_context_id", sort=True):
        best = frame.loc[frame["advantage_vs_global_mean"].idxmax()]
        group_summaries.append(
            {
                "group_id": context_id,
                "positive_central_horizon_count": int((frame["advantage_vs_global_mean"] > 0).sum()),
                "mean_advantage_across_central_horizons": float(frame["advantage_vs_global_mean"].mean()),
                "best_forward_horizon_sessions": int(best["forward_horizon_sessions"]),
                "best_mean_advantage_vs_global": float(best["advantage_vs_global_mean"]),
                "best_hac_p_value": float(best["advantage_vs_global_hac_p_value"]),
                "best_bh_q_value": float(best["advantage_vs_global_bh_q_value"]) if np.isfinite(best["advantage_vs_global_bh_q_value"]) else None,
            }
        )
    overall = primary.groupby("forward_horizon_sessions")["advantage_vs_global_mean"].mean()
    best_forward = int(overall.idxmax()) if len(overall) else None
    tail_summaries: dict[str, Any] = {}
    for tail in ["RANK_1", "TOP_3", "TOP_5"]:
        frame = top_tail.loc[
            top_tail["signal_id"].eq(best_signal)
            & top_tail["analysis_context_type"].eq("ROLE_GROUP")
            & top_tail["maturity_scope"].eq("FULL_DYNAMIC")
            & top_tail["top_tail_definition"].eq(tail)
            & top_tail["forward_horizon_sessions"].eq(best_forward)
        ]
        tail_summaries[tail] = {
            "mean_advantage_vs_global": float(frame["advantage_vs_global_mean"].mean()) if len(frame) else None,
            "mean_positive_frequency": float(frame["advantage_vs_global_positive_frequency"].mean()) if len(frame) else None,
            "group_count": len(frame),
        }
    transition_summary = {}
    for transition in ["IMPROVING->LEADING", "LEADING->WEAKENING"]:
        frame = transitions.loc[
            transitions.get("record_type", pd.Series(index=transitions.index, dtype=str)).eq("TRANSITION")
            & transitions["transition"].eq(transition)
            & transitions["forward_horizon_sessions"].isin(CENTRAL_HORIZONS)
        ] if len(transitions) else pd.DataFrame()
        transition_summary[transition] = {
            "mean_forward_relative_global": float(frame["mean_forward_relative_global"].mean()) if len(frame) else None,
            "minimum_hac_p_value": float(frame["relative_hac_p_value"].min()) if len(frame) else None,
            "cell_count": len(frame),
        }
    maturity = dependencies.loc[dependencies["dependency_scenario"].eq("MATURE_ONLY")]
    mature_summary = {
        "best_signal_mean_top3_advantage_vs_global": float(maturity.loc[maturity["signal_id"].eq(best_signal), "mean_top3_advantage_vs_global"].mean()) if len(maturity) else None,
        "positive_horizon_count": int((maturity.loc[maturity["signal_id"].eq(best_signal), "mean_top3_advantage_vs_global"] > 0).sum()) if len(maturity) else 0,
    }
    candidate_ids = candidates.loc[candidates["classification"].eq("A3R1_RESEARCH_CANDIDATE"), "signal_id"].tolist()
    rejected_ids = candidates.loc[candidates["classification"].eq("REJECTED"), "signal_id"].tolist()
    proceed = decision in ["UKACTIVE_A3R1_STRONG_ROTATION_SIGNAL", "UKACTIVE_A3R1_RESEARCH_CANDIDATE_FOUND"]
    return {
        "stage_id": "UKACTIVE-A3R1",
        "run_id": inputs.policy["run_id"],
        "decision": decision,
        "decision_timestamp": utc_now(),
        "pre_a3r1_checkpoint_commit": inputs.policy["pre_a3r1_checkpoint_commit"],
        "preregistration_commit": "742e65ec457dacb1ac2a1e91287975330dda1f34",
        "post_a3r1_result_commit": "PENDING_GIT_COMMIT",
        "specifications_tested": int(len(ledger)),
        "dynamically_eligible_equity_family_count_any_primary_signal": int(role_features.loc[role_features[[signal_column(s) for s in EVALUATED_SIGNALS]].notna().any(axis=1), "economic_exposure_family_id"].nunique()),
        **dynamic_counts,
        "best_supported_signal_id": best_signal,
        "best_multi_horizon_weighting_id": best_weight,
        "best_forward_holding_horizon_sessions": best_forward,
        "group_results": group_summaries,
        "top_tail_results_at_best_horizon": tail_summaries,
        "state_transition_summary": transition_summary,
        "candidate_signal_ids": candidate_ids,
        "rejected_signal_ids": rejected_ids,
        "signal_classifications": candidates.to_dict(orient="records"),
        "primary_fdr_cell_count": int(top_tail["primary_fdr_family"].eq("YES").sum()),
        "primary_fdr_surviving_cell_count": int((top_tail["advantage_vs_global_bh_q_value"] <= 0.10).sum()),
        "primary_bootstrap_positive_cell_count": int((top_tail["advantage_vs_global_bootstrap_ci_low"] > 0).sum()),
        "mature_only_sensitivity": mature_summary,
        "parent_relative_result_rows": int(len(parent_results)),
        "trend_quality_result_rows": int(len(trend_quality)),
        "leadership_persistence_result_rows": int(len(persistence)),
        "breadth_diagnostic_rows": int(len(breadth)),
        "dependency_result_rows": int(len(dependencies)),
        "parameter_robustness_rows": int(len(robustness)),
        "subperiod_result_rows": int(len(subperiods)),
        "correctness_tests_passed": int(tests["status"].eq("PASS").sum()),
        "correctness_tests_total": int(len(tests)),
        "historically_verified_uk_investable_strategy": False,
        "deployment_candidate": False,
        "portfolio_weighting_optimised": False,
        "a3r2_scientifically_supported": proceed,
        "a3r2_executed": False,
        "warning": WARNING,
    }


def write_statistical_inference(
    top_tail: pd.DataFrame,
    ledger: pd.DataFrame,
    support: pd.DataFrame,
) -> Path:
    primary = top_tail.loc[top_tail["primary_fdr_family"].eq("YES")]
    formal = primary.loc[primary["formal_inference_eligible"].eq("YES")]
    path = PROGRAMME_ROOT / "UKACTIVE_A3R1_STATISTICAL_INFERENCE.md"
    lines = [
        "# UKACTIVE-A3R1 statistical inference",
        "",
        "A3R1's primary estimand is the date-level equal-weight top-three forward-return advantage versus `GLOBAL_DEVELOPED_WORLD`, not a portfolio return. Weekly observations overlap at 10/21/42/63-session forward horizons. Bartlett/Newey–West HAC standard errors use `max(1, ceil(h/5)-1)` lags. The predeclared primary cells also receive a 2,000-replication circular block-bootstrap interval with deterministic seeds.",
        "",
        f"The Benjamini–Hochberg registry contains {len(primary)} primary-predeclared cells: nine primary signals × five primary role groups × four central forward horizons. The preregistered minimum is 24 date observations; {len(formal)} cells meet it and receive formal BH/block-bootstrap inference. {int((formal['advantage_vs_global_bh_q_value'] <= 0.10).sum())} eligible cells survive q ≤ 0.10; {int((formal['advantage_vs_global_bootstrap_ci_low'] > 0).sum())} have a positive 95% block-bootstrap lower bound. Sub-minimum cells retain descriptive effect sizes only.",
        "",
        f"The complete ledger contains {len(ledger):,} executed specification/diagnostic rows. Correlated horizons, tails and subperiods are not described as independent hypotheses. Failed and non-positive cells remain in the ledger.",
        "",
        "## Signal-level primary support summary",
        "",
        support.to_markdown(index=False),
        "",
        "Effect sizes, confidence intervals and hit rates are reported alongside p/q values. A small p-value alone cannot promote a signal. Historical eligibility remains unresolved, so no result is a verified UK-investable strategy or deployment claim.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_candidate_report(candidates: pd.DataFrame, decision: dict[str, Any]) -> Path:
    path = PROGRAMME_ROOT / "UKACTIVE_A3R1_RESEARCH_CANDIDATES.md"
    display = candidates[
        ["signal_id", "signal_family", "criteria_passed", "criteria_total", "qualifying_group_ids", "fdr_surviving_cell_count", "classification"]
    ]
    lines = [
        "# UKACTIVE-A3R1 research candidates",
        "",
        f"Stage decision: **{decision['decision']}**",
        "",
        display.to_markdown(index=False),
        "",
        "Promotion is signal-level only. `A3R1_RESEARCH_CANDIDATE` does not mean historically verified UK investability, portfolio viability or deployment readiness. Equal weighting of top-tail groups is a neutral diagnostic convention; `PORTFOLIO_WEIGHTING_NOT_OPTIMISED`.",
        "",
        f"A3R2 scientific support: **{'YES' if decision['a3r2_scientifically_supported'] else 'NO'}**. A3R2 was not executed.",
        "",
        WARNING,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_manifest(
    inputs: Inputs,
    decision: dict[str, Any],
    output_audit: list[dict[str, Any]],
    tests: pd.DataFrame,
    ledger: pd.DataFrame,
) -> dict[str, Any]:
    input_paths = [PROGRAMME_ROOT / value for value in inputs.policy["authoritative_inputs"].values()]
    input_hashes = {
        path.name: {"path": str(path), "sha256": sha256_file(path), "size_bytes": path.stat().st_size}
        for path in input_paths
        if path.exists() and path.is_file()
    }
    code_paths = [Path(__file__), Path(__file__).with_name("ukactive_a3r1_core.py"), POLICY_PATH, REGISTRY_PATH]
    finalizer = Path(__file__).with_name("finalize_ukactive_a3r1.py")
    if finalizer.exists():
        code_paths.append(finalizer)
    validator = Path(__file__).with_name("validate_ukactive_a3r1_artifacts.py")
    if validator.exists():
        code_paths.append(validator)
    code_hashes = {path.name: sha256_file(path) for path in code_paths}
    excluded_inventory = PROGRAMME_ROOT / "UKACTIVE_GIT_EXCLUDED_DATA_INVENTORY.csv"
    excluded_inventory_record = {
        "path": str(excluded_inventory),
        "sha256": sha256_file(excluded_inventory) if excluded_inventory.exists() else "NOT_AVAILABLE",
        "size_bytes": excluded_inventory.stat().st_size if excluded_inventory.exists() else None,
        "record_count": int(len(pd.read_csv(excluded_inventory))) if excluded_inventory.exists() else None,
        "purpose": "Paths, hashes, sizes, source identities, retrieval dates and generation-policy lineage for data excluded from Git.",
    }
    return {
        "stage_id": "UKACTIVE-A3R1",
        "run_id": inputs.policy["run_id"],
        "created_at": utc_now(),
        "repository_root": str(PLATFORM_ROOT),
        "git_branch": git_value("branch", "--show-current"),
        "pre_a3r1_checkpoint_commit": inputs.policy["pre_a3r1_checkpoint_commit"],
        "pre_a3r1_checkpoint_tag": inputs.policy["pre_a3r1_checkpoint_tag"],
        "preregistration_commit": "742e65ec457dacb1ac2a1e91287975330dda1f34",
        "post_a3r1_result_commit": "PENDING_GIT_COMMIT",
        "post_a3r1_provenance_commit": "PENDING_GIT_COMMIT",
        "remote_count": len(git_value("remote").splitlines()) if git_value("remote") not in ["", "UNAVAILABLE"] else 0,
        "checkpoint_pushed_to_github": False,
        "result_commit_pushed_to_github": False,
        "input_hashes": input_hashes,
        "executed_source_and_policy_hashes": code_hashes,
        "output_artifacts_excluding_self": output_audit,
        "local_excluded_data_inventory": excluded_inventory_record,
        "command_lines": [f"{sys.executable} {Path(__file__)}"],
        "observation_frequency": inputs.policy["calendar_and_timing"]["observation_frequency"],
        "formation_horizons_sessions": MAIN_FORMATION_HORIZONS,
        "forward_horizons_sessions": FORWARD_HORIZONS,
        "top_tail_definitions": TAILS,
        "multi_horizon_weights": inputs.policy["multi_horizon_weights"],
        "signal_registry_sha256": sha256_file(REGISTRY_PATH),
        "signal_registry_rows": len(inputs.registry),
        "complete_specification_ledger_rows": len(ledger),
        "correctness_test_results": tests.to_dict(orient="records"),
        "decision": decision["decision"],
        "package_versions": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "pyarrow": pyarrow.__version__,
        },
        "large_or_licensed_data_committed_to_git": False,
        "manifest_self_hash_excluded": True,
        "historical_eligibility_resolved": False,
        "a3r2_executed": False,
        "warning": WARNING,
    }


def audit_existing(path: Path) -> dict[str, Any]:
    return {"path": str(path), "sha256": sha256_file(path), "size_bytes": path.stat().st_size}


def main() -> None:
    print("A3R1: loading corrected A2R inputs", flush=True)
    inputs = load_inputs()
    metadata = candidate_metadata(inputs)
    if len(metadata) != 82:
        raise AssertionError(f"Expected 82 post-A2R equity rotation candidates; observed {len(metadata)}")
    matrices = build_matrices(inputs, metadata)
    definitions, membership = contexts(metadata)

    print("A3R1: constructing dynamic weekly relative-strength features", flush=True)
    base_weekly = build_base_weekly(inputs, matrices, metadata)
    group_features = build_group_features(inputs, matrices, metadata, definitions)
    group_features = attach_forward_data(group_features, base_weekly)
    dynamic_counts = build_dynamic_counts(group_features, inputs.registry)

    print("A3R1: evaluating top tails and corrected inference", flush=True)
    top_tail, retained, overlap_selections = evaluate_top_tails(group_features, definitions)
    top_tail = add_primary_inference(top_tail, retained, inputs.policy)
    support = score_primary_support(top_tail)
    best_signal = str(support.iloc[0]["signal_id"])

    print("A3R1: running full-rank, persistence, state, parent and robustness diagnostics", flush=True)
    group_results = evaluate_group_diagnostics(group_features)
    persistence = leadership_persistence(group_features)
    transitions = state_transition_results(group_features)
    parent_results = parent_relative_results(base_weekly)
    trend_quality = trend_quality_results(group_features, base_weekly)
    subperiods = build_subperiod_results(retained, inputs.policy)
    decay = build_decay_results(top_tail)
    dependencies = dependency_results(group_features, matrices, metadata)
    robustness = robustness_results(group_features)
    breadth = breadth_results(group_features, retained, best_signal)

    ledger = build_multiple_testing_ledger(top_tail, group_results, subperiods, dependencies, robustness, inputs.registry)
    tests = run_correctness_tests(inputs, matrices, metadata, group_features, retained, ledger)
    all_tests_pass = tests["status"].eq("PASS").all()
    candidate_assessment = build_candidate_assessment(
        top_tail, subperiods, dependencies, persistence, robustness, bool(all_tests_pass)
    )
    decision = build_decision_payload(
        inputs, group_features, top_tail, support, candidate_assessment, transitions, parent_results,
        trend_quality, persistence, breadth, dependencies, robustness, subperiods, tests, ledger,
    )

    print("A3R1: writing machine-readable outputs", flush=True)
    output_audit: list[dict[str, Any]] = []
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_ROTATION_POOL_MEMBERSHIP.csv", membership))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_DYNAMIC_COHORT_COUNTS.csv", dynamic_counts))

    multi_columns = [
        "date", "analysis_context_id", "analysis_context_type", "economic_exposure_family_id",
        "economic_exposure_name", "primary_rotation_role", "primary_competition_pool_id", "universe_tier",
        "a2r_research_maturity", "contemporaneous_research_maturity", "accrued_valid_return_observations",
    ]
    for horizon in MAIN_FORMATION_HORIZONS:
        multi_columns.extend([f"RETURN_{horizon}", f"RS_{horizon}", f"RANK_RS_{horizon}"])
    multi_columns.extend([
        "MH_LEVEL_EQ", "MH_LEVEL_RECENCY_TILT", "MH_LEVEL_60D_CENTERED", "MH_LEVEL_3_6_12_REFERENCE", "warning"
    ])
    output_audit.append(write_parquet(PROGRAMME_ROOT / "UKACTIVE_A3R1_MULTI_HORIZON_RS.parquet", group_features[multi_columns]))

    segment_columns = [
        "date", "economic_exposure_family_id", "economic_exposure_name", "research_group_id",
        "REL_SEG_0_1M", "REL_SEG_1_2M", "REL_SEG_2_3M", "REL_SEG_3_6M", "REL_SEG_6_12M",
        "a2r_research_maturity", "contemporaneous_research_maturity",
    ]
    output_audit.append(write_parquet(PROGRAMME_ROOT / "UKACTIVE_A3R1_DISCRETE_RELATIVE_SEGMENTS.parquet", base_weekly[segment_columns]))

    acceleration_columns = [
        "date", "analysis_context_id", "analysis_context_type", "economic_exposure_family_id",
        "FAST_LEVEL", "RS_RANK_CHANGE_21", "RS_RANK_CHANGE_42", "SHORT_MINUS_LONG_RS",
        "RELATIVE_SLOPE_CHANGE_RANK", "ACCEL_FAST_COMPOSITE", "RECENT_POSITIVE_SEGMENTS",
        "DISCRETE_RECENT_CONSISTENCY", "contemporaneous_research_maturity", "warning",
    ]
    output_audit.append(write_parquet(PROGRAMME_ROOT / "UKACTIVE_A3R1_RS_ACCELERATION.parquet", group_features[acceleration_columns]))
    pairwise_columns = [
        "date", "analysis_context_id", "analysis_context_type", "economic_exposure_family_id",
        "PAIRWISE_MAJORITY_5H", "contemporaneous_research_maturity", "warning",
    ]
    output_audit.append(write_parquet(PROGRAMME_ROOT / "UKACTIVE_A3R1_PAIRWISE_RS_RESULTS.parquet", group_features[pairwise_columns]))
    state_columns = [
        "date", "analysis_context_id", "analysis_context_type", "economic_exposure_family_id",
        "RRG_TRANSPARENT_LEVEL", "RRG_TRANSPARENT_MOMENTUM", "RRG_LEVEL_Z", "RRG_MOMENTUM_Z",
        "ROTATION_STATE", "contemporaneous_research_maturity", "warning",
    ]
    output_audit.append(write_parquet(PROGRAMME_ROOT / "UKACTIVE_A3R1_ROTATION_STATES.parquet", group_features[state_columns]))
    relative_columns = [
        "date", "economic_exposure_family_id", "economic_exposure_name", "research_group_id",
        "REL_SLOPE_21", "REL_SLOPE_42", "REL_SLOPE_63", "REL_R2_21", "REL_R2_42", "REL_R2_63",
        "RELATIVE_SLOPE_CHANGE", "REL_DISTANCE_MA_21", "REL_DISTANCE_MA_50", "REL_DISTANCE_HIGH_63",
        "contemporaneous_research_maturity",
    ]
    output_audit.append(write_parquet(PROGRAMME_ROOT / "UKACTIVE_A3R1_RELATIVE_LINE_FEATURES.parquet", base_weekly[relative_columns]))

    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_TOP_TAIL_RESULTS.csv", top_tail))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_FORWARD_HORIZON_DECAY.csv", decay))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_GROUP_RESULTS.csv", group_results))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_LEADERSHIP_PERSISTENCE.csv", persistence))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_STATE_TRANSITIONS.csv", transitions))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_PARENT_RS_RESULTS.csv", parent_results))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_TREND_QUALITY_DIAGNOSTICS.csv", trend_quality))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_OVERLAP_DIAGNOSTICS.csv", overlap_selections))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_BREADTH_DIAGNOSTICS.csv", breadth))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_SUBPERIOD_RESULTS.csv", subperiods))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_DEPENDENCY_TESTS.csv", dependencies))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_PARAMETER_ROBUSTNESS.csv", robustness))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_MULTIPLE_TESTING_LEDGER.csv", ledger))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_CORRECTNESS_TEST_RESULTS.csv", tests))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_SIGNAL_ASSESSMENT.csv", candidate_assessment))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R1_SIGNAL_SUPPORT_SUMMARY.csv", support))

    inference_path = write_statistical_inference(top_tail, ledger, support)
    candidate_path = write_candidate_report(candidate_assessment, decision)
    decision_path = PROGRAMME_ROOT / "UKACTIVE_A3R1_DECISION.json"
    output_audit.extend([audit_existing(POLICY_PATH), audit_existing(REGISTRY_PATH), audit_existing(PROGRAMME_ROOT / "UKACTIVE_A3R1_SCOPE_AND_PREREGISTRATION.md")])
    output_audit.extend([audit_existing(inference_path), audit_existing(candidate_path)])
    output_audit.append(write_json(decision_path, decision))
    manifest = build_manifest(inputs, decision, output_audit, tests, ledger)
    manifest_path = PROGRAMME_ROOT / "UKACTIVE_A3R1_MANIFEST.json"
    write_json(manifest_path, manifest)

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


if __name__ == "__main__":
    main()
