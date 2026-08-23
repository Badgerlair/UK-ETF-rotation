"""Core primitives for UKACTIVE-A4C.

The module reuses the corrected A2R2 endpoint chain and the exact A4/A4B
simulator.  It adds only preregistered trajectory, trend, risk-budget and
core-satellite mechanics.  No price or return is filled and all target changes
execute after the management close.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

import build_ukactive_a4b_lifecycle as a4b_lifecycle
import ukactive_a3r2_portfolio as a3p
import ukactive_a4b_core as a4b


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = PROGRAMME_ROOT / "config" / "UKACTIVE_A4C_POLICY_v1.json"
WARNING = "HISTORICAL UK RETAIL, ISA, ACCOUNT AND BROKER ELIGIBILITY REMAIN PARTLY UNRESOLVED"
RESEARCH_WARNING = "A4C IS E2 DEVELOPMENTAL RESEARCH; MECHANISM DIAGNOSTICS ARE E1; NO E3 CONFIRMATION"
LATEST5_START = pd.Timestamp("2021-09-01")
LATEST5_REVIEW_START = pd.Timestamp("2021-08-31")
CUTOFF = pd.Timestamp("2026-08-21")


@dataclass
class A4CData:
    policy: dict[str, Any]
    base: a4b.A4BData
    weekly_features: pd.DataFrame
    monthly_features: pd.DataFrame
    daily_technical: pd.DataFrame


def read_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _long_matrix(matrix: pd.DataFrame, dates: pd.DatetimeIndex, members: list[str], name: str) -> pd.DataFrame:
    source = matrix.reindex(index=dates, columns=members)
    result = source.stack(future_stack=True).rename(name).reset_index()
    result.columns = ["date", "economic_exposure_family_id", name]
    return result


def _segment_ewm(values: pd.Series, segments: pd.Series, span: int) -> pd.Series:
    result = pd.Series(np.nan, index=values.index, dtype=float)
    valid = values.notna() & segments.notna()
    source = pd.DataFrame({"value": values.loc[valid], "segment": segments.loc[valid]})
    for _, group in source.groupby("segment", sort=False):
        result.loc[group.index] = group["value"].ewm(span=span, adjust=False, min_periods=span).mean()
    return result


def _segment_rolling_std(values: pd.Series, segments: pd.Series, window: int, minimum: int) -> pd.Series:
    result = pd.Series(np.nan, index=values.index, dtype=float)
    valid = values.notna() & segments.notna()
    source = pd.DataFrame({"value": values.loc[valid], "segment": segments.loc[valid]})
    for _, group in source.groupby("segment", sort=False):
        result.loc[group.index] = group["value"].rolling(window, min_periods=minimum).std(ddof=1)
    return result


def _segment_prior_median(values: pd.Series, segments: pd.Series, window: int, minimum: int) -> pd.Series:
    result = pd.Series(np.nan, index=values.index, dtype=float)
    valid = values.notna() & segments.notna()
    source = pd.DataFrame({"value": values.loc[valid], "segment": segments.loc[valid]})
    for _, group in source.groupby("segment", sort=False):
        result.loc[group.index] = group["value"].shift(1).rolling(window, min_periods=minimum).median()
    return result


def build_daily_technical(base: a4b.A4BData) -> pd.DataFrame:
    """Build point-in-time technical fields from validated GBP TR endpoints."""

    benchmark = "GLOBAL_DEVELOPED_WORLD"
    families = sorted(set(base.members) | {benchmark})
    calendar = base.research.calendar
    benchmark_wealth = base.research.wealth[benchmark]
    benchmark_segment = base.research.segment[benchmark]
    rows: list[pd.DataFrame] = []
    for family in families:
        wealth = base.research.wealth[family].astype(float)
        segment = base.research.segment[family]
        returns = base.research.daily_returns[family].astype(float)
        frame = pd.DataFrame({
            "date": calendar,
            "economic_exposure_family_id": family,
            "INDEX_GBP_TOTAL_RETURN": wealth.to_numpy(),
            "CONTINUITY_SEGMENT_ID": segment.to_numpy(),
            "RETURN_GBP_TOTAL": returns.to_numpy(),
        }).set_index("date")
        for span in (21, 50, 200):
            frame[f"ABS_EMA_{span}"] = _segment_ewm(wealth, segment, span).to_numpy()
            frame[f"ABS_DISTANCE_EMA_{span}"] = frame["INDEX_GBP_TOTAL_RETURN"] / frame[f"ABS_EMA_{span}"] - 1.0
        vol63 = _segment_rolling_std(returns, segment, 63, 63) * math.sqrt(252.0)
        vol21 = _segment_rolling_std(returns, segment, 21, 21) * math.sqrt(252.0)
        prior_median = _segment_prior_median(vol21, segment, 126, 63)
        frame["REALISED_VOL_63"] = vol63.to_numpy()
        frame["REALISED_VOL_21"] = vol21.to_numpy()
        frame["VOL_EXPANSION_RATIO"] = (vol21 / prior_median).to_numpy()

        relative = (wealth / benchmark_wealth).where(wealth.notna() & benchmark_wealth.notna())
        combined_segment = segment.astype("string") + "|" + benchmark_segment.astype("string")
        combined_segment = combined_segment.where(segment.notna() & benchmark_segment.notna())
        frame["RELATIVE_TR_INDEX"] = relative.to_numpy()
        frame["RELATIVE_COMBINED_SEGMENT"] = combined_segment.to_numpy()
        for span in (21, 42, 50):
            rel_ema = _segment_ewm(relative, combined_segment, span)
            frame[f"REL_EMA_{span}"] = rel_ema.to_numpy()
            frame[f"REL_DISTANCE_EMA_{span}"] = frame["RELATIVE_TR_INDEX"] / frame[f"REL_EMA_{span}"] - 1.0
        frame["ABS_BELOW_EMA21"] = frame["INDEX_GBP_TOTAL_RETURN"].lt(frame["ABS_EMA_21"])
        frame["ABS_BELOW_EMA50"] = frame["INDEX_GBP_TOTAL_RETURN"].lt(frame["ABS_EMA_50"])
        frame["ABS_BELOW_EMA200"] = frame["INDEX_GBP_TOTAL_RETURN"].lt(frame["ABS_EMA_200"])
        frame["REL_BELOW_EMA42"] = frame["RELATIVE_TR_INDEX"].lt(frame["REL_EMA_42"])
        frame["DATA_VALID"] = wealth.notna().to_numpy()
        rows.append(frame.reset_index())
    result = pd.concat(rows, ignore_index=True)
    result["WARNING"] = WARNING
    return result.sort_values(["date", "economic_exposure_family_id"]).reset_index(drop=True)


def _augment_features(
    base: a4b.A4BData,
    source: pd.DataFrame,
    daily_technical: pd.DataFrame,
    frequency: str,
) -> pd.DataFrame:
    frame = source.copy()
    dates = pd.DatetimeIndex(frame["date"].unique()).sort_values()
    members = base.members
    for source_name, output in (("REL_SLOPE_21", "RELATIVE_SLOPE_21"), ("RELATIVE_SLOPE_CHANGE", "RELATIVE_SLOPE_CHANGE")):
        part = _long_matrix(base.research.matrices.relative_features[source_name], dates, members, output)
        frame = frame.merge(part, on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    technical_columns = [
        "date", "economic_exposure_family_id", "INDEX_GBP_TOTAL_RETURN", "ABS_EMA_21", "ABS_EMA_50", "ABS_EMA_200",
        "ABS_DISTANCE_EMA_21", "ABS_DISTANCE_EMA_50", "ABS_DISTANCE_EMA_200", "ABS_BELOW_EMA21", "ABS_BELOW_EMA50",
        "ABS_BELOW_EMA200", "REALISED_VOL_63", "REALISED_VOL_21", "VOL_EXPANSION_RATIO", "RELATIVE_TR_INDEX",
        "REL_EMA_21", "REL_EMA_42", "REL_EMA_50", "REL_DISTANCE_EMA_21", "REL_DISTANCE_EMA_42", "REL_DISTANCE_EMA_50",
        "REL_BELOW_EMA42", "DATA_VALID",
    ]
    exact = daily_technical.loc[daily_technical["date"].isin(dates), technical_columns]
    frame = frame.merge(exact, on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    frame = frame.sort_values(["economic_exposure_family_id", "date"]).reset_index(drop=True)
    frame["FAST_MINUS_SLOW"] = frame["FAST_RS"] - frame["SLOW_RS"]
    frame["FAST_RS_CHANGE_1W"] = frame.groupby("economic_exposure_family_id", sort=False)["FAST_RS"].diff(1)
    if frequency == "WEEKLY":
        frame["FAST_ORDINAL_IMPROVEMENT_1W"] = -frame.groupby("economic_exposure_family_id", sort=False)["FAST_ORDINAL_RANK"].diff(1)
        frame["FAST_ORDINAL_IMPROVEMENT_4W"] = -frame.groupby("economic_exposure_family_id", sort=False)["FAST_ORDINAL_RANK"].diff(4)
        frame["SLOW_ORDINAL_IMPROVEMENT_1W"] = -frame.groupby("economic_exposure_family_id", sort=False)["SLOW_ORDINAL_RANK"].diff(1)
    else:
        frame["FAST_ORDINAL_IMPROVEMENT_1W"] = np.nan
        frame["FAST_ORDINAL_IMPROVEMENT_4W"] = np.nan
        frame["SLOW_ORDINAL_IMPROVEMENT_1W"] = np.nan
    frame["POSITIVE_RECENT_RELATIVE_SEGMENTS"] = frame[["REL_SEG_0_1M", "REL_SEG_1_2M", "REL_SEG_2_3M"]].gt(0).sum(axis=1).where(
        frame[["REL_SEG_0_1M", "REL_SEG_1_2M", "REL_SEG_2_3M"]].notna().all(axis=1)
    )
    policy = read_policy()["fast_crossover"]
    for variant in ("PRIMARY", "LOOSER", "TIGHTER"):
        rules = policy[variant]
        flag = (
            frame["FAST_RS"].ge(float(rules["fast_percentile_min"]))
            & frame["FAST_MINUS_SLOW"].ge(float(rules["fast_minus_slow_min"]))
            & frame["FAST_RS_CHANGE_4W"].ge(float(rules["fast_change_4w_min"]))
            & frame["RS_63"].gt(0)
            & frame["RELATIVE_SLOPE_42"].gt(0)
            & frame["DATA_VALID"].fillna(False)
        )
        frame[f"FAST_CROSSOVER_{variant}"] = flag
        if frequency == "WEEKLY":
            run = flag.groupby(frame["economic_exposure_family_id"], sort=False).transform(
                lambda values: values.astype(int).groupby((~values).cumsum()).cumsum()
            )
            frame[f"FAST_CROSSOVER_PERSISTENCE_{variant}"] = run.where(flag, 0).astype(int)
        else:
            frame[f"FAST_CROSSOVER_PERSISTENCE_{variant}"] = np.where(flag, 1, 0)
    frame["WARNING"] = WARNING
    return frame.sort_values(["date", "economic_exposure_family_id"]).reset_index(drop=True)


def load_a4c_data() -> A4CData:
    policy = read_policy()
    base = a4b.load_a4b_data()
    daily = build_daily_technical(base)
    weekly = _augment_features(base, base.weekly_features, daily, "WEEKLY")
    monthly = _augment_features(base, base.monthly_features, daily, "MONTHLY_ONLY")
    return A4CData(policy, base, weekly, monthly, daily)


def feature_frame(data: A4CData, date: pd.Timestamp, frequency: str = "WEEKLY") -> pd.DataFrame:
    source = data.weekly_features if frequency == "WEEKLY" else data.monthly_features
    dates = source.loc[source["date"].le(pd.Timestamp(date)), "date"]
    if dates.empty:
        return source.iloc[0:0].copy()
    return source.loc[source["date"].eq(dates.max())].copy()


def family_row(frame: pd.DataFrame, family: str) -> pd.Series:
    match = frame.loc[frame["economic_exposure_family_id"].eq(family)]
    return match.iloc[0] if len(match) else pd.Series(dtype=object)


def management_dates(data: A4CData, review_start: pd.Timestamp, weekly: bool = True) -> list[pd.Timestamp]:
    dates = pd.DatetimeIndex(data.weekly_features["date"].unique()) if weekly else pd.DatetimeIndex(data.monthly_features["date"].unique())
    if weekly:
        dates = dates.union(pd.DatetimeIndex(data.monthly_features["date"].unique())).union(pd.DatetimeIndex([review_start]))
    return [pd.Timestamp(value) for value in dates[(dates >= review_start) & (dates <= CUTOFF)].sort_values()]


def monthly_leaders(data: A4CData, excluded_families: set[str] | None = None, maturity_scope: str = "DYNAMIC_POINT_IN_TIME") -> pd.DataFrame:
    return a4b.monthly_leaders(data.monthly_features, excluded_families=excluded_families, maturity_scope=maturity_scope)


def leader_at(leaders: pd.DataFrame, date: pd.Timestamp) -> str:
    rows = leaders.loc[leaders["monthly_review_date"].le(pd.Timestamp(date))]
    return str(rows.iloc[-1]["incumbent_family"]) if len(rows) else ""


def build_baseline_plan(
    data: A4CData,
    *,
    review_start: pd.Timestamp = LATEST5_REVIEW_START,
    excluded_families: set[str] | None = None,
    maturity_scope: str = "DYNAMIC_POINT_IN_TIME",
) -> a4b.PlannedPortfolio:
    # Reuse the exact A4B builder, substituting only the augmented feature frames
    # (which retain the frozen SLOW_RS values byte-for-byte).
    replaced = a4b.A4BData(
        data.base.policy,
        data.base.research,
        data.base.members,
        data.base.metadata,
        data.weekly_features,
        data.monthly_features,
        data.base.weekly_regime,
        data.base.monthly_regime,
        data.base.cash_index,
    )
    return a4b_lifecycle.build_plan(
        replaced,
        "A4_BASELINE_MONTHLY",
        frequency="MONTHLY_ONLY",
        scale_module="NONE",
        exit_module="NONE",
        review_start=review_start,
        excluded_families=excluded_families,
        maturity_scope=maturity_scope,
    )


def _planned_portfolio(
    planner: a4b.TargetPlanner,
    module_id: str,
    frequency: str,
    decisions: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> a4b.PlannedPortfolio:
    return a4b.PlannedPortfolio(module_id, frequency, planner.targets, planner.events, planner.cancelled, pd.DataFrame(decisions), pd.DataFrame(actions))


def _candidate(frame: pd.DataFrame, incumbent: str, variant: str, persistence: int) -> str:
    flag = f"FAST_CROSSOVER_{variant}"
    run = f"FAST_CROSSOVER_PERSISTENCE_{variant}"
    candidates = frame.loc[
        frame[flag].fillna(False)
        & frame[run].ge(int(persistence))
        & frame["economic_exposure_family_id"].ne(incumbent)
    ].sort_values(["FAST_RS", "SLOW_RS", "economic_exposure_family_id"], ascending=[False, False, True])
    return str(candidates.iloc[0]["economic_exposure_family_id"]) if len(candidates) else ""


def build_early_plan(
    data: A4CData,
    architecture: str,
    *,
    review_start: pd.Timestamp = LATEST5_REVIEW_START,
    crossover_variant: str = "PRIMARY",
    excluded_families: set[str] | None = None,
    maturity_scope: str = "DYNAMIC_POINT_IN_TIME",
) -> a4b.PlannedPortfolio:
    module_id = f"{architecture}_{crossover_variant}_WEEKLY"
    leaders = monthly_leaders(data, excluded_families, maturity_scope)
    dates = management_dates(data, review_start, weekly=True)
    planner = a4b.TargetPlanner(data.base, module_id, "WEEKLY")
    monthly_set = set(pd.DatetimeIndex(data.monthly_features["date"].unique()))
    decisions: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    challenger = ""
    challenger_max_weight = 0.0
    slow_improvement_run = 0
    last_challenger_slow_rank = np.nan
    last_monthly_leader = ""
    confirmed_top3 = False

    for date in dates:
        frame = a4b.filter_features(feature_frame(data, date, "WEEKLY"), excluded_families=excluded_families, maturity_scope=maturity_scope)
        incumbent = leader_at(leaders, date)
        if not incumbent:
            continue
        monthly_reset = date in monthly_set and incumbent != last_monthly_leader
        if monthly_reset:
            challenger = ""
            challenger_max_weight = 0.0
            slow_improvement_run = 0
            last_challenger_slow_rank = np.nan
            confirmed_top3 = False
        if date in monthly_set:
            last_monthly_leader = incumbent

        entry_persistence = 2 if architecture == "EARLY_B" else 1
        if challenger:
            row = family_row(frame, challenger)
            crossover = bool(row.get(f"FAST_CROSSOVER_{crossover_variant}", False)) if len(row) else False
            slow_rank = float(row.get("SLOW_ORDINAL_RANK", np.nan)) if len(row) and pd.notna(row.get("SLOW_ORDINAL_RANK", np.nan)) else np.nan
            improved = pd.notna(slow_rank) and pd.notna(last_challenger_slow_rank) and slow_rank < float(last_challenger_slow_rank)
            slow_improvement_run = slow_improvement_run + 1 if improved else 0
            if pd.notna(slow_rank):
                last_challenger_slow_rank = slow_rank
            if pd.notna(slow_rank) and slow_rank <= 3:
                confirmed_top3 = True
            fail_before_confirmation = not crossover and not confirmed_top3
            if architecture == "EARLY_C":
                fail_before_confirmation = not crossover and slow_improvement_run < 2 and not confirmed_top3
            if fail_before_confirmation:
                actions.append({"module_id": module_id, "review_date": date, "action_type": "SCOUT_FALSE_START_EXIT", "family": challenger, "from_weight": challenger_max_weight, "to_weight": 0.0, "reason": "CROSSOVER_FAILED_BEFORE_REQUIRED_SLOW_CONFIRMATION"})
                challenger = ""
                challenger_max_weight = 0.0
                slow_improvement_run = 0
                last_challenger_slow_rank = np.nan
                confirmed_top3 = False

        if not challenger:
            proposed = _candidate(frame, incumbent, crossover_variant, entry_persistence)
            if proposed:
                challenger = proposed
                row = family_row(frame, challenger)
                last_challenger_slow_rank = float(row["SLOW_ORDINAL_RANK"]) if pd.notna(row.get("SLOW_ORDINAL_RANK", np.nan)) else np.nan
                challenger_max_weight = 0.20 if architecture == "EARLY_A" else 0.25
                actions.append({"module_id": module_id, "review_date": date, "action_type": "SCOUT_ENTRY", "family": challenger, "from_weight": 0.0, "to_weight": challenger_max_weight, "reason": f"{crossover_variant}_{entry_persistence}W_PERSISTENCE"})

        target: dict[str, float]
        challenger_weight = 0.0
        if challenger:
            row = family_row(frame, challenger)
            slow_rank = float(row.get("SLOW_ORDINAL_RANK", np.nan)) if len(row) and pd.notna(row.get("SLOW_ORDINAL_RANK", np.nan)) else np.nan
            persistence = int(row.get(f"FAST_CROSSOVER_PERSISTENCE_{crossover_variant}", 0)) if len(row) else 0
            proposed_weight = challenger_max_weight
            if architecture == "EARLY_A":
                if persistence >= 2:
                    proposed_weight = max(proposed_weight, 0.40)
                if pd.notna(slow_rank) and slow_rank <= 3:
                    proposed_weight = max(proposed_weight, 0.60)
                if pd.notna(slow_rank) and slow_rank <= 1:
                    proposed_weight = 1.0
            elif architecture == "EARLY_B":
                if pd.notna(slow_rank) and slow_rank <= 5:
                    proposed_weight = max(proposed_weight, 0.50)
                if pd.notna(slow_rank) and slow_rank <= 3:
                    proposed_weight = max(proposed_weight, 0.75)
                if pd.notna(slow_rank) and slow_rank <= 1:
                    proposed_weight = 1.0
            elif architecture == "EARLY_C":
                if slow_improvement_run >= 2:
                    proposed_weight = max(proposed_weight, 0.50)
                    if pd.notna(slow_rank) and slow_rank <= 3:
                        proposed_weight = max(proposed_weight, 0.75)
                if pd.notna(slow_rank) and slow_rank <= 1:
                    proposed_weight = 1.0
            else:
                raise ValueError(architecture)
            if proposed_weight > challenger_max_weight + 1e-12:
                actions.append({"module_id": module_id, "review_date": date, "action_type": "SCOUT_SCALE_UP", "family": challenger, "from_weight": challenger_max_weight, "to_weight": proposed_weight, "reason": f"{architecture}_FROZEN_LADDER"})
            challenger_max_weight = max(challenger_max_weight, proposed_weight)
            challenger_weight = challenger_max_weight
            target = {challenger: challenger_weight}
            if incumbent != challenger and challenger_weight < 1.0:
                incumbent_row = family_row(frame, incumbent)
                if len(incumbent_row) and pd.notna(incumbent_row.get("INDEX_GBP_TOTAL_RETURN", np.nan)):
                    target[incumbent] = 1.0 - challenger_weight
        else:
            target = {incumbent: 1.0}

        execution = planner.submit(date, target, f"{architecture}|{crossover_variant}|FROZEN_SLOW_INCUMBENT")
        decisions.append({
            "module_id": module_id, "review_date": date, "monthly_incumbent": incumbent, "challenger": challenger,
            "challenger_weight": challenger_weight, "slow_improvement_run": slow_improvement_run,
            "confirmed_slow_top3": confirmed_top3, "target_weights_json": json.dumps(target, sort_keys=True),
            "execution_status": execution["execution_status"], "execution_date": execution.get("execution_date", pd.NaT), "warning": WARNING,
        })
    return _planned_portfolio(planner, module_id, "WEEKLY", decisions, actions)


def build_exit_plan(
    data: A4CData,
    exit_module: str,
    *,
    review_start: pd.Timestamp = LATEST5_REVIEW_START,
    excluded_families: set[str] | None = None,
    maturity_scope: str = "DYNAMIC_POINT_IN_TIME",
) -> a4b.PlannedPortfolio:
    module_id = exit_module
    leaders = monthly_leaders(data, excluded_families, maturity_scope)
    dates = management_dates(data, review_start, weekly=True)
    monthly_set = set(pd.DatetimeIndex(data.monthly_features["date"].unique()))
    planner = a4b.TargetPlanner(data.base, module_id, "WEEKLY")
    decisions: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    locked_out = False
    below21_reduced = False
    relative_failure_run = 0
    last_monthly_date: pd.Timestamp | None = None

    for date in dates:
        incumbent = leader_at(leaders, date)
        if not incumbent:
            continue
        is_monthly = date in monthly_set
        if is_monthly and date != last_monthly_date:
            locked_out = False
            below21_reduced = False
            relative_failure_run = 0
            last_monthly_date = date
        frame = a4b.filter_features(feature_frame(data, date, "WEEKLY"), excluded_families=excluded_families, maturity_scope=maturity_scope)
        row = family_row(frame, incumbent)
        below21 = bool(row.get("ABS_BELOW_EMA21", False)) if len(row) else False
        below50 = bool(row.get("ABS_BELOW_EMA50", False)) if len(row) else False
        rel_below42 = bool(row.get("REL_BELOW_EMA42", False)) if len(row) else False
        relative_failure_now = bool(
            len(row)
            and pd.notna(row.get("RELATIVE_SLOPE_42", np.nan))
            and float(row["RELATIVE_SLOPE_42"]) < 0
            and pd.notna(row.get("FAST_RS", np.nan))
            and float(row["FAST_RS"]) < 0.50
        )
        relative_failure_run = relative_failure_run + 1 if relative_failure_now else 0
        target_weight = 1.0
        trigger = "NONE"
        if locked_out:
            target_weight = 0.0
            trigger = "LOCKED_OUT_UNTIL_MONTHLY_REVIEW"
        if exit_module == "EXIT_A_50EMA" and below50:
            target_weight, locked_out, trigger = 0.0, True, "ABS_BELOW_EMA50"
        elif exit_module == "EXIT_B_21_WARNING_50_FAILURE":
            if below50:
                target_weight, locked_out, below21_reduced, trigger = 0.0, True, False, "ABS_BELOW_EMA50"
            elif not locked_out and below21:
                target_weight, below21_reduced, trigger = 0.75, True, "ABS_BELOW_EMA21"
            elif not locked_out and below21_reduced and not below21:
                target_weight, below21_reduced, trigger = 1.0, False, "RECOVERED_ABOVE_EMA21"
        elif exit_module == "EXIT_C_ABSOLUTE_AND_RELATIVE" and below50 and rel_below42:
            target_weight, locked_out, trigger = 0.0, True, "ABS_BELOW_EMA50_AND_REL_BELOW_EMA42"
        elif exit_module == "EXIT_D_RELATIVE_ONLY" and relative_failure_run >= 2:
            target_weight, locked_out, trigger = 0.0, True, "TWO_WEEK_RELATIVE_FAILURE"
        elif exit_module not in {"EXIT_A_50EMA", "EXIT_B_21_WARNING_50_FAILURE", "EXIT_C_ABSOLUTE_AND_RELATIVE", "EXIT_D_RELATIVE_ONLY"}:
            raise ValueError(exit_module)
        target = {incumbent: target_weight} if target_weight > 1e-12 else {}
        before = dict(planner.current_target)
        execution = planner.submit(date, target, f"{exit_module}|{trigger}")
        if not a4b.weight_dict_equal(before, target):
            action_type = trigger if trigger != "NONE" else ("MONTHLY_REENTRY_OR_SELECTION" if is_monthly else "TARGET_RESTORE")
            actions.append({"module_id": module_id, "review_date": date, "family": incumbent, "action_type": action_type, "from_weights_json": json.dumps(before, sort_keys=True), "to_weights_json": json.dumps(target, sort_keys=True), "warning": WARNING})
        decisions.append({
            "module_id": module_id, "review_date": date, "monthly_incumbent": incumbent,
            "abs_below_ema21": below21, "abs_below_ema50": below50, "relative_below_ema42": rel_below42,
            "relative_failure_run": relative_failure_run, "target_risky_weight": target_weight, "trigger": trigger,
            "execution_status": execution["execution_status"], "execution_date": execution.get("execution_date", pd.NaT), "warning": WARNING,
        })
    return _planned_portfolio(planner, module_id, "WEEKLY", decisions, actions)


def build_volatility_plan(
    data: A4CData,
    target_vol: float,
    *,
    review_start: pd.Timestamp = LATEST5_REVIEW_START,
    excluded_families: set[str] | None = None,
    maturity_scope: str = "DYNAMIC_POINT_IN_TIME",
) -> a4b.PlannedPortfolio:
    module_id = f"VOL_TARGET_{str(target_vol).replace('.', '_')}"
    leaders = monthly_leaders(data, excluded_families, maturity_scope)
    dates = management_dates(data, review_start, weekly=False)
    planner = a4b.TargetPlanner(data.base, module_id, "MONTHLY_ONLY")
    floor = float(data.policy["formation_features"]["volatility_floor_annualised"])
    decisions: list[dict[str, Any]] = []
    for date in dates:
        incumbent = leader_at(leaders, date)
        frame = feature_frame(data, date, "MONTHLY_ONLY")
        row = family_row(frame, incumbent)
        sigma = float(row.get("REALISED_VOL_63", np.nan)) if len(row) and pd.notna(row.get("REALISED_VOL_63", np.nan)) else np.nan
        weight = min(1.0, float(target_vol) / max(sigma, floor)) if pd.notna(sigma) else 0.0
        target = {incumbent: weight} if incumbent and weight > 1e-12 else {}
        execution = planner.submit(date, target, f"VOL_TARGET_{target_vol:.4f}|PRIOR_63D_VOL")
        decisions.append({"module_id": module_id, "review_date": date, "monthly_incumbent": incumbent, "prior_realised_vol_63": sigma, "volatility_floor": floor, "target_volatility": target_vol, "target_risky_weight": weight, "target_cash_weight": 1.0 - weight, "execution_status": execution["execution_status"], "execution_date": execution.get("execution_date", pd.NaT), "warning": WARNING})
    return _planned_portfolio(planner, module_id, "MONTHLY_ONLY", decisions, [])


def build_forced_plan(
    data: A4CData,
    module_id: str,
    review_targets: dict[pd.Timestamp, dict[str, float]],
    reason: str,
) -> a4b.PlannedPortfolio:
    """Create next-session events at every review, including same-member rebalance."""

    calendar = data.base.research.calendar
    date_position = {pd.Timestamp(date): index for index, date in enumerate(calendar)}
    current_members: set[str] = set()
    current_segments: dict[str, Any] = {}
    events: list[dict[str, Any]] = []
    cancelled: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    targets: dict[pd.Timestamp, dict[str, float]] = {}
    for review_date, target in sorted(review_targets.items()):
        review_date = pd.Timestamp(review_date)
        if review_date not in date_position:
            continue
        clean = {str(f): float(w) for f, w in target.items() if float(w) > 1e-12}
        if sum(clean.values()) > 1.0 + 1e-12 or any(value < 0 for value in clean.values()):
            raise AssertionError("Forced target violates long-only/no-leverage contract")
        targets[review_date] = clean
        review_position = date_position[review_date]
        execution_position: int | None = None
        for lag in range(1, 4):
            position = review_position + lag
            if position >= len(calendar):
                break
            valid = bool(pd.notna(data.base.cash_index.iloc[position]))
            for family in current_members | set(clean):
                valid &= bool(pd.notna(data.base.research.wealth.iloc[position][family]))
                if family in current_members:
                    valid &= data.base.research.segment.iloc[position][family] == current_segments[family]
            if valid:
                execution_position = position
                break
        if execution_position is None:
            row = {"module_id": module_id, "review_date": review_date, "execution_date": pd.NaT, "execution_position": np.nan, "execution_lag_xlon_sessions": np.nan, "execution_status": "CANCELLED_NO_COMMON_VALID_ENDPOINT_WITHIN_3_XLON_SESSIONS", "target": clean, "reason": reason}
            cancelled.append(row)
            decisions.append({**{key: value for key, value in row.items() if key != "target"}, "target_weights_json": json.dumps(clean, sort_keys=True), "warning": WARNING})
            continue
        row = {"module_id": module_id, "review_date": review_date, "execution_date": pd.Timestamp(calendar[execution_position]), "execution_position": int(execution_position), "execution_lag_xlon_sessions": int(execution_position - review_position), "execution_status": "PLANNED", "target": clean, "reason": reason}
        events.append(row)
        current_members = set(clean)
        current_segments = {family: data.base.research.segment.iloc[execution_position][family] for family in clean}
        decisions.append({"module_id": module_id, "review_date": review_date, "execution_date": row["execution_date"], "execution_lag_xlon_sessions": row["execution_lag_xlon_sessions"], "execution_status": "PLANNED", "target_weights_json": json.dumps(clean, sort_keys=True), "warning": WARNING})
    return a4b.PlannedPortfolio(module_id, "MONTHLY_FORCED_REBALANCE", targets, events, cancelled, pd.DataFrame(decisions), pd.DataFrame())


def build_core_satellite_plan(
    data: A4CData,
    active_weight: float,
    *,
    review_start: pd.Timestamp = LATEST5_REVIEW_START,
    active_weight_override: pd.Series | None = None,
    excluded_families: set[str] | None = None,
    maturity_scope: str = "DYNAMIC_POINT_IN_TIME",
) -> a4b.PlannedPortfolio:
    core_family = str(data.policy["core_satellite"]["core_family"])
    leaders = monthly_leaders(data, excluded_families, maturity_scope)
    dates = management_dates(data, review_start, weekly=False)
    targets: dict[pd.Timestamp, dict[str, float]] = {}
    for date in dates:
        leader = leader_at(leaders, date)
        strategic_active = float(active_weight)
        if active_weight_override is not None:
            eligible = active_weight_override.loc[active_weight_override.index <= date]
            strategic_active *= float(eligible.iloc[-1]) if len(eligible) else 0.0
        target: dict[str, float] = {}
        if strategic_active > 1e-12 and leader:
            target[leader] = strategic_active
        core_weight = 1.0 - float(active_weight)
        if core_weight > 1e-12:
            target[core_family] = core_weight
        targets[date] = target
    module_id = f"CORE_ACTIVE_{int(round(active_weight * 100))}"
    return build_forced_plan(data, module_id, targets, "FROZEN_MONTHLY_CORE_SATELLITE_REBALANCE")


def simulate(plan: a4b.PlannedPortfolio, data: A4CData, *, friction_bps: float | None = None, fixed_fee_gbp: float | None = None, sleeve_size_gbp: float | None = None) -> a4b.A4BSimulation:
    return a4b.simulate_planned_portfolio(plan, data.base, friction_bps=friction_bps, fixed_fee_gbp=fixed_fee_gbp, sleeve_size_gbp=sleeve_size_gbp)


def cagr_from_curve(curve: pd.DataFrame, start: pd.Timestamp | None, end: pd.Timestamp | None) -> float:
    source = curve.copy()
    if start is not None:
        source = source.loc[source["date"].ge(pd.Timestamp(start))]
    if end is not None:
        source = source.loc[source["date"].le(pd.Timestamp(end))]
    source = source.drop_duplicates("date").sort_values("date")
    if len(source) < 2:
        return np.nan
    values = source["portfolio_value"].astype(float)
    years = max((pd.Timestamp(source.iloc[-1]["date"]) - pd.Timestamp(source.iloc[0]["date"])).days / 365.2425, 1 / 365.2425)
    return float((values.iloc[-1] / values.iloc[0]) ** (1 / years) - 1)


def comparator_curves(data: A4CData, review_start: pd.Timestamp = LATEST5_REVIEW_START) -> dict[str, pd.DataFrame]:
    monthly = data.monthly_features.loc[data.monthly_features["date"].ge(review_start)].copy()
    pool_targets: dict[pd.Timestamp, dict[str, float]] = {}
    leaders = monthly_leaders(data)
    unselected_targets: dict[pd.Timestamp, dict[str, float]] = {}
    for date, group in monthly.groupby("date", sort=True):
        valid = group.loc[group["SLOW_RS"].notna(), "economic_exposure_family_id"].sort_values().tolist()
        pool_targets[pd.Timestamp(date)] = {family: 1.0 / len(valid) for family in valid} if valid else {}
        leader = leader_at(leaders, pd.Timestamp(date))
        remainder = [family for family in valid if family != leader]
        unselected_targets[pd.Timestamp(date)] = {family: 1.0 / len(remainder) for family in remainder} if remainder else {}
    pool = a3p.simulate_equal_weight_benchmark(pool_targets, calendar=data.base.research.calendar, daily_returns=data.base.research.daily_returns)
    unselected = a3p.simulate_equal_weight_benchmark(unselected_targets, calendar=data.base.research.calendar, daily_returns=data.base.research.daily_returns)
    global_targets = {review_start: {"GLOBAL_DEVELOPED_WORLD": 1.0}}
    global_plan = build_forced_plan(data, "GLOBAL_DEVELOPED_WORLD_BENCHMARK", global_targets, "BENCHMARK_INIT")
    global_sim = simulate(global_plan, data, friction_bps=0.0, fixed_fee_gbp=0.0)
    return {"GLOBAL_DEVELOPED_WORLD": global_sim.curve, "EQUAL_WEIGHT_POOL": pool.curve, "UNSELECTED_POOL": unselected.curve}


def metric_row(
    simulation: a4b.A4BSimulation,
    data: A4CData,
    module_id: str,
    *,
    start: pd.Timestamp = LATEST5_START,
    end: pd.Timestamp = CUTOFF,
    comparators: dict[str, pd.DataFrame] | None = None,
) -> dict[str, Any]:
    result = a4b.enhanced_performance_metrics(simulation, start=start, end=end)
    row: dict[str, Any] = {"module_id": module_id, "window_start": start, "window_end": end, **result}
    if comparators is not None:
        global_cagr = cagr_from_curve(comparators["GLOBAL_DEVELOPED_WORLD"], start, end)
        pool_cagr = cagr_from_curve(comparators["EQUAL_WEIGHT_POOL"], start, end)
        unselected_cagr = cagr_from_curve(comparators["UNSELECTED_POOL"], start, end)
        row.update({
            "global_benchmark_cagr": global_cagr,
            "equal_weight_pool_cagr": pool_cagr,
            "unselected_pool_cagr": unselected_cagr,
            "net_excess_vs_global": result.get("net_cagr", np.nan) - global_cagr,
            "net_excess_vs_equal_pool": result.get("net_cagr", np.nan) - pool_cagr,
            "selected_vs_unselected_spread": result.get("net_cagr", np.nan) - unselected_cagr,
        })
    row["warning"] = WARNING
    return row


def exact_baseline_reproduction(simulation: a4b.A4BSimulation) -> pd.DataFrame:
    actual = a4b.enhanced_performance_metrics(simulation, start=LATEST5_START, end=CUTOFF)
    source = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4_TOP1_TOP2_TOP3_COMPARISON.csv")
    expected = source.loc[source["candidate_id"].eq("A4_TOP1")].iloc[0]
    checks = [
        ("net_cagr", float(expected["selected_net_cagr"]), float(actual["net_cagr"]), 1e-12),
        ("maximum_drawdown", float(expected["selected_net_maximum_drawdown"]), float(actual["maximum_drawdown"]), 1e-12),
        ("annual_turnover_traded_notional", float(expected["selected_net_annual_turnover_traded_notional"]), float(actual["annual_turnover_traded_notional"]), 1e-12),
        ("trade_legs", float(expected["selected_net_trade_legs"]), float(actual["trade_legs"]), 0.0),
    ]
    return pd.DataFrame([{"test_id": name, "a4_expected": expected_value, "a4c_actual": actual_value, "absolute_difference": abs(actual_value - expected_value), "tolerance": tolerance, "result": "PASS" if abs(actual_value - expected_value) <= tolerance else "FAIL", "warning": WARNING} for name, expected_value, actual_value, tolerance in checks])


def window_definitions(policy: dict[str, Any]) -> dict[str, tuple[pd.Timestamp | None, pd.Timestamp | None]]:
    values = policy["windows"]
    return {
        "LATEST_5Y": (pd.Timestamp(values["LATEST_5Y_START"]), pd.Timestamp(values["CUTOFF"])),
        "LATEST_3Y": (pd.Timestamp(values["LATEST_3Y_START"]), pd.Timestamp(values["CUTOFF"])),
        "POST_2020": (pd.Timestamp(values["POST_2020_START"]), pd.Timestamp(values["CUTOFF"])),
        "PRE_2020": (None, pd.Timestamp(values["PRE_2020_END"])),
        "FULL_HISTORY": (None, pd.Timestamp(values["CUTOFF"])),
    }


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
