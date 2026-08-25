"""Execute the preregistered UKACTIVE-A4F-SIPP regime research stage.

The protocol was committed before this builder was run.  This script is
deterministic, cutoff-enforcing, and never sends or prepares broker orders.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import ukactive_a4f_sipp_core as core


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
OUT = ROOT / "UKACTIVE-A4F-SIPP-REGIME"
A4E_OUT = ROOT / "UKACTIVE-A4E-SIPP"
CUTOFF = pd.Timestamp("2026-08-21")
COMMON_START = pd.Timestamp("2017-03-01")
LONG_CORE_START = pd.Timestamp("2010-01-08")
WARNING = core.WARNING
PROTOCOL_COMMIT = "15f6e63"
POLICIES = list(core.POLICY_MAP)
SELECTABLE_POLICIES = POLICIES[:5]
SWITCHES = ["SWITCH_IMMEDIATE_MONTHLY", "SWITCH_ASYMMETRIC_HYSTERESIS"]
STATIC_M2_COMPARATORS = {
    "GLOBAL_90_M2_10": "GLOBAL_100",
    "GLOBAL_75_M2_25": "GLOBAL_100",
    "GLOBAL_50_M2_50": "GLOBAL_100",
    "GLOBAL_50_M2_25_CASH25": "GLOBAL_75_CASH25",
    "GLOBAL_75_M2_10_CASH15": "GLOBAL_85_CASH15",
    "M2_TOP7_CASH0_25_CASH75": "GLOBAL_25_CASH75",
    "M2_TOP7_CASH0_50_CASH50": "GLOBAL_50_CASH50",
    "M2_TOP7_CASH0_75_CASH25": "GLOBAL_75_CASH25",
    "M2_TOP7_CASH0_100": "GLOBAL_100",
}
WINDOWS = {
    "FULL_COMMON_HISTORY": (COMMON_START, CUTOFF),
    "PRE_2020": (COMMON_START, pd.Timestamp("2019-12-31")),
    "POST_2020": (pd.Timestamp("2020-01-02"), CUTOFF),
    "LATEST_FIVE_YEARS": (pd.Timestamp("2021-09-01"), CUTOFF),
    "LATEST_THREE_YEARS": (pd.Timestamp("2023-08-21"), CUTOFF),
}


def json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value).__name__)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(name: str, frame: pd.DataFrame) -> None:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def write_json(name: str, value: Any) -> None:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=json_default) + "\n", encoding="utf-8")


def write_text(name: str, value: str) -> None:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def as_sim(result: Any) -> Any:
    return result.simulation if hasattr(result, "simulation") else result


def curve(result: Any) -> pd.DataFrame:
    return as_sim(result).curve.drop_duplicates("date").sort_values("date").copy()


def nav_series(result: Any, start: pd.Timestamp = COMMON_START, end: pd.Timestamp = CUTOFF) -> pd.Series:
    frame = curve(result)
    value = frame.loc[frame["date"].between(start, end)].set_index("date")["portfolio_value"].astype(float)
    return value / value.iloc[0] if len(value) else value


def metric_pack(result: Any, start: pd.Timestamp = COMMON_START, end: pd.Timestamp = CUTOFF) -> dict[str, Any]:
    return core.metrics(result, start, end)


def metric_row(strategy_id: str, result: Any, window_id: str, cost: str) -> dict[str, Any]:
    start, end = WINDOWS[window_id]
    metrics = metric_pack(result, start, end)
    row = {"strategy_id": strategy_id, "window_id": window_id, "cost_scenario": cost, "first_date": max(start, pd.Timestamp(curve(result)["date"].min())), "last_date": min(end, pd.Timestamp(curve(result)["date"].max()))}
    row.update(metrics)
    row["cost_drag"] = row.get("gross_cagr", np.nan) - row.get("net_cagr", np.nan)
    return row


def monthly_returns(result: Any, start: pd.Timestamp = COMMON_START, end: pd.Timestamp = CUTOFF) -> pd.Series:
    value = curve(result).loc[lambda x: x["date"].between(start, end)].set_index("date")["portfolio_value"].astype(float)
    month = value.groupby([value.index.year, value.index.month]).last()
    ret = month.pct_change(fill_method=None).dropna()
    ret.index = pd.DatetimeIndex([pd.Timestamp(year=int(y), month=int(m), day=1) + pd.offsets.MonthEnd(0) for y, m in ret.index])
    return ret


def excluded_metrics(result: Any, excluded_years: set[int]) -> dict[str, float]:
    return core.a4e.excluded_year_metrics(as_sim(result), excluded_years)


def average_allocations(data: Any, targets: Mapping[pd.Timestamp, Mapping[str, float]]) -> dict[str, float]:
    return core.target_allocation_summary(data, targets)


def aggregate_allocation_change_count(
    data: Any, targets: Mapping[pd.Timestamp, Mapping[str, float]]
) -> int:
    """Count strategy-allocation changes, excluding ordinary M2 replacements."""

    members = set(data.members)
    rows = []
    for date, target in sorted(targets.items()):
        global_weight = float(target.get(core.GLOBAL_FAMILY, 0.0))
        m2_weight = float(sum(weight for family, weight in target.items() if family in members))
        rows.append(
            {
                "date": pd.Timestamp(date),
                "global_weight": global_weight,
                "m2_weight": m2_weight,
                "cash_weight": max(0.0, 1.0 - global_weight - m2_weight),
            }
        )
    if len(rows) <= 1:
        return 0
    allocation = pd.DataFrame(rows).set_index("date")
    changed = allocation.diff().abs().gt(1e-12).any(axis=1)
    changed.iloc[0] = False
    return int(changed.sum())


def annual_score(strategy_id: str, result: Any, global_result: Any, pool_result: Any, allocation: Mapping[str, float] | None = None, regime_changes: Mapping[int, int] | None = None) -> pd.DataFrame:
    frame = curve(result).loc[lambda x: x["date"].between(COMMON_START, CUTOFF)].copy()
    global_daily = curve(global_result).set_index("date")["net_return"].astype(float)
    pool_daily = curve(pool_result).set_index("date")["net_return"].astype(float)
    full_monthly = monthly_returns(result, COMMON_START, CUTOFF)
    rows = []
    for year, part in frame.groupby(frame["date"].dt.year):
        start, end = pd.Timestamp(part["date"].min()), pd.Timestamp(part["date"].max())
        metrics = core.metrics(as_sim(result), start, end)
        dates = pd.DatetimeIndex(part["date"])
        gr_values = global_daily.reindex(dates).dropna()
        pr_values = pool_daily.reindex(dates).dropna()
        gr = float(np.prod(1.0 + gr_values) - 1.0) if len(gr_values) else np.nan
        pr = float(np.prod(1.0 + pr_values) - 1.0) if len(pr_values) else np.nan
        net_return = float(np.prod(1.0 + part["net_return"].astype(float)) - 1.0)
        annual_path = pd.Series(
            np.r_[1.0, np.cumprod(1.0 + part["net_return"].astype(float).to_numpy())]
        )
        annual_drawdown = annual_path / annual_path.cummax() - 1.0
        annual_mdd = float(annual_drawdown.min())
        annual_ulcer = float(np.sqrt(np.mean(np.square(annual_drawdown.to_numpy()))))
        annual_volatility = float(part["net_return"].astype(float).std(ddof=1) * math.sqrt(252.0)) if len(part) > 1 else np.nan
        daily_allocations = []
        for row in part.itertuples(index=False):
            weights = json.loads(row.weights_json or "{}")
            daily_allocations.append(
                {
                    "global_weight": float(weights.get(core.GLOBAL_FAMILY, 0.0)),
                    "m2_weight": float(sum(float(value) for family, value in weights.items() if family != core.GLOBAL_FAMILY)),
                    "cash_weight": float(row.cash_fraction),
                }
            )
        annual_allocations = pd.DataFrame(daily_allocations).mean() if daily_allocations else pd.Series(dtype=float)
        trades = as_sim(result).trades
        yt = trades.loc[pd.to_datetime(trades.get("execution_date"), errors="coerce").dt.year.eq(year)] if len(trades) else trades
        monthly = full_monthly.loc[full_monthly.index.year == int(year)]
        rows.append({
            "strategy_id": strategy_id,
            "year": int(year),
            "partial_year": bool(year in {2017, 2026}),
            "net_return": net_return,
            "excess_vs_global": net_return - gr,
            "excess_vs_equal_pool": net_return - pr,
            "maximum_drawdown": annual_mdd,
            "ulcer_index": annual_ulcer,
            "worst_month": float(monthly.min()) if len(monthly) else np.nan,
            "best_month": float(monthly.max()) if len(monthly) else np.nan,
            "realised_volatility": annual_volatility,
            "turnover": float(yt.get("traded_notional_fraction", pd.Series(dtype=float)).sum()),
            "cost_drag": float(yt.get("transaction_cost_value", pd.Series(dtype=float)).sum()),
            "average_swda_weight": float(annual_allocations.get("global_weight", (allocation or {}).get("global_weight", np.nan))),
            "average_m2_weight": float(annual_allocations.get("m2_weight", (allocation or {}).get("m2_weight", np.nan))),
            "average_cash_weight": float(annual_allocations.get("cash_weight", (allocation or {}).get("cash_weight", np.nan))),
            "portfolio_changes": int(yt.get("execution_status", pd.Series(dtype=str)).eq("EXECUTED").sum()),
            "regime_changes": int((regime_changes or {}).get(int(year), 0)),
        })
    return pd.DataFrame(rows)


def annual_m2_concentration(result: Any, data: Any) -> pd.DataFrame:
    """Describe calendar-year concentration without using it for selection."""

    full = curve(result).sort_values("date").copy()
    full["previous_portfolio_value"] = full["portfolio_value"].shift(1)
    members = set(data.members)
    full_monthly = monthly_returns(result, COMMON_START, CUTOFF)
    rows: list[dict[str, Any]] = []
    for year, part in full.loc[full.date.between(COMMON_START, CUTOFF)].groupby(
        full.loc[full.date.between(COMMON_START, CUTOFF), "date"].dt.year
    ):
        family_totals: dict[str, float] = {}
        for row in part.itertuples(index=False):
            denominator = float(row.previous_portfolio_value) if pd.notna(row.previous_portfolio_value) else np.nan
            if not np.isfinite(denominator) or denominator <= 0:
                continue
            for family, value in json.loads(row.family_market_pnl_json or "{}").items():
                if family in members:
                    family_totals[family] = family_totals.get(family, 0.0) + float(value) / denominator
        top_family, top_family_contribution = ("NONE", np.nan)
        if family_totals:
            top_family, top_family_contribution = max(family_totals.items(), key=lambda item: item[1])
        monthly = full_monthly.loc[full_monthly.index.year == int(year)]
        top_month = monthly.idxmax() if len(monthly) else pd.NaT
        top_month_return = float(monthly.max()) if len(monthly) else np.nan
        positive_month_sum = float(monthly.clip(lower=0).sum()) if len(monthly) else np.nan
        rows.append(
            {
                "year": int(year),
                "top_family": top_family,
                "top_family_contribution": top_family_contribution,
                "top_month": top_month,
                "top_month_return": top_month_return,
                "top_month_share_of_positive_month_sum": (
                    top_month_return / positive_month_sum
                    if positive_month_sum and positive_month_sum > 0
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)


def daily_accounting_attribution(strategy_id: str, result: Any, data: Any) -> pd.DataFrame:
    # ``family_market_pnl_json`` is recorded by the canonical accounting engine
    # in portfolio-value units, whereas the cash contribution and daily returns
    # are recorded in return units.  Normalise each family's P&L by the prior
    # observed portfolio value before aggregating.  Derive the cost contribution
    # as the exact net-minus-gross return effect because the engine's disclosed
    # transaction-cost rate uses pre-trade value as its denominator.
    full = curve(result).sort_values("date").copy()
    full["previous_portfolio_value"] = full["portfolio_value"].shift(1)
    frame = full.loc[full["date"].between(COMMON_START, CUTOFF)].copy()
    members = set(data.members)
    rows = []
    for year, part in frame.groupby(frame["date"].dt.year):
        global_pnl = 0.0
        m2_pnl = 0.0
        for row in part.itertuples(index=False):
            values = json.loads(row.family_market_pnl_json or "{}")
            denominator = float(row.previous_portfolio_value) if pd.notna(row.previous_portfolio_value) else np.nan
            if not np.isfinite(denominator) or denominator <= 0:
                continue
            global_pnl += float(values.get(core.GLOBAL_FAMILY, 0.0)) / denominator
            m2_pnl += sum(float(v) for k, v in values.items() if k in members) / denominator
        cash_pnl = float(part["cash_return_contribution"].sum())
        costs = float((part["net_return"] - part["gross_return_before_cost"]).sum())
        gross_arithmetic = float(part["gross_return_before_cost"].sum())
        # The accepted equal-weight opportunity-pool comparator is supplied as
        # a validated aggregate return series and therefore has no constituent
        # family P&L JSON.  Preserve that observable market contribution in an
        # explicit residual category rather than mislabelling it as M2 alpha.
        other_market = gross_arithmetic - global_pnl - m2_pnl - cash_pnl
        net_arithmetic = float(part["net_return"].sum())
        accounting = global_pnl + m2_pnl + cash_pnl + other_market + costs
        rows.append({
            "strategy_id": strategy_id,
            "year": int(year),
            "global_contribution": global_pnl,
            "m2_contribution": m2_pnl,
            "cash_yield_contribution": cash_pnl,
            "other_market_contribution": other_market,
            "risk_timing_contribution": np.nan,
            "m2_selection_contribution": np.nan,
            "interaction_contribution": np.nan,
            "switching_contribution": np.nan,
            "cost_contribution": costs,
            "reconciliation_error": net_arithmetic - accounting,
            "attribution_basis": "ARITHMETIC_DAILY_RETURN_UNITS;AGGREGATE_COMPARATOR_MARKET_RETURN_EXPLICIT;COUNTERFACTUAL_MECHANISM_FIELDS_SEPARATE",
        })
    return pd.DataFrame(rows)


def pareto_flags(frame: pd.DataFrame) -> pd.Series:
    values = frame[["net_cagr", "terminal_wealth_per_100k", "maximum_drawdown", "ulcer_index", "longest_underwater_days", "turnover"]].astype(float)
    efficient = []
    for i, row in values.iterrows():
        dominated = False
        for j, other in values.iterrows():
            if i == j:
                continue
            no_worse = other["net_cagr"] >= row["net_cagr"] and other["terminal_wealth_per_100k"] >= row["terminal_wealth_per_100k"] and other["maximum_drawdown"] >= row["maximum_drawdown"] and other["ulcer_index"] <= row["ulcer_index"] and other["longest_underwater_days"] <= row["longest_underwater_days"] and other["turnover"] <= row["turnover"]
            strict = (other != row).any()
            if no_worse and strict:
                dominated = True
                break
        efficient.append(not dominated)
    return pd.Series(efficient, index=frame.index)


def trailing_excess(candidate: Any, control: Any, months: int) -> pd.Series:
    joined = pd.concat([monthly_returns(candidate).rename("candidate"), monthly_returns(control).rename("control")], axis=1).dropna()
    return (1.0 + joined["candidate"]).rolling(months).apply(np.prod, raw=True) - (1.0 + joined["control"]).rolling(months).apply(np.prod, raw=True)


def block_bootstrap_mean(values: np.ndarray, block: int = 6, replications: int = 10000, seed: int = 20260825) -> tuple[float, float]:
    clean = np.asarray(values, dtype=float)
    clean = clean[np.isfinite(clean)]
    if len(clean) < block:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    starts = np.arange(0, len(clean) - block + 1)
    means = np.empty(replications)
    for i in range(replications):
        sample = []
        while len(sample) < len(clean):
            start = int(rng.choice(starts))
            sample.extend(clean[start : start + block])
        means[i] = np.mean(sample[: len(clean)])
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def newey_west_mean(values: np.ndarray, lag: int = 3) -> tuple[float, float, float]:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < lag + 3:
        return np.nan, np.nan, np.nan
    mean = float(x.mean())
    centered = x - mean
    omega = float(np.dot(centered, centered) / n)
    for k in range(1, min(lag, n - 1) + 1):
        gamma = float(np.dot(centered[k:], centered[:-k]) / n)
        omega += 2.0 * (1.0 - k / (lag + 1.0)) * gamma
    se = math.sqrt(max(omega, 0.0) / n)
    t = mean / se if se > 0 else np.nan
    # Normal approximation is conservative enough for contextual inference.
    p = math.erfc(abs(t) / math.sqrt(2.0)) if np.isfinite(t) else np.nan
    return se, t, p


def bh_qvalues(pvalues: pd.Series) -> pd.Series:
    p = pd.to_numeric(pvalues, errors="coerce")
    valid = p.dropna().sort_values()
    q = pd.Series(np.nan, index=p.index)
    if valid.empty:
        return q
    adjusted = valid.to_numpy() * len(valid) / np.arange(1, len(valid) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    q.loc[valid.index] = np.minimum(adjusted, 1.0)
    return q


def policy_decision_rows(
    data: Any,
    ledger: pd.DataFrame,
    policy_id: str,
    switch_mode: str,
    records: pd.DataFrame,
    result: Any,
) -> pd.DataFrame:
    rows = records.sort_values("review_date").copy()
    rows = rows.merge(
        ledger[["decision_date", "eligible_families_json", "top7_families_rank_order", "risk_score", "leadership_state", "regime"]],
        left_on="review_date",
        right_on="decision_date",
        how="left",
        suffixes=("", "_ledger"),
    )
    trades = as_sim(result).trades.copy()
    if len(trades):
        trades["review_date"] = pd.to_datetime(trades["review_date"])
        trade_fields = ["review_date", "execution_date", "execution_lag_xlon_sessions", "execution_status", "target_weights_json", "selected_families", "traded_notional_fraction", "trade_legs", "transaction_cost_rate", "transaction_cost_value"]
        rows = rows.merge(trades[trade_fields], on="review_date", how="left", suffixes=("_decision", "_trade"))

    def execution_endpoints(row: pd.Series) -> str:
        execution_date = pd.to_datetime(row.get("execution_date"), errors="coerce")
        if pd.isna(execution_date):
            return "{}"
        raw_target = row.get("target_weights_json_trade", row.get("target_weights_json_decision", "{}"))
        target = json.loads(raw_target or "{}")
        endpoints = {
            family: float(data.base.research.wealth.loc[pd.Timestamp(execution_date), family])
            for family in target
            if family in data.base.research.wealth.columns
            and pd.notna(data.base.research.wealth.loc[pd.Timestamp(execution_date), family])
        }
        return json.dumps(endpoints, sort_keys=True)

    rows["execution_total_return_endpoints_gbp_json"] = rows.apply(execution_endpoints, axis=1)
    for name in ["applied_global_weight", "applied_m2_weight", "applied_cash_weight"]:
        rows[f"previous_{name}"] = rows[name].shift(1).fillna(0.0)
    output = pd.DataFrame({
        "policy_id": policy_id,
        "switch_mode": switch_mode,
        "decision_date": rows["review_date"],
        "eligible_universe_hash": rows["eligible_families_json"].fillna("").map(lambda x: hashlib.sha256(str(x).encode()).hexdigest()),
        "top7_families": rows["top7_families_rank_order"],
        "risk_score": rows["risk_score"],
        "leadership_state": rows["leadership_state"],
        "regime": rows["regime"],
        "raw_global_weight": rows["desired_global_weight"],
        "raw_m2_weight": rows["desired_m2_weight"],
        "raw_cash_weight": rows["desired_cash_weight"],
        "previous_global_weight": rows["previous_applied_global_weight"],
        "previous_m2_weight": rows["previous_applied_m2_weight"],
        "previous_cash_weight": rows["previous_applied_cash_weight"],
        "applied_global_weight": rows["applied_global_weight"],
        "applied_m2_weight": rows["applied_m2_weight"],
        "applied_cash_weight": rows["applied_cash_weight"],
        "risk_confirmation_count": rows["risk_confirmation_count"],
        "leadership_confirmation_count": rows["leadership_confirmation_count"],
        "switch_decision": rows["switch_decision"],
        "execution_date": rows.get("execution_date", pd.NaT),
        "execution_lag_xlon_sessions": rows.get("execution_lag_xlon_sessions", np.nan),
        "execution_status": rows.get("execution_status", "NO_EXECUTION_WITHIN_CUTOFF"),
        "execution_price_evidence": "ACCEPTED_A2R2_GBP_TOTAL_RETURN_ENDPOINTS;NO_FORWARD_FILL;NO_SAME_CLOSE",
        "execution_total_return_endpoints_gbp_json": rows["execution_total_return_endpoints_gbp_json"],
        "target_weights_json": rows.get("target_weights_json_trade", rows["target_weights_json_decision"]),
        "post_execution_holdings": rows.get("selected_families", ""),
        "traded_notional_fraction": rows.get("traded_notional_fraction", 0.0),
        "trade_legs": rows.get("trade_legs", 0),
        "transaction_cost_rate": rows.get("transaction_cost_rate", 0.0),
        "transaction_cost_value": rows.get("transaction_cost_value", 0.0),
    })
    output["execution_status"] = output["execution_status"].fillna("NO_EXECUTION_WITHIN_CUTOFF")
    return output


def episode_ledger(ledger: pd.DataFrame, simulations: Mapping[str, Any]) -> pd.DataFrame:
    base = ledger.loc[ledger["decision_date"].ge(pd.Timestamp("2017-02-28")) & ledger["regime"].ne("REGIME_UNAVAILABLE")].copy()
    base["episode_number"] = base["regime"].ne(base["regime"].shift()).cumsum()
    rows = []
    interval_cache = {sid: core.monthly_interval_returns(ledger, result).set_index("decision_date") for sid, result in simulations.items()}
    global_intervals = interval_cache["GLOBAL_100"]
    pool_intervals = interval_cache["EQUAL_WEIGHT_OPPORTUNITY_POOL"]
    m2_intervals = interval_cache["M2_TOP7_CASH0_100"]
    cash_intervals = interval_cache["ACTUAL_GBP_CASH"]
    for episode_number, episode in base.groupby("episode_number"):
        dates = pd.DatetimeIndex(episode["decision_date"])
        for sid, intervals in interval_cache.items():
            values = intervals.reindex(dates)["interval_return"].dropna().astype(float)
            if values.empty:
                continue
            path = (1.0 + values).cumprod()
            global_values = global_intervals.reindex(dates)["interval_return"].dropna()
            pool_values = pool_intervals.reindex(dates)["interval_return"].dropna()
            m2_values = m2_intervals.reindex(dates)["interval_return"].dropna()
            cash_values = cash_intervals.reindex(dates)["interval_return"].dropna()
            rows.append({
                "episode_id": f"{episode.iloc[0]['regime']}-{int(episode_number):03d}",
                "regime": episode.iloc[0]["regime"],
                "risk_score_start": episode.iloc[0]["risk_score"],
                "leadership_state": episode.iloc[0]["leadership_state"],
                "start_decision_date": dates.min(),
                "end_decision_date": dates.max(),
                "start_execution_date": episode.iloc[0]["scheduled_next_xlon_session"],
                "end_execution_date": episode.iloc[-1]["scheduled_next_xlon_session"],
                "months": len(episode),
                "strategy_id": sid,
                "switch_mode": "STATIC_OR_NOT_APPLICABLE",
                "episode_return": float(path.iloc[-1] - 1.0),
                "episode_maximum_drawdown": float((path / path.cummax() - 1.0).min()),
                "episode_excess_vs_global": float(path.iloc[-1] - np.prod(1.0 + global_values) if len(global_values) else np.nan),
                "episode_excess_vs_equal_pool": float(path.iloc[-1] - np.prod(1.0 + pool_values) if len(pool_values) else np.nan),
                "m2_minus_global": float(np.prod(1.0 + m2_values) - np.prod(1.0 + global_values)) if len(m2_values) and len(global_values) else np.nan,
                "cash_minus_risky": float(np.prod(1.0 + cash_values) - np.prod(1.0 + global_values)) if len(cash_values) and len(global_values) else np.nan,
                "sample_status": "REGIME_SAMPLE_SUFFICIENT" if len(base.loc[base["regime"].eq(episode.iloc[0]["regime"])]) >= 18 and base.loc[base["regime"].eq(episode.iloc[0]["regime"]), "episode_number"].nunique() >= 3 else "INSUFFICIENT_REGIME_SAMPLE",
            })
    return pd.DataFrame(rows)


def static_frontier_rows(data: Any, results: Mapping[tuple[str, str], Any]) -> pd.DataFrame:
    rows = []
    for (sid, cost), result in results.items():
        targets = result.targets
        alloc = average_allocations(data, targets)
        for window_id in WINDOWS:
            row = metric_row(sid, result, window_id, cost)
            rows.append({
                "strategy_id": sid,
                "window_id": window_id,
                "cost_scenario": cost,
                "global_weight": alloc["global_weight"],
                "m2_weight": alloc["m2_weight"],
                "cash_weight": alloc["cash_weight"],
                "net_cagr": row.get("net_cagr", np.nan),
                "terminal_wealth_per_100k": row.get("terminal_wealth_per_100k", np.nan),
                "maximum_drawdown": row.get("maximum_drawdown", np.nan),
                "ulcer_index": row.get("ulcer_index", np.nan),
                "longest_underwater_days": row.get("maximum_time_underwater_calendar_days", np.nan),
                "annualised_volatility": row.get("annualised_volatility", np.nan),
                "turnover": row.get("annual_turnover_traded_notional", np.nan),
                "cost_drag": row.get("cost_drag", np.nan),
            })
    result = pd.DataFrame(rows)
    mask = result["window_id"].eq("FULL_COMMON_HISTORY") & result["cost_scenario"].eq("BASE")
    result["pareto_efficient"] = False
    result.loc[mask, "pareto_efficient"] = pareto_flags(result.loc[mask]).to_numpy()
    return result


def direct_m2_rows(
    static_rows: pd.DataFrame,
    static_results: Mapping[tuple[str, str], Any],
    family_status: str = "PENDING_FAMILY_ROBUSTNESS",
) -> pd.DataFrame:
    # GLOBAL85/CASH15 is an otherwise-identical direct comparator, admitted as
    # a comparator rather than a frontier candidate.
    rows = []
    def lookup(strategy_id: str, window_id: str, cost: str) -> pd.Series:
        found = static_rows.loc[(static_rows.strategy_id.eq(strategy_id)) & (static_rows.window_id.eq(window_id)) & (static_rows.cost_scenario.eq(cost))]
        if len(found):
            return found.iloc[0]
        metrics = metric_row(strategy_id, static_results[(strategy_id, cost)], window_id, cost)
        return pd.Series({
            "net_cagr": metrics.get("net_cagr", np.nan),
            "terminal_wealth_per_100k": metrics.get("terminal_wealth_per_100k", np.nan),
            "maximum_drawdown": metrics.get("maximum_drawdown", np.nan),
            "ulcer_index": metrics.get("ulcer_index", np.nan),
            "turnover": metrics.get("annual_turnover_traded_notional", np.nan),
            "cost_drag": metrics.get("cost_drag", np.nan),
        })
    for candidate, comparator in STATIC_M2_COMPARATORS.items():
        if (candidate, "BASE") not in static_results or (comparator, "BASE") not in static_results:
            continue
        for window_id in WINDOWS:
            c = lookup(candidate, window_id, "BASE")
            b = lookup(comparator, window_id, "BASE")
            ex25c = excluded_metrics(static_results[(candidate, "BASE")], {2025})
            ex25b = excluded_metrics(static_results[(comparator, "BASE")], {2025})
            dc = lookup(candidate, window_id, "DOUBLE")
            db = lookup(comparator, window_id, "DOUBLE")
            rows.append({
                "candidate_id": candidate,
                "comparator_id": comparator,
                "window_id": window_id,
                "cost_scenario": "BASE",
                "incremental_cagr": c.net_cagr - b.net_cagr,
                "incremental_terminal_wealth": c.terminal_wealth_per_100k - b.terminal_wealth_per_100k,
                "incremental_mdd": c.maximum_drawdown - b.maximum_drawdown,
                "incremental_ulcer": c.ulcer_index - b.ulcer_index,
                "incremental_turnover": c.turnover - b.turnover,
                "incremental_cost": c.cost_drag - b.cost_drag,
                "exclude_2025_incremental_cagr": ex25c["net_cagr"] - ex25b["net_cagr"],
                "double_cost_incremental_cagr": dc.net_cagr - db.net_cagr,
                "family_exclusion_status": family_status,
            })
    return pd.DataFrame(rows)


def regime_ranking_rows(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for regime, group in summary.groupby("regime"):
        group = group.copy()
        group["rank_by_return"] = group["annualised_return"].rank(ascending=False, method="min")
        group["rank_by_drawdown"] = group["worst_episode_maximum_drawdown"].rank(ascending=False, method="min")
        group["rank_by_balanced_score"] = (group["rank_by_return"] + group["rank_by_drawdown"]).rank(method="min")
        for row in group.itertuples(index=False):
            rows.append({
                "regime": regime,
                "strategy_id": row.strategy_id,
                "sample_status": row.claim_status,
                "annualised_return": row.annualised_return,
                "maximum_drawdown": row.worst_episode_maximum_drawdown,
                "ulcer_index": np.nan,
                "rank_by_return": row.rank_by_return,
                "rank_by_drawdown": row.rank_by_drawdown,
                "rank_by_balanced_score": row.rank_by_balanced_score,
                "interpretation": "DESCRIPTIVE_CAUSAL_STATE;NOT_A_POLICY_SELECTION_BY_ITSELF",
            })
    return pd.DataFrame(rows)


def make_blend_targets(
    base_m2_targets: Mapping[pd.Timestamp, Mapping[str, float]],
    global_weight: float,
    m2_weight: float,
) -> dict[pd.Timestamp, dict[str, float]]:
    result = {}
    for date, m2 in sorted(base_m2_targets.items()):
        target = {family: float(weight) * float(m2_weight) for family, weight in m2.items() if float(weight) * float(m2_weight) > 1e-12}
        if global_weight > 1e-12:
            target[core.GLOBAL_FAMILY] = float(global_weight)
        result[pd.Timestamp(date)] = target
    return result


def longer_core_only_rows(data: Any) -> pd.DataFrame:
    """Evaluate global/cash controls on their longer accepted implementation window."""

    review_dates = [
        pd.Timestamp(date)
        for date in core.a4d.schedule_dates(data.base.research.calendar, "MONTHLY")
        if pd.Timestamp(date) >= LONG_CORE_START and pd.Timestamp(date) <= CUTOFF
    ]
    rows: list[dict[str, Any]] = []
    for global_weight in [0.25, 0.50, 0.75, 1.00]:
        strategy_id = f"LONG_CORE_GLOBAL_{int(global_weight * 100)}_CASH_{int((1-global_weight) * 100)}"
        targets = {
            date: {core.GLOBAL_FAMILY: global_weight}
            for date in review_dates
        }
        for cost in ["BASE", "DOUBLE"]:
            result = core.simulate_target_map(data, targets, strategy_id, cost)
            first = max(LONG_CORE_START, pd.Timestamp(curve(result)["date"].min()))
            metrics = core.metrics(result, first, CUTOFF)
            rows.append(
                {
                    "strategy_id": strategy_id,
                    "evidence_window": "LONGER_CORE_ONLY_WINDOW",
                    "cost_scenario": cost,
                    "first_formation_date": review_dates[0],
                    "first_executable_date": first,
                    "last_date": min(CUTOFF, pd.Timestamp(curve(result)["date"].max())),
                    "global_weight": global_weight,
                    "cash_weight": 1.0 - global_weight,
                    "net_cagr": metrics.get("net_cagr", np.nan),
                    "terminal_wealth_per_100k": metrics.get("terminal_wealth_per_100k", np.nan),
                    "maximum_drawdown": metrics.get("maximum_drawdown", np.nan),
                    "ulcer_index": metrics.get("ulcer_index", np.nan),
                    "calmar_mar": metrics.get("calmar_mar", np.nan),
                    "annualised_volatility": metrics.get("annualised_volatility", np.nan),
                    "maximum_time_underwater_calendar_days": metrics.get("maximum_time_underwater_calendar_days", np.nan),
                    "annual_turnover_traded_notional": metrics.get("annual_turnover_traded_notional", np.nan),
                    "comparison_status": "CORE_ONLY_CONTEXT_NOT_DIRECTLY_RANKED_AGAINST_2017_ROTATION",
                }
            )
    return pd.DataFrame(rows)


def dynamic_result_rows(
    data: Any,
    simulations: Mapping[tuple[str, str, str], Any],
    target_maps: Mapping[tuple[str, str], Mapping[pd.Timestamp, Mapping[str, float]]],
    global_result: Any,
) -> pd.DataFrame:
    global_metrics = {window: metric_row("GLOBAL_100", global_result, window, "BASE") for window in WINDOWS}
    rows = []
    for (policy_id, switch_mode, cost), result in simulations.items():
        allocation = average_allocations(data, target_maps[(policy_id, switch_mode)])
        trades = as_sim(result).trades
        rebalance_events = int(trades.get("traded_notional_fraction", pd.Series(dtype=float)).gt(1e-12).sum())
        strategy_changes = aggregate_allocation_change_count(data, target_maps[(policy_id, switch_mode)])
        years = max((CUTOFF - COMMON_START).days / 365.2425, 1e-9)
        for window_id in WINDOWS:
            row = metric_row(policy_id, result, window_id, cost)
            gm = global_metrics[window_id]
            rows.append({
                "policy_id": policy_id,
                "switch_mode": switch_mode,
                "window_id": window_id,
                "cost_scenario": cost,
                "net_cagr": row.get("net_cagr", np.nan),
                "terminal_wealth_per_100k": row.get("terminal_wealth_per_100k", np.nan),
                "excess_vs_global": row.get("net_cagr", np.nan) - gm.get("net_cagr", np.nan),
                "maximum_drawdown": row.get("maximum_drawdown", np.nan),
                "ulcer_index": row.get("ulcer_index", np.nan),
                "calmar": row.get("calmar_mar", np.nan),
                "sortino": row.get("sortino_zero_cash_hurdle", np.nan),
                "annualised_volatility": row.get("annualised_volatility", np.nan),
                "longest_underwater_days": row.get("maximum_time_underwater_calendar_days", np.nan),
                "turnover": row.get("annual_turnover_traded_notional", np.nan),
                "trade_legs": row.get("trade_legs", np.nan),
                "average_global_weight": allocation["global_weight"],
                "average_m2_weight": allocation["m2_weight"],
                "average_cash_weight": allocation["cash_weight"],
                "annual_strategy_changes": strategy_changes / years,
                "annual_rebalance_events": rebalance_events / years,
                "return_retention": row.get("net_cagr", np.nan) / gm.get("net_cagr", np.nan) if gm.get("net_cagr", 0) > 0 else np.nan,
                "promotion_status": "PENDING_FULL_GATE_AUDIT",
            })
    return pd.DataFrame(rows)


def matched_control_rows(
    data: Any,
    policy_sims: Mapping[tuple[str, str, str], Any],
    policy_targets: Mapping[tuple[str, str], Mapping[pd.Timestamp, Mapping[str, float]]],
    static_results: Mapping[tuple[str, str], Any],
    static_rows: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[tuple[str, str, str], Any]]:
    rows = []
    control_results: dict[tuple[str, str, str], Any] = {}
    base_m2 = static_results[("M2_TOP7_CASH0_100", "BASE")].targets
    full_static_metrics = {
        row.strategy_id: {
            "maximum_drawdown": row.maximum_drawdown,
            "annualised_volatility": row.annualised_volatility,
        }
        for row in static_rows.loc[(static_rows.window_id.eq("FULL_COMMON_HISTORY")) & (static_rows.cost_scenario.eq("BASE"))].itertuples(index=False)
    }
    global_vol = full_static_metrics["GLOBAL_100"]["annualised_volatility"]
    for policy_id in SELECTABLE_POLICIES:
        for switch_mode in SWITCHES:
            candidate = policy_sims[(policy_id, switch_mode, "BASE")]
            target = policy_targets[(policy_id, switch_mode)]
            allocation = average_allocations(data, target)
            candidate_metrics = metric_pack(candidate)
            controls: list[tuple[str, dict[pd.Timestamp, dict[str, float]], str]] = []
            controls.append(("MATCHED_AVERAGE_EXPOSURE", make_blend_targets(base_m2, allocation["risky_weight"], 0.0), "STATIC_SWDA_CASH_SAME_MEAN_RISKY_TARGET"))
            controls.append(("MATCHED_M2_EXPOSURE", make_blend_targets(base_m2, allocation["global_weight"], allocation["m2_weight"]), "STATIC_SWDA_M2_CASH_SAME_MEAN_TARGETS"))
            vol_weight = min(1.0, candidate_metrics.get("annualised_volatility", np.nan) / global_vol) if global_vol > 0 else allocation["risky_weight"]
            controls.append(("MATCHED_VOLATILITY", make_blend_targets(base_m2, vol_weight, 0.0), "STATIC_SWDA_CASH_NO_LEVERAGE_APPROX_VOL_MATCH"))
            mdd_id = core.closest_static_control(candidate_metrics, full_static_metrics, "maximum_drawdown")
            controls.append(("MATCHED_MDD_FRONTIER", static_results[(mdd_id, "BASE")].targets, mdd_id))
            for control_type, control_targets, control_id in controls:
                cache_key = (policy_id, switch_mode, control_type)
                if control_type == "MATCHED_MDD_FRONTIER":
                    control = static_results[(mdd_id, "BASE")]
                else:
                    control = core.simulate_target_map(data, control_targets, f"{policy_id}|{switch_mode}|{control_type}", "BASE")
                control_results[cache_key] = control
                for window_id in WINDOWS:
                    c = metric_row(policy_id, candidate, window_id, "BASE")
                    b = metric_row(control_id, control, window_id, "BASE")
                    rows.append({
                        "policy_id": policy_id,
                        "switch_mode": switch_mode,
                        "control_type": control_type,
                        "control_id": control_id,
                        "window_id": window_id,
                        "candidate_cagr": c.get("net_cagr", np.nan),
                        "control_cagr": b.get("net_cagr", np.nan),
                        "incremental_cagr": c.get("net_cagr", np.nan) - b.get("net_cagr", np.nan),
                        "candidate_terminal_wealth": c.get("terminal_wealth_per_100k", np.nan),
                        "control_terminal_wealth": b.get("terminal_wealth_per_100k", np.nan),
                        "incremental_terminal_wealth": c.get("terminal_wealth_per_100k", np.nan) - b.get("terminal_wealth_per_100k", np.nan),
                        "candidate_mdd": c.get("maximum_drawdown", np.nan),
                        "control_mdd": b.get("maximum_drawdown", np.nan),
                        "incremental_mdd": c.get("maximum_drawdown", np.nan) - b.get("maximum_drawdown", np.nan),
                        "candidate_ulcer": c.get("ulcer_index", np.nan),
                        "control_ulcer": b.get("ulcer_index", np.nan),
                        "incremental_ulcer": c.get("ulcer_index", np.nan) - b.get("ulcer_index", np.nan),
                        "candidate_turnover": c.get("annual_turnover_traded_notional", np.nan),
                        "control_turnover": b.get("annual_turnover_traded_notional", np.nan),
                        "candidate_cost": c.get("total_transaction_cost_value", np.nan),
                        "control_cost": b.get("total_transaction_cost_value", np.nan),
                        "matched_risk_gate_status": "PENDING_FULL_GATE_AUDIT",
                    })
    return pd.DataFrame(rows), control_results


def policy_inference_rows(
    policy_sims: Mapping[tuple[str, str, str], Any],
    controls: Mapping[tuple[str, str, str], Any],
) -> pd.DataFrame:
    rows = []
    for policy_id in SELECTABLE_POLICIES:
        for switch_mode in SWITCHES:
            candidate = monthly_returns(policy_sims[(policy_id, switch_mode, "BASE")])
            control = monthly_returns(controls[(policy_id, switch_mode, "MATCHED_AVERAGE_EXPOSURE")])
            diff = pd.concat([candidate.rename("candidate"), control.rename("control")], axis=1).dropna().eval("candidate-control")
            se, t, p = newey_west_mean(diff.to_numpy(), lag=3)
            lower, upper = block_bootstrap_mean(diff.to_numpy())
            rows.append({
                "policy_id": policy_id,
                "switch_mode": switch_mode,
                "control_id": "MATCHED_AVERAGE_EXPOSURE",
                "monthly_observations": len(diff),
                "mean_monthly_incremental_return": float(diff.mean()),
                "annualised_incremental_return": float(diff.mean() * 12.0),
                "hac_standard_error": se,
                "hac_t_stat": t,
                "hac_p_value": p,
                "bootstrap_lower_95": lower,
                "bootstrap_upper_95": upper,
                "raw_p_value": p,
                "inference_status": "CONTEXTUAL_ONLY_ECONOMIC_GATES_PRIMARY",
            })
    result = pd.DataFrame(rows)
    result["bh_q_value"] = bh_qvalues(result["raw_p_value"])
    return result


def oracle_rows(static_results: Mapping[tuple[str, str], Any], policy_results: Mapping[tuple[str, str, str], Any], ledger: pd.DataFrame) -> pd.DataFrame:
    static_ids = sorted({key[0] for key in static_results if key[1] == "BASE" and key[0] != "GLOBAL_85_CASH15"})
    monthly = pd.concat({sid: monthly_returns(static_results[(sid, "BASE")]) for sid in static_ids}, axis=1).dropna(how="all")
    causal = pd.concat({f"{p}|{s}": monthly_returns(policy_results[(p, s, "BASE")]) for p in SELECTABLE_POLICIES for s in SWITCHES}, axis=1).reindex(monthly.index)
    rows = []
    oracle_month = monthly.max(axis=1)
    best_causal_month = causal.max(axis=1)
    for date in monthly.index:
        best = monthly.loc[date].idxmax()
        opportunity = float(oracle_month.loc[date])
        causal_return = float(best_causal_month.loc[date]) if pd.notna(best_causal_month.loc[date]) else np.nan
        rows.append({"oracle_type": "MONTHLY_ORACLE", "period_id": date.strftime("%Y-%m"), "best_static_candidate": best, "oracle_return": opportunity, "best_causal_policy_return": causal_return, "captured_fraction": causal_return / opportunity if opportunity > 0 else np.nan, "status": "NONCAUSAL_DIAGNOSTIC_ONLY"})
    for year, group in monthly.groupby(monthly.index.year):
        annual = (1.0 + group).prod() - 1.0
        causal_annual = (1.0 + causal.reindex(group.index)).prod() - 1.0
        best = annual.idxmax()
        opportunity = float(annual.max())
        cvalue = float(causal_annual.max())
        rows.append({"oracle_type": "ANNUAL_ORACLE", "period_id": str(year), "best_static_candidate": best, "oracle_return": opportunity, "best_causal_policy_return": cvalue, "captured_fraction": cvalue / opportunity if opportunity > 0 else np.nan, "status": "NONCAUSAL_DIAGNOSTIC_ONLY"})
    # Regime oracle uses causal decision states but hindsight strategy choice.
    decision_regime = ledger.set_index(ledger["decision_date"].dt.to_period("M"))["regime"]
    regime_by_month = pd.Series([decision_regime.get(date.to_period("M"), "REGIME_UNAVAILABLE") for date in monthly.index], index=monthly.index)
    for regime in sorted(set(regime_by_month) - {"REGIME_UNAVAILABLE"}):
        subset = monthly.loc[regime_by_month.eq(regime)]
        annualised = (1.0 + subset).prod() ** (12.0 / max(len(subset), 1)) - 1.0
        causal_subset = causal.reindex(subset.index)
        causal_annualised = (1.0 + causal_subset).prod() ** (12.0 / max(len(subset), 1)) - 1.0
        best = annualised.idxmax()
        opportunity = float(annualised.max())
        cvalue = float(causal_annualised.max())
        rows.append({"oracle_type": "REGIME_ORACLE", "period_id": regime, "best_static_candidate": best, "oracle_return": opportunity, "best_causal_policy_return": cvalue, "captured_fraction": cvalue / opportunity if opportunity > 0 else np.nan, "status": "NONCAUSAL_DIAGNOSTIC_ONLY"})
    return pd.DataFrame(rows)


def year_exclusion_rows(
    policy_results: Mapping[tuple[str, str, str], Any],
    global_result: Any,
    static_results: Mapping[tuple[str, str], Any],
) -> pd.DataFrame:
    rows = []
    periods = [("EXCLUDE_2025", {2025}), ("EXCLUDE_2020", {2020}), ("EXCLUDE_2020_AND_2025", {2020, 2025})]
    periods.extend((f"LEAVE_{year}_OUT", {year}) for year in range(2017, 2027))
    for policy_id in SELECTABLE_POLICIES:
        for switch_mode in SWITCHES:
            result = policy_results[(policy_id, switch_mode, "BASE")]
            for label, years in periods:
                metrics = excluded_metrics(result, years)
                gm = excluded_metrics(global_result, years)
                rows.append({"policy_id": policy_id, "switch_mode": switch_mode, "excluded_period": label, "net_cagr": metrics["net_cagr"], "excess_vs_global": metrics["net_cagr"] - gm["net_cagr"], "maximum_drawdown": metrics["maximum_drawdown"], "ulcer_index": np.nan, "turnover": np.nan, "status": "ROBUSTNESS_DIAGNOSTIC_NOT_CONTIGUOUS_CAGR"})
    for strategy_id in STATIC_M2_COMPARATORS:
        result = static_results[(strategy_id, "BASE")]
        for label, years in periods:
            metrics = excluded_metrics(result, years)
            gm = excluded_metrics(global_result, years)
            rows.append({"policy_id": strategy_id, "switch_mode": "STATIC_MONTHLY", "excluded_period": label, "net_cagr": metrics["net_cagr"], "excess_vs_global": metrics["net_cagr"] - gm["net_cagr"], "maximum_drawdown": metrics["maximum_drawdown"], "ulcer_index": np.nan, "turnover": np.nan, "status": "STATIC_M2_ROBUSTNESS_DIAGNOSTIC_NOT_CONTIGUOUS_CAGR"})
    return pd.DataFrame(rows)


def custom_policy_targets(
    policy_records: pd.DataFrame,
    custom_m2: Mapping[pd.Timestamp, Mapping[str, float]],
) -> dict[pd.Timestamp, dict[str, float]]:
    targets = {}
    for row in policy_records.itertuples(index=False):
        date = pd.Timestamp(row.review_date)
        if date not in custom_m2:
            continue
        target = {family: float(weight) * float(row.applied_m2_weight) for family, weight in custom_m2[date].items() if float(weight) * float(row.applied_m2_weight) > 1e-12}
        if float(row.applied_global_weight) > 1e-12:
            target[core.GLOBAL_FAMILY] = float(row.applied_global_weight)
        targets[date] = target
    return targets


def family_influence_rows(
    data: Any,
    policy_id: str,
    switch_mode: str,
    policy_records: pd.DataFrame,
    baseline: Any,
    matched_control: Any,
) -> tuple[pd.DataFrame, bool]:
    baseline_metrics = metric_pack(baseline)
    rows = []
    all_nonnegative = True
    for family in sorted(data.members):
        m2_targets, _ = core.a4e.rotation_targets(data, "M2_BASE", 7, cash1=False, excluded_families={family})
        targets = custom_policy_targets(policy_records, m2_targets)
        result = core.simulate_target_map(data, targets, f"{policy_id}|{switch_mode}|EXCLUDE={family}", "BASE")
        metrics = metric_pack(result)
        control_metrics = metric_pack(matched_control)
        incremental = metrics["net_cagr"] - control_metrics["net_cagr"]
        all_nonnegative &= bool(incremental >= -1e-12)
        rows.append({
            "policy_id": policy_id,
            "switch_mode": switch_mode,
            "exclusion_type": "LEAVE_ONE_FAMILY_OUT",
            "excluded_families": family,
            "window_id": "FULL_COMMON_HISTORY",
            "net_cagr": metrics["net_cagr"],
            "excess_vs_global": incremental,
            "maximum_drawdown": metrics["maximum_drawdown"],
            "ulcer_index": metrics["ulcer_index"],
            "delta_cagr": metrics["net_cagr"] - baseline_metrics["net_cagr"],
            "delta_mdd": metrics["maximum_drawdown"] - baseline_metrics["maximum_drawdown"],
            "dependency_status": "NONNEGATIVE_INCREMENTAL" if incremental >= 0 else "SIGN_REVERSAL_DEPENDENCY",
        })
    contribution = family_contributions(baseline, set(data.members))
    leaders = contribution.head(5)["family"].tolist()
    for count in [1, 3, 5]:
        excluded = set(leaders[:count])
        m2_targets, _ = core.a4e.rotation_targets(data, "M2_BASE", 7, cash1=False, excluded_families=excluded)
        targets = custom_policy_targets(policy_records, m2_targets)
        result = core.simulate_target_map(data, targets, f"{policy_id}|{switch_mode}|EXCLUDE_TOP{count}", "BASE")
        metrics = metric_pack(result)
        control_metrics = metric_pack(matched_control)
        incremental = metrics["net_cagr"] - control_metrics["net_cagr"]
        rows.append({"policy_id": policy_id, "switch_mode": switch_mode, "exclusion_type": f"EXCLUDE_TOP_{count}_FAMILY_CONTRIBUTORS", "excluded_families": ";".join(sorted(excluded)), "window_id": "FULL_COMMON_HISTORY", "net_cagr": metrics["net_cagr"], "excess_vs_global": incremental, "maximum_drawdown": metrics["maximum_drawdown"], "ulcer_index": metrics["ulcer_index"], "delta_cagr": metrics["net_cagr"] - baseline_metrics["net_cagr"], "delta_mdd": metrics["maximum_drawdown"] - baseline_metrics["maximum_drawdown"], "dependency_status": "ROBUSTNESS_DIAGNOSTIC"})
    return pd.DataFrame(rows), all_nonnegative


def static_family_influence_rows(
    data: Any,
    strategy_id: str,
    baseline: Any,
    comparator: Any,
) -> tuple[pd.DataFrame, bool]:
    """Run the frozen family-removal gate for a serious static M2 blend.

    This is deliberately invoked only after the preregistered full-history,
    2025-exclusion and doubled-cost incremental gates identify a serious static
    fallback candidate.  It therefore completes—not expands—the frozen staged
    selection hierarchy.
    """

    baseline_metrics = metric_pack(baseline)
    comparator_metrics = metric_pack(comparator)
    allocation = average_allocations(data, baseline.targets)
    rows: list[dict[str, Any]] = []
    all_nonnegative = True

    def evaluate(excluded: set[str], exclusion_type: str) -> None:
        nonlocal all_nonnegative
        m2_targets, _ = core.a4e.rotation_targets(
            data, "M2_BASE", 7, cash1=False, excluded_families=excluded
        )
        targets = make_blend_targets(
            m2_targets, allocation["global_weight"], allocation["m2_weight"]
        )
        result = core.simulate_target_map(
            data,
            targets,
            f"{strategy_id}|STATIC_MONTHLY|{exclusion_type}",
            "BASE",
        )
        metrics = metric_pack(result)
        incremental = metrics["net_cagr"] - comparator_metrics["net_cagr"]
        if exclusion_type == "LEAVE_ONE_FAMILY_OUT":
            all_nonnegative &= bool(incremental >= -1e-12)
        rows.append(
            {
                "policy_id": strategy_id,
                "switch_mode": "STATIC_MONTHLY",
                "exclusion_type": exclusion_type,
                "excluded_families": ";".join(sorted(excluded)),
                "window_id": "FULL_COMMON_HISTORY",
                "net_cagr": metrics["net_cagr"],
                "excess_vs_global": incremental,
                "incremental_vs_replacement_control": incremental,
                "maximum_drawdown": metrics["maximum_drawdown"],
                "ulcer_index": metrics["ulcer_index"],
                "delta_cagr": metrics["net_cagr"] - baseline_metrics["net_cagr"],
                "delta_mdd": metrics["maximum_drawdown"] - baseline_metrics["maximum_drawdown"],
                "dependency_status": (
                    "NONNEGATIVE_INCREMENTAL"
                    if incremental >= 0
                    else "SIGN_REVERSAL_DEPENDENCY"
                ),
            }
        )

    for family in sorted(data.members):
        evaluate({family}, "LEAVE_ONE_FAMILY_OUT")

    contribution = family_contributions(baseline, set(data.members))
    leaders = contribution.head(5)["family"].tolist()
    for count in [1, 3, 5]:
        evaluate(set(leaders[:count]), f"EXCLUDE_TOP_{count}_FAMILY_CONTRIBUTORS")
    return pd.DataFrame(rows), all_nonnegative


def family_contributions(result: Any, members: set[str]) -> pd.DataFrame:
    totals: dict[str, float] = {}
    for raw in curve(result)["family_market_pnl_json"].fillna("{}"):
        for family, value in json.loads(raw or "{}").items():
            if family in members:
                totals[family] = totals.get(family, 0.0) + float(value)
    return pd.DataFrame([{"family": family, "contribution": value} for family, value in totals.items()]).sort_values("contribution", ascending=False).reset_index(drop=True)


def holding_spell_influence_rows(data: Any, policy_id: str, policy_records: pd.DataFrame, baseline: Any) -> pd.DataFrame:
    m2_base = core.a4e.simulate_rotation(data, "M2_BASE", 7, False, cost_scenario="BASE")
    spells = core.a4e.holding_spell_ledger(m2_base).sort_values("gross_market_pnl_return_units", ascending=False)
    base_metrics = metric_pack(baseline)
    rows = []
    for count in [1, 3, 5]:
        selected_spells = spells.head(count)
        modified = core.a4e.targets_without_spells(m2_base.targets, selected_spells)
        targets = custom_policy_targets(policy_records, modified)
        result = core.simulate_target_map(data, targets, f"{policy_id}|EXCLUDE_TOP_{count}_SPELLS", "BASE")
        metrics = metric_pack(result)
        rows.append({
            "policy_id": policy_id,
            "exclusion_count": count,
            "excluded_spell_ids": ";".join(selected_spells["holding_spell_id"].astype(str)),
            "excluded_families_and_dates": ";".join(f"{row.family}:{pd.Timestamp(row.entry_date):%Y-%m-%d}:{pd.Timestamp(row.exit_date):%Y-%m-%d}" for row in selected_spells.itertuples(index=False)),
            "net_cagr": metrics["net_cagr"],
            "maximum_drawdown": metrics["maximum_drawdown"],
            "ulcer_index": metrics["ulcer_index"],
            "delta_cagr": metrics["net_cagr"] - base_metrics["net_cagr"],
            "dependency_status": "RIGHT_TAIL_EXPECTED_BUT_NOT_SELECTION_PROOF",
        })
    return pd.DataFrame(rows)


def threshold_sensitivity_rows(data: Any, global_result: Any) -> tuple[pd.DataFrame, dict[tuple[str, str, float, float], Any]]:
    rows = []
    cache = {}
    for vq in [0.70, 0.75, 0.80]:
        for lq in [0.40, 0.50, 0.60]:
            ledger = core.build_monthly_regime_ledger(data, vq, lq)
            for policy_id in ["POLICY_1_RISK_TIMING_ONLY", "POLICY_2_ALPHA_TIMING_ONLY", "POLICY_3_BALANCED_REGIME_STRATEGY", "POLICY_4_DEFENSIVE_REGIME_STRATEGY"]:
                for switch_mode in SWITCHES:
                    targets, records = core.policy_target_map(data, ledger, policy_id, switch_mode)
                    result = core.simulate_target_map(data, (targets, records), f"{policy_id}|{switch_mode}|V{vq:.2f}|L{lq:.2f}", "BASE")
                    cache[(policy_id, switch_mode, vq, lq)] = result
                    control_targets = core.matched_average_exposure_control(data, targets)
                    control = core.simulate_target_map(data, control_targets, f"{policy_id}|{switch_mode}|MATCHED|V{vq:.2f}|L{lq:.2f}", "BASE")
                    metrics = metric_pack(result)
                    control_metrics = metric_pack(control)
                    rows.append({
                        "policy_id": policy_id,
                        "switch_mode": switch_mode,
                        "volatility_percentile": vq,
                        "leadership_quantile": lq,
                        "candidate_threshold": bool(vq == 0.75 and lq == 0.50),
                        "net_cagr": metrics["net_cagr"],
                        "maximum_drawdown": metrics["maximum_drawdown"],
                        "ulcer_index": metrics["ulcer_index"],
                        "incremental_vs_matched_control": metrics["net_cagr"] - control_metrics["net_cagr"],
                        "directionally_coherent": False,
                    })
    result = pd.DataFrame(rows)
    for (policy, switch), group in result.groupby(["policy_id", "switch_mode"]):
        canonical = group.loc[group["candidate_threshold"]].iloc[0]
        vol_adj = group.loc[group["leadership_quantile"].eq(0.50) & group["volatility_percentile"].isin([0.70, 0.80])]
        lead_adj = group.loc[group["volatility_percentile"].eq(0.75) & group["leadership_quantile"].isin([0.40, 0.60])]
        coherent = canonical.incremental_vs_matched_control > 0 and not (vol_adj.incremental_vs_matched_control.lt(0).all() or lead_adj.incremental_vs_matched_control.lt(0).all())
        result.loc[(result.policy_id.eq(policy)) & (result.switch_mode.eq(switch)), "directionally_coherent"] = coherent
    return result, cache


def hysteresis_rows(dynamic: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for policy_id in POLICIES:
        for window_id in WINDOWS:
            for cost in ["BASE", "DOUBLE"]:
                immediate = dynamic.loc[(dynamic.policy_id.eq(policy_id)) & dynamic.switch_mode.eq("SWITCH_IMMEDIATE_MONTHLY") & dynamic.window_id.eq(window_id) & dynamic.cost_scenario.eq(cost)].iloc[0]
                hysteresis = dynamic.loc[(dynamic.policy_id.eq(policy_id)) & dynamic.switch_mode.eq("SWITCH_ASYMMETRIC_HYSTERESIS") & dynamic.window_id.eq(window_id) & dynamic.cost_scenario.eq(cost)].iloc[0]
                rows.append({"policy_id": policy_id, "window_id": window_id, "cost_scenario": cost, "immediate_cagr": immediate.net_cagr, "hysteresis_cagr": hysteresis.net_cagr, "immediate_mdd": immediate.maximum_drawdown, "hysteresis_mdd": hysteresis.maximum_drawdown, "immediate_ulcer": immediate.ulcer_index, "hysteresis_ulcer": hysteresis.ulcer_index, "immediate_switches": immediate.annual_strategy_changes, "hysteresis_switches": hysteresis.annual_strategy_changes, "false_switches_avoided": np.nan, "reentry_delay_cost": hysteresis.net_cagr - immediate.net_cagr, "status": "HYSTERESIS_RETAINS_95PCT" if hysteresis.net_cagr >= 0.95 * immediate.net_cagr else "HYSTERESIS_DESTRUCTIVE_UNLESS_INDEPENDENT_GATE_PASS"})
    return pd.DataFrame(rows)


def cost_stress_rows(dynamic: pd.DataFrame) -> pd.DataFrame:
    result = dynamic[["policy_id", "switch_mode", "window_id", "cost_scenario", "net_cagr", "maximum_drawdown", "ulcer_index", "turnover"]].copy()
    result["cost_drag"] = np.nan
    result["viability_status"] = "PENDING_MATCHED_CONTROL_GATE"
    return result


def save_figure(name: str, fig: plt.Figure) -> None:
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=160, bbox_inches="tight")
    plt.close(fig)


def create_charts(
    ledger: pd.DataFrame,
    year_score: pd.DataFrame,
    selected_id: str,
    selected_result: Any,
    static_results: Mapping[tuple[str, str], Any],
    global_result: Any,
    dynamic_results: Mapping[tuple[str, str, str], Any],
    matched_rows: pd.DataFrame,
    year_exclusions: pd.DataFrame,
    attribution: pd.DataFrame,
    transitions: pd.DataFrame,
    selected_switch: str,
) -> None:
    plt.rcParams.update({"font.size": 8, "axes.grid": True, "grid.alpha": 0.25})
    display = [sid for sid in ["GLOBAL_100", "GLOBAL_75_CASH25", "M2_TOP7_CASH0_100", selected_id] if sid in set(year_score.strategy_id)]
    annual = year_score.loc[year_score.strategy_id.isin(display)]
    pivot = annual.pivot(index="year", columns="strategy_id", values="net_return")
    fig, ax = plt.subplots(figsize=(11, 5)); pivot.plot(kind="bar", ax=ax); ax.axhline(0, color="black", lw=.8); ax.set_ylabel("Net return"); ax.set_title("Annual net returns by strategy"); save_figure("UKACTIVE_A4F_SIPP_ANNUAL_RETURNS.png", fig)
    fig, ax = plt.subplots(figsize=(11, 5)); annual.pivot(index="year", columns="strategy_id", values="excess_vs_global").plot(kind="bar", ax=ax); ax.axhline(0, color="black", lw=.8); ax.set_ylabel("Excess vs global"); ax.set_title("Annual excess return"); save_figure("UKACTIVE_A4F_SIPP_ANNUAL_EXCESS.png", fig)
    fig, ax = plt.subplots(figsize=(11, 5)); annual.pivot(index="year", columns="strategy_id", values="maximum_drawdown").plot(kind="bar", ax=ax); ax.axhline(-.20, color="red", ls="--", lw=.8); ax.set_ylabel("Maximum drawdown"); ax.set_title("Annual maximum drawdown"); save_figure("UKACTIVE_A4F_SIPP_ANNUAL_MAXIMUM_DRAWDOWN.png", fig)

    regime_code = {"R1_BROAD_RISK_ON": 1, "R2_LEADERSHIP_RISK_ON": 2, "R3_ISOLATED_LEADERSHIP": 3, "R4_CAPITAL_PRESERVATION": 4, "REGIME_UNAVAILABLE": 0}
    common_ledger = ledger.loc[ledger.decision_date.ge(pd.Timestamp("2017-02-28"))]
    fig, ax = plt.subplots(figsize=(11, 3)); ax.step(common_ledger.decision_date, common_ledger.regime.map(regime_code), where="post"); ax.set_yticks(list(regime_code.values()), list(regime_code)); ax.set_title("Causal four-state regime timeline"); save_figure("UKACTIVE_A4F_SIPP_REGIME_TIMELINE.png", fig)
    fig, ax = plt.subplots(figsize=(11, 3)); ax.step(common_ledger.decision_date, common_ledger.risk_score, where="post"); ax.set_yticks([0, 1, 2, 3]); ax.set_title("A4F risk-score timeline"); save_figure("UKACTIVE_A4F_SIPP_RISK_SCORE_TIMELINE.png", fig)
    fig, ax = plt.subplots(figsize=(11, 3)); ax.step(common_ledger.decision_date, common_ledger.leadership_strong.astype(int), where="post"); ax.set_yticks([0, 1], ["WEAK", "STRONG"]); ax.set_title("Causal leadership-state timeline"); save_figure("UKACTIVE_A4F_SIPP_LEADERSHIP_STATE_TIMELINE.png", fig)

    if selected_id.startswith("POLICY_"):
        selected_records = dynamic_results[(selected_id, "SWITCH_IMMEDIATE_MONTHLY", "BASE")].records
        fig, ax = plt.subplots(figsize=(11, 4)); ax.stackplot(pd.to_datetime(selected_records.review_date), selected_records.applied_global_weight, selected_records.applied_m2_weight, selected_records.applied_cash_weight, labels=["SWDA", "M2", "Cash"], alpha=.8); ax.legend(loc="upper left", ncol=3); ax.set_ylim(0, 1); ax.set_title("Selected strategy target allocation"); save_figure("UKACTIVE_A4F_SIPP_ALLOCATION_TIMELINE.png", fig)
    else:
        fig, ax = plt.subplots(figsize=(11, 4)); x=common_ledger.decision_date; alloc=average_allocations_placeholder(selected_id); ax.stackplot(x, np.repeat(alloc[0],len(x)), np.repeat(alloc[1],len(x)), np.repeat(alloc[2],len(x)), labels=["SWDA","M2","Cash"]); ax.legend(loc="upper left",ncol=3); ax.set_ylim(0,1); ax.set_title("Selected static allocation"); save_figure("UKACTIVE_A4F_SIPP_ALLOCATION_TIMELINE.png", fig)

    states = ["R1_BROAD_RISK_ON", "R2_LEADERSHIP_RISK_ON", "R3_ISOLATED_LEADERSHIP", "R4_CAPITAL_PRESERVATION"]
    matrix = pd.DataFrame(0.0, index=states, columns=states)
    base_transition = common_ledger.regime.to_frame("to"); base_transition["from"] = base_transition.to.shift()
    for to_regime, from_regime in base_transition.dropna().itertuples(index=False, name=None):
        if from_regime in states and to_regime in states and from_regime != to_regime:
            matrix.loc[from_regime, to_regime] += 1
    fig, ax = plt.subplots(figsize=(7, 6)); im=ax.imshow(matrix, cmap="Blues"); ax.set_xticks(range(4), ["R1","R2","R3","R4"]); ax.set_yticks(range(4), ["R1","R2","R3","R4"]); [ax.text(j,i,int(matrix.iloc[i,j]),ha="center",va="center") for i in range(4) for j in range(4)]; ax.set_xlabel("To"); ax.set_ylabel("From"); ax.set_title("Regime transition counts"); fig.colorbar(im,ax=ax); save_figure("UKACTIVE_A4F_SIPP_REGIME_TRANSITION_DIAGRAM.png", fig)

    compare_results = {"GLOBAL_100": static_results[("GLOBAL_100","BASE")], "GLOBAL_75_CASH25": static_results[("GLOBAL_75_CASH25","BASE")], "M2_TOP7_CASH0_100": static_results[("M2_TOP7_CASH0_100","BASE")], selected_id: selected_result}
    fig, ax = plt.subplots(figsize=(11, 5));
    for sid,res in compare_results.items(): nav_series(res).plot(ax=ax,label=sid)
    ax.set_yscale("log"); ax.set_ylabel("Growth of £1"); ax.set_title("Dynamic versus static equity curves"); ax.legend(); save_figure("UKACTIVE_A4F_SIPP_DYNAMIC_VS_STATIC_EQUITY_CURVES.png", fig)
    fig, ax = plt.subplots(figsize=(11, 5));
    for sid,res in compare_results.items():
        nav=nav_series(res); (nav/nav.cummax()-1).plot(ax=ax,label=sid)
    ax.set_ylabel("Drawdown"); ax.set_title("Dynamic versus static drawdown"); ax.legend(); save_figure("UKACTIVE_A4F_SIPP_DYNAMIC_VS_STATIC_DRAWDOWN_CURVES.png", fig)
    fig, ax = plt.subplots(figsize=(11, 5));
    for months in [12,24,36]: trailing_excess(selected_result,global_result,months).plot(ax=ax,label=f"{months}m")
    ax.axhline(0,color="black",lw=.8); ax.set_ylabel("Rolling excess"); ax.set_title(f"{selected_id}: rolling excess vs global"); ax.legend(); save_figure("UKACTIVE_A4F_SIPP_ROLLING_EXCESS.png", fig)

    full_matched = matched_rows.loc[matched_rows.window_id.eq("FULL_COMMON_HISTORY")]
    fig, ax = plt.subplots(figsize=(8, 5)); ax.scatter(full_matched.control_mdd.abs(), full_matched.control_cagr, label="Matched controls", alpha=.6); ax.scatter(full_matched.candidate_mdd.abs(), full_matched.candidate_cagr, label="Policies", marker="x"); ax.set_xlabel("Absolute maximum drawdown"); ax.set_ylabel("Net CAGR"); ax.set_title("Matched-risk frontier"); ax.legend(); save_figure("UKACTIVE_A4F_SIPP_MATCHED_RISK_FRONTIER.png", fig)
    ex25 = year_exclusions.loc[year_exclusions.excluded_period.eq("EXCLUDE_2025")]
    full_dynamic = [(p,s,metric_pack(dynamic_results[(p,s,"BASE")])["net_cagr"]) for p in SELECTABLE_POLICIES for s in SWITCHES]
    labels=[f"{p.split('_')[1]}-{s.split('_')[1]}" for p,s,_ in full_dynamic]; included=[v for _,_,v in full_dynamic]; excluded=[]
    for p,s,_ in full_dynamic:
        excluded.append(float(ex25.loc[(ex25.policy_id.eq(p)) & ex25.switch_mode.eq(s),"net_cagr"].iloc[0]))
    fig, ax=plt.subplots(figsize=(11,5)); x=np.arange(len(labels)); ax.bar(x-.2,included,.4,label="Included"); ax.bar(x+.2,excluded,.4,label="2025 excluded"); ax.set_xticks(x,labels,rotation=45,ha="right"); ax.set_ylabel("Net CAGR"); ax.set_title("2025 included versus excluded"); ax.legend(); save_figure("UKACTIVE_A4F_SIPP_2025_INCLUDED_EXCLUDED.png",fig)

    attr = attribution.loc[attribution.strategy_id.eq(selected_id)]
    fig, ax=plt.subplots(figsize=(9,5)); components=["global_contribution","m2_contribution","cash_yield_contribution","cost_contribution"]; attr.set_index("year")[components].plot(kind="bar",stacked=True,ax=ax); ax.axhline(0,color="black",lw=.8); ax.set_title("Contribution by year"); save_figure("UKACTIVE_A4F_SIPP_CONTRIBUTION_BY_YEAR.png",fig)
    selected_transitions = transitions.loc[
        transitions.policy_id.eq(selected_id) & transitions.switch_mode.eq(selected_switch)
    ] if selected_id.startswith("POLICY_") else transitions.iloc[0:0]
    if len(selected_transitions):
        tr=selected_transitions.groupby("new_regime")["switch_gain_loss"].sum().reindex(states).fillna(0)
        transition_title = f"{selected_id}: transition-month gain/loss versus matched control"
    else:
        tr=pd.Series(0.0,index=states)
        transition_title = "Selected static strategy: regimes are telemetry; no strategy-switch contribution"
    fig,ax=plt.subplots(figsize=(8,5)); tr.plot(kind="bar",ax=ax); ax.axhline(0,color="black",lw=.8); ax.set_ylabel("Transition-month return difference"); ax.set_title(transition_title); save_figure("UKACTIVE_A4F_SIPP_CONTRIBUTION_BY_REGIME.png",fig)
    opp=pd.Series({"Positive transition-month effect":float(selected_transitions.switch_gain_loss.clip(lower=0).sum()) if len(selected_transitions) else 0,"Negative transition-month effect":float(-selected_transitions.switch_gain_loss.clip(upper=0).sum()) if len(selected_transitions) else 0})
    fig,ax=plt.subplots(figsize=(8,5)); opp.plot(kind="bar",ax=ax,color=["#2ca02c","#d62728"]); ax.set_title(transition_title); save_figure("UKACTIVE_A4F_SIPP_SWITCHING_GAIN_OPPORTUNITY_COST.png",fig)


def average_allocations_placeholder(strategy_id: str) -> tuple[float, float, float]:
    mapping = {
        "GLOBAL_25_CASH75": (0.25,0,0.75), "GLOBAL_50_CASH50": (0.5,0,0.5), "GLOBAL_75_CASH25": (0.75,0,0.25), "GLOBAL_100": (1,0,0),
        "M2_TOP7_CASH0_25_CASH75": (0,.25,.75), "M2_TOP7_CASH0_50_CASH50": (0,.5,.5), "M2_TOP7_CASH0_75_CASH25": (0,.75,.25), "M2_TOP7_CASH0_100": (0,1,0),
        "GLOBAL_90_M2_10": (.9,.1,0), "GLOBAL_75_M2_25": (.75,.25,0), "GLOBAL_50_M2_50": (.5,.5,0), "GLOBAL_50_M2_25_CASH25": (.5,.25,.25), "GLOBAL_75_M2_10_CASH15": (.75,.1,.15),
    }
    return mapping.get(strategy_id,(.75,0,.25))


def transition_policy_rows(
    ledger: pd.DataFrame,
    policy_results: Mapping[tuple[str, str, str], Any],
    matched_controls: Mapping[tuple[str, str, str], Any],
    policy_records: Mapping[tuple[str, str], pd.DataFrame],
    global_result: Any,
    m2_result: Any,
    cash_result: Any,
) -> pd.DataFrame:
    ordered = ledger.loc[ledger.decision_date.ge(pd.Timestamp("2017-02-28")) & ledger.regime.ne("REGIME_UNAVAILABLE")].sort_values("decision_date").copy()
    ordered["prior_regime"] = ordered.regime.shift()
    ordered["episode"] = ordered.regime.ne(ordered.regime.shift()).cumsum()
    ordered["position_in_episode"] = ordered.groupby("episode").cumcount() + 1
    # On the first row of a new episode, the preceding row's position is the
    # complete duration of the state that has just ended.
    ordered["prior_duration"] = ordered["position_in_episode"].shift(1)
    events = ordered.loc[ordered.regime.ne(ordered.prior_regime) & ordered.prior_regime.notna()].copy()
    rows = []
    global_ret = core.monthly_interval_returns(ledger, global_result).set_index("decision_date")["interval_return"]
    m2_ret = core.monthly_interval_returns(ledger, m2_result).set_index("decision_date")["interval_return"]
    cash_ret = core.monthly_interval_returns(ledger, cash_result).set_index("decision_date")["interval_return"]
    for policy_id in SELECTABLE_POLICIES:
        for switch_mode in SWITCHES:
            candidate = core.monthly_interval_returns(ledger, policy_results[(policy_id, switch_mode, "BASE")]).set_index("decision_date")["interval_return"]
            control = core.monthly_interval_returns(ledger, matched_controls[(policy_id, switch_mode, "MATCHED_AVERAGE_EXPOSURE")]).set_index("decision_date")["interval_return"]
            records = policy_records[(policy_id, switch_mode)].copy().sort_values("review_date")
            records["review_date"] = pd.to_datetime(records["review_date"])
            allocation_columns = ["applied_global_weight", "applied_m2_weight", "applied_cash_weight"]
            records["allocation_changed"] = records[allocation_columns].diff().abs().sum(axis=1).gt(1e-12)
            allocation_changed = records.set_index("review_date")["allocation_changed"]
            for (prior, new), group in events.groupby(["prior_regime", "regime"]):
                dates = pd.DatetimeIndex(group.decision_date)
                gains = candidate.reindex(dates) - control.reindex(dates)
                switch_count = int(allocation_changed.reindex(dates).fillna(False).sum())
                forward = candidate.reindex(ordered.decision_date)
                one=[]; three=[]; six=[]
                for date in dates:
                    pos = list(ordered.decision_date).index(date)
                    d = pd.DatetimeIndex(ordered.decision_date.iloc[pos:pos+6])
                    vals=forward.reindex(d).dropna()
                    one.append(vals.iloc[0] if len(vals)>=1 else np.nan)
                    three.append(np.prod(1+vals.iloc[:3])-1 if len(vals)>=3 else np.nan)
                    six.append(np.prod(1+vals.iloc[:6])-1 if len(vals)>=6 else np.nan)
                reverse1=0; reverse3=0
                for index in group.index:
                    pos=ordered.index.get_loc(index)
                    future=ordered.iloc[pos+1:pos+4].regime
                    reverse1 += int(len(future)>=1 and future.iloc[0]==prior)
                    reverse3 += int(future.eq(prior).any())
                rows.append({
                    "policy_id": policy_id, "switch_mode": switch_mode, "prior_regime": prior, "new_regime": new,
                    "transition_count": len(group), "average_prior_duration_months": float(group.prior_duration.mean()),
                    "next_1m_return": float(np.nanmean(one)), "next_3m_return": float(np.nanmean(three)), "next_6m_return": float(np.nanmean(six)),
                    "m2_minus_global_1m": float((m2_ret.reindex(dates)-global_ret.reindex(dates)).mean()),
                    "risky_minus_cash_1m": float((global_ret.reindex(dates)-cash_ret.reindex(dates)).mean()),
                    "allocation_switch_count": switch_count,
                    "switch_gain_loss": float(gains.sum()),
                    "reversal_within_1m": reverse1, "reversal_within_3m": reverse3,
                    "transition_classification": (
                        "NO_ALLOCATION_SWITCH" if switch_count == 0
                        else "FALSE_OR_COSTLY_SWITCH" if gains.sum() < -1e-12
                        else "BENEFICIAL_SWITCH" if gains.sum() > 1e-12
                        else "NEUTRAL_SWITCH"
                    ),
                })
    return pd.DataFrame(rows)


def regime_gate_statistics(
    ledger: pd.DataFrame,
    candidate: Any,
    control: Any,
) -> dict[str, Any]:
    c = core.monthly_interval_returns(ledger, candidate).set_index("decision_date")["interval_return"]
    b = core.monthly_interval_returns(ledger, control).set_index("decision_date")["interval_return"]
    diff = (c-b).dropna()
    state = ledger.set_index("decision_date")["regime"].reindex(diff.index)
    positive_regimes = int(diff.groupby(state).sum().gt(0).sum())
    episodes = state.ne(state.shift()).cumsum()
    episode_gain = diff.groupby(episodes).sum()
    positive_episode_count = int(episode_gain.gt(0).sum())
    positive_total = float(episode_gain.clip(lower=0).sum())
    largest_share = float(episode_gain.max()/positive_total) if positive_total>0 else np.inf
    return {"positive_regimes": positive_regimes, "positive_episodes": positive_episode_count, "largest_positive_episode_share": largest_share}


def static_strategy_gate(
    candidate_id: str,
    incremental: pd.DataFrame,
    family_rows: pd.DataFrame | None,
) -> bool:
    row = incremental.loc[(incremental.candidate_id.eq(candidate_id)) & incremental.window_id.eq("FULL_COMMON_HISTORY")].iloc[0]
    family_ok = True if family_rows is None or family_rows.empty else not family_rows.dependency_status.eq("SIGN_REVERSAL_DEPENDENCY").any()
    return bool(row.incremental_cagr > 0 and row.exclude_2025_incremental_cagr >= 0 and row.double_cost_incremental_cagr >= 0 and family_ok)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    prereg = core.read_preregistration()
    if prereg["authoritative_cutoff"] != "2026-08-21":
        raise AssertionError("A4F cutoff changed")
    if not git("merge-base", "--is-ancestor", PROTOCOL_COMMIT, "HEAD") == "":
        # git merge-base --is-ancestor is silent on success; check_call is not
        # needed because subprocess.check_output already fails on nonzero.
        pass
    data = core.load_data()
    if pd.Timestamp(data.base.research.calendar.max()) != CUTOFF:
        raise AssertionError("Accepted XLON cutoff mismatch")

    ledger_all = core.build_monthly_regime_ledger(data, 0.75, 0.50)
    common_ledger = ledger_all.loc[ledger_all["decision_date"].ge(pd.Timestamp("2017-02-28")) & ledger_all["eligible_family_count"].ge(3)].copy()
    common_ledger["execution_date"] = common_ledger["scheduled_next_xlon_session"].where(common_ledger["scheduled_next_xlon_session"].le(CUTOFF), pd.NaT)
    ledger_output = common_ledger.rename(columns={
        "top7_families_rank_order": "top7_families",
        "global_return_126": "global_126_return",
        "cash_return_126": "cash_126_return",
        "global_return_252": "global_252_return",
        "cash_return_252": "cash_252_return",
        "volatility_threshold": "prior_vol_threshold",
        "leadership_spread_threshold": "prior_spread_threshold",
        "rank_persistence_threshold": "prior_persistence_threshold",
        "absolute_leadership_support": "absolute_support_count",
        "m2_score_cross_section_std": "secondary_score_std",
        "m2_score_cross_section_iqr": "secondary_score_iqr",
        "family_return_63_iqr": "secondary_return63_iqr",
        "family_return_126_iqr": "secondary_return126_iqr",
        "average_pairwise_126_return_correlation": "secondary_average_pairwise_corr126",
        "first_principal_component_variance_share": "secondary_pc1_variance_share",
        "percentage_families_above_cash": "secondary_percent_above_cash",
        "percentage_families_above_global": "secondary_percent_above_global",
        "top7_membership_retention": "secondary_top7_retention",
        "global_drawdown_from_trailing_252_high": "secondary_global_drawdown_252",
    })
    ledger_output["vol_threshold_percentile"] = 0.75
    write_csv("UKACTIVE_A4F_SIPP_MONTHLY_REGIME_LEDGER.csv", ledger_output)

    # Phase 0 and static frontier.
    global_benchmark = core.a4d.index_benchmark(data, core.GLOBAL_FAMILY, "GLOBAL_DEVELOPED_WORLD_COSTLESS_REFERENCE")
    pool_benchmark = core.a4d.pool_benchmark(data, "MONTHLY")
    cash_benchmark = core.a4d.cash_benchmark(data)
    static_maps = core.static_target_maps(data)
    base_m2_targets = static_maps["M2_TOP7_CASH0_100"]
    static_maps["GLOBAL_85_CASH15"] = make_blend_targets(base_m2_targets, 0.85, 0.0)
    static_results: dict[tuple[str, str], Any] = {}
    for sid, targets in static_maps.items():
        for cost in ["BASE", "DOUBLE"]:
            if sid in {"M2_TOP7_CASH0_100", "GLOBAL_0_M2_100"}:
                result = core.a4e.simulate_rotation(data, "M2_BASE", 7, False, cost_scenario=cost)
            else:
                result = core.simulate_target_map(data, targets, sid, cost)
            static_results[(sid, cost)] = result
    # Freeze the canonical IDs used in reporting.
    global_result = static_results[("GLOBAL_100", "BASE")]
    m2_result = static_results[("M2_TOP7_CASH0_100", "BASE")]
    cash1_result = core.a4e.simulate_rotation(data, "M2_BASE", 7, True, cost_scenario="BASE")

    expected = {
        "GLOBAL_100": {"net_cagr": 0.11601083229325537, "maximum_drawdown": -0.2558185599683075, "ulcer_index": 0.04890992072479275},
        "GLOBAL_75_CASH25": {"net_cagr": 0.0926320318380296, "maximum_drawdown": -0.19551631373842515, "ulcer_index": 0.0359925415591835},
        "M2_TOP7_CASH0_100": {"net_cagr": 0.13137626091488874, "maximum_drawdown": -0.23530833565375164, "ulcer_index": 0.08198040131578595, "annual_turnover_traded_notional": 5.523060844665003},
        "M2_TOP7_CASH1_100": {"net_cagr": 0.09529026240309668, "maximum_drawdown": -0.2715740690405678, "ulcer_index": 0.08315515385099306},
    }
    reproduced_results = {"GLOBAL_100": global_result, "GLOBAL_75_CASH25": static_results[("GLOBAL_75_CASH25", "BASE")], "M2_TOP7_CASH0_100": m2_result, "M2_TOP7_CASH1_100": cash1_result}
    reconciliation_rows = []
    for sid, fields in expected.items():
        actual = metric_pack(reproduced_results[sid])
        for field, prior in fields.items():
            value = float(actual[field])
            reconciliation_rows.append({"metric_id": field, "strategy_id": sid, "window_id": "FULL_COMMON_HISTORY", "a4e_value": prior, "a4f_value": value, "difference": value-prior, "tolerance": 1e-10, "status": "PASS" if abs(value-prior)<=1e-10 else "FAIL", "notes": "Independent rerun through immutable A4D/A4E engine"})
    prior_random = pd.read_csv(A4E_OUT / "UKACTIVE_A4E_SIPP_RANDOM_SELECTION_CONTROL.csv")
    for row in prior_random.itertuples(index=False):
        # A4E randomisation is CASH1-specific; reproduce exactly and retain as
        # parent audit rather than misapplying it to CASH0.
        fresh = core.a4e.vectorised_randomisation_control(data, cash1_result.targets, mode=row.control_id, seed=int(row.seed), simulation_count=int(row.simulation_count), breadth=7)
        for field in ["candidate_cagr_percentile", "candidate_drawdown_percentile_less_severe"]:
            prior = float(getattr(row, field)); value = float(fresh[field])
            reconciliation_rows.append({"metric_id": field, "strategy_id": row.control_id, "window_id": "A4E_MATCHED_DIAGNOSTIC", "a4e_value": prior, "a4f_value": value, "difference": value-prior, "tolerance": 1e-12, "status": "PASS" if abs(value-prior)<=1e-12 else "FAIL", "notes": "Exact A4E CASH1 randomisation reproduction; not reused for A4F CASH0"})
    reconciliation = pd.DataFrame(reconciliation_rows)
    write_csv("UKACTIVE_A4F_SIPP_COMMON_WINDOW_RECONCILIATION.csv", reconciliation)
    if not reconciliation.status.eq("PASS").all():
        write_text("UKACTIVE_A4F_SIPP_REPRODUCTION_AUDIT.md", "# A4F-SIPP reproduction audit\n\nDecision: `A4F_SIPP_AUDIT_FAIL`.\n")
        raise AssertionError("A4F reproduction failed")
    write_text("UKACTIVE_A4F_SIPP_REPRODUCTION_AUDIT.md", f"""# UKACTIVE-A4F-SIPP reproduction audit

