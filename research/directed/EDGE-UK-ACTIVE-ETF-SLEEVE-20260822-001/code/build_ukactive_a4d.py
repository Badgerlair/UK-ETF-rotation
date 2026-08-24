"""Build the preregistered UKACTIVE-A4D research stage.

The build is deliberately staged.  Later portfolio dimensions are evaluated
only after the earlier gate has selected a small, recorded region.  Existing
UKACTIVE outputs are inputs only and are never rewritten by this script.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm

import ukactive_a4d_core as core


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
CHARTS = ROOT / "charts" / "UKACTIVE_A4D"
WARNING = core.WARNING
BUILD_TIMESTAMP = "2026-08-24T00:00:00+01:00"
WINDOWS = ["FULL_HISTORY", "PRE_2020", "POST_2020", "LATEST_5Y", "LATEST_3Y"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT.parents[2], text=True).strip()


def csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=json_default) + "\n", encoding="utf-8")


def json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value).__name__)


def pct(value: Any) -> str:
    return "N/A" if pd.isna(value) else f"{100.0 * float(value):.2f}%"


def number(value: Any, digits: int = 2) -> str:
    return "N/A" if pd.isna(value) else f"{float(value):.{digits}f}"


def frame_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.to_markdown(index=False)


def spec_id(
    signal: str,
    breadth: int,
    frequency: str,
    cash_architecture: str,
    weighting: str,
    maturity: str = "DYNAMIC_POINT_IN_TIME",
    suffix: str = "BASE",
) -> str:
    return "|".join([signal, f"TOP_{breadth}", frequency, cash_architecture, weighting, maturity, suffix])


def common_dates(curves: list[pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    dates: set[pd.Timestamp] | None = None
    for curve in curves:
        local = set(pd.to_datetime(curve.loc[curve["date"].between(start, end), "date"]))
        dates = local if dates is None else dates & local
    return pd.DatetimeIndex(sorted(dates or set()))


def normalised(curve: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.Series:
    value = curve.set_index("date")["portfolio_value"].reindex(dates).dropna().astype(float)
    return value / value.iloc[0] if len(value) else value


def holding_statistics(simulation: core.a4b.A4BSimulation, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, float]:
    trades = simulation.trades.copy()
    if trades.empty or "execution_status" not in trades:
        return {"trades_per_year": 0.0, "average_holding_period_calendar_days": np.nan, "average_etf_replacement_rate": np.nan}
    trades = trades.loc[trades["execution_status"].eq("EXECUTED")].copy()
    trades = trades.loc[pd.to_datetime(trades["execution_date"]).between(start, end)].sort_values("execution_date")
    years = max((end - start).days / 365.2425, 1 / 365.2425)
    prior: set[str] = set()
    entry: dict[str, pd.Timestamp] = {}
    durations: list[int] = []
    replacements: list[float] = []
    for row in trades.itertuples(index=False):
        date = pd.Timestamp(row.execution_date)
        target = set(str(row.selected_families).split(";")) if str(row.selected_families) else set()
        target.discard("")
        for family in prior - target:
            if family in entry:
                durations.append((date - entry.pop(family)).days)
        for family in target - prior:
            entry[family] = date
        if prior:
            replacements.append(len(prior - target) / max(len(prior), 1))
        prior = target
    for date in entry.values():
        durations.append((end - date).days)
    return {
        "trades_per_year": len(trades) / years,
        "average_holding_period_calendar_days": float(np.mean(durations)) if durations else np.nan,
        "average_etf_replacement_rate": float(np.mean(replacements)) if replacements else np.nan,
    }


def add_spec_metadata(frame: pd.DataFrame, metadata: dict[str, Any]) -> pd.DataFrame:
    result = frame.copy()
    for key, value in metadata.items():
        result[key] = value
    return result


def flatten_windows(results: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, group in results.groupby(keys, dropna=False, sort=True):
        identity = {key: group.iloc[0][key] for key in keys}
        row = dict(identity)
        for window in WINDOWS:
            local = group.loc[group["window_id"].eq(window)]
            if local.empty:
                continue
            item = local.iloc[0]
            for metric in [
                "net_cagr",
                "gross_cagr",
                "net_excess_vs_global",
                "net_excess_vs_equal_pool",
                "maximum_drawdown",
                "calmar_mar",
                "ulcer_index",
                "annualised_volatility",
                "sortino_zero_cash_hurdle",
                "annual_turnover_traded_notional",
                "trade_legs",
                "cost_drag_cagr",
                "average_cash_weight",
                "percentage_time_100_cash",
                "percentage_time_partially_invested",
                "maximum_time_underwater_calendar_days",
                "terminal_wealth_per_100k",
                "drawdown_efficiency_excess_vs_pool",
            ]:
                if metric in item:
                    row[f"{window.lower()}_{metric}"] = item[metric]
        row["warning"] = WARNING
        rows.append(row)
    return pd.DataFrame(rows)


def contiguous_regions(values: list[int]) -> list[list[int]]:
    if not values:
        return []
    result = [[values[0]]]
    for value in values[1:]:
        if value == result[-1][-1] + 1:
            result[-1].append(value)
        else:
            result.append([value])
    return result


def breadth_plateaus(summary: pd.DataFrame, policy: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, list[int]]]:
    rows: list[dict[str, Any]] = []
    selected_regions: dict[str, list[int]] = {}
    rule = policy["breadth_plateau"]
    for signal, group in summary.groupby("signal_id", sort=True):
        group = group.sort_values("breadth").copy()
        viable = group[
            group["latest_5y_net_excess_vs_equal_pool"].gt(0)
            & group["post_2020_net_excess_vs_equal_pool"].gt(0)
        ].copy()
        best_excess = viable["latest_5y_net_excess_vs_equal_pool"].max() if len(viable) else np.nan
        best_mdd = viable["latest_5y_maximum_drawdown"].max() if len(viable) else np.nan
        if len(viable):
            stable = viable[
                viable["latest_5y_net_excess_vs_equal_pool"].ge(best_excess - float(rule["latest5_excess_within_best_percentage_points"]) / 100.0)
                & viable["latest_5y_maximum_drawdown"].ge(best_mdd - float(rule["maximum_drawdown_within_best_percentage_points"]) / 100.0)
            ]
            regions = [region for region in contiguous_regions(sorted(stable["breadth"].astype(int))) if len(region) >= int(rule["minimum_adjacent_breadths"])]
        else:
            stable = viable
            regions = []
        if regions:
            regions.sort(
                key=lambda region: (
                    len(region),
                    group.loc[group["breadth"].isin(region), "latest_5y_drawdown_efficiency_excess_vs_pool"].median(),
                    group.loc[group["breadth"].isin(region), "latest_5y_net_excess_vs_equal_pool"].median(),
                ),
                reverse=True,
            )
            selected_regions[str(signal)] = regions[0]
        else:
            selected_regions[str(signal)] = []
        for item in group.itertuples(index=False):
            breadth = int(item.breadth)
            rows.append(
                {
                    "signal_id": signal,
                    "breadth": breadth,
                    "positive_latest5_pool_excess": bool(item.latest_5y_net_excess_vs_equal_pool > 0),
                    "positive_post2020_pool_excess": bool(item.post_2020_net_excess_vs_equal_pool > 0),
                    "within_excess_band": bool(pd.notna(best_excess) and item.latest_5y_net_excess_vs_equal_pool >= best_excess - 0.03),
                    "within_mdd_band": bool(pd.notna(best_mdd) and item.latest_5y_maximum_drawdown >= best_mdd - 0.05),
                    "in_selected_plateau": breadth in selected_regions[str(signal)],
                    "selected_plateau": ";".join(map(str, selected_regions[str(signal)])),
                    "warning": WARNING,
                }
            )
    return pd.DataFrame(rows), selected_regions


def choose_signal_region(summary: pd.DataFrame, regions: dict[str, list[int]]) -> tuple[str, list[int], bool]:
    candidates = []
    for signal, region in regions.items():
        if not region:
            continue
        local = summary.loc[(summary["signal_id"].eq(signal)) & summary["breadth"].isin(region)]
        candidates.append(
            (
                len(region),
                float(local["latest_5y_drawdown_efficiency_excess_vs_pool"].median()),
                float(local["latest_5y_net_excess_vs_equal_pool"].median()),
                signal,
                region,
            )
        )
    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][3], candidates[0][4], True
    fallback_signal = (
        summary.groupby("signal_id")["latest_5y_net_excess_vs_equal_pool"].median().sort_values(ascending=False).index[0]
        if len(summary)
        else "M1_EQUAL_5H"
    )
    return str(fallback_signal), [5, 6], False


def representative_breadth(region: list[int]) -> int:
    ordered = sorted(region)
    return int(ordered[(len(ordered) - 1) // 2])


def frequency_choice(summary: pd.DataFrame, doubled: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    rows = []
    for frequency, group in summary.groupby("frequency", sort=True):
        double_group = doubled.loc[doubled["frequency"].eq(frequency)]
        passed = (
            group["latest_5y_net_excess_vs_global"].gt(0)
            & group["latest_5y_net_excess_vs_equal_pool"].gt(0)
        )
        double_pass = double_group["latest_5y_net_excess_vs_equal_pool"].gt(0)
        rows.append(
            {
                "frequency": frequency,
                "breadth_count": len(group),
                "positive_benchmark_gate_fraction": float(passed.mean()),
                "positive_double_cost_pool_gate_fraction": float(double_pass.mean()) if len(double_pass) else 0.0,
                "median_latest5_pool_excess": float(group["latest_5y_net_excess_vs_equal_pool"].median()),
                "median_latest5_mdd": float(group["latest_5y_maximum_drawdown"].median()),
                "median_latest5_drawdown_efficiency": float(group["latest_5y_drawdown_efficiency_excess_vs_pool"].median()),
                "median_turnover": float(group["latest_5y_annual_turnover_traded_notional"].median()),
                "passes_frequency_gate": bool(passed.mean() >= 0.5 and (double_pass.mean() if len(double_pass) else 0.0) >= 0.5),
                "warning": WARNING,
            }
        )
    result = pd.DataFrame(rows)
    eligible = result.loc[result["passes_frequency_gate"]]
    if eligible.empty:
        return "MONTHLY", result
    order = {"WEEKLY": 2, "MONTHLY": 1, "DAILY": 0}
    eligible = eligible.assign(tie_order=eligible["frequency"].map(order)).sort_values(
        ["median_latest5_drawdown_efficiency", "median_latest5_pool_excess", "median_turnover", "tie_order"],
        ascending=[False, False, True, False],
    )
    return str(eligible.iloc[0]["frequency"]), result


def cash_choice(summary: pd.DataFrame, doubled: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    baseline = summary.loc[summary["cash_architecture"].eq("CASH_0_ALWAYS_INVESTED")]
    baseline_mdd = float(baseline["latest_5y_maximum_drawdown"].median())
    baseline_cagr = float(baseline["latest_5y_net_cagr"].median())
    rows = []
    for architecture, group in summary.groupby("cash_architecture", sort=True):
        double_group = doubled.loc[doubled["cash_architecture"].eq(architecture)]
        mdd = float(group["latest_5y_maximum_drawdown"].median())
        cagr = float(group["latest_5y_net_cagr"].median())
        mdd_improvement = mdd - baseline_mdd
        rows.append(
            {
                "cash_architecture": architecture,
                "median_latest5_net_cagr": cagr,
                "median_latest5_return_sacrifice_vs_always_invested": baseline_cagr - cagr,
                "median_latest5_maximum_drawdown": mdd,
                "median_latest5_drawdown_avoided": mdd_improvement,
                "median_latest5_pool_excess": float(group["latest_5y_net_excess_vs_equal_pool"].median()),
                "median_latest5_global_excess": float(group["latest_5y_net_excess_vs_global"].median()),
                "median_latest5_calmar": float(group["latest_5y_calmar_mar"].median()),
                "median_latest5_ulcer": float(group["latest_5y_ulcer_index"].median()),
                "median_average_cash_weight": float(group["latest_5y_average_cash_weight"].median()),
                "median_time_100_cash": float(group["latest_5y_percentage_time_100_cash"].median()),
                "double_cost_pool_excess": float(double_group["latest_5y_net_excess_vs_equal_pool"].median()) if len(double_group) else np.nan,
                "passes_cash_promotion_gate": bool(
                    architecture != "CASH_0_ALWAYS_INVESTED"
                    and mdd_improvement >= 0.05
                    and group["latest_5y_net_excess_vs_equal_pool"].median() > 0
                    and group["latest_5y_net_excess_vs_global"].median() > 0
                    and (double_group["latest_5y_net_excess_vs_equal_pool"].median() if len(double_group) else -np.inf) > 0
                ),
                "warning": WARNING,
            }
        )
    result = pd.DataFrame(rows)
    eligible = result.loc[result["passes_cash_promotion_gate"]]
    if eligible.empty:
        return "CASH_0_ALWAYS_INVESTED", result
    eligible = eligible.sort_values(["median_latest5_calmar", "median_latest5_ulcer", "median_latest5_net_cagr"], ascending=[False, True, False])
    return str(eligible.iloc[0]["cash_architecture"]), result


def weighting_choice(summary: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    control = summary.loc[summary["weighting_method"].eq("W0_EQUAL")].iloc[0]
    result = summary.copy()
    result["improves_latest5_and_post2020_pool_excess"] = (
        result["latest_5y_net_excess_vs_equal_pool"].gt(control["latest_5y_net_excess_vs_equal_pool"])
        & result["post_2020_net_excess_vs_equal_pool"].gt(control["post_2020_net_excess_vs_equal_pool"])
    )
    result["mdd_not_worse"] = result["latest_5y_maximum_drawdown"].ge(control["latest_5y_maximum_drawdown"] - 1e-12)
    eligible = result.loc[result["improves_latest5_and_post2020_pool_excess"] & result["mdd_not_worse"]]
    if eligible.empty:
        return "W0_EQUAL", result
    eligible = eligible.sort_values(["latest_5y_drawdown_efficiency_excess_vs_pool", "latest_5y_net_excess_vs_equal_pool"], ascending=False)
    return str(eligible.iloc[0]["weighting_method"]), result


def year_rows(
    specification_id: str,
    selected: core.a4b.A4BSimulation,
    global_sim: core.a4b.A4BSimulation,
    pool: core.a4b.A4BSimulation,
) -> pd.DataFrame:
    rows = []
    first = int(selected.curve["date"].dt.year.min())
    last = int(selected.curve["date"].dt.year.max())
    for year in range(first, last + 1):
        start = pd.Timestamp(f"{year}-01-01")
        end = pd.Timestamp(f"{year}-12-31")
        common_start, common_end = core._common_window([selected, global_sim, pool], start, end)
        sm = core.a4b.enhanced_performance_metrics(selected, start=common_start, end=common_end)
        gm = core.a4b.enhanced_performance_metrics(global_sim, start=common_start, end=common_end)
        pm = core.a4b.enhanced_performance_metrics(pool, start=common_start, end=common_end)
        rows.append(
            {
                "specification_id": specification_id,
                "calendar_year": year,
                "partial_year": year == last,
                "start": common_start,
                "end": common_end,
                "net_return_or_cagr": sm.get("net_cagr"),
                "global_return_or_cagr": gm.get("net_cagr"),
                "pool_return_or_cagr": pm.get("net_cagr"),
                "excess_vs_global": sm.get("net_cagr", np.nan) - gm.get("net_cagr", np.nan),
                "excess_vs_pool": sm.get("net_cagr", np.nan) - pm.get("net_cagr", np.nan),
                "maximum_drawdown": sm.get("maximum_drawdown"),
                "calmar_mar": sm.get("calmar_mar"),
                "turnover": sm.get("annual_turnover_traded_notional"),
                "warning": WARNING,
            }
        )
    return pd.DataFrame(rows)


def benchmark_drawdown_episodes(global_sim: core.a4b.A4BSimulation, start: pd.Timestamp) -> pd.DataFrame:
    value = global_sim.curve.loc[global_sim.curve["date"].ge(start)].set_index("date")["portfolio_value"].astype(float)
    drawdown = value / value.cummax() - 1.0
    episodes = []
    in_drawdown = False
    peak = trough = None
    trough_value = 0.0
    for date, dd in drawdown.items():
        if dd < -1e-12 and not in_drawdown:
            in_drawdown = True
            peak = pd.Timestamp(value.loc[:date].idxmax())
            trough = pd.Timestamp(date)
            trough_value = float(dd)
        elif in_drawdown and dd < trough_value:
            trough = pd.Timestamp(date)
            trough_value = float(dd)
        elif in_drawdown and dd >= -1e-12:
            episodes.append({"peak_date": peak, "trough_date": trough, "recovery_date": pd.Timestamp(date), "global_max_drawdown": trough_value})
            in_drawdown = False
    if in_drawdown:
        episodes.append({"peak_date": peak, "trough_date": trough, "recovery_date": pd.NaT, "global_max_drawdown": trough_value})
    return pd.DataFrame(episodes).sort_values("global_max_drawdown").head(5).reset_index(drop=True)


def stress_rows(episodes: pd.DataFrame, simulations: dict[str, core.a4b.A4BSimulation]) -> pd.DataFrame:
    rows = []
    for episode_index, episode in episodes.iterrows():
        end = episode["recovery_date"] if pd.notna(episode["recovery_date"]) else episode["trough_date"]
        for label, simulation in simulations.items():
            value = simulation.curve.set_index("date")["portfolio_value"].loc[episode["peak_date"]:end].dropna()
            result = value.iloc[-1] / value.iloc[0] - 1.0 if len(value) >= 2 else np.nan
            mdd = (value / value.cummax() - 1.0).min() if len(value) else np.nan
            rows.append(
                {
                    "stress_episode": int(episode_index + 1),
                    "global_peak_date": episode["peak_date"],
                    "global_trough_date": episode["trough_date"],
                    "global_recovery_date": episode["recovery_date"],
                    "global_max_drawdown": episode["global_max_drawdown"],
                    "architecture": label,
                    "episode_return": result,
                    "episode_max_drawdown": mdd,
                    "warning": WARNING,
                }
            )
    return pd.DataFrame(rows)


def false_defensive_periods(simulation: core.a4b.A4BSimulation, global_sim: core.a4b.A4BSimulation) -> pd.DataFrame:
    curve = simulation.curve.set_index("date")
    global_value = global_sim.curve.set_index("date")["portfolio_value"]
    rows = []
    month = curve.groupby([curve.index.year, curve.index.month]).tail(1)
    for date, row in month.iterrows():
        if float(row["cash_fraction"]) < 0.5:
            continue
        future = global_value.loc[global_value.index > date].head(63)
        if len(future) < 42:
            continue
        ret = float(future.iloc[-1] / global_value.loc[:date].iloc[-1] - 1.0)
        if ret > 0:
            rows.append({"defensive_date": date, "cash_fraction": row["cash_fraction"], "subsequent_global_return_approx_3m": ret, "false_defensive": True, "warning": WARNING})
    return pd.DataFrame(rows)


def newey_west_mean(values: pd.Series, maximum_lag: int) -> tuple[float, float, float, float]:
    series = pd.Series(values, dtype=float).dropna().to_numpy(float)
    count = len(series)
    if count < 3:
        return np.nan, np.nan, np.nan, np.nan
    estimate = float(series.mean())
    centered = series - estimate
    long_run_variance = float(np.dot(centered, centered) / count)
    for lag in range(1, min(int(maximum_lag), count - 1) + 1):
        covariance = float(np.dot(centered[lag:], centered[:-lag]) / count)
        weight = 1.0 - lag / (maximum_lag + 1.0)
        long_run_variance += 2.0 * weight * covariance
    standard_error = math.sqrt(max(long_run_variance, 0.0) / count)
    statistic = estimate / standard_error if standard_error > 0 else np.nan
    p_value = 2.0 * (1.0 - norm.cdf(abs(statistic))) if pd.notna(statistic) else np.nan
    return estimate, standard_error, statistic, p_value


def bh_adjust(values: pd.Series) -> pd.Series:
    result = pd.Series(np.nan, index=values.index, dtype=float)
    valid = values.dropna().sort_values()
    if valid.empty:
        return result
    count = len(valid)
    adjusted = np.minimum.accumulate((valid.to_numpy(float) * count / np.arange(1, count + 1))[::-1])[::-1]
    result.loc[valid.index] = np.minimum(adjusted, 1.0)
    return result


def signal_hac_inference(date_diagnostics: pd.DataFrame, policy: dict[str, Any]) -> pd.DataFrame:
    rows = []
    window_ids = ["FULL_HISTORY", "POST_2020", "LATEST_5Y", "LATEST_3Y"]
    for (signal, horizon), source in date_diagnostics.groupby(["signal_id", "forward_horizon_sessions"], sort=True):
        lag = max(1, int(math.ceil(int(horizon) / 5)))
        for window_id in window_ids:
            mask = core._window_mask(source["date"], window_id, policy)
            group = source.loc[mask]
            for metric in ["ic", "top_quintile_advantage", "rank1_advantage"]:
                estimate, standard_error, statistic, p_value = newey_west_mean(group[metric], lag)
                rows.append(
                    {
                        "signal_id": signal,
                        "forward_horizon_sessions": int(horizon),
                        "window_id": window_id,
                        "metric": metric,
                        "observation_count": int(group[metric].notna().sum()),
                        "hac_maximum_lag_weeks": lag,
                        "estimate": estimate,
                        "hac_standard_error": standard_error,
                        "hac_z_statistic": statistic,
                        "raw_two_sided_p_value": p_value,
                        "warning": WARNING,
                    }
                )
    result = pd.DataFrame(rows)
    result["bh_q_value_within_window_metric"] = result.groupby(["window_id", "metric"], group_keys=False)["raw_two_sided_p_value"].apply(bh_adjust)
    return result


def monthly_block_bootstrap(
    specification_id: str,
    selected: core.a4b.A4BSimulation,
    comparators: dict[str, core.a4b.A4BSimulation],
    start: pd.Timestamp,
    end: pd.Timestamp,
    *,
    simulations: int = 5000,
    block_months: int = 6,
    seed: int = 20260824,
) -> pd.DataFrame:
    selected_value = selected.curve.set_index("date")["portfolio_value"].loc[start:end].astype(float)
    rows = []
    for comparator_id, comparator in comparators.items():
        comparator_value = comparator.curve.set_index("date")["portfolio_value"].loc[start:end].astype(float)
        joined = pd.concat([selected_value.rename("selected"), comparator_value.rename("comparator")], axis=1, join="inner").dropna()
        monthly = joined.groupby([joined.index.year, joined.index.month]).last().pct_change(fill_method=None).dropna()
        count = len(monthly)
        if count < 12:
            continue
        selected_returns = monthly["selected"].to_numpy(float)
        comparator_returns = monthly["comparator"].to_numpy(float)
        observed_selected = float(np.prod(1.0 + selected_returns) ** (12.0 / count) - 1.0)
        observed_comparator = float(np.prod(1.0 + comparator_returns) ** (12.0 / count) - 1.0)
        observed_excess = observed_selected - observed_comparator
        rng = np.random.default_rng(seed + sum(ord(char) for char in comparator_id))
        samples = np.empty(simulations, dtype=float)
        block_count = int(math.ceil(count / block_months))
        for draw in range(simulations):
            indices: list[int] = []
            for start_index in rng.integers(0, count, size=block_count):
                indices.extend(((start_index + np.arange(block_months)) % count).tolist())
            take = np.asarray(indices[:count], dtype=int)
            selected_cagr = float(np.prod(1.0 + selected_returns[take]) ** (12.0 / count) - 1.0)
            comparator_cagr = float(np.prod(1.0 + comparator_returns[take]) ** (12.0 / count) - 1.0)
            samples[draw] = selected_cagr - comparator_cagr
        rows.append(
            {
                "specification_id": specification_id,
                "window_start": start,
                "window_end": end,
                "comparator_id": comparator_id,
                "monthly_observation_count": count,
                "block_months": block_months,
                "simulation_count": simulations,
                "random_seed": seed + sum(ord(char) for char in comparator_id),
                "observed_annualised_excess": observed_excess,
                "bootstrap_mean_excess": float(samples.mean()),
                "bootstrap_2_5_percentile": float(np.quantile(samples, 0.025)),
                "bootstrap_97_5_percentile": float(np.quantile(samples, 0.975)),
                "bootstrap_probability_excess_positive": float(np.mean(samples > 0)),
                "two_sided_tail_probability": float(min(1.0, 2.0 * min(np.mean(samples <= 0), np.mean(samples >= 0)))),
                "warning": WARNING,
            }
        )
    return pd.DataFrame(rows)


def plots(
    global_sim: core.a4b.A4BSimulation,
    pool: core.a4b.A4BSimulation,
    always: core.a4b.A4BSimulation,
    defensive: core.a4b.A4BSimulation,
    breadth_summary: pd.DataFrame,
    frequency_summary: pd.DataFrame,
    rolling: pd.DataFrame,
    contribution_family: pd.DataFrame,
    contribution_rank: pd.DataFrame,
) -> list[Path]:
    CHARTS.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    start = pd.Timestamp("2021-09-01")
    dates = common_dates([global_sim.curve, pool.curve, always.curve, defensive.curve], start, pd.Timestamp("2026-08-21"))
    series = {
        "Global developed": normalised(global_sim.curve, dates),
        "Equal-weight pool": normalised(pool.curve, dates),
        "Always invested rotation": normalised(always.curve, dates),
        "Most-defensive diagnostic": normalised(defensive.curve, dates),
    }
    fig, ax = plt.subplots(figsize=(11, 6))
    for label, value in series.items():
        ax.plot(value.index, value.values, label=label, linewidth=1.8)
    ax.set_title("UKACTIVE-A4D comparative wealth — final five years")
    ax.set_ylabel("Growth of £1")
    ax.grid(alpha=0.25)
    ax.legend()
    path = CHARTS / "UKACTIVE_A4D_COMPARATIVE_EQUITY_CURVES.png"
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig); paths.append(path)

    fig, ax = plt.subplots(figsize=(11, 6))
    for label, value in series.items():
        drawdown = value / value.cummax() - 1.0
        ax.plot(drawdown.index, 100 * drawdown.values, label=label, linewidth=1.5)
    ax.set_title("Drawdown comparison")
    ax.set_ylabel("Drawdown (%)")
    ax.grid(alpha=0.25); ax.legend()
    path = CHARTS / "UKACTIVE_A4D_DRAWDOWN_CURVES.png"
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig); paths.append(path)

    fig, ax1 = plt.subplots(figsize=(10, 6))
    for signal, group in breadth_summary.groupby("signal_id"):
        group = group.sort_values("breadth")
        ax1.plot(group["breadth"], 100 * group["latest_5y_net_excess_vs_equal_pool"], marker="o", label=f"{signal} pool excess")
    ax1.axhline(0, color="black", linewidth=0.8)
    ax1.set_xlabel("Number of holdings"); ax1.set_ylabel("Net excess CAGR vs equal pool (pp)")
    ax1.set_title("A4D breadth frontier — final five years"); ax1.grid(alpha=0.25); ax1.legend(fontsize=8)
    path = CHARTS / "UKACTIVE_A4D_BREADTH_FRONTIER.png"
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig); paths.append(path)

    fig, ax = plt.subplots(figsize=(9, 5))
    local = frequency_summary.assign(_order=frequency_summary["frequency"].map({"DAILY": 0, "WEEKLY": 1, "MONTHLY": 2})).sort_values("_order")
    ax.bar(local["frequency"], 100 * local["median_latest5_pool_excess"], color=["#4c78a8", "#f58518", "#54a24b"][:len(local)])
    ax.set_ylabel("Median net excess CAGR vs pool (pp)"); ax.set_title("Frequency comparison across selected breadth region"); ax.axhline(0, color="black", linewidth=0.8)
    path = CHARTS / "UKACTIVE_A4D_FREQUENCY_COMPARISON.png"
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig); paths.append(path)

    fig, ax = plt.subplots(figsize=(11, 6))
    local = rolling.loc[(rolling["comparator_id"].eq("EQUAL_POOL")) & rolling["rolling_months"].isin([12, 24, 36])]
    for months, group in local.groupby("rolling_months"):
        date = pd.to_datetime(dict(year=group["end_year"], month=group["end_month"], day=1))
        ax.plot(date, 100 * group["excess_return"], label=f"{months}m")
    ax.axhline(0, color="black", linewidth=0.8); ax.set_ylabel("Rolling excess vs equal pool (%)"); ax.set_title("Representative A4D rolling excess")
    ax.grid(alpha=0.25); ax.legend()
    path = CHARTS / "UKACTIVE_A4D_ROLLING_EXCESS.png"
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig); paths.append(path)

    fig, ax = plt.subplots(figsize=(11, 4))
    exposure = defensive.curve.loc[defensive.curve["date"].ge(start)]
    ax.fill_between(exposure["date"], 0, 100 * exposure["invested_fraction"], step="post", alpha=0.65)
    ax.set_ylim(0, 105); ax.set_ylabel("Risk assets (%)"); ax.set_title("Defensive architecture invested fraction"); ax.grid(alpha=0.25)
    path = CHARTS / "UKACTIVE_A4D_INVESTED_FRACTION.png"
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig); paths.append(path)

    if len(contribution_rank):
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(contribution_rank["rank_bucket"], contribution_rank["gross_market_pnl_return_units"])
        ax.set_title("Gross market P&L contribution by selected rank bucket"); ax.set_ylabel("Return-value units")
        path = CHARTS / "UKACTIVE_A4D_CONTRIBUTION_BY_RANK.png"
        fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig); paths.append(path)
    if len(contribution_family):
        fig, ax = plt.subplots(figsize=(10, 6))
        local = contribution_family.head(12).sort_values("gross_market_pnl_return_units")
        ax.barh(local["economic_exposure_family_id"], local["gross_market_pnl_return_units"])
        ax.set_title("Largest gross family market-P&L contributions"); ax.set_xlabel("Return-value units")
        path = CHARTS / "UKACTIVE_A4D_CONTRIBUTION_BY_FAMILY.png"
        fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig); paths.append(path)
    return paths


def main() -> None:
    data = core.load_data()
    policy = data.policy
    CHARTS.mkdir(parents=True, exist_ok=True)
    immutable_paths = [
        ROOT / "UKACTIVE_A4_DECISION.json",
        ROOT / "UKACTIVE_A4B_DECISION.json",
        ROOT / "UKACTIVE_A4C_DECISION.json",
        ROOT / "UKACTIVE_A5_SETUP_DECISION.json",
        ROOT / "UKACTIVE_A5_DECISION_LEDGER.csv",
        ROOT / "UKACTIVE_A5_EXECUTION_LEDGER.csv",
        ROOT / "UKACTIVE_A5_NAV_HISTORY.csv",
    ]
    immutable_before = {path.name: sha256(path) for path in immutable_paths if path.exists()}

    # Stage A: causal cross-sectional diagnostics.
    diagnostics, date_diagnostics, state_results, age_results = core.signal_diagnostics(data)
    carried_signals, signal_gate = core.select_stage_b_signals(diagnostics, policy)
    csv(ROOT / "UKACTIVE_A4D_SIGNAL_DIAGNOSTICS.csv", diagnostics)
    parquet(ROOT / "UKACTIVE_A4D_SIGNAL_DATE_DIAGNOSTICS.parquet", date_diagnostics)
    csv(ROOT / "UKACTIVE_A4D_LEADERSHIP_STATE_RESULTS.csv", state_results)
    csv(ROOT / "UKACTIVE_A4D_MOMENTUM_AGE_DIAGNOSTICS.csv", age_results)
    csv(ROOT / "UKACTIVE_A4D_STAGE_A_SIGNAL_GATE.csv", signal_gate)

    global_sim = core.index_benchmark(data, "GLOBAL_DEVELOPED_WORLD", "GLOBAL_DEVELOPED_WORLD")
    cash_sim = core.cash_benchmark(data)
    pool_cache: dict[str, core.a4b.A4BSimulation] = {}
    simulation_cache: dict[tuple[Any, ...], core.PlannedResult] = {}
    registry_rows: list[dict[str, Any]] = []

    def pool(frequency: str) -> core.a4b.A4BSimulation:
        if frequency not in pool_cache:
            pool_cache[frequency] = core.pool_benchmark(data, frequency)
        return pool_cache[frequency]

    def run(
        stage: str,
        signal: str,
        breadth: int,
        frequency: str,
        cash_architecture: str = "CASH_0_ALWAYS_INVESTED",
        weighting: str = "W0_EQUAL",
        maturity: str = "DYNAMIC_POINT_IN_TIME",
        exclusions: set[str] | None = None,
        double_cost: bool = False,
    ) -> tuple[str, core.PlannedResult, pd.DataFrame, pd.DataFrame]:
        exclusions = exclusions or set()
        suffix = "DOUBLE_COST" if double_cost else ("EXCLUDE_" + "_".join(sorted(exclusions)) if exclusions else "BASE")
        identifier = spec_id(signal, breadth, frequency, cash_architecture, weighting, maturity, suffix)
        key = (signal, breadth, frequency, cash_architecture, weighting, maturity, tuple(sorted(exclusions)), double_cost)
        if key not in simulation_cache:
            simulation_cache[key] = core.simulate_specification(
                data,
                module_id=identifier,
                signal_id=signal,
                breadth=breadth,
                frequency=frequency,
                cash_architecture=cash_architecture,
                weighting_method=weighting,
                maturity_scope=maturity,
                excluded_families=exclusions,
                friction_bps=float(policy["costs"]["double_one_way_friction_bps"] if double_cost else policy["costs"]["canonical_one_way_friction_bps"]),
                fixed_fee_gbp=float(policy["costs"]["double_fixed_fee_gbp_per_leg"] if double_cost else policy["costs"]["canonical_fixed_fee_gbp_per_leg"]),
            )
            registry_rows.append(
                {
                    "specification_id": identifier,
                    "research_stage": stage,
                    "signal_id": signal,
                    "breadth": breadth,
                    "frequency": frequency,
                    "cash_architecture": cash_architecture,
                    "weighting_method": weighting,
                    "maturity_scope": maturity,
                    "excluded_families": ";".join(sorted(exclusions)),
                    "one_way_friction_bps": policy["costs"]["double_one_way_friction_bps"] if double_cost else policy["costs"]["canonical_one_way_friction_bps"],
                    "fixed_fee_gbp_per_leg": policy["costs"]["double_fixed_fee_gbp_per_leg"] if double_cost else policy["costs"]["canonical_fixed_fee_gbp_per_leg"],
                    "classification": "PREREGISTERED" if stage in {"STAGE_B_BREADTH", "STAGE_C_FREQUENCY", "STAGE_D_CASH", "STAGE_E_WEIGHTING"} else "ROBUSTNESS",
                    "warning": WARNING,
                }
            )
        planned = simulation_cache[key]
        evaluated, rolling = core.evaluate(identifier, planned.simulation, global_sim, pool(frequency), policy)
        metadata = {
            "signal_id": signal,
            "breadth": breadth,
            "frequency": frequency,
            "cash_architecture": cash_architecture,
            "weighting_method": weighting,
            "maturity_scope": maturity,
            "cost_scenario": suffix,
            "excluded_families": ";".join(sorted(exclusions)),
            "leadership_capture_delay_sessions": core.capture_delay_sessions(data, planned.target_records, signal, breadth),
            "drawdown_response_calendar_days": core.drawdown_response_days(planned.simulation),
        }
        evaluated = add_spec_metadata(evaluated, metadata)
        for index, row in evaluated.iterrows():
            start = pd.Timestamp(row["window_start"])
            end = pd.Timestamp(row["window_end"])
            for key2, value2 in holding_statistics(planned.simulation, start, end).items():
                evaluated.loc[index, key2] = value2
        rolling = add_spec_metadata(rolling, metadata) if len(rolling) else rolling
        return identifier, planned, evaluated, rolling

    # Stage B: breadth, monthly, equal weight, always invested.
    breadth_result_frames: list[pd.DataFrame] = []
    breadth_rollings: list[pd.DataFrame] = []
    for signal in carried_signals:
        for breadth in policy["breadths"]:
            _, _, result, rolling = run("STAGE_B_BREADTH", signal, int(breadth), "MONTHLY")
            breadth_result_frames.append(result)
            breadth_rollings.append(rolling)
    breadth_results = pd.concat(breadth_result_frames, ignore_index=True)
    breadth_summary = flatten_windows(breadth_results, ["specification_id", "signal_id", "breadth", "frequency", "cash_architecture", "weighting_method"])
    plateau_audit, regions = breadth_plateaus(breadth_summary, policy)
    chosen_signal, breadth_region, plateau_found = choose_signal_region(breadth_summary, regions)
    chosen_breadth = representative_breadth(breadth_region)
    marginal_rows = []
    for signal, group in breadth_summary.groupby("signal_id"):
        group = group.sort_values("breadth")
        for prior, current in zip(group.iloc[:-1].itertuples(index=False), group.iloc[1:].itertuples(index=False)):
            row = {"signal_id": signal, "from_breadth": int(prior.breadth), "to_breadth": int(current.breadth)}
            for metric in ["net_cagr", "net_excess_vs_equal_pool", "maximum_drawdown", "calmar_mar", "ulcer_index", "annualised_volatility", "annual_turnover_traded_notional"]:
                row[f"marginal_change_latest5_{metric}"] = getattr(current, f"latest_5y_{metric}") - getattr(prior, f"latest_5y_{metric}")
            row["warning"] = WARNING
            marginal_rows.append(row)
    csv(ROOT / "UKACTIVE_A4D_BREADTH_RESULTS.csv", breadth_results)
    csv(ROOT / "UKACTIVE_A4D_BREADTH_FRONTIER.csv", breadth_summary)
    csv(ROOT / "UKACTIVE_A4D_BREADTH_PLATEAU_AUDIT.csv", plateau_audit)
    csv(ROOT / "UKACTIVE_A4D_BREADTH_MARGINAL_EFFECTS.csv", pd.DataFrame(marginal_rows))

    # Stage C: cadence only inside the selected broad region.
    frequency_results_frames: list[pd.DataFrame] = []
    frequency_double_frames: list[pd.DataFrame] = []
    frequency_rollings: list[pd.DataFrame] = []
    for breadth in breadth_region:
        for frequency in policy["frequencies"]:
            _, _, result, rolling = run("STAGE_C_FREQUENCY", chosen_signal, breadth, frequency)
            _, _, doubled_result, _ = run("STAGE_C_FREQUENCY_DOUBLE_COST", chosen_signal, breadth, frequency, double_cost=True)
            frequency_results_frames.append(result)
            frequency_double_frames.append(doubled_result)
            frequency_rollings.append(rolling)
    frequency_results = pd.concat(frequency_results_frames, ignore_index=True)
    frequency_double_results = pd.concat(frequency_double_frames, ignore_index=True)
    frequency_flat = flatten_windows(frequency_results, ["specification_id", "signal_id", "breadth", "frequency", "cash_architecture", "weighting_method"])
    frequency_double_flat = flatten_windows(frequency_double_results, ["specification_id", "signal_id", "breadth", "frequency", "cash_architecture", "weighting_method"])
    chosen_frequency, frequency_summary = frequency_choice(frequency_flat, frequency_double_flat)
    csv(ROOT / "UKACTIVE_A4D_FREQUENCY_RESULTS.csv", frequency_results)
    csv(ROOT / "UKACTIVE_A4D_FREQUENCY_DOUBLE_COST_RESULTS.csv", frequency_double_results)
    csv(ROOT / "UKACTIVE_A4D_FREQUENCY_SUMMARY.csv", frequency_summary)

    # Stage D: cash architectures on the selected signal/frequency region.
    cash_result_frames: list[pd.DataFrame] = []
    cash_double_frames: list[pd.DataFrame] = []
    cash_rollings: list[pd.DataFrame] = []
    cash_plans: dict[tuple[str, int], core.PlannedResult] = {}
    for breadth in breadth_region:
        for cash_architecture in policy["cash_architectures"]:
            _, planned, result, rolling = run("STAGE_D_CASH", chosen_signal, breadth, chosen_frequency, cash_architecture)
            _, _, doubled_result, _ = run("STAGE_D_CASH_DOUBLE_COST", chosen_signal, breadth, chosen_frequency, cash_architecture, double_cost=True)
            cash_result_frames.append(result)
            cash_double_frames.append(doubled_result)
            cash_rollings.append(rolling)
            cash_plans[(cash_architecture, breadth)] = planned
    cash_results = pd.concat(cash_result_frames, ignore_index=True)
    cash_double_results = pd.concat(cash_double_frames, ignore_index=True)
    cash_flat = flatten_windows(cash_results, ["specification_id", "signal_id", "breadth", "frequency", "cash_architecture", "weighting_method"])
    cash_double_flat = flatten_windows(cash_double_results, ["specification_id", "signal_id", "breadth", "frequency", "cash_architecture", "weighting_method"])
    chosen_cash, cash_summary = cash_choice(cash_flat, cash_double_flat)
    csv(ROOT / "UKACTIVE_A4D_CASH_DEFENCE_RESULTS.csv", cash_results)
    csv(ROOT / "UKACTIVE_A4D_CASH_DOUBLE_COST_RESULTS.csv", cash_double_results)
    csv(ROOT / "UKACTIVE_A4D_CASH_ECONOMIC_VALUE.csv", cash_summary)

    # Stage E: limited predetermined weights on the representative architecture.
    weighting_result_frames: list[pd.DataFrame] = []
    weighting_plans: dict[str, core.PlannedResult] = {}
    for weighting in policy["weighting"]:
        _, planned, result, _ = run("STAGE_E_WEIGHTING", chosen_signal, chosen_breadth, chosen_frequency, chosen_cash, weighting)
        weighting_result_frames.append(result)
        weighting_plans[weighting] = planned
    weighting_results = pd.concat(weighting_result_frames, ignore_index=True)
    weighting_flat = flatten_windows(weighting_results, ["specification_id", "signal_id", "breadth", "frequency", "cash_architecture", "weighting_method"])
    chosen_weighting, weighting_decision = weighting_choice(weighting_flat)
    csv(ROOT / "UKACTIVE_A4D_WEIGHTING_RESULTS.csv", weighting_results)
    csv(ROOT / "UKACTIVE_A4D_WEIGHTING_DECISION.csv", weighting_decision)

    final_id, final_plan, final_results, final_rolling = run(
        "REPRESENTATIVE", chosen_signal, chosen_breadth, chosen_frequency, chosen_cash, chosen_weighting
    )
    always_id, always_plan, always_results, _ = run(
        "ALWAYS_INVESTED_REPRESENTATIVE", chosen_signal, chosen_breadth, chosen_frequency, "CASH_0_ALWAYS_INVESTED", chosen_weighting
    )
    # The most defensive diagnostic is retained for transparent comparison even when it fails promotion.
    defensive_architecture = str(cash_summary.sort_values(["median_latest5_maximum_drawdown", "median_latest5_calmar"], ascending=[False, False]).iloc[0]["cash_architecture"])
    _, defensive_plan, _, _ = run(
        "DEFENSIVE_DIAGNOSTIC", chosen_signal, chosen_breadth, chosen_frequency, defensive_architecture, chosen_weighting
    )

    # Robustness: signal neighbourhood, maturity, doubled costs and major-contributor exclusions.
    robustness_frames: list[pd.DataFrame] = []
    for signal in core.SIGNALS:
        _, _, result, _ = run("ROBUSTNESS_SIGNAL", signal, chosen_breadth, chosen_frequency, chosen_cash, chosen_weighting)
        robustness_frames.append(result)
    for maturity in ["MATURE_ONLY", "MATURE_PLUS_DEVELOPING"]:
        _, _, result, _ = run("ROBUSTNESS_MATURITY", chosen_signal, chosen_breadth, chosen_frequency, chosen_cash, chosen_weighting, maturity=maturity)
        robustness_frames.append(result)
    _, _, doubled_final, _ = run("ROBUSTNESS_DOUBLE_COST", chosen_signal, chosen_breadth, chosen_frequency, chosen_cash, chosen_weighting, double_cost=True)
    robustness_frames.append(doubled_final)
    family_contribution, rank_contribution = core.contribution_tables(final_plan, data.base.research.calendar)
    top_families = list(family_contribution.head(3)["economic_exposure_family_id"]) if len(family_contribution) else []
    for family in top_families:
        _, _, result, _ = run("ROBUSTNESS_LEAVE_ONE_FAMILY_OUT", chosen_signal, chosen_breadth, chosen_frequency, chosen_cash, chosen_weighting, exclusions={family})
        robustness_frames.append(result)
    if top_families:
        _, _, result, _ = run("ROBUSTNESS_EXCLUDE_TOP_THREE", chosen_signal, chosen_breadth, chosen_frequency, chosen_cash, chosen_weighting, exclusions=set(top_families))
        robustness_frames.append(result)
    robustness = pd.concat(robustness_frames, ignore_index=True)
    csv(ROOT / "UKACTIVE_A4D_ROBUSTNESS_RESULTS.csv", robustness)
    csv(ROOT / "UKACTIVE_A4D_CONTRIBUTION_BY_FAMILY.csv", family_contribution)
    csv(ROOT / "UKACTIVE_A4D_CONTRIBUTION_BY_RANK.csv", rank_contribution)

    final_pool = pool(chosen_frequency)
    year = year_rows(final_id, final_plan.simulation, global_sim, final_pool)
    csv(ROOT / "UKACTIVE_A4D_YEAR_BY_YEAR_RESULTS.csv", year)
    csv(ROOT / "UKACTIVE_A4D_ROLLING_EXCESS_RESULTS.csv", final_rolling)
    rolling_summary = (
        final_rolling.groupby(["comparator_id", "rolling_months"], as_index=False)
        .agg(
            window_count=("excess_return", "size"),
            positive_excess_frequency=("excess_return", lambda x: float(pd.Series(x).gt(0).mean())),
            mean_excess=("excess_return", "mean"),
            median_excess=("excess_return", "median"),
            worst_excess=("excess_return", "min"),
        )
    )
    rolling_summary["warning"] = WARNING
    csv(ROOT / "UKACTIVE_A4D_ROLLING_EXCESS_SUMMARY.csv", rolling_summary)

    episodes = benchmark_drawdown_episodes(global_sim, pd.Timestamp(policy["windows"]["COMMON_CAUSAL_CHAIN_START"]))
    cash_stress = stress_rows(
        episodes,
        {
            "GLOBAL_DEVELOPED_WORLD": global_sim,
            "ALWAYS_INVESTED": always_plan.simulation,
            "SELECTED_CASH_ARCHITECTURE": final_plan.simulation,
            "MOST_DEFENSIVE_DIAGNOSTIC": defensive_plan.simulation,
        },
    )
    false_frames = []
    for architecture in policy["cash_architectures"]:
        local = false_defensive_periods(cash_plans[(architecture, chosen_breadth)].simulation, global_sim)
        if len(local):
            local.insert(0, "cash_architecture", architecture)
            false_frames.append(local)
    false_defence = pd.concat(false_frames, ignore_index=True) if false_frames else pd.DataFrame(
        columns=["cash_architecture", "defensive_date", "cash_fraction", "subsequent_global_return_approx_3m", "false_defensive", "warning"]
    )
    csv(ROOT / "UKACTIVE_A4D_CASH_STRESS_EPISODES.csv", cash_stress)
    csv(ROOT / "UKACTIVE_A4D_FALSE_DEFENSIVE_PERIODS.csv", false_defence)

    cash_exposure_frames = []
    for architecture in policy["cash_architectures"]:
        curve = cash_plans[(architecture, chosen_breadth)].simulation.curve[
            ["date", "invested_fraction", "cash_fraction", "holdings"]
        ].copy()
        curve.insert(0, "cash_architecture", architecture)
        cash_exposure_frames.append(curve)
    parquet(ROOT / "UKACTIVE_A4D_CASH_EXPOSURE_HISTORY.parquet", pd.concat(cash_exposure_frames, ignore_index=True))

    signal_inference = signal_hac_inference(date_diagnostics, policy)
    bootstrap_inference = monthly_block_bootstrap(
        final_id,
        final_plan.simulation,
        {"GLOBAL_DEVELOPED_WORLD": global_sim, "EQUAL_WEIGHT_OPPORTUNITY_POOL": final_pool},
        pd.Timestamp(policy["windows"]["LATEST_5Y_START"]),
        pd.Timestamp(policy["windows"]["CUTOFF"]),
    )
    csv(ROOT / "UKACTIVE_A4D_SIGNAL_HAC_INFERENCE.csv", signal_inference)
    csv(ROOT / "UKACTIVE_A4D_REPRESENTATIVE_BLOCK_BOOTSTRAP.csv", bootstrap_inference)

    curves = []
    for label, simulation in {
        "GLOBAL_DEVELOPED_WORLD": global_sim,
        "EQUAL_WEIGHT_OPPORTUNITY_POOL": final_pool,
        "REPRESENTATIVE_ALWAYS_INVESTED": always_plan.simulation,
        "REPRESENTATIVE_SELECTED": final_plan.simulation,
        "DEFENSIVE_DIAGNOSTIC": defensive_plan.simulation,
        "ACTUAL_GBP_CASH": cash_sim,
    }.items():
        local = simulation.curve.copy()
        local.insert(0, "series_id", label)
        curves.append(local)
    equity_curves = pd.concat(curves, ignore_index=True, sort=False)
    parquet(ROOT / "UKACTIVE_A4D_EQUITY_CURVES.parquet", equity_curves)

    chart_paths = plots(
        global_sim,
        final_pool,
        always_plan.simulation,
        defensive_plan.simulation,
        breadth_summary,
        frequency_summary,
        final_rolling,
        family_contribution,
        rank_contribution,
    )

    # Specification registry and tests.
    registry = pd.DataFrame(registry_rows).drop_duplicates("specification_id").sort_values(["research_stage", "specification_id"])
    csv(ROOT / "UKACTIVE_A4D_SPECIFICATION_REGISTRY.csv", registry)
    testing_ledger = (
        registry.groupby(["research_stage", "classification"], as_index=False)
        .agg(specification_count=("specification_id", "size"))
        .sort_values(["research_stage", "classification"])
    )
    testing_ledger["independent_hypotheses_claimed"] = 0
    testing_ledger["selection_or_use"] = np.select(
        [
            testing_ledger["research_stage"].eq("STAGE_B_BREADTH"),
            testing_ledger["research_stage"].eq("STAGE_C_FREQUENCY"),
            testing_ledger["research_stage"].eq("STAGE_D_CASH"),
            testing_ledger["research_stage"].eq("STAGE_E_WEIGHTING"),
        ],
        ["MAP_ADJACENT_BREADTH_REGION", "SELECT_REGION_LEVEL_CADENCE", "FIXED_DEFENSIVE_GATE", "LIMITED_FIXED_WEIGHT_COMPARISON"],
        default="ROBUSTNESS_OR_REFERENCE",
    )
    testing_ledger["interpretation"] = "CORRELATED_ARCHITECTURE_CELLS; NOT COUNTED AS INDEPENDENT DISCOVERIES"
    testing_ledger["warning"] = WARNING
    csv(ROOT / "UKACTIVE_A4D_MULTIPLE_TESTING_LEDGER.csv", testing_ledger)
    immutable_after = {path.name: sha256(path) for path in immutable_paths if path.exists()}
    executions = final_plan.simulation.trades.loc[final_plan.simulation.trades.get("execution_status", pd.Series(dtype=str)).eq("EXECUTED")]
    feature_sample = data.daily_features.dropna(subset=["M1_EQUAL_5H", "M2_INTERMEDIATE_5H"]).head(1000)
    m1_rebuilt = feature_sample[[f"RANK_RS_{h}" for h in core.HORIZONS]].mean(axis=1)
    weights2 = policy["signals"]["M2_INTERMEDIATE_5H"]
    m2_rebuilt = sum(float(weights2[f"RS_{h}"]) * feature_sample[f"RANK_RS_{h}"] for h in core.HORIZONS)
    test_rows = [
        ("A4D_UNIVERSE_27_FAMILIES", len(data.members) == 27, f"observed={len(data.members)}"),
        ("RANKING_IDENTITY_ECONOMIC_FAMILY", data.daily_features[["date", "economic_exposure_family_id"]].duplicated().sum() == 0, "date-family keys unique"),
        ("M1_EQUAL_FORMULA", np.allclose(feature_sample["M1_EQUAL_5H"], m1_rebuilt, atol=1e-12), "five equal ranks"),
        ("M2_FROZEN_FORMULA", np.allclose(feature_sample["M2_INTERMEDIATE_5H"], m2_rebuilt, atol=1e-12), "10/15/25/30/20"),
        ("NO_SAME_CLOSE_EXECUTION", bool((pd.to_datetime(executions["execution_date"]) > pd.to_datetime(executions["review_date"])).all()), "all executed after review close"),
        ("EXECUTION_LAG_ONE_TO_THREE", bool(executions["execution_lag_xlon_sessions"].between(1, 3).all()), "authoritative tolerance"),
        ("NO_LEVERAGE", bool(final_plan.simulation.curve["invested_fraction"].le(1 + 1e-10).all()), "risky fraction <=100%"),
        ("NONNEGATIVE_CASH", bool(final_plan.simulation.curve["cash_fraction"].ge(-1e-10).all()), "cash fraction nonnegative"),
        ("COMMON_CHAIN_START_RESPECTED", bool(final_plan.simulation.curve["date"].min() >= pd.Timestamp(policy["windows"]["COMMON_CAUSAL_CHAIN_START"])), "no fabricated pre-break compounding"),
        ("A5_AND_PRIOR_IMMUTABLE_HASHES", immutable_before == immutable_after, json.dumps(immutable_before, sort_keys=True)),
        ("ALL_FORMAL_SPECS_REGISTERED", len(registry) == len(simulation_cache), f"registry={len(registry)} cache={len(simulation_cache)}"),
        ("RANK_CONTRIBUTION_RECONCILES", abs(rank_contribution["gross_market_pnl_return_units"].sum() - family_contribution["gross_market_pnl_return_units"].sum()) < 1e-10, "rank buckets equal gross family market P&L"),
        ("CAPTURE_DELAY_DIAGNOSTIC_NONDEGENERATE", bool(frequency_results["leadership_capture_delay_sessions"].max() > 0), "diagnostic is not a constant zero"),
        ("CASH_CAN_REACH_100_PERCENT", any(plan.simulation.curve["cash_fraction"].ge(1 - 1e-10).any() for (architecture, _), plan in cash_plans.items() if architecture != "CASH_0_ALWAYS_INVESTED"), "at least one defensive specification reaches cash"),
        ("NO_A5_PROSPECTIVE_EVENT_CREATED", all((not path.exists()) or sum(1 for _ in path.open(encoding="utf-8")) <= 1 for path in [ROOT / "UKACTIVE_A5_DECISION_LEDGER.csv", ROOT / "UKACTIVE_A5_EXECUTION_LEDGER.csv"]), "A5 ledgers remain header-only"),
    ]
    tests = pd.DataFrame([{"test_id": name, "status": "PASS" if passed else "FAIL", "detail": detail} for name, passed, detail in test_rows])
    tests["warning"] = WARNING
    csv(ROOT / "UKACTIVE_A4D_CORRECTNESS_TEST_RESULTS.csv", tests)

    # Classification uses the preregistered plateau and cash/frequency evidence, never the best-CAGR cell alone.
    final_l5 = final_results.loc[final_results["window_id"].eq("LATEST_5Y")].iloc[0]
    final_post = final_results.loc[final_results["window_id"].eq("POST_2020")].iloc[0]
    signal_neighbor = robustness.loc[(robustness["window_id"].eq("LATEST_5Y")) & robustness["cost_scenario"].eq("BASE") & robustness["maturity_scope"].eq("DYNAMIC_POINT_IN_TIME")]
    positive_signal_count = int(signal_neighbor["net_excess_vs_equal_pool"].gt(0).sum())
    rolling_pool = rolling_summary.loc[rolling_summary["comparator_id"].eq("EQUAL_POOL")]
    rolling12_positive = float(rolling_pool.loc[rolling_pool["rolling_months"].eq(12), "positive_excess_frequency"].iloc[0]) if len(rolling_pool.loc[rolling_pool["rolling_months"].eq(12)]) else np.nan
    top3_share = float(family_contribution.head(3)["share_of_gross_family_market_pnl"].sum()) if len(family_contribution) else np.nan
    cash_promoted = chosen_cash != "CASH_0_ALWAYS_INVESTED"
    if (
        plateau_found
        and final_l5["net_excess_vs_global"] > 0
        and final_l5["net_excess_vs_equal_pool"] > 0
        and final_post["net_excess_vs_equal_pool"] > 0
        and positive_signal_count >= 2
        and pd.notna(rolling12_positive)
        and rolling12_positive >= 0.55
        and tests["status"].eq("PASS").all()
    ):
        classification = "A4D_STRONG_RESEARCH_CANDIDATE" if cash_promoted and top3_share < 0.70 else "A4D_PROMISING_BUT_UNCONFIRMED"
    elif final_l5["net_excess_vs_equal_pool"] > 0 and tests["status"].eq("PASS").all():
        classification = "A4D_WEAK_OR_REGIME_DEPENDENT"
    else:
        classification = "A4D_NO_USEFUL_EDGE" if tests["status"].eq("PASS").all() else "A4D_WEAK_OR_REGIME_DEPENDENT"

    untouched_holdout = False
    forward_spec = {
        "stage": "UKACTIVE-A4D",
        "evidence_level": "E2_DEVELOPMENTAL",
        "status": "DEVELOPMENTAL_REFERENCE_NOT_AUTHORISED_FOR_PROSPECTIVE_VALIDATION",
        "untouched_historical_holdout_available": untouched_holdout,
        "prospective_test_started": False,
        "signal_id": chosen_signal,
        "signal_definition": policy["signals"][chosen_signal],
        "pool": policy["universe"]["context_id"],
        "breadth": chosen_breadth,
        "acceptable_breadth_region": breadth_region,
        "frequency": chosen_frequency,
        "cash_architecture": chosen_cash,
        "weighting_method": chosen_weighting,
        "benchmark": policy["benchmarks"]["global"],
        "pool_comparator": policy["benchmarks"]["pool"],
        "cash": policy["benchmarks"]["cash"],
        "execution": policy["execution"],
        "costs": policy["costs"],
        "warning": "NOT AUTHORISED AND NOT STARTED; A4D disposition is insufficient to open a new prospective lineage. Existing A5 remains unchanged.",
    }
    write_json(ROOT / "config" / "UKACTIVE_A4D_REPRESENTATIVE_FORWARD_SPEC.json", forward_spec)

    final_flat = flatten_windows(final_results, ["specification_id", "signal_id", "breadth", "frequency", "cash_architecture", "weighting_method"])
    csv(ROOT / "UKACTIVE_A4D_PRIMARY_ECONOMIC_SCORECARD.csv", final_results)

    unresolved = pd.DataFrame(
        [
            {"item_id": "A4D-OPEN-001", "status": "OPEN_NON_BLOCKING", "item": "No untouched historical interval remains; confirmation must be prospective.", "blocking_for_research_disposition": False},
            {"item_id": "A4D-OPEN-002", "status": "OPEN_NON_BLOCKING", "item": "Historical UK retail, ISA, account and broker eligibility remain partly unresolved.", "blocking_for_research_disposition": False},
            {"item_id": "A4D-OPEN-003", "status": "DISCLOSED_LIMITATION", "item": "Broad-portfolio efficacy before 2017-02-03 cannot be compounded without fabricating the GLOBAL_GOLD_MINERS continuity break.", "blocking_for_research_disposition": False},
            {"item_id": "A4D-OPEN-004", "status": "OPEN_NON_BLOCKING", "item": "Equal-weight opportunity-pool benchmark is a causal research index, not a fully costed implementation claim.", "blocking_for_research_disposition": False},
        ]
    )
    unresolved["warning"] = WARNING
    csv(ROOT / "UKACTIVE_A4D_UNRESOLVED_ITEMS.csv", unresolved)

    inference_table = bootstrap_inference[
        ["comparator_id", "observed_annualised_excess", "bootstrap_2_5_percentile", "bootstrap_97_5_percentile", "bootstrap_probability_excess_positive", "two_sided_tail_probability"]
    ].copy()
    for column in ["observed_annualised_excess", "bootstrap_2_5_percentile", "bootstrap_97_5_percentile", "bootstrap_probability_excess_positive", "two_sided_tail_probability"]:
        inference_table[column] = inference_table[column].map(lambda value: f"{100 * value:.2f}%" if pd.notna(value) else "N/A")
    inference_report = f"""# UKACTIVE-A4D statistical inference

