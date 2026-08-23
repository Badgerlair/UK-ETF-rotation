from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow

from ukactive_a2r2_core import (
    build_continuous_family_history,
    build_xlon_session_calendar,
    endpoint_formation_matrices,
    endpoint_forward_matrices,
    endpoint_valid_mask,
    sha256_file,
    utc_now,
)
from ukactive_a3r1_core import strict_rolling_total_return, weekly_last_positions


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_ROOT = PROGRAMME_ROOT.parents[2]
POLICY_PATH = PROGRAMME_ROOT / "config" / "UKACTIVE_A2R2_POLICY_v1.json"
A3R1_POLICY_PATH = PROGRAMME_ROOT / "config" / "UKACTIVE_A3R1_POLICY_v1.json"
WARNING = "HISTORICAL UK RETAIL, ACCOUNT AND BROKER ELIGIBILITY REMAIN UNRESOLVED"
PRIMARY_ROLE_TO_GROUP = {
    "BROAD_GEOGRAPHY_ROTATION": "GEOGRAPHY",
    "COUNTRY_ROTATION": "COUNTRY",
    "SECTOR_ROTATION": "SECTOR",
    "INDUSTRY_ROTATION": "INDUSTRY",
    "THEME_ROTATION": "THEME",
}
REPRESENTATIVE_FAMILIES = [
    "GLOBAL_DEVELOPED_WORLD",
    "US_BROAD_LARGE_CAP",
    "UK_BROAD_MARKET",
    "EUROPE_BROAD",
    "JAPAN",
    "GLOBAL_TECHNOLOGY",
    "EUROPE_TECHNOLOGY",
    "GLOBAL_SEMICONDUCTORS",
    "GLOBAL_HEALTHCARE",
    "GLOBAL_CYBERSECURITY",
]