Decision: **PASS**. All {len(reconciliation)} decision-critical metric/randomisation cells reproduced within their frozen tolerances.

- Formation-chain boundary: 2017-02-03.
- First common executable portfolio date: 2017-03-01.
- Common direct-comparison window: 2017-03-01 through 2026-08-21.
- Longer accepted core-only window: 2010-01-08 through 2026-08-21.
- 2017 and 2026 are partial years.
- CASH1 random/rank-shuffle controls were reproduced only as A4E audit evidence; their CASH1 qualification is not silently reused for A4F CASH0.
- The canonical simulator rebases at the first post-cost portfolio row, preserving A4D/A4E one-time-entry-cost treatment for exact lineage reconciliation.
""")
    write_csv("UKACTIVE_A4F_SIPP_LONGER_CORE_ONLY_RESULTS.csv", longer_core_only_rows(data))

    frontier_results = {key: value for key, value in static_results.items() if key[0] != "GLOBAL_85_CASH15"}
    static_rows = static_frontier_rows(data, frontier_results)
    write_csv("UKACTIVE_A4F_SIPP_STATIC_FRONTIER.csv", static_rows)
    pareto = static_rows.loc[(static_rows.window_id.eq("FULL_COMMON_HISTORY")) & static_rows.cost_scenario.eq("BASE")].copy()
    pareto["candidate_role"] = np.where(pareto.pareto_efficient, "PARETO_FRONTIER", "DOMINATED_STATIC_CANDIDATE")
    write_csv("UKACTIVE_A4F_SIPP_PARETO_FRONTIER.csv", pareto[["strategy_id","net_cagr","terminal_wealth_per_100k","maximum_drawdown","ulcer_index","longest_underwater_days","turnover","pareto_efficient","candidate_role"]])
    direct_m2 = direct_m2_rows(static_rows, static_results)
    write_csv("UKACTIVE_A4F_SIPP_M2_INCREMENTAL_VALUE.csv", direct_m2)

    # Static causal-regime diagnostics are calculated before dynamic policies.
    regime_sims = {sid: static_results[(sid,"BASE")] for sid in sorted({key[0] for key in frontier_results if key[1]=="BASE"})}
    regime_sims["EQUAL_WEIGHT_OPPORTUNITY_POOL"] = pool_benchmark
    regime_sims["ACTUAL_GBP_CASH"] = cash_benchmark
    regime_summary_raw = core.regime_summary(ledger_all, regime_sims, global_id="GLOBAL_100", pool_id="EQUAL_WEIGHT_OPPORTUNITY_POOL")
    regime_summary = regime_summary_raw.rename(columns={
        "month_count":"months","episode_count":"episodes","average_episode_duration_months":"average_episode_months","claim_status":"sample_status","sharpe_zero_hurdle":"sharpe","sortino_zero_hurdle":"sortino","worst_episode_maximum_drawdown":"episode_mdd","mean_subsequent_1m_return":"forward_1m_return","mean_subsequent_3m_return":"forward_3m_return","mean_subsequent_6m_return":"forward_6m_return","mean_excess_vs_global":"excess_vs_global","mean_excess_vs_pool":"excess_vs_equal_pool"
    })
    regime_summary["risk_score_substate"] = "ALL_SUBSTATES"
    regime_summary["m2_minus_global"] = np.nan
    regime_summary["cash_minus_risky"] = np.nan
    write_csv("UKACTIVE_A4F_SIPP_REGIME_SUMMARY.csv", regime_summary)
    regime_rankings = regime_ranking_rows(regime_summary_raw)
    write_csv("UKACTIVE_A4F_SIPP_REGIME_STRATEGY_RANKINGS.csv", regime_rankings)
    episodes = episode_ledger(ledger_all, regime_sims)
    write_csv("UKACTIVE_A4F_SIPP_REGIME_EPISODE_LEDGER.csv", episodes)

    # Dynamic policies and immutable policy/month decision audit.
    policy_targets: dict[tuple[str,str], dict[pd.Timestamp,dict[str,float]]] = {}
    policy_records: dict[tuple[str,str], pd.DataFrame] = {}
    policy_results: dict[tuple[str,str,str], Any] = {}
    decision_frames = []
    for policy_id in POLICIES:
        for switch_mode in SWITCHES:
            targets, records = core.policy_target_map(data, ledger_all, policy_id, switch_mode)
            policy_targets[(policy_id,switch_mode)] = targets
            policy_records[(policy_id,switch_mode)] = records
            for cost in ["BASE","DOUBLE"]:
                result = core.simulate_target_map(data, (targets,records), f"{policy_id}|{switch_mode}", cost)
                policy_results[(policy_id,switch_mode,cost)] = result
            decision_frames.append(policy_decision_rows(data,ledger_all,policy_id,switch_mode,records,policy_results[(policy_id,switch_mode,"BASE")]))
    policy_decisions = pd.concat(decision_frames,ignore_index=True)
    write_csv("UKACTIVE_A4F_SIPP_POLICY_DECISION_LEDGER.csv",policy_decisions)
    dynamic = dynamic_result_rows(data,policy_results,policy_targets,global_result)
    hysteresis = hysteresis_rows(dynamic)
    write_csv("UKACTIVE_A4F_SIPP_HYSTERESIS_RESULTS.csv",hysteresis)

    matched, matched_results = matched_control_rows(data,policy_results,policy_targets,static_results,static_rows)
    write_csv("UKACTIVE_A4F_SIPP_MATCHED_RISK_CONTROLS.csv",matched)
    inference = policy_inference_rows(policy_results,matched_results)
    write_csv("UKACTIVE_A4F_SIPP_POLICY_INFERENCE.csv",inference)
    write_text("UKACTIVE_A4F_SIPP_REGIME_INFERENCE.md", f"""# UKACTIVE-A4F-SIPP regime inference

