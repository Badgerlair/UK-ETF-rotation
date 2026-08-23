"""Run A4C5: fixed global-core / frozen-active portfolio construction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import ukactive_a4c_core as core


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
CORE_FAMILY = "GLOBAL_DEVELOPED_WORLD"


def _write(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(PROGRAMME_ROOT / name, index=False, date_format="%Y-%m-%d")


def _market_contributions(simulation: Any) -> dict[str, float]:
    contributions: dict[str, float] = {}
    curve = simulation.curve.loc[simulation.curve["date"].between(core.LATEST5_START, core.CUTOFF)]
    for text in curve["family_market_pnl_json"]:
        for family, value in json.loads(text).items():
            contributions[family] = contributions.get(family, 0.0) + float(value)
    return contributions


def contribution_rows(simulations: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for module_id, simulation in simulations.items():
        curve = simulation.curve.loc[simulation.curve["date"].between(core.LATEST5_START, core.CUTOFF)].copy()
        values = curve["portfolio_value"].astype(float)
        contributions = _market_contributions(simulation)
        core_contribution = float(contributions.get(CORE_FAMILY, 0.0))
        active_contribution = float(sum(value for family, value in contributions.items() if family != CORE_FAMILY))
        cash_contribution = 0.0
        costs = -float(simulation.trades.loc[pd.to_datetime(simulation.trades["execution_date"], errors="coerce").between(core.LATEST5_START, core.CUTOFF), "transaction_cost_value"].fillna(0).sum())
        total_change = float(values.iloc[-1] - 1.0) if len(values) else np.nan
        component_sum = active_contribution + core_contribution + cash_contribution + costs
        rows.append({
            "module_id": module_id, "active_market_pnl_contribution": active_contribution, "core_market_pnl_contribution": core_contribution,
            "cash_return_contribution": cash_contribution, "transaction_cost_contribution": costs,
            "portfolio_value_change": total_change, "component_sum": component_sum, "reconciliation_difference": total_change - component_sum,
            "active_share_of_positive_market_contribution": active_contribution / (active_contribution + core_contribution) if active_contribution + core_contribution > 0 else np.nan,
            "warning": core.WARNING,
        })
    return pd.DataFrame(rows)


def _curve_return(curve: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> float:
    values = curve.loc[curve["date"].between(start, end), ["date", "portfolio_value"]].drop_duplicates("date").sort_values("date")
    return float(values.iloc[-1]["portfolio_value"] / values.iloc[0]["portfolio_value"] - 1.0) if len(values) >= 2 else np.nan


def strategic_rebalance_rows(plans: dict[str, Any], simulations: dict[str, Any], baseline: Any, data: core.A4CData) -> pd.DataFrame:
    rows = []
    for module_id, plan in plans.items():
        if module_id == "CORE_ACTIVE_100":
            continue
        strategic_active = float(module_id.rsplit("_", 1)[-1]) / 100.0
        trades = simulations[module_id].trades.loc[simulations[module_id].trades["execution_status"].eq("EXECUTED")].sort_values("execution_date").reset_index(drop=True)
        prior_target: dict[str, float] = {}
        prior_execution = pd.NaT
        for index, trade in trades.iterrows():
            execution = pd.Timestamp(trade["execution_date"])
            target = json.loads(str(trade["target_weights_json"]))
            active_family = next((family for family in target if family != CORE_FAMILY), "")
            if prior_target and pd.notna(prior_execution):
                prior_active_family = next((family for family in prior_target if family != CORE_FAMILY), "")
                prior_active_weight = float(sum(weight for family, weight in prior_target.items() if family != CORE_FAMILY))
                prior_core_weight = float(prior_target.get(CORE_FAMILY, 0.0))
                active_growth = 1.0 + _interval_asset_return(data, prior_active_family, prior_execution, execution) if prior_active_family else 1.0
                core_growth = 1.0 + _interval_asset_return(data, CORE_FAMILY, prior_execution, execution)
                active_value = prior_active_weight * active_growth
                core_value = prior_core_weight * core_growth
                denominator = active_value + core_value
                active_weight_pre = active_value / denominator if denominator > 0 else np.nan
                transfer_to_core = max(0.0, active_weight_pre - strategic_active) if pd.notna(active_weight_pre) else 0.0
            else:
                prior_active_family = ""
                active_weight_pre = np.nan
                transfer_to_core = 0.0
            next_execution = pd.Timestamp(trades.iloc[index + 1]["execution_date"]) if index + 1 < len(trades) else core.CUTOFF
            if transfer_to_core > 0:
                core_return = _interval_asset_return(data, CORE_FAMILY, execution, next_execution)
                active_return = _curve_return(baseline.curve, execution, next_execution)
                net = transfer_to_core * ((core_return if pd.notna(core_return) else 0.0) - (active_return if pd.notna(active_return) else 0.0))
            else:
                core_return = active_return = net = 0.0
            rows.append({
                "module_id": module_id, "review_date": trade["review_date"], "execution_date": execution, "next_execution_or_cutoff": next_execution,
                "prior_active_family": prior_active_family, "new_active_family": active_family, "strategic_active_weight": strategic_active,
                "active_weight_immediately_before_rebalance": active_weight_pre, "active_weight_transferred_to_core": transfer_to_core,
                "subsequent_global_core_return": core_return, "subsequent_frozen_active_return": active_return,
                "active_profit_protected_from_subsequent_active_drawdown": max(0.0, net), "foregone_active_upside": max(0.0, -net),
                "strategic_rebalance_monetisation_value": net, "warning": core.WARNING,
            })
            prior_target = target
            prior_execution = execution
    return pd.DataFrame(rows)


def _interval_asset_return(data: core.A4CData, family: str, start: pd.Timestamp, end: pd.Timestamp) -> float:
    if not family:
        return np.nan
    values = data.base.research.wealth.loc[start:end, family].dropna()
    return float(values.iloc[-1] / values.iloc[0] - 1.0) if len(values) >= 2 else np.nan


def main() -> None:
    data = core.load_a4c_data()
    baseline = core.simulate(core.build_baseline_plan(data), data)
    if not core.exact_baseline_reproduction(baseline)["result"].eq("PASS").all():
        raise AssertionError("A4 baseline did not reproduce")
    comparators = core.comparator_curves(data)
    baseline_metrics = core.metric_row(baseline, data, "A4_BASELINE", comparators=comparators)

    plans: dict[str, Any] = {}
    simulations: dict[str, Any] = {}
    rows = []
    curves = []
    for active_weight in (0.25, 0.50, 0.75, 1.0):
        plan = core.build_core_satellite_plan(data, active_weight)
        sim = core.simulate(plan, data)
        plans[plan.module_id], simulations[plan.module_id] = plan, sim
        metrics = core.metric_row(sim, data, plan.module_id, comparators=comparators)
        metrics["strategic_active_weight"] = active_weight
        metrics["strategic_core_weight"] = 1.0 - active_weight
        metrics["drawdown_improvement_vs_100_active"] = metrics["maximum_drawdown"] - baseline_metrics["maximum_drawdown"]
        metrics["passes_whole_portfolio_dd_below_20"] = metrics["maximum_drawdown"] > -0.20
        metrics["passes_whole_portfolio_dd_below_15"] = metrics["maximum_drawdown"] > -0.15
        metrics["passes_whole_portfolio_dd_below_10"] = metrics["maximum_drawdown"] > -0.10
        metrics["passes_core_satellite_promotion_gate_pre_rolling"] = (
            metrics["drawdown_improvement_vs_100_active"] >= 0.05
            and metrics["net_cagr"] > metrics["global_benchmark_cagr"] + 0.01
            and metrics["calmar_mar"] >= baseline_metrics["calmar_mar"]
            and metrics["net_excess_vs_equal_pool"] > 0
        )
        rows.append(metrics)
        curve = sim.curve.copy()
        curve["drawdown"] = curve["portfolio_value"] / curve["portfolio_value"].cummax() - 1.0
        curves.append(curve)

    results = pd.DataFrame(rows)
    contributions = contribution_rows(simulations)
    monetisation = strategic_rebalance_rows(plans, simulations, baseline, data)
    if len(monetisation):
        summary = monetisation.groupby("module_id", as_index=False).agg(
            rebalance_observations=("review_date", "count"), active_to_core_transfer_events=("active_weight_transferred_to_core", lambda values: int((values > 1e-12).sum())),
            aggregate_active_weight_transferred_to_core=("active_weight_transferred_to_core", "sum"),
            aggregate_active_profit_protected=("active_profit_protected_from_subsequent_active_drawdown", "sum"), aggregate_foregone_active_upside=("foregone_active_upside", "sum"),
            strategic_rebalance_monetisation_value=("strategic_rebalance_monetisation_value", "sum"),
        )
        summary["record_type"] = "MODULE_SUMMARY"
        detail = monetisation.copy()
        detail["record_type"] = "REBALANCE_DETAIL"
        monetisation = pd.concat([detail, summary], ignore_index=True, sort=False)
        monetisation["warning"] = core.WARNING

    _write(results, "UKACTIVE_A4C_CORE_SATELLITE_RESULTS.csv")
    pd.concat(curves, ignore_index=True).to_parquet(PROGRAMME_ROOT / "UKACTIVE_A4C_CORE_SATELLITE_EQUITY_CURVES.parquet", index=False)
    _write(contributions, "UKACTIVE_A4C_CORE_ACTIVE_CONTRIBUTION.csv")
    _write(monetisation, "UKACTIVE_A4C_STRATEGIC_REBALANCE_MONETISATION.csv")


if __name__ == "__main__":
    main()