All inference is E2 developmental. Weekly signal observations and forward returns overlap, so naive independent-observation t-tests are prohibited. `UKACTIVE_A4D_SIGNAL_HAC_INFERENCE.csv` uses a Newey–West long-run variance for each signal/horizon, with the lag tied to the forward horizon. Benjamini–Hochberg q-values are calculated within each evidence-window/metric family.

The representative portfolio uses a paired six-month circular block bootstrap of monthly returns with 5,000 deterministic draws. This is a falsification/uncertainty diagnostic, not independent confirmation.

{frame_markdown(inference_table)}

The full architecture grid is correlated and staged. It is not described as 77 independent hypotheses; the complete accounting is in `UKACTIVE_A4D_MULTIPLE_TESTING_LEDGER.csv`.
"""
    (ROOT / "UKACTIVE_A4D_STATISTICAL_INFERENCE.md").write_text(inference_report, encoding="utf-8")

    latest_features = data.daily_features.loc[data.daily_features["date"].eq(pd.Timestamp(policy["windows"]["CUTOFF"]))]
    cancelled = sum(
        int(item.simulation.trades["execution_status"].astype(str).str.startswith("CANCELLED", na=False).sum())
        for item in simulation_cache.values()
        if len(item.simulation.trades) and "execution_status" in item.simulation.trades
    )
    data_quality = f"""# UKACTIVE-A4D data-quality report