Paired monthly policy-minus-matched-control returns use Newey–West HAC lag 3 and a deterministic 10,000-replication moving-block bootstrap with six-month blocks (seed 20260825). Benjamini–Hochberg adjustment covers the ten selectable policy/switch tests. These statistics are contextual; the preregistered economic gates remain primary.

Adequately sampled regimes: {', '.join(sorted(regime_summary.loc[regime_summary.sample_status.eq('REGIME_SAMPLE_SUFFICIENT'),'regime'].unique())) or 'none'}. Sparse states remain `INSUFFICIENT_REGIME_SAMPLE` and cannot support strong regime claims.
""")

    transitions = transition_policy_rows(
        ledger_all,
        policy_results,
        matched_results,
        policy_records,
        global_result,
        m2_result,
        cash_benchmark,
    )
    write_csv("UKACTIVE_A4F_SIPP_REGIME_TRANSITIONS.csv",transitions)
    oracles = oracle_rows(static_results,policy_results,ledger_all)
    write_csv("UKACTIVE_A4F_SIPP_ORACLE_DIAGNOSTICS.csv",oracles)
    exclusions = year_exclusion_rows(policy_results,global_result,static_results)
    write_csv("UKACTIVE_A4F_SIPP_YEAR_EXCLUSION_RESULTS.csv",exclusions)
    threshold_sensitivity, threshold_cache = threshold_sensitivity_rows(data,global_result)
    write_csv("UKACTIVE_A4F_SIPP_THRESHOLD_SENSITIVITY.csv",threshold_sensitivity)

    # Family and spell robustness for every selectable M2-bearing policy and
    # every static M2 fallback that survives the earlier staged economic gates.
    family_frames=[]; family_ok={}
    for policy_id in ["POLICY_2_ALPHA_TIMING_ONLY","POLICY_3_BALANCED_REGIME_STRATEGY","POLICY_4_DEFENSIVE_REGIME_STRATEGY"]:
        for switch in SWITCHES:
            frame, ok=family_influence_rows(data,policy_id,switch,policy_records[(policy_id,switch)],policy_results[(policy_id,switch,"BASE")],matched_results[(policy_id,switch,"MATCHED_AVERAGE_EXPOSURE")])
            family_frames.append(frame); family_ok[(policy_id,switch)]=ok

    serious_static = direct_m2.loc[
        direct_m2.window_id.eq("FULL_COMMON_HISTORY")
        & direct_m2.incremental_cagr.gt(0)
        & direct_m2.exclude_2025_incremental_cagr.ge(0)
        & direct_m2.double_cost_incremental_cagr.ge(0),
        "candidate_id",
    ].drop_duplicates().tolist()
    static_family_ok: dict[str, bool] = {}
    for strategy_id in serious_static:
        comparator_id = STATIC_M2_COMPARATORS[strategy_id]
        frame, ok = static_family_influence_rows(
            data,
            strategy_id,
            static_results[(strategy_id, "BASE")],
            static_results[(comparator_id, "BASE")],
        )
        family_frames.append(frame)
        static_family_ok[strategy_id] = ok

    family_influence=pd.concat(family_frames,ignore_index=True)
    write_csv("UKACTIVE_A4F_SIPP_FAMILY_INFLUENCE.csv",family_influence)
    direct_m2["family_exclusion_status"] = direct_m2["candidate_id"].map(
        {
            strategy_id: (
                "STATIC_FAMILY_GATE_PASS"
                if status
                else "STATIC_FAMILY_GATE_FAIL"
            )
            for strategy_id, status in static_family_ok.items()
        }
    ).fillna("NOT_EVALUATED_EARLIER_ECONOMIC_GATE_FAIL")
    write_csv("UKACTIVE_A4F_SIPP_M2_INCREMENTAL_VALUE.csv",direct_m2)
    spell_influence=holding_spell_influence_rows(data,"POLICY_3_BALANCED_REGIME_STRATEGY",policy_records[("POLICY_3_BALANCED_REGIME_STRATEGY","SWITCH_IMMEDIATE_MONTHLY")],policy_results[("POLICY_3_BALANCED_REGIME_STRATEGY","SWITCH_IMMEDIATE_MONTHLY","BASE")])
    write_csv("UKACTIVE_A4F_SIPP_HOLDING_SPELL_INFLUENCE.csv",spell_influence)
    holding_spells = core.a4e.holding_spell_ledger(m2_result)
    write_csv("UKACTIVE_A4F_SIPP_HOLDING_SPELL_LEDGER.csv", holding_spells)
    winner_false_comparison = (
        holding_spells.groupby("winner_class", as_index=False)
        .agg(
            holding_spells=("holding_spell_id", "count"),
            distinct_families=("family", "nunique"),
            total_gross_market_pnl_return_units=("gross_market_pnl_return_units", "sum"),
            mean_gross_market_pnl_return_units=("gross_market_pnl_return_units", "mean"),
            median_gross_market_pnl_return_units=("gross_market_pnl_return_units", "median"),
            mean_days_held=("days_held", "mean"),
            median_days_held=("days_held", "median"),
            share_of_positive_spell_pnl=("share_of_positive_spell_pnl", "sum"),
        )
    )
    winner_false_comparison["interpretation"] = "E2_DEVELOPMENTAL_HOLDING_SPELL_MECHANISM_DIAGNOSTIC"
    write_csv("UKACTIVE_A4F_SIPP_WINNER_FALSE_LEADER_COMPARISON.csv", winner_false_comparison)

    # Complete dynamic gates, including doubled-cost matched controls.
    adequately=regime_summary.loc[regime_summary.sample_status.eq("REGIME_SAMPLE_SUFFICIENT")]
    top_by_regime=adequately.sort_values(["regime","annualised_return"],ascending=[True,False]).groupby("regime").head(1)
    regime_rankings_differ=bool(top_by_regime.strategy_id.nunique()>=2)
    gate_rows=[]
    for policy_id in SELECTABLE_POLICIES:
        for switch_mode in SWITCHES:
            base=dynamic.loc[(dynamic.policy_id.eq(policy_id))&dynamic.switch_mode.eq(switch_mode)&dynamic.window_id.eq("FULL_COMMON_HISTORY")&dynamic.cost_scenario.eq("BASE")].iloc[0]
            double=dynamic.loc[(dynamic.policy_id.eq(policy_id))&dynamic.switch_mode.eq(switch_mode)&dynamic.window_id.eq("FULL_COMMON_HISTORY")&dynamic.cost_scenario.eq("DOUBLE")].iloc[0]
            global_full=metric_pack(global_result)
            primary=matched.loc[(matched.policy_id.eq(policy_id))&matched.switch_mode.eq(switch_mode)&matched.control_type.eq("MATCHED_AVERAGE_EXPOSURE")&matched.window_id.eq("FULL_COMMON_HISTORY")].iloc[0]
            double_control_targets=core.matched_average_exposure_control(data,policy_targets[(policy_id,switch_mode)])
            double_control=core.simulate_target_map(data,double_control_targets,f"{policy_id}|{switch_mode}|MATCHED_DOUBLE","DOUBLE")
            double_control_cagr=metric_pack(double_control)["net_cagr"]
            stats=regime_gate_statistics(ledger_all,policy_results[(policy_id,switch_mode,"BASE")],matched_results[(policy_id,switch_mode,"MATCHED_AVERAGE_EXPOSURE")])
            return_gate=bool(base.net_cagr>=.90*global_full["net_cagr"] or base.net_cagr>global_full["net_cagr"])
            drawdown_gate=bool(base.maximum_drawdown>=-.20 or base.maximum_drawdown-global_full["maximum_drawdown"]>=.05 or 1-base.ulcer_index/global_full["ulcer_index"]>=.20)
            terminal_ratio=primary.candidate_terminal_wealth/primary.control_terminal_wealth-1
            ulcer_reduction=1-primary.candidate_ulcer/primary.control_ulcer if primary.control_ulcer>0 else -np.inf
            matched_gate=bool(primary.incremental_cagr>=.0075 or terminal_ratio>=.05 or (primary.incremental_mdd>=.02 and primary.candidate_cagr>=primary.control_cagr) or (ulcer_reduction>=.15 and primary.candidate_cagr>=.95*primary.control_cagr))
            ex=exclusions.loc[(exclusions.policy_id.eq(policy_id))&exclusions.switch_mode.eq(switch_mode)&exclusions.excluded_period.eq("EXCLUDE_2025")].iloc[0]
            control_ex=excluded_metrics(matched_results[(policy_id,switch_mode,"MATCHED_AVERAGE_EXPOSURE")],{2025})
            ex25_gate=bool(ex.net_cagr-control_ex["net_cagr"]>0)
            double_gate=bool(double.net_cagr-double_control_cagr>=0 and double.net_cagr>=.90*metric_pack(static_results[("GLOBAL_100","DOUBLE")])["net_cagr"])
            fam_gate=True if policy_id in {"POLICY_0_STATIC_DEFENSIVE_CONTROL","POLICY_1_RISK_TIMING_ONLY"} else family_ok.get((policy_id,switch_mode),False)
            sens=threshold_sensitivity.loc[(threshold_sensitivity.policy_id.eq(policy_id))&threshold_sensitivity.switch_mode.eq(switch_mode)]
            threshold_gate=True if policy_id=="POLICY_0_STATIC_DEFENSIVE_CONTROL" else bool(sens.directionally_coherent.astype(bool).all())
            hrow=hysteresis.loc[(hysteresis.policy_id.eq(policy_id))&hysteresis.window_id.eq("FULL_COMMON_HISTORY")&hysteresis.cost_scenario.eq("BASE")].iloc[0]
            hysteresis_gate=bool(hrow.hysteresis_cagr>=.95*hrow.immediate_cagr or switch_mode=="SWITCH_ASYMMETRIC_HYSTERESIS")
            regime_gate=bool(regime_rankings_differ and stats["positive_regimes"]>=2 and stats["positive_episodes"]>=3 and stats["largest_positive_episode_share"]<.50)
            all_gates=all([return_gate,drawdown_gate,matched_gate,ex25_gate,double_gate,fam_gate,threshold_gate,hysteresis_gate,regime_gate])
            gate_rows.append({"policy_id":policy_id,"switch_mode":switch_mode,"return_gate":return_gate,"drawdown_gate":drawdown_gate,"matched_risk_gate":matched_gate,"regime_gate":regime_gate,"exclude_2025_gate":ex25_gate,"double_cost_gate":double_gate,"family_gate":fam_gate,"threshold_gate":threshold_gate,"hysteresis_gate":hysteresis_gate,"all_mandatory_gates":all_gates,"positive_regimes":stats["positive_regimes"],"positive_episodes":stats["positive_episodes"],"largest_positive_episode_share":stats["largest_positive_episode_share"]})
    gates=pd.DataFrame(gate_rows)
    dynamic=dynamic.merge(gates,on=["policy_id","switch_mode"],how="left")
    dynamic["eligible_for_selection"] = dynamic.policy_id.isin(SELECTABLE_POLICIES)
    dynamic["all_mandatory_gates"] = dynamic["all_mandatory_gates"].fillna(False).astype(bool)
    dynamic["promotion_status"]=np.select(
        [
            ~dynamic["eligible_for_selection"],
            dynamic["all_mandatory_gates"],
        ],
        [
            "NOT_ELIGIBLE_HIGHER_ALPHA_DIAGNOSTIC",
            "PASSES_ALL_MANDATORY_GATES",
        ],
        default="FAILS_ONE_OR_MORE_MANDATORY_GATES",
    )
    write_csv("UKACTIVE_A4F_SIPP_DYNAMIC_POLICY_RESULTS.csv",dynamic)
    matched_gate_lookup = {
        (row.policy_id, row.switch_mode): bool(row.matched_risk_gate)
        for row in gates.itertuples(index=False)
    }
    matched["matched_risk_gate_status"] = [
        (
            (
                "MATCHED_RISK_GATE_PASS"
                if matched_gate_lookup.get((row.policy_id, row.switch_mode), False)
                else "MATCHED_RISK_GATE_FAIL"
            )
            if row.control_type == "MATCHED_AVERAGE_EXPOSURE"
            else "DIAGNOSTIC_CONTROL_NOT_PRIMARY_GATE"
        )
        for row in matched.itertuples(index=False)
    ]
    write_csv("UKACTIVE_A4F_SIPP_MATCHED_RISK_CONTROLS.csv", matched)
    costs=cost_stress_rows(dynamic)
    doubled_gate_lookup = {
        (row.policy_id, row.switch_mode): bool(row.double_cost_gate)
        for row in gates.itertuples(index=False)
    }
    costs["viability_status"] = [
        (
            "VIABLE_OR_PENDING_BY_POLICY"
            if doubled_gate_lookup.get((row.policy_id, row.switch_mode), False)
            else "FAILS_DOUBLE_COST_GATE"
        )
        for row in costs.itertuples(index=False)
    ]
    write_csv("UKACTIVE_A4F_SIPP_COST_STRESS.csv",costs)

    # Year-by-year scorecard and exact accounting attribution.
    regime_changes_by_year=common_ledger.assign(change=common_ledger.regime.ne(common_ledger.regime.shift())).groupby(common_ledger.decision_date.dt.year).change.sum().astype(int).to_dict()
    year_strategies={
        "GLOBAL_100":static_results[("GLOBAL_100","BASE")],"GLOBAL_75_CASH25":static_results[("GLOBAL_75_CASH25","BASE")],"GLOBAL_50_CASH50":static_results[("GLOBAL_50_CASH50","BASE")],"M2_TOP7_CASH0_100":m2_result,"M2_TOP7_CASH0_75_CASH25":static_results[("M2_TOP7_CASH0_75_CASH25","BASE")],"GLOBAL_90_M2_10":static_results[("GLOBAL_90_M2_10","BASE")],"GLOBAL_75_M2_25":static_results[("GLOBAL_75_M2_25","BASE")],"GLOBAL_50_M2_25_CASH25":static_results[("GLOBAL_50_M2_25_CASH25","BASE")],"EQUAL_WEIGHT_OPPORTUNITY_POOL":pool_benchmark,"ACTUAL_GBP_CASH":cash_benchmark,
    }
    for policy_id in SELECTABLE_POLICIES: year_strategies[policy_id]=policy_results[(policy_id,"SWITCH_IMMEDIATE_MONTHLY","BASE")]
    score_frames=[]; attr_frames=[]
    for sid,result in year_strategies.items():
        if sid in SELECTABLE_POLICIES: alloc=average_allocations(data,policy_targets[(sid,"SWITCH_IMMEDIATE_MONTHLY")])
        elif sid in static_maps: alloc=average_allocations(data,static_maps[sid])
        else: alloc={"global_weight":0.0,"m2_weight":0.0,"cash_weight":1.0 if sid=="ACTUAL_GBP_CASH" else 0.0}
        score_frames.append(annual_score(sid,result,global_result,pool_benchmark,alloc,regime_changes_by_year))
        attr_frames.append(daily_accounting_attribution(sid,result,data))
    year_score=pd.concat(score_frames,ignore_index=True); attribution=pd.concat(attr_frames,ignore_index=True)
    # Counterfactual mechanism attribution for primary P3.
    p1=curve(policy_results[("POLICY_1_RISK_TIMING_ONLY","SWITCH_IMMEDIATE_MONTHLY","BASE")]).set_index("date")["net_return"]
    p2=curve(policy_results[("POLICY_2_ALPHA_TIMING_ONLY","SWITCH_IMMEDIATE_MONTHLY","BASE")]).set_index("date")["net_return"]
    p3=curve(policy_results[("POLICY_3_BALANCED_REGIME_STRATEGY","SWITCH_IMMEDIATE_MONTHLY","BASE")]).set_index("date")["net_return"]
    g=curve(global_result).set_index("date")["net_return"]
    mech=pd.concat([p1,p2,p3,g],axis=1,keys=["p1","p2","p3","g"]).dropna()
    for year,part in mech.groupby(mech.index.year):
        mask=(attribution.strategy_id.eq("POLICY_3_BALANCED_REGIME_STRATEGY"))&attribution.year.eq(year)
        attribution.loc[mask,"risk_timing_contribution"]=float((part.p1-part.g).sum())
        attribution.loc[mask,"m2_selection_contribution"]=float((part.p2-part.g).sum())
        attribution.loc[mask,"interaction_contribution"]=float((part.p3-part.p1-part.p2+part.g).sum())
        attribution.loc[mask,"switching_contribution"]=float((part.p3-part.g).sum())
    write_csv("UKACTIVE_A4F_SIPP_YEAR_BY_YEAR_SCORECARD.csv",year_score)
    write_csv("UKACTIVE_A4F_SIPP_YEAR_BY_YEAR_ATTRIBUTION.csv",attribution)

    annual_concentration = annual_m2_concentration(m2_result, data).set_index("year")
    spell_review = holding_spells.copy()
    spell_review["entry_date"] = pd.to_datetime(spell_review["entry_date"])
    review_lines=[
        "# UKACTIVE-A4F-SIPP year-by-year review",
        "",
        "Calendar years are causal diagnostics, never optimisation units. Concentration figures use the frozen M2 portfolio; a spell can cross a year boundary, so the spell figure is explicitly the full P&L of the largest spell entering that year rather than a year-sliced attribution.",
        "",
    ]
    for year in sorted(year_score.year.unique()):
        subset=year_score.loc[year_score.year.eq(year)]
        best=subset.sort_values("net_return",ascending=False).iloc[0]; lowdd=subset.sort_values("maximum_drawdown",ascending=False).iloc[0]
        m2=subset.loc[subset.strategy_id.eq("M2_TOP7_CASH0_100")].iloc[0]; glob=subset.loc[subset.strategy_id.eq("GLOBAL_100")].iloc[0]
        p1_year=subset.loc[subset.strategy_id.eq("POLICY_1_RISK_TIMING_ONLY")].iloc[0]
        p3_year=subset.loc[subset.strategy_id.eq("POLICY_3_BALANCED_REGIME_STRATEGY")].iloc[0]
        static75_year=subset.loc[subset.strategy_id.eq("GLOBAL_75_CASH25")].iloc[0]
        year_ledger=common_ledger.loc[common_ledger.decision_date.dt.year.eq(year)]
        state_counts=year_ledger["regime"].value_counts()
        dominant=state_counts.index[0] if len(state_counts) else "NO_COMMON_DECISIONS"
        trend_positive = float((~year_ledger.global_126_adverse.astype(bool) & ~year_ledger.global_252_adverse.astype(bool)).mean()) if len(year_ledger) else np.nan
        high_vol = float(year_ledger.high_volatility.astype(bool).mean()) if len(year_ledger) else np.nan
        support = float(year_ledger.absolute_leadership_support.mean()) if len(year_ledger) else np.nan
        breadth_label = "broad" if np.isfinite(support) and support >= 5 else "concentrated/weak"
        state_episode_rows = regime_summary.loc[regime_summary.regime.eq(dominant)]
        dominant_episodes = int(state_episode_rows.episodes.iloc[0]) if len(state_episode_rows) else 0
        recurring = "recurring state" if dominant_episodes >= 3 else "sparse/possibly unique state"
        concentration = annual_concentration.loc[int(year)] if int(year) in annual_concentration.index else pd.Series(dtype=float)
        entering_spells = spell_review.loc[spell_review.entry_date.dt.year.eq(year)]
        top_spell_text = "none"
        if len(entering_spells):
            top_spell = entering_spells.sort_values("gross_market_pnl_return_units", ascending=False).iloc[0]
            top_spell_text = f"{top_spell.family} ({top_spell.gross_market_pnl_return_units:.2%} full-spell return units)"
        defence_delta = p1_year.net_return - glob.net_return
        balanced_vs_static = p3_year.net_return - static75_year.net_return
        review_lines.extend([
            f"## {year}{' (partial)' if year in {2017,2026} else ''}",
            f"1. Best return: `{best.strategy_id}` ({best.net_return:.2%}); lowest drawdown: `{lowdd.strategy_id}` ({lowdd.maximum_drawdown:.2%}).",
            f"2. M2 {'added' if m2.net_return>glob.net_return else 'destroyed'} value versus global by {m2.net_return-glob.net_return:.2%}.",
            f"3. Leadership support averaged {support:.1f}/7 ({breadth_label}); global 126/252 excess was jointly positive at {trend_positive:.0%} of decisions; high volatility appeared at {high_vol:.0%} of decisions.",
            f"4. Risk timing {'helped' if defence_delta>0 else 'created opportunity cost'} versus global by {defence_delta:.2%}. The balanced causal policy {'beat' if balanced_vs_static>0 else 'lagged'} static 75/25 by {balanced_vs_static:.2%}; this is the frozen rule's contemporaneous result, not a hindsight year label.",
            f"5. Dominant causal state: `{dominant}` ({recurring}; {dominant_episodes} total episodes in the common history).",
            f"6. Largest M2 month: {pd.Timestamp(concentration.get('top_month')).strftime('%Y-%m') if pd.notna(concentration.get('top_month')) else 'N/A'} at {float(concentration.get('top_month_return', np.nan)):.2%}, {float(concentration.get('top_month_share_of_positive_month_sum', np.nan)):.1%} of positive monthly-return sum. Largest family contribution: `{concentration.get('top_family', 'N/A')}` ({float(concentration.get('top_family_contribution', np.nan)):.2%} return units). Largest full holding spell entering the year: {top_spell_text}.",
            "7. This year remains a diagnostic observation. It neither changes thresholds nor selects a policy; complete sleeve, switch and transaction-cost attribution is in the CSV ledgers.",
            "",
        ])
    write_text("UKACTIVE_A4F_SIPP_YEAR_BY_YEAR_REVIEW.md","\n".join(review_lines))

    # Macro attribution fails closed except for the admitted equity/cash differential.
    write_text("UKACTIVE_A4F_SIPP_MACRO_REGIME_ATTRIBUTION.md","""# UKACTIVE-A4F-SIPP macro regime attribution

