"""Run A4B3 and the preregistered sequential A4B4 combination gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import ukactive_a4b_core as core
from build_ukactive_a4b_lifecycle import (
    CUTOFF,
    LATEST5_REVIEW_START,
    LATEST5_START,
    _a4_comparators,
    _metric_row,
    build_plan,
)


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]


def _final_value(sim: core.A4BSimulation) -> float:
    curve = sim.curve.loc[sim.curve["date"].between(LATEST5_START, CUTOFF)]
    return float(curve.iloc[-1]["portfolio_value"] / curve.iloc[0]["portfolio_value"]) if len(curve) else np.nan


def _top3_retention(module_id: str) -> float:
    source = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4B_RIGHT_TAIL_RETENTION.csv")
    top3 = {"GLOBAL_SILVER_MINERS", "EUROPE_BANKS", "GLOBAL_SEMICONDUCTORS"}
    rows = source.loc[source["module_id"].eq(module_id) & source["family"].isin(top3)]
    baseline = rows["same_method_baseline_market_pnl_contribution"].sum()
    return float(rows["module_market_pnl_contribution"].sum() / baseline) if baseline else np.nan


def _select_scale_module() -> tuple[str, str]:
    metrics = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4B_LIFECYCLE_MODULE_METRICS.csv")
    early = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4B_EARLY_ENTRY_VALUE.csv")
    baseline = metrics.loc[metrics["module_id"].eq("A4_BASELINE_MONTHLY")].iloc[0]
    candidates = metrics.loc[metrics["module_family"].eq("SCALE_IN")].copy()
    candidates = candidates.merge(early[["module_id", "aggregate_early_entry_value_vs_incumbent"]], on="module_id", how="left")
    candidates["top3_retention"] = candidates["module_id"].map(_top3_retention)
    candidates["qualifies"] = (
        candidates["net_cagr"].gt(float(baseline["net_cagr"]))
        & candidates["maximum_drawdown"].ge(float(baseline["maximum_drawdown"]) - 1e-12)
        & candidates["aggregate_early_entry_value_vs_incumbent"].gt(0)
        & candidates["top3_retention"].ge(0.70)
    )
    passed = candidates.loc[candidates["qualifies"]].sort_values(
        ["net_cagr", "calmar_mar", "module_id"], ascending=[False, False, True]
    )
    if passed.empty:
        return "NONE", "NO_SCALE_IN_MODULE_PASSED_SEQUENTIAL_GATE"
    module_id = str(passed.iloc[0]["module_id"])
    return ("STARTER_B" if "STARTER_B" in module_id else "STARTER_A"), module_id


def _select_exit_module() -> tuple[str, str]:
    metrics = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4B_LIFECYCLE_MODULE_METRICS.csv")
    money = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4B_NET_MONETISATION_VALUE.csv")
    baseline = metrics.loc[metrics["module_id"].eq("A4_BASELINE_MONTHLY")].iloc[0]
    candidates = metrics.loc[metrics["module_family"].isin(["EXIT", "PROFIT_LOCK"])].merge(
        money[["module_id", "aggregate_net_monetisation_value"]], on="module_id", how="left"
    )
    candidates["top3_retention"] = candidates["module_id"].map(_top3_retention)
    candidates["qualifies"] = (
        candidates["aggregate_net_monetisation_value"].gt(0)
        & candidates["net_excess_vs_equal_pool_cagr"].gt(0)
        & candidates["top3_retention"].ge(0.70)
        & (
            candidates["maximum_drawdown"].ge(-0.25)
            | candidates["maximum_drawdown"].ge(float(baseline["maximum_drawdown"]) + 0.05)
        )
    )
    passed = candidates.loc[candidates["qualifies"]].sort_values(
        ["maximum_drawdown", "calmar_mar", "module_id"], ascending=[False, False, True]
    )
    if passed.empty:
        return "NONE", "NO_EXIT_OR_PROFIT_MODULE_PASSED_SEQUENTIAL_GATE"
    module_id = str(passed.iloc[0]["module_id"])
    if "MFE_GIVEBACK_LOCK" in module_id:
        return "MFE_GIVEBACK_LOCK", module_id
    if "FAST_TAPER" in module_id:
        return "FAST_TAPER", module_id
    if "STRENGTH_PLUS_DECELERATION" in module_id:
        return "STRENGTH_PLUS_DECELERATION", module_id
    return "STRENGTH_HARVEST", module_id


def _normalised_value(sim: core.A4BSimulation, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    source = sim.curve.loc[sim.curve["date"].between(start, end)].set_index("date")["portfolio_value"].astype(float)
    return source / source.iloc[0] if len(source) else source


def _regime_event_ledger(
    module_id: str,
    sim: core.A4BSimulation,
    control: core.A4BSimulation,
) -> pd.DataFrame:
    trades = sim.trades.loc[sim.trades["execution_status"].eq("EXECUTED")].sort_values("execution_date").reset_index(drop=True)
    module_curve = sim.curve.set_index("date")["portfolio_value"].astype(float)
    control_curve = control.curve.set_index("date")["portfolio_value"].astype(float)
    rows: list[dict[str, Any]] = []
    previous_risky = 0.0
    for index, trade in trades.iterrows():
        current_risky = float(trade["target_risky_weight"])
        if current_risky < previous_risky - 1e-12:
            date = pd.Timestamp(trade["execution_date"])
            review = pd.Timestamp(trade["review_date"])
            end_candidates = trades.loc[(trades.index > index) & trades["target_risky_weight"].gt(current_risky + 1e-12)]
            rebuild_date = pd.Timestamp(end_candidates.iloc[0]["execution_date"]) if len(end_candidates) else pd.NaT
            row: dict[str, Any] = {
                "module_id": module_id,
                "regime_derisk_event_id": f"{module_id}-RD-{len(rows)+1:03d}",
                "review_date": review,
                "execution_date": date,
                "prior_risky_allocation": previous_risky,
                "new_risky_allocation": current_risky,
                "risky_allocation_reduced": previous_risky - current_risky,
                "cash_created": previous_risky - current_risky,
                "risk_rebuild_date": rebuild_date,
            }
            decision = sim.decisions.loc[sim.decisions["review_date"].eq(review)].head(1)
            row["regime_state_before_reduction"] = decision.iloc[0]["regime_state"] if len(decision) else "UNKNOWN"
            for sessions, label in [(5, "1w"), (10, "2w"), (21, "4w"), (42, "8w")]:
                available = module_curve.index[module_curve.index >= date]
                if len(available) <= sessions:
                    row[f"module_return_{label}"] = np.nan
                    row[f"control_return_{label}"] = np.nan
                    row[f"derisk_value_{label}"] = np.nan
                    continue
                end = pd.Timestamp(available[sessions])
                common_start = date if date in control_curve.index else control_curve.index[control_curve.index >= date][0]
                common_end = end if end in control_curve.index else control_curve.index[control_curve.index <= end][-1]
                module_return = float(module_curve.loc[end] / module_curve.loc[date] - 1)
                control_return = float(control_curve.loc[common_end] / control_curve.loc[common_start] - 1)
                row[f"module_return_{label}"] = module_return
                row[f"control_return_{label}"] = control_return
                row[f"derisk_value_{label}"] = module_return - control_return
            d4 = row.get("derisk_value_4w", np.nan)
            row["event_classification"] = (
                "USEFUL" if pd.notna(d4) and d4 > 0.01 else
                "FALSE_OR_COSTLY" if pd.notna(d4) and d4 < -0.01 else "NEUTRAL"
            )
            row["warning"] = core.WARNING
            rows.append(row)
        previous_risky = current_risky
    return pd.DataFrame(rows)


def _regime_summary(sim: core.A4BSimulation, control: core.A4BSimulation, module_id: str) -> dict[str, Any]:
    row = _metric_row(sim, module_id, "WEEKLY" if "WEEKLY" in module_id else "MONTHLY_ONLY", "REGIME")
    row["terminal_wealth_multiple"] = _final_value(sim)
    row["control_terminal_wealth_multiple"] = _final_value(control)
    row["aggregate_regime_derisk_value"] = row["terminal_wealth_multiple"] - row["control_terminal_wealth_multiple"]
    row["drawdown_improvement_percentage_points"] = row["maximum_drawdown"] - core.enhanced_performance_metrics(
        control, start=LATEST5_START, end=CUTOFF
    )["maximum_drawdown"]
    return row


def _write(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(PROGRAMME_ROOT / name, index=False, date_format="%Y-%m-%d")


def main() -> None:
    data = core.load_a4b_data()
    baseline_plan = build_plan(data, "A4_BASELINE_MONTHLY", frequency="MONTHLY_ONLY")
    baseline = core.simulate_planned_portfolio(baseline_plan, data)
    regime_specs = [
        ("REGIME_BINARY_WEEKLY", "WEEKLY", "BINARY"),
        ("REGIME_GRADUAL_WEEKLY", "WEEKLY", "GRADUAL"),
        ("REGIME_GRADUAL_HOSTILE25_WEEKLY", "WEEKLY", "GRADUAL_HOSTILE_25"),
        ("REGIME_BINARY_MONTHLY", "MONTHLY_ONLY", "BINARY"),
        ("REGIME_GRADUAL_MONTHLY", "MONTHLY_ONLY", "GRADUAL"),
        ("REGIME_GRADUAL_HOSTILE25_MONTHLY", "MONTHLY_ONLY", "GRADUAL_HOSTILE_25"),
    ]
    regime_plans: dict[str, core.PlannedPortfolio] = {}
    regime_sims: dict[str, core.A4BSimulation] = {}
    regime_rows: list[dict[str, Any]] = []
    regime_event_parts: list[pd.DataFrame] = []
    for module_id, frequency, regime in regime_specs:
        plan = build_plan(data, module_id, frequency=frequency, regime_module=regime)
        sim = core.simulate_planned_portfolio(plan, data)
        regime_plans[module_id] = plan
        regime_sims[module_id] = sim
        regime_rows.append(_regime_summary(sim, baseline, module_id))
        events = _regime_event_ledger(module_id, sim, baseline)
        if len(events):
            regime_event_parts.append(events)
    regime_results = pd.DataFrame(regime_rows)
    regime_results["qualifies_sequential_gate"] = (
        regime_results["maximum_drawdown"].gt(core.enhanced_performance_metrics(baseline, start=LATEST5_START, end=CUTOFF)["maximum_drawdown"])
        & regime_results["ulcer_index"].lt(core.enhanced_performance_metrics(baseline, start=LATEST5_START, end=CUTOFF)["ulcer_index"])
        & regime_results["net_excess_vs_equal_pool_cagr"].gt(0)
        & regime_results["aggregate_regime_derisk_value"].gt(0)
    )
    passed_regimes = regime_results.loc[regime_results["qualifies_sequential_gate"]].sort_values(
        ["hard_drawdown_gate_pass", "maximum_drawdown", "calmar_mar", "ulcer_index", "net_excess_vs_equal_pool_cagr", "module_id"],
        ascending=[False, False, False, True, False, True],
    )
    if len(passed_regimes):
        best_regime_id = str(passed_regimes.iloc[0]["module_id"])
        best_regime_code = (
            "GRADUAL_HOSTILE_25" if "HOSTILE25" in best_regime_id else
            "GRADUAL" if "GRADUAL" in best_regime_id else "BINARY"
        )
    else:
        best_regime_id, best_regime_code = "NONE", "CONTROL"

    best_scale, best_scale_source = _select_scale_module()
    best_exit, best_exit_source = _select_exit_module()
    combinations: list[tuple[str, str, str, str]] = [
        ("ABLATION_BASELINE", "NONE", "NONE", "CONTROL"),
    ]
    if best_scale != "NONE":
        combinations.append(("ABLATION_SCALE_IN_ONLY", best_scale, "NONE", "CONTROL"))
    else:
        combinations.append(("ABLATION_SCALE_IN_ONLY_NOT_RUN", "NONE", "NONE", "CONTROL"))
    if best_exit != "NONE":
        combinations.append(("ABLATION_EXIT_ONLY", "NONE", best_exit, "CONTROL"))
    else:
        combinations.append(("ABLATION_EXIT_ONLY_NOT_RUN", "NONE", "NONE", "CONTROL"))
    # The best preregistered harvest remains visible as an ablation diagnostic,
    # even though it is not eligible for combination when monetisation is negative.
    combinations.append(("ABLATION_PROFIT_HARVEST_ONLY", "NONE", "STRENGTH_PLUS_DECELERATION", "CONTROL"))
    combinations.append(("ABLATION_REGIME_ONLY", "NONE", "NONE", best_regime_code))
    if best_scale != "NONE" and best_exit != "NONE":
        combinations.append(("ABLATION_SCALE_IN_PLUS_EXIT", best_scale, best_exit, "CONTROL"))
    else:
        combinations.append(("ABLATION_SCALE_IN_PLUS_EXIT_NOT_RUN", best_scale if best_scale != "NONE" else "NONE", "NONE", "CONTROL"))
    lifecycle_exit = best_exit if best_exit != "NONE" else "NONE"
    combinations.append(("ABLATION_LIFECYCLE_PLUS_REGIME", best_scale, lifecycle_exit, best_regime_code))
    combinations.append(("FULL_CONTROLLED_COMBINATION", best_scale, lifecycle_exit, best_regime_code))

    combo_plans: dict[str, core.PlannedPortfolio] = {}
    combo_sims: dict[str, core.A4BSimulation] = {}
    combo_rows: list[dict[str, Any]] = []
    for module_id, scale, exit_module, regime in combinations:
        plan = build_plan(data, module_id, frequency="WEEKLY", scale_module=scale, exit_module=exit_module, regime_module=regime)
        sim = core.simulate_planned_portfolio(plan, data)
        combo_plans[module_id] = plan
        combo_sims[module_id] = sim
        row = _metric_row(sim, module_id, "WEEKLY", "ABLATION")
        row.update({
            "scale_in_module": scale, "exit_or_profit_module": exit_module,
            "regime_module": regime, "scale_source_gate": best_scale_source,
            "exit_source_gate": best_exit_source, "regime_source_gate": best_regime_id,
            "top3_winner_contribution_retention": np.nan,
            "ablation_execution_status": "NOT_RUN_NO_QUALIFYING_COMPONENT" if "NOT_RUN" in module_id else "EXECUTED",
        })
        combo_rows.append(row)
    combo_results = pd.DataFrame(combo_rows)

    # Regime histories and causal action ledgers.
    score_columns = [
        "date", "global_trend_regime", "volatility_regime", "dispersion_regime",
        "breadth_regime", "rotation_intensity_regime", "us_technology_dominance",
        "REGIME_SCORE", "PRIOR_8W_MAX_SCORE", "warning",
    ]
    _write(data.weekly_regime[[column for column in score_columns if column in data.weekly_regime.columns]], "UKACTIVE_A4B_REGIME_SCORE_HISTORY.csv")
    state_columns = score_columns[:-1] + ["REGIME_STATE", "REGIME_PEAK_DETECTED", "REGIME_PEAK_DATE", "REGIME_PEAK_OR_MATURITY_FLAG", "warning"]
    _write(data.weekly_regime[[column for column in state_columns if column in data.weekly_regime.columns]], "UKACTIVE_A4B_REGIME_STATE_HISTORY.csv")
    peaks = data.weekly_regime.loc[data.weekly_regime["REGIME_PEAK_DETECTED"]].copy()
    _write(peaks, "UKACTIVE_A4B_REGIME_PEAK_EVENTS.csv")
    _write(regime_results, "UKACTIVE_A4B_REGIME_SCALING_RESULTS.csv")
    regime_events = pd.concat(regime_event_parts, ignore_index=True) if regime_event_parts else pd.DataFrame()
    _write(regime_events, "UKACTIVE_A4B_REGIME_DERISK_EVENTS.csv")
    derisk_value = regime_results[[
        "module_id", "terminal_wealth_multiple", "control_terminal_wealth_multiple",
        "aggregate_regime_derisk_value", "drawdown_improvement_percentage_points",
        "maximum_drawdown", "ulcer_index", "maximum_time_underwater_calendar_days",
        "qualifies_sequential_gate", "warning",
    ]].copy()
    _write(derisk_value, "UKACTIVE_A4B_REGIME_DERISK_VALUE.csv")

    all_sims = {"A4_BASELINE_MONTHLY": baseline, **regime_sims, **combo_sims}
    cash_parts = []
    curve_parts = []
    trade_parts = []
    target_parts = []
    decision_parts = []
    for module_id, sim in all_sims.items():
        curve = sim.curve.loc[sim.curve["date"].between(LATEST5_START, CUTOFF)].copy()
        if len(curve):
            cash_parts.append(curve[["module_id", "date", "cash_fraction", "cash_value", "cash_return_contribution", "cumulative_cash_return_contribution"]])
            curve_parts.append(curve)
        if len(sim.trades):
            trade_parts.append(sim.trades)
        if len(sim.targets):
            target_parts.append(sim.targets)
        if len(sim.decisions):
            decision_parts.append(sim.decisions)
    cash_history = pd.concat(cash_parts, ignore_index=True)
    _write(cash_history, "UKACTIVE_A4B_CASH_ALLOCATION_HISTORY.csv")
    _write(combo_results, "UKACTIVE_A4B_ABLATION_RESULTS.csv")
    _write(combo_results, "UKACTIVE_A4B_COMBINED_LIFECYCLE_RESULTS.csv")
    position_size = pd.concat(decision_parts, ignore_index=True)
    _write(position_size, "UKACTIVE_A4B_POSITION_SIZE_HISTORY.csv")
    trade_ledger = pd.concat(trade_parts, ignore_index=True)
    _write(trade_ledger, "UKACTIVE_A4B_TRADE_AND_CASH_LEDGER.csv")
    equity_curves = pd.concat(curve_parts, ignore_index=True)
    equity_curves.to_parquet(PROGRAMME_ROOT / "UKACTIVE_A4B_EQUITY_CURVES.parquet", index=False)
    drawdown = pd.concat([
        frame.assign(
            normalised_value=frame["portfolio_value"] / frame["portfolio_value"].iloc[0],
        )[["module_id", "date", "normalised_value"]]
        for _, frame in equity_curves.groupby("module_id", sort=False)
    ], ignore_index=True)
    drawdown["drawdown"] = drawdown.groupby("module_id", sort=False)["normalised_value"].transform(lambda values: values / values.cummax() - 1.0)
    _write(drawdown, "UKACTIVE_A4B_DRAWDOWN_COMPARISON.csv")
    smoothness_fields = [
        "module_id", "net_cagr", "maximum_drawdown", "calmar_mar", "ulcer_index",
        "ulcer_performance_index", "maximum_time_underwater_calendar_days",
        "percentage_positive_rolling_12m", "log_equity_curve_r2",
        "log_equity_trend_standard_error", "frequency_of_new_equity_highs",
        "median_calendar_days_between_equity_highs", "percentage_days_underwater",
        "warning",
    ]
    smoothness = pd.concat([regime_results, combo_results], ignore_index=True, sort=False)
    _write(smoothness[[column for column in smoothness_fields if column in smoothness.columns]], "UKACTIVE_A4B_EQUITY_CURVE_SMOOTHNESS.csv")

    registry = {
        "best_scale_in_module": best_scale,
        "best_scale_in_source": best_scale_source,
        "best_exit_or_profit_module": best_exit,
        "best_exit_or_profit_source": best_exit_source,
        "best_regime_module": best_regime_code,
        "best_regime_source": best_regime_id,
        "combination_count": len(combinations),
        "warning": core.WARNING,
    }
    (PROGRAMME_ROOT / "UKACTIVE_A4B_SEQUENTIAL_GATE_RESULTS.json").write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