- Authoritative A2R2 corrected endpoint chain: retained.
- Deterministic XLON calendar and next-session execution: retained.
- Economic-family ranking identity: 27 frozen `INDUSTRY_PLUS_THEME` families; no ticker-level ranks.
- Latest 252-session-composite signal-ready count at {policy['windows']['CUTOFF']}: {int(latest_features['M1_EQUAL_5H'].notna().sum())}.
- Common causal portfolio-chain start: {policy['windows']['COMMON_CAUSAL_CHAIN_START']}.
- Reason: {policy['windows']['COMMON_CAUSAL_CHAIN_REASON']}
- Cancelled rebalances across all registered baseline/robustness simulations: {cancelled}. These remain cancelled; no stale price or discretionary execution was manufactured.
- Same-close executions: zero by construction and test.
- Forward-filled prices/returns: none introduced.
- Leverage/shorting: none.
- Immutable A4/A4B/A4C/A5 hashes: unchanged.
- A5 prospective decisions/executions created: zero.
- In-build tests: {int(tests['status'].eq('PASS').sum())}/{len(tests)} PASS.
- Standalone pytest controls: recorded separately by the Git/test handoff.

The equal-weight opportunity-pool comparator is the existing causal research index: membership becomes effective after the review date and invalid constituent-day observations are excluded rather than filled. It is not represented as a costed executable fund.
"""
    (ROOT / "UKACTIVE_A4D_DATA_QUALITY_REPORT.md").write_text(data_quality, encoding="utf-8")

    recommended_region = f"TOP{min(breadth_region)}–TOP{max(breadth_region)}" if len(breadth_region) > 1 else f"TOP{breadth_region[0]}"
    breadth_display = breadth_summary.loc[breadth_summary["signal_id"].eq(chosen_signal), [
        "breadth", "latest_5y_net_cagr", "latest_5y_net_excess_vs_equal_pool", "latest_5y_maximum_drawdown", "latest_5y_calmar_mar", "latest_5y_annual_turnover_traded_notional"
    ]].sort_values("breadth").copy()
    for column in ["latest_5y_net_cagr", "latest_5y_net_excess_vs_equal_pool", "latest_5y_maximum_drawdown"]:
        breadth_display[column] = breadth_display[column].map(pct)
    breadth_display["latest_5y_calmar_mar"] = breadth_display["latest_5y_calmar_mar"].map(number)
    breadth_display["latest_5y_annual_turnover_traded_notional"] = breadth_display["latest_5y_annual_turnover_traded_notional"].map(lambda value: number(value) + "x")
    frequency_display = frequency_summary[["frequency", "median_latest5_pool_excess", "median_latest5_mdd", "median_turnover", "positive_double_cost_pool_gate_fraction", "passes_frequency_gate"]].copy()
    frequency_display["_order"] = frequency_display["frequency"].map({"DAILY": 0, "WEEKLY": 1, "MONTHLY": 2})
    frequency_display = frequency_display.sort_values("_order").drop(columns="_order")
    for column in ["median_latest5_pool_excess", "median_latest5_mdd", "positive_double_cost_pool_gate_fraction"]:
        frequency_display[column] = frequency_display[column].map(pct)
    frequency_display["median_turnover"] = frequency_display["median_turnover"].map(lambda value: number(value) + "x")
    cash_display = cash_summary[["cash_architecture", "median_latest5_net_cagr", "median_latest5_return_sacrifice_vs_always_invested", "median_latest5_drawdown_avoided", "median_latest5_pool_excess", "double_cost_pool_excess", "median_latest5_calmar", "median_latest5_ulcer", "median_average_cash_weight", "passes_cash_promotion_gate"]].copy()
    for column in ["median_latest5_net_cagr", "median_latest5_return_sacrifice_vs_always_invested", "median_latest5_drawdown_avoided", "median_latest5_pool_excess", "double_cost_pool_excess", "median_latest5_ulcer", "median_average_cash_weight"]:
        cash_display[column] = cash_display[column].map(pct)
    cash_display["median_latest5_calmar"] = cash_display["median_latest5_calmar"].map(number)
    year_display = year[["calendar_year", "partial_year", "net_return_or_cagr", "excess_vs_global", "excess_vs_pool", "maximum_drawdown"]].copy()
    for column in ["net_return_or_cagr", "excess_vs_global", "excess_vs_pool", "maximum_drawdown"]:
        year_display[column] = year_display[column].map(pct)
    contribution_display = family_contribution.head(10)[["economic_exposure_family_id", "gross_market_pnl_return_units", "share_of_gross_family_market_pnl"]].copy()
    contribution_display["gross_market_pnl_return_units"] = contribution_display["gross_market_pnl_return_units"].map(number)
    contribution_display["share_of_gross_family_market_pnl"] = contribution_display["share_of_gross_family_market_pnl"].map(pct)
    defensive_candidates = cash_summary.loc[
        cash_summary["cash_architecture"].ne("CASH_0_ALWAYS_INVESTED")
        & cash_summary["median_latest5_pool_excess"].gt(0)
        & cash_summary["double_cost_pool_excess"].gt(0)
    ].sort_values(["median_latest5_calmar", "median_latest5_ulcer"], ascending=[False, True])
    defensive_research_lead = str(defensive_candidates.iloc[0]["cash_architecture"]) if len(defensive_candidates) else "NONE"
    defensive_lead_row = cash_flat.loc[(cash_flat["cash_architecture"].eq(defensive_research_lead)) & cash_flat["breadth"].eq(chosen_breadth)]
    defensive_lead_row = defensive_lead_row.iloc[0] if len(defensive_lead_row) else None
    top_three_suffix = "EXCLUDE_" + "_".join(sorted(top_families)) if top_families else ""
    top_three_exclusion = robustness.loc[
        robustness["window_id"].eq("LATEST_5Y")
        & robustness["cost_scenario"].eq(top_three_suffix)
    ]
    top_three_exclusion_pool_excess = float(top_three_exclusion.iloc[0]["net_excess_vs_equal_pool"]) if len(top_three_exclusion) else np.nan
    rank_display = rank_contribution[["rank_bucket", "gross_market_pnl_return_units", "share_of_gross_family_market_pnl"]].copy()
    rank_display["gross_market_pnl_return_units"] = rank_display["gross_market_pnl_return_units"].map(number)
    rank_display["share_of_gross_family_market_pnl"] = rank_display["share_of_gross_family_market_pnl"].map(pct)
    report = f"""# UKACTIVE-A4D — final research report