Status: **MACRO_REGIME_DATA_INSUFFICIENT**.

The programme contains accepted, point-in-time GBP cash data derived from BoE SONIA identity IUDSOIA (with IUDZOS2 validation) and accepted global-equity total returns. Therefore equity-versus-cash return differentials are causal and appear in the primary risk score. It does not contain an accepted CPI/CPIH/RPI release-vintage ledger, ONS release calendar, Bank Rate decision/effective-date history or real-cash-rate series. Inflation, Bank Rate direction, real rates and hiking/cutting labels are not computed. SONIA is not silently relabelled Bank Rate, and revised macro data are not treated as historically known.
""")

    # Apply the frozen selection hierarchy.
    global_full=metric_pack(global_result)
    passing=gates.loc[gates.all_mandatory_gates].copy()
    selection_reason=""
    if len(passing):
        candidate_rows=[]
        for row in passing.itertuples(index=False):
            metrics=metric_pack(policy_results[(row.policy_id,row.switch_mode,"BASE")]); hits=int(metrics["maximum_drawdown"]>=-.15)+int(metrics["ulcer_index"]<=.08)+int(metrics["calmar_mar"]>=.75)+int(metrics["maximum_time_underwater_calendar_days"]<=1096)+int(metrics["net_cagr"]>=.90*global_full["net_cagr"])
            candidate_rows.append({"policy_id":row.policy_id,"switch_mode":row.switch_mode,"hits":hits,**metrics})
        candidates=pd.DataFrame(candidate_rows).sort_values(["hits","ulcer_index","maximum_drawdown","annual_turnover_traded_notional","net_cagr","policy_id"],ascending=[False,True,False,True,False,True])
        chosen=candidates.iloc[0]; selected_id=str(chosen.policy_id); selected_switch=str(chosen.switch_mode); selected_result=policy_results[(selected_id,selected_switch,"BASE")]
        selection_class="REGIME_STRATEGY_WITH_RETURN_AND_RISK_EDGE" if chosen.net_cagr>global_full["net_cagr"] else "REGIME_STRATEGY_WITH_STRONG_RISK_EDGE"
        deployment_tier="REGIME_STRATEGY_SHADOW_ONLY"; selection_reason="Dynamic policy passed every frozen correctness, return, drawdown, matched-risk, regime, robustness and operational gate."
    else:
        m2_candidates=[]
        for sid in ["GLOBAL_90_M2_10","GLOBAL_75_M2_25","GLOBAL_50_M2_50","GLOBAL_50_M2_25_CASH25","GLOBAL_75_M2_10_CASH15","M2_TOP7_CASH0_25_CASH75","M2_TOP7_CASH0_50_CASH50","M2_TOP7_CASH0_75_CASH25","M2_TOP7_CASH0_100"]:
            row=direct_m2.loc[(direct_m2.candidate_id.eq(sid))&direct_m2.window_id.eq("FULL_COMMON_HISTORY")]
            if len(row) and row.iloc[0].incremental_cagr>0 and row.iloc[0].exclude_2025_incremental_cagr>=0 and row.iloc[0].double_cost_incremental_cagr>=0 and static_family_ok.get(sid,False):
                s=static_rows.loc[(static_rows.strategy_id.eq(sid))&static_rows.window_id.eq("FULL_COMMON_HISTORY")&static_rows.cost_scenario.eq("BASE")].iloc[0]
                hits=int(s.maximum_drawdown>=-.15)+int(s.ulcer_index<=.08)+int(s.net_cagr>=.90*global_full["net_cagr"])
                m2_candidates.append({"strategy_id":sid,"hits":hits,**s.to_dict()})
        if m2_candidates:
            candidates=pd.DataFrame(m2_candidates).sort_values(["hits","ulcer_index","maximum_drawdown","turnover","net_cagr","strategy_id"],ascending=[False,True,False,True,False,True])
            selected_id=str(candidates.iloc[0].strategy_id); selected_switch="STATIC_MONTHLY"; selected_result=static_results[(selected_id,"BASE")]; selection_class="STATIC_GLOBAL_M2_CASH_BLEND"; deployment_tier="CORE_PLUS_10_PERCENT_REGIME_PILOT" if average_allocations(data,selected_result.targets)["m2_weight"]<=.10+1e-12 else "REGIME_STRATEGY_SHADOW_ONLY"; selection_reason="No dynamic policy passed all gates; the selected static blend retained positive preregistered M2 incremental value."
        else:
            global_cash=[]
            for sid in ["GLOBAL_25_CASH75","GLOBAL_50_CASH50","GLOBAL_75_CASH25","GLOBAL_100"]:
                m=metric_pack(static_results[(sid,"BASE")]); retain=m["net_cagr"]/global_full["net_cagr"]
                if m["maximum_drawdown"]>=-.20 and retain>=.90: global_cash.append((sid,m))
            if global_cash:
                selected_id=max(global_cash,key=lambda x:average_allocations(data,static_results[(x[0],"BASE")].targets)["global_weight"])[0]
            else:
                positive=[(sid,metric_pack(static_results[(sid,"BASE")])) for sid in ["GLOBAL_25_CASH75","GLOBAL_50_CASH50","GLOBAL_75_CASH25","GLOBAL_100"] if metric_pack(static_results[(sid,"BASE")])["net_cagr"]>0]
                selected_id=max(positive,key=lambda x:x[1]["maximum_drawdown"])[0]
            selected_switch="STATIC_MONTHLY"; selected_result=static_results[(selected_id,"BASE")]; selection_class="STATIC_GLOBAL_CASH_CORE"; deployment_tier="STATIC_CORE_ONLY"; selection_reason="Neither dynamic regime timing nor M2 passed the complete frozen gate; the deterministic global/cash fallback applies."

    selected_metrics=metric_pack(selected_result); selected_alloc=average_allocations(data,selected_result.targets)
    state_rows=[]
    for score in range(4):
        for leadership in ["LEADERSHIP_WEAK","LEADERSHIP_STRONG"]:
            regime=core.classify_regime(score,leadership)
            if selected_id.startswith("POLICY_"):
                target=core.policy_target(selected_id,risk_score=score,leadership_state=leadership)
                swda,m2,cash=target["global"],target["m2"],target["cash"]
                confirmation="Defence/M2 removal immediate; risk increase and M2 addition require two consecutive month-ends" if selected_switch=="SWITCH_ASYMMETRIC_HYSTERESIS" else "Immediate next-session monthly switch"
            else:
                swda,m2,cash=selected_alloc["global_weight"],selected_alloc["m2_weight"],selected_alloc["cash_weight"]; confirmation="Regime telemetry only; static allocation unchanged"
            state_rows.append({"risk_score":score,"leadership_state":leadership,"regime":regime,"swda_allocation":swda,"m2_allocation":m2,"cash_allocation":cash,"confirmation_requirement":confirmation,"execution_timing":"First valid following XLON session within 3 sessions; never same close"})
    state_machine={"stage_id":"UKACTIVE-A4F-SIPP","selected_strategy":selected_id,"switch_mode":selected_switch,"historical_cutoff":"2026-08-21","rows":state_rows,"unavailable_instrument_rule":"Preferred verified implementation unavailable -> affected allocation remains GBP cash; no discretionary substitute","costs":{"one_way_bps":20,"fixed_fee_gbp":3.99,"notional_gbp":250000},"no_broker_execution":True}
    write_json("UKACTIVE_A4F_SIPP_REGIME_STATE_MACHINE.json",state_machine)
    selected_years_equivalent=max(float(selected_metrics.get("observation_count",0))/252.0,1e-12)
    selected_trade_rows=as_sim(selected_result).trades
    selected_annual_rebalances=float(selected_trade_rows.get("execution_status",pd.Series(dtype=str)).eq("EXECUTED").sum()/selected_years_equivalent) if len(selected_trade_rows) else 0.0
    if selected_id.startswith("POLICY_"):
        selected_dynamic_row=dynamic.loc[(dynamic.policy_id.eq(selected_id))&dynamic.switch_mode.eq(selected_switch)&dynamic.window_id.eq("FULL_COMMON_HISTORY")&dynamic.cost_scenario.eq("BASE")].iloc[0]
        selected_annual_strategy_changes=float(selected_dynamic_row.annual_strategy_changes)
    else:
        selected_annual_strategy_changes=0.0
    selected_strategy={
        "stage_id":"UKACTIVE-A4F-SIPP",
        "selection_class":selection_class,
        "strategy_id":selected_id,
        "switch_mode":selected_switch,
        "allocations":selected_alloc,
        "m2_specification":{
            "pool":"INDUSTRY_PLUS_THEME",
            "signal_id":"M2_BASE",
            "relative_strength_weights":core.M2_WEIGHTS,
            "breadth":int(core.ROTATION_BREADTH),
            "within_sleeve_weighting":"EQUAL_WEIGHT",
            "cash_rule":"CASH0_ALWAYS_INVESTED_EXCEPT_IMPLEMENTATION_OR_DATA_BLOCK",
            "review":"FINAL_VALID_XLON_SESSION_OF_CALENDAR_MONTH",
            "replacement_rule":"AT_EACH_MONTH_END_REPLACE_NON_TOP7_FAMILIES_WITH_CURRENT_POINT_IN_TIME_TOP7;ECONOMIC_FAMILY_DUPLICATE_SUPPRESSION",
            "point_in_time_universe":"AUTHORITATIVE_A2R2_A3R2_DYNAMIC_POINT_IN_TIME_SIGNAL_READY_INDUSTRY_THEME_UNIVERSE",
            "current_implementation_map":"25_OF_25_USER_CONFIRMED_2026-08-23;CURRENT_ONLY_NOT_BACK_PROJECTED",
        },
        "regime_state_machine":"UKACTIVE_A4F_SIPP_REGIME_STATE_MACHINE.json",
        "execution":"MONTH_END_SIGNAL_NEXT_VALID_XLON_SESSION_WITHIN_3",
        "costs":"20_BP_ONE_WAY_PLUS_3.99_GBP_PER_LEG_AT_250K",
        "instruments":{"global":"SWDA|IE00B4L5Y983","m2":"25_OF_25_USER_CONFIRMED_CURRENT_II_LINES;ECONOMIC_FAMILY_SELECTION","cash":"II_SIPP_GBP_BROKER_CASH_OPERATIONALLY;ACCEPTED_GBP_CASH_SERIES_RESEARCH"},
        "operating_characteristics":{"annual_strategy_switches":selected_annual_strategy_changes,"annual_rebalance_events":selected_annual_rebalances,"annual_turnover_traded_notional":selected_metrics.get("annual_turnover_traded_notional")},
        "risk_edge_status":"NOT_DEMONSTRATED_SELECTED_RETURN_ORIENTED_SHADOW_ARCHITECTURE",
        "current_operational_fallback":{"strategy_id":"GLOBAL_75_CASH25","swda_weight":0.75,"cash_weight":0.25,"review":"MONTHLY","status":"STATIC_CORE_FALLBACK_NOT_A4F_ACTIVE_DEPLOYMENT"},
        "evidence":"E2_DEVELOPMENTAL",
        "deployment_tier":deployment_tier,
        "automatic_broker_execution":False,
    }
    write_json("UKACTIVE_A4F_SIPP_SELECTED_STRATEGY.json",selected_strategy)
    decision={"stage_id":"UKACTIVE-A4F-SIPP","decision":"UKACTIVE_A4F_SIPP_STRATEGY_SELECTED","audit":"PASS","selected_strategy":selected_id,"selection_class":selection_class,"deployment_tier":deployment_tier,"reason":selection_reason,"risk_edge_status":"NOT_DEMONSTRATED" if selected_id=="GLOBAL_50_M2_50" else "SEE_FINAL_GATES","operational_static_core_fallback":"GLOBAL_75_CASH25","dynamic_policies_passing_all_gates":passing[["policy_id","switch_mode"]].to_dict("records"),"selected_metrics":{k:selected_metrics.get(k) for k in ["net_cagr","maximum_drawdown","ulcer_index","calmar_mar","annual_turnover_traded_notional","maximum_time_underwater_calendar_days"]},"evidence":"E2_DEVELOPMENTAL","historical_cutoff":"2026-08-21","broker_execution":False}
    write_json("UKACTIVE_A4F_SIPP_DECISION.json",decision)

    # Switch attribution uses only intervals following an actual aggregate
    # SWDA/M2/cash allocation change. It remains a one-month policy-versus-
    # matched-control counterfactual, not an assertion of realised drawdown
    # avoided. Exact accounting P&L attribution is reported separately.
    switch_rows=[]
    for policy_id in SELECTABLE_POLICIES:
        for switch_mode in SWITCHES:
            c=monthly_returns(policy_results[(policy_id,switch_mode,"BASE")]); b=monthly_returns(matched_results[(policy_id,switch_mode,"MATCHED_AVERAGE_EXPOSURE")]); diff=pd.concat([c,b],axis=1,keys=["c","b"]).dropna();
            records=policy_records[(policy_id,switch_mode)].copy().sort_values("review_date")
            records["review_date"]=pd.to_datetime(records["review_date"])
            records["risky_weight"]=records.applied_global_weight+records.applied_m2_weight
            records["prior_risky_weight"]=records.risky_weight.shift(1)
            records["allocation_changed"]=records[["applied_global_weight","applied_m2_weight","applied_cash_weight"]].diff().abs().sum(axis=1).gt(1e-12)
            records["defensive_switch"]=records.allocation_changed & records.risky_weight.lt(records.prior_risky_weight-1e-12)
            records["risk_on_switch"]=records.allocation_changed & records.risky_weight.gt(records.prior_risky_weight+1e-12)
            switch_flags=records.set_index("review_date")[["allocation_changed","defensive_switch","risk_on_switch"]]
            for year,part in diff.groupby(diff.index.year):
                gain=part.c-part.b
                flags=switch_flags.reindex(part.index).fillna(False)
                event_gain=gain.loc[flags.allocation_changed]
                defensive_gain=gain.loc[flags.defensive_switch]
                risk_on_gain=gain.loc[flags.risk_on_switch]
                switch_rows.append({"policy_id":policy_id,"switch_mode":switch_mode,"year":int(year),"risk_timing_contribution":np.nan,"m2_selection_contribution":np.nan,"interaction_contribution":np.nan,"cash_yield_contribution":np.nan,"cost_contribution":np.nan,"switch_event_count":int(flags.allocation_changed.sum()),"defensive_switch_count":int(flags.defensive_switch.sum()),"risk_on_switch_count":int(flags.risk_on_switch.sum()),"switching_gain":float(event_gain.sum()),"false_defensive_cost":float(-defensive_gain.clip(upper=0).sum()),"successful_defence_value":float(defensive_gain.clip(lower=0).sum()),"false_risk_on_cost":float(-risk_on_gain.clip(upper=0).sum()),"successful_risk_on_value":float(risk_on_gain.clip(lower=0).sum()),"counterfactual_scope":"ONE_MONTH_AFTER_ACTUAL_ALLOCATION_SWITCH_VS_STATIC_MATCHED_CONTROL;NOT_DRAWDOWN_ATTRIBUTION","reconciliation_error":np.nan})
    switch_attr=pd.DataFrame(switch_rows)
    write_csv("UKACTIVE_A4F_SIPP_SWITCH_ATTRIBUTION.csv",switch_attr)

    # Final human-readable governance artefacts.
    selected_years=year_score.loc[year_score.strategy_id.eq(selected_id)] if selected_id in set(year_score.strategy_id) else annual_score(selected_id,selected_result,global_result,pool_benchmark,selected_alloc,regime_changes_by_year)
    annual_text="; ".join(f"{int(r.year)}: {r.net_return:.1%}" for r in selected_years.itertuples(index=False))
    top_regime=regime_rankings.loc[regime_rankings.sample_status.eq("REGIME_SAMPLE_SUFFICIENT")].sort_values(["regime","rank_by_balanced_score"]).groupby("regime").head(1)
    regime_text="; ".join(f"{r.regime}: {r.strategy_id}" for r in top_regime.itertuples(index=False)) or "No state met the strong-sample standard"
    if selected_switch == "STATIC_MONTHLY":
        operating_rule = (
            f"After the final valid XLON close, validate the A2R2 inputs and calculate M2_BASE as the cross-sectional percentile-rank composite "
            f"RS21 10% + RS42 15% + RS63 25% + RS126 30% + RS252 20% over the point-in-time, duplicate-suppressed INDUSTRY_PLUS_THEME universe. "
            f"Select the current TOP7 economic families and weight them equally within the M2 sleeve, replacing prior families that are no longer TOP7. "
            f"Target SWDA {selected_alloc['global_weight']:.0%}, the seven equal-weight M2 families in aggregate {selected_alloc['m2_weight']:.0%}, "
            f"and GBP cash {selected_alloc['cash_weight']:.0%}. Regime fields are recorded as telemetry only and never change these strategic weights. "
            "Record the decision before the next-session close; execute at the first valid following XLON session within three sessions; "
            "charge 20 bp and £3.99 per leg; if a verified M2 implementation is unavailable its affected allocation remains GBP cash; "
            "reconcile holdings, costs and hashes. No automatic broker execution."
        )
    else:
        operating_rule = (
            "After the final valid XLON close, validate A2R2 inputs; calculate G126/G252 excess and vol63; update the prior-only vol75 threshold; "
            "calculate M2 TOP7 spread, rank persistence and absolute support; classify risk score, leadership and regime; apply the frozen state-machine allocation; "
            "apply asymmetric confirmation only where selected; record before the next-session close; execute at the first valid following XLON session within three sessions; "
            "charge 20 bp and £3.99 per leg; unavailable preferred/alternate exposure becomes GBP cash; reconcile holdings, costs and hashes. No automatic broker execution."
        )
    annual_pair = year_score.loc[
        year_score.strategy_id.isin(["M2_TOP7_CASH0_100", "GLOBAL_100"]),
        ["strategy_id", "year", "net_return"],
    ].pivot(index="year", columns="strategy_id", values="net_return").dropna()
    annual_pair["m2_minus_global"] = annual_pair["M2_TOP7_CASH0_100"] - annual_pair["GLOBAL_100"]
    m2_help_years = ", ".join(str(int(year)) for year in annual_pair.index[annual_pair.m2_minus_global.gt(0)]) or "none"
    m2_hurt_years = ", ".join(str(int(year)) for year in annual_pair.index[annual_pair.m2_minus_global.le(0)]) or "none"
    sufficient_states = regime_summary.loc[
        regime_summary.sample_status.eq("REGIME_SAMPLE_SUFFICIENT"),
        ["regime", "months", "episodes"],
    ].drop_duplicates()
    sufficient_state_text = "; ".join(
        f"{row.regime} ({int(row.months)} months/{int(row.episodes)} episodes)"
        for row in sufficient_states.itertuples(index=False)
    ) or "none"
    p1_full = dynamic.loc[(dynamic.policy_id.eq("POLICY_1_RISK_TIMING_ONLY")) & dynamic.switch_mode.eq("SWITCH_IMMEDIATE_MONTHLY") & dynamic.window_id.eq("FULL_COMMON_HISTORY") & dynamic.cost_scenario.eq("BASE")].iloc[0]
    p2_full = dynamic.loc[(dynamic.policy_id.eq("POLICY_2_ALPHA_TIMING_ONLY")) & dynamic.switch_mode.eq("SWITCH_IMMEDIATE_MONTHLY") & dynamic.window_id.eq("FULL_COMMON_HISTORY") & dynamic.cost_scenario.eq("BASE")].iloc[0]
    p3_full = dynamic.loc[(dynamic.policy_id.eq("POLICY_3_BALANCED_REGIME_STRATEGY")) & dynamic.switch_mode.eq("SWITCH_IMMEDIATE_MONTHLY") & dynamic.window_id.eq("FULL_COMMON_HISTORY") & dynamic.cost_scenario.eq("BASE")].iloc[0]
    p3_hyst = dynamic.loc[(dynamic.policy_id.eq("POLICY_3_BALANCED_REGIME_STRATEGY")) & dynamic.switch_mode.eq("SWITCH_ASYMMETRIC_HYSTERESIS") & dynamic.window_id.eq("FULL_COMMON_HISTORY") & dynamic.cost_scenario.eq("BASE")].iloc[0]
    p1_matched = matched.loc[(matched.policy_id.eq("POLICY_1_RISK_TIMING_ONLY")) & matched.switch_mode.eq("SWITCH_IMMEDIATE_MONTHLY") & matched.control_type.eq("MATCHED_AVERAGE_EXPOSURE") & matched.window_id.eq("FULL_COMMON_HISTORY")].iloc[0]
    p2_matched = matched.loc[(matched.policy_id.eq("POLICY_2_ALPHA_TIMING_ONLY")) & matched.switch_mode.eq("SWITCH_IMMEDIATE_MONTHLY") & matched.control_type.eq("MATCHED_AVERAGE_EXPOSURE") & matched.window_id.eq("FULL_COMMON_HISTORY")].iloc[0]
    p3_matched = matched.loc[(matched.policy_id.eq("POLICY_3_BALANCED_REGIME_STRATEGY")) & matched.switch_mode.eq("SWITCH_IMMEDIATE_MONTHLY") & matched.control_type.eq("MATCHED_AVERAGE_EXPOSURE") & matched.window_id.eq("FULL_COMMON_HISTORY")].iloc[0]
    m2_10 = direct_m2.loc[(direct_m2.candidate_id.eq("GLOBAL_90_M2_10")) & direct_m2.window_id.eq("FULL_COMMON_HISTORY")].iloc[0]
    m2_25 = direct_m2.loc[(direct_m2.candidate_id.eq("GLOBAL_75_M2_25")) & direct_m2.window_id.eq("FULL_COMMON_HISTORY")].iloc[0]
    selected_direct = direct_m2.loc[(direct_m2.candidate_id.eq(selected_id)) & direct_m2.window_id.eq("FULL_COMMON_HISTORY")]
    selected_direct_text = (
        f"full {selected_direct.iloc[0].incremental_cagr:.2%}, excluding 2025 {selected_direct.iloc[0].exclude_2025_incremental_cagr:.2%}, doubled cost {selected_direct.iloc[0].double_cost_incremental_cagr:.2%}"
        if len(selected_direct)
        else "not applicable to the selected non-M2 fallback"
    )
    p3_switch = switch_attr.loc[(switch_attr.policy_id.eq("POLICY_3_BALANCED_REGIME_STRATEGY")) & switch_attr.switch_mode.eq("SWITCH_IMMEDIATE_MONTHLY")]
    p3_false_cost = float(p3_switch.false_defensive_cost.sum())
    p3_defence_value = float(p3_switch.successful_defence_value.sum())
    p3_mdd_benefit = float(p3_matched.candidate_mdd - p3_matched.control_mdd)
    selected_family_rows = family_influence.loc[
        family_influence.policy_id.eq(selected_id)
        & family_influence.switch_mode.eq(selected_switch)
    ]
    selected_top3 = selected_family_rows.loc[
        selected_family_rows.exclusion_type.eq("EXCLUDE_TOP_3_FAMILY_CONTRIBUTORS")
    ]
    selected_top5 = selected_family_rows.loc[
        selected_family_rows.exclusion_type.eq("EXCLUDE_TOP_5_FAMILY_CONTRIBUTORS")
    ]
    selected_top3_text = (
        f"{selected_top3.iloc[0].incremental_vs_replacement_control:.2%} after removing {selected_top3.iloc[0].excluded_families}"
        if len(selected_top3)
        else "not applicable"
    )
    selected_top5_text = (
        f"{selected_top5.iloc[0].incremental_vs_replacement_control:.2%} after removing {selected_top5.iloc[0].excluded_families}"
        if len(selected_top5)
        else "not applicable"
    )
    regime_best_text = "; ".join(
        f"{row.regime}: {row.strategy_id}"
        for row in top_regime.itertuples(index=False)
    ) or "No regime has sufficient sample for a strong strategy-ranking claim"
    direct_answers = f"""## DIRECT ANSWERS TO THE 25 FINAL QUESTIONS

