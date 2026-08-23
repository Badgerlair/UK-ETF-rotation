"""Run A4C3-A4C4: preregistered trend exits and volatility risk budgets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import ukactive_a4c_core as core


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]


def _write(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(PROGRAMME_ROOT / name, index=False, date_format="%Y-%m-%d")


def _family_market_contribution(simulation: Any, family: str) -> float:
    curve = simulation.curve.loc[simulation.curve["date"].between(core.LATEST5_START, core.CUTOFF)]
    return float(sum(float(json.loads(value).get(family, 0.0)) for value in curve["family_market_pnl_json"]))


def _weight(target_json: str, family: str) -> float:
    return float(json.loads(str(target_json)).get(family, 0.0))


def _interval_return(series: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> float:
    values = series.loc[start:end].dropna()
    return float(values.iloc[-1] / values.iloc[0] - 1.0) if len(values) >= 2 else np.nan


def exit_event_ledger(plan: Any, simulation: Any, data: core.A4CData) -> pd.DataFrame:
    actions = plan.actions.copy()
    if actions.empty:
        return pd.DataFrame()
    actions["review_date"] = pd.to_datetime(actions["review_date"])
    trades = simulation.trades.loc[simulation.trades["execution_status"].eq("EXECUTED")].copy()
    trades["review_date"] = pd.to_datetime(trades["review_date"])
    trades["execution_date"] = pd.to_datetime(trades["execution_date"])
    leaders = core.monthly_leaders(data).sort_values("monthly_review_date")
    calendar = data.base.research.calendar
    rows: list[dict[str, Any]] = []
    for action_number, action in enumerate(actions.itertuples(index=False), start=1):
        family = str(action.family)
        trade = trades.loc[trades["review_date"].eq(pd.Timestamp(action.review_date))]
        if trade.empty:
            continue
        execution_date = pd.Timestamp(trade.iloc[0]["execution_date"])
        before = json.loads(str(action.from_weights_json))
        after = json.loads(str(action.to_weights_json))
        from_weight = float(before.get(family, 0.0))
        to_weight = float(after.get(family, 0.0))
        later = actions.loc[(actions["review_date"].gt(action.review_date)) & actions["family"].eq(family)].copy()
        reentry_review = pd.NaT
        for later_action in later.itertuples(index=False):
            later_before = _weight(later_action.from_weights_json, family)
            later_after = _weight(later_action.to_weights_json, family)
            if later_after > later_before + 1e-12:
                reentry_review = pd.Timestamp(later_action.review_date)
                break
        if pd.notna(reentry_review):
            reentry_trade = trades.loc[trades["review_date"].eq(reentry_review)]
            reentry_end = pd.Timestamp(reentry_trade.iloc[0]["execution_date"]) if len(reentry_trade) else reentry_review
        else:
            reentry_end = core.CUTOFF
        # A failure overlay is counterfactual only until the frozen baseline
        # would itself switch away from this family.  Extending the old family
        # to the panel cutoff would double-count foregone return that the
        # baseline never owned.
        switch = leaders.loc[(leaders["monthly_review_date"].gt(action.review_date)) & leaders["incumbent_family"].ne(family)]
        if len(switch):
            switch_review = pd.Timestamp(switch.iloc[0]["monthly_review_date"])
            switch_position = calendar.get_loc(switch_review)
            switch_end = pd.Timestamp(calendar[min(switch_position + 1, len(calendar) - 1)])
        else:
            switch_review, switch_end = pd.NaT, core.CUTOFF
        end_date = min(reentry_end, switch_end)
        asset_return = _interval_return(data.base.research.wealth[family], execution_date, end_date)
        cash_return = _interval_return(data.base.cash_index, execution_date, end_date)
        reduced_weight = max(0.0, from_weight - to_weight)
        opportunity = reduced_weight * ((cash_return if pd.notna(cash_return) else 0.0) - (asset_return if pd.notna(asset_return) else 0.0))
        avoided = max(0.0, opportunity)
        foregone = max(0.0, -opportunity)
        cost = float(trade.iloc[0]["transaction_cost_rate"])
        session_count = data.base.research.calendar.get_indexer([end_date])[0] - data.base.research.calendar.get_indexer([execution_date])[0] if end_date in data.base.research.calendar and execution_date in data.base.research.calendar else np.nan
        rows.append({
            "module_id": plan.module_id, "exit_event_id": f"{plan.module_id}_EXIT_{action_number:03d}", "family": family,
            "review_date": action.review_date, "execution_date": execution_date, "action_type": action.action_type,
            "from_weight": from_weight, "to_weight": to_weight, "risky_weight_reduced": reduced_weight,
            "counterfactual_end_date": end_date, "reentry_review_date": reentry_review, "xlon_sessions_until_reentry_or_cutoff": session_count,
            "frozen_baseline_switch_review_date": switch_review, "frozen_baseline_switch_execution_proxy_date": switch_end,
            "selected_asset_return_if_held": asset_return, "actual_cash_return_on_reduced_capital": cash_return,
            "avoided_downside": avoided, "foregone_upside": foregone, "incremental_cost": cost,
            "net_exit_value": avoided - foregone - cost,
            "whipsaw_within_42_sessions": bool(pd.notna(session_count) and session_count <= 42 and pd.notna(asset_return) and asset_return > cash_return),
            "same_close_execution": False, "warning": core.WARNING,
        })
    return pd.DataFrame(rows)


def _right_tail(simulations: dict[str, Any], baseline: Any) -> pd.DataFrame:
    families = ["GLOBAL_SILVER_MINERS", "EUROPE_BANKS", "GLOBAL_SEMICONDUCTORS"]
    baseline_values = {family: _family_market_contribution(baseline, family) for family in families}
    rows = []
    for module_id, simulation in simulations.items():
        for family in families:
            contribution = _family_market_contribution(simulation, family)
            rows.append({"module_id": module_id, "family": family, "module_market_pnl_contribution": contribution, "baseline_market_pnl_contribution": baseline_values[family], "contribution_retention_ratio": contribution / baseline_values[family] if baseline_values[family] else np.nan, "warning": core.WARNING})
    return pd.DataFrame(rows)


def _aggregate_retention(right_tail: pd.DataFrame) -> pd.Series:
    return right_tail.groupby("module_id").apply(
        lambda group: group["module_market_pnl_contribution"].sum() / group["baseline_market_pnl_contribution"].sum()
        if group["baseline_market_pnl_contribution"].sum() else np.nan,
        include_groups=False,
    )


def run_exits(data: core.A4CData, baseline: Any, comparators: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    modules = ["EXIT_A_50EMA", "EXIT_B_21_WARNING_50_FAILURE", "EXIT_C_ABSOLUTE_AND_RELATIVE", "EXIT_D_RELATIVE_ONLY"]
    simulations: dict[str, Any] = {}
    plans: dict[str, Any] = {}
    metrics_rows: list[dict[str, Any]] = []
    event_parts: list[pd.DataFrame] = []
    baseline_metrics = core.metric_row(baseline, data, "A4_BASELINE", comparators=comparators)
    for module_id in modules:
        plan = core.build_exit_plan(data, module_id)
        sim = core.simulate(plan, data)
        plans[module_id], simulations[module_id] = plan, sim
        metrics_rows.append(core.metric_row(sim, data, module_id, comparators=comparators))
        events = exit_event_ledger(plan, sim, data)
        if len(events):
            event_parts.append(events)
    events = pd.concat(event_parts, ignore_index=True) if event_parts else pd.DataFrame()
    right_tail = _right_tail(simulations, baseline)
    retention = _aggregate_retention(right_tail)
    net_rows = []
    whipsaw_rows = []
    for module_id in modules:
        all_actions = events.loc[events["module_id"].eq(module_id)] if len(events) else pd.DataFrame()
        subset = all_actions.loc[all_actions["risky_weight_reduced"].gt(1e-12)] if len(all_actions) else pd.DataFrame()
        incremental_cost = max(0.0, float(simulations[module_id].trades["transaction_cost_rate"].fillna(0).sum() - baseline.trades["transaction_cost_rate"].fillna(0).sum()))
        net_rows.append({
            "module_id": module_id, "exit_event_count": len(subset), "aggregate_avoided_downside": subset["avoided_downside"].sum() if len(subset) else 0.0,
            "aggregate_foregone_upside": subset["foregone_upside"].sum() if len(subset) else 0.0, "aggregate_incremental_cost": incremental_cost,
            "net_exit_value": (subset["avoided_downside"].sum() - subset["foregone_upside"].sum() - incremental_cost) if len(subset) else -incremental_cost, "warning": core.WARNING,
        })
        whipsaw_rows.append({
            "module_id": module_id, "reduction_or_exit_events": len(subset), "whipsaw_count_42_sessions": int(subset["whipsaw_within_42_sessions"].sum()) if len(subset) else 0,
            "whipsaw_rate": float(subset["whipsaw_within_42_sessions"].mean()) if len(subset) else np.nan,
            "median_sessions_until_reentry": subset["xlon_sessions_until_reentry_or_cutoff"].median() if len(subset) else np.nan, "warning": core.WARNING,
        })
    metrics = pd.DataFrame(metrics_rows)
    net = pd.DataFrame(net_rows)
    metrics = metrics.merge(net[["module_id", "net_exit_value"]], on="module_id", how="left", validate="one_to_one")
    metrics["top_three_contribution_retention"] = metrics["module_id"].map(retention)
    metrics["drawdown_improvement_vs_baseline"] = metrics["maximum_drawdown"] - baseline_metrics["maximum_drawdown"]
    metrics["passes_exit_promotion_gate"] = (
        metrics["net_exit_value"].gt(0)
        & metrics["drawdown_improvement_vs_baseline"].ge(0.05)
        & metrics["net_excess_vs_equal_pool"].gt(0)
        & metrics["top_three_contribution_retention"].ge(0.70)
    )
    return metrics, events, net, right_tail, pd.DataFrame(whipsaw_rows), simulations


def volatility_attribution(plan: Any, data: core.A4CData) -> pd.DataFrame:
    decisions = plan.decisions.sort_values("review_date").reset_index(drop=True)
    rows = []
    for index, row in decisions.iterrows():
        if row["target_risky_weight"] >= 1.0 - 1e-12 or not row["monthly_incumbent"]:
            continue
        start = pd.Timestamp(row["execution_date"]) if pd.notna(row["execution_date"]) else pd.Timestamp(row["review_date"])
        if index + 1 < len(decisions):
            end_value = decisions.iloc[index + 1]["execution_date"]
            end = pd.Timestamp(end_value) if pd.notna(end_value) else pd.Timestamp(decisions.iloc[index + 1]["review_date"])
        else:
            end = core.CUTOFF
        family = str(row["monthly_incumbent"])
        asset_return = _interval_return(data.base.research.wealth[family], start, end)
        cash_return = _interval_return(data.base.cash_index, start, end)
        cash_weight = 1.0 - float(row["target_risky_weight"])
        difference = cash_weight * ((cash_return if pd.notna(cash_return) else 0.0) - (asset_return if pd.notna(asset_return) else 0.0))
        rows.append({
            "module_id": plan.module_id, "review_date": row["review_date"], "execution_date": start, "counterfactual_end_date": end,
            "family": family, "prior_realised_vol_63": row["prior_realised_vol_63"], "target_volatility": row["target_volatility"],
            "risky_weight": row["target_risky_weight"], "cash_weight": cash_weight, "subsequent_asset_return": asset_return, "subsequent_cash_return": cash_return,
            "avoided_loss": max(0.0, difference), "foregone_upside": max(0.0, -difference), "net_effect_before_incremental_cost": difference,
            "warning": core.WARNING,
        })
    return pd.DataFrame(rows)


def run_volatility(data: core.A4CData, baseline: Any, comparators: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    simulations: dict[str, Any] = {}
    plans: dict[str, Any] = {}
    metrics_rows: list[dict[str, Any]] = []
    position_parts: list[pd.DataFrame] = []
    attribution_parts: list[pd.DataFrame] = []
    cash_parts: list[pd.DataFrame] = []
    baseline_metrics = core.metric_row(baseline, data, "A4_BASELINE", comparators=comparators)
    for target in (0.10, 0.125, 0.15):
        plan = core.build_volatility_plan(data, target)
        sim = core.simulate(plan, data)
        plans[plan.module_id], simulations[plan.module_id] = plan, sim
        metrics_rows.append(core.metric_row(sim, data, plan.module_id, comparators=comparators))
        position_parts.append(plan.decisions.assign(warning=core.WARNING))
        attr = volatility_attribution(plan, data)
        if len(attr):
            attribution_parts.append(attr)
        cash_parts.append(sim.curve[["module_id", "date", "portfolio_value", "invested_fraction", "cash_fraction", "cash_value", "cash_return_contribution", "cumulative_cash_return_contribution", "data_valid"]].assign(warning=core.WARNING))
    right_tail = _right_tail(simulations, baseline)
    retention = _aggregate_retention(right_tail)
    metrics = pd.DataFrame(metrics_rows)
    metrics["top_three_contribution_retention"] = metrics["module_id"].map(retention)
    metrics["drawdown_improvement_vs_baseline"] = metrics["maximum_drawdown"] - baseline_metrics["maximum_drawdown"]
    metrics["calmar_improvement_vs_baseline"] = metrics["calmar_mar"] - baseline_metrics["calmar_mar"]
    metrics["ulcer_improvement_vs_baseline"] = baseline_metrics["ulcer_index"] - metrics["ulcer_index"]
    metrics["passes_volatility_promotion_gate"] = (
        metrics["drawdown_improvement_vs_baseline"].ge(0.05)
        & metrics["calmar_improvement_vs_baseline"].gt(0)
        & metrics["ulcer_improvement_vs_baseline"].gt(0)
        & metrics["net_excess_vs_equal_pool"].gt(0)
        & metrics["top_three_contribution_retention"].ge(0.70)
    )
    return metrics, pd.concat(position_parts, ignore_index=True), pd.concat(attribution_parts, ignore_index=True) if attribution_parts else pd.DataFrame(), pd.concat(cash_parts, ignore_index=True), simulations


def main() -> None:
    data = core.load_a4c_data()
    baseline = core.simulate(core.build_baseline_plan(data), data)
    reproduction = core.exact_baseline_reproduction(baseline)
    if not reproduction["result"].eq("PASS").all():
        raise AssertionError("A4 baseline did not reproduce")
    comparators = core.comparator_curves(data)

    exit_metrics, exit_events, net_exit, exit_right_tail, whipsaw, _ = run_exits(data, baseline, comparators)
    _write(exit_metrics, "UKACTIVE_A4C_TREND_EXIT_RESULTS.csv")
    _write(exit_events, "UKACTIVE_A4C_EXIT_EVENTS.csv")
    _write(net_exit, "UKACTIVE_A4C_NET_EXIT_VALUE.csv")
    _write(exit_right_tail, "UKACTIVE_A4C_EXIT_RIGHT_TAIL_RETENTION.csv")
    _write(whipsaw, "UKACTIVE_A4C_EXIT_WHIPSAW_ANALYSIS.csv")

    vol_metrics, position_history, attribution, cash_history, _ = run_volatility(data, baseline, comparators)
    _write(vol_metrics, "UKACTIVE_A4C_VOLATILITY_TARGET_RESULTS.csv")
    _write(position_history, "UKACTIVE_A4C_VOLATILITY_POSITION_HISTORY.csv")
    _write(attribution, "UKACTIVE_A4C_VOLATILITY_SIZING_ATTRIBUTION.csv")
    _write(cash_history, "UKACTIVE_A4C_CASH_HISTORY.csv")


if __name__ == "__main__":
    main()
