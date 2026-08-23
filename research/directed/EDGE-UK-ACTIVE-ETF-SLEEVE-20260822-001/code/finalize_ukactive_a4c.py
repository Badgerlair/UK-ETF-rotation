"""Finalize UKACTIVE-A4C controlled combination, robustness and governance."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import build_ukactive_a4c_risk as risk
import query_ukactive_rotation as query_engine
import ukactive_a4c_core as core


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROGRAMME_ROOT.parents[2]
DECISION = "UKACTIVE_A4C_CORE_SATELLITE_CANDIDATE_FOUND"
PROMOTED = "CORE_ACTIVE_50"


def _write(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(PROGRAMME_ROOT / name, index=False, date_format="%Y-%m-%d")


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _family_contribution(simulation: Any, family: str) -> float:
    curve = simulation.curve.loc[simulation.curve["date"].between(core.LATEST5_START, core.CUTOFF)]
    return float(sum(float(json.loads(text).get(family, 0.0)) for text in curve["family_market_pnl_json"]))


def _rolling_rows(simulations: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for module_id, simulation in simulations.items():
        curve = simulation.curve.loc[simulation.curve["date"].between(core.LATEST5_START, core.CUTOFF)].drop_duplicates("date").sort_values("date")
        value = curve.set_index("date")["portfolio_value"].astype(float)
        month_end = value.groupby([value.index.year, value.index.month]).last()
        month_dates = value.groupby([value.index.year, value.index.month]).apply(lambda series: series.index[-1])
        for months in (12, 24):
            for end_index in range(months, len(month_end)):
                start_value = float(month_end.iloc[end_index - months])
                end_value = float(month_end.iloc[end_index])
                start_date = pd.Timestamp(month_dates.iloc[end_index - months])
                end_date = pd.Timestamp(month_dates.iloc[end_index])
                total = end_value / start_value - 1.0
                cagr = (1.0 + total) ** (12.0 / months) - 1.0
                window = value.loc[start_date:end_date]
                dd = float((window / window.cummax() - 1.0).min())
                rows.append({"record_type": f"ROLLING_{months}M", "module_id": module_id, "window_start": start_date, "window_end": end_date, "excluded_year": np.nan, "total_return": total, "annualised_return": cagr, "maximum_drawdown": dd, "positive_return": total > 0, "warning": core.WARNING})
        returns = value.pct_change(fill_method=None).dropna()
        for year in sorted(set(returns.index.year) & {2021, 2022, 2023, 2024, 2025, 2026}):
            retained = returns.loc[returns.index.year != year]
            synthetic = (1.0 + retained).cumprod()
            cagr = float(synthetic.iloc[-1] ** (252.0 / len(retained)) - 1.0) if len(retained) else np.nan
            dd = float((synthetic / synthetic.cummax() - 1.0).min()) if len(synthetic) else np.nan
            rows.append({"record_type": "LEAVE_ONE_YEAR_OUT", "module_id": module_id, "window_start": retained.index.min() if len(retained) else pd.NaT, "window_end": retained.index.max() if len(retained) else pd.NaT, "excluded_year": year, "total_return": float(synthetic.iloc[-1] - 1.0) if len(synthetic) else np.nan, "annualised_return": cagr, "maximum_drawdown": dd, "positive_return": bool(len(synthetic) and synthetic.iloc[-1] > 1.0), "warning": core.WARNING})
    return pd.DataFrame(rows)


def _year_rows(simulations: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for module_id, simulation in simulations.items():
        curve = simulation.curve.loc[simulation.curve["date"].between(core.LATEST5_START, core.CUTOFF)].drop_duplicates("date").sort_values("date")
        value = curve.set_index("date")["portfolio_value"].astype(float)
        daily = value.pct_change(fill_method=None)
        for year, group in daily.groupby(daily.index.year):
            returns = group.dropna()
            if not len(returns):
                continue
            synthetic = (1.0 + returns).cumprod()
            rows.append({"module_id": module_id, "calendar_year": int(year), "period_start": returns.index.min(), "period_end": returns.index.max(), "partial_year": bool(year in {2021, 2026}), "year_return": float(synthetic.iloc[-1] - 1.0), "maximum_drawdown_within_year": float((synthetic / synthetic.cummax() - 1.0).min()), "positive_year": bool(synthetic.iloc[-1] > 1.0), "warning": core.WARNING})
    return pd.DataFrame(rows)


def _first_valid_review(data: core.A4CData) -> pd.Timestamp:
    leaders = core.monthly_leaders(data)
    valid = leaders.loc[leaders["incumbent_family"].ne("")]
    if valid.empty:
        raise AssertionError("No historical slow leader")
    return pd.Timestamp(valid.iloc[0]["monthly_review_date"])


def _window_results(data: core.A4CData) -> tuple[pd.DataFrame, dict[str, Any]]:
    first_review = _first_valid_review(data)
    comparators_full = core.comparator_curves(data, first_review)
    comparators_latest5 = core.comparator_curves(data)
    baseline_full = core.simulate(core.build_baseline_plan(data, review_start=first_review), data)
    baseline_latest5 = core.simulate(core.build_baseline_plan(data), data)
    full_sims: dict[str, Any] = {"A4_BASELINE": baseline_full}
    latest5_sims: dict[str, Any] = {"A4_BASELINE": baseline_latest5}
    for weight in (0.25, 0.50, 0.75, 1.0):
        plan = core.build_core_satellite_plan(data, weight, review_start=first_review)
        full_sims[plan.module_id] = core.simulate(plan, data)
        latest5_plan = core.build_core_satellite_plan(data, weight)
        latest5_sims[latest5_plan.module_id] = core.simulate(latest5_plan, data)
    rows = []
    for module_id, simulation in full_sims.items():
        for window_id, (start, end) in core.window_definitions(data.policy).items():
            if window_id in {"LATEST_5Y", "LATEST_3Y"}:
                source_simulation = latest5_sims[module_id]
                source_comparators = comparators_latest5
            else:
                source_simulation = simulation
                source_comparators = comparators_full
            metrics = core.metric_row(source_simulation, data, module_id, start=start, end=end, comparators=source_comparators)
            metrics["window_id"] = window_id
            rows.append(metrics)
    return pd.DataFrame(rows), full_sims


def _dependency_rows(data: core.A4CData, comparators: dict[str, pd.DataFrame]) -> pd.DataFrame:
    tests = {
        "CONTROL": (set(), "DYNAMIC_POINT_IN_TIME"),
        "REMOVE_SILVER_MINERS": ({"GLOBAL_SILVER_MINERS"}, "DYNAMIC_POINT_IN_TIME"),
        "REMOVE_EUROPE_BANKS": ({"EUROPE_BANKS"}, "DYNAMIC_POINT_IN_TIME"),
        "REMOVE_SEMICONDUCTORS": ({"GLOBAL_SEMICONDUCTORS"}, "DYNAMIC_POINT_IN_TIME"),
        "REMOVE_TOP3_CONTRIBUTORS": ({"GLOBAL_SILVER_MINERS", "EUROPE_BANKS", "GLOBAL_SEMICONDUCTORS"}, "DYNAMIC_POINT_IN_TIME"),
        "MATURE_ONLY": (set(), "MATURE_ONLY"),
        "MATURE_PLUS_DEVELOPING": (set(), "MATURE_PLUS_DEVELOPING"),
    }
    rows = []
    for test_id, (excluded, maturity_scope) in tests.items():
        baseline = core.simulate(core.build_baseline_plan(data, excluded_families=excluded, maturity_scope=maturity_scope), data)
        blend = core.simulate(core.build_core_satellite_plan(data, 0.50, excluded_families=excluded, maturity_scope=maturity_scope), data)
        for module_id, simulation in (("A4_BASELINE", baseline), (PROMOTED, blend)):
            metrics = core.metric_row(simulation, data, module_id, comparators=comparators)
            rows.append({"dependency_test": test_id, "excluded_families": ";".join(sorted(excluded)), "maturity_scope": maturity_scope, "module_id": module_id, "net_cagr": metrics["net_cagr"], "net_excess_vs_global": metrics["net_excess_vs_global"], "net_excess_vs_equal_pool": metrics["net_excess_vs_equal_pool"], "maximum_drawdown": metrics["maximum_drawdown"], "calmar_mar": metrics["calmar_mar"], "ulcer_index": metrics["ulcer_index"], "warning": core.WARNING})
    return pd.DataFrame(rows)


def _cost_rows(data: core.A4CData) -> pd.DataFrame:
    rows = []
    for module_id, plan in (("A4_BASELINE", core.build_baseline_plan(data)), (PROMOTED, core.build_core_satellite_plan(data, 0.50))):
        for bps in (10.0, 20.0, 40.0):
            for size in (100_000.0, 250_000.0, 500_000.0):
                simulation = core.simulate(plan, data, friction_bps=bps, fixed_fee_gbp=3.99, sleeve_size_gbp=size)
                metrics = core.a4b.enhanced_performance_metrics(simulation, start=core.LATEST5_START, end=core.CUTOFF)
                rows.append({"module_id": module_id, "one_way_friction_bps": bps, "ii_fixed_fee_gbp_per_trade_leg": 3.99, "sleeve_size_gbp": size, "net_cagr": metrics["net_cagr"], "maximum_drawdown": metrics["maximum_drawdown"], "calmar_mar": metrics["calmar_mar"], "ulcer_index": metrics["ulcer_index"], "annual_turnover_traded_notional": metrics["annual_turnover_traded_notional"], "trade_legs": metrics["trade_legs"], "warning": core.WARNING})
    return pd.DataFrame(rows)


def _right_tail_rows(simulations: dict[str, Any], baseline: Any) -> pd.DataFrame:
    families = ["GLOBAL_SILVER_MINERS", "EUROPE_BANKS", "GLOBAL_SEMICONDUCTORS"]
    baseline_values = {family: _family_contribution(baseline, family) for family in families}
    rows = []
    for module_id, simulation in simulations.items():
        for family in families:
            value = _family_contribution(simulation, family)
            rows.append({"module_id": module_id, "family": family, "module_contribution": value, "baseline_contribution": baseline_values[family], "contribution_retention": value / baseline_values[family] if baseline_values[family] else np.nan, "warning": core.WARNING})
    return pd.DataFrame(rows)


def _drawdown_state_trace(data: core.A4CData, baseline: Any) -> pd.DataFrame:
    """Create a daily episode trace with the last contemporaneous weekly state."""
    episodes = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4C_DRAWDOWN_EPISODES.csv", parse_dates=["portfolio_peak_date", "trough_date", "recovery_date"])
    curve = baseline.curve.copy().sort_values("date").reset_index(drop=True)
    curve["holding_run"] = curve["holdings"].ne(curve["holdings"].shift()).cumsum()
    curve["holding_entry_date_asof"] = curve.groupby("holding_run")["date"].transform("min")
    curve_indexed = curve.set_index("date", drop=False)
    daily = data.daily_technical.set_index(["date", "economic_exposure_family_id"], drop=False).sort_index()
    weekly = data.weekly_features.copy().sort_values(["date", "economic_exposure_family_id"])
    weekly_indexed = weekly.set_index(["date", "economic_exposure_family_id"], drop=False)
    weekly_dates = pd.DatetimeIndex(weekly["date"].drop_duplicates().sort_values())
    crossover_by_date = {
        pd.Timestamp(date): ";".join(group.loc[group["FAST_CROSSOVER_PRIMARY"].fillna(False), "economic_exposure_family_id"].sort_values())
        for date, group in weekly.groupby("date", sort=True)
    }
    rows: list[dict[str, Any]] = []
    for episode in episodes.itertuples(index=False):
        end = pd.Timestamp(episode.recovery_date) if pd.notna(episode.recovery_date) else core.CUTOFF
        period = curve.loc[curve["date"].between(pd.Timestamp(episode.portfolio_peak_date), end)].copy()
        peak_value = float(curve_indexed.loc[pd.Timestamp(episode.portfolio_peak_date), "portfolio_value"])
        for curve_row in period.itertuples(index=False):
            date = pd.Timestamp(curve_row.date)
            family = str(curve_row.holdings).split(";")[0] if str(curve_row.holdings) else ""
            weekly_position = weekly_dates.searchsorted(date, side="right") - 1
            weekly_asof = pd.Timestamp(weekly_dates[weekly_position]) if weekly_position >= 0 else pd.NaT
            technical = daily.loc[(date, family)] if family and (date, family) in daily.index else pd.Series(dtype=object)
            feature = weekly_indexed.loc[(weekly_asof, family)] if family and pd.notna(weekly_asof) and (weekly_asof, family) in weekly_indexed.index else pd.Series(dtype=object)
            entry = pd.Timestamp(curve_row.holding_entry_date_asof)
            family_values = data.base.research.wealth.loc[entry:date, family].dropna() if family in data.base.research.wealth.columns else pd.Series(dtype=float)
            entry_value = data.base.research.wealth.loc[entry, family] if family in data.base.research.wealth.columns and entry in data.base.research.wealth.index else np.nan
            mfe = float(family_values.max() / entry_value - 1.0) if len(family_values) and pd.notna(entry_value) else np.nan
            challengers = [value for value in crossover_by_date.get(weekly_asof, "").split(";") if value and value != family]
            rows.append({
                "drawdown_episode_id": episode.drawdown_episode_id,
                "date": date,
                "state_frequency": "DAILY_WITH_LAST_WEEKLY_SIGNAL_ASOF",
                "weekly_signal_asof_date": weekly_asof,
                "is_weekly_observation_date": bool(date == weekly_asof),
                "portfolio_peak_date": episode.portfolio_peak_date,
                "trough_date": episode.trough_date,
                "recovery_date": episode.recovery_date,
                "portfolio_value": float(curve_row.portfolio_value),
                "portfolio_drawdown_from_episode_peak": float(curve_row.portfolio_value / peak_value - 1.0),
                "economic_exposure_family_id": family,
                "holding_entry_date_asof": entry,
                "slow_rank": feature.get("SLOW_ORDINAL_RANK", np.nan),
                "fast_rank": feature.get("FAST_ORDINAL_RANK", np.nan),
                "RS21": feature.get("RS_21", np.nan),
                "RS42": feature.get("RS_42", np.nan),
                "RS63": feature.get("RS_63", np.nan),
                "RS126": feature.get("RS_126", np.nan),
                "RS252": feature.get("RS_252", np.nan),
                "relative_price_line_slope_42": feature.get("RELATIVE_SLOPE_42", np.nan),
                "absolute_total_return_index": technical.get("INDEX_GBP_TOTAL_RETURN", np.nan),
                "distance_from_ema21": technical.get("ABS_DISTANCE_EMA_21", np.nan),
                "distance_from_ema50": technical.get("ABS_DISTANCE_EMA_50", np.nan),
                "distance_from_ema200": technical.get("ABS_DISTANCE_EMA_200", np.nan),
                "realised_volatility_63": technical.get("REALISED_VOL_63", np.nan),
                "volatility_expansion_ratio": technical.get("VOL_EXPANSION_RATIO", np.nan),
                "atr_status": "NOT_AVAILABLE_NO_VALIDATED_HIGH_LOW_PANEL",
                "maximum_favourable_excursion_since_entry_asof": mfe,
                "remains_slow_rank1": bool(feature.get("SLOW_ORDINAL_RANK", np.nan) == 1),
                "challenger_existed": bool(challengers),
                "challengers": ";".join(challengers),
                "validated_gap_contribution": "NOT_DETERMINABLE_FROM_CLOSE_ONLY_PANEL",
                "daily_data_valid": bool(technical.get("DATA_VALID", False)),
                "warning": core.WARNING,
            })
    return pd.DataFrame(rows).sort_values(["drawdown_episode_id", "date"]).reset_index(drop=True)


def _query_overlay(data: core.A4CData) -> pd.DataFrame:
    frame = data.weekly_features.copy()
    probabilities = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4C_CONVERSION_PROBABILITIES.csv")
    cumulative = probabilities.loc[probabilities["grouping_dimension"].eq("FAST_RANK_CUMULATIVE")].set_index("grouping_value")
    def probability(row: pd.Series, outcome: str) -> float:
        if pd.isna(row["FAST_RS"]):
            return np.nan
        label = "TOP_5_PERCENT" if row["FAST_RS"] >= 0.95 else "TOP_10_PERCENT" if row["FAST_RS"] >= 0.90 else "TOP_20_PERCENT" if row["FAST_RS"] >= 0.80 else ""
        return float(cumulative.loc[label, outcome]) if label and label in cumulative.index else np.nan
    frame["PROBABILITY_SLOW_TOP3_8W"] = frame.apply(lambda row: probability(row, "probability_slow_top3_8w"), axis=1)
    frame["PROBABILITY_SLOW_RANK1_8W"] = frame.apply(lambda row: probability(row, "probability_slow_top1_8w"), axis=1)
    frame["ABSOLUTE_TREND_STATE"] = np.select(
        [frame["ABS_BELOW_EMA200"].fillna(False), frame["ABS_BELOW_EMA50"].fillna(False), frame["ABS_BELOW_EMA21"].fillna(False)],
        ["BELOW_EMA200", "BELOW_EMA50", "BELOW_EMA21_WARNING"], default="ABOVE_EMA21_50_200",
    )
    floor = float(data.policy["formation_features"]["volatility_floor_annualised"])
    for target in (0.10, 0.125, 0.15):
        frame[f"IMPLIED_RISK_WEIGHT_{str(target).replace('.', '_')}"] = (target / frame["REALISED_VOL_63"].clip(lower=floor)).clip(upper=1.0)
    leaders = core.monthly_leaders(data).rename(columns={"monthly_review_date": "leader_review_date", "incumbent_family": "CURRENT_SLOW_LEADER"})
    dates = pd.DataFrame({"date": sorted(pd.DatetimeIndex(frame["date"].unique()))})
    dated_leaders = pd.merge_asof(dates, leaders[["leader_review_date", "CURRENT_SLOW_LEADER"]].sort_values("leader_review_date"), left_on="date", right_on="leader_review_date", direction="backward")
    frame = frame.merge(dated_leaders[["date", "CURRENT_SLOW_LEADER"]], on="date", how="left", validate="many_to_one")
    frame["IS_CURRENT_SLOW_LEADER"] = frame["economic_exposure_family_id"].eq(frame["CURRENT_SLOW_LEADER"])
    frame["A4C_PROMOTED_ARCHITECTURE"] = PROMOTED
    frame["A4C_CURRENT_ACTIVE_ALLOCATION"] = np.where(frame["IS_CURRENT_SLOW_LEADER"], 0.50, 0.0)
    frame["A4C_CURRENT_CORE_ALLOCATION"] = 0.50
    frame["A4C_CURRENT_CASH_ALLOCATION"] = 0.0
    frame["WARNING"] = core.WARNING
    columns = [
        "date", "economic_exposure_family_id", "FAST_RS", "SLOW_RS", "FAST_ORDINAL_RANK", "SLOW_ORDINAL_RANK", "FAST_MINUS_SLOW",
        "FAST_RS_CHANGE_1W", "FAST_RS_CHANGE_4W", "FAST_CROSSOVER_PRIMARY", "FAST_CROSSOVER_PERSISTENCE_PRIMARY",
        "PROBABILITY_SLOW_TOP3_8W", "PROBABILITY_SLOW_RANK1_8W", "ABSOLUTE_TREND_STATE", "ABS_BELOW_EMA21", "ABS_BELOW_EMA50",
        "REALISED_VOL_63", "IMPLIED_RISK_WEIGHT_0_1", "IMPLIED_RISK_WEIGHT_0_125", "IMPLIED_RISK_WEIGHT_0_15",
        "CURRENT_SLOW_LEADER", "IS_CURRENT_SLOW_LEADER", "A4C_PROMOTED_ARCHITECTURE", "A4C_CURRENT_ACTIVE_ALLOCATION",
        "A4C_CURRENT_CORE_ALLOCATION", "A4C_CURRENT_CASH_ALLOCATION", "WARNING",
    ]
    return frame[columns].sort_values(["date", "economic_exposure_family_id"]).reset_index(drop=True)


def _correctness_tests(
    data: core.A4CData,
    baseline: Any,
    all_simulations: dict[str, Any],
    query_overlay: pd.DataFrame,
) -> pd.DataFrame:
    tests: list[dict[str, Any]] = []
    def add(test_id: str, passed: bool, evidence: str) -> None:
        tests.append({"test_id": test_id, "result": "PASS" if bool(passed) else "FAIL", "evidence": evidence, "warning": core.WARNING})
    reproduction = core.exact_baseline_reproduction(baseline)
    add("A4_BASELINE_EXACT_REPRODUCTION", reproduction["result"].eq("PASS").all(), f"max_abs_diff={reproduction['absolute_difference'].max():.3g}")
    all_trades = pd.concat([simulation.trades.assign(test_module=module_id) for module_id, simulation in all_simulations.items()], ignore_index=True)
    executed = all_trades.loc[all_trades["execution_status"].eq("EXECUTED")]
    add("NO_SAME_CLOSE_EXECUTION", (pd.to_datetime(executed["execution_date"]) > pd.to_datetime(executed["review_date"])).all() and ~executed["same_close_execution"].astype(bool).any(), f"executed_rows={len(executed)}")
    a2_dates = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A2R2_CORRECTED_SIGNAL_ELIGIBILITY.parquet", columns=["date"])["date"].drop_duplicates().sort_values()
    add("CORRECTED_XLON_CALENDAR_RETAINED", pd.DatetimeIndex(a2_dates).equals(data.base.research.calendar), f"sessions={len(a2_dates)}")
    weekly = data.weekly_features
    fast_diff = (weekly["FAST_RS"] - weekly[["RANK_RS_21", "RANK_RS_42", "RANK_RS_63"]].mean(axis=1, skipna=False)).abs().max()
    slow_diff = (weekly["SLOW_RS"] - weekly[["RANK_RS_63", "RANK_RS_126", "RANK_RS_252"]].mean(axis=1, skipna=False)).abs().max()
    add("FAST_SLOW_CALCULATIONS_CORRECT", max(float(fast_diff), float(slow_diff)) < 1e-12, f"max_abs_diff={max(float(fast_diff), float(slow_diff)):.3g}")
    trajectories = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4C_PRE_LEADER_TRAJECTORIES.csv", parse_dates=["observation_date", "target_slow_rank1_date"])
    add("PRE_LEADER_TRAJECTORY_USES_ONLY_PRIOR_OR_CURRENT_DATA", (trajectories["observation_date"] <= trajectories["target_slow_rank1_date"]).all(), f"rows={len(trajectories)}")
    rules = data.policy["fast_crossover"]["PRIMARY"]
    recomputed = weekly["FAST_RS"].ge(rules["fast_percentile_min"]) & weekly["FAST_MINUS_SLOW"].ge(rules["fast_minus_slow_min"]) & weekly["FAST_RS_CHANGE_4W"].ge(rules["fast_change_4w_min"]) & weekly["RS_63"].gt(0) & weekly["RELATIVE_SLOPE_42"].gt(0) & weekly["DATA_VALID"].fillna(False)
    add("CROSSOVER_RULE_FROZEN_AND_CURRENT_ONLY", recomputed.equals(weekly["FAST_CROSSOVER_PRIMARY"]), f"rows={len(weekly)}")
    add("CONVERSION_OUTCOME_NOT_IN_CROSSOVER_SIGNAL", not any("FUTURE" in key.upper() for key in rules), "policy inputs are contemporaneous FAST/gap/change/RS63/slope42 only")
    early_results = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4C_EARLY_PARTICIPATION_RESULTS.csv")
    early_scouts = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4C_SCOUT_EPISODES.csv")
    add("SCOUT_TOTAL_EXPOSURE_NO_GREATER_THAN_100PCT", early_scouts["maximum_allocation"].le(1.0 + 1e-12).all(), f"max_scout={early_scouts['maximum_allocation'].max():.3f}")
    max_holdings = max(int(sim.curve["holding_count"].max()) for module_id, sim in all_simulations.items() if module_id.startswith("EARLY_"))
    add("SCOUT_MAXIMUM_TWO_RISKY_HOLDINGS", max_holdings <= 2, f"max_holding_count={max_holdings}")
    exit_modules = [module for module in all_simulations if module.startswith("EXIT_")]
    exit_trades = pd.concat([all_simulations[module].trades for module in exit_modules], ignore_index=True)
    exit_executed = exit_trades.loc[exit_trades["execution_status"].eq("EXECUTED")]
    add("TREND_EXITS_EXECUTE_NEXT_VALID_SESSION", (pd.to_datetime(exit_executed["execution_date"]) > pd.to_datetime(exit_executed["review_date"])).all(), f"exit_trade_rows={len(exit_executed)}")
    vol_decisions = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4C_VOLATILITY_POSITION_HISTORY.csv")
    positive_vol_targets = vol_decisions.loc[vol_decisions["target_risky_weight"].gt(0)].copy()
    missing_vol_targets = vol_decisions.loc[vol_decisions["prior_realised_vol_63"].isna()].copy()
    executable_vol_decisions = vol_decisions.loc[~vol_decisions["execution_status"].str.startswith("CANCELLED")].copy()
    cancelled_vol_decisions = vol_decisions.loc[vol_decisions["execution_status"].str.startswith("CANCELLED")].copy()
    vol_prior_only = (
        (pd.to_datetime(executable_vol_decisions["execution_date"]) > pd.to_datetime(executable_vol_decisions["review_date"])).all()
        and cancelled_vol_decisions["execution_date"].isna().all()
        and positive_vol_targets["prior_realised_vol_63"].notna().all()
        and missing_vol_targets["target_risky_weight"].eq(0).all()
    )
    add("VOLATILITY_SIZING_PRIOR_ONLY", vol_prior_only, f"decisions={len(vol_decisions)} executable={len(executable_vol_decisions)} cancelled_at_panel_end={len(cancelled_vol_decisions)} positive_targets={len(positive_vol_targets)} missing_vol_cash_only={len(missing_vol_targets)}")
    target_rows = pd.concat([simulation.targets.assign(test_module=module_id) for module_id, simulation in all_simulations.items()], ignore_index=True)
    add("NO_LEVERAGE", target_rows["target_risky_weight"].le(1.0 + 1e-12).all(), f"max_target={target_rows['target_risky_weight'].max():.12f}")
    vol_sim = all_simulations["VOL_TARGET_0_125"]
    curve = vol_sim.curve.copy().sort_values("date")
    curve["prior_cash_value"] = curve["cash_value"].shift(1)
    curve["prior_date"] = curve["date"].shift(1)
    sample = curve.loc[curve["cash_fraction"].gt(0) & ~curve["execution_event"]].dropna(subset=["prior_cash_value", "prior_date"]).head(100)
    cash_errors = []
    for row in sample.itertuples(index=False):
        expected = data.base.cash_index.loc[pd.Timestamp(row.date)] / data.base.cash_index.loc[pd.Timestamp(row.prior_date)]
        cash_errors.append(abs(row.cash_value / row.prior_cash_value - expected))
    add("RESIDUAL_WEIGHT_EARNS_VALIDATED_GBP_CASH", bool(cash_errors) and max(cash_errors) < 1e-12, f"sample={len(cash_errors)} max_diff={max(cash_errors) if cash_errors else np.nan:.3g}")
    core_sim = all_simulations[PROMOTED]
    core_trade = core_sim.trades.loc[core_sim.trades["execution_status"].eq("EXECUTED") & core_sim.trades["trade_legs"].gt(0)].iloc[0]
    expected_cost = core_trade["pre_trade_portfolio_value"] * core_trade["traded_notional_fraction"] * 20.0 / 10_000.0 + core_trade["trade_legs"] * 3.99 / 250_000.0
    add("CORE_SATELLITE_REBALANCE_COST_CORRECT", abs(float(core_trade["transaction_cost_value"]) - expected_cost) < 1e-12, f"difference={abs(float(core_trade['transaction_cost_value'])-expected_cost):.3g}")
    source_text = "\n".join((PROGRAMME_ROOT / "code" / name).read_text(encoding="utf-8") for name in ["ukactive_a4c_core.py", "build_ukactive_a4c_early.py", "build_ukactive_a4c_risk.py", "build_ukactive_a4c_core_satellite.py"])
    add("CURRENT_II_STATUS_NOT_USED_OR_BACK_PROJECTED", "II_CURRENT_TRADABLE" not in source_text, "A4C engines contain no ii field")
    registry = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4C_MODULE_REGISTRY.csv")
    expected_families = {"EARLY_A", "EARLY_B", "EARLY_C", "EXIT_A_50EMA", "EXIT_B_21_WARNING_50_FAILURE", "EXIT_C_ABSOLUTE_AND_RELATIVE", "EXIT_D_RELATIVE_ONLY", "VOL_TARGET_10", "VOL_TARGET_12_5", "VOL_TARGET_15", "CORE_ACTIVE_25", "CORE_ACTIVE_50", "CORE_ACTIVE_75", "CORE_ACTIVE_100"}
    add("EVERY_TESTED_MODULE_REGISTERED", expected_families.issubset(set(registry["module_id"])), f"registered={len(registry)}")
    add("FAILED_MODULES_RETAINED", len(early_results) == 9 and len(pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4C_TREND_EXIT_RESULTS.csv")) == 4 and len(pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4C_VOLATILITY_TARGET_RESULTS.csv")) == 3, "9 early + 4 exit + 3 volatility rows retained")
    add("NO_FORWARD_FILLED_OR_STALE_VALUES_INTRODUCED", data.daily_technical.loc[data.daily_technical["DATA_VALID"].eq(False), "INDEX_GBP_TOTAL_RETURN"].isna().all(), "invalid endpoints remain NaN")
    add("QUERY_OVERLAY_REPRODUCES_FEATURES", len(query_overlay) == len(weekly) and query_overlay[["date", "economic_exposure_family_id"]].duplicated().sum() == 0, f"rows={len(query_overlay)}")
    latest_parts = [query_engine.build_snapshot("latest", pool)[0] for pool in ("industry", "theme")]
    latest_query = pd.concat(latest_parts, ignore_index=True)
    latest_overlay = query_overlay.loc[query_overlay["date"].eq(query_overlay["date"].max()), ["economic_exposure_family_id", "FAST_ORDINAL_RANK", "SLOW_ORDINAL_RANK"]]
    query_check = latest_query.merge(latest_overlay, on="economic_exposure_family_id", how="inner", validate="one_to_one")
    query_diff = max(
        (query_check["fast_rank"].astype(float) - query_check["FAST_ORDINAL_RANK"].astype(float)).abs().max(),
        (query_check["slow_rank"].astype(float) - query_check["SLOW_ORDINAL_RANK"].astype(float)).abs().max(),
    )
    add("CURRENT_QUERY_REPRODUCES_A4C_OVERLAY", len(query_check) == len(latest_overlay) and float(query_diff) < 1e-12, f"families={len(query_check)} max_rank_diff={query_diff:.3g}")
    historical_query, _ = query_engine.build_snapshot("2025-08-22", "industry")
    history_safe = historical_query["a4c_current_active_allocation"].isna().all() and historical_query["a4c_current_core_allocation"].isna().all() and historical_query["II_CURRENT_TRADABLE"].eq("NOT_APPLICABLE_HISTORICAL_ASOF").all()
    add("HISTORICAL_QUERY_DOES_NOT_BACK_PROJECT_A4C_OR_II", history_safe, f"rows={len(historical_query)}")
    return pd.DataFrame(tests)


def _data_quality_report(correctness: pd.DataFrame, contribution: pd.DataFrame) -> None:
    lines = [
        "# UKACTIVE-A4C data-quality report", "", core.RESEARCH_WARNING, "",
        f"Correctness harness: {int(correctness['result'].eq('PASS').sum())}/{len(correctness)} PASS.",
        f"Maximum core/active contribution reconciliation error: {contribution['reconciliation_difference'].abs().max():.3g}.",
        "The corrected A2R2 XLON calendar, endpoint continuity, missing/stale invalidation, total-return accounting and next-session execution contract remain authoritative. A4C adds no price, return, universe member or external signal.",
        "No validated next-open/high/low panel exists for this stage. ATR and executable opening-gap attribution are therefore not fabricated; the volatility-expansion proxy is explicitly labelled.",
        "Historical UK retail, ISA, account and broker eligibility remains partly unresolved and no current ii status is back-projected.",
    ]
    (PROGRAMME_ROOT / "UKACTIVE_A4C_DATA_QUALITY_REPORT.md").write_text("\n\n".join(lines) + "\n", encoding="utf-8")


def _director_review(
    core_results: pd.DataFrame,
    early: pd.DataFrame,
    exits: pd.DataFrame,
    vol: pd.DataFrame,
    rolling: pd.DataFrame,
    dependency: pd.DataFrame,
) -> None:
    chosen = core_results.loc[core_results["module_id"].eq(PROMOTED)].iloc[0]
    rolling50 = rolling.loc[rolling["module_id"].eq(PROMOTED) & rolling["record_type"].eq("ROLLING_12M")]
    top3_removed = dependency.loc[(dependency["module_id"].eq(PROMOTED)) & dependency["dependency_test"].eq("REMOVE_TOP3_CONTRIBUTORS")].iloc[0]
    lines = [
        "# UKACTIVE-A4C research-director review", "", core.RESEARCH_WARNING, "",
        "## A. What we now know", "",
        f"The frozen active sleeve still reproduces exactly, but its -30.90% drawdown is not repaired by the preregistered scout, trend-exit or standalone volatility modules. A fixed 50% active / 50% global-developed core is the strongest qualifying portfolio construction: {chosen['net_cagr']:.2%} net CAGR, {chosen['maximum_drawdown']:.2%} maximum drawdown and {chosen['calmar_mar']:.2f} Calmar in the final five years.", "",
        "## B. What we can rule out", "",
        "The three frozen fast-crossover scout ladders do not add net wealth; the four deterioration exits have negative net exit value and substantial whipsaw; 10%/12.5%/15% standalone volatility targets suppress too much right-tail contribution to qualify. A4B profit-taking and regime rules remain rejected and were not retested.", "",
        "## C. What looks economically interesting", "",
        "Fast leadership is predictive of migration into slow leadership, but conversion does not automatically become a profitable handover rule. Direct volatility scaling cleanly lowers drawdown, showing that exposure amplitude is a real risk mechanism even though the tested targets sacrifice too much edge. Strategic diversification is more efficient: the 50/50 blend preserves half the active engine while recycling gains into a distinct global core.", "",
        "## D. What new edge hypotheses the data suggest", "",
        "The principal supported adjacent hypothesis is portfolio interaction rather than a new selection or exit rule: a concentrated positively skewed active sleeve may be economically useful as a bounded satellite. The migration probability surface remains an E1 mechanism hypothesis for future prospective entry design, not a promoted rule.", "",
        "## E. Evidence status", "",
        "All portfolio results are E2 developmental. Migration, warning-clock and monetisation diagnostics are E1 exploratory. Nothing is E3.", "",
        "## F. Highest-value next discrimination test", "",
        "Freeze the unchanged A4 baseline V1 and the 50/50 core-satellite construction as parallel shadow comparators on genuinely new monthly decisions. Do not add the failed early, exit or volatility modules. The 50/50 candidate must be evaluated with current-ii implementation controls before any capital claim.", "",
        "## G. Is further research worth the compute and time?", "",
        f"Yes, prospectively and at low incremental compute cost. The candidate remains dependent on the active right tail: removing the three historical leaders leaves the 50/50 variant at {top3_removed['net_cagr']:.2%} CAGR and {top3_removed['net_excess_vs_global']:.2%} global excess. Its positive rolling-12-month frequency is {rolling50['positive_return'].mean():.1%}. This is sufficient to justify a shadow comparison, not deployment.",
    ]
    (PROGRAMME_ROOT / "UKACTIVE_A4C_RESEARCH_DIRECTOR_REVIEW.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _manifest(output_paths: list[Path], correctness: pd.DataFrame, unresolved: pd.DataFrame) -> None:
    inputs = [
        PROGRAMME_ROOT / "UKACTIVE_A2R2_CORRECTED_TOTAL_RETURN_PANEL_GBP.parquet",
        PROGRAMME_ROOT / "UKACTIVE_A2R2_CORRECTED_SIGNAL_ELIGIBILITY.parquet",
        PROGRAMME_ROOT / "UKACTIVE_A4_TOP1_TOP2_TOP3_COMPARISON.csv",
        PROGRAMME_ROOT / "UKACTIVE_A4B_DECISION.json",
        POLICY_PATH := PROGRAMME_ROOT / "config" / "UKACTIVE_A4C_POLICY_v1.json",
    ]
    code_paths = sorted((PROGRAMME_ROOT / "code").glob("*a4c*.py")) + [PROGRAMME_ROOT / "code" / "query_ukactive_rotation.py"]
    excluded_inventory_path = PROGRAMME_ROOT / "UKACTIVE_GIT_EXCLUDED_DATA_INVENTORY.csv"
    excluded_inventory = pd.read_csv(excluded_inventory_path)
    a4c_excluded = excluded_inventory.loc[excluded_inventory["relative_path"].str.contains("UKACTIVE_A4C_", case=False, na=False)]
    payload = {
        "stage_id": "UKACTIVE-A4C", "run_id": "UKACTIVE-A4C-20260823-001", "decision": DECISION,
        "generated_utc": datetime.now(timezone.utc).isoformat(), "repository_root": str(REPO_ROOT), "branch": _git("branch", "--show-current"),
        "build_parent_commit": _git("rev-parse", "HEAD"), "preflight_tag": "ukactive-a4c-preflight-20260823",
        "preflight_commit": "d18fef020bb0082ac199b7a202f90882e23b1bbd", "preregistration_commit": "f344677ff506f87e9b3f99592823d73d17c3b29f",
        "engine_freeze_commit": "6bffdadc78e49517606a48b10f853ec7ab6941f3", "early_rotation_commit": "aa448860e6044f5b9e38e745db345832c2c8c3e0",
        "risk_control_commit": "7112302367e8dc6d47b054a10d76be2951573aa7", "core_satellite_commit": "164d84522081ee84c6347aab508b43740035e25c",
        "final_result_commit": "PENDING_POST_OUTPUT_COMMIT", "git_remote": _git("remote", "get-url", "origin"),
        "git_status_at_generation": _git("status", "--porcelain"),
        "evidence_level": "E2_DEVELOPMENTAL", "mechanism_evidence_level": "E1_EXPLORATORY", "independent_confirmation": False,
        "input_hashes": {str(path.relative_to(PROGRAMME_ROOT)): _sha256(path) for path in inputs},
        "code_hashes": {str(path.relative_to(PROGRAMME_ROOT)): _sha256(path) for path in code_paths},
        "output_hashes": {str(path.relative_to(PROGRAMME_ROOT)): _sha256(path) for path in output_paths if path.exists() and path.name != "UKACTIVE_A4C_MANIFEST.json"},
        "package_versions": {"python": platform.python_version(), **{name: importlib.metadata.version(name) for name in ["numpy", "pandas", "pyarrow"]}},
        "executed_commands": [
            "python code/build_ukactive_a4c_early.py",
            "python code/build_ukactive_a4c_risk.py",
            "python code/build_ukactive_a4c_core_satellite.py",
            "python code/finalize_ukactive_a4c.py",
            "python code/build_git_excluded_data_inventory.py",
            "python code/query_ukactive_rotation.py --asof latest --pool industry --top 3",
            "python code/query_ukactive_rotation.py --asof 2025-08-22 --pool industry --top 1",
        ],
        "excluded_data_inventory": {
            "path": str(excluded_inventory_path.relative_to(PROGRAMME_ROOT)),
            "sha256": _sha256(excluded_inventory_path),
            "record_count": int(len(excluded_inventory)),
            "a4c_record_count": int(len(a4c_excluded)),
            "a4c_records": a4c_excluded.to_dict(orient="records"),
        },
        "policy_path": str(POLICY_PATH), "correctness_tests": correctness.to_dict(orient="records"),
        "unresolved_items": unresolved.to_dict(orient="records"), "a5_started": False,
        "warning": core.WARNING,
    }
    (PROGRAMME_ROOT / "UKACTIVE_A4C_MANIFEST.json").write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> None:
    data = core.load_a4c_data()
    comparators = core.comparator_curves(data)
    baseline_plan = core.build_baseline_plan(data)
    baseline = core.simulate(baseline_plan, data)
    if not core.exact_baseline_reproduction(baseline)["result"].eq("PASS").all():
        raise AssertionError("A4 baseline did not reproduce")

    simulations: dict[str, Any] = {"A4_BASELINE": baseline}
    for architecture in ("EARLY_A", "EARLY_B", "EARLY_C"):
        plan = core.build_early_plan(data, architecture)
        simulations[architecture] = core.simulate(plan, data)
    for module_id in ("EXIT_A_50EMA", "EXIT_B_21_WARNING_50_FAILURE", "EXIT_C_ABSOLUTE_AND_RELATIVE", "EXIT_D_RELATIVE_ONLY"):
        simulations[module_id] = core.simulate(core.build_exit_plan(data, module_id), data)
    for target in (0.10, 0.125, 0.15):
        plan = core.build_volatility_plan(data, target)
        simulations[plan.module_id] = core.simulate(plan, data)
    for weight in (0.25, 0.50, 0.75, 1.0):
        plan = core.build_core_satellite_plan(data, weight)
        simulations[plan.module_id] = core.simulate(plan, data)

    ablation_rows = []
    early_results = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4C_EARLY_PARTICIPATION_RESULTS.csv")
    exit_results = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4C_TREND_EXIT_RESULTS.csv")
    vol_results = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4C_VOLATILITY_TARGET_RESULTS.csv")
    core_results = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4C_CORE_SATELLITE_RESULTS.csv")
    base_metrics = core.metric_row(baseline, data, "A4_BASELINE", comparators=comparators)
    ablation_rows.append({"module_id": "A4_BASELINE", "module_family": "BASELINE", "independently_qualifies": False, "qualification_reason": "CONTROL_FAILS_MINUS_25PCT_ACTIVE_DRAWDOWN_WARNING", **base_metrics})
    for row in early_results.loc[early_results["crossover_variant"].eq("PRIMARY")].to_dict(orient="records"):
        ablation_rows.append({"module_id": row["architecture"], "module_family": "EARLY_PARTICIPATION", "independently_qualifies": False, "qualification_reason": "NEGATIVE_NET_EARLY_PARTICIPATION_VALUE", **row})
    for row in exit_results.to_dict(orient="records"):
        ablation_rows.append({"module_id": row["module_id"], "module_family": "TREND_EXIT", "independently_qualifies": bool(row["passes_exit_promotion_gate"]), "qualification_reason": "PASS" if row["passes_exit_promotion_gate"] else "NEGATIVE_NET_EXIT_VALUE_OR_GATE_FAILURE", **row})
    for row in vol_results.to_dict(orient="records"):
        ablation_rows.append({"module_id": row["module_id"], "module_family": "VOLATILITY_SIZING", "independently_qualifies": bool(row["passes_volatility_promotion_gate"]), "qualification_reason": "PASS" if row["passes_volatility_promotion_gate"] else "RIGHT_TAIL_RETENTION_OR_EXCESS_GATE_FAILURE", **row})
    for row in core_results.to_dict(orient="records"):
        ablation_rows.append({"module_id": row["module_id"], "module_family": "CORE_SATELLITE", "independently_qualifies": bool(row["passes_core_satellite_promotion_gate_pre_rolling"]), "qualification_reason": "PASS_PRE_ROLLING" if row["passes_core_satellite_promotion_gate_pre_rolling"] else "CONTROL_OR_GATE_FAILURE", **row})
    ablation = pd.DataFrame(ablation_rows)

    combined_rows = []
    for row in core_results.to_dict(orient="records"):
        combined_rows.append({"architecture_id": row["module_id"], "execution_status": "EXECUTED_FIXED_CORE_SATELLITE", "entered_modules": "A4_BASELINE_ACTIVE_SLEEVE;GLOBAL_DEVELOPED_WORLD_CORE", "excluded_modules": "EARLY;TREND_EXIT;VOL_TARGET", **row})
    for architecture in ("EARLY_PLUS_EXIT", "EARLY_PLUS_VOLATILITY", "EXIT_PLUS_VOLATILITY", "VOL_SIZED_ACTIVE_INSIDE_CORE"):
        combined_rows.append({"architecture_id": architecture, "execution_status": "NOT_RUN_INDEPENDENT_MODULE_GATE_FAILED", "entered_modules": "NONE", "excluded_modules": architecture, "warning": core.WARNING})
    combined = pd.DataFrame(combined_rows)

    dd_columns = ["module_id", "module_family", "net_cagr", "maximum_drawdown", "calmar_mar", "ulcer_index", "maximum_time_underwater_calendar_days", "percentage_positive_rolling_12m", "net_excess_vs_global", "net_excess_vs_equal_pool", "warning"]
    drawdown = ablation[[column for column in dd_columns if column in ablation.columns]].copy()
    drawdown["passes_minus_25pct_active_warning"] = drawdown["maximum_drawdown"].gt(-0.25)
    drawdown["reaches_preferred_minus_15pct"] = drawdown["maximum_drawdown"].gt(-0.15)

    right_tail = _right_tail_rows(simulations, baseline)
    rolling = _rolling_rows({key: simulations[key] for key in ["A4_BASELINE", "CORE_ACTIVE_25", "CORE_ACTIVE_50", "CORE_ACTIVE_75", "CORE_ACTIVE_100"]})
    years = _year_rows({key: simulations[key] for key in ["A4_BASELINE", "CORE_ACTIVE_25", "CORE_ACTIVE_50", "CORE_ACTIVE_75", "CORE_ACTIVE_100"]})
    dependency = _dependency_rows(data, comparators)
    costs = _cost_rows(data)
    window_results, _ = _window_results(data)
    combined_window = window_results.loc[window_results["module_id"].isin(["A4_BASELINE", "CORE_ACTIVE_25", "CORE_ACTIVE_50", "CORE_ACTIVE_75", "CORE_ACTIVE_100"])].copy()
    combined_window.insert(0, "execution_status", "EXECUTED_FIXED_CORE_SATELLITE")
    combined_window.insert(0, "architecture_id", combined_window["module_id"])
    not_run = combined.loc[combined["execution_status"].eq("NOT_RUN_INDEPENDENT_MODULE_GATE_FAILED")].copy()
    combined_output = pd.concat([combined_window, not_run], ignore_index=True, sort=False)

    _write(ablation, "UKACTIVE_A4C_ABLATION_RESULTS.csv")
    _write(combined_output, "UKACTIVE_A4C_COMBINED_ARCHITECTURES.csv")
    _write(drawdown, "UKACTIVE_A4C_DRAWDOWN_COMPARISON.csv")
    _write(right_tail, "UKACTIVE_A4C_RIGHT_TAIL_RETENTION.csv")
    _write(rolling, "UKACTIVE_A4C_ROLLING_RESULTS.csv")
    _write(years, "UKACTIVE_A4C_YEAR_BY_YEAR_RESULTS.csv")
    _write(dependency, "UKACTIVE_A4C_DEPENDENCY_TESTS.csv")
    _write(costs, "UKACTIVE_A4C_COST_STRESS.csv")

    drawdown_trace = _drawdown_state_trace(data, baseline)
    _write(drawdown_trace, "UKACTIVE_A4C_DRAWDOWN_STATE_TRACE.csv")

    query_overlay = _query_overlay(data)
    query_overlay.to_parquet(PROGRAMME_ROOT / "UKACTIVE_A4C_QUERY_OVERLAY.parquet", index=False)
    correctness = _correctness_tests(data, baseline, simulations, query_overlay)
    _write(correctness, "UKACTIVE_A4C_CORRECTNESS_TEST_RESULTS.csv")
    if not correctness["result"].eq("PASS").all():
        raise AssertionError(f"A4C correctness failure: {correctness.loc[correctness['result'].ne('PASS'), 'test_id'].tolist()}")

    contribution = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A4C_CORE_ACTIVE_CONTRIBUTION.csv")
    _data_quality_report(correctness, contribution)
    _director_review(core_results, early_results, exit_results, vol_results, rolling, dependency)

    module_decisions = pd.DataFrame([
        {"module_family": "EARLY_PARTICIPATION", "best_module": "EARLY_B_PRIMARY_WEEKLY", "decision": "REJECTED", "reason": "Closest scout lost terminal wealth and worsened drawdown; neighbourhood robustness failed.", "evidence_level": "E2_DEVELOPMENTAL", "warning": core.WARNING},
        {"module_family": "TREND_FAILURE_EXIT", "best_module": "EXIT_D_RELATIVE_ONLY", "decision": "REJECTED", "reason": "Negative net exit value and no material drawdown improvement.", "evidence_level": "E2_DEVELOPMENTAL", "warning": core.WARNING},
        {"module_family": "VOLATILITY_SIZING", "best_module": "VOL_TARGET_0_15", "decision": "DRAWDOWN_CONTROL_DIAGNOSTIC_ONLY", "reason": "Drawdown improved, but top-three contribution retention was too low for standalone promotion.", "evidence_level": "E2_DEVELOPMENTAL", "warning": core.WARNING},
        {"module_family": "CORE_SATELLITE", "best_module": PROMOTED, "decision": "RESEARCH_CANDIDATE", "reason": "Material drawdown reduction, higher Calmar and positive excess over global core and equal pool.", "evidence_level": "E2_DEVELOPMENTAL", "warning": core.WARNING},
        {"module_family": "CONTROLLED_COMBINATION", "best_module": PROMOTED, "decision": "CORE_ONLY_COMBINATION", "reason": "No failed early/exit/volatility module was admitted; active selection remains unchanged inside fixed core.", "evidence_level": "E2_DEVELOPMENTAL", "warning": core.WARNING},
    ])
    _write(module_decisions, "UKACTIVE_A4C_MODULE_DECISIONS.csv")

    unresolved = pd.DataFrame([
        {"item_id": "A4C_OPEN_001", "severity": "BLOCKS_DEPLOYMENT_NOT_RESEARCH", "item": "Historical UK retail/ISA/account/broker eligibility remains partly unresolved for active selections.", "owner": "FUTURE_IMPLEMENTATION_RECONSTRUCTION", "warning": core.WARNING},
        {"item_id": "A4C_OPEN_002", "severity": "EVIDENCE_LIMITATION", "item": "All A4C market evidence is E2 developmental and uses previously observed history; no E3 confirmation exists.", "owner": "PROSPECTIVE_A5", "warning": core.WARNING},
        {"item_id": "A4C_OPEN_003", "severity": "RISK_LIMITATION", "item": "The 50/50 candidate remains above the preferred -15% whole-portfolio drawdown range.", "owner": "PROSPECTIVE_A5", "warning": core.WARNING},
        {"item_id": "A4C_OPEN_004", "severity": "DATA_LIMITATION", "item": "Validated next-open/high/low history is unavailable; opening-gap and true ATR diagnostics remain unresolved.", "owner": "FUTURE_DATA_STAGE", "warning": core.WARNING},
        {"item_id": "A4C_OPEN_005", "severity": "MECHANISM_LIMITATION", "item": "Fast-to-slow migration is observable but none of the preregistered scout ladders monetised it robustly.", "owner": "DO_NOT_PROMOTE_WITHOUT_NEW_PREREGISTRATION", "warning": core.WARNING},
    ])
    _write(unresolved, "UKACTIVE_A4C_UNRESOLVED_ITEMS.csv")

    decision = {
        "stage_id": "UKACTIVE-A4C", "decision": DECISION, "primary_candidate": PROMOTED,
        "candidate_definition": "50% A4 frozen INDUSTRY_PLUS_THEME 3/6/12 TOP_1 monthly active sleeve + 50% GLOBAL_DEVELOPED_WORLD; monthly fixed-weight rebalance; canonical costs",
        "early_participation": "REJECTED", "trend_failure_exits": "REJECTED", "standalone_volatility_sizing": "DRAWDOWN_CONTROL_DIAGNOSTIC_ONLY",
        "core_satellite": "RESEARCH_CANDIDATE", "a5_started": False, "a5_recommendation": "FREEZE_BASELINE_V1_AND_CORE_ACTIVE_50_AS_PARALLEL_PROSPECTIVE_SHADOW_COMPARATORS",
        "evidence_level": "E2_DEVELOPMENTAL", "independent_confirmation": False, "warning": core.WARNING,
    }
    (PROGRAMME_ROOT / "UKACTIVE_A4C_DECISION.json").write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")

    output_names = [
        "UKACTIVE_A4C_BASELINE_REPRODUCTION.csv", "UKACTIVE_A4C_DAILY_TECHNICAL_FEATURES.parquet",
        "UKACTIVE_A4C_DRAWDOWN_EPISODES.csv", "UKACTIVE_A4C_DRAWDOWN_ROOT_CAUSE.csv", "UKACTIVE_A4C_WARNING_LEAD_TIMES.csv", "UKACTIVE_A4C_DRAWDOWN_FORENSIC_REPORT.md", "UKACTIVE_A4C_DRAWDOWN_STATE_TRACE.csv",
        "UKACTIVE_A4C_FAST_TO_SLOW_MIGRATION.parquet", "UKACTIVE_A4C_PRE_LEADER_TRAJECTORIES.csv", "UKACTIVE_A4C_CONVERSION_PROBABILITIES.csv", "UKACTIVE_A4C_FAST_CROSSOVER_RESULTS.csv", "UKACTIVE_A4C_FAST_PERSISTENCE_RESULTS.csv", "UKACTIVE_A4C_EARLY_PARTICIPATION_RESULTS.csv", "UKACTIVE_A4C_SCOUT_EPISODES.csv", "UKACTIVE_A4C_NET_EARLY_PARTICIPATION_VALUE.csv", "UKACTIVE_A4C_EARLY_RIGHT_TAIL_CAPTURE.csv",
        "UKACTIVE_A4C_TREND_EXIT_RESULTS.csv", "UKACTIVE_A4C_EXIT_EVENTS.csv", "UKACTIVE_A4C_NET_EXIT_VALUE.csv", "UKACTIVE_A4C_EXIT_RIGHT_TAIL_RETENTION.csv", "UKACTIVE_A4C_EXIT_WHIPSAW_ANALYSIS.csv",
        "UKACTIVE_A4C_VOLATILITY_TARGET_RESULTS.csv", "UKACTIVE_A4C_VOLATILITY_POSITION_HISTORY.csv", "UKACTIVE_A4C_VOLATILITY_SIZING_ATTRIBUTION.csv", "UKACTIVE_A4C_CASH_HISTORY.csv",
        "UKACTIVE_A4C_CORE_SATELLITE_RESULTS.csv", "UKACTIVE_A4C_CORE_SATELLITE_EQUITY_CURVES.parquet", "UKACTIVE_A4C_CORE_ACTIVE_CONTRIBUTION.csv", "UKACTIVE_A4C_STRATEGIC_REBALANCE_MONETISATION.csv",
        "UKACTIVE_A4C_ABLATION_RESULTS.csv", "UKACTIVE_A4C_COMBINED_ARCHITECTURES.csv", "UKACTIVE_A4C_DRAWDOWN_COMPARISON.csv", "UKACTIVE_A4C_RIGHT_TAIL_RETENTION.csv", "UKACTIVE_A4C_ROLLING_RESULTS.csv", "UKACTIVE_A4C_YEAR_BY_YEAR_RESULTS.csv", "UKACTIVE_A4C_DEPENDENCY_TESTS.csv", "UKACTIVE_A4C_COST_STRESS.csv",
        "UKACTIVE_A4C_SCOPE_AND_PREREGISTRATION.md", "UKACTIVE_A4C_MODULE_REGISTRY.csv", "UKACTIVE_A4C_RESEARCH_DIRECTOR_REVIEW.md", "UKACTIVE_A4C_MODULE_DECISIONS.csv", "UKACTIVE_A4C_DATA_QUALITY_REPORT.md", "UKACTIVE_A4C_CORRECTNESS_TEST_RESULTS.csv", "UKACTIVE_A4C_UNRESOLVED_ITEMS.csv", "UKACTIVE_A4C_DECISION.json", "UKACTIVE_A4C_QUERY_OVERLAY.parquet", "UKACTIVE_A3R2Q_QUERY_GUIDE.md",
    ]
    _manifest([PROGRAMME_ROOT / name for name in output_names], correctness, unresolved)


if __name__ == "__main__":
    main()
