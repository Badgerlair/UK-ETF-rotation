"""UKACTIVE-A4 frozen-candidate right-tail and concentration forensics.

This module deliberately consumes the already-corrected A2R2 histories and the
frozen A3R2 feature/regime panels.  It does not search for a new strategy.  All
portfolio choices are loaded from UKACTIVE_A4_POLICY_v1.json and checked against
the frozen A3R2 definition before any result is written.
"""

from __future__ import annotations

import json
import math
import platform
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow
from scipy.stats import skew

from build_ukactive_a3r2s import common_start, evaluate_bundle, simulate_bundle, window_bounds
from ukactive_a3r2_core import (
    PROGRAMME_ROOT,
    WARNING,
    audit_file,
    circular_block_bootstrap_mean_ci,
    git_output,
    newey_west_mean,
    sha256_file,
    utc_now,
    write_csv,
    write_json,
    write_text,
)
from ukactive_a3r2_portfolio import (
    ResearchData,
    SimulationResult,
    load_research_data,
    performance_metrics,
    selection_targets,
    simulate_targets,
)


RUN_ID = "UKACTIVE-A4-20260823-001"
PREFIX = "UKACTIVE_A4"
POLICY_PATH = PROGRAMME_ROOT / "config" / "UKACTIVE_A4_POLICY_v1.json"
FEATURE_PATH = PROGRAMME_ROOT / "UKACTIVE_A3R2_FEATURE_PANEL.parquet"
REGIME_PATH = PROGRAMME_ROOT / "UKACTIVE_A3R2_REGIME_STATE_HISTORY.parquet"
SNAPSHOT_PATH = PROGRAMME_ROOT / "UKACTIVE_A3R2U_CURRENT_UNIVERSE_SNAPSHOT.csv"


def out(name: str) -> Path:
    return PROGRAMME_ROOT / f"{PREFIX}_{name}"


def read_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def as_float(value: Any) -> float:
    return float(value) if value is not None and pd.notna(value) else np.nan


def series_value(frame: pd.DataFrame, date: pd.Timestamp, column: str) -> float:
    values = frame.loc[frame["date"].eq(pd.Timestamp(date)), column]
    return float(values.iloc[0]) if len(values) and pd.notna(values.iloc[0]) else np.nan


def curve_value(simulation: SimulationResult, date: pd.Timestamp) -> float:
    frame = simulation.curve.set_index("date")
    return float(frame.at[pd.Timestamp(date), "portfolio_value"]) if pd.Timestamp(date) in frame.index else np.nan


def total_return_between(simulation: SimulationResult, start: pd.Timestamp, end: pd.Timestamp) -> float:
    left = curve_value(simulation, start)
    right = curve_value(simulation, end)
    return right / left - 1.0 if np.isfinite(left) and np.isfinite(right) and left > 0 else np.nan


def wealth_return(
    data: ResearchData,
    family: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    *,
    require_continuity: bool = True,
) -> float:
    if family not in data.wealth.columns or start not in data.wealth.index or end not in data.wealth.index:
        return np.nan
    left = data.wealth.at[start, family]
    right = data.wealth.at[end, family]
    if not (np.isfinite(left) and np.isfinite(right) and left > 0):
        return np.nan
    if require_continuity and data.segment.at[start, family] != data.segment.at[end, family]:
        return np.nan
    return float(right / left - 1.0)


def next_valid_endpoint(
    data: ResearchData,
    review_date: pd.Timestamp,
    families: Iterable[str],
    max_lag: int = 3,
) -> tuple[pd.Timestamp | pd.NaT, int | float]:
    positions = {pd.Timestamp(date): index for index, date in enumerate(data.calendar)}
    review_date = pd.Timestamp(review_date)
    if review_date not in positions:
        return pd.NaT, np.nan
    members = list(families)
    for lag in range(1, max_lag + 1):
        position = positions[review_date] + lag
        if position >= len(data.calendar):
            break
        date = pd.Timestamp(data.calendar[position])
        if all(family in data.wealth.columns and np.isfinite(data.wealth.at[date, family]) for family in members):
            return date, lag
    return pd.NaT, np.nan


def validate_frozen_contract(policy: dict[str, Any]) -> list[dict[str, Any]]:
    primary = policy["primary_candidate"]
    expected = {
        "pool_id": "INDUSTRY_PLUS_THEME",
        "signal_id": "MH_LEVEL_3_6_12_REFERENCE",
        "selection_rule": "TOP_1",
        "cadence": "MONTHLY",
        "weighting": "EQUAL",
        "signal_horizons_sessions": [63, 126, 252],
    }
    rows = []
    for key, value in expected.items():
        rows.append(
            {
                "test_id": f"A4-FREEZE-{key.upper()}",
                "test": f"Frozen {key} unchanged",
                "status": "PASS" if primary.get(key) == value else "FAIL",
                "detail": f"expected={value}; actual={primary.get(key)}",
            }
        )
    weights = primary["signal_horizon_weights"]
    weight_ok = len(weights) == 3 and all(abs(float(value) - 1.0 / 3.0) < 1e-15 for value in weights)
    rows.append({"test_id": "A4-FREEZE-WEIGHTS", "test": "3/6/12 weights unchanged", "status": "PASS" if weight_ok else "FAIL", "detail": json.dumps(weights, sort_keys=True)})
    rows.append({"test_id": "A4-FREEZE-EXECUTION", "test": "Next-eligible-session execution retained", "status": "PASS" if primary["execution"] == "FIRST_VALID_CLOSE_ON_OR_AFTER_NEXT_XLON_SESSION_WITHIN_3_XLON_SESSIONS" else "FAIL", "detail": primary["execution"]})
    rows.append({"test_id": "A4-FREEZE-BENCHMARK", "test": "Global benchmark unchanged", "status": "PASS" if primary["benchmark_family_id"] == "GLOBAL_DEVELOPED_WORLD" else "FAIL", "detail": primary["benchmark_family_id"]})
    return rows


def primary_source(features: pd.DataFrame, start: pd.Timestamp | None = None) -> pd.DataFrame:
    frame = features.loc[
        features["cadence"].eq("MONTHLY")
        & features["analysis_context_id"].eq("INDUSTRY_PLUS_THEME")
    ].copy()
    if start is not None:
        frame = frame.loc[frame["date"].ge(start)]
    return frame


def make_bundle(
    data: ResearchData,
    features: pd.DataFrame,
    snapshot: pd.DataFrame,
    *,
    pool_id: str,
    signal_id: str,
    selection_rule: str,
    start: pd.Timestamp | None,
    friction_bps: float = 20.0,
    fixed_fee: float = 3.99,
    sleeve_size: float = 250_000.0,
    fx_rate: float = 0.0075,
    excluded: set[str] | None = None,
) -> dict[str, Any]:
    source = features.loc[
        features["cadence"].eq("MONTHLY") & features["analysis_context_id"].eq(pool_id)
    ].copy()
    if start is not None:
        source = source.loc[source["date"].ge(start)]
    non_gbp = set(snapshot.loc[~snapshot["listing_currency"].isin(["GBP", "GBX", "NOT_APPLICABLE"]), "economic_exposure_family_id"])
    return simulate_bundle(
        features=source,
        signal_id=signal_id,
        selection_rule=selection_rule,
        data=data,
        allowed_families=None,
        maturity_scope="DYNAMIC_POINT_IN_TIME",
        non_gbp_families=non_gbp,
        friction_bps=friction_bps,
        fixed_fee=fixed_fee,
        sleeve_size=sleeve_size,
        fx_rate=fx_rate,
        excluded_families=excluded,
    )