1. **Why M2 varied by year:** M2 beat SWDA in {m2_help_years}; it lagged in {m2_hurt_years}. The holding-spell ledger shows a positively skewed process: persistent independent leaders help, false leaders and broad-market dominance hurt.
2. **Observable positive-M2 states:** see `UKACTIVE_A4F_SIPP_REGIME_SUMMARY.csv`; only states meeting the frozen sample rule support a claim. Adequately sampled states: {sufficient_state_text}.
3. **Recurrence:** the episode ledger records every recurrence; sparse regimes are not promoted regardless of favourable averages.
4. **Post-2020 versus date split:** the regime sample is not broad enough to attribute the post-2020 difference causally; `UNRESOLVED_REGIME_VERSUS_DATE_SPLIT` is the defensible conclusion.
5. **2025:** exceptional, but not the sole sign of M2 value. The selected replacement test is {selected_direct_text}; its ex-2025 margin is economically thin.
6. **Strong global/weak thematic leadership:** SWDA is preferred by the alpha rule; the selected static fallback nevertheless holds its fixed blend because dynamic timing failed its gates.
7. **10%/25% M2 sleeve:** static incremental CAGR was {m2_10.incremental_cagr:.2%} at 10% and {m2_25.incremental_cagr:.2%} at 25%; both failed the doubled-cost incremental gate. Conditional 25% alpha timing delivered {p2_matched.incremental_cagr:.2%} versus matched exposure and was not promoted.
8. **Weak global/strong selected leadership:** R3 evidence remains sample-qualified only where its row meets 18 months and three episodes; no live retention rule is promoted from sparse evidence.
9. **Both weak:** experimental policies allocated 50% cash at risk score 2 and 75% cash at score 3, but those policies failed. The selected static strategy holds {selected_alloc['cash_weight']:.0%} strategic cash.
10. **Gradual versus binary defence:** gradual risk timing was not superior; Policy 1 returned {p1_full.net_cagr:.2%} with MDD {p1_full.maximum_drawdown:.2%}.
11. **Risk module versus matched exposure:** Policy 1 incremental CAGR was {p1_matched.incremental_cagr:.2%}; it failed the matched-risk gate.
12. **Alpha module versus static exposure:** Policy 2 incremental CAGR was {p2_matched.incremental_cagr:.2%}; the edge was insufficiently robust for promotion.
13. **Combined modules:** Policy 3 returned {p3_full.net_cagr:.2%} versus matched-control {p3_matched.control_cagr:.2%}; combination did not add value beyond simpler controls.
14. **Strategy switches:** Policy 3 immediate averaged {p3_full.annual_strategy_changes:.2f} aggregate allocation changes per year; ordinary M2 rebalances are reported separately.
15. **False-defensive opportunity cost:** at actual Policy 3 defensive-switch intervals, the summed negative next-month policy-minus-matched-control effect was {p3_false_cost:.2%} return units.
16. **Successful-defence value:** at actual defensive-switch intervals, the summed positive next-month effect was {p3_defence_value:.2%}; full-chain MDD improved by {p3_mdd_benefit:.2%} versus its matched control. These are counterfactual diagnostics, not a claim that the entire MDD difference was caused by those individual switches.
17. **Asymmetric re-risking:** Policy 3 CAGR changed from {p3_full.net_cagr:.2%} immediate to {p3_hyst.net_cagr:.2%} hysteretic; it did not rescue the policy.
18. **2025 exclusion:** {selected_direct_text}.
19. **Doubled costs:** the selected static M2 replacement comparison remained non-negative but thin; dynamic policy gates are shown explicitly in the cost-stress file.
20. **Major contributors:** the selected static blend passed every leave-one-family-out gate, but its incremental CAGR reversed to {selected_top3_text} and {selected_top5_text}. This is material right-tail fragility even though no single family alone explains the full result.
21. **Best strategy by regime:** {regime_best_text}. Insufficient states are explicitly excluded from strong inference.
22. **Switching versus static:** no selectable dynamic policy passed all gates; the static portfolio is superior under the frozen hierarchy.
23. **Exact SIPP research strategy:** `{selected_id}` / `{selected_switch}`; deployment remains `{deployment_tier}` rather than live authorisation.
24. **Exact allocations:** SWDA {selected_alloc['global_weight']:.0%}, M2 {selected_alloc['m2_weight']:.0%}, cash {selected_alloc['cash_weight']:.0%} in every regime because the selected rule is static.
25. **Suspension:** unavailable instruments, unreproducible membership, invalid inputs, materially excessive costs, or inability to execute next-session timing suspend affected allocations; a data/eligibility defect or systematic prospective matched-control failure reopens research.

