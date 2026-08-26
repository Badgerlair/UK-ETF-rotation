"""Frozen operational primitives for UKACTIVE-A5C-SIPP.

This module adds no research hypothesis.  It reuses the immutable A4E/A4F
engines, enforces the 2026-08-21 evidence boundary, constructs only the frozen
M2 TOP7 CASH0 portfolios and applies the two declared Interactive Investor fee
schedules.  Prospective records are written by a separate append-only runner;
this module never creates an order or a post-cutoff signal.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

import ukactive_a4b_core as a4b
import ukactive_a4e_sipp_core as a4e
import ukactive_a4f_sipp_core as a4f


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
STAGE_ROOT = PROGRAMME_ROOT / "UKACTIVE-A5C-SIPP"
FROZEN_SPEC_PATH = STAGE_ROOT / "UKACTIVE_A5C_SIPP_FROZEN_SPEC.json"
AUTHORITATIVE_CUTOFF = pd.Timestamp("2026-08-21")
COMMON_START = pd.Timestamp("2017-03-01")
GLOBAL_FAMILY = "GLOBAL_DEVELOPED_WORLD"
M2_WEIGHTS = {"RS21": 0.10, "RS42": 0.15, "RS63": 0.25, "RS126": 0.30, "RS252": 0.20}
M2_BREADTH = 7
CURRENT_PORTFOLIO_GBP = 563_000.0
CANONICAL_PORTFOLIO_GBP = 250_000.0
ONE_WAY_FRICTION_BPS = 20.0

PLAN_SPECS: dict[str, dict[str, float]] = {
    "GLOBAL_75_DEFENSIVE_25": {"global": 0.75, "m2": 0.00, "cash": 0.25},
    "GLOBAL_65_M2_10_DEFENSIVE_25": {"global": 0.65, "m2": 0.10, "cash": 0.25},
    "GLOBAL_60_M2_15_DEFENSIVE_25": {"global": 0.60, "m2": 0.15, "cash": 0.25},
    "GLOBAL_50_M2_25_DEFENSIVE_25": {"global": 0.50, "m2": 0.25, "cash": 0.25},
    "M2_100_DIAGNOSTIC": {"global": 0.00, "m2": 1.00, "cash": 0.00},
    "GLOBAL_100": {"global": 1.00, "m2": 0.00, "cash": 0.00},
}

II_PLANS: dict[str, dict[str, float | int]] = {
    "II_PLUS": {"fee_per_paid_leg_gbp": 3.99, "monthly_free_credits": 1, "monthly_subscription_gbp": 14.99},
    "II_PREMIUM": {"fee_per_paid_leg_gbp": 2.99, "monthly_free_credits": 2, "monthly_subscription_gbp": 39.99},
}


@dataclass
class PlanResult:
    strategy_id: str
    ii_plan: str
    notional_gbp: float
    target_map: dict[pd.Timestamp, dict[str, float]]
    simulation: a4b.A4BSimulation
    fee_audit: pd.DataFrame
    subscription_treatment: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frozen_spec() -> dict[str, Any]:
    return json.loads(FROZEN_SPEC_PATH.read_text(encoding="utf-8"))


def load_data() -> a4f.a4d.A4DData:
    spec = frozen_spec()
    if spec["model_development_status"] != "M2_HISTORICAL_MODEL_DEVELOPMENT_CLOSED":
        raise AssertionError("M2 model development is not closed")
    if spec["m2"]["relative_strength_weights"] != M2_WEIGHTS:
        raise AssertionError("Frozen M2 weights differ from the A5C specification")
    if int(spec["m2"]["breadth"]) != M2_BREADTH:
        raise AssertionError("Frozen M2 breadth differs from TOP7")
    data = a4f.load_data()
    maxima = {
        "calendar": pd.Timestamp(data.base.research.calendar.max()),
        "daily_features": pd.Timestamp(data.daily_features["date"].max()),
        "cash": pd.Timestamp(data.base.cash_index.dropna().index.max()),
    }
    if any(value > AUTHORITATIVE_CUTOFF for value in maxima.values()):
        raise AssertionError(f"A5C post-cutoff data detected: {maxima}")
    return data


def frozen_rotation_targets(data: a4f.a4d.A4DData) -> tuple[dict[pd.Timestamp, dict[str, float]], pd.DataFrame]:
    targets, records = a4e.rotation_targets(data, "M2_BASE", M2_BREADTH, cash1=False)
    targets = {
        pd.Timestamp(date): {str(family): float(weight) for family, weight in target.items()}
        for date, target in targets.items()
        # Keep the 2017-02-28 review because it executes on the canonical
        # 2017-03-01 portfolio-chain start.  Filtering on review >= chain start
        # would silently lose the first executable month.
        if pd.Timestamp(date) <= AUTHORITATIVE_CUTOFF
    }
    records = records.loc[records["review_date"].le(AUTHORITATIVE_CUTOFF)].copy()
    if not targets:
        raise AssertionError("Frozen M2 target map is empty")
    if max(targets) > AUTHORITATIVE_CUTOFF:
        raise AssertionError("Post-cutoff M2 target detected")
    for target in targets.values():
        # TOP7 is a cap.  The early point-in-time history may contain only
        # three to six eligible families; the accepted engine weights the
        # available set equally rather than inventing or backfilling members.
        if not 3 <= len(target) <= M2_BREADTH or not math.isclose(sum(target.values()), 1.0, abs_tol=1e-12):
            raise AssertionError("M2 target is not an equally invested point-in-time TOP7 set")
        if any(not math.isclose(weight, 1.0 / len(target), abs_tol=1e-12) for weight in target.values()):
            raise AssertionError("M2 target weights are not equal")
    return targets, records


def blend_targets(
    rotation: Mapping[pd.Timestamp, Mapping[str, float]],
    global_weight: float,
    m2_weight: float,
) -> dict[pd.Timestamp, dict[str, float]]:
    if global_weight < 0 or m2_weight < 0 or global_weight + m2_weight > 1.0 + 1e-12:
        raise ValueError("Invalid allocation")
    targets: dict[pd.Timestamp, dict[str, float]] = {}
    for date, selected in sorted(rotation.items()):
        target = {str(family): float(weight) * float(m2_weight) for family, weight in selected.items()}
        if global_weight > 1e-12:
            target[GLOBAL_FAMILY] = float(global_weight)
        targets[pd.Timestamp(date)] = target
    return targets


def target_maps(data: a4f.a4d.A4DData) -> dict[str, dict[pd.Timestamp, dict[str, float]]]:
    rotation, _ = frozen_rotation_targets(data)
    return {
        strategy_id: blend_targets(rotation, spec["global"], spec["m2"])
        for strategy_id, spec in PLAN_SPECS.items()
    }


def _records(strategy_id: str, targets: Mapping[pd.Timestamp, Mapping[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "review_date": pd.Timestamp(date),
            "strategy_id": strategy_id,
            "target_weights_json": json.dumps(dict(target), sort_keys=True),
            "target_risky_weight": float(sum(target.values())),
            "target_cash_weight": float(1.0 - sum(target.values())),
            "warning": "E2_DEVELOPMENTAL; A5C_COST_RESTATEMENT_ONLY",
        }
        for date, target in sorted(targets.items())
    )


def _gross_simulation(
    data: a4f.a4d.A4DData,
    strategy_id: str,
    targets: Mapping[pd.Timestamp, Mapping[str, float]],
) -> a4b.A4BSimulation:
    clean = {pd.Timestamp(date): dict(target) for date, target in targets.items() if pd.Timestamp(date) <= AUTHORITATIVE_CUTOFF}
    # Standalone M2 must reproduce the canonical target-change event stream.
    # Fixed whole-SIPP mixes are strategically rebalanced every month.
    force_every_review = strategy_id != "M2_100_DIAGNOSTIC"
    plan = a4e._resolve_events(
        data,
        strategy_id,
        clean,
        _records(strategy_id, clean),
        force_every_review=force_every_review,
    )
    result = a4b.simulate_planned_portfolio(
        plan,
        data.base,
        friction_bps=0.0,
        fixed_fee_gbp=0.0,
        sleeve_size_gbp=CURRENT_PORTFOLIO_GBP,
        non_gbp_families=set(),
        fx_rate=0.0,
    )
    if result.curve.empty:
        raise AssertionError(f"Empty gross simulation: {strategy_id}")
    return result


def _charge_curve(
    gross: a4b.A4BSimulation,
    strategy_id: str,
    ii_plan: str,
    notional_gbp: float,
    *,
    include_full_subscription: bool,
) -> tuple[a4b.A4BSimulation, pd.DataFrame]:
    if ii_plan not in II_PLANS:
        raise ValueError(ii_plan)
    plan = II_PLANS[ii_plan]
    fee = float(plan["fee_per_paid_leg_gbp"])
    monthly_credit = int(plan["monthly_free_credits"])
    subscription = float(plan["monthly_subscription_gbp"])
    trade_lookup = {
        pd.Timestamp(row.execution_date): row
        for row in gross.trades.loc[gross.trades["execution_status"].eq("EXECUTED")].itertuples(index=False)
    }
    credits_remaining: dict[tuple[int, int], int] = {}
    charged_subscription_months: set[tuple[int, int]] = set()
    nav = 1.0
    prior_nav: float | None = None
    cumulative_cost = 0.0
    curve_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for row in gross.curve.sort_values("date").itertuples(index=False):
        date = pd.Timestamp(row.date)
        pre = nav if prior_nav is None else nav * (1.0 + float(row.gross_return_before_cost))
        month = (date.year, date.month)
        variable_cost = 0.0
        fixed_cost = 0.0
        subscription_cost = 0.0
        trade_legs = 0
        free_legs = 0
        paid_legs = 0
        turnover = 0.0
        m2_leg_count = 0
        core_leg_count = 0
        if date in trade_lookup:
            trade = trade_lookup[date]
            turnover = float(trade.traded_notional_fraction)
            trade_legs = int(trade.trade_legs)
            variable_cost = pre * turnover * ONE_WAY_FRICTION_BPS / 10_000.0
            if month not in credits_remaining:
                credits_remaining[month] = monthly_credit
            free_legs = min(trade_legs, credits_remaining[month])
            credits_remaining[month] -= free_legs
            paid_legs = trade_legs - free_legs
            fixed_cost = paid_legs * fee / float(notional_gbp)
            target = json.loads(str(trade.target_weights_json))
            core_leg_count = 1 if GLOBAL_FAMILY in target and trade_legs > 0 else 0
            m2_leg_count = max(0, trade_legs - core_leg_count)
        if include_full_subscription and month not in charged_subscription_months:
            subscription_cost = subscription / float(notional_gbp)
            charged_subscription_months.add(month)
        total_cost = variable_cost + fixed_cost + subscription_cost
        nav = max(0.0, pre - total_cost)
        cumulative_cost += total_cost
        net_return = 0.0 if prior_nav is None else nav / prior_nav - 1.0
        curve_rows.append(
            {
                "module_id": strategy_id,
                "date": date,
                "portfolio_value": nav,
                "gross_return_before_cost": float(row.gross_return_before_cost),
                "net_return": net_return,
                "cash_return_contribution": float(row.cash_return_contribution),
                "cumulative_cash_return_contribution": float(row.cumulative_cash_return_contribution),
                "transaction_cost_return": -total_cost / pre if pre > 0 else 0.0,
                "cumulative_transaction_cost_value": cumulative_cost,
                "invested_fraction": float(row.invested_fraction),
                "cash_fraction": float(row.cash_fraction),
                "cash_value": float(row.cash_fraction) * nav,
                "holding_count": int(row.holding_count),
                "concentration_hhi": float(row.concentration_hhi),
                "holdings": row.holdings,
                "weights_json": row.weights_json,
                "family_values_json": row.family_values_json,
                "family_market_pnl_json": row.family_market_pnl_json,
                "execution_event": bool(row.execution_event),
                "decision_review_date": row.decision_review_date,
                "data_valid": bool(row.data_valid),
            }
        )
        if date in trade_lookup or subscription_cost:
            audit_rows.append(
                {
                    "strategy_id": strategy_id,
                    "ii_plan": ii_plan,
                    "notional_gbp": float(notional_gbp),
                    "date": date,
                    "trade_legs": trade_legs,
                    "free_trade_legs": free_legs,
                    "paid_trade_legs": paid_legs,
                    "core_leg_count_diagnostic": core_leg_count,
                    "m2_leg_count_diagnostic": m2_leg_count,
                    "traded_notional_fraction": turnover,
                    "market_friction_gbp": variable_cost * float(notional_gbp),
                    "dealing_fee_gbp": fixed_cost * float(notional_gbp),
                    "subscription_fee_gbp": subscription_cost * float(notional_gbp),
                    "total_cost_gbp": total_cost * float(notional_gbp),
                    "credit_assumption": "MONTHLY_CREDITS_RESERVED_FOR_MODEL_TRADES_NO_CARRY",
                }
            )
        prior_nav = nav
    curve = pd.DataFrame(curve_rows)
    fee_audit = pd.DataFrame(audit_rows)
    trades = gross.trades.copy()
    if not trades.empty:
        fee_lookup = fee_audit.loc[fee_audit["trade_legs"].gt(0)].set_index("date")
        trades["free_trade_legs"] = trades["execution_date"].map(fee_lookup["free_trade_legs"])
        trades["paid_trade_legs"] = trades["execution_date"].map(fee_lookup["paid_trade_legs"])
        trades["market_friction_gbp"] = trades["execution_date"].map(fee_lookup["market_friction_gbp"])
        trades["dealing_fee_gbp"] = trades["execution_date"].map(fee_lookup["dealing_fee_gbp"])
        trades["transaction_cost_value"] = (
            trades["market_friction_gbp"].fillna(0.0) + trades["dealing_fee_gbp"].fillna(0.0)
        ) / float(notional_gbp)
        trades["transaction_cost_rate"] = np.where(
            trades["pre_trade_portfolio_value"].astype(float).gt(0.0),
            trades["transaction_cost_value"] / trades["pre_trade_portfolio_value"].astype(float),
            0.0,
        )
    sim = a4b.A4BSimulation(strategy_id, curve, trades, gross.targets, gross.decisions, gross.actions)
    return sim, fee_audit


def simulate_plan(
    data: a4f.a4d.A4DData,
    strategy_id: str,
    targets: Mapping[pd.Timestamp, Mapping[str, float]],
    ii_plan: str,
    notional_gbp: float,
    *,
    include_full_subscription: bool,
) -> PlanResult:
    gross = _gross_simulation(data, strategy_id, targets)
    sim, audit = _charge_curve(
        gross,
        strategy_id,
        ii_plan,
        notional_gbp,
        include_full_subscription=include_full_subscription,
    )
    return PlanResult(
        strategy_id,
        ii_plan,
        float(notional_gbp),
        {pd.Timestamp(date): dict(target) for date, target in targets.items()},
        sim,
        audit,
        "FULL_SUBSCRIPTION_DEDUCTED" if include_full_subscription else "SUBSCRIPTION_REPORTED_SEPARATELY",
    )


def metrics(result: PlanResult, start: pd.Timestamp | str, end: pd.Timestamp | str) -> dict[str, Any]:
    return a4e.metric_pack(result.simulation, pd.Timestamp(start), pd.Timestamp(end))


def monthly_returns(simulation: a4b.A4BSimulation) -> pd.Series:
    curve = simulation.curve.drop_duplicates("date").sort_values("date").copy()
    curve["month"] = curve["date"].dt.to_period("M")
    return curve.groupby("month")["net_return"].apply(lambda values: float((1.0 + values.astype(float)).prod() - 1.0))


def relative_nav(candidate: a4b.A4BSimulation, comparator: a4b.A4BSimulation) -> pd.Series:
    c = candidate.curve.drop_duplicates("date").set_index("date")["portfolio_value"].astype(float)
    b = comparator.curve.drop_duplicates("date").set_index("date")["portfolio_value"].astype(float)
    joined = pd.concat([c.rename("candidate"), b.rename("comparator")], axis=1, join="inner").dropna()
    ratio = (joined["candidate"] / joined["candidate"].iloc[0]) / (joined["comparator"] / joined["comparator"].iloc[0])
    ratio.name = "relative_nav"
    return ratio


def maximum_relative_drawdown(candidate: a4b.A4BSimulation, comparator: a4b.A4BSimulation) -> float:
    ratio = relative_nav(candidate, comparator)
    return float((ratio / ratio.cummax() - 1.0).min())


def longest_relative_underwater_days(candidate: a4b.A4BSimulation, comparator: a4b.A4BSimulation) -> int:
    ratio = relative_nav(candidate, comparator)
    high = ratio.cummax()
    underwater = ratio < high - 1e-12
    longest = 0
    start: pd.Timestamp | None = None
    for date, flag in underwater.items():
        date = pd.Timestamp(date)
        if flag and start is None:
            start = date
        elif not flag and start is not None:
            longest = max(longest, (date - start).days)
            start = None
    if start is not None:
        longest = max(longest, (pd.Timestamp(ratio.index[-1]) - start).days)
    return int(longest)


def rolling_relative(candidate: a4b.A4BSimulation, comparator: a4b.A4BSimulation, months: int) -> pd.Series:
    c = monthly_returns(candidate)
    b = monthly_returns(comparator)
    joined = pd.concat([c.rename("candidate"), b.rename("comparator")], axis=1, join="inner").dropna()
    return (1.0 + joined["candidate"]).rolling(months).apply(np.prod, raw=True) - (1.0 + joined["comparator"]).rolling(months).apply(np.prod, raw=True)


def exclusion_return(simulation: a4b.A4BSimulation, excluded_years: set[int]) -> float:
    curve = simulation.curve.drop_duplicates("date").sort_values("date")
    returns = curve.loc[~curve["date"].dt.year.isin(excluded_years), "net_return"].astype(float)
    if returns.empty:
        return float("nan")
    years = len(returns) / 252.0
    return float((1.0 + returns).prod() ** (1.0 / years) - 1.0)


def annualised_years(start: pd.Timestamp, end: pd.Timestamp) -> float:
    # Match the authoritative A4B/A4D performance annualisation basis exactly.
    return max((pd.Timestamp(end) - pd.Timestamp(start)).days / 365.2425, 1.0 / 12.0)
