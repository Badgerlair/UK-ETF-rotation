"""Core primitives for UKACTIVE-A4B lifecycle and regime research.

The module deliberately reuses the corrected A2R2 endpoint chain and the
frozen A3R2 rank mathematics.  It adds only point-in-time position-management
state, actual GBP cash accrual, next-session target execution and enhanced
drawdown/profit-retention diagnostics.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

import ukactive_a3r2_portfolio as a3p
from ukactive_a3r1_core import percentile_rank


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = PROGRAMME_ROOT / "config" / "UKACTIVE_A4B_POLICY_v1.json"
WARNING = "HISTORICAL UK RETAIL, ISA, ACCOUNT AND BROKER ELIGIBILITY REMAIN PARTLY UNRESOLVED"
RESEARCH_WARNING = "A4B IS E2 DEVELOPMENTAL RESEARCH; NO E3 CONFIRMATION"


@dataclass
class A4BData:
    policy: dict[str, Any]
    research: a3p.ResearchData
    members: list[str]
    metadata: pd.DataFrame
    weekly_features: pd.DataFrame
    monthly_features: pd.DataFrame
    weekly_regime: pd.DataFrame
    monthly_regime: pd.DataFrame
    cash_index: pd.Series


@dataclass
class PlannedPortfolio:
    module_id: str
    management_frequency: str
    targets: dict[pd.Timestamp, dict[str, float]]
    events: list[dict[str, Any]]
    cancelled_events: list[dict[str, Any]]
    decisions: pd.DataFrame
    actions: pd.DataFrame


@dataclass
class A4BSimulation:
    module_id: str
    curve: pd.DataFrame
    trades: pd.DataFrame
    targets: pd.DataFrame
    decisions: pd.DataFrame
    actions: pd.DataFrame


def read_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _context_members(research: a3p.ResearchData) -> list[str]:
    for definition in research.definitions:
        if definition["context_id"] == "INDUSTRY_PLUS_THEME":
            return sorted(definition["members"])
    raise AssertionError("INDUSTRY_PLUS_THEME context is absent")


def _schedule_dates(calendar: pd.DatetimeIndex, frequency: str) -> pd.DatetimeIndex:
    cadence = "WEEKLY" if frequency == "WEEKLY" else "MONTHLY"
    return calendar[a3p.schedule_positions(calendar, cadence)]


def _ordinal_rank(frame: pd.DataFrame, score: str, output: str) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for date, group in frame.groupby("date", sort=True):
        valid = group.loc[group[score].notna()].sort_values(
            [score, "economic_exposure_family_id"], ascending=[False, True]
        ).copy()
        valid[output] = np.arange(1, len(valid) + 1, dtype=int)
        rows.append(valid[["date", "economic_exposure_family_id", output]])
    if not rows:
        return pd.DataFrame(columns=["date", "economic_exposure_family_id", output])
    return pd.concat(rows, ignore_index=True)


def _weekly_reference_change(
    current: pd.DataFrame,
    weekly: pd.DataFrame,
    field: str,
    output: str,
    prior_weekly_observations: int = 4,
) -> pd.Series:
    values: list[float] = []
    by_family = {
        family: group.sort_values("date")[["date", field]].reset_index(drop=True)
        for family, group in weekly.groupby("economic_exposure_family_id", sort=False)
    }
    for row in current[["date", "economic_exposure_family_id", field]].itertuples(index=False):
        history = by_family.get(row.economic_exposure_family_id)
        if history is None or pd.isna(getattr(row, field)):
            values.append(np.nan)
            continue
        dates = pd.DatetimeIndex(history["date"])
        insertion = int(dates.searchsorted(pd.Timestamp(row.date), side="left"))
        reference_position = insertion - int(prior_weekly_observations)
        if reference_position < 0:
            values.append(np.nan)
            continue
        reference = history.iloc[reference_position][field]
        values.append(float(getattr(row, field) - reference) if pd.notna(reference) else np.nan)
    return pd.Series(values, index=current.index, name=output, dtype=float)


def _expanding_prior_quantile_by_family(
    weekly: pd.DataFrame,
    value_field: str,
    quantile: float,
    minimum_prior: int,
) -> pd.DataFrame:
    out = weekly[["date", "economic_exposure_family_id", value_field]].copy()
    out["extension_threshold"] = out.groupby("economic_exposure_family_id", sort=False)[value_field].transform(
        lambda values: values.shift(1).expanding(min_periods=int(minimum_prior)).quantile(float(quantile))
    )
    return out[["date", "economic_exposure_family_id", "extension_threshold"]]


def _asof_family_field(
    current: pd.DataFrame,
    weekly_field: pd.DataFrame,
    value_field: str,
) -> pd.Series:
    pieces: list[pd.DataFrame] = []
    for family, group in current.groupby("economic_exposure_family_id", sort=False):
        right = weekly_field.loc[weekly_field["economic_exposure_family_id"].eq(family), ["date", value_field]].sort_values("date")
        left = group[["date"]].sort_values("date").copy()
        if right.empty:
            left[value_field] = np.nan
        else:
            left = pd.merge_asof(left, right, on="date", direction="backward", allow_exact_matches=True)
        left["economic_exposure_family_id"] = family
        pieces.append(left)
    merged = pd.concat(pieces, ignore_index=True)
    lookup = merged.set_index(["date", "economic_exposure_family_id"])[value_field]
    return pd.Series(
        [lookup.get((pd.Timestamp(row.date), row.economic_exposure_family_id), np.nan) for row in current.itertuples()],
        index=current.index,
        dtype=float,
    )


def _state_parameters(policy: dict[str, Any], variant: str) -> dict[str, float]:
    if variant == "PRIMARY":
        return {
            "emerging_fast": 0.90,
            "emerging_change": 0.10,
            "emerging_slow_max": 0.80,
            "confirming_fast": 0.80,
            "confirming_slow": 0.60,
            "weakening_fast": 0.50,
            "weakening_change": -0.20,
            "failed_rank": 5,
            "failed_fast": 0.50,
            "extension_quantile": 0.90,
        }
    source = policy["leadership_state_neighbourhoods"][variant]
    return {
        "emerging_fast": float(source["emerging_fast_min"]),
        "emerging_change": float(source["emerging_fast_change_min"]),
        "emerging_slow_max": float(source["emerging_slow_max"]),
        "confirming_fast": float(source["confirming_fast_min"]),
        "confirming_slow": float(source["confirming_slow_min"]),
        "weakening_fast": float(source["weakening_fast_cutoff"]),
        "weakening_change": float(source["weakening_fast_change_cutoff"]),
        "failed_rank": int(source["failed_rank_cutoff"]),
        "failed_fast": float(source["failed_fast_cutoff"]),
        "extension_quantile": float(source["extension_quantile"]),
    }


def _assign_states(frame: pd.DataFrame, params: dict[str, float]) -> pd.DataFrame:
    result = frame.copy()
    failed = (
        (result["SLOW_ORDINAL_RANK"].gt(params["failed_rank"]) & result["FAST_RS"].lt(params["failed_fast"]))
        | (result["RS_63"].le(0) & result["RELATIVE_SLOPE_42"].lt(0))
    )
    weakening = result["SLOW_ORDINAL_RANK"].le(3) & (
        result["FAST_RS"].lt(params["weakening_fast"])
        | result["FAST_RS_CHANGE_4W"].le(params["weakening_change"])
        | result["RELATIVE_SLOPE_42"].lt(0)
    )
    established = (
        result["SLOW_ORDINAL_RANK"].eq(1)
        & result["FAST_RS"].ge(0.50)
        & result["RS_63"].gt(0)
        & result["RELATIVE_SLOPE_42"].ge(0)
    )
    extended = established & result["RS_63"].gt(result["RS63_EXTENSION_THRESHOLD_PRIOR"])
    confirming = (
        result["FAST_RS"].ge(params["confirming_fast"])
        & result["SLOW_RS"].ge(params["confirming_slow"])
        & result["SLOW_RS_CHANGE_4W"].gt(0)
        & result["RS_63"].gt(0)
    )
    emerging = (
        result["FAST_RS"].ge(params["emerging_fast"])
        & result["RS_63"].gt(0)
        & result["FAST_RS_CHANGE_4W"].ge(params["emerging_change"])
        & result["SLOW_RS"].lt(params["emerging_slow_max"])
    )
    result["LEADERSHIP_STATE"] = np.select(
        [failed, weakening, extended, established, confirming, emerging],
        ["FAILED", "WEAKENING", "EXTENDED", "ESTABLISHED", "CONFIRMING", "EMERGING"],
        default="OTHER",
    )
    prior_state = result.groupby("economic_exposure_family_id", sort=False)["LEADERSHIP_STATE"].shift(1)
    result["STRONGER_WEAKENING_FLAG"] = result["LEADERSHIP_STATE"].eq("WEAKENING") & (
        result["FAST_RS"].lt(0.25)
        | (result["RELATIVE_SLOPE_42"].lt(0) & prior_state.eq("WEAKENING"))
    )
    result["EXTENSION_FLAG"] = extended
    result["STATE_THRESHOLD_VARIANT"] = result.get("STATE_THRESHOLD_VARIANT", "PRIMARY")
    return result


def build_management_features(
    research: a3p.ResearchData,
    members: list[str],
    policy: dict[str, Any],
    frequency: str,
    variant: str = "PRIMARY",
    weekly_reference: pd.DataFrame | None = None,
) -> pd.DataFrame:
    dates = _schedule_dates(research.calendar, frequency)
    positions = research.calendar.get_indexer(dates)
    ranks = {
        horizon: percentile_rank(research.matrices.relative_strength[horizon][members], minimum_count=3)
        for horizon in [21, 42, 63, 126, 252]
    }
    sampled: list[pd.DataFrame] = []
    for horizon, matrix in ranks.items():
        long = matrix.iloc[positions].copy()
        long.index = dates
        long = long.stack(future_stack=True).rename(f"RANK_RS_{horizon}").reset_index()
        long.columns = ["date", "economic_exposure_family_id", f"RANK_RS_{horizon}"]
        sampled.append(long)
    frame = sampled[0]
    for part in sampled[1:]:
        frame = frame.merge(part, on=["date", "economic_exposure_family_id"], how="outer", validate="one_to_one")
    for horizon in [21, 42, 63, 126, 252]:
        matrix = research.matrices.relative_strength[horizon][members].iloc[positions].copy()
        matrix.index = dates
        long = matrix.stack(future_stack=True).rename(f"RS_{horizon}").reset_index()
        long.columns = ["date", "economic_exposure_family_id", f"RS_{horizon}"]
        frame = frame.merge(long, on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    frame["FAST_RS"] = frame[["RANK_RS_21", "RANK_RS_42", "RANK_RS_63"]].mean(axis=1, skipna=False)
    frame["SLOW_RS"] = frame[["RANK_RS_63", "RANK_RS_126", "RANK_RS_252"]].mean(axis=1, skipna=False)
    for window in [42, 63]:
        matrix = research.matrices.relative_features[f"REL_SLOPE_{window}"][members].iloc[positions].copy()
        matrix.index = dates
        long = matrix.stack(future_stack=True).rename(f"RELATIVE_SLOPE_{window}").reset_index()
        long.columns = ["date", "economic_exposure_family_id", f"RELATIVE_SLOPE_{window}"]
        frame = frame.merge(long, on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    for segment_id in ["REL_SEG_0_1M", "REL_SEG_1_2M", "REL_SEG_2_3M"]:
        matrix = research.matrices.segments[segment_id][members].iloc[positions].copy()
        matrix.index = dates
        long = matrix.stack(future_stack=True).rename(segment_id).reset_index()
        long.columns = ["date", "economic_exposure_family_id", segment_id]
        frame = frame.merge(long, on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    accrued = research.matrices.accrued_valid[members].iloc[positions].copy()
    accrued.index = dates
    accrued_long = accrued.stack(future_stack=True).rename("ACCRUED_VALID_RETURN_OBSERVATIONS").reset_index()
    accrued_long.columns = ["date", "economic_exposure_family_id", "ACCRUED_VALID_RETURN_OBSERVATIONS"]
    frame = frame.merge(accrued_long, on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    frame["RESEARCH_MATURITY"] = np.select(
        [frame["ACCRUED_VALID_RETURN_OBSERVATIONS"].ge(1260), frame["ACCRUED_VALID_RETURN_OBSERVATIONS"].ge(504)],
        ["MATURE", "DEVELOPING"],
        default="NEW",
    )
    frame = frame.merge(_ordinal_rank(frame, "FAST_RS", "FAST_ORDINAL_RANK"), on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    frame = frame.merge(_ordinal_rank(frame, "SLOW_RS", "SLOW_ORDINAL_RANK"), on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    frame["MANAGEMENT_FREQUENCY"] = frequency
    frame["STATE_THRESHOLD_VARIANT"] = variant

    if frequency == "WEEKLY":
        frame = frame.sort_values(["economic_exposure_family_id", "date"]).reset_index(drop=True)
        frame["FAST_RS_CHANGE_4W"] = frame.groupby("economic_exposure_family_id", sort=False)["FAST_RS"].diff(4)
        frame["SLOW_RS_CHANGE_4W"] = frame.groupby("economic_exposure_family_id", sort=False)["SLOW_RS"].diff(4)
        weekly_reference = frame.copy()
    else:
        if weekly_reference is None:
            weekly_reference = build_management_features(research, members, policy, "WEEKLY", variant)
        frame = frame.sort_values(["economic_exposure_family_id", "date"]).reset_index(drop=True)
        frame["FAST_RS_CHANGE_4W"] = _weekly_reference_change(frame, weekly_reference, "FAST_RS", "FAST_RS_CHANGE_4W")
        frame["SLOW_RS_CHANGE_4W"] = _weekly_reference_change(frame, weekly_reference, "SLOW_RS", "SLOW_RS_CHANGE_4W")

    params = _state_parameters(policy, variant)
    weekly_for_threshold = frame if frequency == "WEEKLY" else weekly_reference
    threshold = _expanding_prior_quantile_by_family(
        weekly_for_threshold,
        "RS_63",
        params["extension_quantile"],
        int(policy["features"]["extension_minimum_prior_weekly_observations"]),
    )
    if frequency == "WEEKLY":
        frame = frame.merge(
            threshold.rename(columns={"extension_threshold": "RS63_EXTENSION_THRESHOLD_PRIOR"}),
            on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one",
        )
    else:
        threshold = threshold.rename(columns={"extension_threshold": "RS63_EXTENSION_THRESHOLD_PRIOR"})
        frame["RS63_EXTENSION_THRESHOLD_PRIOR"] = _asof_family_field(frame, threshold, "RS63_EXTENSION_THRESHOLD_PRIOR")
    frame = _assign_states(frame, params)
    frame["WARNING"] = WARNING
    return frame.sort_values(["date", "economic_exposure_family_id"]).reset_index(drop=True)


def build_regime_state_history(policy: dict[str, Any], monthly_dates: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    source = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A3R2_REGIME_STATE_HISTORY.parquet")
    source["date"] = pd.to_datetime(source["date"])
    weekly = source.loc[source["pool_id"].eq("INDUSTRY_PLUS_THEME")].sort_values("date").reset_index(drop=True)
    if "warning" in weekly.columns:
        weekly = weekly.rename(columns={"warning": "A3R2_SOURCE_WARNING"})
    weekly["REGIME_SCORE"] = (
        weekly["global_trend_regime"].eq("ABOVE_200").astype(int)
        + weekly["dispersion_regime"].eq("HIGH").astype(int)
        + weekly["breadth_regime"].eq("MEDIUM").astype(int)
        + weekly["rotation_intensity_regime"].eq("HIGH").astype(int)
        + weekly["us_technology_dominance"].eq("NOT_DOMINANT").astype(int)
        - weekly["volatility_regime"].eq("HIGH").astype(int)
    )
    weekly["PRIOR_8W_MAX_SCORE"] = weekly["REGIME_SCORE"].shift(1).rolling(8, min_periods=1).max()
    hostile = weekly["REGIME_SCORE"].le(0) | (
        weekly["global_trend_regime"].eq("BELOW_OR_EQUAL_200") & weekly["volatility_regime"].eq("HIGH")
    )
    deteriorating = weekly["PRIOR_8W_MAX_SCORE"].ge(4) & weekly["REGIME_SCORE"].le(weekly["PRIOR_8W_MAX_SCORE"] - 2)
    mature = weekly["PRIOR_8W_MAX_SCORE"].ge(4) & weekly["REGIME_SCORE"].eq(weekly["PRIOR_8W_MAX_SCORE"] - 1)
    strong = weekly["REGIME_SCORE"].ge(4)
    weekly["REGIME_STATE"] = np.select(
        [hostile, deteriorating, mature, strong],
        ["HOSTILE", "DETERIORATING", "MATURE", "STRONG"],
        default="POSITIVE",
    )
    prior_score = weekly["REGIME_SCORE"].shift(1)
    prior_trailing_max = weekly["REGIME_SCORE"].shift(1).rolling(8, min_periods=1).max()
    weekly["REGIME_PEAK_DETECTED"] = prior_score.eq(prior_trailing_max) & weekly["REGIME_SCORE"].le(prior_score - 1)
    weekly["REGIME_PEAK_DATE"] = weekly["date"].shift(1).where(weekly["REGIME_PEAK_DETECTED"])
    weekly["REGIME_PEAK_OR_MATURITY_FLAG"] = np.select(
        [weekly["REGIME_PEAK_DETECTED"], weekly["REGIME_STATE"].eq("MATURE")],
        ["PEAK_DETECTED", "MATURE"], default="NONE",
    )
    weekly["WARNING"] = WARNING

    monthly_base = pd.DataFrame({"date": pd.DatetimeIndex(monthly_dates).sort_values()})
    weekly_for_asof = weekly.copy()
    weekly_for_asof["REGIME_SOURCE_DATE"] = weekly_for_asof["date"]
    monthly = pd.merge_asof(
        monthly_base,
        weekly_for_asof.sort_values("date"),
        on="date",
        direction="backward",
        allow_exact_matches=True,
    )
    monthly["MANAGEMENT_FREQUENCY"] = "MONTHLY_ONLY"
    weekly["MANAGEMENT_FREQUENCY"] = "WEEKLY"
    return weekly, monthly


def load_a4b_data() -> A4BData:
    policy = read_policy()
    research = a3p.load_research_data()
    members = _context_members(research)
    weekly = build_management_features(research, members, policy, "WEEKLY", "PRIMARY")
    monthly = build_management_features(research, members, policy, "MONTHLY_ONLY", "PRIMARY", weekly_reference=weekly)
    weekly_regime, monthly_regime = build_regime_state_history(policy, pd.DatetimeIndex(monthly["date"].unique()))
    cash = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A2_CASH_SERIES.parquet")
    cash["date"] = pd.to_datetime(cash["date"])
    cash = cash.set_index("date").reindex(research.calendar)
    cash_index = cash["cash_index"].where(cash["data_valid"].fillna(False) | cash["cash_index"].notna())
    # A2 cash has one preserved unavailable observation (2000-07-14).  It is
    # left invalid rather than filled; the next valid cash index embeds the
    # evidenced accrual across the gap.  Modern A4B windows have full coverage.
    if cash_index.loc[pd.Timestamp(policy["windows"]["POST_2020_START"]):].isna().any():
        missing = int(cash_index.loc[pd.Timestamp(policy["windows"]["POST_2020_START"]):].isna().sum())
        raise AssertionError(f"Actual GBP cash index has {missing} missing modern official sessions")
    metadata = research.metadata.loc[research.metadata["economic_exposure_family_id"].isin(members)].copy()
    return A4BData(policy, research, members, metadata, weekly, monthly, weekly_regime, monthly_regime, cash_index.astype(float))


def filter_features(
    frame: pd.DataFrame,
    *,
    excluded_families: set[str] | None = None,
    maturity_scope: str = "DYNAMIC_POINT_IN_TIME",
) -> pd.DataFrame:
    result = frame.copy()
    excluded = excluded_families or set()
    if excluded:
        result = result.loc[~result["economic_exposure_family_id"].isin(excluded)]
    if maturity_scope == "MATURE_ONLY":
        result = result.loc[result["RESEARCH_MATURITY"].eq("MATURE")]
    elif maturity_scope == "MATURE_PLUS_DEVELOPING":
        result = result.loc[result["RESEARCH_MATURITY"].isin(["MATURE", "DEVELOPING"])]
    elif maturity_scope != "DYNAMIC_POINT_IN_TIME":
        raise ValueError(maturity_scope)
    return result


def monthly_leaders(
    monthly_features: pd.DataFrame,
    *,
    excluded_families: set[str] | None = None,
    maturity_scope: str = "DYNAMIC_POINT_IN_TIME",
) -> pd.DataFrame:
    source = filter_features(monthly_features, excluded_families=excluded_families, maturity_scope=maturity_scope)
    rows = []
    for date, group in source.groupby("date", sort=True):
        valid = group.loc[group["SLOW_RS"].notna()].sort_values(
            ["SLOW_RS", "economic_exposure_family_id"], ascending=[False, True]
        )
        rows.append({
            "monthly_review_date": pd.Timestamp(date),
            "incumbent_family": valid.iloc[0]["economic_exposure_family_id"] if len(valid) else "",
            "incumbent_slow_score": float(valid.iloc[0]["SLOW_RS"]) if len(valid) else np.nan,
            "eligible_family_count": int(len(valid)),
        })
    return pd.DataFrame(rows).sort_values("monthly_review_date").reset_index(drop=True)


def attach_incumbent(management_dates: pd.DatetimeIndex, leaders: pd.DataFrame) -> pd.DataFrame:
    left = pd.DataFrame({"date": pd.DatetimeIndex(management_dates).sort_values()})
    right = leaders.sort_values("monthly_review_date")
    result = pd.merge_asof(left, right, left_on="date", right_on="monthly_review_date", direction="backward")
    result["incumbent_family"] = result["incumbent_family"].fillna("")
    return result


def weight_dict_equal(left: dict[str, float], right: dict[str, float], tolerance: float = 1e-12) -> bool:
    keys = set(left) | set(right)
    return all(abs(float(left.get(key, 0.0)) - float(right.get(key, 0.0))) <= tolerance for key in keys)


class TargetPlanner:
    """Plans next-session target events and tracks true implementation entries."""

    def __init__(self, data: A4BData, module_id: str, management_frequency: str):
        self.data = data
        self.module_id = module_id
        self.management_frequency = management_frequency
        self.calendar = data.research.calendar
        self.date_position = {pd.Timestamp(date): index for index, date in enumerate(self.calendar)}
        self.wealth = data.research.wealth
        self.segment = data.research.segment
        self.current_target: dict[str, float] = {}
        self.entry_position: dict[str, int] = {}
        self.entry_level: dict[str, float] = {}
        self.entry_segment: dict[str, Any] = {}
        self.started = False
        self.targets: dict[pd.Timestamp, dict[str, float]] = {}
        self.events: list[dict[str, Any]] = []
        self.cancelled: list[dict[str, Any]] = []

    def position_stats(self, family: str, review_date: pd.Timestamp) -> dict[str, float]:
        if family not in self.entry_position or review_date not in self.date_position:
            return {"position_return": np.nan, "mfe": np.nan, "mae": np.nan, "giveback_ratio": np.nan}
        start = self.entry_position[family]
        end = self.date_position[pd.Timestamp(review_date)]
        if end < start:
            raise AssertionError("Review precedes actual entry")
        levels = self.wealth.iloc[start:end + 1][family].astype(float)
        segments = self.segment.iloc[start:end + 1][family]
        valid = levels.notna() & segments.eq(self.entry_segment[family])
        observed = levels.loc[valid]
        if observed.empty:
            return {"position_return": np.nan, "mfe": np.nan, "mae": np.nan, "giveback_ratio": np.nan}
        base = float(self.entry_level[family])
        returns = observed / base - 1.0
        current = float(returns.iloc[-1])
        mfe = float(max(0.0, returns.max()))
        mae = float(min(0.0, returns.min()))
        giveback = (mfe - current) / mfe if mfe > 0 else np.nan
        return {"position_return": current, "mfe": mfe, "mae": mae, "giveback_ratio": giveback}

    def submit(self, review_date: pd.Timestamp, target: dict[str, float], reason: str) -> dict[str, Any]:
        review_date = pd.Timestamp(review_date)
        clean = {str(family): float(weight) for family, weight in target.items() if float(weight) > 1e-12}
        if any(weight < -1e-12 for weight in clean.values()) or sum(clean.values()) > 1.0 + 1e-12:
            raise AssertionError("Risky target must be long-only and no greater than 100%")
        if len(clean) > 2:
            raise AssertionError("A4B permits at most two risky holdings")
        self.targets[review_date] = clean
        if self.started and weight_dict_equal(clean, self.current_target):
            return {"execution_status": "NO_TARGET_CHANGE", "execution_date": pd.NaT, "execution_lag_xlon_sessions": np.nan}
        review_position = self.date_position[review_date]
        execution_position = None
        union = set(self.current_target) | set(clean)
        for lag in range(1, 4):
            candidate = review_position + lag
            if candidate >= len(self.calendar):
                break
            valid = bool(pd.notna(self.data.cash_index.iloc[candidate]))
            for family in union:
                valid &= bool(pd.notna(self.wealth.iloc[candidate][family]))
                if family in self.current_target and family in self.entry_segment:
                    valid &= self.segment.iloc[candidate][family] == self.entry_segment[family]
            if valid:
                execution_position = candidate
                break
        if execution_position is None:
            status = "CANCELLED_PANEL_END_NO_EXECUTION_SESSION" if review_position + 1 >= len(self.calendar) else "CANCELLED_NO_COMMON_VALID_ENDPOINT_WITHIN_3_XLON_SESSIONS"
            row = {
                "module_id": self.module_id,
                "review_date": review_date,
                "execution_date": pd.NaT,
                "execution_position": np.nan,
                "execution_lag_xlon_sessions": np.nan,
                "execution_status": status,
                "target": clean,
                "reason": reason,
            }
            self.cancelled.append(row)
            return row
        event = {
            "module_id": self.module_id,
            "review_date": review_date,
            "execution_date": pd.Timestamp(self.calendar[execution_position]),
            "execution_position": int(execution_position),
            "execution_lag_xlon_sessions": int(execution_position - review_position),
            "execution_status": "PLANNED",
            "target": clean,
            "reason": reason,
        }
        old_members = set(self.current_target)
        for family in old_members - set(clean):
            self.entry_position.pop(family, None)
            self.entry_level.pop(family, None)
            self.entry_segment.pop(family, None)
        for family in set(clean) - old_members:
            self.entry_position[family] = int(execution_position)
            self.entry_level[family] = float(self.wealth.iloc[execution_position][family])
            self.entry_segment[family] = self.segment.iloc[execution_position][family]
        self.current_target = dict(clean)
        self.events.append(event)
        self.started = True
        return event


def simulate_planned_portfolio(
    plan: PlannedPortfolio,
    data: A4BData,
    *,
    friction_bps: float | None = None,
    fixed_fee_gbp: float | None = None,
    sleeve_size_gbp: float | None = None,
    non_gbp_families: set[str] | None = None,
    fx_rate: float | None = None,
) -> A4BSimulation:
    policy = data.policy["costs"]
    friction_bps = float(policy["canonical_one_way_friction_bps"] if friction_bps is None else friction_bps)
    fixed_fee_gbp = float(policy["ii_fixed_fee_gbp_per_risky_trade_leg"] if fixed_fee_gbp is None else fixed_fee_gbp)
    sleeve_size_gbp = float(policy["canonical_sleeve_size_gbp"] if sleeve_size_gbp is None else sleeve_size_gbp)
    fx_rate = float(policy["non_gbp_fx_rate"] if fx_rate is None else fx_rate)
    non_gbp = non_gbp_families or set()
    events_by_position = {int(event["execution_position"]): event for event in plan.events}
    if not events_by_position:
        empty_curve = pd.DataFrame(columns=["date", "portfolio_value"])
        return A4BSimulation(plan.module_id, empty_curve, pd.DataFrame(), pd.DataFrame(), plan.decisions, plan.actions)

    calendar = data.research.calendar
    wealth = data.research.wealth
    segment = data.research.segment
    cash_index = data.cash_index
    first_position = min(events_by_position)
    risky_units: dict[str, float] = {}
    risky_entry_segments: dict[str, Any] = {}
    cash_units = 0.0
    last_observed_position: int | None = None
    last_post_value: float | None = None
    curve_rows: list[dict[str, Any]] = []
    trade_rows: list[dict[str, Any]] = []
    cumulative_cash_return_contribution = 0.0
    cumulative_transaction_cost = 0.0
    last_risky_values: dict[str, float] = {}

    for position in range(first_position, len(calendar)):
        date = pd.Timestamp(calendar[position])
        event = events_by_position.get(position)
        valid = pd.notna(cash_index.iloc[position])
        for family in risky_units:
            valid &= pd.notna(wealth.iloc[position][family])
            valid &= segment.iloc[position][family] == risky_entry_segments[family]
        if not valid and event is None:
            continue
        if not valid and event is not None:
            raise AssertionError("Planned execution reached an invalid endpoint")

        if last_observed_position is None:
            pre_value = 1.0
            pre_cash_value = 1.0
            pre_risky_values: dict[str, float] = {}
            gross_return = 0.0
            cash_return_contribution = 0.0
            family_pnl = {}
        else:
            pre_cash_value = float(cash_units * cash_index.iloc[position])
            pre_risky_values = {
                family: float(units * wealth.iloc[position][family]) for family, units in risky_units.items()
            }
            pre_value = float(pre_cash_value + sum(pre_risky_values.values()))
            if last_post_value is None or last_post_value <= 0:
                raise AssertionError("Invalid prior portfolio value")
            gross_return = pre_value / last_post_value - 1.0
            previous_cash_value = float(cash_units * cash_index.iloc[last_observed_position])
            cash_return_contribution = (pre_cash_value - previous_cash_value) / last_post_value
            cumulative_cash_return_contribution += cash_return_contribution
            family_pnl = {
                family: float(pre_risky_values.get(family, 0.0) - last_risky_values.get(family, 0.0))
                for family in sorted(set(pre_risky_values) | set(last_risky_values))
            }

        transaction_cost = 0.0
        transaction_cost_rate = 0.0
        traded_notional = 0.0
        trade_legs = 0
        if event is not None:
            target = event["target"]
            current_weights = {family: value / pre_value for family, value in pre_risky_values.items()} if pre_value > 0 else {}
            keys = sorted(set(current_weights) | set(target))
            deltas = {family: float(target.get(family, 0.0) - current_weights.get(family, 0.0)) for family in keys}
            traded_notional = float(sum(abs(delta) for delta in deltas.values()))
            trade_legs = int(sum(abs(delta) > 1e-12 for delta in deltas.values()))
            fx_notional = float(sum(abs(delta) for family, delta in deltas.items() if family in non_gbp))
            variable = pre_value * (traded_notional * friction_bps / 10_000.0 + fx_notional * fx_rate)
            fixed = trade_legs * fixed_fee_gbp / sleeve_size_gbp
            transaction_cost = min(pre_value, variable + fixed)
            transaction_cost_rate = transaction_cost / pre_value if pre_value > 0 else 0.0
            cumulative_transaction_cost += transaction_cost
            post_value = pre_value - transaction_cost
            risky_units = {
                family: post_value * float(weight) / float(wealth.iloc[position][family])
                for family, weight in target.items()
            }
            risky_entry_segments = {family: segment.iloc[position][family] for family in target}
            cash_weight = max(0.0, 1.0 - float(sum(target.values())))
            cash_units = post_value * cash_weight / float(cash_index.iloc[position])
            trade_rows.append({
                "module_id": plan.module_id,
                "review_date": event["review_date"],
                "execution_date": date,
                "execution_lag_xlon_sessions": event["execution_lag_xlon_sessions"],
                "same_close_execution": False,
                "execution_status": "EXECUTED",
                "target_weights_json": json.dumps(target, sort_keys=True),
                "selected_families": ";".join(sorted(target)),
                "selected_count": len(target),
                "target_risky_weight": float(sum(target.values())),
                "traded_notional_fraction": traded_notional,
                "trade_legs": trade_legs,
                "transaction_cost_rate": transaction_cost_rate,
                "transaction_cost_value": transaction_cost,
                "pre_trade_portfolio_value": pre_value,
                "reason": event["reason"],
            })
        else:
            post_value = pre_value

        risky_values = {family: float(units * wealth.iloc[position][family]) for family, units in risky_units.items()}
        cash_value = float(cash_units * cash_index.iloc[position])
        observed_value = float(cash_value + sum(risky_values.values()))
        if event is not None:
            observed_value = post_value
            scale = post_value / max(cash_value + sum(risky_values.values()), 1e-30)
            cash_value *= scale
            risky_values = {family: value * scale for family, value in risky_values.items()}
        invested_value = float(sum(risky_values.values()))
        weights = {family: value / observed_value for family, value in risky_values.items()} if observed_value > 0 else {}
        net_return = 0.0 if last_post_value is None else observed_value / last_post_value - 1.0
        curve_rows.append({
            "module_id": plan.module_id,
            "date": date,
            "portfolio_value": observed_value,
            "gross_return_before_cost": gross_return,
            "net_return": net_return,
            "cash_return_contribution": cash_return_contribution,
            "cumulative_cash_return_contribution": cumulative_cash_return_contribution,
            "transaction_cost_return": -transaction_cost_rate,
            "cumulative_transaction_cost_value": cumulative_transaction_cost,
            "invested_fraction": invested_value / observed_value if observed_value > 0 else np.nan,
            "cash_fraction": cash_value / observed_value if observed_value > 0 else np.nan,
            "cash_value": cash_value,
            "holding_count": len(risky_values),
            "concentration_hhi": float(sum(weight * weight for weight in weights.values())),
            "holdings": ";".join(sorted(risky_values)),
            "weights_json": json.dumps(weights, sort_keys=True),
            "family_values_json": json.dumps(risky_values, sort_keys=True),
            "family_market_pnl_json": json.dumps(family_pnl, sort_keys=True),
            "execution_event": event is not None,
            "decision_review_date": event["review_date"] if event is not None else pd.NaT,
            "data_valid": True,
        })
        last_observed_position = position
        last_post_value = observed_value
        last_risky_values = dict(risky_values)

    for cancelled in plan.cancelled_events:
        trade_rows.append({
            "module_id": plan.module_id,
            "review_date": cancelled["review_date"],
            "execution_date": pd.NaT,
            "execution_lag_xlon_sessions": np.nan,
            "same_close_execution": False,
            "execution_status": cancelled["execution_status"],
            "target_weights_json": json.dumps(cancelled["target"], sort_keys=True),
            "selected_families": ";".join(sorted(cancelled["target"])),
            "selected_count": len(cancelled["target"]),
            "target_risky_weight": float(sum(cancelled["target"].values())),
            "traded_notional_fraction": np.nan,
            "trade_legs": 0,
            "transaction_cost_rate": 0.0,
            "transaction_cost_value": 0.0,
            "pre_trade_portfolio_value": np.nan,
            "reason": cancelled["reason"],
        })
    target_rows = [
        {
            "module_id": plan.module_id,
            "review_date": date,
            "target_weights_json": json.dumps(target, sort_keys=True),
            "target_members": ";".join(sorted(target)),
            "target_count": len(target),
            "target_risky_weight": float(sum(target.values())),
            "target_cash_weight": float(1.0 - sum(target.values())),
        }
        for date, target in sorted(plan.targets.items())
    ]
    return A4BSimulation(
        plan.module_id,
        pd.DataFrame(curve_rows),
        pd.DataFrame(trade_rows).sort_values(["review_date", "execution_date"], na_position="last").reset_index(drop=True),
        pd.DataFrame(target_rows),
        plan.decisions.copy(),
        plan.actions.copy(),
    )


def _max_consecutive_true(values: Iterable[bool]) -> int:
    best = current = 0
    for value in values:
        current = current + 1 if bool(value) else 0
        best = max(best, current)
    return best


def _loss_clusters(monthly_returns: pd.Series) -> tuple[int, int, float]:
    clusters: list[list[float]] = []
    current: list[float] = []
    for value in monthly_returns:
        if value < 0:
            current.append(float(value))
        elif current:
            clusters.append(current)
            current = []
    if current:
        clusters.append(current)
    multi = [cluster for cluster in clusters if len(cluster) >= 2]
    worst = min((float(np.prod([1.0 + value for value in cluster]) - 1.0) for cluster in multi), default=np.nan)
    return len(multi), max((len(cluster) for cluster in clusters), default=0), worst


def enhanced_performance_metrics(
    simulation: A4BSimulation,
    *,
    start: pd.Timestamp | None,
    end: pd.Timestamp | None,
) -> dict[str, Any]:
    curve = simulation.curve.copy()
    if start is not None:
        curve = curve.loc[curve["date"].ge(pd.Timestamp(start))]
    if end is not None:
        curve = curve.loc[curve["date"].le(pd.Timestamp(end))]
    curve = curve.drop_duplicates("date").sort_values("date")
    if len(curve) < 2:
        return {"observation_count": len(curve), "cagr": np.nan}
    value = curve.set_index("date")["portfolio_value"].astype(float)
    returns = value.pct_change(fill_method=None).dropna()
    years = max((value.index[-1] - value.index[0]).days / 365.2425, 1 / 365.2425)
    cagr = float((value.iloc[-1] / value.iloc[0]) ** (1 / years) - 1)
    gross_daily = curve.set_index("date")["gross_return_before_cost"].astype(float)
    gross_value = (1.0 + gross_daily.fillna(0.0)).cumprod()
    gross_cagr = float((gross_value.iloc[-1] / gross_value.iloc[0]) ** (1 / years) - 1)
    normalised = value / value.iloc[0]
    drawdown = normalised / normalised.cummax() - 1.0
    max_drawdown = float(drawdown.min())
    annual_vol = float(returns.std(ddof=1) * math.sqrt(252)) if len(returns) > 1 else np.nan
    downside = returns.loc[returns < 0]
    downside_vol = float(downside.std(ddof=1) * math.sqrt(252)) if len(downside) > 1 else np.nan
    ulcer = float(np.sqrt(np.mean(np.square(drawdown))))
    month_end = value.groupby([value.index.year, value.index.month]).last()
    month_returns = month_end.pct_change(fill_method=None).dropna()
    rolling3 = (1 + month_returns).rolling(3, min_periods=3).apply(np.prod, raw=True) - 1
    rolling6 = (1 + month_returns).rolling(6, min_periods=6).apply(np.prod, raw=True) - 1
    rolling12 = (1 + month_returns).rolling(12, min_periods=12).apply(np.prod, raw=True) - 1
    new_high = normalised.ge(normalised.cummax() - 1e-12)
    high_dates = normalised.index[new_high]
    high_gaps = pd.Series(high_dates).diff().dt.days.dropna()
    underwater = drawdown.lt(-1e-12)
    max_underwater_days = 0
    start_underwater: pd.Timestamp | None = None
    for date, flag in underwater.items():
        if flag and start_underwater is None:
            start_underwater = pd.Timestamp(date)
        elif not flag and start_underwater is not None:
            max_underwater_days = max(max_underwater_days, (pd.Timestamp(date) - start_underwater).days)
            start_underwater = None
    if start_underwater is not None:
        max_underwater_days = max(max_underwater_days, (pd.Timestamp(drawdown.index[-1]) - start_underwater).days)
    x = np.arange(len(value), dtype=float)
    y = np.log(value.to_numpy(float))
    slope, intercept = np.polyfit(x, y, 1)
    fitted = intercept + slope * x
    residual = y - fitted
    ss_total = float(np.square(y - y.mean()).sum())
    r2 = 1.0 - float(np.square(residual).sum()) / ss_total if ss_total > 0 else np.nan
    trend_se = float(np.sqrt(np.square(residual).sum() / max(len(y) - 2, 1)))
    clusters, max_losing_run, worst_cluster = _loss_clusters(month_returns)
    trades = simulation.trades.loc[simulation.trades.get("execution_status", pd.Series(dtype=str)).eq("EXECUTED")].copy()
    if start is not None and not trades.empty:
        trades = trades.loc[pd.to_datetime(trades["execution_date"]).ge(pd.Timestamp(start))]
    if end is not None and not trades.empty:
        trades = trades.loc[pd.to_datetime(trades["execution_date"]).le(pd.Timestamp(end))]
    curve_window = curve.loc[curve["date"].between(value.index[0], value.index[-1])]
    return {
        "first_observation_date": value.index[0],
        "last_observation_date": value.index[-1],
        "observation_count": int(len(value)),
        "calendar_years": years,
        "gross_cagr": gross_cagr,
        "net_cagr": cagr,
        "annualised_volatility": annual_vol,
        "downside_volatility": downside_vol,
        "sharpe_zero_cash_hurdle": cagr / annual_vol if annual_vol and annual_vol > 0 else np.nan,
        "sortino_zero_cash_hurdle": cagr / downside_vol if downside_vol and downside_vol > 0 else np.nan,
        "maximum_drawdown": max_drawdown,
        "average_drawdown": float(drawdown.mean()),
        "calmar_mar": cagr / abs(max_drawdown) if max_drawdown < 0 else np.nan,
        "ulcer_index": ulcer,
        "ulcer_performance_index": cagr / ulcer if ulcer > 0 else np.nan,
        "worst_month": float(month_returns.min()) if len(month_returns) else np.nan,
        "worst_quarter": float(rolling3.min()) if len(rolling3.dropna()) else np.nan,
        "worst_rolling_six_months": float(rolling6.min()) if len(rolling6.dropna()) else np.nan,
        "maximum_time_underwater_calendar_days": int(max_underwater_days),
        "percentage_months_in_drawdown": float(underwater.groupby([underwater.index.year, underwater.index.month]).last().mean()),
        "percentage_positive_months": float(month_returns.gt(0).mean()) if len(month_returns) else np.nan,
        "percentage_positive_rolling_12m": float(rolling12.dropna().gt(0).mean()) if len(rolling12.dropna()) else np.nan,
        "maximum_consecutive_losing_months": int(max_losing_run),
        "loss_cluster_count_ge_2_months": int(clusters),
        "worst_loss_cluster_return": worst_cluster,
        "annual_turnover_traded_notional": float(trades["traded_notional_fraction"].fillna(0).sum() / years) if len(trades) else 0.0,
        "trade_legs": int(trades["trade_legs"].fillna(0).sum()) if len(trades) else 0,
        "executed_rebalances": int(len(trades)),
        "average_cash_weight": float(curve_window["cash_fraction"].mean()),
        "percentage_time_with_cash": float(curve_window["cash_fraction"].gt(1e-12).mean()),
        "cash_return_contribution": float(curve_window["cash_return_contribution"].sum()),
        "total_transaction_cost_value": float(trades["transaction_cost_value"].fillna(0).sum()) if len(trades) else 0.0,
        "log_equity_curve_r2": r2,
        "log_equity_trend_standard_error": trend_se,
        "frequency_of_new_equity_highs": float(new_high.mean()),
        "median_calendar_days_between_equity_highs": float(high_gaps.median()) if len(high_gaps) else np.nan,
        "percentage_days_underwater": float(underwater.mean()),
        "warning": WARNING,
    }


def normalise_curve_at_start(curve: pd.DataFrame, start: pd.Timestamp) -> pd.Series:
    source = curve.loc[curve["date"].ge(pd.Timestamp(start))].set_index("date")["portfolio_value"].astype(float)
    if source.empty:
        return source
    return source / source.iloc[0]


def window_definitions(policy: dict[str, Any]) -> dict[str, tuple[pd.Timestamp | None, pd.Timestamp | None]]:
    windows = policy["windows"]
    return {
        "LATEST_5Y": (pd.Timestamp(windows["LATEST_5Y_START"]), pd.Timestamp(windows["CUTOFF"])),
        "LATEST_3Y": (pd.Timestamp(windows["LATEST_3Y_START"]), pd.Timestamp(windows["CUTOFF"])),
        "POST_2020": (pd.Timestamp(windows["POST_2020_START"]), pd.Timestamp(windows["CUTOFF"])),
        "PRE_2020": (None, pd.Timestamp(windows["PRE_2020_END"])),
        "FULL_HISTORY": (None, pd.Timestamp(windows["CUTOFF"])),
    }