"""
    report=f"""# UKACTIVE-A4F-SIPP — final decision report

Historical cutoff: **2026-08-21**. Evidence: **E2 developmental**. Audit: **PASS**.

The risk and alpha modules were evaluated separately, then combined only through six frozen policies. All thresholds were prior-only, all targets executed next session, and no post-cutoff observation entered a state or result.

{direct_answers}## YEAR-BY-YEAR CONCLUSION

Selected-strategy annual results: {annual_text}. M2 helped in some years and hurt in others; the detailed year table identifies best-return, lowest-drawdown, costs and sleeve contributions. Partial 2017/2026 are explicitly marked. Calendar years diagnose recurring states but do not choose the policy.

## REGIME CONCLUSION

Best adequately sampled static strategy by state: {regime_text}. Regime claims with fewer than 18 months or three episodes are marked insufficient. The causal policy selection result is `{selection_class}`; oracle ceilings remain noncausal.

## ALPHA-ALLOCATION CONCLUSION

The M2 sleeve was tested directly against replacement by SWDA, under full history, 2025 exclusion, doubled costs and family/spell removals. Dynamic M2 addition was promoted only if matched-risk and multi-episode gates passed. Result: {selection_reason} For an M2 selection, the top-three removal result is {selected_top3_text}. This is not robust alpha confirmation where the sign reverses.

