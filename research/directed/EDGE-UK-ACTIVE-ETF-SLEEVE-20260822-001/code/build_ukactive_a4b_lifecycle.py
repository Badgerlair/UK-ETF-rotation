"""Run the preregistered A4B0-A4B2 lifecycle modules.

This file deliberately stops before choosing a combined lifecycle/regime
architecture.  It reproduces the frozen A4 baseline, evaluates the two
starter ladders and four exit/profit modules independently, and writes the
module-level audit ledgers used by the sequential A4B gates.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import ukactive_a4b_core as core


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
LATEST5_START = pd.Timestamp("2021-09-01")
LATEST5_REVIEW_START = pd.Timestamp("2021-08-31")
CUTOFF = pd.Timestamp("2026-08-21")


def _feature_frame(data: core.A4BData, date: pd.Timestamp, frequency: str) -> pd.DataFrame:
    monthly_dates = set(pd.DatetimeIndex(data.monthly_features["date"].unique()))
    weekly_dates = set(pd.DatetimeIndex(data.weekly_features["date"].unique()))
    use_monthly = frequency == "MONTHLY_ONLY" or (date in monthly_dates and date not in weekly_dates)
    source = data.monthly_features if use_monthly else data.weekly_features
    exact = source.loc[source["date"].eq(date)].copy()
    if not exact.empty:
        return exact
    prior = source.loc[source["date"].le(date), "date"]
    if prior.empty:
        return source.iloc[0:0].copy()
    return source.loc[source["date"].eq(prior.max())].copy()


def _regime_row(data: core.A4BData, date: pd.Timestamp) -> pd.Series:
    source = data.weekly_regime.loc[data.weekly_regime["date"].le(date)]
    if source.empty:
        return pd.Series(dtype=object)
    return source.iloc[-1]


def _family_row(frame: pd.DataFrame, family: str) -> pd.Series:
    match = frame.loc[frame["economic_exposure_family_id"].eq(family)]
    return match.iloc[0] if len(match) else pd.Series(dtype=object)


def _state(row: pd.Series) -> str:
    return str(row.get("LEADERSHIP_STATE", "OTHER")) if len(row) else "OTHER"


def _target_dates(data: core.A4BData, frequency: str, review_start: pd.Timestamp) -> list[pd.Timestamp]:
    if frequency == "MONTHLY_ONLY":
        dates = pd.DatetimeIndex(data.monthly_features["date"].unique())
    else:
        dates = pd.DatetimeIndex(data.weekly_features["date"].unique())
        # Weekly management supplements rather than delays the frozen monthly
        # selection decision.  A month-end that is not the week's final XLON
        # session must therefore remain an explicit review date.
        dates = dates.union(pd.DatetimeIndex(data.monthly_features["date"].unique()))
        dates = dates.union(pd.DatetimeIndex([review_start]))
    return [pd.Timestamp(value) for value in dates[(dates >= review_start) & (dates <= CUTOFF)].sort_values()]


def _leader_at(leaders: pd.DataFrame, date: pd.Timestamp) -> str:
    rows = leaders.loc[leaders["monthly_review_date"].le(date)]
    return str(rows.iloc[-1]["incumbent_family"]) if len(rows) else ""


def _challenger_weight(row: pd.Series) -> float:
    if not len(row):
        return 0.0
    slow_rank = row.get("SLOW_ORDINAL_RANK", np.nan)
    state = _state(row)
    if pd.notna(slow_rank) and float(slow_rank) <= 1:
        return 1.0
    if pd.notna(slow_rank) and float(slow_rank) <= 3:
        return 0.75
    if state == "CONFIRMING":
        return 0.50
    if state == "EMERGING":
        return 0.25
    return 0.0


def _select_new_challenger(frame: pd.DataFrame, incumbent: str) -> str:
    candidates = frame.loc[
        frame["LEADERSHIP_STATE"].eq("EMERGING")
        & frame["economic_exposure_family_id"].ne(incumbent)
    ].sort_values(["FAST_RS", "economic_exposure_family_id"], ascending=[False, True])
    return str(candidates.iloc[0]["economic_exposure_family_id"]) if len(candidates) else ""


def build_plan(
    data: core.A4BData,
    module_id: str,
    *,
    frequency: str,
    scale_module: str = "NONE",
    exit_module: str = "NONE",
    regime_module: str = "CONTROL",
    review_start: pd.Timestamp = LATEST5_REVIEW_START,
) -> core.PlannedPortfolio:
    """Build a single registered module without consulting its returns."""

    leaders = core.monthly_leaders(data.monthly_features)
    dates = _target_dates(data, frequency, review_start)
    planner = core.TargetPlanner(data, module_id, frequency)
    decisions: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    challenger = ""
    last_incumbent = ""
    persistent_caps: dict[str, float] = {}
    exit_lockout: set[str] = set()
    episode_trimmed: set[str] = set()
    prior_challenger_weight = 0.0

    for date in dates:
        frame = _feature_frame(data, date, frequency)
        incumbent = _leader_at(leaders, date)
        if not incumbent:
            continue
        incumbent_changed = bool(last_incumbent and incumbent != last_incumbent)
        if incumbent_changed:
            challenger = ""
            persistent_caps.clear()
            exit_lockout.clear()
            episode_trimmed.clear()
            prior_challenger_weight = 0.0
        last_incumbent = incumbent
        incumbent_row = _family_row(frame, incumbent)
        incumbent_state = _state(incumbent_row)

        leadership_target: dict[str, float]
        challenger_event = "NONE"
        if scale_module == "NONE":
            leadership_target = {incumbent: 1.0}
        else:
            challenger_failed_now = False
            if challenger:
                current_challenger_row = _family_row(frame, challenger)
                challenger_weight = _challenger_weight(current_challenger_row)
                if challenger_weight <= 0 or _state(current_challenger_row) == "FAILED":
                    actions.append({
                        "module_id": module_id, "review_date": date, "action_type": "STARTER_FAILED",
                        "family": challenger, "from_weight": prior_challenger_weight, "to_weight": 0.0,
                        "leadership_state": _state(current_challenger_row), "reason": "CHALLENGER_FAILED_BEFORE_OR_AFTER_CONFIRMATION",
                    })
                    challenger = ""
                    prior_challenger_weight = 0.0
                    challenger_failed_now = True
            if not challenger:
                proposed = _select_new_challenger(frame, incumbent)
                permitted = bool(proposed)
                if scale_module == "STARTER_B":
                    permitted &= incumbent_state == "WEAKENING"
                if permitted:
                    challenger = proposed
                    challenger_event = "STARTER_OPEN"
            if challenger:
                challenger_row = _family_row(frame, challenger)
                challenger_weight = _challenger_weight(challenger_row)
                if challenger_weight <= 0:
                    challenger = ""
                    challenger_weight = 0.0
                incumbent_valid = incumbent_state != "FAILED"
                incumbent_weight = max(0.0, 1.0 - challenger_weight) if incumbent_valid else 0.0
                leadership_target = {}
                if incumbent_weight > 0:
                    leadership_target[incumbent] = incumbent_weight
                if challenger_weight > 0:
                    leadership_target[challenger] = challenger_weight
                if challenger:
                    event_type = challenger_event or ("STARTER_ADVANCE" if challenger_weight > prior_challenger_weight + 1e-12 else "STARTER_MAINTAIN")
                    if event_type != "STARTER_MAINTAIN":
                        actions.append({
                            "module_id": module_id, "review_date": date, "action_type": event_type,
                            "family": challenger, "from_weight": prior_challenger_weight,
                            "to_weight": challenger_weight, "leadership_state": _state(challenger_row),
                            "reason": f"{scale_module}_FROZEN_LADDER",
                        })
                    prior_challenger_weight = challenger_weight
            else:
                # The cash fallback belongs only to an actual failed starter
                # handover.  A starter architecture must not smuggle in an
                # independent incumbent-failure exit rule.
                leadership_target = {} if challenger_failed_now and incumbent_state == "FAILED" else {incumbent: 1.0}

        target = dict(leadership_target)
        # Apply one independent exit/profit module after the leadership target.
        for family, raw_weight in list(target.items()):
            row = _family_row(frame, family)
            state = _state(row)
            stats = planner.position_stats(family, date)
            cap = float(raw_weight)
            trigger = ""
            if exit_module == "FAST_TAPER":
                if state == "FAILED":
                    cap, trigger = 0.0, "FAILED_EXIT"
                elif state == "WEAKENING":
                    cap = min(cap, 0.50 if bool(row.get("STRONGER_WEAKENING_FLAG", False)) else 0.75)
                    trigger = "STRONGER_WEAKENING_50" if cap <= 0.50 else "FIRST_WEAKENING_75"
            elif exit_module == "MFE_GIVEBACK_LOCK":
                if family in exit_lockout:
                    cap, trigger = 0.0, "PERSISTENT_EXIT_LOCKOUT"
                else:
                    mfe = stats["mfe"]
                    giveback = stats["giveback_ratio"]
                    deterioration = state in {"WEAKENING", "FAILED"}
                    if state == "FAILED" or (pd.notna(mfe) and mfe >= 0.10 and pd.notna(giveback) and giveback >= 0.50 and deterioration):
                        cap, trigger = 0.0, "MFE_50_GIVEBACK_OR_FAILED_EXIT"
                        exit_lockout.add(family)
                    elif pd.notna(mfe) and mfe >= 0.10 and pd.notna(giveback) and giveback >= 0.25 and deterioration:
                        cap, trigger = min(cap, 0.50), "MFE_25_GIVEBACK_WEAKENING_CAP50"
                        persistent_caps[family] = min(persistent_caps.get(family, 1.0), 0.50)
                    cap = min(cap, persistent_caps.get(family, 1.0))
            elif exit_module in {"STRENGTH_HARVEST", "STRENGTH_PLUS_DECELERATION"}:
                qualifies = (
                    pd.notna(stats["position_return"]) and stats["position_return"] >= 0.20
                    and bool(row.get("EXTENSION_FLAG", False))
                    and pd.notna(row.get("SLOW_ORDINAL_RANK", np.nan))
                    and float(row.get("SLOW_ORDINAL_RANK")) <= 1
                )
                if exit_module == "STRENGTH_PLUS_DECELERATION":
                    regime_state = str(_regime_row(data, date).get("REGIME_STATE", "POSITIVE"))
                    qualifies &= (
                        (pd.notna(row.get("FAST_RS_CHANGE_4W", np.nan)) and float(row.get("FAST_RS_CHANGE_4W")) < 0)
                        or regime_state in {"MATURE", "DETERIORATING", "HOSTILE"}
                    )
                if qualifies and family not in episode_trimmed:
                    persistent_caps[family] = max(0.0, cap - 0.25)
                    episode_trimmed.add(family)
                    trigger = "EXCEPTIONAL_STRENGTH_TRIM25" if exit_module == "STRENGTH_HARVEST" else "STRENGTH_AND_DECELERATION_TRIM25"
                cap = min(cap, persistent_caps.get(family, 1.0))

            if trigger and cap < raw_weight - 1e-12:
                actions.append({
                    "module_id": module_id, "review_date": date, "action_type": trigger,
                    "family": family, "from_weight": raw_weight, "to_weight": cap,
                    "leadership_state": state, "position_return": stats["position_return"],
                    "mfe": stats["mfe"], "mae": stats["mae"], "giveback_ratio": stats["giveback_ratio"],
                    "reason": exit_module,
                })
            if cap <= 1e-12:
                target.pop(family, None)
            else:
                target[family] = cap

        regime = _regime_row(data, date)
        regime_state = str(regime.get("REGIME_STATE", "POSITIVE"))
        multiplier = float(data.policy["regime"]["multipliers"][regime_module].get(regime_state, 1.0))
        target = {family: weight * multiplier for family, weight in target.items() if weight * multiplier > 1e-12}
        target_risky = float(sum(target.values()))
        execution = planner.submit(date, target, f"{scale_module}|{exit_module}|REGIME_{regime_module}")
        decisions.append({
            "module_id": module_id,
            "management_frequency": frequency,
            "review_date": date,
            "monthly_incumbent": incumbent,
            "incumbent_state": incumbent_state,
            "challenger": challenger,
            "leadership_target_json": json.dumps(leadership_target, sort_keys=True),
            "target_weights_json": json.dumps(target, sort_keys=True),
            "target_leadership_allocation": float(sum(leadership_target.values())),
            "regime_score": regime.get("REGIME_SCORE", np.nan),
            "regime_state": regime_state,
            "regime_multiplier": multiplier,
            "target_risky_allocation": target_risky,
            "target_cash_allocation": 1.0 - target_risky,
            "execution_status": execution["execution_status"],
            "execution_date": execution.get("execution_date", pd.NaT),
            "warning": core.WARNING,
        })

    return core.PlannedPortfolio(
        module_id=module_id,
        management_frequency=frequency,
        targets=planner.targets,
        events=planner.events,
        cancelled_events=planner.cancelled,
        decisions=pd.DataFrame(decisions),
        actions=pd.DataFrame(actions),
    )


def _a4_comparators() -> dict[str, float]:
    source = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4_TOP1_TOP2_TOP3_COMPARISON.csv")
    row = source.loc[source["candidate_id"].eq("A4_TOP1")].iloc[0]
    return {
        "equal_pool_cagr": float(row["equal_pool_cagr"]),
        "unselected_pool_cagr": float(row["unselected_pool_cagr"]),
        "global_benchmark_cagr": float(row["global_benchmark_cagr"]),
    }


def _metric_row(sim: core.A4BSimulation, module_id: str, frequency: str, module_family: str) -> dict[str, Any]:
    metrics = core.enhanced_performance_metrics(sim, start=LATEST5_START, end=CUTOFF)
    comparators = _a4_comparators()
    row = {"module_id": module_id, "module_family": module_family, "management_frequency": frequency, **metrics}
    row["net_excess_vs_equal_pool_cagr"] = row["net_cagr"] - comparators["equal_pool_cagr"]
    row["net_excess_vs_global_cagr"] = row["net_cagr"] - comparators["global_benchmark_cagr"]
    row["selected_vs_frozen_unselected_cagr_spread"] = row["net_cagr"] - comparators["unselected_pool_cagr"]
    row["hard_drawdown_gate_pass"] = row["maximum_drawdown"] >= -0.25
    row["preferred_drawdown_range_reached"] = row["maximum_drawdown"] >= -0.15
    row["evidence_level"] = "E2_DEVELOPMENTAL"
    row["warning"] = core.WARNING
    return row


def _episodes(sim: core.A4BSimulation, data: core.A4BData) -> pd.DataFrame:
    trades = sim.trades.loc[sim.trades["execution_status"].eq("EXECUTED")].copy().sort_values("execution_date")
    if trades.empty:
        return pd.DataFrame()
    current: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    final_date = min(CUTOFF, pd.Timestamp(sim.curve["date"].max()))
    for trade in trades.itertuples():
        date = pd.Timestamp(trade.execution_date)
        target = json.loads(trade.target_weights_json)
        prior = set(current)
        new = set(target)
        for family in prior - new:
            episode = current.pop(family)
            episode["exit_date"] = date
            rows.append(episode)
        for family in new - prior:
            current[family] = {
                "module_id": sim.module_id,
                "family": family,
                "entry_date": date,
                "initial_weight": float(target[family]),
                "entry_level": float(data.research.wealth.loc[date, family]),
            }
    for family, episode in current.items():
        episode["exit_date"] = final_date
        rows.append(episode)
    output: list[dict[str, Any]] = []
    for index, episode in enumerate(rows, 1):
        family = episode["family"]
        start = pd.Timestamp(episode["entry_date"])
        end = pd.Timestamp(episode["exit_date"])
        levels = data.research.wealth.loc[start:end, family].dropna().astype(float)
        if levels.empty:
            continue
        returns = levels / float(episode["entry_level"]) - 1.0
        mfe = float(max(0.0, returns.max()))
        mae = float(min(0.0, returns.min()))
        realised = float(returns.iloc[-1])
        output.append({
            "episode_id": f"{sim.module_id}-EP-{index:03d}", **episode,
            "xlon_observations": int(len(levels)), "position_return_at_exit_or_cutoff": realised,
            "mfe": mfe, "mae": mae,
            "capture_ratio": realised / mfe if mfe > 0 else np.nan,
            "giveback_ratio": (mfe - realised) / mfe if mfe > 0 else np.nan,
            "profitable_episode_ended_negative": bool(mfe > 0 and realised < 0),
            "mfe_ge_10_retained_lt_25pct": bool(mfe >= 0.10 and realised < 0.25 * mfe),
            "surrendered_more_than_50pct_mfe": bool(mfe > 0 and realised < 0.50 * mfe),
            "warning": core.WARNING,
        })
    return pd.DataFrame(output)


def _starter_diagnostics(plans: dict[str, core.PlannedPortfolio], data: core.A4BData) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    episodes: list[dict[str, Any]] = []
    for module_id, plan in plans.items():
        if "STARTER" not in module_id or plan.decisions.empty:
            continue
        decisions = plan.decisions.sort_values("review_date").reset_index(drop=True)
        actions = plan.actions.sort_values("review_date") if not plan.actions.empty else pd.DataFrame()
        active: dict[str, Any] | None = None
        raw_episodes: list[dict[str, Any]] = []
        for position, decision in decisions.iterrows():
            family = str(decision.get("challenger", "") or "")
            if active is not None and family != active["family"]:
                active["end_position"] = position - 1
                active["next_position"] = position
                raw_episodes.append(active)
                active = None
            if family and active is None:
                active = {"family": family, "start_position": position}
        if active is not None:
            active["end_position"] = len(decisions) - 1
            active["next_position"] = None
            raw_episodes.append(active)

        for number, raw in enumerate(raw_episodes, 1):
            family = raw["family"]
            block = decisions.iloc[raw["start_position"]:raw["end_position"] + 1]
            start = pd.Timestamp(block.iloc[0]["review_date"])
            weights = block["target_weights_json"].map(lambda value: float(json.loads(value).get(family, 0.0)))
            confirming_flag = bool(weights.ge(0.50).any())
            next_row = decisions.iloc[raw["next_position"]] if raw["next_position"] is not None else pd.Series(dtype=object)
            became_slow_leader = bool(len(next_row) and str(next_row.get("monthly_incumbent", "")) == family)
            slow_date = pd.Timestamp(next_row["review_date"]) if became_slow_leader else pd.NaT
            failed_rows = actions.loc[
                actions["action_type"].eq("STARTER_FAILED")
                & actions["family"].eq(family)
                & actions["review_date"].between(start, pd.Timestamp(next_row.get("review_date", CUTOFF)) if len(next_row) else CUTOFF)
            ] if len(actions) else pd.DataFrame()
            execution = next((event for event in plan.events if pd.Timestamp(event["review_date"]) == start), None)
            entry_date = pd.Timestamp(execution["execution_date"]) if execution else pd.NaT
            early_return = np.nan
            incumbent_return = np.nan
            comparison_boundary = slow_date if pd.notna(slow_date) else pd.Timestamp(block.iloc[-1]["review_date"])
            if pd.notna(entry_date) and comparison_boundary > entry_date:
                end_candidates = data.research.calendar[data.research.calendar >= comparison_boundary]
                if len(end_candidates):
                    end = pd.Timestamp(end_candidates[0])
                    early_return = float(data.research.wealth.loc[end, family] / data.research.wealth.loc[entry_date, family] - 1)
                    incumbent = str(block.iloc[0]["monthly_incumbent"])
                    if incumbent and pd.notna(data.research.wealth.loc[entry_date, incumbent]) and pd.notna(data.research.wealth.loc[end, incumbent]):
                        incumbent_return = float(data.research.wealth.loc[end, incumbent] / data.research.wealth.loc[entry_date, incumbent] - 1)
            episodes.append({
                "module_id": module_id, "starter_episode_id": f"{module_id}-ST-{number:03d}", "family": family,
                "emerging_signal_date": start, "starter_execution_date": entry_date,
                "confirming_date": pd.Timestamp(block.loc[weights.ge(0.50)].iloc[0]["review_date"]) if confirming_flag else pd.NaT,
                "slow_rank1_or_monthly_leader_date": slow_date,
                "failure_date": pd.Timestamp(failed_rows.iloc[0]["review_date"]) if len(failed_rows) else pd.NaT,
                "became_confirming": confirming_flag, "became_slow_leader": became_slow_leader,
                "failed": bool(len(failed_rows)), "maximum_allocation": float(weights.max()),
                "early_entry_return_until_slow_entry": early_return,
                "incumbent_return_same_interval": incumbent_return,
                "early_entry_value_vs_incumbent": early_return - incumbent_return if pd.notna(early_return) and pd.notna(incumbent_return) else np.nan,
                "time_saved_calendar_days": int((slow_date - entry_date).days) if pd.notna(slow_date) and pd.notna(entry_date) else np.nan,
                "warning": core.WARNING,
            })
    frame = pd.DataFrame(episodes)
    rates: list[dict[str, Any]] = []
    if len(frame):
        for module_id, group in frame.groupby("module_id"):
            rates.append({
                "module_id": module_id, "starter_episode_count": len(group),
                "emerging_to_confirming_conversion_rate": float(group["became_confirming"].mean()),
                "emerging_to_slow_leader_conversion_rate": float(group["became_slow_leader"].mean()),
                "false_start_rate": float(group["failed"].mean()),
                "mean_time_saved_calendar_days": float(group["time_saved_calendar_days"].mean()),
                "warning": core.WARNING,
            })
    rates_frame = pd.DataFrame(rates)
    early = frame.groupby("module_id", as_index=False).agg(
        starter_episode_count=("starter_episode_id", "count"),
        aggregate_early_entry_value_vs_incumbent=("early_entry_value_vs_incumbent", "sum"),
        mean_early_entry_value_vs_incumbent=("early_entry_value_vs_incumbent", "mean"),
        mean_early_entry_return=("early_entry_return_until_slow_entry", "mean"),
    ) if len(frame) else pd.DataFrame()
    handovers = frame.loc[frame.get("became_slow_leader", pd.Series(dtype=bool)).fillna(False)].copy() if len(frame) else pd.DataFrame()
    return frame, rates_frame, early, handovers


def _counterfactual_actions(simulations: dict[str, core.A4BSimulation], data: core.A4BData) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for module_id, sim in simulations.items():
        if sim.actions.empty:
            continue
        trades = sim.trades.loc[sim.trades["execution_status"].eq("EXECUTED")].sort_values("execution_date")
        for number, action in enumerate(sim.actions.itertuples(), 1):
            if not hasattr(action, "from_weight") or float(action.from_weight) <= float(action.to_weight):
                continue
            trade = trades.loc[trades["review_date"].eq(pd.Timestamp(action.review_date))].head(1)
            if trade.empty:
                continue
            execution_date = pd.Timestamp(trade.iloc[0]["execution_date"])
            later = trades.loc[trades["execution_date"].gt(execution_date)]
            end_date = pd.Timestamp(later.iloc[0]["execution_date"]) if len(later) else CUTOFF
            family = str(action.family)
            if execution_date not in data.research.wealth.index or end_date not in data.research.wealth.index:
                continue
            family_factor = float(data.research.wealth.loc[end_date, family] / data.research.wealth.loc[execution_date, family])
            cash_factor = float(data.cash_index.loc[end_date] / data.cash_index.loc[execution_date])
            reduction = float(action.from_weight) - float(action.to_weight)
            delta = reduction * (cash_factor - family_factor)
            avoided = max(0.0, delta)
            foregone = max(0.0, -delta)
            incremental_cost = reduction * 20.0 / 10_000.0 + 3.99 / 250000.0
            rows.append({
                "module_id": module_id, "counterfactual_event_id": f"{module_id}-CF-{number:03d}",
                "review_date": pd.Timestamp(action.review_date), "execution_date": execution_date,
                "counterfactual_end_date": end_date, "family": family,
                "action_type": action.action_type, "allocation_reduced": reduction,
                "family_counterfactual_return": family_factor - 1.0, "actual_cash_return": cash_factor - 1.0,
                "avoided_downside_return_equivalent": avoided, "foregone_upside_return_equivalent": foregone,
                "incremental_cost_return_equivalent": incremental_cost,
                "net_monetisation_value": delta - incremental_cost,
                "warning": core.WARNING,
            })
    return pd.DataFrame(rows)


def _baseline_reproduction(sim: core.A4BSimulation) -> pd.DataFrame:
    actual = core.enhanced_performance_metrics(sim, start=LATEST5_START, end=CUTOFF)
    source = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4_TOP1_TOP2_TOP3_COMPARISON.csv")
    row = source.loc[source["candidate_id"].eq("A4_TOP1")].iloc[0]
    tests = [
        ("net_cagr", float(row["selected_net_cagr"]), actual["net_cagr"], 1e-12),
        ("maximum_drawdown", float(row["selected_net_maximum_drawdown"]), actual["maximum_drawdown"], 1e-12),
        ("annual_turnover_traded_notional", float(row["selected_net_annual_turnover_traded_notional"]), actual["annual_turnover_traded_notional"], 1e-12),
        ("trade_legs", int(row["selected_net_trade_legs"]), actual["trade_legs"], 0),
    ]
    return pd.DataFrame([{
        "test_id": name, "a4_expected": expected, "a4b_actual": observed,
        "absolute_difference": abs(float(observed) - float(expected)), "tolerance": tolerance,
        "result": "PASS" if abs(float(observed) - float(expected)) <= tolerance else "FAIL",
        "warning": core.WARNING,
    } for name, expected, observed, tolerance in tests])


def _write(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(PROGRAMME_ROOT / name, index=False, date_format="%Y-%m-%d")


def main() -> None:
    data = core.load_a4b_data()
    specs = [
        ("A4_BASELINE_MONTHLY", "MONTHLY_ONLY", "NONE", "NONE", "BASELINE"),
        ("A4_BASELINE_WEEKLY_CONTROL", "WEEKLY", "NONE", "NONE", "BASELINE"),
        ("SCALE_IN_STARTER_A_WEEKLY", "WEEKLY", "STARTER_A", "NONE", "SCALE_IN"),
        ("SCALE_IN_STARTER_B_WEEKLY", "WEEKLY", "STARTER_B", "NONE", "SCALE_IN"),
        ("SCALE_IN_STARTER_A_MONTHLY", "MONTHLY_ONLY", "STARTER_A", "NONE", "SCALE_IN"),
        ("SCALE_IN_STARTER_B_MONTHLY", "MONTHLY_ONLY", "STARTER_B", "NONE", "SCALE_IN"),
        ("EXIT_FAST_TAPER_WEEKLY", "WEEKLY", "NONE", "FAST_TAPER", "EXIT"),
        ("EXIT_FAST_TAPER_MONTHLY", "MONTHLY_ONLY", "NONE", "FAST_TAPER", "EXIT"),
        ("EXIT_MFE_GIVEBACK_LOCK_WEEKLY", "WEEKLY", "NONE", "MFE_GIVEBACK_LOCK", "EXIT"),
        ("EXIT_MFE_GIVEBACK_LOCK_MONTHLY", "MONTHLY_ONLY", "NONE", "MFE_GIVEBACK_LOCK", "EXIT"),
        ("EXIT_STRENGTH_HARVEST_WEEKLY", "WEEKLY", "NONE", "STRENGTH_HARVEST", "PROFIT_LOCK"),
        ("EXIT_STRENGTH_HARVEST_MONTHLY", "MONTHLY_ONLY", "NONE", "STRENGTH_HARVEST", "PROFIT_LOCK"),
        ("EXIT_STRENGTH_PLUS_DECELERATION_WEEKLY", "WEEKLY", "NONE", "STRENGTH_PLUS_DECELERATION", "PROFIT_LOCK"),
        ("EXIT_STRENGTH_PLUS_DECELERATION_MONTHLY", "MONTHLY_ONLY", "NONE", "STRENGTH_PLUS_DECELERATION", "PROFIT_LOCK"),
    ]
    plans: dict[str, core.PlannedPortfolio] = {}
    simulations: dict[str, core.A4BSimulation] = {}
    results: list[dict[str, Any]] = []
    episode_parts: list[pd.DataFrame] = []
    for module_id, frequency, scale, exit_module, family in specs:
        plan = build_plan(data, module_id, frequency=frequency, scale_module=scale, exit_module=exit_module)
        sim = core.simulate_planned_portfolio(plan, data)
        plans[module_id] = plan
        simulations[module_id] = sim
        results.append(_metric_row(sim, module_id, frequency, family))
        episodes = _episodes(sim, data)
        if len(episodes):
            episode_parts.append(episodes)

    metrics = pd.DataFrame(results)
    baseline = simulations["A4_BASELINE_MONTHLY"]
    reproduction = _baseline_reproduction(baseline)
    if not reproduction["result"].eq("PASS").all():
        raise AssertionError("Frozen A4 baseline did not reproduce exactly")

    starter_episodes, conversion, early_value, handovers = _starter_diagnostics(plans, data)
    action_parts = [sim.actions for sim in simulations.values() if not sim.actions.empty]
    actions = pd.concat(action_parts, ignore_index=True) if action_parts else pd.DataFrame()
    counterfactual = _counterfactual_actions(simulations, data)
    episodes = pd.concat(episode_parts, ignore_index=True) if episode_parts else pd.DataFrame()
    capture = episodes.copy()
    if len(capture):
        capture["retained_mfe_fraction"] = capture["capture_ratio"]
    giveback = capture[[column for column in ["module_id", "episode_id", "family", "entry_date", "exit_date", "mfe", "position_return_at_exit_or_cutoff", "giveback_ratio", "surrendered_more_than_50pct_mfe", "warning"] if column in capture.columns]].copy()
    roundtrips = capture.loc[capture.get("profitable_episode_ended_negative", pd.Series(dtype=bool)).fillna(False)].copy() if len(capture) else pd.DataFrame()

    # Aggregate action-counterfactual economics without using it to choose rules here.
    monetisation = counterfactual.groupby("module_id", as_index=False).agg(
        partial_reduction_events=("counterfactual_event_id", "count"),
        aggregate_avoided_downside=("avoided_downside_return_equivalent", "sum"),
        aggregate_foregone_upside=("foregone_upside_return_equivalent", "sum"),
        aggregate_incremental_cost=("incremental_cost_return_equivalent", "sum"),
        aggregate_net_monetisation_value=("net_monetisation_value", "sum"),
    ) if len(counterfactual) else pd.DataFrame(columns=["module_id"])
    monetisation["warning"] = core.WARNING

    baseline_contributors = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4_RETURN_CONTRIBUTION_BY_FAMILY.csv")
    top_families = baseline_contributors.head(5)["family"].tolist()
    right_tail_rows: list[dict[str, Any]] = []
    for module_id, sim in simulations.items():
        curve = sim.curve.loc[sim.curve["date"].between(LATEST5_START, CUTOFF)]
        family_pnl = {family: 0.0 for family in top_families}
        for value in curve["family_market_pnl_json"]:
            parsed = json.loads(value)
            for family in family_pnl:
                family_pnl[family] += float(parsed.get(family, 0.0))
        for family, contribution in family_pnl.items():
            base = float(baseline_contributors.loc[baseline_contributors["family"].eq(family), "net_portfolio_pnl_contribution"].iloc[0])
            right_tail_rows.append({
                "module_id": module_id, "family": family,
                "module_market_pnl_contribution": contribution,
                "baseline_net_pnl_contribution": base,
                "contribution_retention_ratio": contribution / base if base != 0 else np.nan,
                "warning": core.WARNING,
            })
    right_tail = pd.DataFrame(right_tail_rows)

    _write(reproduction, "UKACTIVE_A4B_BASELINE_REPRODUCTION.csv")
    _write(metrics.loc[metrics["module_family"].eq("SCALE_IN")], "UKACTIVE_A4B_SCALE_IN_RESULTS.csv")
    _write(starter_episodes, "UKACTIVE_A4B_STARTER_EPISODES.csv")
    _write(conversion, "UKACTIVE_A4B_EMERGING_CONVERSION_RATES.csv")
    _write(early_value, "UKACTIVE_A4B_EARLY_ENTRY_VALUE.csv")
    _write(handovers, "UKACTIVE_A4B_INCUMBENT_CHALLENGER_HANDOVERS.csv")
    _write(metrics.loc[metrics["module_family"].isin(["EXIT", "PROFIT_LOCK"])], "UKACTIVE_A4B_EXIT_MODULE_RESULTS.csv")
    _write(actions, "UKACTIVE_A4B_PARTIAL_SALE_LEDGER.csv")
    _write(capture, "UKACTIVE_A4B_MFE_MAE_CAPTURE.csv")
    _write(giveback, "UKACTIVE_A4B_PROFIT_GIVEBACK.csv")
    _write(roundtrips, "UKACTIVE_A4B_PROFIT_ROUND_TRIPS.csv")
    _write(counterfactual, "UKACTIVE_A4B_COUNTERFACTUAL_REDUCTION_LEDGER.csv")
    _write(monetisation, "UKACTIVE_A4B_NET_MONETISATION_VALUE.csv")
    _write(right_tail, "UKACTIVE_A4B_RIGHT_TAIL_RETENTION.csv")
    _write(metrics, "UKACTIVE_A4B_LIFECYCLE_MODULE_METRICS.csv")

    report = [
        "# UKACTIVE-A4B sell-into-strength report",
        "",
        core.RESEARCH_WARNING,
        "",
        "The strength-harvest modules were tested exactly once under the preregistered +20% / prior expanding 90th-percentile extension conditions. The deceleration variant additionally required negative four-week FAST_RS change or a MATURE/DETERIORATING/HOSTILE regime. No gain threshold was searched.",
        "",
        "The counterfactual ledger records avoided downside, foregone upside, incremental cost and net monetisation value for every reduction. Positive realised gains are not treated as value-add unless the counterfactual is positive after cost.",
    ]
    (PROGRAMME_ROOT / "UKACTIVE_A4B_SELL_INTO_STRENGTH_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