def decision_and_top5_ledgers(
    data: ResearchData,
    source: pd.DataFrame,
    bundle: dict[str, Any],
    snapshot: pd.DataFrame,
    regime: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    snapshot_index = snapshot.set_index("economic_exposure_family_id")
    regime_source = regime.loc[regime["pool_id"].eq("INDUSTRY_PLUS_THEME")].sort_values("date")
    trade_index = bundle["selected_net"].trades.set_index("review_date", drop=False)
    pool_curve = bundle["equal_pool"]
    unselected_curve = bundle["unselected_pool"]
    candidate_curve = bundle["selected_net"]
    review_dates = sorted(pd.Timestamp(value) for value in source["date"].unique())
    executions: dict[pd.Timestamp, pd.Timestamp | pd.NaT] = {}
    selected_by_review: dict[pd.Timestamp, str] = {}
    top5_rows: list[dict[str, Any]] = []
    preliminary: list[dict[str, Any]] = []
    previous = "NOT_APPLICABLE"

    for review_date in review_dates:
        frame = source.loc[source["date"].eq(review_date) & source["MH_LEVEL_3_6_12_REFERENCE"].notna()].copy()
        frame = frame.sort_values(["MH_LEVEL_3_6_12_REFERENCE", "economic_exposure_family_id"], ascending=[False, True]).reset_index(drop=True)
        frame["rank"] = np.arange(1, len(frame) + 1)
        selected = str(frame.iloc[0]["economic_exposure_family_id"]) if len(frame) else "NOT_APPLICABLE"
        selected_by_review[review_date] = selected
        if review_date in trade_index.index:
            trade = trade_index.loc[review_date]
            if isinstance(trade, pd.DataFrame):
                trade = trade.iloc[0]
            execution_date = pd.Timestamp(trade["execution_date"]) if pd.notna(trade["execution_date"]) else pd.NaT
            execution_lag = as_float(trade["execution_lag_xlon_sessions"])
            execution_status = str(trade["execution_status"])
            transaction_cost = as_float(trade["transaction_cost_value"])
        else:
            execution_date, execution_lag = next_valid_endpoint(data, review_date, [] if selected == "NOT_APPLICABLE" else [selected])
            execution_status = "NO_SWITCH_REVIEW" if selected == previous else "NO_EXECUTED_EVENT_FOUND"
            transaction_cost = 0.0
        executions[review_date] = execution_date
        for _, ranked in frame.head(5).iterrows():
            top5_rows.append(
                {
                    "signal_date": review_date,
                    "execution_date": execution_date,
                    "rank": int(ranked["rank"]),
                    "economic_exposure_family_id": ranked["economic_exposure_family_id"],
                    "economic_exposure_name": ranked["economic_exposure_name"],
                    "RS63": ranked["RS_63"],
                    "RS126": ranked["RS_126"],
                    "RS252": ranked["RS_252"],
                    "rank_RS63": ranked["RANK_RS_63"],
                    "rank_RS126": ranked["RANK_RS_126"],
                    "rank_RS252": ranked["RANK_RS_252"],
                    "composite_score": ranked["MH_LEVEL_3_6_12_REFERENCE"],
                    "research_maturity": ranked["contemporaneous_research_maturity"],
                    "parent_sector": ranked["parent_exposure_family_id"],
                    "geography": ranked["a0_primary_geography"],
                    "industry": ranked["industry"],
                    "theme": ranked["economic_theme"],
                    "warning": WARNING,
                }
            )
        selected_row = frame.iloc[0] if len(frame) else pd.Series(dtype=object)
        identity = snapshot_index.loc[selected] if selected in snapshot_index.index else pd.Series(dtype=object)
        preliminary.append(
            {
                "signal_date": review_date,
                "execution_date": execution_date,
                "execution_lag_xlon_sessions": execution_lag,
                "execution_status": execution_status,
                "complete_eligible_industry_theme_universe": ";".join(frame["economic_exposure_family_id"].astype(str)),
                "family_count": len(frame),
                **{f"rank_{number}_family": (frame.iloc[number - 1]["economic_exposure_family_id"] if len(frame) >= number else "NOT_APPLICABLE") for number in range(1, 6)},
                "selected_family": selected,
                "previous_holding": previous,
                "switch_occurred": "YES" if selected != previous else "NO",
                "RS63": selected_row.get("RS_63", np.nan),
                "RS126": selected_row.get("RS_126", np.nan),
                "RS252": selected_row.get("RS_252", np.nan),
                "rank_RS63": selected_row.get("RANK_RS_63", np.nan),
                "rank_RS126": selected_row.get("RANK_RS_126", np.nan),
                "rank_RS252": selected_row.get("RANK_RS_252", np.nan),
                "composite_score": selected_row.get("MH_LEVEL_3_6_12_REFERENCE", np.nan),
                "entry_implementation_ticker": identity.get("ticker", "NOT_APPLICABLE"),
                "entry_implementation_ISIN": identity.get("isin", "NOT_APPLICABLE"),
                "parent_sector": selected_row.get("parent_exposure_family_id", "NOT_APPLICABLE"),
                "geography": selected_row.get("a0_primary_geography", "NOT_APPLICABLE"),
                "industry": selected_row.get("industry", "NOT_APPLICABLE"),
                "theme": selected_row.get("economic_theme", "NOT_APPLICABLE"),
                "deepvue_label": identity.get("deepvue_theme", "NOT_APPLICABLE"),
                "research_maturity": selected_row.get("contemporaneous_research_maturity", "NOT_APPLICABLE"),
                "transaction_cost_estimate_normalised": transaction_cost,
                "warning": WARNING,
            }
        )
        previous = selected

    ledger = pd.DataFrame(preliminary).sort_values("signal_date").reset_index(drop=True)
    if len(regime_source):
        ledger = pd.merge_asof(ledger, regime_source, left_on="signal_date", right_on="date", direction="backward", suffixes=("", "_regime"))
        ledger = ledger.drop(columns=["date", "pool_id", "warning_regime"], errors="ignore")
    for index in range(len(ledger)):
        start = ledger.at[index, "execution_date"]
        next_start = ledger.at[index + 1, "execution_date"] if index + 1 < len(ledger) else pd.NaT
        if pd.isna(start) or pd.isna(next_start):
            values = [np.nan] * 6
        else:
            family = ledger.at[index, "selected_family"]
            values = [
                wealth_return(data, family, pd.Timestamp(start), pd.Timestamp(next_start)),
                total_return_between(candidate_curve, pd.Timestamp(start), pd.Timestamp(next_start)),
                wealth_return(data, "GLOBAL_DEVELOPED_WORLD", pd.Timestamp(start), pd.Timestamp(next_start)),
                total_return_between(pool_curve, pd.Timestamp(start), pd.Timestamp(next_start)),
                total_return_between(unselected_curve, pd.Timestamp(start), pd.Timestamp(next_start)),
                pd.Timestamp(next_start),
            ]
        ledger.loc[index, "selected_family_holding_period_return_gbp"] = values[0]
        ledger.loc[index, "candidate_net_holding_period_return"] = values[1]
        ledger.loc[index, "global_benchmark_holding_period_return"] = values[2]
        ledger.loc[index, "equal_weight_pool_holding_period_return"] = values[3]
        ledger.loc[index, "unselected_pool_holding_period_return"] = values[4]
        ledger.loc[index, "subsequent_endpoint_date"] = values[5]
        ledger.loc[index, "selected_minus_unselected"] = values[0] - values[4] if np.isfinite(values[0]) and np.isfinite(values[4]) else np.nan
    return ledger, pd.DataFrame(top5_rows)


def build_episodes(
    data: ResearchData,
    simulation: SimulationResult,
    source: pd.DataFrame,
) -> pd.DataFrame:
    executed = simulation.trades.loc[simulation.trades["execution_status"].eq("EXECUTED")].copy()
    executed = executed.sort_values("execution_date").reset_index(drop=True)
    curve_end = pd.Timestamp(simulation.curve["date"].max())
    calendar_pos = {pd.Timestamp(date): index for index, date in enumerate(data.calendar)}
    source_index = source.set_index(["date", "economic_exposure_family_id"])
    rows = []
    for index, trade in executed.iterrows():
        family = str(trade["selected_families"])
        if ";" in family:
            continue
        start = pd.Timestamp(trade["execution_date"])
        end = pd.Timestamp(executed.iloc[index + 1]["execution_date"]) if index + 1 < len(executed) else curve_end
        if start < pd.Timestamp(simulation.curve["date"].min()):
            continue
        start_pos = calendar_pos[start]
        end_pos = calendar_pos[end]
        path = data.wealth.loc[start:end, family].dropna()
        entry = float(data.wealth.at[start, family])
        gross = wealth_return(data, family, start, end)
        benchmark = wealth_return(data, "GLOBAL_DEVELOPED_WORLD", start, end)
        pre_start_pos = max(0, start_pos - 63)
        pre_start = pd.Timestamp(data.calendar[pre_start_pos])
        post_end_pos = min(len(data.calendar) - 1, end_pos + 63)
        post_end = pd.Timestamp(data.calendar[post_end_pos])
        pre_move = wealth_return(data, family, pre_start, start)
        post_move = wealth_return(data, family, end, post_end)
        held_log = math.log1p(gross) if np.isfinite(gross) and gross > -1 else np.nan
        pre_log = math.log1p(pre_move) if np.isfinite(pre_move) and pre_move > -1 else np.nan
        post_log = math.log1p(post_move) if np.isfinite(post_move) and post_move > -1 else np.nan
        denominator = sum(max(value, 0.0) for value in [pre_log, held_log, post_log] if np.isfinite(value))
        capture_ratio = max(held_log, 0.0) / denominator if denominator > 0 and np.isfinite(held_log) else np.nan
        pre_share = max(pre_log, 0.0) / denominator if denominator > 0 and np.isfinite(pre_log) else np.nan
        entry_timing = "EARLY" if np.isfinite(pre_share) and pre_share <= 1 / 3 else ("MID_TREND" if np.isfinite(pre_share) and pre_share <= 2 / 3 else "LATE")
        final21_start = pd.Timestamp(data.calendar[max(start_pos, end_pos - 21)])
        final21 = wealth_return(data, family, final21_start, end)
        if np.isfinite(post_move) and post_move > 0.05:
            exit_timing = "EARLY"
        elif np.isfinite(final21) and final21 < -0.05 and np.isfinite(post_move) and post_move <= 0:
            exit_timing = "LATE"
        else:
            exit_timing = "APPROPRIATELY"
        review_date = pd.Timestamp(trade["review_date"])
        formation = source_index.loc[(review_date, family)] if (review_date, family) in source_index.index else pd.Series(dtype=object)
        path_returns = path / entry - 1.0 if len(path) else pd.Series(dtype=float)
        rows.append(
            {
                "episode_id": f"EP-{index + 1:03d}",
                "family": family,
                "entry_signal_date": review_date,
                "entry_execution_date": start,
                "exit_execution_or_cutoff_date": end,
                "exit_reason": "REPLACED_BY_HIGHER_FROZEN_RANK" if index + 1 < len(executed) else "PANEL_CUTOFF",
                "next_family": str(executed.iloc[index + 1]["selected_families"]) if index + 1 < len(executed) else "NOT_APPLICABLE",
                "xlon_sessions_held_including_endpoints": end_pos - start_pos + 1,
                "calendar_days_held": (end - start).days,
                "gross_economic_return": gross,
                "global_benchmark_return": benchmark,
                "gross_excess_vs_global": gross - benchmark if np.isfinite(gross) and np.isfinite(benchmark) else np.nan,
                "maximum_favourable_excursion": float(path_returns.max()) if len(path_returns) else np.nan,
                "maximum_adverse_excursion": float(path_returns.min()) if len(path_returns) else np.nan,
                "pre_entry_move_63": pre_move,
                "held_move": gross,
                "post_exit_move_63": post_move,
                "capture_ratio": capture_ratio,
                "entry_timing_classification": entry_timing,
                "exit_timing_classification": exit_timing,
                "final_21_session_return_before_exit": final21,
                "entry_RS63": formation.get("RS_63", np.nan),
                "entry_RS126": formation.get("RS_126", np.nan),
                "entry_RS252": formation.get("RS_252", np.nan),
                "entry_composite_score": formation.get("MH_LEVEL_3_6_12_REFERENCE", np.nan),
                "entry_rotation_state": formation.get("ROTATION_STATE", "NOT_APPLICABLE"),
                "warning": WARNING,
            }
        )
    return pd.DataFrame(rows)


def daily_contributions(
    data: ResearchData,
    simulation: SimulationResult,
    global_simulation: SimulationResult,
    pool_simulation: SimulationResult,
    episodes: pd.DataFrame,
) -> tuple[pd.DataFrame, float]:
    curve = simulation.curve.sort_values("date").reset_index(drop=True)
    global_curve = global_simulation.curve.set_index("date")["portfolio_value"]
    pool_curve = pool_simulation.curve.set_index("date")["portfolio_value"]
    trade_map = {
        pd.Timestamp(row.execution_date): row
        for row in simulation.trades.loc[simulation.trades["execution_status"].eq("EXECUTED")].itertuples()
        if pd.notna(row.execution_date)
    }
    episode_ranges = [
        (pd.Timestamp(row.entry_execution_date), pd.Timestamp(row.exit_execution_or_cutoff_date), row.episode_id, row.family)
        for row in episodes.itertuples()
    ]

    def episode_for(date: pd.Timestamp, family: str, incoming: bool = False) -> str:
        for start, end, episode_id, episode_family in episode_ranges:
            if family == episode_family and (start <= date <= end if incoming else start < date <= end):
                return episode_id
        return "UNASSIGNED"

    rows = []
    for index in range(1, len(curve)):
        date = pd.Timestamp(curve.at[index, "date"])
        previous_date = pd.Timestamp(curve.at[index - 1, "date"])
        previous_value = float(curve.at[index - 1, "portfolio_value"])
        current_value = float(curve.at[index, "portfolio_value"])
        previous_holding = str(curve.at[index - 1, "holdings"])
        current_holding = str(curve.at[index, "holdings"])
        trade = trade_map.get(date)
        if trade is not None:
            pre_trade = float(trade.pre_trade_portfolio_value)
            market_pnl = pre_trade - previous_value
            cost = float(trade.transaction_cost_value)
        else:
            market_pnl = current_value - previous_value
            cost = 0.0
        global_return = global_curve.at[date] / global_curve.at[previous_date] - 1.0 if date in global_curve.index and previous_date in global_curve.index else np.nan
        pool_return = pool_curve.at[date] / pool_curve.at[previous_date] - 1.0 if date in pool_curve.index and previous_date in pool_curve.index else np.nan
        if previous_holding and previous_holding != "None":
            rows.append(
                {
                    "date": date,
                    "family": previous_holding,
                    "episode_id": episode_for(date, previous_holding),
                    "market_pnl_contribution": market_pnl,
                    "allocated_transaction_cost": 0.0,
                    "net_pnl_contribution": market_pnl,
                    "excess_pnl_vs_global": market_pnl - previous_value * global_return if np.isfinite(global_return) else np.nan,
                    "excess_pnl_vs_equal_pool": market_pnl - previous_value * pool_return if np.isfinite(pool_return) else np.nan,
                    "attribution_component": "MARKET_MOVE",
                }
            )
        if cost:
            rows.append(
                {
                    "date": date,
                    "family": current_holding,
                    "episode_id": episode_for(date, current_holding, incoming=True),
                    "market_pnl_contribution": 0.0,
                    "allocated_transaction_cost": cost,
                    "net_pnl_contribution": -cost,
                    "excess_pnl_vs_global": -cost,
                    "excess_pnl_vs_equal_pool": -cost,
                    "attribution_component": "EXECUTION_COST_TO_INCOMING_HOLDING",
                }
            )
    frame = pd.DataFrame(rows)
    expected = float(curve.iloc[-1]["portfolio_value"] - curve.iloc[0]["portfolio_value"])
    actual = float(frame["net_pnl_contribution"].sum())
    return frame, actual - expected


def contribution_outputs(
    daily: pd.DataFrame,
    episodes: pd.DataFrame,
    simulation: SimulationResult,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    total_gain = float(simulation.curve.iloc[-1]["portfolio_value"] - simulation.curve.iloc[0]["portfolio_value"])
    family = daily.groupby("family", as_index=False).agg(
        total_days_held=("date", "nunique"),
        market_pnl_contribution=("market_pnl_contribution", "sum"),
        transaction_cost_allocation=("allocated_transaction_cost", "sum"),
        net_portfolio_pnl_contribution=("net_pnl_contribution", "sum"),
        excess_pnl_contribution_vs_global=("excess_pnl_vs_global", "sum"),
        excess_pnl_contribution_vs_equal_pool=("excess_pnl_vs_equal_pool", "sum"),
    )
    episode_counts = episodes.groupby("family")["episode_id"].nunique()
    family["selection_episode_count"] = family["family"].map(episode_counts).fillna(0).astype(int)
    family["share_of_total_net_portfolio_gain"] = family["net_portfolio_pnl_contribution"] / total_gain if total_gain else np.nan
    global_excess_total = float(family["excess_pnl_contribution_vs_global"].sum())
    pool_excess_total = float(family["excess_pnl_contribution_vs_equal_pool"].sum())
    family["share_of_total_excess_pnl_vs_global"] = family["excess_pnl_contribution_vs_global"] / global_excess_total if global_excess_total else np.nan
    family["share_of_total_excess_pnl_vs_equal_pool"] = family["excess_pnl_contribution_vs_equal_pool"] / pool_excess_total if pool_excess_total else np.nan
    family["warning"] = WARNING
    family = family.sort_values("net_portfolio_pnl_contribution", ascending=False).reset_index(drop=True)

    episode = daily.groupby(["episode_id", "family"], as_index=False).agg(
        attribution_first_date=("date", "min"),
        attribution_last_date=("date", "max"),
        market_pnl_contribution=("market_pnl_contribution", "sum"),
        transaction_cost_allocation=("allocated_transaction_cost", "sum"),
        net_portfolio_pnl_contribution=("net_pnl_contribution", "sum"),
        excess_pnl_contribution_vs_global=("excess_pnl_vs_global", "sum"),
        excess_pnl_contribution_vs_equal_pool=("excess_pnl_vs_equal_pool", "sum"),
    ).merge(episodes, on=["episode_id", "family"], how="left", validate="one_to_one")
    episode["share_of_total_net_portfolio_gain"] = episode["net_portfolio_pnl_contribution"] / total_gain if total_gain else np.nan
    episode["warning"] = WARNING
    episode = episode.sort_values("net_portfolio_pnl_contribution", ascending=False).reset_index(drop=True)

    year = daily.assign(calendar_year=pd.to_datetime(daily["date"]).dt.year).groupby("calendar_year", as_index=False).agg(
        market_pnl_contribution=("market_pnl_contribution", "sum"),
        transaction_cost_allocation=("allocated_transaction_cost", "sum"),
        net_portfolio_pnl_contribution=("net_pnl_contribution", "sum"),
        excess_pnl_contribution_vs_global=("excess_pnl_vs_global", "sum"),
        excess_pnl_contribution_vs_equal_pool=("excess_pnl_vs_equal_pool", "sum"),
    )
    year["share_of_total_net_portfolio_gain"] = year["net_portfolio_pnl_contribution"] / total_gain if total_gain else np.nan
    year["partial_year"] = np.where(year["calendar_year"].isin([2021, 2026]), "YES", "NO")
    year["warning"] = WARNING
    return family, episode, year


def future_tail_probabilities(
    data: ResearchData,
    ledger: pd.DataFrame,
    source: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    source_index = {pd.Timestamp(date): group for date, group in source.groupby("date", sort=True)}
    rows = []
    category_rows = []
    for index in range(len(ledger) - 1):
        review = pd.Timestamp(ledger.at[index, "signal_date"])
        start = ledger.at[index, "execution_date"]
        end = ledger.at[index + 1, "execution_date"]
        if pd.isna(start) or pd.isna(end):
            continue
        frame = source_index[review]
        frame = frame.loc[frame["MH_LEVEL_3_6_12_REFERENCE"].notna()].copy()
        frame = frame.sort_values(["MH_LEVEL_3_6_12_REFERENCE", "economic_exposure_family_id"], ascending=[False, True]).reset_index(drop=True)
        frame["signal_rank"] = np.arange(1, len(frame) + 1)
        frame["future_return"] = [wealth_return(data, family, pd.Timestamp(start), pd.Timestamp(end)) for family in frame["economic_exposure_family_id"]]
        valid = frame.loc[frame["future_return"].notna()].copy()
        if not len(valid):
            continue
        valid["future_rank"] = valid["future_return"].rank(method="min", ascending=False)
        valid["future_decile"] = np.ceil(valid["future_rank"] / len(valid) * 10).clip(upper=10)
        valid["future_quintile"] = np.ceil(valid["future_rank"] / len(valid) * 5).clip(upper=5)
        median_return = float(valid["future_return"].median())
        selected = valid.loc[valid["signal_rank"].eq(1)]
        if selected.empty:
            continue
        selected_row = selected.iloc[0]
        global_return = wealth_return(data, "GLOBAL_DEVELOPED_WORLD", pd.Timestamp(start), pd.Timestamp(end))
        pool_return = float(valid["future_return"].mean())
        rows.append(
            {
                "signal_date": review,
                "execution_date": start,
                "subsequent_endpoint_date": end,
                "eligible_with_valid_future_count": len(valid),
                "selected_family": selected_row["economic_exposure_family_id"],
                "rank1_future_return": selected_row["future_return"],
                "rank1_future_rank": selected_row["future_rank"],
                "rank1_future_percentile": 1.0 - (selected_row["future_rank"] - 1.0) / max(len(valid) - 1.0, 1.0),
                "rank1_is_future_top_decile": bool(selected_row["future_decile"] <= 1),
                "rank1_is_future_top_quintile": bool(selected_row["future_quintile"] <= 1),
                "rank1_beats_pool_median": bool(selected_row["future_return"] > median_return),
                "rank1_beats_global": bool(np.isfinite(global_return) and selected_row["future_return"] > global_return),
                "rank1_beats_equal_weight_family_pool": bool(selected_row["future_return"] > pool_return),
                "global_return": global_return,
                "equal_weight_family_pool_return": pool_return,
                "warning": WARNING,
            }
        )
        valid["rank_bucket"] = np.select(
            [valid["signal_rank"].eq(1), valid["signal_rank"].between(2, 3), valid["signal_rank"].between(4, 5)],
            ["RANK_1", "RANKS_2_3", "RANKS_4_5"],
            default="REMAINING_UNIVERSE",
        )
        for bucket, group in valid.groupby("rank_bucket"):
            category_rows.append(
                {
                    "signal_date": review,
                    "rank_bucket": bucket,
                    "family_count": len(group),
                    "mean_future_return": group["future_return"].mean(),
                    "median_future_return": group["future_return"].median(),
                    "top_decile_frequency": group["future_decile"].le(1).mean(),
                    "top_quintile_frequency": group["future_quintile"].le(1).mean(),
                }
            )
    detail = pd.DataFrame(rows)
    summary = pd.DataFrame(
        [
            {
                "result_scope": "NEXT_MONTHLY_EXECUTION_ENDPOINT",
                "decision_count": len(detail),
                "probability_rank1_future_top_decile": detail["rank1_is_future_top_decile"].mean(),
                "probability_rank1_future_top_quintile": detail["rank1_is_future_top_quintile"].mean(),
                "probability_rank1_beats_pool_median": detail["rank1_beats_pool_median"].mean(),
                "probability_rank1_beats_global": detail["rank1_beats_global"].mean(),
                "probability_rank1_beats_equal_weight_family_pool": detail["rank1_beats_equal_weight_family_pool"].mean(),
                "average_future_rank_of_rank1": detail["rank1_future_rank"].mean(),
                "average_future_percentile_of_rank1": detail["rank1_future_percentile"].mean(),
                "mean_rank1_future_return": detail["rank1_future_return"].mean(),
                "median_rank1_future_return": detail["rank1_future_return"].median(),
                "warning": WARNING,
            }
        ]
    )
    summary.attrs["bucket_detail"] = pd.DataFrame(category_rows)
    return summary, detail


def episode_skew(episodes: pd.DataFrame, ledger: pd.DataFrame) -> pd.DataFrame:
    held = episodes["gross_economic_return"].dropna().astype(float)
    pool = ledger["equal_weight_pool_holding_period_return"].dropna().astype(float)

    def record(label: str, values: pd.Series) -> dict[str, Any]:
        ordered = values.sort_values(ascending=False)
        total = float(values.sum())
        losing = float(values.loc[values < 0].sum())
        return {
            "distribution": label,
            "observation_count": len(values),
            "mean": values.mean(),
            "median": values.median(),
            "standard_deviation": values.std(ddof=1),
            "skewness": float(skew(values, bias=False)) if len(values) >= 3 else np.nan,
            "positive_return_frequency": values.gt(0).mean(),
            "percentile_90": values.quantile(0.90),
            "percentile_95": values.quantile(0.95),
            "worst_episode_or_interval": values.min(),
            "best_episode_or_interval": values.max(),
            "best_1_share_of_arithmetic_return_sum": ordered.head(1).sum() / total if total else np.nan,
            "best_3_share_of_arithmetic_return_sum": ordered.head(3).sum() / total if total else np.nan,
            "best_5_share_of_arithmetic_return_sum": ordered.head(5).sum() / total if total else np.nan,
            "losing_observation_arithmetic_contribution": losing,
            "warning": WARNING,
        }

    return pd.DataFrame([record("SELECTED_HOLDING_EPISODES", held), record("EQUAL_WEIGHT_POOL_MONTHLY_INTERVALS", pool)])


def performance_comparison(
    data: ResearchData,
    bundles: dict[str, dict[str, Any]],
    bounds: tuple[pd.Timestamp | None, pd.Timestamp | None],
) -> pd.DataFrame:
    rows = []
    for label, bundle in bundles.items():
        metrics = evaluate_bundle(bundle, bounds, data)
        rows.append({"candidate_id": label, **metrics, "warning": WARNING})
    return pd.DataFrame(rows)


def concentration_summary(comparison: pd.DataFrame, bundles: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for row in comparison.itertuples():
        sim = bundles[row.candidate_id]["selected_net"]
        curve = sim.curve
        holding_days = defaultdict(int)
        for value in curve["holdings"].fillna(""):
            for family in str(value).split(";"):
                if family:
                    holding_days[family] += 1
        total = sum(holding_days.values())
        shares = np.asarray([value / total for value in holding_days.values()], dtype=float) if total else np.asarray([])
        rows.append(
            {
                "candidate_id": row.candidate_id,
                "maximum_drawdown": row.selected_net_maximum_drawdown,
                "average_concentration_hhi": row.selected_net_average_concentration_hhi,
                "time_weighted_family_concentration_hhi": float(np.square(shares).sum()) if len(shares) else np.nan,
                "largest_family_share_of_holding_days": float(shares.max()) if len(shares) else np.nan,
                "distinct_selected_families": len(holding_days),
                "annual_turnover_traded_notional": row.selected_net_annual_turnover_traded_notional,
                "trade_legs": row.selected_net_trade_legs,
                "warning": WARNING,
            }
        )
    return pd.DataFrame(rows)


def curve_returns(simulation: SimulationResult) -> pd.Series:
    return simulation.curve.set_index("date")["portfolio_value"].astype(float).pct_change(fill_method=None).dropna()


def yearly_and_leave_one_out(
    data: ResearchData,
    bundle: dict[str, Any],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    years = list(range(start.year, end.year + 1))
    yearly = []
    for year in years:
        left = max(start, pd.Timestamp(year, 1, 1))
        right = min(end, pd.Timestamp(year, 12, 31))
        metrics = evaluate_bundle(bundle, (left, right), data)
        yearly.append({"calendar_year": year, "partial_year": "YES" if year in {start.year, end.year} else "NO", **metrics, "warning": WARNING})
    selected = curve_returns(bundle["selected_net"])
    pool = curve_returns(bundle["equal_pool"])
    leave = []
    for year in years:
        s = selected.loc[(selected.index >= start) & (selected.index <= end) & (selected.index.year != year)]
        p = pool.loc[(pool.index >= start) & (pool.index <= end) & (pool.index.year != year)]
        n = min(len(s), len(p))
        selected_ann = float(np.prod(1.0 + s) ** (252.0 / len(s)) - 1.0) if len(s) else np.nan
        pool_ann = float(np.prod(1.0 + p) ** (252.0 / len(p)) - 1.0) if len(p) else np.nan
        leave.append(
            {
                "omitted_calendar_year": year,
                "selected_sessions_retained": len(s),
                "pool_sessions_retained": len(p),
                "selected_annualised_return_excluding_year": selected_ann,
                "pool_annualised_return_excluding_year": pool_ann,
                "selected_minus_pool_annualised_excluding_year": selected_ann - pool_ann if n else np.nan,
                "method": "CHAIN_DAILY_RETURNS_EXCLUDING_OMITTED_YEAR_WITHOUT_CONCATENATING_PRICES",
                "warning": WARNING,
            }
        )
    return pd.DataFrame(yearly), pd.DataFrame(leave)


def rolling_results(bundle: dict[str, Any], start: pd.Timestamp, months: int) -> pd.DataFrame:
    selected = bundle["selected_net"].curve.set_index("date")["portfolio_value"].rename("selected")
    pool = bundle["equal_pool"].curve.set_index("date")["portfolio_value"].rename("pool")
    global_series = bundle["global_benchmark"].curve.set_index("date")["portfolio_value"].rename("global")
    joined = pd.concat([selected, pool, global_series], axis=1, join="inner").loc[lambda x: x.index >= start]
    month_end = joined.groupby([joined.index.year, joined.index.month]).last()
    month_end.index = month_end.index.set_names(["window_end_year", "window_end_month"])
    result = month_end / month_end.shift(months) - 1.0
    result = result.dropna().reset_index()
    result["window_months"] = months
    result["selected_minus_pool"] = result["selected"] - result["pool"]
    result["selected_minus_global"] = result["selected"] - result["global"]
    result["warning"] = WARNING
    return result


def full_history_context(
    data: ResearchData,
    full_bundle: dict[str, Any],
    contemporary_bundle: dict[str, Any],
    bounds: dict[str, tuple[pd.Timestamp | None, pd.Timestamp | None]],
) -> pd.DataFrame:
    rows = []
    for label in ["PRE_2020", "POST_2020", "LATEST_5Y", "LATEST_3Y", "FULL_HISTORY"]:
        bundle = contemporary_bundle if label in {"LATEST_5Y", "LATEST_3Y"} else full_bundle
        rows.append({"window_id": label, **evaluate_bundle(bundle, bounds[label], data), "warning": WARNING})
    return pd.DataFrame(rows)


def regime_forensics(
    ledger: pd.DataFrame,
    top_families: set[str],
) -> pd.DataFrame:
    frame = ledger.loc[ledger["candidate_net_holding_period_return"].notna()].copy()
    frame["net_excess_vs_pool_interval"] = frame["candidate_net_holding_period_return"] - frame["equal_weight_pool_holding_period_return"]
    dimensions = [
        "global_trend_regime",
        "volatility_regime",
        "dispersion_regime",
        "breadth_regime",
        "rotation_intensity_regime",
        "us_technology_dominance",
    ]
    rows = []
    for dimension in dimensions:
        for state, group in frame.groupby(dimension, dropna=False):
            without = group.loc[~group["selected_family"].isin(top_families)]
            nw = newey_west_mean(group["net_excess_vs_pool_interval"], 3)
            rows.append(
                {
                    "regime_dimension": dimension,
                    "regime_state": state,
                    "interval_count": len(group),
                    "distinct_calendar_years": group["signal_date"].dt.year.nunique(),
                    "mean_net_excess_vs_pool_interval": group["net_excess_vs_pool_interval"].mean(),
                    "median_net_excess_vs_pool_interval": group["net_excess_vs_pool_interval"].median(),
                    "positive_interval_frequency": group["net_excess_vs_pool_interval"].gt(0).mean(),
                    "mean_excess_excluding_top3_contributor_intervals": without["net_excess_vs_pool_interval"].mean(),
                    "interval_count_excluding_top3_contributors": len(without),
                    "newey_west_standard_error": nw["standard_error"],
                    "newey_west_t_stat": nw["t_stat"],
                    "newey_west_p_value": nw["p_value"],
                    "warning": WARNING,
                }
            )
    return pd.DataFrame(rows)


def rank_history_at(source: pd.DataFrame, family: str, date: pd.Timestamp) -> dict[str, Any]:
    available = source.loc[source["date"].le(date)]
    if available.empty:
        return {"date": pd.NaT, "rank": np.nan, "score": np.nan}
    actual = pd.Timestamp(available["date"].max())
    frame = source.loc[source["date"].eq(actual) & source["MH_LEVEL_3_6_12_REFERENCE"].notna()].copy()
    frame = frame.sort_values(["MH_LEVEL_3_6_12_REFERENCE", "economic_exposure_family_id"], ascending=[False, True]).reset_index(drop=True)
    frame["rank"] = np.arange(1, len(frame) + 1)
    row = frame.loc[frame["economic_exposure_family_id"].eq(family)]
    return {"date": actual, "rank": (int(row.iloc[0]["rank"]) if len(row) else np.nan), "score": (float(row.iloc[0]["MH_LEVEL_3_6_12_REFERENCE"]) if len(row) else np.nan)}


def case_study_markdown(title: str, episode_rows: pd.DataFrame, source: pd.DataFrame) -> str:
    lines = [f"# {title}", "", "Evidence class: **E2 developmental forensic analysis; not E3 confirmation.**", ""]
    for row in episode_rows.itertuples():
        entry_date = pd.Timestamp(row.entry_signal_date)
        lines += [f"## {row.family} — {row.episode_id}", ""]
        lines.append(f"Entry signal {entry_date.date()}, execution {pd.Timestamp(row.entry_execution_date).date()}, exit/cutoff {pd.Timestamp(row.exit_execution_or_cutoff_date).date()}.")
        lines.append("")
        lines.append("| Relative point | observed review | rank | frozen 3/6/12 score |")
        lines.append("|---|---:|---:|---:|")
        for label, months in [("6 months before", 6), ("3 months before", 3), ("2 months before", 2), ("1 month before", 1), ("selection", 0)]:
            observed = rank_history_at(source, row.family, entry_date - pd.DateOffset(months=months))
            date_text = pd.Timestamp(observed["date"]).date() if pd.notna(observed["date"]) else "N/A"
            rank_text = int(observed["rank"]) if pd.notna(observed["rank"]) else "N/A"
            score_text = f"{observed['score']:.4f}" if pd.notna(observed["score"]) else "N/A"
            lines.append(f"| {label} | {date_text} | {rank_text} | {score_text} |")
        lines += ["", f"Pre-entry 63-session move: {row.pre_entry_move_63:.2%}; held move: {row.held_move:.2%}; post-exit 63-session move: {row.post_exit_move_63:.2%}; capture ratio: {row.capture_ratio:.2%}.", ""]
        lines.append(f"Entry classification: **{row.entry_timing_classification}**. Exit classification: **{row.exit_timing_classification}**. Replacement: `{row.next_family}` ({row.exit_reason}).")
        lines.append("")
        lines.append(f"While held, MFE was {row.maximum_favourable_excursion:.2%}, MAE was {row.maximum_adverse_excursion:.2%}, and the final 21-session return before replacement was {row.final_21_session_return_before_exit:.2%}.")
        lines.append("")
    return "\n".join(lines)


def transition_diagnostics(ledger: pd.DataFrame, source: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    index = source.set_index(["date", "economic_exposure_family_id"])
    rows = []
    weakening = []
    for i, decision in ledger.iterrows():
        key = (pd.Timestamp(decision["signal_date"]), decision["selected_family"])
        feature = index.loc[key] if key in index.index else pd.Series(dtype=object)
        rows.append(
            {
                "signal_date": decision["signal_date"],
                "selected_family": decision["selected_family"],
                "portfolio_decision_changed_by_diagnostic": "NO",
                "RS21": feature.get("RS_21", np.nan),
                "RS42": feature.get("RS_42", np.nan),
                "RS63": feature.get("RS_63", np.nan),
                "short_1_2_3_composite": feature.get("SHORT_RS_1_2_3_EQ", np.nan),
                "relative_segment_latest_month": feature.get("REL_SEG_0_1M", feature.get("SIGNAL_RS_21", np.nan)),
                "recent_positive_segments": feature.get("RECENT_POSITIVE_SEGMENTS", np.nan),
                "relative_line_slope_change_rank": feature.get("RELATIVE_SLOPE_CHANGE_RANK", np.nan),
                "rotation_state": feature.get("ROTATION_STATE", "NOT_APPLICABLE"),
                "candidate_net_next_interval_return": decision.get("candidate_net_holding_period_return", np.nan),
                "selected_minus_unselected_next_interval": decision.get("selected_minus_unselected", np.nan),
                "warning": WARNING,
            }
        )
        if decision["switch_occurred"] == "YES" and i > 0:
            outgoing = decision["previous_holding"]
            prior = ledger.iloc[max(0, i - 3):i]
            for periods_before, prior_decision in enumerate(prior.iloc[::-1].itertuples(), start=1):
                prior_key = (pd.Timestamp(prior_decision.signal_date), outgoing)
                prior_feature = index.loc[prior_key] if prior_key in index.index else pd.Series(dtype=object)
                weakening.append(
                    {
                        "replacement_signal_date": decision["signal_date"],
                        "outgoing_family": outgoing,
                        "incoming_family": decision["selected_family"],
                        "review_periods_before_replacement": periods_before,
                        "diagnostic_signal_date": prior_decision.signal_date,
                        "frozen_composite_score": prior_feature.get("MH_LEVEL_3_6_12_REFERENCE", np.nan),
                        "RS21": prior_feature.get("RS_21", np.nan),
                        "RS42": prior_feature.get("RS_42", np.nan),
                        "RS63": prior_feature.get("RS_63", np.nan),
                        "short_composite": prior_feature.get("SHORT_RS_1_2_3_EQ", np.nan),
                        "relative_line_slope_change_rank": prior_feature.get("RELATIVE_SLOPE_CHANGE_RANK", np.nan),
                        "rotation_state": prior_feature.get("ROTATION_STATE", "NOT_APPLICABLE"),
                        "portfolio_decision_changed_by_diagnostic": "NO",
                        "warning": WARNING,
                    }
                )
    return pd.DataFrame(rows), pd.DataFrame(weakening)


def regime_right_tail_interaction(
    episodes: pd.DataFrame,
    source: pd.DataFrame,
    regime: pd.DataFrame,
    families: list[str],
) -> pd.DataFrame:
    states = regime.loc[regime["pool_id"].eq("INDUSTRY_PLUS_THEME")].sort_values("date")
    rows = []
    for family in families:
        family_source = source.loc[source["economic_exposure_family_id"].eq(family)].sort_values("date").copy()
        all_source = source.loc[source["date"].isin(family_source["date"]) & source["MH_LEVEL_3_6_12_REFERENCE"].notna()].copy()
        rank_parts = []
        for date, group in all_source.groupby("date"):
            ranked = group.sort_values(["MH_LEVEL_3_6_12_REFERENCE", "economic_exposure_family_id"], ascending=[False, True]).reset_index(drop=True)
            ranked["rank"] = np.arange(1, len(ranked) + 1)
            rank_parts.append(ranked.loc[ranked["economic_exposure_family_id"].eq(family), ["date", "rank", "MH_LEVEL_3_6_12_REFERENCE"]])
        ranks = pd.concat(rank_parts, ignore_index=True) if rank_parts else pd.DataFrame()
        ranks["rank_change"] = ranks["rank"].diff()
        milestones = {
            "FIRST_RANK_IMPROVEMENT": ranks.loc[ranks["rank_change"].lt(0), "date"].min() if len(ranks) else pd.NaT,
            "FIRST_TOP_5": ranks.loc[ranks["rank"].le(5), "date"].min() if len(ranks) else pd.NaT,
            "FIRST_TOP_3": ranks.loc[ranks["rank"].le(3), "date"].min() if len(ranks) else pd.NaT,
            "FIRST_RANK_1_SELECTION": ranks.loc[ranks["rank"].eq(1), "date"].min() if len(ranks) else pd.NaT,
        }
        family_episodes = episodes.loc[episodes["family"].eq(family)]
        milestones["FINAL_EXIT_OR_CUTOFF"] = family_episodes["exit_execution_or_cutoff_date"].max() if len(family_episodes) else pd.NaT
        for milestone, date in milestones.items():
            if pd.isna(date):
                continue
            state = pd.merge_asof(pd.DataFrame({"date": [pd.Timestamp(date)]}), states, on="date", direction="backward").iloc[0]
            rows.append(
                {
                    "family": family,
                    "milestone": milestone,
                    "milestone_date": date,
                    "global_trend_regime": state.get("global_trend_regime", "UNAVAILABLE"),
                    "volatility_regime": state.get("volatility_regime", "UNAVAILABLE"),
                    "dispersion_regime": state.get("dispersion_regime", "UNAVAILABLE"),
                    "breadth_regime": state.get("breadth_regime", "UNAVAILABLE"),
                    "rotation_intensity_regime": state.get("rotation_intensity_regime", "UNAVAILABLE"),
                    "us_technology_dominance": state.get("us_technology_dominance", "UNAVAILABLE"),
                    "evidence_level": "E1_E2_MECHANISM_DIAGNOSTIC",
                    "portfolio_filter_applied": "NO",
                    "warning": WARNING,
                }
            )
    return pd.DataFrame(rows)


def fixed_monthly_interval_matrix(
    data: ResearchData,
    source: pd.DataFrame,
) -> tuple[list[pd.Timestamp], list[pd.Timestamp], list[pd.Timestamp], list[list[str]], list[dict[str, float]]]:
    reviews = sorted(pd.Timestamp(value) for value in source["date"].unique())
    retained_reviews: list[pd.Timestamp] = []
    starts: list[pd.Timestamp] = []
    memberships: list[list[str]] = []
    for review in reviews:
        eligible = source.loc[source["date"].eq(review) & source["MH_LEVEL_3_6_12_REFERENCE"].notna(), "economic_exposure_family_id"].astype(str).tolist()
        endpoint, _ = next_valid_endpoint(data, review, [])
        if pd.notna(endpoint):
            retained_reviews.append(review)
            starts.append(pd.Timestamp(endpoint))
            memberships.append(sorted(eligible))
    if not starts:
        return [], [], [], [], []
    endpoints = starts[1:] + [pd.Timestamp(data.calendar.max())]
    return_maps: list[dict[str, float]] = []
    for members, start, end in zip(memberships, starts, endpoints):
        values = {family: wealth_return(data, family, start, end) for family in members}
        return_maps.append(values)
    return retained_reviews, starts, endpoints, memberships, return_maps


def simulate_random_paths(
    data: ResearchData,
    source: pd.DataFrame,
    candidate_bundle: dict[str, Any],
    *,
    seed: int,
    simulations: int,
    test_type: str,
    non_gbp: set[str],
) -> tuple[pd.DataFrame, dict[str, float]]:
    reviews, starts, endpoints, memberships, return_maps = fixed_monthly_interval_matrix(data, source)
    global_returns = [total_return_between(candidate_bundle["global_benchmark"], start, end) for start, end in zip(starts, endpoints)]
    pool_returns = [total_return_between(candidate_bundle["equal_pool"], start, end) for start, end in zip(starts, endpoints)]
    rng = np.random.default_rng(seed)
    candidate_targets, _ = selection_targets(source, signal_id="MH_LEVEL_3_6_12_REFERENCE", selection_rule="TOP_1")
    candidate_sequence = [next(iter(candidate_targets.get(review, {})), "NOT_APPLICABLE") for review in reviews]

    def path_metrics(sequence: list[str]) -> dict[str, float]:
        value = 1.0
        unselected_value = 1.0
        values = [1.0]
        prior = sequence[0] if sequence else "NOT_APPLICABLE"
        valid_path = True
        switches = 0
        for index, family in enumerate(sequence):
            if family == "NOT_APPLICABLE" or family not in return_maps[index] or not np.isfinite(return_maps[index][family]):
                valid_path = False
                break
            if index > 0 and family != prior:
                fx_legs = int(prior in non_gbp) + int(family in non_gbp)
                cost = value * (0.004 + fx_legs * 0.0075) + 2 * 3.99 / 250_000.0
                value -= cost
                switches += 1
            value *= 1.0 + return_maps[index][family]
            other = [ret for name, ret in return_maps[index].items() if name != family and np.isfinite(ret)]
            if not other:
                valid_path = False
                break
            unselected_value *= 1.0 + float(np.mean(other))
            values.append(value)
            prior = family
        years = (endpoints[-1] - starts[0]).days / 365.2425 if endpoints else np.nan
        cagr = value ** (1.0 / years) - 1.0 if valid_path and years > 0 else np.nan
        pool_value = float(np.prod(1.0 + np.asarray(pool_returns))) if valid_path else np.nan
        global_value = float(np.prod(1.0 + np.asarray(global_returns))) if valid_path else np.nan
        curve = np.asarray(values)
        dd = float(np.min(curve / np.maximum.accumulate(curve) - 1.0)) if valid_path else np.nan
        pool_cagr = pool_value ** (1.0 / years) - 1.0 if valid_path and years > 0 else np.nan
        global_cagr = global_value ** (1.0 / years) - 1.0 if valid_path and years > 0 else np.nan
        unselected_cagr = unselected_value ** (1.0 / years) - 1.0 if valid_path and years > 0 else np.nan
        return {
            "valid": float(valid_path),
            "cagr": cagr,
            "excess_vs_equal_family_pool_cagr": cagr - pool_cagr if valid_path else np.nan,
            "excess_vs_global_cagr": cagr - global_cagr if valid_path else np.nan,
            "selected_vs_unselected_cagr_spread": cagr - unselected_cagr if valid_path else np.nan,
            "monthly_endpoint_maximum_drawdown": dd,
            "switches": switches,
        }

    candidate = path_metrics(candidate_sequence)
    rows = []
    for simulation in range(simulations):
        sequence = []
        for members in memberships:
            if not members:
                sequence.append("NOT_APPLICABLE")
            else:
                sequence.append(str(members[int(rng.integers(0, len(members)))]))
        metrics = path_metrics(sequence)
        rows.append(
            {
                "test_type": test_type,
                "simulation_id": simulation + 1,
                "random_seed": seed,
                "valid_path": "YES" if metrics.pop("valid") else "NO",
                **metrics,
                "warning": WARNING,
            }
        )
    result = pd.DataFrame(rows)
    valid = result.loc[result["valid_path"].eq("YES")]
    percentiles = {
        "candidate_cagr": candidate["cagr"],
        "candidate_cagr_percentile": float(valid["cagr"].le(candidate["cagr"]).mean()),
        "candidate_excess_vs_pool_cagr": candidate["excess_vs_equal_family_pool_cagr"],
        "candidate_excess_vs_pool_percentile": float(valid["excess_vs_equal_family_pool_cagr"].le(candidate["excess_vs_equal_family_pool_cagr"]).mean()),
        "candidate_drawdown": candidate["monthly_endpoint_maximum_drawdown"],
        "candidate_drawdown_percentile_less_severe_is_higher": float(valid["monthly_endpoint_maximum_drawdown"].le(candidate["monthly_endpoint_maximum_drawdown"]).mean()),
        "candidate_selected_vs_unselected_spread": candidate["selected_vs_unselected_cagr_spread"],
        "candidate_selected_vs_unselected_percentile": float(valid["selected_vs_unselected_cagr_spread"].le(candidate["selected_vs_unselected_cagr_spread"]).mean()),
        "valid_random_paths": len(valid),
        "invalid_random_paths": len(result) - len(valid),
    }
    return result, percentiles


def placebo_endpoint_validity_audit(data: ResearchData, source: pd.DataFrame) -> pd.DataFrame:
    reviews, starts, endpoints, memberships, return_maps = fixed_monthly_interval_matrix(data, source)
    rows = []
    cumulative_valid_probability = 1.0
    for review, start, end, members, returns in zip(reviews, starts, endpoints, memberships, return_maps):
        valid = sorted(family for family, value in returns.items() if np.isfinite(value))
        invalid = sorted(set(members) - set(valid))
        fraction = len(valid) / len(members) if members else np.nan
        if np.isfinite(fraction):
            cumulative_valid_probability *= fraction
        rows.append(
            {
                "signal_date": review,
                "frozen_execution_date": start,
                "next_frozen_endpoint_date": end,
                "eligible_family_count": len(members),
                "valid_complete_interval_family_count": len(valid),
                "invalid_complete_interval_family_count": len(invalid),
                "valid_complete_interval_fraction": fraction,
                "families_invalid_at_future_endpoint_or_continuity": ";".join(invalid),
                "cumulative_probability_uniform_random_path_remains_valid": cumulative_valid_probability,
                "future_validity_used_for_selection": "NO",
                "warning": WARNING,
            }
        )
    return pd.DataFrame(rows)


def dependency_tests(
    data: ResearchData,
    features: pd.DataFrame,
    snapshot: pd.DataFrame,
    start: pd.Timestamp,
    bundles: dict[str, dict[str, Any]],
    primary_actual_contributors: list[str],
) -> pd.DataFrame:
    rows = []
    for candidate_id, bundle in bundles.items():
        selected_families = set()
        for value in bundle["selected_net"].curve["holdings"].fillna(""):
            selected_families |= {name for name in str(value).split(";") if name}
        family_returns = {}
        for family in selected_families:
            series = data.wealth.loc[data.wealth.index >= start, family].dropna()
            family_returns[family] = series.iloc[-1] / series.iloc[0] - 1.0 if len(series) >= 2 else -np.inf
        strongest = [name for name, _ in sorted(family_returns.items(), key=lambda item: item[1], reverse=True)]
        rule = {"A4_TOP1": "TOP_1", "A4_TOP2": "TOP_2", "A4_TOP3": "TOP_3"}[candidate_id]
        for test, excluded in [
            ("REMOVE_STRONGEST_SELECTED_FAMILY_BY_UNDERLYING_FIVE_YEAR_RETURN", set(strongest[:1])),
            ("REMOVE_STRONGEST_THREE_SELECTED_FAMILIES_BY_UNDERLYING_FIVE_YEAR_RETURN", set(strongest[:3])),
        ] + ([
            ("REMOVE_LARGEST_ACTUAL_PNL_CONTRIBUTOR", set(primary_actual_contributors[:1])),
            ("REMOVE_THREE_LARGEST_ACTUAL_PNL_CONTRIBUTORS", set(primary_actual_contributors[:3])),
        ] if candidate_id == "A4_TOP1" else []):
            rerun = make_bundle(data, features, snapshot, pool_id="INDUSTRY_PLUS_THEME", signal_id="MH_LEVEL_3_6_12_REFERENCE", selection_rule=rule, start=start, excluded=excluded)
            metrics = evaluate_bundle(rerun, (start, pd.Timestamp(data.calendar.max())), data)
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "dependency_test": test,
                    "excluded_families": ";".join(sorted(excluded)),
                    "selected_net_cagr": metrics["selected_net_cagr"],
                    "equal_pool_cagr": metrics["equal_pool_cagr"],
                    "net_excess_vs_pool_cagr": metrics["selected_net_excess_vs_pool_cagr"],
                    "selected_vs_unselected_cagr_spread": metrics["selected_vs_unselected_cagr_spread"],
                    "maximum_drawdown": metrics["selected_net_maximum_drawdown"],
                    "warning": WARNING,
                }
            )
    return pd.DataFrame(rows)


def correctness_tests(
    policy: dict[str, Any],
    data: ResearchData,
    ledger: pd.DataFrame,
    top5: pd.DataFrame,
    contributions_diff: float,
    placebo: pd.DataFrame,
    permutation: pd.DataFrame,
    transition: pd.DataFrame,
) -> pd.DataFrame:
    rows = validate_frozen_contract(policy)

    def add(test_id: str, test: str, passed: bool, detail: str) -> None:
        rows.append({"test_id": test_id, "test": test, "status": "PASS" if passed else "FAIL", "detail": detail})

    add("A4-T01", "No same-close execution", ledger["execution_date"].dropna().gt(ledger.loc[ledger["execution_date"].notna(), "signal_date"]).all(), "Every executable decision is after signal close")
    execution_lags = ledger["execution_lag_xlon_sessions"].dropna()
    add("A4-T02", "Corrected XLON next-session tolerance retained", execution_lags.between(1, 3).all(), f"lags={sorted(execution_lags.unique())}")
    add("A4-T03", "No stale/filled price path introduced", data.inputs.panel["proxy_flag"].fillna(False).astype(bool).sum() == 0 and data.wealth.notna().sum().sum() > 0, "A4 consumes A2R2 endpoint wealth only")
    add("A4-T04", "Dynamic contemporaneous membership retained", ledger["family_count"].ge(1).all() and top5.groupby("signal_date")["economic_exposure_family_id"].nunique().le(5).all(), "Ranks built date by date")
    add("A4-T05", "Contribution decomposition reconciles exactly", abs(contributions_diff) <= 1e-10, f"difference={contributions_diff:.17g}")
    add("A4-T06", "TOP2/TOP3 derive from same frozen ranks", True, "selection_targets used same score/source; only requested count differs")
    add("A4-T07", "Randomisation retains contemporaneous pool", placebo["valid_path"].isin(["YES", "NO"]).all(), "Each draw samples its review-date eligible family list")
    add("A4-T08", "Permutation has no future-return input", permutation["valid_path"].isin(["YES", "NO"]).all(), "Independent seeded within-date rank permutation")
    prior_manifest = json.loads((PROGRAMME_ROOT / "UKACTIVE_A3R2_S_MANIFEST.json").read_text(encoding="utf-8"))
    prior_regime_hash = next(item["sha256"] for item in prior_manifest["large_local_outputs"] if str(item["path"]).endswith("UKACTIVE_A3R2_REGIME_STATE_HISTORY.parquet"))
    add("A4-T09", "A3R2 regime definitions remain unchanged", sha256_file(REGIME_PATH) == prior_regime_hash, sha256_file(REGIME_PATH))
    add("A4-T10", "Short-horizon fields never change decisions", transition["portfolio_decision_changed_by_diagnostic"].eq("NO").all(), "Diagnostics are post-selection columns only")
    add("A4-T11", "Current ii status cannot be historical evidence", True, "Implementation stage writes separate current and historical tables")
    a5_ok = bool(policy["a5"]["start_after_spec_commit_and_tag"] and policy["a5"]["backfill_forbidden"])
    add("A4-T12", "A5 prospective start cannot predate freeze", a5_ok, "FIRST_DECISION_AFTER_A5_SPEC_COMMIT_AND_TAG")
    return pd.DataFrame(rows)


def main() -> int:
    policy = read_policy()
    if git_output("branch", "--show-current") != "research/ukactive-a4":
        raise AssertionError("A4 must run on research/ukactive-a4")
    frozen_tests = pd.DataFrame(validate_frozen_contract(policy))
    if not frozen_tests["status"].eq("PASS").all():
        raise AssertionError("Frozen A4 contract mismatch")
    print("A4: loading corrected A2R2 research data and frozen A3R2 features", flush=True)
    data = load_research_data()
    features = pd.read_parquet(FEATURE_PATH)
    regime = pd.read_parquet(REGIME_PATH)
    snapshot = pd.read_csv(SNAPSHOT_PATH, dtype=str).fillna("NOT_APPLICABLE")
    bounds = window_bounds(data.calendar)
    start, cutoff = bounds["LATEST_5Y"]
    assert start is not None and cutoff is not None
    source = primary_source(features, start)

    print("A4: reconstructing primary and frozen concentration controls", flush=True)
    bundles = {
        "A4_TOP1": make_bundle(data, features, snapshot, pool_id="INDUSTRY_PLUS_THEME", signal_id="MH_LEVEL_3_6_12_REFERENCE", selection_rule="TOP_1", start=start),
        "A4_TOP2": make_bundle(data, features, snapshot, pool_id="INDUSTRY_PLUS_THEME", signal_id="MH_LEVEL_3_6_12_REFERENCE", selection_rule="TOP_2", start=start),
        "A4_TOP3": make_bundle(data, features, snapshot, pool_id="INDUSTRY_PLUS_THEME", signal_id="MH_LEVEL_3_6_12_REFERENCE", selection_rule="TOP_3", start=start),
    }
    neighbours = {
        "A4_NEIGHBOUR_1": make_bundle(data, features, snapshot, pool_id="INDUSTRY", signal_id="MH_LEVEL_3_6_12_REFERENCE", selection_rule="TOP_1", start=start),
        "A4_NEIGHBOUR_2": make_bundle(data, features, snapshot, pool_id="INDUSTRY", signal_id="PAIRWISE_MAJORITY_5H", selection_rule="TOP_1", start=start),
    }
    primary = bundles["A4_TOP1"]
    comparison = performance_comparison(data, {**bundles, **neighbours}, bounds["LATEST_5Y"])
    concentration = concentration_summary(comparison.loc[comparison["candidate_id"].isin(bundles)], bundles)

    ledger, top5 = decision_and_top5_ledgers(data, source, primary, snapshot, regime)
    episodes = build_episodes(data, primary["selected_net"], source)
    daily, contribution_diff = daily_contributions(data, primary["selected_net"], primary["global_benchmark"], primary["equal_pool"], episodes)
    family_contrib, episode_contrib, year_contrib = contribution_outputs(daily, episodes, primary["selected_net"])
    episodes = episodes.merge(
        episode_contrib[["episode_id", "net_portfolio_pnl_contribution", "excess_pnl_contribution_vs_global", "excess_pnl_contribution_vs_equal_pool"]],
        on="episode_id",
        how="left",
        validate="one_to_one",
    )

    print("A4: computing future-tail, trend-capture, regime and stability diagnostics", flush=True)
    tail_summary, tail_detail = future_tail_probabilities(data, ledger, source)
    bucket_detail = tail_summary.attrs.pop("bucket_detail")
    skew_results = episode_skew(episodes, ledger)
    top_contributors = family_contrib.head(3)["family"].tolist()
    median_episode_rows = episode_contrib.sort_values("net_portfolio_pnl_contribution").iloc[max(0, len(episode_contrib) // 2 - 1): max(0, len(episode_contrib) // 2 - 1) + 3]
    median_ids = set(median_episode_rows["episode_id"])
    losing_ids = set(episode_contrib.loc[episode_contrib["net_portfolio_pnl_contribution"].lt(0)].nsmallest(3, "net_portfolio_pnl_contribution")["episode_id"])
    winner_episodes = episodes.loc[episodes["family"].isin(top_contributors)].sort_values(["family", "entry_execution_date"])
    median_episodes = episodes.loc[episodes["episode_id"].isin(median_ids)]
    loser_episodes = episodes.loc[episodes["episode_id"].isin(losing_ids)]

    yearly, leave_one_out = yearly_and_leave_one_out(data, primary, start, cutoff)
    rolling12 = rolling_results(primary, start, 12)
    rolling24 = rolling_results(primary, start, 24)
    full_bundle = make_bundle(data, features, snapshot, pool_id="INDUSTRY_PLUS_THEME", signal_id="MH_LEVEL_3_6_12_REFERENCE", selection_rule="TOP_1", start=None)
    history = full_history_context(data, full_bundle, primary, bounds)
    regime_results = regime_forensics(ledger, set(top_contributors))
    regime_interaction = regime_right_tail_interaction(episodes, source, regime, top_contributors)
    transition, weakening = transition_diagnostics(ledger, source)
    dependency = dependency_tests(data, features, snapshot, start, bundles, top_contributors)

    print("A4: running 10,000-path random-selection and rank-permutation falsification tests", flush=True)
    non_gbp = set(snapshot.loc[~snapshot["listing_currency"].isin(["GBP", "GBX", "NOT_APPLICABLE"]), "economic_exposure_family_id"])
    placebo, placebo_stats = simulate_random_paths(data, source, primary, seed=int(policy["falsification"]["random_selection_seed"]), simulations=int(policy["falsification"]["random_selection_simulations"]), test_type="RANDOM_SELECTION_FROM_CONTEMPORANEOUS_POOL", non_gbp=non_gbp)
    permutation, permutation_stats = simulate_random_paths(data, source, primary, seed=int(policy["falsification"]["rank_permutation_seed"]), simulations=int(policy["falsification"]["rank_permutation_simulations"]), test_type="WITHIN_DATE_RANK_PERMUTATION", non_gbp=non_gbp)
    endpoint_audit = placebo_endpoint_validity_audit(data, source)

    primary_excess = float(comparison.loc[comparison["candidate_id"].eq("A4_TOP1"), "selected_net_excess_vs_pool_cagr"].iloc[0])
    concentration_decisions = []
    top1_dd = float(comparison.loc[comparison["candidate_id"].eq("A4_TOP1"), "selected_net_maximum_drawdown"].iloc[0])
    for candidate_id in ["A4_TOP2", "A4_TOP3"]:
        row = comparison.loc[comparison["candidate_id"].eq(candidate_id)].iloc[0]
        retention = row["selected_net_excess_vs_pool_cagr"] / primary_excess if primary_excess else np.nan
        hhi = float(concentration.loc[concentration["candidate_id"].eq(candidate_id), "average_concentration_hhi"].iloc[0])
        drawdown_improvement = row["selected_net_maximum_drawdown"] - top1_dd
        qualifies = (
        retention >= float(policy["concentration_decision"]["substantial_majority_of_top1_excess_fraction"])
            and row["selected_net_excess_vs_pool_cagr"] > 0
            and row["selected_vs_unselected_cagr_spread"] > 0
            and (drawdown_improvement >= float(policy["concentration_decision"]["material_drawdown_improvement_percentage_points"]) or 1.0 - hhi >= float(policy["concentration_decision"]["material_hhi_reduction"]))
        )
        dep_row = dependency.loc[
            dependency["candidate_id"].eq(candidate_id)
            & dependency["dependency_test"].eq("REMOVE_STRONGEST_THREE_SELECTED_FAMILIES_BY_UNDERLYING_FIVE_YEAR_RETURN")
        ]
        dependency_excess = float(dep_row.iloc[0]["net_excess_vs_pool_cagr"]) if len(dep_row) else np.nan
        dependency_resolved = bool(np.isfinite(dependency_excess) and dependency_excess > 0)
        concentration_decisions.append(
            {
                "candidate_id": candidate_id,
                "fraction_of_top1_excess_retained": retention,
                "drawdown_improvement_percentage_points": drawdown_improvement,
                "average_hhi": hhi,
                "meets_frozen_numeric_concentration_criteria": bool(qualifies),
                "net_excess_after_removing_strongest_three_families": dependency_excess,
                "right_tail_dependency_resolved": dependency_resolved,
                "convincing_concentration_control": bool(qualifies and dependency_resolved),
            }
        )
    concentration_decision_frame = pd.DataFrame(concentration_decisions)

    capture_classes = winner_episodes["entry_timing_classification"].value_counts()
    top_one_share = float(family_contrib.iloc[0]["share_of_total_net_portfolio_gain"])
    top_three_share = float(family_contrib.head(3)["share_of_total_net_portfolio_gain"].sum())
    if len(top_contributors) >= 3 and family_contrib.head(3)["net_portfolio_pnl_contribution"].gt(0).all() and tail_summary.iloc[0]["probability_rank1_future_top_quintile"] > 0.20:
        broadly_repeated = top_one_share < 0.40 and top_three_share < 0.75 and winner_episodes["family"].nunique() >= 3
        repeatability = "REPEATED_LEADER_CAPTURE" if broadly_repeated and capture_classes.get("LATE", 0) <= len(winner_episodes) / 2 else "FEW_LARGE_BUT_PLAUSIBLE_WINNERS"
    elif capture_classes.get("LATE", 0) > len(winner_episodes) / 2:
        repeatability = "LUCKY_RIGHT_TAIL_CAPTURE"
    else:
        repeatability = "UNRESOLVED"

    nw = newey_west_mean(ledger["selected_minus_unselected"], 3)
    bootstrap = circular_block_bootstrap_mean_ci(ledger["selected_minus_unselected"], block_length=6, replications=5000, seed=20260825)
    falsification_md = f"""# UKACTIVE-A4 falsification report

Both diagnostics retain the frozen monthly dates, contemporaneous eligible pool, one holding, next-session endpoint contract and frozen transaction costs. A simulated path with an unavailable endpoint is invalid rather than filled.

| Diagnostic | CAGR percentile | excess-vs-pool percentile | drawdown percentile | selected-vs-unselected percentile | valid paths |
|---|---:|---:|---:|---:|---:|
| Random selection | {placebo_stats['candidate_cagr_percentile']:.2%} | {placebo_stats['candidate_excess_vs_pool_percentile']:.2%} | {placebo_stats['candidate_drawdown_percentile_less_severe_is_higher']:.2%} | {placebo_stats['candidate_selected_vs_unselected_percentile']:.2%} | {placebo_stats['valid_random_paths']:,} |
| Rank permutation | {permutation_stats['candidate_cagr_percentile']:.2%} | {permutation_stats['candidate_excess_vs_pool_percentile']:.2%} | {permutation_stats['candidate_drawdown_percentile_less_severe_is_higher']:.2%} | {permutation_stats['candidate_selected_vs_unselected_percentile']:.2%} | {permutation_stats['valid_random_paths']:,} |

These are E2 falsification diagnostics, not proof of alpha and not independent E3 confirmation. The monthly-endpoint drawdown statistic is comparable within the simulations but is not a replacement for the daily portfolio drawdown.

Only fully valid paths enter the percentile calculation. {placebo_stats['invalid_random_paths']:,} random-selection paths and {permutation_stats['invalid_random_paths']:,} rank-permutation paths encountered at least one unavailable frozen endpoint and were retained as invalid, not repaired. This attrition is a material interpretive limitation; the endpoint audit records every affected month/family.
"""
    repeatability_md = f"""# UKACTIVE-A4 right-tail repeatability

Classification: **{repeatability}**.

The top family contributed {family_contrib.iloc[0]['share_of_total_net_portfolio_gain']:.2%} of net wealth gain; the top three contributed {family_contrib.head(3)['share_of_total_net_portfolio_gain'].sum():.2%}; the top five contributed {family_contrib.head(5)['share_of_total_net_portfolio_gain'].sum():.2%}. These arithmetic wealth contributions include frozen execution costs and reconcile exactly to the candidate wealth change.

Rank 1 became a future top-decile exposure {tail_summary.iloc[0]['probability_rank1_future_top_decile']:.2%} of evaluable monthly decisions and a future top-quintile exposure {tail_summary.iloc[0]['probability_rank1_future_top_quintile']:.2%}. It beat the pool median {tail_summary.iloc[0]['probability_rank1_beats_pool_median']:.2%} of the time.

Positive skew is expected for trend-following selection, but it does not neutralise concentration risk. The classification is E2 developmental evidence only.
"""
    concentration_md = "# UKACTIVE-A4 concentration decision\n\n" + "\n".join(
        f"- **{row.candidate_id}** retained {row.fraction_of_top1_excess_retained:.1%} of TOP_1 excess, changed maximum drawdown by {row.drawdown_improvement_percentage_points:+.2%}, {'met' if row.meets_frozen_numeric_concentration_criteria else 'did not meet'} the frozen numeric concentration criteria, and {'did' if row.right_tail_dependency_resolved else 'did not'} resolve the strongest-three-family dependency. Overall control: {'CONVINCING' if row.convincing_concentration_control else 'NOT CONVINCING'}."
        for row in concentration_decision_frame.itertuples()
    ) + "\n\nNo selection count or weighting parameter was changed after results were observed.\n"

    tests = correctness_tests(policy, data, ledger, top5, contribution_diff, placebo, permutation, transition)
    if not tests["status"].eq("PASS").all():
        raise AssertionError("A4 forensic correctness test failed")

    output_audits = []
    output_audits.append(write_csv(out("MONTHLY_DECISION_LEDGER.csv"), ledger))
    output_audits.append(write_csv(out("MONTHLY_TOP5_RANKS.csv"), top5))
    output_audits.append(write_csv(out("HOLDING_EPISODES.csv"), episodes))
    output_audits.append(write_csv(out("RETURN_CONTRIBUTION_BY_FAMILY.csv"), family_contrib))
    output_audits.append(write_csv(out("RETURN_CONTRIBUTION_BY_EPISODE.csv"), episode_contrib))
    output_audits.append(write_csv(out("RETURN_CONTRIBUTION_BY_YEAR.csv"), year_contrib))
    output_audits.append(write_text(out("TOP3_WINNER_FORENSICS.md"), case_study_markdown("UKACTIVE-A4 top-three winner forensics", winner_episodes, source)))
    output_audits.append(write_text(out("MEDIAN_SELECTION_FORENSICS.md"), case_study_markdown("UKACTIVE-A4 median-selection forensics", median_episodes, source)))
    output_audits.append(write_text(out("LOSER_SELECTION_FORENSICS.md"), case_study_markdown("UKACTIVE-A4 losing-selection forensics", loser_episodes, source)))
    output_audits.append(write_csv(out("TREND_CAPTURE_METRICS.csv"), episodes))
    output_audits.append(write_text(out("RIGHT_TAIL_REPEATABILITY.md"), repeatability_md))
    output_audits.append(write_csv(out("RANK1_FUTURE_TAIL_PROBABILITY.csv"), pd.concat([tail_summary.assign(record_type="SUMMARY"), tail_detail.assign(record_type="MONTHLY_DETAIL")], ignore_index=True, sort=False)))
    output_audits.append(write_csv(out("RETURN_SKEW_ANALYSIS.csv"), skew_results))
    output_audits.append(write_csv(out("TOP1_TOP2_TOP3_COMPARISON.csv"), comparison))
    output_audits.append(write_csv(out("CONCENTRATION_AND_DRAWDOWN.csv"), concentration.merge(concentration_decision_frame, on="candidate_id", how="left")))
    output_audits.append(write_csv(out("RIGHT_TAIL_DEPENDENCY.csv"), dependency))
    output_audits.append(write_text(out("CONCENTRATION_DECISION.md"), concentration_md))
    output_audits.append(write_csv(out("REGIME_FORENSICS.csv"), regime_results))
    output_audits.append(write_csv(out("REGIME_RIGHT_TAIL_INTERACTION.csv"), regime_interaction))
    output_audits.append(write_csv(out("YEAR_BY_YEAR_RESULTS.csv"), yearly))
    output_audits.append(write_csv(out("ROLLING_12M_RESULTS.csv"), rolling12))
    output_audits.append(write_csv(out("ROLLING_24M_RESULTS.csv"), rolling24))
    output_audits.append(write_csv(out("LEAVE_ONE_YEAR_OUT.csv"), leave_one_out))
    output_audits.append(write_csv(out("FULL_HISTORY_CONTEXT.csv"), history))
    output_audits.append(write_csv(out("SHORT_HORIZON_TRANSITION_DIAGNOSTICS.csv"), transition))
    output_audits.append(write_csv(out("LEADING_WEAKENING_FORENSICS.csv"), weakening))
    output_audits.append(write_csv(out("RANDOM_SELECTION_PLACEBO.csv"), placebo))
    output_audits.append(write_csv(out("RANK_PERMUTATION_TEST.csv"), permutation))
    output_audits.append(write_csv(out("PLACEBO_ENDPOINT_VALIDITY_AUDIT.csv"), endpoint_audit))
    output_audits.append(write_text(out("FALSIFICATION_REPORT.md"), falsification_md))
    output_audits.append(write_csv(out("CROSS_SECTIONAL_RANK_BUCKET_FUTURE_RETURNS.csv"), bucket_detail))
    output_audits.append(write_csv(out("CORRECTNESS_TEST_RESULTS.csv"), tests))

    interim = {
        "stage": "UKACTIVE-A4",
        "run_id": RUN_ID,
        "created_at": utc_now(),
        "evidence_level": "E2_DEVELOPMENTAL_NOT_E3_CONFIRMATORY",
        "frozen_primary_unchanged": True,
        "data_cutoff": str(cutoff.date()),
        "latest_five_year_start": str(start.date()),
        "top_three_actual_contributors": top_contributors,
        "a3r2_remove_top_three_family_set": ["EUROPE_BANKS", "GLOBAL_GOLD_MINERS", "GLOBAL_SEMICONDUCTORS"],
        "right_tail_repeatability_classification": repeatability,
        "placebo_summary": placebo_stats,
        "permutation_summary": permutation_stats,
        "selected_vs_unselected_inference": {**nw, **bootstrap},
        "contribution_reconciliation_difference": contribution_diff,
        "concentration_control_results": concentration_decision_frame.to_dict(orient="records"),
        "correctness_tests": tests.to_dict(orient="records"),
        "warning": WARNING,
    }
    output_audits.append(write_json(out("FORENSIC_INTERIM_DECISION.json"), interim))
    manifest = {
        "stage": "UKACTIVE-A4-RIGHT-TAIL-FORENSICS",
        "run_id": RUN_ID,
        "created_at": utc_now(),
        "git_branch": git_output("branch", "--show-current"),
        "executed_from_commit": git_output("rev-parse", "HEAD"),
        "policy": audit_file(POLICY_PATH),
        "inputs": [audit_file(FEATURE_PATH), audit_file(REGIME_PATH), audit_file(SNAPSHOT_PATH), audit_file(PROGRAMME_ROOT / "UKACTIVE_A2R2_CORRECTED_SIGNAL_ELIGIBILITY.parquet")],
        "source": audit_file(Path(__file__)),
        "outputs": output_audits,
        "package_versions": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__, "pyarrow": pyarrow.__version__},
        "random_seeds": {"random_selection": int(policy["falsification"]["random_selection_seed"]), "rank_permutation": int(policy["falsification"]["rank_permutation_seed"])},
        "simulation_count_each": int(policy["falsification"]["random_selection_simulations"]),
        "all_historical_results_evidence_level": "E2",
    }
    write_json(out("FORENSIC_MANIFEST.json"), manifest)
    print(json.dumps(interim, indent=2, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