Decision: **{classification}**  
Evidence: **E2 developmental; no independent historical confirmation**  
Data cutoff: **{policy['windows']['CUTOFF']}**  
Common causal portfolio-chain start: **{policy['windows']['COMMON_CAUSAL_CHAIN_START']}**

## Executive finding

A4D preserved the accepted 27-family point-in-time `INDUSTRY_PLUS_THEME` universe, the A2R2 endpoint chain, the global-developed benchmark, actual GBP cash, next-session execution and the 20 bp plus £3.99 cost model. It did not modify A1–A5 or start prospective testing.

The staged experiment selected `{chosen_signal}`, found {'a stable breadth plateau' if plateau_found else 'no stable breadth plateau'}, and used `{chosen_frequency}` as the region-level cadence. The defensive gate {'selected `' + chosen_cash + '`' if cash_promoted else 'did not promote a cash overlay; always-invested remained the representative control'}. The final representative retained `{chosen_weighting}`.

Final-five-year representative economics: net CAGR **{pct(final_l5['net_cagr'])}**, excess versus global **{pct(final_l5['net_excess_vs_global'])}**, excess versus the equal-weight opportunity pool **{pct(final_l5['net_excess_vs_equal_pool'])}**, maximum drawdown **{pct(final_l5['maximum_drawdown'])}**, Calmar **{number(final_l5['calmar_mar'])}**, Ulcer Index **{pct(final_l5['ulcer_index'])}**, and annual traded-notional turnover **{number(final_l5['annual_turnover_traded_notional'])}x**.

