"""Causal portfolio primitives for UKACTIVE-A4E-SIPP.

The module reuses the immutable A4D/A2R2 data and execution engines.  It adds
only the preregistered signal-neighbour audit, exact CASH1 controls, bounded
turnover variants, global/cash core, fixed core/satellite blends and no-
leverage portfolio-volatility scaling.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

import ukactive_a4b_core as a4b
import ukactive_a4d_core as a4d


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
STAGE_ROOT = PROGRAMME_ROOT / "UKACTIVE-A4E-SIPP"
PREREGISTRATION_PATH = STAGE_ROOT / "UKACTIVE_A4E_SIPP_PREREGISTRATION.json"
WARNING = "E2 DEVELOPMENTAL; HISTORICAL UK RETAIL/SIPP ELIGIBILITY IS NOT FULLY RECONSTRUCTED"
HORIZONS = [21, 42, 63, 126, 252]
SIGNAL_WEIGHTS = {
    "M2_BASE": [0.10, 0.15, 0.25, 0.30, 0.20],
    "M2_N1": [0.10, 0.15, 0.25, 0.25, 0.25],
    "M2_N2": [0.10, 0.10, 0.25, 0.30, 0.25],
    "M2_N3": [0.15, 0.15, 0.25, 0.25, 0.20],
    "M1_EQUAL_CONTROL": [0.20, 0.20, 0.20, 0.20, 0.20],
}
SIGNAL_COLUMN = {
    "M2_BASE": "M2_INTERMEDIATE_5H",
    "M1_EQUAL_CONTROL": "M1_EQUAL_5H",
    "M2_N1": "A4E_M2_N1",
    "M2_N2": "A4E_M2_N2",
    "M2_N3": "A4E_M2_N3",
}


@dataclass
class StrategyResult:
    strategy_id: str
    simulation: a4b.A4BSimulation
    targets: dict[pd.Timestamp, dict[str, float]]
    records: pd.DataFrame
    metadata: dict[str, Any]

    @property
    def target_records(self) -> pd.DataFrame:
        """Compatibility alias for immutable A4D attribution helpers."""
        return self.records


def read_preregistration() -> dict[str, Any]:
    return json.loads(PREREGISTRATION_PATH.read_text(encoding="utf-8"))


def load_data() -> a4d.A4DData:
    data = a4d.load_data()
    frame = data.daily_features
    for signal, weights in SIGNAL_WEIGHTS.items():
        column = SIGNAL_COLUMN[signal]
        if column in frame.columns:
            continue
        frame[column] = sum(float(weight) * frame[f"RANK_RS_{horizon}"] for horizon, weight in zip(HORIZONS, weights))
    return data


def monthly_features(data: a4d.A4DData) -> pd.DataFrame:
    return a4d.sample_features(data, "MONTHLY")


def _selection_frame(
    data: a4d.A4DData,
    source: pd.DataFrame,
    signal_id: str,
    excluded_families: set[str] | None = None,
) -> pd.DataFrame:
    column = SIGNAL_COLUMN[signal_id]
    frame = source.loc[source[column].notna()].copy()
    if excluded_families:
        frame = frame.loc[~frame["economic_exposure_family_id"].isin(excluded_families)]
    return frame.sort_values([column, "economic_exposure_family_id"], ascending=[False, True]).reset_index(drop=True)


def rotation_targets(
    data: a4d.A4DData,
    signal_id: str,
    breadth: int,
    *,
    cash1: bool,
    excluded_families: set[str] | None = None,
) -> tuple[dict[pd.Timestamp, dict[str, float]], pd.DataFrame]:
    """Construct A4D-equivalent monthly equal-weight targets.

    The denominator remains the number selected before CASH1, exactly matching
    A4D.  A failed slot therefore becomes cash rather than being redistributed.
    """
    features = monthly_features(data)
    start = pd.Timestamp(data.policy["windows"]["COMMON_CAUSAL_CHAIN_START"])
    features = features.loc[features["date"].ge(start)]
    column = SIGNAL_COLUMN[signal_id]
    targets: dict[pd.Timestamp, dict[str, float]] = {}
    rows: list[dict[str, Any]] = []
    for date, source in features.groupby("date", sort=True):
        frame = _selection_frame(data, source, signal_id, excluded_families)
        if len(frame) < 3:
            continue
        selected = frame.head(min(int(breadth), len(frame))).copy()
        selected["selection_rank"] = np.arange(1, len(selected) + 1)
        slot = 1.0 / len(selected)
        target: dict[str, float] = {}
        for row in selected.itertuples(index=False):
            if not cash1 or float(row.ABOVE_CASH_252) == 1.0:
                target[str(row.economic_exposure_family_id)] = slot
        targets[pd.Timestamp(date)] = target
        rows.append(
            {
                "review_date": pd.Timestamp(date),
                "signal_id": signal_id,
                "signal_column": column,
                "breadth": int(breadth),
                "frequency": "MONTHLY",
                "cash_architecture": "CASH_1_INDIVIDUAL_ABOVE_CASH_252" if cash1 else "CASH_0_ALWAYS_INVESTED",
                "eligible_family_count": int(len(frame)),
                "selected_family_count_before_cash": int(len(selected)),
                "selected_risky_family_count": int(len(target)),
                "selected_families_rank_order": ";".join(selected["economic_exposure_family_id"]),
                "selected_scores": ";".join(f"{value:.12g}" for value in selected[column]),
                "target_weights_json": json.dumps(target, sort_keys=True),
                "target_risky_weight": float(sum(target.values())),
                "target_cash_weight": float(1.0 - sum(target.values())),
                "warning": WARNING,
            }
        )
    return targets, pd.DataFrame(rows)


def _resolve_events(
    data: a4d.A4DData,
    module_id: str,
    targets: dict[pd.Timestamp, dict[str, float]],
    records: pd.DataFrame,
    *,
    force_every_review: bool,
) -> a4b.PlannedPortfolio:
    if not force_every_review:
        plan, _ = a4d.plan_targets(data, module_id, "MONTHLY", targets, records)
        return plan
    calendar = data.base.research.calendar
    position = {pd.Timestamp(date): i for i, date in enumerate(calendar)}
    wealth = data.base.research.wealth
    segment = data.base.research.segment
    cash = data.base.cash_index
    events: list[dict[str, Any]] = []
    cancelled: list[dict[str, Any]] = []
    current: dict[str, float] = {}
    entry_segment: dict[str, Any] = {}
    for review_date, requested in sorted(targets.items()):
        review_date = pd.Timestamp(review_date)
        clean = {str(k): float(v) for k, v in requested.items() if float(v) > 1e-12}
        if sum(clean.values()) > 1.0 + 1e-12:
            raise AssertionError("Target exceeds 100%")
        union = set(current) | set(clean)
        execution_position: int | None = None
        for lag in range(1, 4):
            candidate = position[review_date] + lag
            if candidate >= len(calendar):
                break
            valid = bool(pd.notna(cash.iloc[candidate]))
            for family in union:
                valid &= bool(pd.notna(wealth.iloc[candidate][family]))
                if family in current and family in entry_segment:
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
                    "reason": "A4E_FORCED_MONTHLY_REBALANCE",
                }
            )
            continue
        event = {
            "module_id": module_id,
            "review_date": review_date,
            "execution_date": pd.Timestamp(calendar[execution_position]),
            "execution_position": int(execution_position),
            "execution_lag_xlon_sessions": int(execution_position - position[review_date]),
            "execution_status": "PLANNED",
            "target": clean,
            "reason": "A4E_FORCED_MONTHLY_REBALANCE",
        }
        events.append(event)
        current = dict(clean)
        entry_segment = {family: segment.iloc[execution_position][family] for family in clean}
    return a4b.PlannedPortfolio(module_id, "MONTHLY", targets, events, cancelled, records.copy(), pd.DataFrame())


def simulate_targets(
    data: a4d.A4DData,
    strategy_id: str,
    targets: dict[pd.Timestamp, dict[str, float]],
    records: pd.DataFrame,
    *,
    cost_scenario: str = "BASE",
    force_every_review: bool = False,
) -> StrategyResult:
    prereg = read_preregistration()
    costs = prereg["costs"][cost_scenario]
    plan = _resolve_events(data, strategy_id, targets, records, force_every_review=force_every_review)
    simulation = a4b.simulate_planned_portfolio(
        plan,
        data.base,
        friction_bps=float(costs["one_way_bps"]),
        fixed_fee_gbp=float(costs["fixed_fee_per_leg_gbp"]),
        sleeve_size_gbp=float(costs["notional_gbp"]),
        non_gbp_families=set(),
        fx_rate=float(data.policy["costs"]["non_gbp_fx_rate"]),
    )
    return StrategyResult(strategy_id, simulation, targets, records, {"cost_scenario": cost_scenario, "force_every_review": force_every_review})


def simulate_rotation(
    data: a4d.A4DData,
    signal_id: str,
    breadth: int,
    cash1: bool,
    *,
    cost_scenario: str = "BASE",
    excluded_families: set[str] | None = None,
) -> StrategyResult:
    targets, records = rotation_targets(data, signal_id, breadth, cash1=cash1, excluded_families=excluded_families)
    cash_id = "CASH1" if cash1 else "CASH0"
    exclusions = "NONE" if not excluded_families else "+".join(sorted(excluded_families))
    strategy_id = f"{signal_id}|TOP{breadth}|MONTHLY|{cash_id}|EQUAL|{cost_scenario}|EXCL={exclusions}"
    return simulate_targets(data, strategy_id, targets, records, cost_scenario=cost_scenario)


def hysteresis_targets(data: a4d.A4DData) -> tuple[dict[pd.Timestamp, dict[str, float]], pd.DataFrame]:
    features = monthly_features(data)
    start = pd.Timestamp(data.policy["windows"]["COMMON_CAUSAL_CHAIN_START"])
    features = features.loc[features["date"].ge(start)]
    holdings: list[str] = []
    targets: dict[pd.Timestamp, dict[str, float]] = {}
    rows: list[dict[str, Any]] = []
    for date, source in features.groupby("date", sort=True):
        frame = _selection_frame(data, source, "M2_BASE")
        if len(frame) < 3:
            continue
        frame["rank"] = np.arange(1, len(frame) + 1)
        lookup = frame.set_index("economic_exposure_family_id")
        retained = [
            family for family in holdings
            if family in lookup.index and int(lookup.loc[family, "rank"]) <= 9 and float(lookup.loc[family, "ABOVE_CASH_252"]) == 1.0
        ]
        entrants = [
            family for family in frame.loc[frame["rank"].le(7) & frame["ABOVE_CASH_252"].eq(1.0), "economic_exposure_family_id"]
            if family not in retained
        ]
        holdings = (retained + entrants)[:7]
        target = {family: 1.0 / 7.0 for family in holdings}
        targets[pd.Timestamp(date)] = target
        rows.append(
            {
                "review_date": pd.Timestamp(date),
                "variant_id": "R1_RANK_HYSTERESIS",
                "selected_families_rank_order": ";".join(holdings),
                "target_weights_json": json.dumps(target, sort_keys=True),
                "target_risky_weight": float(sum(target.values())),
                "target_cash_weight": float(1.0 - sum(target.values())),
                "retained_count": len(retained),
                "entrant_count": len([family for family in holdings if family in entrants]),
                "warning": WARNING,
            }
        )
    return targets, pd.DataFrame(rows)


def weekly_exit_targets(data: a4d.A4DData) -> tuple[dict[pd.Timestamp, dict[str, float]], pd.DataFrame]:
    monthly, _ = rotation_targets(data, "M2_BASE", 7, cash1=True)
    weekly_dates = set(a4d.schedule_dates(data.base.research.calendar, "WEEKLY"))
    all_dates = sorted(set(monthly) | {date for date in weekly_dates if date >= min(monthly)})
    feature = data.daily_features.set_index(["date", "economic_exposure_family_id"])
    current: dict[str, float] = {}
    targets: dict[pd.Timestamp, dict[str, float]] = {}
    rows: list[dict[str, Any]] = []
    for date in all_dates:
        date = pd.Timestamp(date)
        if date in monthly:
            current = dict(monthly[date])
            reason = "MONTHLY_RECONSTRUCTION"
        else:
            failed = []
            for family in list(current):
                key = (date, family)
                valid = key in feature.index and float(feature.loc[key, "ABOVE_CASH_252"]) == 1.0
                if not valid:
                    failed.append(family)
            current = {family: weight for family, weight in current.items() if family not in failed}
            reason = "WEEKLY_CASH1_EXIT_ONLY" if failed else "WEEKLY_NO_CHANGE"
        targets[date] = dict(current)
        rows.append(
            {
                "review_date": date,
                "variant_id": "R2_WEEKLY_EXIT_ONLY",
                "reason": reason,
                "selected_families_rank_order": ";".join(current),
                "target_weights_json": json.dumps(current, sort_keys=True),
                "target_risky_weight": float(sum(current.values())),
                "target_cash_weight": float(1.0 - sum(current.values())),
                "warning": WARNING,
            }
        )
    return targets, pd.DataFrame(rows)


def core_targets(data: a4d.A4DData, core_id: str, *, start: pd.Timestamp | None = None) -> tuple[dict[pd.Timestamp, dict[str, float]], pd.DataFrame]:
    start = pd.Timestamp(start or data.policy["windows"]["COMMON_CAUSAL_CHAIN_START"])
    dates = [date for date in a4d.schedule_dates(data.base.research.calendar, "MONTHLY") if date >= start]
    global_return = data.base.research.matrices.cumulative_returns[252]["GLOBAL_DEVELOPED_WORLD"]
    targets: dict[pd.Timestamp, dict[str, float]] = {}
    rows = []
    for date in dates:
        if core_id == "CORE_0_GLOBAL":
            target = {"GLOBAL_DEVELOPED_WORLD": 1.0}
            qualified = True
        elif core_id == "CORE_1_GLOBAL_ABSOLUTE_MOMENTUM":
            qualified = bool(pd.notna(global_return.loc[date]) and pd.notna(data.cash_return_252.loc[date]) and global_return.loc[date] > data.cash_return_252.loc[date])
            target = {"GLOBAL_DEVELOPED_WORLD": 1.0} if qualified else {}
        else:
            raise ValueError(core_id)
        targets[pd.Timestamp(date)] = target
        rows.append({"review_date": pd.Timestamp(date), "core_id": core_id, "qualified": qualified, "target_weights_json": json.dumps(target), "target_risky_weight": float(sum(target.values())), "target_cash_weight": float(1.0 - sum(target.values())), "warning": WARNING})
    return targets, pd.DataFrame(rows)


def static_global_targets(data: a4d.A4DData, global_weight: float) -> tuple[dict[pd.Timestamp, dict[str, float]], pd.DataFrame]:
    dates = [date for date in a4d.schedule_dates(data.base.research.calendar, "MONTHLY") if date >= pd.Timestamp(data.policy["windows"]["COMMON_CAUSAL_CHAIN_START"])]
    targets = {pd.Timestamp(date): ({"GLOBAL_DEVELOPED_WORLD": float(global_weight)} if global_weight > 0 else {}) for date in dates}
    rows = pd.DataFrame([{"review_date": date, "global_weight": global_weight, "target_weights_json": json.dumps(target), "target_risky_weight": sum(target.values()), "target_cash_weight": 1.0 - sum(target.values()), "warning": WARNING} for date, target in targets.items()])
    return targets, rows


def scale_target_map(targets: dict[pd.Timestamp, dict[str, float]], scale: float) -> dict[pd.Timestamp, dict[str, float]]:
    return {date: {family: float(weight) * float(scale) for family, weight in target.items()} for date, target in targets.items()}


def combine_target_maps(
    rotation_targets_map: dict[pd.Timestamp, dict[str, float]],
    core_targets_map: dict[pd.Timestamp, dict[str, float]],
    rotation_weight: float,
) -> tuple[dict[pd.Timestamp, dict[str, float]], pd.DataFrame]:
    dates = sorted(set(rotation_targets_map) & set(core_targets_map))
    targets: dict[pd.Timestamp, dict[str, float]] = {}
    rows = []
    for date in dates:
        target: dict[str, float] = {}
        for family, weight in rotation_targets_map[date].items():
            target[family] = target.get(family, 0.0) + float(rotation_weight) * float(weight)
        for family, weight in core_targets_map[date].items():
            target[family] = target.get(family, 0.0) + (1.0 - float(rotation_weight)) * float(weight)
        target = {family: weight for family, weight in target.items() if weight > 1e-12}
        targets[date] = target
        rotation_risk = sum(rotation_targets_map[date].values()) * float(rotation_weight)
        core_risk = sum(core_targets_map[date].values()) * (1.0 - float(rotation_weight))
        rows.append({"review_date": date, "rotation_strategic_weight": rotation_weight, "core_strategic_weight": 1.0 - rotation_weight, "rotation_risky_target": rotation_risk, "core_risky_target": core_risk, "target_weights_json": json.dumps(target, sort_keys=True), "target_risky_weight": sum(target.values()), "target_cash_weight": 1.0 - sum(target.values()), "warning": WARNING})
    return targets, pd.DataFrame(rows)


def volatility_scaled_targets(
    base_result: StrategyResult,
    target_volatility: float,
) -> tuple[dict[pd.Timestamp, dict[str, float]], pd.DataFrame]:
    returns = base_result.simulation.curve.set_index("date")["net_return"].astype(float)
    targets: dict[pd.Timestamp, dict[str, float]] = {}
    rows = []
    for date, target in sorted(base_result.targets.items()):
        history = returns.loc[returns.index <= pd.Timestamp(date)].tail(63)
        if len(history) < 63 or float(history.std(ddof=1)) <= 0:
            realised = np.nan
            exposure = 1.0
            status = "NO_SCALE_UNTIL_63_VALID_PRIOR_OBSERVATIONS"
        else:
            realised = float(history.std(ddof=1) * math.sqrt(252))
            exposure = min(1.0, float(target_volatility) / realised)
            status = "SCALED" if exposure < 1.0 - 1e-12 else "UNCAPPED_BELOW_TARGET"
        scaled = {family: weight * exposure for family, weight in target.items()}
        targets[pd.Timestamp(date)] = scaled
        rows.append({"review_date": pd.Timestamp(date), "target_volatility": target_volatility, "trailing_realised_volatility": realised, "exposure_multiplier": exposure, "status": status, "target_weights_json": json.dumps(scaled, sort_keys=True), "target_risky_weight": sum(scaled.values()), "target_cash_weight": 1.0 - sum(scaled.values()), "warning": WARNING})
    return targets, pd.DataFrame(rows)


def _monthly_returns(value: pd.Series) -> pd.Series:
    month = value.groupby([value.index.year, value.index.month]).last()
    return month.pct_change(fill_method=None).dropna()


def metric_pack(simulation: a4b.A4BSimulation, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, Any]:
    base = a4b.enhanced_performance_metrics(simulation, start=start, end=end)
    curve = simulation.curve.loc[simulation.curve["date"].between(start, end)].drop_duplicates("date").sort_values("date")
    if len(curve) < 2:
        return base
    value = curve.set_index("date")["portfolio_value"].astype(float)
    normalised = value / value.iloc[0]
    drawdown = normalised / normalised.cummax() - 1.0
    monthly = _monthly_returns(value)
    rolling12 = (1.0 + monthly).rolling(12, min_periods=12).apply(np.prod, raw=True) - 1.0
    rolling24 = (1.0 + monthly).rolling(24, min_periods=24).apply(np.prod, raw=True) - 1.0
    rolling36 = (1.0 + monthly).rolling(36, min_periods=36).apply(np.prod, raw=True) - 1.0
    threshold = float(drawdown.quantile(0.05))
    base.update(
        {
            "terminal_wealth_per_100k": float(100000.0 * normalised.iloc[-1]),
            "conditional_drawdown_at_risk_95": float(drawdown.loc[drawdown.le(threshold)].mean()),
            "worst_rolling_12_months": float(rolling12.min()) if rolling12.notna().any() else np.nan,
            "worst_rolling_36_months": float(rolling36.min()) if rolling36.notna().any() else np.nan,
            "percentage_positive_rolling_24m": float(rolling24.dropna().gt(0).mean()) if rolling24.notna().any() else np.nan,
            "percentage_positive_rolling_36m": float(rolling36.dropna().gt(0).mean()) if rolling36.notna().any() else np.nan,
            "average_equity_exposure": float(curve["invested_fraction"].mean()),
            "average_cash_exposure": float(curve["cash_fraction"].mean()),
            "percentage_time_partially_invested": float(
                (
                    curve["cash_fraction"].gt(1e-10)
                    & curve["cash_fraction"].lt(1.0 - 1e-10)
                ).mean()
            ),
            "percentage_time_completely_cash": float(curve["cash_fraction"].ge(1.0 - 1e-10).mean()),
        }
    )
    return base


def primary_windows(data: a4d.A4DData) -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
    cutoff = pd.Timestamp(data.policy["windows"]["CUTOFF"])
    start = pd.Timestamp(data.policy["windows"]["COMMON_CAUSAL_CHAIN_START"])
    return {
        "FULL_HISTORY": (start, cutoff),
        "PRE_2020": (start, pd.Timestamp("2019-12-31")),
        "POST_2020": (pd.Timestamp("2020-01-02"), cutoff),
        "LATEST_5Y": (pd.Timestamp("2021-09-01"), cutoff),
        "LATEST_3Y": (pd.Timestamp("2023-08-21"), cutoff),
    }


def evaluation_rows(
    data: a4d.A4DData,
    result: StrategyResult,
    global_sim: a4b.A4BSimulation,
    pool_sim: a4b.A4BSimulation,
) -> pd.DataFrame:
    rows = []
    for window_id, (start, end) in primary_windows(data).items():
        first = max(start, pd.Timestamp(result.simulation.curve["date"].min()), pd.Timestamp(global_sim.curve["date"].min()), pd.Timestamp(pool_sim.curve["date"].min()))
        last = min(end, pd.Timestamp(result.simulation.curve["date"].max()), pd.Timestamp(global_sim.curve["date"].max()), pd.Timestamp(pool_sim.curve["date"].max()))
        metrics = metric_pack(result.simulation, first, last)
        global_metrics = metric_pack(global_sim, first, last)
        pool_metrics = metric_pack(pool_sim, first, last)
        row = {"strategy_id": result.strategy_id, "window_id": window_id, "cost_scenario": result.metadata.get("cost_scenario", "BASE"), "first_date": first, "last_date": last}
        row.update(metrics)
        row["global_cagr"] = global_metrics.get("net_cagr", np.nan)
        row["pool_cagr"] = pool_metrics.get("net_cagr", np.nan)
        row["excess_vs_global"] = row.get("net_cagr", np.nan) - row["global_cagr"]
        row["excess_vs_pool"] = row.get("net_cagr", np.nan) - row["pool_cagr"]
        row["cost_drag_cagr"] = row.get("gross_cagr", np.nan) - row.get("net_cagr", np.nan)
        row["average_rotation_exposure"] = result.metadata.get("average_rotation_exposure", np.nan)
        row["warning"] = WARNING
        rows.append(row)
    return pd.DataFrame(rows)


def excluded_year_metrics(simulation: a4b.A4BSimulation, excluded_years: set[int]) -> dict[str, float]:
    curve = simulation.curve.drop_duplicates("date").sort_values("date")
    returns = curve.set_index("date")["net_return"].astype(float)
    returns = returns.loc[~returns.index.year.isin(excluded_years)]
    if len(returns) < 2:
        return {"net_cagr": np.nan, "maximum_drawdown": np.nan, "terminal_wealth_per_100k": np.nan}
    value = (1.0 + returns).cumprod()
    years = len(returns) / 252.0
    cagr = float(value.iloc[-1] ** (1.0 / years) - 1.0)
    drawdown = value / value.cummax() - 1.0
    return {"net_cagr": cagr, "maximum_drawdown": float(drawdown.min()), "terminal_wealth_per_100k": float(100000.0 * value.iloc[-1]), "observation_count": int(len(returns))}


def holding_spell_ledger(result: StrategyResult) -> pd.DataFrame:
    curve = result.simulation.curve.sort_values("date").reset_index(drop=True)
    open_spells: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    last_weights: dict[str, float] = {}
    last_review: pd.Timestamp | None = None
    for row in curve.itertuples(index=False):
        date = pd.Timestamp(row.date)
        weights = json.loads(row.weights_json) if row.weights_json else {}
        pnl = json.loads(row.family_market_pnl_json) if row.family_market_pnl_json else {}
        review = pd.Timestamp(row.decision_review_date) if pd.notna(row.decision_review_date) else last_review
        entered = set(weights) - set(last_weights)
        exited = set(last_weights) - set(weights)
        for family in entered:
            open_spells[family] = {"family": family, "entry_date": date, "entry_review_date": review, "gross_market_pnl_return_units": 0.0, "days_held": 0}
        for family, value in pnl.items():
            if family in open_spells:
                open_spells[family]["gross_market_pnl_return_units"] += float(value)
        for family in set(weights):
            if family in open_spells:
                open_spells[family]["days_held"] = (date - open_spells[family]["entry_date"]).days
        for family in exited:
            spell = open_spells.pop(family, {"family": family, "entry_date": pd.NaT, "entry_review_date": pd.NaT, "gross_market_pnl_return_units": 0.0, "days_held": 0})
            spell["exit_date"] = date
            spell["exit_review_date"] = review
            rows.append(spell)
        last_weights = weights
        if pd.notna(row.decision_review_date):
            last_review = pd.Timestamp(row.decision_review_date)
    end = pd.Timestamp(curve["date"].max()) if len(curve) else pd.NaT
    for family, spell in open_spells.items():
        spell["exit_date"] = pd.NaT
        spell["exit_review_date"] = pd.NaT
        spell["days_held"] = (end - spell["entry_date"]).days
        rows.append(spell)
    ledger = pd.DataFrame(rows)
    if ledger.empty:
        return ledger
    ledger.insert(0, "holding_spell_id", [f"SPELL-{i:04d}" for i in range(1, len(ledger) + 1)])
    total_positive = ledger["gross_market_pnl_return_units"].clip(lower=0).sum()
    ledger["share_of_positive_spell_pnl"] = ledger["gross_market_pnl_return_units"].clip(lower=0) / total_positive if total_positive > 0 else np.nan
    ledger["winner_class"] = np.where(ledger["gross_market_pnl_return_units"] > 0, "WINNER", "FALSE_OR_LOSING_LEADER")
    ledger["warning"] = WARNING
    return ledger.sort_values("gross_market_pnl_return_units", ascending=False).reset_index(drop=True)


def targets_without_spells(
    targets: dict[pd.Timestamp, dict[str, float]],
    spells: pd.DataFrame,
) -> dict[pd.Timestamp, dict[str, float]]:
    result = {date: dict(target) for date, target in targets.items()}
    for spell in spells.itertuples(index=False):
        entry = pd.Timestamp(spell.entry_review_date) if pd.notna(spell.entry_review_date) else pd.Timestamp(spell.entry_date)
        exit_date = pd.Timestamp(spell.exit_review_date) if pd.notna(spell.exit_review_date) else pd.Timestamp.max
        for date in list(result):
            if entry <= pd.Timestamp(date) < exit_date:
                result[date].pop(spell.family, None)
    return result


def random_control_targets(
    data: a4d.A4DData,
    baseline_targets: dict[pd.Timestamp, dict[str, float]],
    rng: np.random.Generator,
    *,
    mode: str,
    breadth: int = 7,
) -> tuple[dict[pd.Timestamp, dict[str, float]], pd.DataFrame]:
    monthly = monthly_features(data).set_index("date")
    targets: dict[pd.Timestamp, dict[str, float]] = {}
    rows = []
    for date, baseline in sorted(baseline_targets.items()):
        source = monthly.loc[date]
        frame = _selection_frame(data, source.reset_index(), "M2_BASE")
        if mode == "RANDOM_SELECTION_SAME_RISKY_COUNT":
            qualified = frame.loc[frame["ABOVE_CASH_252"].eq(1.0), "economic_exposure_family_id"].to_numpy(object)
            count = min(len(baseline), len(qualified))
            chosen = list(rng.choice(qualified, size=count, replace=False)) if count else []
            target = {str(family): 1.0 / breadth for family in chosen}
        elif mode == "MONTHLY_RANK_SHUFFLE":
            order = rng.permutation(len(frame))
            selected = frame.iloc[order[: min(breadth, len(frame))]]
            slot = 1.0 / len(selected)
            target = {str(row.economic_exposure_family_id): slot for row in selected.itertuples(index=False) if float(row.ABOVE_CASH_252) == 1.0}
        else:
            raise ValueError(mode)
        targets[pd.Timestamp(date)] = target
        rows.append({"review_date": date, "mode": mode, "target_weights_json": json.dumps(target, sort_keys=True), "target_risky_weight": sum(target.values()), "target_cash_weight": 1.0 - sum(target.values()), "warning": WARNING})
    return targets, pd.DataFrame(rows)


def vectorised_randomisation_control(
    data: a4d.A4DData,
    baseline_targets: dict[pd.Timestamp, dict[str, float]],
    *,
    mode: str,
    seed: int,
    simulation_count: int,
    breadth: int = 7,
    friction_bps: float = 20.0,
    fixed_fee_gbp: float = 3.99,
    sleeve_size_gbp: float = 250000.0,
) -> dict[str, Any]:
    """Monthly randomisation diagnostic with deterministic vectorised accounting.

    The signal universe is contemporaneous.  Trades occur on the first next
    XLON session.  A selected slot whose accepted implementation endpoint is
    unavailable at either interval boundary is conservatively allocated to
    cash for that interval; no return is filled or spliced.  Candidate and
    random paths use the same diagnostic engine, so the percentile comparison
    is internally matched.  This is a falsification diagnostic, not the
    canonical portfolio score.
    """
    dates = sorted(baseline_targets)
    calendar = data.base.research.calendar
    position = {pd.Timestamp(date): i for i, date in enumerate(calendar)}
    execution_dates = []
    decision_dates = []
    for date in dates:
        pos = position[pd.Timestamp(date)] + 1
        if pos < len(calendar) and pd.Timestamp(calendar[pos]) <= pd.Timestamp(data.policy["windows"]["CUTOFF"]):
            decision_dates.append(pd.Timestamp(date))
            execution_dates.append(pd.Timestamp(calendar[pos]))
    if len(execution_dates) < 3:
        raise AssertionError("Insufficient randomisation intervals")
    members = list(data.members)
    member_index = {family: i for i, family in enumerate(members)}
    feature = monthly_features(data).set_index("date")
    wealth = data.base.research.wealth[members]
    segment = data.base.research.segment[members]
    cash = data.base.cash_index
    interval_count = len(execution_dates) - 1
    asset_factors = np.full((interval_count, len(members)), np.nan, dtype=float)
    cash_factors = np.ones(interval_count, dtype=float)
    for k in range(interval_count):
        left, right = execution_dates[k], execution_dates[k + 1]
        left_value = wealth.loc[left].to_numpy(float)
        right_value = wealth.loc[right].to_numpy(float)
        same = segment.loc[left].to_numpy(object) == segment.loc[right].to_numpy(object)
        valid = np.isfinite(left_value) & np.isfinite(right_value) & same
        asset_factors[k, valid] = right_value[valid] / left_value[valid]
        cash_factors[k] = float(cash.loc[right] / cash.loc[left])

    rng = np.random.default_rng(int(seed))
    target_cube = np.zeros((interval_count, int(simulation_count), len(members)), dtype=float)
    baseline_cube = np.zeros((interval_count, 1, len(members)), dtype=float)
    invalid_slot_count = 0
    for k in range(interval_count):
        date = decision_dates[k]
        source = feature.loc[date]
        frame = _selection_frame(data, source.reset_index(), "M2_BASE")
        eligible = frame["economic_exposure_family_id"].astype(str).tolist()
        qualifying = frame.loc[frame["ABOVE_CASH_252"].eq(1.0), "economic_exposure_family_id"].astype(str).tolist()
        valid_interval = np.isfinite(asset_factors[k])
        baseline = baseline_targets.get(date, {})
        for family, weight in baseline.items():
            idx = member_index[family]
            if valid_interval[idx]:
                baseline_cube[k, 0, idx] = float(weight)
            else:
                invalid_slot_count += 1
        if mode == "RANDOM_SELECTION_SAME_RISKY_COUNT":
            pool = np.asarray(qualifying, dtype=object)
            count = min(len(baseline), len(pool))
            if count:
                scores = rng.random((simulation_count, len(pool)))
                selected_positions = np.argpartition(scores, count - 1, axis=1)[:, :count]
                for path in range(simulation_count):
                    for family in pool[selected_positions[path]]:
                        idx = member_index[str(family)]
                        if valid_interval[idx]:
                            target_cube[k, path, idx] = 1.0 / breadth
                        else:
                            invalid_slot_count += 1
        elif mode == "MONTHLY_RANK_SHUFFLE":
            pool = np.asarray(eligible, dtype=object)
            count = min(breadth, len(pool))
            scores = rng.random((simulation_count, len(pool)))
            selected_positions = np.argpartition(scores, count - 1, axis=1)[:, :count]
            above = {family: family in qualifying for family in eligible}
            for path in range(simulation_count):
                for family in pool[selected_positions[path]]:
                    family = str(family)
                    idx = member_index[family]
                    if above[family] and valid_interval[idx]:
                        target_cube[k, path, idx] = 1.0 / count
                    elif above[family] and not valid_interval[idx]:
                        invalid_slot_count += 1
        else:
            raise ValueError(mode)

    def run(targets: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        paths = targets.shape[1]
        nav = np.ones(paths, dtype=float)
        high = np.ones(paths, dtype=float)
        maximum_drawdown = np.zeros(paths, dtype=float)
        current_weights = np.zeros((paths, len(members)), dtype=float)
        monthly_nav = np.ones((interval_count + 1, paths), dtype=float)
        total_turnover = np.zeros(paths, dtype=float)
        for k in range(interval_count):
            target = targets[k]
            delta = target - current_weights
            turnover = np.abs(delta).sum(axis=1)
            legs = (np.abs(delta) > 1e-12).sum(axis=1)
            cost = turnover * float(friction_bps) / 10000.0 + legs * float(fixed_fee_gbp) / float(sleeve_size_gbp)
            nav *= np.maximum(0.0, 1.0 - cost)
            total_turnover += turnover
            cash_weight = np.maximum(0.0, 1.0 - target.sum(axis=1))
            factor_matrix = np.where(np.isfinite(asset_factors[k]), asset_factors[k], 1.0)
            risky_end = target * factor_matrix[None, :]
            cash_end = cash_weight * cash_factors[k]
            portfolio_factor = risky_end.sum(axis=1) + cash_end
            nav *= portfolio_factor
            current_weights = np.divide(risky_end, portfolio_factor[:, None], out=np.zeros_like(risky_end), where=portfolio_factor[:, None] > 0)
            high = np.maximum(high, nav)
            maximum_drawdown = np.minimum(maximum_drawdown, nav / high - 1.0)
            monthly_nav[k + 1] = nav
        years = interval_count / 12.0
        cagr = np.power(nav, 1.0 / years) - 1.0
        return cagr, maximum_drawdown, total_turnover / years

    random_cagr, random_mdd, random_turnover = run(target_cube)
    baseline_cagr, baseline_mdd, baseline_turnover = run(baseline_cube)
    observed_cagr = float(baseline_cagr[0])
    observed_mdd = float(baseline_mdd[0])
    return {
        "control_id": mode,
        "seed": int(seed),
        "simulation_count": int(simulation_count),
        "diagnostic_first_execution_date": execution_dates[0],
        "diagnostic_last_execution_date": execution_dates[-1],
        "candidate_diagnostic_cagr": observed_cagr,
        "candidate_diagnostic_maximum_drawdown": observed_mdd,
        "candidate_diagnostic_turnover": float(baseline_turnover[0]),
        "candidate_cagr_percentile": float(np.mean(random_cagr <= observed_cagr)),
        "candidate_drawdown_percentile_less_severe": float(np.mean(random_mdd <= observed_mdd)),
        "random_cagr_mean": float(np.mean(random_cagr)),
        "random_cagr_median": float(np.median(random_cagr)),
        "random_cagr_5pct": float(np.quantile(random_cagr, 0.05)),
        "random_cagr_95pct": float(np.quantile(random_cagr, 0.95)),
        "random_mdd_mean": float(np.mean(random_mdd)),
        "random_mdd_median": float(np.median(random_mdd)),
        "random_turnover_mean": float(np.mean(random_turnover)),
        "invalid_selected_slots_allocated_to_cash": int(invalid_slot_count),
        "method": "VECTORIZED_MONTHLY_NEXT_XLON_SESSION; INVALID_INTERVAL_ENDPOINT_SLOT_TO_CASH; NO_FILLED_RETURN",
        "warning": WARNING,
    }


def immutable_hashes(paths: Iterable[Path]) -> dict[str, str]:
    import hashlib

    result = {}
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        result[str(path)] = digest
    return result