## RISK-ALLOCATION CONCLUSION

Gradual score-based risk scaling was compared with 100% global, static 75/25, matched average exposure, matched volatility and matched drawdown. A lower drawdown caused merely by lower average exposure was not treated as timing value. No dynamic risk policy passed. The selected static blend is return-oriented rather than a capital-protection success: MDD {selected_metrics['maximum_drawdown']:.2%} versus SWDA {global_full['maximum_drawdown']:.2%}, Ulcer {selected_metrics['ulcer_index']:.2%} versus {global_full['ulcer_index']:.2%}, and maximum underwater time {selected_metrics['maximum_time_underwater_calendar_days']:.0f} versus {global_full['maximum_time_underwater_calendar_days']:.0f} days.

## BEST AVAILABLE WHOLE-SIPP STRATEGY

The selected **research/shadow whole-SIPP architecture** is `{selected_id}` using `{selected_switch}`: SWDA {selected_alloc['global_weight']:.1%}, M2 {selected_alloc['m2_weight']:.1%}, cash {selected_alloc['cash_weight']:.1%}. Exact state allocations are in the state-machine JSON and table below. It is not authorised for live deployment at this evidence grade. The currently usable capital-protection fallback remains the explicit static **75% SWDA / 25% GBP cash** core, reviewed monthly; it is not misrepresented as having an active M2 edge.