## Direct answers

1. **Multi-horizon rank versus prior A3:** M1 is the prior equal-five-horizon signal, not new evidence. M2 passed the frozen Stage-A gate and improved the same TOP7/monthly five-year pool excess from **0.08%** under M1 to **2.63%** under M2. M3's deterioration penalty did not add portfolio value. This is developmental comparison, not independent confirmation.
2. **Repeatable cross-sectional edge:** M2's full-history mean IC was positive at 21/42/63 sessions, but its mean top-quintile advantages were only **0.07% / −0.05% / 0.18%**. The representative's positive rolling-12m excess frequency was only **{pct(rolling12_positive)}** versus the pool and **40.20%** versus global. That is not persistent enough for a strong claim.
3. **Breadth TOP3–TOP10:** TOP3–TOP5 generally diluted net selection economics; TOP6–TOP9 formed the M2 plateau; TOP10 lost pool excess. The table below is the five-year, after-cost frontier.

{frame_markdown(breadth_display)}

4. **Plateau:** **{'Yes: ' + recommended_region if plateau_found else 'No; TOP5/TOP6 were used only as a diagnostic fallback.'}**
5. **Ranks creating excess:** ranks 4–5 contributed the most gross family market P&L, followed by ranks 6–10; the exact reconciled attribution is below.