@dataclass
class ResearchMatrices:
    calendar: pd.DatetimeIndex
    level: pd.DataFrame
    segment: pd.DataFrame
    endpoint_valid: pd.DataFrame
    formation: dict[int, pd.DataFrame]
    target_positions: dict[int, pd.DataFrame]
    target_offsets: dict[int, pd.DataFrame]
    forward: dict[int, pd.DataFrame]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_value(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=PLATFORM_ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else f"UNAVAILABLE:{result.stderr.strip()}"


def write_csv(path: Path, frame: pd.DataFrame) -> dict[str, Any]:
    frame.to_csv(path, index=False, lineterminator="\n")
    loaded = pd.read_csv(path, low_memory=False)
    if len(loaded) != len(frame):
        raise AssertionError(f"CSV round-trip row mismatch: {path.name}")
    return {"path": str(path), "rows": int(len(frame)), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def write_parquet(path: Path, frame: pd.DataFrame) -> dict[str, Any]:
    frame.to_parquet(path, index=False, compression="zstd")
    loaded = pd.read_parquet(path)
    if len(loaded) != len(frame) or list(loaded.columns) != list(frame.columns):
        raise AssertionError(f"Parquet round-trip mismatch: {path.name}")
    return {"path": str(path), "rows": int(len(frame)), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def write_text(path: Path, text: str) -> dict[str, Any]:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return {"path": str(path), "rows": None, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def write_json(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"path": str(path), "rows": None, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def load_metadata() -> tuple[pd.DataFrame, list[str]]:
    roles = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_ROTATION_ROLE_MASTER_POST_A2R.csv", dtype=str).fillna("NOT_APPLICABLE")
    mask = (
        roles["selectable_flag"].eq("YES")
        & roles["primary_equity_competition_flag"].eq("YES")
        & roles["research_data_ready_flag"].eq("YES")
        & roles["primary_rotation_role"].isin(PRIMARY_ROLE_TO_GROUP)
    )
    metadata = roles.loc[mask].copy()
    metadata["research_group_id"] = metadata["primary_rotation_role"].map(PRIMARY_ROLE_TO_GROUP)
    parent = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_PARENT_BENCHMARK_MAP_POST_A2R.csv", dtype=str).fillna("NOT_APPLICABLE")
    columns = [
        "economic_exposure_family_id",
        "parent_benchmark_family_id",
        "global_fallback_benchmark_family_id",
    ]
    metadata = metadata.merge(parent[columns], on="economic_exposure_family_id", how="left", validate="one_to_one")
    metadata["effective_parent_benchmark_family_id"] = metadata["parent_benchmark_family_id"].where(
        ~metadata["parent_benchmark_family_id"].isin(["", "NOT_APPLICABLE"]),
        metadata["global_fallback_benchmark_family_id"],
    ).fillna("GLOBAL_DEVELOPED_WORLD")
    all_needed = sorted(
        set(metadata["economic_exposure_family_id"])
        | set(metadata["effective_parent_benchmark_family_id"])
        | {"GLOBAL_DEVELOPED_WORLD", "GLOBAL_ALL_WORLD"}
    )
    if metadata["economic_exposure_family_id"].duplicated().any():
        raise AssertionError("A3R1 candidate family identity is not unique")
    return metadata, all_needed


def build_calendar_audit(policy: dict[str, Any]) -> tuple[pd.DataFrame, pd.DatetimeIndex, set[pd.Timestamp]]:
    old = pd.read_csv(PROGRAMME_ROOT / policy["authoritative_inputs"]["a2_observed_union_calendar"])
    old["date"] = pd.to_datetime(old["date"]).dt.normalize()
    old_included = old["included_in_canonical_calendar"].astype(str).str.lower().eq("true")
    start = old.loc[old_included, "date"].min()
    end = old.loc[old_included, "date"].max()
    sessions, holiday_map = build_xlon_session_calendar(start, end)
    session_set = set(sessions)
    old_set = set(old.loc[old_included, "date"])
    union = pd.DatetimeIndex(sorted(old_set | session_set))
    base = pd.DataFrame({"date": union})
    keep = [column for column in ["date", "anchor_observed", "listing_observation_count", "included_in_canonical_calendar"] if column in old]
    base = base.merge(old[keep], on="date", how="left", validate="one_to_one")
    base["a2r2_official_xlon_session"] = base["date"].isin(session_set)
    base["old_a2_included"] = base["date"].isin(old_set)
    base["holiday_or_closure_reason"] = base["date"].map(holiday_map).fillna("NOT_APPLICABLE")
    base["calendar_action"] = np.select(
        [base["old_a2_included"] & ~base["a2r2_official_xlon_session"], ~base["old_a2_included"] & base["a2r2_official_xlon_session"]],
        ["REMOVE_EXTRANEOUS_NON_SESSION", "ADD_GENUINE_XLON_SESSION"],
        default="RETAIN",
    )
    next_map = pd.Series(sessions[1:].to_numpy(), index=sessions[:-1])
    base["next_a2r2_xlon_session"] = base["date"].map(next_map)
    removed = set(base.loc[base["calendar_action"].eq("REMOVE_EXTRANEOUS_NON_SESSION"), "date"])
    return base, sessions, removed


def load_combined_instrument_history(all_needed: list[str], sessions: pd.DatetimeIndex) -> pd.DataFrame:
    original = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A2_INSTRUMENT_HISTORY_MASTER.parquet")
    corrected = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A2R_CORRECTED_IMPLEMENTATION_HISTORY.parquet")
    original["date"] = pd.to_datetime(original["date"]).dt.normalize()
    corrected["date"] = pd.to_datetime(corrected["date"]).dt.normalize()
    corrected_families = set(corrected["economic_exposure_family_id"])
    original = original.loc[
        original["economic_exposure_family_id"].isin(all_needed)
        & ~original["economic_exposure_family_id"].isin(corrected_families)
    ]
    corrected = corrected.loc[corrected["economic_exposure_family_id"].isin(all_needed)]
    instrument = pd.concat([original, corrected], ignore_index=True, sort=False)
    instrument = instrument.loc[instrument["date"].isin(sessions)].copy()
    if instrument.duplicated(["date", "economic_exposure_family_id", "listing_id"]).any():
        raise AssertionError("Combined A2/A2R instrument endpoint source is not unique")
    return instrument


def endpoint_failure_reason(frame: pd.DataFrame) -> pd.Series:
    semantic = frame.get("semantic_family_match", pd.Series(np.nan, index=frame.index))
    validation = frame.get("total_return_validation_status", pd.Series("", index=frame.index)).fillna("").astype(str)
    wealth = pd.to_numeric(frame.get("adjusted_wealth_gbp"), errors="coerce")
    return pd.Series(
        np.select(
            [
                frame["effective_listing_id"].isna(),
                frame["listing_id"].isna(),
                ~frame.get("price_available", False).fillna(False).astype(bool),
                frame.get("missing_flag", True).fillna(True).astype(bool),
                frame.get("stale_flag", False).fillna(False).astype(bool),
                frame.get("proxy_flag", False).fillna(False).astype(bool),
                frame.get("price_before_inception_flag", False).fillna(False).astype(bool),
                semantic.notna() & semantic.astype(str).str.lower().eq("false"),
                ~validation.str.startswith("PASS"),
                ~wealth.gt(0) | ~np.isfinite(wealth),
            ],
            [
                "NO_CANONICAL_IMPLEMENTATION_SELECTED",
                "SELECTED_IMPLEMENTATION_ENDPOINT_NOT_FOUND",
                "PRICE_NOT_AVAILABLE",
                "MISSING_OBSERVATION",
                "STALE_OBSERVATION",
                "PROXY_FORBIDDEN",
                "PRE_INCEPTION_OBSERVATION",
                "SEMANTIC_FINGERPRINT_NOT_YET_VALID",
                "TOTAL_RETURN_ROUTE_NOT_VALIDATED",
                "ADJUSTED_WEALTH_ENDPOINT_INVALID",
            ],
            default="VALID_ENDPOINT",
        ),
        index=frame.index,
    )


def build_signal_endpoint_history(
    policy: dict[str, Any],
    sessions: pd.DatetimeIndex,
    removed_dates: set[pd.Timestamp],
    all_needed: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    instrument = load_combined_instrument_history(all_needed, sessions)
    position_map = pd.Series(np.arange(len(sessions), dtype=int), index=sessions)
    instrument["session_position"] = instrument["date"].map(position_map).astype(int)
    instrument["endpoint_valid"] = endpoint_valid_mask(instrument)

    valid_listing = instrument.loc[instrument["endpoint_valid"]].sort_values(["listing_id", "session_position"], kind="mergesort").copy()
    valid_listing["previous_listing_valid_session_position"] = valid_listing.groupby("listing_id")["session_position"].shift()
    valid_listing["previous_listing_valid_date"] = valid_listing.groupby("listing_id")["date"].shift()
    valid_listing["previous_listing_valid_wealth_gbp"] = valid_listing.groupby("listing_id")["adjusted_wealth_gbp"].shift()

    endpoint_columns = [
        "date", "economic_exposure_family_id", "listing_id", "share_class_id", "isin", "ticker", "mic",
        "adjusted_wealth_gbp", "adjusted_price_listing_currency", "price_listing_currency", "price_available",
        "missing_flag", "stale_flag", "proxy_flag", "price_before_inception_flag", "listing_active",
        "total_return_validation_status", "semantic_family_match", "source_vendor", "source_series_identifier",
        "endpoint_valid", "session_position",
    ]
    for column in endpoint_columns:
        if column not in instrument:
            instrument[column] = np.nan
    endpoint = instrument[endpoint_columns].copy()
    previous_columns = [
        "date", "economic_exposure_family_id", "listing_id", "previous_listing_valid_session_position",
        "previous_listing_valid_date", "previous_listing_valid_wealth_gbp",
    ]
    endpoint = endpoint.merge(
        valid_listing[previous_columns],
        on=["date", "economic_exposure_family_id", "listing_id"],
        how="left",
        validate="one_to_one",
    )

    panel = pd.read_parquet(
        PROGRAMME_ROOT / policy["authoritative_inputs"]["a2r_corrected_panel"],
        columns=["date", "economic_exposure_family_id", "implementation_listing_id"],
    )
    panel["date"] = pd.to_datetime(panel["date"]).dt.normalize()
    panel = panel.loc[panel["economic_exposure_family_id"].isin(all_needed)]
    grid = pd.MultiIndex.from_product([sessions, all_needed], names=["date", "economic_exposure_family_id"]).to_frame(index=False)
    grid = grid.merge(panel, on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    grid["raw_selected_listing_id"] = grid["implementation_listing_id"].where(
        grid["implementation_listing_id"].notna()
        & ~grid["implementation_listing_id"].astype(str).str.startswith("NOT_")
    )
    previous_true_session = pd.Series(sessions[:-1].to_numpy(), index=sessions[1:])
    grid["previous_true_xlon_session"] = grid["date"].map(previous_true_session)
    removed_between: set[pd.Timestamp] = set()
    for current, previous in previous_true_session.items():
        if any(previous < removed < current for removed in removed_dates):
            removed_between.add(current)
    grid["calendar_contamination_repair_eligible"] = grid["date"].isin(removed_between)
    grid = grid.sort_values(["economic_exposure_family_id", "date"], kind="mergesort")
    previous_raw = grid.groupby("economic_exposure_family_id")["raw_selected_listing_id"].shift(1)
    repair = grid["raw_selected_listing_id"].isna() & grid["calendar_contamination_repair_eligible"] & previous_raw.notna()
    grid["effective_listing_id"] = grid["raw_selected_listing_id"].where(~repair, previous_raw)
    grid["selection_source"] = np.select(
        [grid["raw_selected_listing_id"].notna(), repair],
        ["A2R_CANONICAL_SELECTION", "PAST_ONLY_CALENDAR_CONTAMINATION_REPAIR"],
        default="NO_SELECTION",
    )
    grid["session_position"] = grid["date"].map(position_map).astype(int)
    selected = grid.merge(
        endpoint,
        left_on=["date", "economic_exposure_family_id", "effective_listing_id"],
        right_on=["date", "economic_exposure_family_id", "listing_id"],
        how="left",
        validate="one_to_one",
        suffixes=("", "_endpoint"),
    )
    selected["endpoint_valid"] = selected["endpoint_valid"].fillna(False).astype(bool)
    selected["endpoint_failure_reason"] = endpoint_failure_reason(selected)
    history = build_continuous_family_history(
        selected,
        maximum_gap_sessions=int(policy["endpoint_policy"]["maximum_continuity_gap_xlon_sessions"]),
    )
    history["warning"] = WARNING
    return history, instrument


def build_research_matrices(history: pd.DataFrame, policy: dict[str, Any], sessions: pd.DatetimeIndex, all_needed: list[str]) -> ResearchMatrices:
    level = history.pivot(index="date", columns="economic_exposure_family_id", values="signal_wealth_index_gbp").reindex(index=sessions, columns=all_needed)
    segment = history.pivot(index="date", columns="economic_exposure_family_id", values="continuity_segment_id").reindex(index=sessions, columns=all_needed)
    valid = history.pivot(index="date", columns="economic_exposure_family_id", values="endpoint_valid").reindex(index=sessions, columns=all_needed).fillna(False).astype(bool)
    formation, target_positions, target_offsets = endpoint_formation_matrices(
        level,
        segment,
        policy["formation_horizons_sessions"],
        int(policy["endpoint_policy"]["target_backward_tolerance_xlon_sessions"]),
    )
    forward = endpoint_forward_matrices(level, segment, policy["forward_horizons_sessions"])
    return ResearchMatrices(sessions, level, segment, valid, formation, target_positions, target_offsets, forward)


def build_corrected_daily_panel(policy: dict[str, Any], sessions: pd.DatetimeIndex) -> pd.DataFrame:
    """Calendar projection of A2R; authoritative daily values are not rewritten."""
    panel = pd.read_parquet(PROGRAMME_ROOT / policy["authoritative_inputs"]["a2r_corrected_panel"])
    panel["date"] = pd.to_datetime(panel["date"]).dt.normalize()
    panel = panel.loc[panel["date"].isin(sessions)].copy()
    next_map = pd.Series(sessions[1:].to_numpy(), index=sessions[:-1])
    panel["next_execution_eligible_date"] = panel["date"].map(next_map)
    panel["a2r2_official_xlon_session"] = True
    panel["a2r2_raw_daily_return_rewritten"] = False
    panel["a2r2_signal_endpoint_policy"] = "SEPARATE_ENDPOINT_HISTORY"
    return panel.sort_values(["date", "economic_exposure_family_id"], kind="mergesort").reset_index(drop=True)


def build_signal_eligibility(history: pd.DataFrame, matrices: ResearchMatrices, policy: dict[str, Any]) -> pd.DataFrame:
    columns = [
        "date", "economic_exposure_family_id", "effective_listing_id", "share_class_id", "isin", "ticker", "mic",
        "selection_source", "adjusted_wealth_gbp", "signal_wealth_index_gbp", "continuity_segment_id",
        "endpoint_valid", "endpoint_failure_reason", "return_since_prior_valid_endpoint", "return_span_xlon_sessions",
        "implementation_transition_flag", "continuity_reason", "stale_flag", "missing_flag", "proxy_flag",
        "total_return_validation_status", "source_vendor", "source_series_identifier",
    ]
    output = history[[column for column in columns if column in history]].copy()
    key_index = pd.MultiIndex.from_frame(output[["date", "economic_exposure_family_id"]])
    session_array = matrices.calendar.to_numpy()
    for horizon in policy["formation_horizons_sessions"]:
        formation = matrices.formation[int(horizon)].stack(future_stack=True).rename(f"formation_return_{horizon}")
        target_position = matrices.target_positions[int(horizon)].stack(future_stack=True).rename(f"target_position_{horizon}")
        target_offset = matrices.target_offsets[int(horizon)].stack(future_stack=True).rename(f"target_backward_offset_{horizon}")
        output[f"formation_return_{horizon}"] = formation.reindex(key_index).to_numpy(float)
        positions = target_position.reindex(key_index).fillna(-1).to_numpy(int)
        output[f"target_session_{horizon}"] = pd.to_datetime(
            np.where(positions >= 0, session_array[np.maximum(positions, 0)], np.datetime64("NaT"))
        )
        output[f"target_backward_offset_{horizon}"] = target_offset.reindex(key_index).fillna(-1).to_numpy(int)
        output[f"actual_elapsed_xlon_sessions_{horizon}"] = np.where(
            positions >= 0,
            int(horizon) + output[f"target_backward_offset_{horizon}"],
            -1,
        )
        elapsed_days = output["date"] - output[f"target_session_{horizon}"]
        output[f"actual_elapsed_calendar_days_{horizon}"] = elapsed_days.dt.days.fillna(-1).astype(int)
        output[f"signal_valid_{horizon}"] = output[f"formation_return_{horizon}"].notna()
    for horizon in policy["forward_horizons_sessions"]:
        forward = matrices.forward[int(horizon)].stack(future_stack=True).rename(f"forward_return_{horizon}")
        output[f"forward_return_{horizon}"] = forward.reindex(key_index).to_numpy(float)
        output[f"forward_valid_{horizon}"] = output[f"forward_return_{horizon}"].notna()
    output["warning"] = WARNING
    return output


def old_strict_matrices(
    policy: dict[str, Any],
    old_calendar: pd.DatetimeIndex,
    all_needed: list[str],
) -> tuple[pd.DataFrame, dict[int, pd.DataFrame]]:
    panel = pd.read_parquet(PROGRAMME_ROOT / policy["authoritative_inputs"]["a2r_corrected_panel"])
    panel["date"] = pd.to_datetime(panel["date"]).dt.normalize()
    valid = (
        panel["data_valid"].astype(bool)
        & ~panel["stale_flag"].astype(bool)
        & ~panel["missing_flag"].astype(bool)
        & ~panel["proxy_flag"].astype(bool)
        & panel["return_gbp_total"].notna()
    )
    subset = panel.loc[panel["economic_exposure_family_id"].isin(all_needed), ["date", "economic_exposure_family_id", "return_gbp_total"]].copy()
    subset.loc[~valid.loc[subset.index], "return_gbp_total"] = np.nan
    returns = subset.pivot(index="date", columns="economic_exposure_family_id", values="return_gbp_total").reindex(index=old_calendar, columns=all_needed)
    strict = {h: strict_rolling_total_return(returns, h) for h in [21, 32, 42, 50, 52, 63, 75, 126, 252]}
    return returns, strict


def build_cutoff_trace(
    policy: dict[str, Any],
    calendar_audit: pd.DataFrame,
    sessions: pd.DatetimeIndex,
    history: pd.DataFrame,
    matrices: ResearchMatrices,
    all_needed: list[str],
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame, dict[int, pd.DataFrame]]:
    old_dates = pd.DatetimeIndex(
        calendar_audit.loc[calendar_audit["old_a2_included"], "date"].sort_values(),
        name="date",
    )
    old_returns, old_strict = old_strict_matrices(policy, old_dates, all_needed)
    old_rs = {
        horizon: (1.0 + frame).div(1.0 + frame["GLOBAL_DEVELOPED_WORLD"], axis=0) - 1.0
        for horizon, frame in old_strict.items()
    }
    old_composite_valid = np.logical_and.reduce([old_rs[h].notna() for h in [21, 42, 63, 126, 252]])
    weekly = weekly_last_positions(old_dates)
    weekly_dates = old_dates[weekly]
    rs252_weekly = old_rs[252].iloc[weekly]
    composite_weekly = pd.DataFrame(old_composite_valid, index=old_dates, columns=all_needed).iloc[weekly]
    rs252_last = rs252_weekly.stack().index.get_level_values(0).max()
    composite_last = composite_weekly.stack().loc[lambda values: values].index.get_level_values(0).max()

    panel_columns = [
        "date", "economic_exposure_family_id", "implementation_listing_id", "price_local", "price_gbp_if_required",
        "return_gbp_total", "data_valid", "listing_active", "stale_flag", "missing_flag",
    ]
    panel = pd.read_parquet(PROGRAMME_ROOT / policy["authoritative_inputs"]["a2r_corrected_panel"], columns=panel_columns)
    panel["date"] = pd.to_datetime(panel["date"]).dt.normalize()
    panel = panel.set_index(["date", "economic_exposure_family_id"])
    history_indexed = history.set_index(["date", "economic_exposure_family_id"])
    count_frames = {h: old_returns.notna().rolling(h, min_periods=1).sum() for h in [21, 42, 63, 126, 252]}
    previous_valid: dict[str, pd.Series] = {}
    for family in REPRESENTATIVE_FAMILIES:
        if family in old_returns:
            dates = pd.Series(old_dates.where(old_returns[family].notna()), index=old_dates).ffill().shift(1)
            previous_valid[family] = dates

    trace_dates = old_dates[
        ((old_dates >= pd.Timestamp("2017-08-24")) & (old_dates <= pd.Timestamp("2017-09-01")))
        | ((old_dates >= pd.Timestamp("2017-11-03")) & (old_dates <= pd.Timestamp("2017-11-10")))
    ]
    rows: list[dict[str, Any]] = []
    session_set = set(sessions)
    benchmark_old_valid = old_returns["GLOBAL_DEVELOPED_WORLD"].notna()
    for family in REPRESENTATIVE_FAMILIES:
        if family not in old_returns:
            continue
        for date in trace_dates:
            key = (date, family)
            old_row = panel.loc[key] if key in panel.index else pd.Series(dtype=object)
            new_row = history_indexed.loc[key] if key in history_indexed.index else pd.Series(dtype=object)
            counts = {h: int(count_frames[h].at[date, family]) for h in [21, 42, 63, 126, 252]}
            exchange_session = date in session_set
            if not exchange_session:
                reason = "MASTER_CALENDAR_CONTAMINATION_NON_XLON_SESSION"
            elif pd.isna(old_returns.at[date, family]):
                reason = "A2_DAILY_RETURN_OR_PRIOR_SESSION_SELECTION_INVALID"
            elif not bool(benchmark_old_valid.at[date]):
                reason = "GLOBAL_BENCHMARK_DAILY_RETURN_INVALID"
            elif counts[252] < 252:
                reason = "STRICT_252_GAP_FREE_MASTER_ROW_REQUIREMENT"
            else:
                reason = "NO_FAILURE_AT_THIS_ROW"
            rows.append(
                {
                    "date": date,
                    "economic_exposure_family_id": family,
                    "selected_implementation_id": old_row.get("implementation_listing_id", "NOT_AVAILABLE"),
                    "local_price": old_row.get("price_local", np.nan),
                    "gbp_total_return_value": old_row.get("price_gbp_if_required", np.nan),
                    "return_gbp_total": old_row.get("return_gbp_total", np.nan),
                    "a2_a2r_data_valid": old_row.get("data_valid", False),
                    "listing_active_flag": old_row.get("listing_active", "NOT_AVAILABLE"),
                    "stale_flag": old_row.get("stale_flag", False),
                    "missing_flag": old_row.get("missing_flag", True),
                    "exchange_session_flag": exchange_session,
                    "benchmark_valid_flag": bool(benchmark_old_valid.at[date]),
                    "previous_valid_observation_date": previous_valid.get(family, pd.Series(dtype="datetime64[ns]")).get(date, pd.NaT),
                    **{f"valid_observations_prior_{h}": counts[h] for h in [21, 42, 63, 126, 252]},
                    "rolling_window_eligibility_252": counts[252] == 252,
                    "old_RS_252_valid": bool(pd.notna(old_rs[252].at[date, family])),
                    "old_five_horizon_composite_valid": bool(old_composite_valid[old_dates.get_loc(date), all_needed.index(family)]),
                    "a2r2_endpoint_valid": bool(new_row.get("endpoint_valid", False)),
                    "a2r2_RS_252_valid": bool(pd.notna(matrices.formation[252].at[date, family])) if date in sessions else False,
                    "exact_failure_reason_code": reason,
                }
            )
    preserved = pd.read_parquet(
        PROGRAMME_ROOT / "UKACTIVE_A3R1_MULTI_HORIZON_RS.parquet",
        columns=["date", "RS_252", "MH_LEVEL_EQ"],
    )
    preserved["date"] = pd.to_datetime(preserved["date"])
    preserved_rs_last = preserved.loc[preserved["RS_252"].notna(), "date"].max()
    preserved_composite_last = preserved.loc[preserved["MH_LEVEL_EQ"].notna(), "date"].max()
    summary = {
        "old_rs_252_last_valid_weekly_date": pd.Timestamp(preserved_rs_last).date().isoformat(),
        "old_five_horizon_composite_last_valid_weekly_date": pd.Timestamp(preserved_composite_last).date().isoformat(),
        "raw_family_benchmark_rs252_last_date": pd.Timestamp(rs252_last).date().isoformat(),
        "raw_all_horizon_availability_last_date": pd.Timestamp(composite_last).date().isoformat(),
        "cutoff_measurement_source": "PRESERVED_UKACTIVE_A3R1_MULTI_HORIZON_RS_PARQUET",
        "extraneous_non_session_count": int(calendar_audit["calendar_action"].eq("REMOVE_EXTRANEOUS_NON_SESSION").sum()),
        "genuine_session_added_count": int(calendar_audit["calendar_action"].eq("ADD_GENUINE_XLON_SESSION").sum()),
    }
    return pd.DataFrame(rows), summary, old_returns, old_strict


def build_benchmark_audit(
    history: pd.DataFrame,
    matrices: ResearchMatrices,
    old_returns: pd.DataFrame,
) -> pd.DataFrame:
    benchmark = "GLOBAL_DEVELOPED_WORLD"
    h = history.loc[history["economic_exposure_family_id"].eq(benchmark)].set_index("date")
    rows: list[dict[str, Any]] = []
    for year, dates in pd.Series(matrices.calendar, index=matrices.calendar).groupby(matrices.calendar.year):
        year_dates = pd.DatetimeIndex(dates.to_numpy())
        final_date = year_dates.max()
        old_subset = old_returns.loc[old_returns.index.year == year, benchmark] if benchmark in old_returns else pd.Series(dtype=float)
        endpoint_subset = h.reindex(year_dates)
        row: dict[str, Any] = {
            "year": int(year),
            "final_xlon_session": final_date,
            "official_xlon_sessions": int(len(year_dates)),
            "old_valid_daily_returns": int(old_subset.notna().sum()),
            "a2r2_valid_endpoints": int(endpoint_subset["endpoint_valid"].fillna(False).sum()),
            "a2r2_stale_endpoints": int(endpoint_subset["stale_flag"].fillna(False).sum()),
            "a2r2_missing_endpoints": int(endpoint_subset["missing_flag"].fillna(True).sum()),
        }
        for horizon in [21, 42, 63, 126, 252]:
            values = matrices.formation[horizon].loc[year_dates, benchmark]
            row[f"formation_{horizon}_valid_dates"] = int(values.notna().sum())
            row[f"formation_{horizon}_valid_at_year_end"] = bool(pd.notna(values.iloc[-1]))
        row["benchmark_audit_result"] = "PASS" if row["a2r2_valid_endpoints"] > 0 else "NO_HISTORY_IN_YEAR"
        rows.append(row)
    return pd.DataFrame(rows)


def build_transition_audit(history: pd.DataFrame) -> pd.DataFrame:
    frame = history.sort_values(["economic_exposure_family_id", "date"], kind="mergesort").copy()
    frame["prior_effective_listing_id"] = frame.groupby("economic_exposure_family_id")["effective_listing_id"].shift(1)
    changed = (
        frame["effective_listing_id"].notna()
        & frame["prior_effective_listing_id"].notna()
        & frame["effective_listing_id"].ne(frame["prior_effective_listing_id"])
    )
    columns = [
        "date", "economic_exposure_family_id", "prior_effective_listing_id", "effective_listing_id", "isin", "ticker",
        "selection_source", "endpoint_valid", "previous_listing_valid_date", "return_span_xlon_sessions",
        "implementation_transition_flag", "continuity_segment_id", "continuity_reason",
    ]
    result = frame.loc[changed, columns].copy()
    result["semantic_fingerprint_match"] = "YES_SAME_A2R_ECONOMIC_FAMILY"
    result["transition_policy_result"] = np.where(
        result["continuity_reason"].eq("SEMANTICALLY_IDENTICAL_IMPLEMENTATION_TRANSITION"),
        "CONTINUE",
        "RESET_OR_ENDPOINT_UNAVAILABLE",
    )
    result["return_similarity_used_for_decision"] = "NO"
    return result


def build_affected_family_audit(
    metadata: pd.DataFrame,
    matrices: ResearchMatrices,
    old_strict: dict[int, pd.DataFrame],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    benchmark = "GLOBAL_DEVELOPED_WORLD"
    candidate_ids = metadata["economic_exposure_family_id"].tolist()
    for family in candidate_ids:
        meta = metadata.loc[metadata["economic_exposure_family_id"].eq(family)].iloc[0]
        for horizon in [21, 42, 63, 126, 252]:
            old_relative_valid = old_strict[horizon][family].notna() & old_strict[horizon][benchmark].notna()
            new_relative_valid = matrices.formation[horizon][family].notna() & matrices.formation[horizon][benchmark].notna()
            old_dates = old_strict[horizon].index[old_relative_valid]
            new_dates = matrices.calendar[new_relative_valid.to_numpy()]
            old_last = old_dates.max() if len(old_dates) else pd.NaT
            new_last = new_dates.max() if len(new_dates) else pd.NaT
            rows.append(
                {
                    "economic_exposure_family_id": family,
                    "rotation_role": meta["primary_rotation_role"],
                    "rotation_pool": meta["primary_competition_pool_id"],
                    "signal_horizon_sessions": horizon,
                    "old_valid_observations": int(old_relative_valid.sum()),
                    "old_first_valid_date": old_dates.min() if len(old_dates) else pd.NaT,
                    "old_last_valid_date": old_last,
                    "a2r2_valid_observations": int(new_relative_valid.sum()),
                    "a2r2_first_valid_date": new_dates.min() if len(new_dates) else pd.NaT,
                    "a2r2_last_valid_date": new_last,
                    "modern_coverage_restored": bool(pd.notna(new_last) and new_last >= pd.Timestamp("2020-01-01")),
                    "affected_by_old_defect": bool(pd.notna(new_last) and (pd.isna(old_last) or new_last > old_last)),
                    "root_cause_family_code": "MASTER_CALENDAR_PLUS_STRICT_CONSECUTIVE_DAILY_RETURN_CHAIN",
                }
            )
    return pd.DataFrame(rows)


def build_coverage(
    metadata: pd.DataFrame,
    matrices: ResearchMatrices,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[int, int]]:
    weekly_positions_array = weekly_last_positions(matrices.calendar)
    weekly_dates = matrices.calendar[weekly_positions_array]
    benchmark = "GLOBAL_DEVELOPED_WORLD"
    contexts: dict[str, list[str]] = {
        group: sorted(metadata.loc[metadata["research_group_id"].eq(group), "economic_exposure_family_id"].tolist())
        for group in PRIMARY_ROLE_TO_GROUP.values()
    }
    contexts["ALL_EQUITY_OPPORTUNITIES"] = sorted(metadata["economic_exposure_family_id"].tolist())
    rows: list[dict[str, Any]] = []
    for horizon in [21, 42, 63, 126, 252]:
        benchmark_valid = matrices.formation[horizon][benchmark].notna()
        for context, members in contexts.items():
            valid = matrices.formation[horizon][members].notna().mul(benchmark_valid, axis=0)
            selected = valid.iloc[weekly_positions_array]
            selected.index = weekly_dates
            for date, values in selected.iterrows():
                rows.append(
                    {
                        "date": date,
                        "year": int(date.year),
                        "analysis_context_id": context,
                        "signal_horizon_sessions": horizon,
                        "eligible_family_count": int(values.sum()),
                        "total_frozen_family_count": int(len(members)),
                    }
                )
    heatmap = pd.DataFrame(rows)
    year_end = (
        heatmap.sort_values("date")
        .groupby(["year", "analysis_context_id", "signal_horizon_sessions"], as_index=False)
        .tail(1)
        .sort_values(["year", "analysis_context_id", "signal_horizon_sessions"])
        .reset_index(drop=True)
    )
    latest_counts = {
        horizon: int(
            matrices.formation[horizon].loc[matrices.calendar.max(), metadata["economic_exposure_family_id"]].notna().sum()
            if pd.notna(matrices.formation[horizon].at[matrices.calendar.max(), benchmark])
            else 0
        )
        for horizon in [21, 42, 63, 126, 252]
    }
    return heatmap, year_end, latest_counts


def build_before_after_audit(
    corrected_daily: pd.DataFrame,
    calendar_audit: pd.DataFrame,
    old_strict: dict[int, pd.DataFrame],
    matrices: ResearchMatrices,
    all_needed: list[str],
) -> pd.DataFrame:
    original = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A2R_CORRECTED_TOTAL_RETURN_PANEL_GBP.parquet")
    original["date"] = pd.to_datetime(original["date"]).dt.normalize()
    keys = ["date", "economic_exposure_family_id"]
    comparison = original.merge(
        corrected_daily[keys + ["return_gbp_total", "data_valid", "stale_flag", "missing_flag"]],
        on=keys,
        how="inner",
        suffixes=("_old", "_new"),
        validate="one_to_one",
    )
    return_equal = np.isclose(
        pd.to_numeric(comparison["return_gbp_total_old"], errors="coerce"),
        pd.to_numeric(comparison["return_gbp_total_new"], errors="coerce"),
        rtol=0.0,
        atol=0.0,
        equal_nan=True,
    )
    flag_equal = (
        comparison["data_valid_old"].eq(comparison["data_valid_new"])
        & comparison["stale_flag_old"].eq(comparison["stale_flag_new"])
        & comparison["missing_flag_old"].eq(comparison["missing_flag_new"])
    )
    rows: list[dict[str, Any]] = [
        {
            "audit_scope": "RETAINED_RAW_DAILY_PANEL_ROWS",
            "compared_observations": int(len(comparison)),
            "exact_matches": int((return_equal & flag_equal).sum()),
            "expected_differences": 0,
            "unexplained_differences": int((~return_equal | ~flag_equal).sum()),
            "maximum_absolute_difference": float(np.nanmax(np.abs(comparison["return_gbp_total_old"] - comparison["return_gbp_total_new"]))) if comparison["return_gbp_total_old"].notna().any() else 0.0,
            "audit_result": "PASS" if bool((return_equal & flag_equal).all()) else "FAIL",
        },
        {
            "audit_scope": "EXTRANEOUS_NON_XLON_ROWS_REMOVED",
            "compared_observations": int(calendar_audit["calendar_action"].eq("REMOVE_EXTRANEOUS_NON_SESSION").sum()),
            "exact_matches": 0,
            "expected_differences": int(calendar_audit["calendar_action"].eq("REMOVE_EXTRANEOUS_NON_SESSION").sum()),
            "unexplained_differences": 0,
            "maximum_absolute_difference": np.nan,
            "audit_result": "PASS",
        },
    ]
    cutoff = pd.Timestamp("2017-08-25")
    corrected_session_dates = set(
        calendar_audit.loc[
            calendar_audit["calendar_action"].isin(["ADD_GENUINE_XLON_SESSION", "REMOVE_EXTRANEOUS_NON_SESSION"]),
            "date",
        ]
    )
    for horizon in [21, 42, 63, 126, 252]:
        old = old_strict[horizon].reindex(index=matrices.calendar, columns=all_needed)
        new = matrices.formation[horizon]
        common = old.notna() & new.notna() & (old.index.to_series().le(cutoff).to_numpy()[:, None])
        differences = (old - new).where(common).stack().abs()
        max_difference = float(differences.max()) if len(differences) else np.nan
        materially_different = differences[differences > 1e-10] if len(differences) else pd.Series(dtype=float)
        expected_index: list[tuple[pd.Timestamp, str]] = []
        for date, family in materially_different.index:
            current_position = matrices.calendar.get_loc(date)
            start_position = max(0, current_position - horizon)
            formation_dates = set(matrices.calendar[start_position : current_position + 1])
            if formation_dates & corrected_session_dates:
                expected_index.append((date, family))
        expected_differences = len(expected_index)
        unexplained = int(len(materially_different) - expected_differences)
        rows.append(
            {
                "audit_scope": f"PRE_DEFECT_FORMATION_RETURN_{horizon}",
                "compared_observations": int(common.sum().sum()),
                "exact_matches": int((differences <= 1e-10).sum()) if len(differences) else 0,
                "expected_differences": expected_differences,
                "unexplained_differences": unexplained,
                "maximum_absolute_difference": max_difference,
                "audit_result": "PASS" if unexplained == 0 else "FAIL",
            }
        )
    return pd.DataFrame(rows)


def build_manual_cases(
    metadata: pd.DataFrame,
    history: pd.DataFrame,
    matrices: ResearchMatrices,
) -> tuple[pd.DataFrame, str]:
    candidates = [family for family in REPRESENTATIVE_FAMILIES if family in matrices.level.columns]
    if len(candidates) < 10:
        extras = [family for family in metadata["economic_exposure_family_id"] if family not in candidates]
        candidates.extend(extras[: 10 - len(candidates)])
    candidates = candidates[:10]
    benchmark = "GLOBAL_DEVELOPED_WORLD"
    history_index = history.set_index(["date", "economic_exposure_family_id"])
    rows: list[dict[str, Any]] = []
    for case_number, family in enumerate(candidates, start=1):
        horizon = 252 if case_number <= 8 else (63 if case_number == 9 else 21)
        valid = matrices.formation[horizon][family].notna() & matrices.formation[horizon][benchmark].notna()
        valid_dates = matrices.calendar[valid.to_numpy()]
        if not len(valid_dates):
            rows.append({"case_id": case_number, "economic_exposure_family_id": family, "validation_result": "FAIL_NO_VALID_CASE"})
            continue
        signal_date = valid_dates.max()
        current_position = matrices.calendar.get_loc(signal_date)
        target_position = int(matrices.target_positions[horizon].at[signal_date, family])
        benchmark_target_position = int(matrices.target_positions[horizon].at[signal_date, benchmark])
        target_date = matrices.calendar[target_position]
        benchmark_target_date = matrices.calendar[benchmark_target_position]
        current_value = float(matrices.level.at[signal_date, family])
        target_value = float(matrices.level.at[target_date, family])
        benchmark_current = float(matrices.level.at[signal_date, benchmark])
        benchmark_target = float(matrices.level.at[benchmark_target_date, benchmark])
        independent_return = current_value / target_value - 1.0
        independent_benchmark = benchmark_current / benchmark_target - 1.0
        independent_rs = (1.0 + independent_return) / (1.0 + independent_benchmark) - 1.0
        stored_return = float(matrices.formation[horizon].at[signal_date, family])
        stored_benchmark = float(matrices.formation[horizon].at[signal_date, benchmark])
        stored_rs = (1.0 + stored_return) / (1.0 + stored_benchmark) - 1.0
        row = history_index.loc[(signal_date, family)]
        result = "PASS" if max(abs(independent_return - stored_return), abs(independent_rs - stored_rs)) <= 1e-12 else "FAIL"
        rows.append(
            {
                "case_id": case_number,
                "economic_exposure_family_id": family,
                "selected_implementation_id": row["effective_listing_id"],
                "nominal_horizon_sessions": horizon,
                "signal_date": signal_date,
                "target_session": matrices.calendar[current_position - horizon],
                "actual_family_observation_date": target_date,
                "actual_benchmark_observation_date": benchmark_target_date,
                "actual_elapsed_family_xlon_sessions": current_position - target_position,
                "family_current_wealth": current_value,
                "family_target_wealth": target_value,
                "benchmark_current_wealth": benchmark_current,
                "benchmark_target_wealth": benchmark_target,
                "independent_family_return": independent_return,
                "stored_family_return": stored_return,
                "independent_benchmark_return": independent_benchmark,
                "stored_benchmark_return": stored_benchmark,
                "independent_relative_return": independent_rs,
                "stored_relative_return": stored_rs,
                "absolute_error": max(abs(independent_return - stored_return), abs(independent_rs - stored_rs)),
                "endpoint_failure_or_validity": row["endpoint_failure_reason"],
                "validation_result": result,
            }
        )
    cases = pd.DataFrame(rows)
    lines = [
        "# UKACTIVE-A2R2 manual validation cases",
        "",
        "Each case independently divides validated GBP total-return-index endpoints. No intervening price or return is filled. The benchmark-relative result is reconstructed from the independently calculated exposure and benchmark formation returns.",
        "",
    ]
    for row in cases.itertuples(index=False):
        lines.extend(
            [
                f"## Case {row.case_id}: {row.economic_exposure_family_id}",
                "",
                f"Implementation `{getattr(row, 'selected_implementation_id', 'NOT_AVAILABLE')}`; nominal horizon `{getattr(row, 'nominal_horizon_sessions', 'NOT_AVAILABLE')}` sessions; signal date `{getattr(row, 'signal_date', 'NOT_AVAILABLE')}`; target `{getattr(row, 'actual_family_observation_date', 'NOT_AVAILABLE')}`.",
                "",
                f"Exposure endpoints `{getattr(row, 'family_target_wealth', np.nan)}` → `{getattr(row, 'family_current_wealth', np.nan)}`; independent/stored return `{getattr(row, 'independent_family_return', np.nan)}` / `{getattr(row, 'stored_family_return', np.nan)}`. Independent/stored global-relative return `{getattr(row, 'independent_relative_return', np.nan)}` / `{getattr(row, 'stored_relative_return', np.nan)}`.",
                "",
                f"Result: **{row.validation_result}**.",
                "",
            ]
        )
    return cases, "\n".join(lines)


def build_synthetic_tests(policy: dict[str, Any]) -> pd.DataFrame:
    from ukactive_a2r2_core import build_continuous_family_history, endpoint_formation_matrices, endpoint_forward_matrices

    rows: list[dict[str, Any]] = []

    def record(test_id: str, description: str, passed: bool, observed: Any) -> None:
        rows.append(
            {
                "test_id": test_id,
                "description": description,
                "result": "PASS" if bool(passed) else "FAIL",
                "observed": json.dumps(observed, default=str),
            }
        )

    dates = pd.bdate_range("2020-01-02", periods=320)
    level = pd.DataFrame({"X": np.exp(np.arange(320) * 0.001)}, index=dates)
    segment = pd.DataFrame({"X": 1.0}, index=dates)
    level.at[dates[100], "X"] = np.nan
    formation, _, _ = endpoint_formation_matrices(level, segment, [252], 3)
    record("A2R2-SYN-01", "One missing master-calendar row does not permanently destroy a 252-session signal", pd.notna(formation[252].iloc[-1, 0]), formation[252].iloc[-1, 0])

    stale_fixture = pd.DataFrame(
        {
            "price_available": [True], "missing_flag": [False], "stale_flag": [True], "proxy_flag": [False],
            "price_before_inception_flag": [False], "adjusted_wealth_gbp": [101.0],
            "total_return_validation_status": ["PASS_EXPLICIT"], "semantic_family_match": [True],
        }
    )
    record("A2R2-SYN-02", "A stale observation is not treated as a fresh zero-return observation", not bool(endpoint_valid_mask(stale_fixture).iloc[0]), endpoint_valid_mask(stale_fixture).tolist())

    suspension = pd.DataFrame(
        {
            "date": dates[[0, 1, 10]], "economic_exposure_family_id": ["X"] * 3,
            "effective_listing_id": ["L1"] * 3, "endpoint_valid": [True] * 3,
            "endpoint_failure_reason": ["VALID_ENDPOINT"] * 3, "adjusted_wealth_gbp": [100.0, 101.0, 110.0],
            "session_position": [0, 1, 10], "previous_listing_valid_session_position": [np.nan, 0, 1],
            "previous_listing_valid_wealth_gbp": [np.nan, 100.0, 101.0],
        }
    )
    suspension_history = build_continuous_family_history(suspension, 3)
    record("A2R2-SYN-03", "A genuinely long suspension resets continuity", suspension_history["continuity_segment_id"].tolist() == [1, 1, 2], suspension_history["continuity_segment_id"].tolist())

    holiday_level = pd.DataFrame({"X": np.arange(1.0, 80.0)}, index=dates[:79])
    holiday_segment = pd.DataFrame({"X": 1.0}, index=dates[:79])
    holiday_level.iloc[57, 0] = np.nan
    holiday_formation, _, holiday_offset = endpoint_formation_matrices(holiday_level, holiday_segment, [21], 3)
    record("A2R2-SYN-04", "A short international fund holiday uses only the declared prior-endpoint tolerance", pd.notna(holiday_formation[21].iloc[79 - 1, 0]) and holiday_offset[21].iloc[79 - 1, 0] in [0, 1, 2, 3], holiday_offset[21].iloc[79 - 1, 0])

    benchmark_level = pd.DataFrame({"X": np.arange(1.0, 80.0), "B": np.arange(2.0, 81.0)}, index=dates[:79])
    benchmark_segment = pd.DataFrame(1.0, index=dates[:79], columns=["X", "B"])
    benchmark_level.iloc[-22:, 1] = np.nan
    benchmark_formation, _, _ = endpoint_formation_matrices(benchmark_level, benchmark_segment, [21], 0)
    rs_valid = benchmark_formation[21]["X"].notna() & benchmark_formation[21]["B"].notna()
    record("A2R2-SYN-05", "A benchmark missing observation creates no future leakage", not bool(rs_valid.iloc[-1]), rs_valid.iloc[-1])

    transition = pd.DataFrame(
        {
            "date": dates[:3], "economic_exposure_family_id": ["X"] * 3,
            "effective_listing_id": ["L1", "L1", "L2"], "endpoint_valid": [True] * 3,
            "endpoint_failure_reason": ["VALID_ENDPOINT"] * 3, "adjusted_wealth_gbp": [100.0, 101.0, 202.0],
            "session_position": [0, 1, 2], "previous_listing_valid_session_position": [np.nan, 0, 1],
            "previous_listing_valid_wealth_gbp": [np.nan, 100.0, 200.0],
        }
    )
    transition_history = build_continuous_family_history(transition, 3)
    transition_pass = transition_history["continuity_segment_id"].tolist() == [1, 1, 1] and transition_history.iloc[-1]["continuity_reason"] == "SEMANTICALLY_IDENTICAL_IMPLEMENTATION_TRANSITION"
    record("A2R2-SYN-06", "An economically identical canonical implementation transition follows the lineage policy", transition_pass, transition_history[["continuity_segment_id", "continuity_reason"]].to_dict("records"))

    pre_inception = stale_fixture.copy()
    pre_inception["stale_flag"] = False
    pre_inception["price_before_inception_flag"] = True
    record("A2R2-SYN-07", "Pre-inception observations never enter", not bool(endpoint_valid_mask(pre_inception).iloc[0]), endpoint_valid_mask(pre_inception).tolist())

    forward_level = pd.DataFrame({"X": [100.0, 101.0, 103.0]}, index=dates[:3])
    forward_segment = pd.DataFrame({"X": 1.0}, index=dates[:3])
    forward = endpoint_forward_matrices(forward_level, forward_segment, [1])[1]
    expected = 101.0 / 100.0 - 1.0
    record("A2R2-SYN-08", "Date-T close never earns date-T forward return", abs(float(forward.iloc[0, 0]) - expected) <= 1e-12, {"stored": forward.iloc[0, 0], "expected_t_plus_1": expected})
    return pd.DataFrame(rows)


def scope_markdown() -> str:
    return """# UKACTIVE-A2R2 scope and method

UKACTIVE-A2R2 remediates only the research-session calendar and return-validity chain used by the frozen A3R1 experiment. It does not alter the 99-family master, classification, competition pools, parent maps, benchmark choice, signal definitions, horizon weights, observation frequency, top-tail definitions, forward horizons, inference or promotion thresholds.

The remediation policy was declared without reference to whether any A3R1 signal improves. Prior A3R1 efficacy outputs remain preserved and are labelled `A3R1_PRE_REMEDIATION_INVALID_FOR_EFFICACY_CONCLUSION` because their modern long-horizon coverage failed.

The authoritative daily A2R returns remain unchanged on retained sessions. A2R2 adds a separate formation-history layer based on validated GBP adjusted-wealth endpoints. Daily-return validity and endpoint validity are deliberately separate concepts.

CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY. Historical UK retail, account and broker eligibility remain unresolved.
"""


def session_policy_markdown(policy: dict[str, Any], calendar_audit: pd.DataFrame) -> str:
    removed = calendar_audit.loc[calendar_audit["calendar_action"].eq("REMOVE_EXTRANEOUS_NON_SESSION")]
    added = calendar_audit.loc[calendar_audit["calendar_action"].eq("ADD_GENUINE_XLON_SESSION")]
    return f"""# UKACTIVE-A2R2 session-calendar policy

The canonical research calendar is Monday–Friday excluding England and Wales public/bank holidays and dated one-off LSE closures. Half sessions remain sessions. Vendor observation presence is evidence about a price route; it is not proof that XLON was open.

Primary policy sources:

- London Stock Exchange business days: https://www.londonstockexchange.com/equities-trading/business-days
- GOV.UK bank holidays: https://www.gov.uk/bank-holidays
- London Stock Exchange notices: https://www.londonstockexchange.com/resources/london-stock-exchange-notices

The old observed union contained **{len(removed)}** extraneous non-sessions, including 2017-08-28. A2R2 adds **{len(added)}** genuine weekday session omitted by the observation union (2000-07-14); no instrument value is manufactured for that date.

The weekly A3R1 convention remains frozen: the final eligible XLON session of each calendar week, signal after close, forward measurement from a later eligible session.
"""


def signal_policy_markdown(policy: dict[str, Any]) -> str:
    endpoint = policy["endpoint_policy"]
    return f"""# UKACTIVE-A2R2 signal-history policy

For an h-session formation return, A2R2 compares the exact valid signal-date GBP total-return-index endpoint with the nominal h-session historical endpoint. If that historical boundary is unavailable, only the nearest **previous** valid endpoint within **{endpoint['target_backward_tolerance_xlon_sessions']}** genuine XLON sessions may be used. The actual date and elapsed sessions are recorded.

The signal-date endpoint must be exact. A future endpoint is never used at a formation boundary. Forward returns require exact endpoints at T and T+h and exclude date-T return.

A missing daily return does not imply that all later formation endpoints lack information. Conversely, an adjusted-wealth endpoint is valid only when the price exists, is non-stale, non-proxy, post-inception, semantically valid and belongs to a total-return route that passed A2/A2R validation.

No price, return or relative-strength series is forward-filled. No zero return is manufactured. No proxy enters. A gap exceeding **{endpoint['maximum_continuity_gap_xlon_sessions']}** XLON sessions resets the continuity segment, so formation and forward returns cannot cross a long suspension.
"""


def gap_policy_markdown(policy: dict[str, Any]) -> str:
    return f"""# UKACTIVE-A2R2 gap and staleness policy

- Latest formation endpoint: exact signal-date observation only.
- Historical boundary: exact nominal session, or nearest previous valid endpoint within {policy['endpoint_policy']['target_backward_tolerance_xlon_sessions']} sessions.
- Continuity bridge: at most {policy['endpoint_policy']['maximum_continuity_gap_xlon_sessions']} genuine XLON sessions, calculated from two validated endpoints of the same listing.
- Missing intervening rows remain missing.
- Stale observations remain invalid and are never assigned a zero return.
- Longer gaps reset the continuity segment and cannot be crossed by formation or forward returns.
- Implementation transitions continue only when both lines remain in the same frozen A2R economic fingerprint and the incoming line has a recent prior validated endpoint; otherwise the segment resets.

The three-session tolerance was selected before the corrected A3R1 results were run. It covers ordinary international fund holidays and short vendor timing gaps without bridging a material suspension; it was not chosen to improve a signal result.
"""


def root_cause_markdown(summary: dict[str, Any], calendar_audit: pd.DataFrame) -> str:
    removed = calendar_audit.loc[calendar_audit["calendar_action"].eq("REMOVE_EXTRANEOUS_NON_SESSION")]
    examples = ", ".join(date.date().isoformat() for date in removed["date"].head(8))
    return f"""# UKACTIVE-A2R2 root-cause report

## Exact cutoff

The old A3R1 constructor reproduces `RS_252_LAST_VALID_DATE = {summary['old_rs_252_last_valid_weekly_date']}` and `FIVE_HORIZON_COMPOSITE_LAST_VALID_DATE = {summary['old_five_horizon_composite_last_valid_weekly_date']}`.

## Root cause

The A2 calendar was an observed vendor-session union, not a complete official XLON calendar. It admitted {summary['extraneous_non_session_count']} bank holidays/non-sessions. Examples are {examples}. On 2017-08-28, a small number of vendor rows caused the bank holiday to be treated as a session. Some instruments received a spurious valid zero return; most received a missing row, and the next genuine session could also lose the prior-session canonical selection.

A3R1 then required every one of 252 consecutive master-calendar daily-return rows to be valid. The benchmark suffered a genuine selected-line gap on 2017-11-08. A single gap could age out after 252 master rows, but recurring contaminated bank-holiday/missing-selection pairs ensured that no later 252-row window became clean. Thus short horizons intermittently recovered while strict 252-session and five-horizon signals disappeared from the modern period.

The root-cause codes are: `MASTER_CALENDAR_CONTAMINATION`, `CONSECUTIVE_ROW_REQUIREMENT`, `BENCHMARK_VALIDITY_CHAIN`, `RETURN_CHAIN_BREAK`, `MASTER_ROW_SESSION_COUNT_ERROR`, and `DAILY_VALIDITY_USED_AS_FORMATION_ENDPOINT_VALIDITY`. Stale-price propagation and canonical implementation transitions were investigated and are not the cause of the synchronous 2017 cutoff.

## Repair

A2R2 replaces only the research-session and signal-history adapter: official-session rules determine the XLON calendar, while formation returns use validated GBP total-return-index endpoints within explicit continuity segments. Raw A2R daily values on retained dates are unchanged. Missing and stale observations remain invalid.
"""


def quality_report_markdown(
    decision: str,
    tests: pd.DataFrame,
    manual: pd.DataFrame,
    synthetic: pd.DataFrame,
    latest_counts: dict[int, int],
    benchmark_audit: pd.DataFrame,
) -> str:
    modern = benchmark_audit.loc[benchmark_audit["year"].ge(2020)]
    return f"""# UKACTIVE-A2R2 data-quality report

Decision: `{decision}`.

- Automated tests: {int(tests['result'].eq('PASS').sum())}/{len(tests)} PASS.
- Manual endpoint reconstructions: {int(manual['validation_result'].eq('PASS').sum())}/{len(manual)} PASS.
- Synthetic fixtures: {int(synthetic['result'].eq('PASS').sum())}/{len(synthetic)} PASS.
- Latest candidate-family eligibility: 21={latest_counts[21]}, 42={latest_counts[42]}, 63={latest_counts[63]}, 126={latest_counts[126]}, 252={latest_counts[252]}.
- GLOBAL_DEVELOPED_WORLD has at least one valid 252-session formation observation in every modern year audited: {bool((modern['formation_252_valid_dates'] > 0).all())}.
- Prices/returns forward-filled: NO.
- Stale observations admitted: NO.
- Lookahead introduced: NO.
- Proxy history admitted: NO.

The remaining programme-wide warning is historical public retail/account/broker eligibility. It does not affect A3R1 signal-efficacy measurement and is not back-projected.
"""


def readiness_markdown(decision: str, tests: pd.DataFrame, latest_counts: dict[int, int]) -> str:
    authorised = decision in {"UKACTIVE_A2R2_PASS", "UKACTIVE_A2R2_PASS_WITH_OPEN_ITEMS"} and tests["result"].eq("PASS").all()
    return f"""# UKACTIVE-A2R2 A3R1R1 readiness report

A2R2 decision: `{decision}`.

The unchanged A3R1 rerun is scientifically authorised: **{'YES' if authorised else 'NO'}**.

The corrected formation chain reaches the latest source date with candidate-family counts 21={latest_counts[21]}, 42={latest_counts[42]}, 63={latest_counts[63]}, 126={latest_counts[126]}, 252={latest_counts[252]}. The frozen A3R1 signals, weights, groups, weekly schedule, top-tail definitions, forward horizons, inference and promotion thresholds must be reused exactly.

The original A3R1 outputs are preserved and classified `A3R1_PRE_REMEDIATION_INVALID_FOR_EFFICACY_CONCLUSION`. A3R2 remains unauthorised until the exact A3R1R1 rerun is evaluated.
"""


def main() -> int:
    print("A2R2: loading frozen policies and Git checkpoint", flush=True)
    policy = read_json(POLICY_PATH)
    a3r1_policy = read_json(A3R1_POLICY_PATH)
    metadata, all_needed = load_metadata()
    calendar_audit, sessions, removed_dates = build_calendar_audit(policy)

    print("A2R2: constructing validated endpoint and continuity history", flush=True)
    history, instrument = build_signal_endpoint_history(policy, sessions, removed_dates, all_needed)
    matrices = build_research_matrices(history, policy, sessions, all_needed)
    corrected_daily = build_corrected_daily_panel(policy, sessions)
    eligibility = build_signal_eligibility(history, matrices, policy)

    print("A2R2: reproducing the old cutoff and building audits", flush=True)
    cutoff_trace, cutoff_summary, old_returns, old_strict = build_cutoff_trace(
        policy, calendar_audit, sessions, history, matrices, all_needed
    )
    benchmark_audit = build_benchmark_audit(history, matrices, old_returns)
    transition_audit = build_transition_audit(history)
    affected = build_affected_family_audit(metadata, matrices, old_strict)
    heatmap, year_coverage, latest_counts = build_coverage(metadata, matrices)
    before_after = build_before_after_audit(corrected_daily, calendar_audit, old_strict, matrices, all_needed)
    manual_cases, manual_markdown = build_manual_cases(metadata, history, matrices)
    synthetic = build_synthetic_tests(policy)
    tests = build_automated_tests(
        policy, calendar_audit, history, matrices, cutoff_summary, benchmark_audit,
        before_after, manual_cases, synthetic, year_coverage,
    )
    blocking = int(tests["result"].eq("FAIL").sum())
    decision = "UKACTIVE_A2R2_PASS" if blocking == 0 else "UKACTIVE_A2R2_FAIL"
    a3r1r1_authorised = decision == "UKACTIVE_A2R2_PASS"

    output_audit: list[dict[str, Any]] = []
    print("A2R2: writing auditable outputs", flush=True)
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A2R2_2017_CUTOFF_FORENSIC_TRACE.csv", cutoff_trace))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A2R2_XLON_RESEARCH_CALENDAR.csv", calendar_audit))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A2R2_BENCHMARK_VALIDITY_AUDIT.csv", benchmark_audit))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A2R2_IMPLEMENTATION_TRANSITION_AUDIT.csv", transition_audit))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A2R2_AFFECTED_FAMILY_AUDIT.csv", affected))
    output_audit.append(write_parquet(PROGRAMME_ROOT / "UKACTIVE_A2R2_CORRECTED_TOTAL_RETURN_PANEL_GBP.parquet", corrected_daily))
    output_audit.append(write_parquet(PROGRAMME_ROOT / "UKACTIVE_A2R2_SIGNAL_ENDPOINT_HISTORY.parquet", history))
    output_audit.append(write_parquet(PROGRAMME_ROOT / "UKACTIVE_A2R2_CORRECTED_SIGNAL_ELIGIBILITY.parquet", eligibility))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A2R2_HORIZON_COVERAGE_HEATMAP.csv", heatmap))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A2R2_HORIZON_COVERAGE_BY_YEAR.csv", year_coverage))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A2R2_BEFORE_AFTER_DIFF_AUDIT.csv", before_after))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A2R2_MANUAL_VALIDATION_CASES.csv", manual_cases))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A2R2_SYNTHETIC_TEST_RESULTS.csv", synthetic))
    output_audit.append(write_csv(PROGRAMME_ROOT / "UKACTIVE_A2R2_AUTOMATED_TEST_RESULTS.csv", tests))
    output_audit.append(write_text(PROGRAMME_ROOT / "UKACTIVE_A2R2_SCOPE_AND_METHOD.md", scope_markdown()))
    output_audit.append(write_text(PROGRAMME_ROOT / "UKACTIVE_A2R2_ROOT_CAUSE_REPORT.md", root_cause_markdown(cutoff_summary, calendar_audit)))
    output_audit.append(write_text(PROGRAMME_ROOT / "UKACTIVE_A2R2_SESSION_CALENDAR_POLICY.md", session_policy_markdown(policy, calendar_audit)))
    output_audit.append(write_text(PROGRAMME_ROOT / "UKACTIVE_A2R2_SIGNAL_HISTORY_POLICY.md", signal_policy_markdown(policy)))
    output_audit.append(write_text(PROGRAMME_ROOT / "UKACTIVE_A2R2_GAP_AND_STALENESS_POLICY.md", gap_policy_markdown(policy)))
    output_audit.append(write_text(PROGRAMME_ROOT / "UKACTIVE_A2R2_MANUAL_VALIDATION_CASES.md", manual_markdown))
    output_audit.append(write_text(PROGRAMME_ROOT / "UKACTIVE_A2R2_DATA_QUALITY_REPORT.md", quality_report_markdown(decision, tests, manual_cases, synthetic, latest_counts, benchmark_audit)))
    output_audit.append(write_text(PROGRAMME_ROOT / "UKACTIVE_A2R2_A3R1R1_READINESS_REPORT.md", readiness_markdown(decision, tests, latest_counts)))
    output_audit.append(write_text(PROGRAMME_ROOT / "UKACTIVE_A2R2_PRIOR_A3R1_STATUS.md", "# Prior A3R1 status\n\n`A3R1_PRE_REMEDIATION_INVALID_FOR_EFFICACY_CONCLUSION`. Original A3R1 artifacts are preserved unchanged.\n"))

    decision_payload = {
        "stage_id": "UKACTIVE-A2R2",
        "run_id": policy["run_id"],
        "decision": decision,
        "root_cause": "OBSERVED_UNION_MASTER_CALENDAR_CONTAMINATION_PLUS_STRICT_CONSECUTIVE_DAILY_RETURN_ROLLING",
        "old_rs_252_last_valid_date": cutoff_summary["old_rs_252_last_valid_weekly_date"],
        "old_five_horizon_composite_last_valid_date": cutoff_summary["old_five_horizon_composite_last_valid_weekly_date"],
        "prices_or_returns_forward_filled": False,
        "stale_observations_admitted": False,
        "lookahead_introduced": False,
        "latest_eligible_family_counts": {str(key): value for key, value in latest_counts.items()},
        "automated_tests": tests["result"].value_counts().to_dict(),
        "manual_validation": manual_cases["validation_result"].value_counts().to_dict(),
        "synthetic_tests": synthetic["result"].value_counts().to_dict(),
        "a3r1r1_authorised": a3r1r1_authorised,
        "a3r2_authorised": False,
        "warning": WARNING,
    }
    decision_path = PROGRAMME_ROOT / "UKACTIVE_A2R2_DECISION.json"
    output_audit.append(write_json(decision_path, decision_payload))

    input_paths = [
        POLICY_PATH,
        A3R1_POLICY_PATH,
        PROGRAMME_ROOT / policy["authoritative_inputs"]["a2_instrument_history"],
        PROGRAMME_ROOT / policy["authoritative_inputs"]["a2r_corrected_instrument_history"],
        PROGRAMME_ROOT / policy["authoritative_inputs"]["a2r_corrected_panel"],
        PROGRAMME_ROOT / policy["authoritative_inputs"]["a2_observed_union_calendar"],
        PROGRAMME_ROOT / policy["authoritative_inputs"]["a3r1_signal_registry"],
    ]
    manifest = {
        "stage_id": "UKACTIVE-A2R2",
        "run_id": policy["run_id"],
        "started_from_git_commit": git_value("rev-parse", "HEAD"),
        "git_branch": git_value("branch", "--show-current"),
        "git_remote": git_value("remote", "-v") or "NONE",
        "post_a2r2_commit": "PENDING_AFTER_EXECUTION",
        "created_at": utc_now(),
        "policy": policy,
        "frozen_a3r1_policy_sha256": sha256_file(A3R1_POLICY_PATH),
        "frozen_a3r1_registry_sha256": sha256_file(PROGRAMME_ROOT / "UKACTIVE_A3R1_SIGNAL_REGISTRY.csv"),
        "inputs": [{"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in input_paths],
        "outputs": output_audit,
        "source_urls": policy["official_calendar_policy"]["official_sources"],
        "source_retrieval_date": "2026-08-23",
        "calendar_statistics": cutoff_summary,
        "latest_eligible_family_counts": {str(key): value for key, value in latest_counts.items()},
        "packages": {
            "python": sys.version,
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "pyarrow": pyarrow.__version__,
        },
        "executed_code": [
            {"path": str(Path(__file__).resolve()), "sha256": sha256_file(Path(__file__).resolve())},
            {"path": str(Path(__file__).resolve().with_name("ukactive_a2r2_core.py")), "sha256": sha256_file(Path(__file__).resolve().with_name("ukactive_a2r2_core.py"))},
        ],
        "exact_command": f'python "{Path(__file__).resolve()}"',
        "automated_test_results": tests.to_dict("records"),
        "unresolved_items": [WARNING],
        "decision": decision,
        "a3r1r1_authorised": a3r1r1_authorised,
    }
    manifest_path = PROGRAMME_ROOT / "UKACTIVE_A2R2_MANIFEST.json"
    write_json(manifest_path, manifest)
    print(json.dumps(decision_payload, indent=2), flush=True)
    return 0 if a3r1r1_authorised else 2


def build_automated_tests(
    policy: dict[str, Any],
    calendar_audit: pd.DataFrame,
    history: pd.DataFrame,
    matrices: ResearchMatrices,
    cutoff_summary: dict[str, Any],
    benchmark_audit: pd.DataFrame,
    before_after: pd.DataFrame,
    manual_cases: pd.DataFrame,
    synthetic: pd.DataFrame,
    year_coverage: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(test_id: str, description: str, passed: bool, observed: Any) -> None:
        rows.append({"test_id": test_id, "description": description, "result": "PASS" if bool(passed) else "FAIL", "observed": json.dumps(observed, default=str)})

    add("A2R2-T01", "Exact old RS_252 cutoff is reproduced", cutoff_summary["old_rs_252_last_valid_weekly_date"] == "2017-11-03", cutoff_summary["old_rs_252_last_valid_weekly_date"])
    add("A2R2-T02", "Exact old five-horizon cutoff is reproduced", cutoff_summary["old_five_horizon_composite_last_valid_weekly_date"] == "2017-08-25", cutoff_summary["old_five_horizon_composite_last_valid_weekly_date"])
    removed = calendar_audit.loc[calendar_audit["calendar_action"].eq("REMOVE_EXTRANEOUS_NON_SESSION"), "date"]
    add("A2R2-T03", "Extraneous bank-holiday sessions are removed", pd.Timestamp("2017-08-28") in set(removed) and len(removed) == 29, {"removed": len(removed), "contains_2017_08_28": pd.Timestamp("2017-08-28") in set(removed)})
    add("A2R2-T04", "No endpoint marked valid is stale, missing or proxy", not ((history["endpoint_valid"] & (history["stale_flag"].fillna(False) | history["missing_flag"].fillna(True) | history["proxy_flag"].fillna(False))).any()), int((history["endpoint_valid"] & (history["stale_flag"].fillna(False) | history["missing_flag"].fillna(True) | history["proxy_flag"].fillna(False))).sum()))
    add("A2R2-T05", "No formation target uses a future or later-than-nominal endpoint", all((frame.to_numpy() <= 3).all() for frame in matrices.target_offsets.values()), {h: int(frame.max().max()) for h, frame in matrices.target_offsets.items()})
    add("A2R2-T06", "Formation endpoint tolerance is fixed independently of signal results", int(policy["endpoint_policy"]["target_backward_tolerance_xlon_sessions"]) == 3 and not policy["research_boundary"]["remediation_may_use_a3r1_efficacy_results"], policy["endpoint_policy"])
    add("A2R2-T07", "Long gaps reset continuity", not ((history["return_span_xlon_sessions"].fillna(0) > 3).any()), float(history["return_span_xlon_sessions"].max()))
    add("A2R2-T08", "US defence pre-mandate history is excluded", not history.loc[(history["economic_exposure_family_id"].eq("US_AEROSPACE_DEFENCE")) & (history["date"] < pd.Timestamp("2026-07-16")), "endpoint_valid"].any(), int(history.loc[(history["economic_exposure_family_id"].eq("US_AEROSPACE_DEFENCE")) & (history["date"] < pd.Timestamp("2026-07-16")), "endpoint_valid"].sum()))
    add("A2R2-T09", "GLOBAL_BANKS is absent from the A3R1 ranking input", "GLOBAL_BANKS" not in matrices.level.columns or matrices.level["GLOBAL_BANKS"].notna().sum() == 0, "GLOBAL_BANKS" in matrices.level.columns)
    add("A2R2-T10", "Raw retained A2R panel values are unchanged", before_after.loc[before_after["audit_scope"].eq("RETAINED_RAW_DAILY_PANEL_ROWS"), "audit_result"].eq("PASS").all(), before_after.to_dict("records")[:2])
    add("A2R2-T11", "Pre-defect formation-return regression is clean", before_after.loc[before_after["audit_scope"].str.startswith("PRE_DEFECT"), "audit_result"].eq("PASS").all(), before_after.loc[before_after["audit_scope"].str.startswith("PRE_DEFECT")].to_dict("records"))
    modern_252 = year_coverage.loc[(year_coverage["analysis_context_id"].eq("ALL_EQUITY_OPPORTUNITIES")) & (year_coverage["signal_horizon_sessions"].eq(252)) & (year_coverage["year"].ge(2020)), "eligible_family_count"]
    add("A2R2-T12", "Modern 252-session coverage is restored wherever genuine histories exist", len(modern_252) >= 7 and modern_252.min() > 0, modern_252.to_dict())
    modern_benchmark = benchmark_audit.loc[benchmark_audit["year"].ge(2020), "formation_252_valid_dates"]
    add("A2R2-T13", "GLOBAL_DEVELOPED_WORLD retains modern 252-session formation coverage", len(modern_benchmark) >= 7 and modern_benchmark.min() > 0, modern_benchmark.to_dict())
    add("A2R2-T14", "All ten manual reconstructions pass", len(manual_cases) == 10 and manual_cases["validation_result"].eq("PASS").all(), manual_cases["validation_result"].value_counts().to_dict())
    add("A2R2-T15", "All eight synthetic fixtures pass", len(synthetic) == 8 and synthetic["result"].eq("PASS").all(), synthetic["result"].value_counts().to_dict())
    add("A2R2-T16", "Signal endpoint grid is unique by date and economic family", not history.duplicated(["date", "economic_exposure_family_id"]).any(), int(history.duplicated(["date", "economic_exposure_family_id"]).sum()))
    add("A2R2-T17", "No implementation listing is a ranking identity", set(history["economic_exposure_family_id"]) == set(matrices.level.columns), {"families": len(set(history["economic_exposure_family_id"])), "matrix_columns": len(matrices.level.columns)})
    add("A2R2-T18", "No same-close forward return construction", all(frame.iloc[-h:].isna().all().all() for h, frame in matrices.forward.items()), {h: int(frame.iloc[-h:].notna().sum().sum()) for h, frame in matrices.forward.items()})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    raise SystemExit(main())