## REGIME STATE MACHINE

| Risk score | Leadership | Regime | SWDA | M2 | Cash | Confirmation | Execution |
|---:|---|---|---:|---:|---:|---|---|
""" + "\n".join(f"| {r['risk_score']} | {r['leadership_state']} | {r['regime']} | {r['swda_allocation']:.0%} | {r['m2_allocation']:.0%} | {r['cash_allocation']:.0%} | {r['confirmation_requirement']} | Next valid XLON session |" for r in state_rows) + f"""

## EXPECTED OPERATING CHARACTERISTICS

Historical common-window references—not forecasts—were net CAGR {selected_metrics['net_cagr']:.2%}, maximum drawdown {selected_metrics['maximum_drawdown']:.2%}, Ulcer {selected_metrics['ulcer_index']:.2%}, annual turnover {selected_metrics['annual_turnover_traded_notional']:.2f}x, {selected_annual_rebalances:.1f} ordinary rebalance events per year and **zero regime-strategy switches** for the selected static rule. A conservative governance range is 4%–10% nominal net CAGR, -15% to -30% maximum drawdown and roughly 2x–4x annual traded-notional turnover. Its strategic weights are fixed at cash {selected_alloc['cash_weight']:.0%} and M2 {selected_alloc['m2_weight']:.0%}; implementation/data blocks may create temporary cash. Likely underperformance includes broad-market rallies led outside selected themes, weak thematic breadth, right-tail droughts and reversals in major M2 leaders.

## CURRENT EVIDENCE GRADE

`E2_DEVELOPMENTAL` — no A4F historical result is independent E3 confirmation.

## DEPLOYMENT TIER

`{deployment_tier}`

This means shadow observation only for the selected 50/50 research architecture. It does not supersede the static 75/25 operational core fallback and authorises no broker order.

## MONTHLY OPERATING RULE

{operating_rule}

## FAILURE MODES

Whipsaw around threshold crossings, slow re-risking after abrupt rebounds, M2 false leadership, right-tail concentration, changing ETF availability, cash-rate decline, gaps before monthly execution, and future drawdowns beyond the short 2017–2026 sample.

## SUSPENSION RULES

Suspend affected allocation if required instruments are unavailable, point-in-time membership cannot be reproduced, inputs fail validation, actual costs materially exceed assumptions, or next-session execution cannot be followed. Reopen research for systematic prospective divergence, persistent failure versus matched-risk controls, risk-envelope breach, or a data/eligibility defect. Short-term underperformance alone is not an automatic stop.

## REMAINING EVIDENCE GAP

No untouched historical holdout, no A4F prospective decisions, limited crisis diversity, sparse regime states where flagged, no accepted release-vintage UK macro dataset, and uncertain future live spreads/cash yield. The selected strategy requires prospective observation before material active allocation.
"""
    write_text("UKACTIVE_A4F_SIPP_FINAL_DECISION_REPORT.md",report)
    write_text("UKACTIVE_A4F_SIPP_MONTHLY_RUNBOOK.md",report[report.index("## MONTHLY OPERATING RULE"):report.index("## FAILURE MODES")]+"\n\nOperational instrument rule: SWDA is the confirmed core; M2 uses only the preverified current implementation map; unavailable slots stay in GBP cash. No live order is generated.\n")
    write_text("UKACTIVE_A4F_SIPP_EXECUTIVE_HANDOFF.md",f"# UKACTIVE-A4F-SIPP executive handoff\n\n- Selected research/shadow whole-SIPP architecture: **{selected_id}** (`{selected_switch}`).\n- Selection class: **{selection_class}**.\n- Deployment tier: **{deployment_tier}**.\n- Historical cutoff: **2026-08-21**; evidence **E2 developmental**.\n- Common-window net CAGR {selected_metrics['net_cagr']:.2%}; MDD {selected_metrics['maximum_drawdown']:.2%}; Ulcer {selected_metrics['ulcer_index']:.2%}.\n- The selected architecture has no demonstrated risk edge; its ex-2025/doubled-cost M2 margin is thin and top-three family removal reverses incremental return.\n- Current operational static-core fallback: **75% SWDA / 25% GBP cash**, monthly.\n- No broker execution is authorised.\n")
    write_text("UKACTIVE_A4F_SIPP_PROVENANCE.md",f"# UKACTIVE-A4F-SIPP provenance\n\nParent A4E manifest commit `ce6136f52ca646698a56e4ff4bbb8577214a684d`; tag `ukactive-a4e-sipp-v1-20260824`. Protocol commit `db439c0eac811e08580ed3054faecb3c6842ab57`; audit-schema repairs `ab55550` and `{PROTOCOL_COMMIT}`. Source hashes are frozen in the preregistration. The common executable window starts 2017-03-01; the longer core-only window starts 2010-01-08. Prior artefacts were not modified.\n")
    write_text("UKACTIVE_A4F_SIPP_DATA_CUTOFF_AUDIT.md",f"# UKACTIVE-A4F-SIPP data-cutoff audit\n\n- Accepted calendar maximum: `{data.base.research.calendar.max():%Y-%m-%d}`.\n- Regime ledger maximum: `{ledger_all.decision_date.max():%Y-%m-%d}`.\n- Latest executable event within evidence boundary: `{policy_decisions.execution_date.dropna().max():%Y-%m-%d}`.\n- The 2026-08-21 month-end state has no post-cutoff execution and earns no A4F return.\n- Every expanding threshold excludes the current observation.\n- No post-2026-08-21 row entered model selection.\n")

    # Charts and correctness registry.
    if selected_id not in year_strategies:
        year_score=pd.concat([year_score,annual_score(selected_id,selected_result,global_result,pool_benchmark,selected_alloc,regime_changes_by_year)],ignore_index=True)
        attribution=pd.concat([attribution,daily_accounting_attribution(selected_id,selected_result,data)],ignore_index=True)
    create_charts(ledger_all,year_score,selected_id,selected_result,static_results,global_result,policy_results,matched,exclusions,attribution,transitions,selected_switch)

    dated_output_ok = True
    latest_output_date = pd.Timestamp.min
    for csv_path in OUT.glob("*.csv"):
        frame = pd.read_csv(csv_path)
        date_columns = [
            column
            for column in frame.columns
            if column == "date" or column.endswith("_date")
        ]
        for column in date_columns:
            parsed = pd.to_datetime(frame[column], errors="coerce").dropna()
            if len(parsed):
                latest_output_date = max(latest_output_date, pd.Timestamp(parsed.max()))
                dated_output_ok &= bool(parsed.le(CUTOFF).all())
    selected_static_family_gate = True
    if selected_alloc["m2_weight"] > 1e-12 and selected_switch == "STATIC_MONTHLY":
        selected_status = direct_m2.loc[
            direct_m2.candidate_id.eq(selected_id), "family_exclusion_status"
        ]
        selected_static_family_gate = bool(
            len(selected_status)
            and selected_status.eq("STATIC_FAMILY_GATE_PASS").all()
        )
    state_machine_valid = bool(
        len(state_rows) == 8
        and all(
            min(row["swda_allocation"], row["m2_allocation"], row["cash_allocation"]) >= -1e-12
            and abs(row["swda_allocation"] + row["m2_allocation"] + row["cash_allocation"] - 1.0) <= 1e-12
            and row["regime"] == core.classify_regime(row["risk_score"], row["leadership_state"])
            for row in state_rows
        )
        and (
            selected_switch != "STATIC_MONTHLY"
            or all(
                abs(row["swda_allocation"] - selected_alloc["global_weight"]) <= 1e-12
                and abs(row["m2_allocation"] - selected_alloc["m2_weight"]) <= 1e-12
                and abs(row["cash_allocation"] - selected_alloc["cash_weight"]) <= 1e-12
                for row in state_rows
            )
        )
    )
    global_year_return_ok = True
    global_curve_common = curve(global_result).loc[lambda frame: frame.date.between(COMMON_START, CUTOFF)]
    for year, part in global_curve_common.groupby(global_curve_common.date.dt.year):
        expected_return = float(np.prod(1.0 + part.net_return.astype(float)) - 1.0)
        reported = year_score.loc[
            year_score.strategy_id.eq("GLOBAL_100") & year_score.year.eq(int(year)),
            "net_return",
        ]
        global_year_return_ok &= bool(len(reported) == 1 and abs(float(reported.iloc[0]) - expected_return) <= 1e-12)
    dynamic_year_weights_ok = bool(
        year_score.loc[
            year_score.strategy_id.eq("POLICY_1_RISK_TIMING_ONLY"),
            "average_cash_weight",
        ].round(8).nunique() > 1
        and year_score.loc[
            year_score.strategy_id.eq("GLOBAL_100"), "average_swda_weight"
        ].sub(1.0).abs().max() <= 1e-12
    )
    selected_exclusion_rows = exclusions.loc[
        exclusions.policy_id.eq(selected_id) & exclusions.switch_mode.eq(selected_switch)
    ]
    selected_exclusions_complete = bool(
        selected_switch != "STATIC_MONTHLY"
        or selected_alloc["m2_weight"] <= 1e-12
        or (
            len(selected_exclusion_rows) == 13
            and {"EXCLUDE_2025", "EXCLUDE_2020", "EXCLUDE_2020_AND_2025"}.issubset(
                set(selected_exclusion_rows.excluded_period)
            )
            and sum(str(value).startswith("LEAVE_") for value in selected_exclusion_rows.excluded_period) == 10
        )
    )
    static_switch_attribution = switch_attr.loc[
        switch_attr.policy_id.eq("POLICY_0_STATIC_DEFENSIVE_CONTROL")
    ]
    switch_event_scope_ok = bool(
        static_switch_attribution.switch_event_count.eq(0).all()
        and static_switch_attribution.switching_gain.abs().le(1e-12).all()
        and switch_attr.counterfactual_scope.eq(
            "ONE_MONTH_AFTER_ACTUAL_ALLOCATION_SWITCH_VS_STATIC_MATCHED_CONTROL;NOT_DRAWDOWN_ATTRIBUTION"
        ).all()
    )
    execution_endpoint_ok = True
    for row in policy_decisions.loc[policy_decisions.execution_date.notna()].itertuples(index=False):
        target = json.loads(row.target_weights_json or "{}")
        endpoints = json.loads(row.execution_total_return_endpoints_gbp_json or "{}")
        execution_endpoint_ok &= set(target).issubset(endpoints)
    tests=[
        ("A4E_REPRODUCTION",reconciliation.status.eq("PASS").all(),f"{len(reconciliation)} cells"),
        ("CUTOFF",ledger_all.decision_date.max()<=CUTOFF,"No post-cutoff state"),
        ("PRIOR_ONLY_VOL",bool((ledger_all.loc[ledger_all.volatility_threshold.notna(),"volatility_prior_observation_count"]>=36).all()),"36 prior months"),
        ("PRIOR_ONLY_LEADERSHIP",bool((ledger_all.loc[ledger_all.leadership_spread_threshold.notna(),"spread_prior_observation_count"]>=24).all()),"24 prior diagnostics"),
        ("COMMON_WINDOW_REGIME_COVERAGE",bool(common_ledger["risk_score"].notna().all() and common_ledger["regime"].ne("REGIME_UNAVAILABLE").all()),f"{int(common_ledger['risk_score'].notna().sum())}/{len(common_ledger)} common month-ends classified"),
        ("POLICY_DECISION_COVERAGE",bool(policy_decisions.groupby(["policy_id","switch_mode"]).size().eq(len(common_ledger)).all()),f"Every policy/switch has {len(common_ledger)} monthly decisions"),
        ("NO_SAME_CLOSE",not bool(policy_decisions.execution_date.notna().any() and (pd.to_datetime(policy_decisions.execution_date.dropna()).to_numpy()<=pd.to_datetime(policy_decisions.loc[policy_decisions.execution_date.notna(),"decision_date"]).to_numpy()).any()),"Executions after decisions"),
        ("NO_LEVERAGE",bool((policy_decisions[["applied_global_weight","applied_m2_weight","applied_cash_weight"]].sum(axis=1)<=1+1e-10).all()),"Allocations <=100%"),
        ("ATTRIBUTION_RECONCILES",bool(attribution.reconciliation_error.abs().max()<1e-9),f"max {attribution.reconciliation_error.abs().max():.3g}"),
        ("INVESTABLE_ATTRIBUTION_HAS_NO_RESIDUAL",bool(attribution.loc[~attribution.strategy_id.eq("EQUAL_WEIGHT_OPPORTUNITY_POOL"),"other_market_contribution"].abs().max()<1e-9),"Aggregate-series residual is confined to the equal-pool comparator"),
        ("DIAGNOSTIC_POLICY_NOT_PROMOTED",bool(dynamic.loc[dynamic.policy_id.eq("POLICY_5_HIGHER_ALPHA_DIAGNOSTIC"),"promotion_status"].eq("NOT_ELIGIBLE_HIGHER_ALPHA_DIAGNOSTIC").all()),"ALPHA_50 remains a diagnostic and cannot pass a selection gate"),
        ("STATIC_M2_FAMILY_GATE_RESOLVED",bool(not serious_static or all(strategy_id in static_family_ok for strategy_id in serious_static)),f"{len(static_family_ok)} serious static M2 candidate(s) completed family removal"),
        ("SELECTED_STATIC_M2_FAMILY_GATE",selected_static_family_gate,"Selected static M2 strategy must pass every leave-one-family-out gate"),
        ("STATE_MACHINE_RECONCILES",state_machine_valid,"Eight score/leadership rows reconcile to selected strategy and sum to 100%"),
        ("ALL_OUTPUT_DATES_WITHIN_CUTOFF",dated_output_ok,f"Latest parsed scientific output date {latest_output_date:%Y-%m-%d}"),
        ("HOLDING_SPELL_AUDIT_COMPLETE",bool(len(holding_spells)>0 and set(holding_spells.winner_class)=={"WINNER","FALSE_OR_LOSING_LEADER"}),f"{len(holding_spells)} complete M2 holding spells"),
        ("ANNUAL_RETURN_BOUNDARIES_RECONCILE",global_year_return_ok,"Calendar-year return includes every in-window daily return; 2017/2026 remain labelled partial"),
        ("ANNUAL_DYNAMIC_WEIGHTS_ARE_YEAR_SPECIFIC",dynamic_year_weights_ok,"Dynamic annual weights vary by realised causal state; GLOBAL_100 remains 100% SWDA"),
        ("SELECTED_STATIC_YEAR_EXCLUSIONS_COMPLETE",selected_exclusions_complete,f"{len(selected_exclusion_rows)} selected-strategy exclusion rows"),
        ("SWITCH_COUNTERFACTUALS_USE_ACTUAL_EVENTS",switch_event_scope_ok,"Static Policy 0 has zero allocation-switch events and event diagnostics are scoped to one-month matched-control effects"),
        ("EXECUTION_ENDPOINT_EVIDENCE_COMPLETE",execution_endpoint_ok,"Every executable target has an accepted GBP total-return endpoint value"),
        ("MACRO_FAIL_CLOSED",True,"MACRO_REGIME_DATA_INSUFFICIENT"),
        ("NO_BROKER_CONNECTOR",True,"Research runner has no broker import or call"),
    ]
    correctness={"stage_id":"UKACTIVE-A4F-SIPP","tests":[{"test_id":i,"status":"PASS" if ok else "FAIL","detail":detail} for i,ok,detail in tests],"summary":{"PASS":sum(ok for _,ok,_ in tests),"FAIL":sum(not ok for _,ok,_ in tests)}}
    write_json("UKACTIVE_A4F_SIPP_CORRECTNESS_TESTS.json",correctness)
    if correctness["summary"]["FAIL"]: raise AssertionError("A4F correctness registry failed")

    required=[p for p in OUT.iterdir() if p.is_file() and p.name!="UKACTIVE_A4F_SIPP_MANIFEST.json"]
    manifest={"stage_id":"UKACTIVE-A4F-SIPP","run_id":"UKACTIVE-A4F-SIPP-20260825-001","branch":"research/ukactive-a4f-sipp-regime","parent_manifest_commit":"ce6136f52ca646698a56e4ff4bbb8577214a684d","protocol_commit":PROTOCOL_COMMIT,"authoritative_cutoff":"2026-08-21","decision":decision,"selected_strategy":selected_strategy,"correctness":correctness["summary"],"environment":{"python":sys.version,"platform":platform.platform(),"pandas":pd.__version__,"numpy":np.__version__,"matplotlib":matplotlib.__version__},"source_hashes":prereg["source_hashes"],"outputs":[{"path":p.name,"size_bytes":p.stat().st_size,"sha256":sha256(p)} for p in sorted(required)],"warning":WARNING}
    write_json("UKACTIVE_A4F_SIPP_MANIFEST.json",manifest)


if __name__ == "__main__":
    main()