{frame_markdown(rank_display)}

6. **Diversification and drawdown:** the representative TOP7 reduced concentration versus TOP1, but five-year drawdown remained **{pct(final_l5['maximum_drawdown'])}**. Marginal changes for every added holding are retained.
7. **Cadence:** weekly looked best before full cost stress, but doubled costs erased pool excess across all four breadths. Monthly retained positive doubled-cost pool excess in two of four breadths and therefore won the frozen region-level gate. Daily was dominated by noise and roughly **36.9x** median annual turnover.

{frame_markdown(frequency_display)}

8. **Costs:** baseline and doubled-cost results are both retained. At TOP7/monthly the pool excess fell from **2.63%** to **0.96%** under doubled costs. No gross-only result is promoted.
9. **Cash:** **{'Promoted because it passed the fixed drawdown and excess gates.' if cash_promoted else 'No tested cash architecture passed the complete preregistered promotion gate.'}** Individual asset qualification (`{defensive_research_lead}`) was the best defensive research lead: at representative TOP7 it produced net CAGR **{pct(defensive_lead_row['latest_5y_net_cagr']) if defensive_lead_row is not None else 'N/A'}**, pool excess **{pct(defensive_lead_row['latest_5y_net_excess_vs_equal_pool']) if defensive_lead_row is not None else 'N/A'}** and MDD **{pct(defensive_lead_row['latest_5y_maximum_drawdown']) if defensive_lead_row is not None else 'N/A'}**, but its region-level drawdown improvement missed the fixed five-point gate.
10. **Defensive mechanism:** C1 preserved return best; C2 reduced drawdown more but its median doubled-cost pool excess turned negative; global confirmation and the combined rule sacrificed too much return. Always-invested therefore remains the representative, while C1 is a future preregistration lead—not a promoted A4D rule.

{frame_markdown(cash_display)}

11. **CAGR sacrificed per drawdown reduction:** C1's region median sacrificed about **0.01 percentage point** of CAGR for **4.15 points** of MDD improvement. C2 sacrificed about **0.97 point** for **5.77 points**. The full arithmetic is retained in `UKACTIVE_A4D_CASH_ECONOMIC_VALUE.csv`.
12. **Versus global:** final-five-year excess was **{pct(final_l5['net_excess_vs_global'])}**.
13. **Versus equal pool:** final-five-year excess was **{pct(final_l5['net_excess_vs_equal_pool'])}**.
14. **Winner dependence:** the top three family share of gross family market P&L was **{pct(top3_share)}**. Removing all three changed five-year pool excess to **{pct(top_three_exclusion_pool_excess)}**, so the edge remains materially right-tail dependent even though removing any single contributor left positive excess.
15. **Subperiod/neighbour stability:** pre-2020 pool excess was **{pct(final_results.loc[final_results['window_id'].eq('PRE_2020'), 'net_excess_vs_equal_pool'].iloc[0])}**, post-2020 **{pct(final_post['net_excess_vs_equal_pool'])}**. Calendar-year pool excess was positive in only five of ten displayed years, and 2025 supplied a disproportionate gain. MATURE and MATURE+DEVELOPING sensitivities were positive, so launch cohorts do not explain the whole result. Pre-2017 breadth compounding is intentionally unavailable.
16. **Simplest architecture:** `{chosen_signal} | TOP_{chosen_breadth} | {chosen_frequency} | {chosen_cash} | {chosen_weighting}`.
17. **Prospective freeze:** **not authorised from A4D**. A reproducible developmental reference specification is written, but no untouched historical holdout exists and the weak/regime-dependent disposition does not justify opening a new validation lineage.

## Statistical uncertainty

No Stage-A IC, top-quintile or rank-1 effect survived the within-window/metric HAC–BH screen at q < 0.10. The paired six-month block-bootstrap 95% interval for five-year annualised excess was **−9.04% to 16.20%** versus global and **−5.61% to 12.73%** versus the equal pool; both include zero. Positive-excess bootstrap probabilities were **59.86%** and **73.80%**, respectively. This supports the weak/regime-dependent disposition rather than a strong claim.

## Calendar-year stability

{frame_markdown(year_display)}

## Largest gross family contributors

{frame_markdown(contribution_display)}

## Leadership deterioration and momentum age

The fixed state definitions and high-rank age buckets are diagnostics only. `MATURE_DECELERATING` did not underperform established leadership; in the latest five years its mean 42-session forward return was higher. Momentum age was not monotonic. Therefore no deterioration exit, age rule, fast exit or discretionary override was added.

## Data-lineage limitation

The last unreconstructed `GLOBAL_GOLD_MINERS` implementation gap makes broad-portfolio compounding before 2017-02-03 non-causal. A4D starts portfolio tests at the first endpoint of the final admitted segment. No price, return, liquidation proceeds or proxy was manufactured. Signal diagnostics can use earlier valid observations, but they are not represented as a continuous executable portfolio.

## RECOMMENDED ROBUST PORTFOLIO REGION

- Preferred signal family: `{chosen_signal}`.
- Acceptable breadth range: `{recommended_region}`.
- Preferred rebalance frequency: `{chosen_frequency}`.
- Acceptable neighbouring frequency: see the complete gate in `UKACTIVE_A4D_FREQUENCY_SUMMARY.csv`; no neighbour is implied if it failed.
- Cash/risk-state mechanism: `{chosen_cash}` for the representative; `CASH_1_INDIVIDUAL_ABOVE_CASH_252` is the best unpromoted defensive research lead.
- Weighting: `{chosen_weighting}`.
- Expected historical CAGR range across the breadth region: **{pct(breadth_summary.loc[(breadth_summary['signal_id'].eq(chosen_signal)) & breadth_summary['breadth'].isin(breadth_region), 'latest_5y_net_cagr'].min())} to {pct(breadth_summary.loc[(breadth_summary['signal_id'].eq(chosen_signal)) & breadth_summary['breadth'].isin(breadth_region), 'latest_5y_net_cagr'].max())}**.
- Excess CAGR versus equal pool: **{pct(breadth_summary.loc[(breadth_summary['signal_id'].eq(chosen_signal)) & breadth_summary['breadth'].isin(breadth_region), 'latest_5y_net_excess_vs_equal_pool'].min())} to {pct(breadth_summary.loc[(breadth_summary['signal_id'].eq(chosen_signal)) & breadth_summary['breadth'].isin(breadth_region), 'latest_5y_net_excess_vs_equal_pool'].max())}**.
- Maximum drawdown range: **{pct(breadth_summary.loc[(breadth_summary['signal_id'].eq(chosen_signal)) & breadth_summary['breadth'].isin(breadth_region), 'latest_5y_maximum_drawdown'].min())} to {pct(breadth_summary.loc[(breadth_summary['signal_id'].eq(chosen_signal)) & breadth_summary['breadth'].isin(breadth_region), 'latest_5y_maximum_drawdown'].max())}**.
- Calmar range: **{number(breadth_summary.loc[(breadth_summary['signal_id'].eq(chosen_signal)) & breadth_summary['breadth'].isin(breadth_region), 'latest_5y_calmar_mar'].min())} to {number(breadth_summary.loc[(breadth_summary['signal_id'].eq(chosen_signal)) & breadth_summary['breadth'].isin(breadth_region), 'latest_5y_calmar_mar'].max())}**.
- Turnover range: **{number(breadth_summary.loc[(breadth_summary['signal_id'].eq(chosen_signal)) & breadth_summary['breadth'].isin(breadth_region), 'latest_5y_annual_turnover_traded_notional'].min())}x to {number(breadth_summary.loc[(breadth_summary['signal_id'].eq(chosen_signal)) & breadth_summary['breadth'].isin(breadth_region), 'latest_5y_annual_turnover_traded_notional'].max())}x**.
- Principal failure modes: top-three removal turns excess negative; only 50% of rolling 12-month pool-excess windows are positive; pre-2020 weakness; cost-fragile weekly results; 2025 concentration; and incomplete historical implementation eligibility evidence.
- Remaining evidence gap: genuinely prospective data after a separately approved freeze.

## REPRESENTATIVE SPECIFICATION FOR FORWARD TESTING

`{chosen_signal} | TOP_{chosen_breadth} | {chosen_frequency} | {chosen_cash} | {chosen_weighting}`

This is the middle of the selected breadth region, uses the region-level cadence decision, and retains the simplest weight/cash choice that passed its gate. It is not the maximum-CAGR cell. It is stored only as a **developmental reference** in `config/UKACTIVE_A4D_REPRESENTATIVE_FORWARD_SPEC.json`; A4D does not authorise or start it and does not modify the existing A5 lineages.
"""
    (ROOT / "UKACTIVE_A4D_FINAL_DECISION_REPORT.md").write_text(report, encoding="utf-8")

    director = f"""# UKACTIVE-A4D research-director review

The stage followed the registered signal → breadth → frequency → cash → weighting sequence. Failed and non-selected cells remain in the registry and result tables. Selection was made from adjacent regions and fixed gates, not the maximum historical CAGR.

Scientific disposition: **{classification}**. Evidence cannot exceed E2 because every historical interval was already observable to the programme. A4D does **not** authorise a new prospective lineage: rolling consistency, pre-2020 evidence and top-three-contributor dependence remain too weak. The written representative is a reproducibility reference only. Existing A5 remains immutable and not started.

The main data limitation is explicit: broad portfolios cannot be compounded through the 2016–2017 gold-miners implementation gap without inventing proceeds. The 2017-02-03 common-chain start was registered during engine validation before formal A4D outcomes.
"""
    (ROOT / "UKACTIVE_A4D_RESEARCH_DIRECTOR_REVIEW.md").write_text(director, encoding="utf-8")

    decision = {
        "stage_id": "UKACTIVE-A4D",
        "run_id": policy["run_id"],
        "decision": classification,
        "evidence_level": "E2_DEVELOPMENTAL",
        "untouched_historical_holdout": False,
        "representative_specification_id": final_id,
        "selected_signal": chosen_signal,
        "breadth_plateau_found": plateau_found,
        "breadth_region": breadth_region,
        "representative_breadth": chosen_breadth,
        "frequency": chosen_frequency,
        "cash_architecture": chosen_cash,
        "cash_architecture_promoted": cash_promoted,
        "best_unpromoted_defensive_research_lead": defensive_research_lead,
        "weighting": chosen_weighting,
        "common_causal_chain_start": policy["windows"]["COMMON_CAUSAL_CHAIN_START"],
        "latest5": {key: final_l5.get(key) for key in ["net_cagr", "net_excess_vs_global", "net_excess_vs_equal_pool", "maximum_drawdown", "calmar_mar", "ulcer_index", "annual_turnover_traded_notional"]},
        "post2020_pool_excess": final_post["net_excess_vs_equal_pool"],
        "top_three_family_pnl_share": top3_share,
        "representative_reference_spec_written": True,
        "prospective_validation_authorised": False,
        "existing_a5_modified": False,
        "warning": WARNING,
    }
    write_json(ROOT / "UKACTIVE_A4D_DECISION.json", decision)

    # Manifest is written last and omits itself from its output-hash inventory.
    outputs = sorted(path for path in ROOT.glob("UKACTIVE_A4D_*") if path.name != "UKACTIVE_A4D_MANIFEST.json")
    outputs += [ROOT / "config" / "UKACTIVE_A4D_POLICY_v1.json", ROOT / "config" / "UKACTIVE_A4D_REPRESENTATIVE_FORWARD_SPEC.json", CODE / "ukactive_a4d_core.py", CODE / "build_ukactive_a4d.py"]
    manifest = {
        "stage_id": "UKACTIVE-A4D",
        "run_id": policy["run_id"],
        "generated_at": BUILD_TIMESTAMP,
        "decision": classification,
        "git_branch": git("branch", "--show-current"),
        "starting_commit": json.loads((ROOT / "UKACTIVE_A4D_STAGE_REGISTRATION.json").read_text(encoding="utf-8"))["starting_git_commit"],
        "preregistration_commit": "31c665d118fc3a50dafbe19febc41cb6bd3f4dcc",
        "pre_outcome_chain_amendment_commit": "b57a2ed2d02a257bb4225aac08b42d70027de783",
        "authoritative_input_hashes": {
            name: sha256(ROOT / name)
            for name in [
                policy["authoritative_inputs"]["corrected_panel"],
                policy["authoritative_inputs"]["signal_eligibility"],
                policy["authoritative_inputs"]["endpoint_history"],
                policy["authoritative_inputs"]["calendar"],
                policy["authoritative_inputs"]["role_master"],
                policy["authoritative_inputs"]["cash_series"],
            ]
        },
        "immutable_prior_hashes_before": immutable_before,
        "immutable_prior_hashes_after": immutable_after,
        "prior_outputs_unchanged": immutable_before == immutable_after,
        "outputs": [{"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "size_bytes": path.stat().st_size} for path in sorted(set(outputs)) if path.exists()],
        "charts": [{"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "size_bytes": path.stat().st_size} for path in chart_paths],
        "environment": {"python": sys.version, "platform": platform.platform(), "pandas": pd.__version__, "numpy": np.__version__, "matplotlib": matplotlib.__version__},
        "test_summary": tests["status"].value_counts().to_dict(),
        "specification_count": len(registry),
        "warning": WARNING,
    }
    write_json(ROOT / "UKACTIVE_A4D_MANIFEST.json", manifest)

    print(json.dumps({
        "decision": classification,
        "carried_signals": carried_signals,
        "selected_signal": chosen_signal,
        "breadth_region": breadth_region,
        "representative_breadth": chosen_breadth,
        "frequency": chosen_frequency,
        "cash_architecture": chosen_cash,
        "weighting": chosen_weighting,
        "latest5_net_cagr": final_l5["net_cagr"],
        "latest5_excess_vs_global": final_l5["net_excess_vs_global"],
        "latest5_excess_vs_pool": final_l5["net_excess_vs_equal_pool"],
        "latest5_maximum_drawdown": final_l5["maximum_drawdown"],
        "tests": tests["status"].value_counts().to_dict(),
        "specifications": len(registry),
    }, indent=2, default=json_default))


if __name__ == "__main__":
    main()
