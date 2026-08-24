"""Build the preregistered UKACTIVE-A4E-SIPP research stage."""

from __future__ import annotations

import hashlib
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import ukactive_a4e_sipp_core as core


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "UKACTIVE-A4E-SIPP"
WARNING = core.WARNING
PREREG_COMMIT = "d49ee47"
RETRIEVAL_DATE = "2026-08-24"
II_CHARGES_URL = "https://www.ii.co.uk/our-charges"
II_CASH_URL = "https://www.ii.co.uk/investing-with-ii/cash-interest-rates"
ISHARES_SWDA_URL = "https://www.ishares.com/uk/individual/en/products/251882/ishares-core-msci-world-ucits-etf"
LSE_SWDA_URL = "https://www.londonstockexchange.com/stock/SWDA/company/company-page"


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


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT.parents[3], text=True).strip()


def metric_row(frame: pd.DataFrame, window: str) -> pd.Series:
    return frame.loc[frame["window_id"].eq(window)].iloc[0]


def defensive_episode_count(records: pd.DataFrame) -> int:
    defensive = records.sort_values("review_date")["target_cash_weight"].gt(1e-12)
    return int((defensive & ~defensive.shift(1).fillna(False).astype(bool)).sum())


def annualised_excess_arithmetic(selected: core.a4b.A4BSimulation, comparator: core.a4b.A4BSimulation, start: pd.Timestamp, end: pd.Timestamp) -> float:
    left = selected.curve.set_index("date")["net_return"].loc[start:end]
    right = comparator.curve.set_index("date")["net_return"].loc[start:end]
    joined = pd.concat([left.rename("left"), right.rename("right")], axis=1, join="inner").dropna()
    return float((joined["left"] - joined["right"]).mean() * 252.0)


def excluded_comparison(selected: core.StrategyResult, comparator: core.a4b.A4BSimulation, years: set[int]) -> dict[str, float]:
    sm = core.excluded_year_metrics(selected.simulation, years)
    cm = core.excluded_year_metrics(comparator, years)
    return {"selected_cagr": sm["net_cagr"], "comparator_cagr": cm["net_cagr"], "excess": sm["net_cagr"] - cm["net_cagr"], "selected_mdd": sm["maximum_drawdown"], "comparator_mdd": cm["maximum_drawdown"]}


def same_exposure_control(
    data: core.a4d.A4DData,
    base_targets: dict[pd.Timestamp, dict[str, float]],
    scale: float,
    strategy_id: str,
    cost_scenario: str = "BASE",
) -> core.StrategyResult:
    targets = core.scale_target_map(base_targets, scale)
    records = pd.DataFrame([{"review_date": date, "target_weights_json": json.dumps(target, sort_keys=True), "target_risky_weight": sum(target.values()), "target_cash_weight": 1.0 - sum(target.values()), "warning": WARNING} for date, target in sorted(targets.items())])
    return core.simulate_targets(data, strategy_id, targets, records, cost_scenario=cost_scenario, force_every_review=True)


def build_implementation_map() -> pd.DataFrame:
    current = pd.read_csv(ROOT / "UKACTIVE_A5_IMPLEMENTATION_MAP.csv", dtype=str).fillna("")
    shares = pd.read_csv(ROOT / "UKACTIVE_A0A1_SHARE_CLASS_MASTER.csv", dtype=str).fillna("")
    snapshot = pd.read_csv(ROOT / "UKACTIVE_A3R2U_CURRENT_UNIVERSE_SNAPSHOT.csv", dtype=str).fillna("")
    share_fields = shares[["isin", "share_class_name", "ter_ocf_percent", "benchmark_index", "replication_method", "product_structure", "ucits_status", "accumulating_distributing", "share_class_inception_date", "fund_base_currency", "share_class_currency", "hedged_unhedged"]].drop_duplicates("isin")
    result = current.merge(share_fields, left_on="preferred_isin", right_on="isin", how="left", suffixes=("", "_master"))
    source = snapshot[["economic_exposure_family_id", "public_evidence_URLs", "public_evidence_date", "LSE_current_status"]].drop_duplicates("economic_exposure_family_id")
    result = result.merge(source, on="economic_exposure_family_id", how="left")
    rows = []
    for row in result.itertuples(index=False):
        family = row.economic_exposure_family_id
        swda = family == "GLOBAL_DEVELOPED_WORLD"
        ter_text = getattr(row, "ter_ocf_percent", "")
        try:
            ter = float(ter_text) / 100.0
        except (TypeError, ValueError):
            ter = np.nan
        urls = str(getattr(row, "public_evidence_URLs", "") or "")
        if swda:
            urls = ";".join([ISHARES_SWDA_URL, LSE_SWDA_URL])
        rows.append(
            {
                "economic_exposure_family_id": family,
                "fund_name": getattr(row, "share_class_name", "") or row.display_name,
                "ticker": row.preferred_ticker,
                "isin": row.preferred_isin,
                "exchange": row.exchange,
                "domicile": "IRELAND" if swda else "NOT_EVIDENCED_IN_CURRENT_CANONICAL_ARTIFACT",
                "ucits_status": "YES" if swda else (getattr(row, "ucits_status_master", "") or getattr(row, "ucits_status", "") or "NOT_DETERMINED"),
                "priips_kid_status": "CURRENT_PUBLIC_DOCUMENTATION_CONFIRMED" if row.current_public_uk_eligibility_status == "PUBLIC_UK_ELIGIBLE_CONFIRMED" or swda else "TO_CHECK",
                "uk_retail_status": row.current_public_uk_eligibility_status,
                "sipp_availability": "YES_OFFICIAL_ISHARES" if swda else "TO_CHECK_SIPP_SPECIFIC_ACCOUNT",
                "broker_availability": row.ii_current_tradable,
                "distribution_policy": getattr(row, "accumulating_distributing_master", "") or getattr(row, "accumulating_distributing", "") or "NOT_DETERMINED",
                "ter": ter,
                "tracking_difference": np.nan,
                "aum": "USD 146.234bn FUND / USD 142.006bn SHARE CLASS AS OF 2026-07-03" if swda else "NOT_EVIDENCED_IN_CURRENT_CANONICAL_ARTIFACT",
                "launch_date": "2009-09-25" if swda else (getattr(row, "share_class_inception_date", "") or "NOT_DETERMINED"),
                "replication_method": "OPTIMISED_PHYSICAL" if swda else (getattr(row, "replication_method", "") or "NOT_VERIFIED"),
                "base_currency": "USD" if swda else (getattr(row, "fund_base_currency", "") or "NOT_DETERMINED"),
                "trading_currency": row.listing_currency,
                "currency_hedging_status": getattr(row, "hedged_unhedged", "") or "NOT_DETERMINED",
                "underlying_index": "MSCI WORLD INDEX (NET)" if swda else (getattr(row, "benchmark_index", "") or "NOT_VERIFIED"),
                "indicative_spread": "CURRENT_SPREAD_NOT_ARCHIVED" if not swda else "NOT_USED; 2024 LSE TWS REFERENCE 3.23 BPS IS NOT CURRENT",
                "traded_value": "LSE ON-BOOK TURNOVER GBP 794,285.36 ON 2026-08-21" if swda else "NOT_EVIDENCED_IN_CURRENT_CANONICAL_ARTIFACT",
                "closure_risk": "LOWER_CURRENT_OPERATIONAL_RISK_NOT_GUARANTEED" if row.ii_current_tradable == "CONFIRMED_BY_USER" else "ELEVATED_UNVERIFIED",
                "substitute_instrument": f"{row.alternate_ticker}|{row.alternate_isin}" if row.alternate_ticker else "NONE_PREDECLARED",
                "no_investment_rule": "IF PREFERRED AND PREDECLARED ALTERNATE ARE UNAVAILABLE, ALLOCATE SLOT TO GBP CASH; NO DISCRETIONARY SUBSTITUTE",
                "source_url": urls,
                "retrieval_date": RETRIEVAL_DATE,
                "evidence_notes": "Current-only evidence; never back-project ii/SIPP availability. SIPP-specific availability remains separate from user account tradability." if not swda else "Official iShares page reports UCITS, ISA eligibility, SIPP availability, Ireland domicile, 0.20% TER, accumulating, physical optimised structure.",
            }
        )
    rows.append(
        {
            "economic_exposure_family_id": "LIVE_GBP_CASH",
            "fund_name": "Interactive Investor SIPP GBP broker cash",
            "ticker": "BROKER_CASH",
            "isin": "NOT_APPLICABLE",
            "exchange": "NOT_APPLICABLE",
            "domicile": "UNITED_KINGDOM_ACCOUNT_CASH",
            "ucits_status": "NOT_APPLICABLE",
            "priips_kid_status": "NOT_APPLICABLE",
            "uk_retail_status": "II_SIPP_ACCOUNT_CASH",
            "sipp_availability": "YES_OFFICIAL_II",
            "broker_availability": "AVAILABLE_AS_ACCOUNT_CASH",
            "distribution_policy": "MONTHLY_INTEREST",
            "ter": 0.0,
            "tracking_difference": np.nan,
            "aum": "NOT_APPLICABLE",
            "launch_date": "NOT_APPLICABLE",
            "replication_method": "BROKER_CASH_BALANCE",
            "base_currency": "GBP",
            "trading_currency": "GBP",
            "currency_hedging_status": "NOT_APPLICABLE",
            "underlying_index": "NOT_APPLICABLE",
            "indicative_spread": "NONE",
            "traded_value": "NOT_APPLICABLE",
            "closure_risk": "BROKER_CREDIT_AND_RATE_CHANGE RISK; NOT AN ETF",
            "substitute_instrument": "NONE FROZEN; CASH ETF/MMF REQUIRES SEPARATE OPERATIONAL DECISION",
            "no_investment_rule": "USE BROKER GBP CASH FOR LIVE DESIGN; DO NOT SUBSTITUTE CSH2 OR GILT ETF WITHOUT NEW VERSION",
            "source_url": II_CASH_URL,
            "retrieval_date": RETRIEVAL_DATE,
            "evidence_notes": "Official ii rates effective 2026-01-06 are tiered; historical backtest continues to use accepted GBP cash series, not current broker rates.",
        }
    )
    return pd.DataFrame(rows)


def live_cost_rows(strategies: list[dict[str, Any]], instrument_map: pd.DataFrame) -> pd.DataFrame:
    active_ters = pd.to_numeric(instrument_map.loc[instrument_map["economic_exposure_family_id"].isin(pd.read_csv(ROOT / "UKACTIVE_CURRENT_II_IMPLEMENTATION_VERIFIED_20260823.csv")["economic_exposure_family_id"]), "ter"], errors="coerce").dropna()
    active_ter_proxy = float(active_ters.median()) if len(active_ters) else 0.005
    rows = []
    for strategy in strategies:
        for size in [100000, 250000, 500000, 750000, 1000000]:
            platform_fee = 5.99 * 12 if size <= 100000 else 14.99 * 12
            turnover = float(strategy["turnover"])
            legs = float(strategy["trade_legs_per_year"])
            rotation_weight = float(strategy.get("rotation_weight", 0.0))
            core_weight = float(strategy.get("core_weight", 0.0))
            commission = legs * 3.99
            spread = turnover * size * 0.002
            fx = 0.0
            ter = size * (rotation_weight * active_ter_proxy + core_weight * 0.002)
            tracking = 0.0
            cash_cost = 0.0
            total = platform_fee + commission + spread + fx + ter + tracking + cash_cost
            canonical = commission + spread
            doubled = legs * 7.98 + turnover * size * 0.004
            rows.append(
                {
                    "strategy_id": strategy["strategy_id"],
                    "sipp_size_gbp": size,
                    "commission_estimate": commission,
                    "spread_estimate": spread,
                    "fx_estimate": fx,
                    "ter_estimate": ter,
                    "tracking_difference_estimate": tracking,
                    "platform_fee_estimate": platform_fee,
                    "cash_cost_estimate": cash_cost,
                    "turnover": turnover,
                    "total_estimated_annual_cost": total,
                    "cost_as_percentage": total / size,
                    "canonical_cost_comparison": canonical,
                    "double_cost_comparison": doubled,
                    "source_url": II_CHARGES_URL,
                    "retrieval_date": RETRIEVAL_DATE,
                    "assumption_notes": f"Conservative ad-hoc £3.99 per UK ETF leg; published free monthly trade ignored. Preferred GBP lines imply zero FX. Active TER uses median {active_ter_proxy:.2%} of documented current-map TER values; missing product TER/tracking difference remains an open implementation item.",
                }
            )
    return pd.DataFrame(rows)


def retirement_rows(strategy_results: dict[str, core.StrategyResult], seed: int = 20260826) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for strategy_id, result in strategy_results.items():
        value = result.simulation.curve.set_index("date")["portfolio_value"].astype(float)
        monthly_value = value.groupby([value.index.year, value.index.month]).last()
        returns = monthly_value.pct_change(fill_method=None).dropna().to_numpy(float)
        if len(returns) < 36:
            continue
        max_recovery = core.metric_pack(result.simulation, pd.Timestamp(result.simulation.curve["date"].min()), pd.Timestamp(result.simulation.curve["date"].max())).get("maximum_time_underwater_calendar_days", np.nan)
        for withdrawal in [0.0, 0.03, 0.04]:
            terminal3 = []
            terminal5 = []
            for horizon, store in [(36, terminal3), (60, terminal5)]:
                for start in range(0, len(returns) - horizon + 1):
                    balance = 100000.0
                    for ret in returns[start:start + horizon]:
                        balance = balance * (1.0 + ret) - 100000.0 * withdrawal / 12.0
                    store.append(balance)
            blocks = []
            block = 6
            for _ in range(5000):
                path = []
                while len(path) < 36:
                    start = int(rng.integers(0, max(1, len(returns) - block + 1)))
                    path.extend(returns[start:start + block])
                balance = 1.0
                for ret in path[:36]:
                    balance = balance * (1.0 + ret) - withdrawal / 12.0
                blocks.append(balance)
            rows.append(
                {
                    "strategy_id": strategy_id,
                    "withdrawal_rate": withdrawal,
                    "stress_method": "ROLLING_HISTORICAL_AND_6M_MONTHLY_BLOCK_RESAMPLING_5000",
                    "worst_3y_terminal_wealth": min(terminal3) if terminal3 else np.nan,
                    "worst_5y_terminal_wealth": min(terminal5) if terminal5 else np.nan,
                    "negative_real_3y_probability": np.nan,
                    "negative_nominal_3y_probability": float(np.mean(np.asarray(blocks) < 1.0)),
                    "maximum_recovery_days": max_recovery,
                    "drawdown_start_withdrawal_effect": (min(terminal3) - 100000.0) if terminal3 else np.nan,
                    "inflation_status": "NO_ACCEPTED_POINT_IN_TIME_UK_INFLATION_SERIES_IN_PROGRAMME; NOMINAL DIAGNOSTIC ONLY",
                    "evidence_level": "E1_RISK_DIAGNOSTIC",
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = core.load_data()
    prereg = core.read_preregistration()
    cutoff = pd.Timestamp(prereg["authoritative_cutoff"])
    if pd.Timestamp(data.base.research.calendar.max()) != cutoff:
        raise AssertionError("Authoritative cutoff mismatch")
    global_sim = core.a4d.index_benchmark(data, "GLOBAL_DEVELOPED_WORLD", "GLOBAL_DEVELOPED_WORLD")
    pool_sim = core.a4d.pool_benchmark(data, "MONTHLY")
    cash_sim = core.a4d.cash_benchmark(data)

    # Phase 0: deterministic A4D reproduction.
    rotation_cache: dict[tuple[str, int, bool, str], core.StrategyResult] = {}
    eval_cache: dict[tuple[str, int, bool, str], pd.DataFrame] = {}
    for breadth in range(6, 10):
        for cash1 in [False, True]:
            for cost in ["BASE", "DOUBLE"]:
                key = ("M2_BASE", breadth, cash1, cost)
                result = core.simulate_rotation(data, "M2_BASE", breadth, cash1, cost_scenario=cost)
                rotation_cache[key] = result
                eval_cache[key] = core.evaluation_rows(data, result, global_sim, pool_sim)

    prior_base = pd.read_csv(ROOT / "UKACTIVE_A4D_CASH_DEFENCE_RESULTS.csv")
    prior_double = pd.read_csv(ROOT / "UKACTIVE_A4D_CASH_DOUBLE_COST_RESULTS.csv")
    metric_map = {
        "net_cagr": "net_cagr",
        "maximum_drawdown": "maximum_drawdown",
        "ulcer_index": "ulcer_index",
        "calmar_mar": "calmar_mar",
        "annual_turnover_traded_notional": "annual_turnover_traded_notional",
        "net_excess_vs_equal_pool": "excess_vs_pool",
        "net_excess_vs_global": "excess_vs_global",
        "average_cash_weight": "average_cash_weight",
        "worst_rolling_six_months": "worst_rolling_six_months",
    }
    reconciliation_rows = []
    for breadth in range(6, 10):
        for cash1 in [False, True]:
            cash_name = "CASH_1_INDIVIDUAL_ABOVE_CASH_252" if cash1 else "CASH_0_ALWAYS_INVESTED"
            for cost, prior in [("BASE", prior_base), ("DOUBLE", prior_double)]:
                current = eval_cache[("M2_BASE", breadth, cash1, cost)]
                old = prior.loc[(prior["signal_id"].eq("M2_INTERMEDIATE_5H")) & (prior["breadth"].eq(breadth)) & (prior["frequency"].eq("MONTHLY")) & (prior["cash_architecture"].eq(cash_name))]
                for window in ["FULL_HISTORY", "PRE_2020", "POST_2020", "LATEST_5Y", "LATEST_3Y"]:
                    old_row = old.loc[old["window_id"].eq(window)].iloc[0]
                    new_row = current.loc[current["window_id"].eq(window)].iloc[0]
                    for old_metric, new_metric in metric_map.items():
                        a4d_value = float(old_row[old_metric])
                        reproduced = float(new_row[new_metric])
                        diff = reproduced - a4d_value
                        reconciliation_rows.append({"metric_id": old_metric, "specification_id": f"M2_BASE|TOP{breadth}|{cash_name}|{cost}", "window_id": window, "a4d_value": a4d_value, "a4e_reproduced_value": reproduced, "difference": diff, "tolerance": 1e-10, "status": "PASS" if abs(diff) <= 1e-10 else "FAIL", "explanation": "Independent rerun through immutable A4D primitives"})
    reconciliation = pd.DataFrame(reconciliation_rows)
    write_csv("UKACTIVE_A4E_SIPP_METRIC_RECONCILIATION.csv", reconciliation)
    audit_pass = bool(reconciliation["status"].eq("PASS").all())
    if not audit_pass:
        write_text("UKACTIVE_A4E_SIPP_REPRODUCTION_AUDIT.md", "# A4E-SIPP reproduction audit\n\nDecision: `A4E_SIPP_AUDIT_FAIL`\n")
        raise AssertionError("A4D reproduction failed")

    representative_cash0 = rotation_cache[("M2_BASE", 7, False, "BASE")]
    representative_cash1 = rotation_cache[("M2_BASE", 7, True, "BASE")]
    full_start, full_end = core.primary_windows(data)["FULL_HISTORY"]
    arith_pool = annualised_excess_arithmetic(representative_cash0.simulation, pool_sim, full_start, full_end)
    cagr_pool = float(metric_row(eval_cache[("M2_BASE", 7, False, "BASE")], "FULL_HISTORY")["excess_vs_pool"])
    bootstrap = pd.read_csv(ROOT / "UKACTIVE_A4D_REPRESENTATIVE_BLOCK_BOOTSTRAP.csv")
    bootstrap_pool = float(
        bootstrap.loc[
            bootstrap["comparator_id"].eq("EQUAL_WEIGHT_OPPORTUNITY_POOL"),
            "observed_annualised_excess",
        ].iloc[0]
    )
    write_text(
        "UKACTIVE_A4E_SIPP_REPRODUCTION_AUDIT.md",
        f"""# UKACTIVE-A4E-SIPP reproduction audit

Decision: `PASS`

- Deterministic cells reconciled: {len(reconciliation):,}/{len(reconciliation):,} within 1e-10.
- Common causal boundary: 2017-02-03; first executable monthly portfolio row: {representative_cash0.simulation.curve['date'].min():%Y-%m-%d}.
- Headline CAGR-difference full-history excess vs pool: {cagr_pool:.6%}.
- Arithmetic annualised daily-return excess vs pool: {arith_pool:.6%}.
- A4D monthly block-bootstrap observed excess vs pool: {bootstrap_pool:.6%}.

These are different estimands and are not expected to be numerically identical. Turnover is window-specific because the numerator includes only trades executed inside each window and the denominator is that window’s calendar duration. Accepted GBP cash accrues from `UKACTIVE_A2_CASH_SERIES.parquet`; distributions and FX are already embedded once in the A2R2 GBP total-return endpoints. No later data, proxy, closure bridge or forward-filled return was introduced. Partial 2017 and partial 2026 remain explicitly partial.
""",
    )

    # Phase 1: bounded signal stability.
    signal_rows = []
    signal_results: dict[tuple[str, int, str], core.StrategyResult] = {}
    for signal in core.SIGNAL_WEIGHTS:
        for breadth in range(6, 10):
            for cost in ["BASE", "DOUBLE"]:
                result = core.simulate_rotation(data, signal, breadth, False, cost_scenario=cost)
                signal_results[(signal, breadth, cost)] = result
                evaluated = core.evaluation_rows(data, result, global_sim, pool_sim)
                for row in evaluated.itertuples(index=False):
                    signal_rows.append({"signal_id": signal, "breadth": breadth, "cost_scenario": cost, "window_id": row.window_id, "net_cagr": row.net_cagr, "excess_vs_global": row.excess_vs_global, "excess_vs_pool": row.excess_vs_pool, "maximum_drawdown": row.maximum_drawdown, "calmar": row.calmar_mar, "ulcer_index": row.ulcer_index, "turnover": row.annual_turnover_traded_notional, "stability_status": "CONTROL_ONLY_M2_BASE_REMAINS_ONLY_FINAL_ELIGIBLE" if signal != "M2_BASE" else "FINAL_ELIGIBLE_SIGNAL", "warning": WARNING})
    signal_stability = pd.DataFrame(signal_rows)
    write_csv("UKACTIVE_A4E_SIPP_SIGNAL_STABILITY.csv", signal_stability)

    # Phase 2: exact CASH1 confirmation and advancement gate.
    cash_rows = []
    cash_region_checks = []
    for breadth in range(6, 10):
        base0 = eval_cache[("M2_BASE", breadth, False, "BASE")]
        base1 = eval_cache[("M2_BASE", breadth, True, "BASE")]
        double1 = eval_cache[("M2_BASE", breadth, True, "DOUBLE")]
        episodes = defensive_episode_count(rotation_cache[("M2_BASE", breadth, True, "BASE")].records)
        for window in ["FULL_HISTORY", "PRE_2020", "POST_2020", "LATEST_5Y", "LATEST_3Y"]:
            c0 = metric_row(base0, window)
            c1 = metric_row(base1, window)
            d1 = metric_row(double1, window)
            row = {
                "breadth": breadth,
                "window_id": window,
                "cost_scenario": "BASE_WITH_DOUBLE_COST_DIAGNOSTIC",
                "cash0_cagr": c0.net_cagr,
                "cash1_cagr": c1.net_cagr,
                "cagr_retention": c1.net_cagr / c0.net_cagr if c0.net_cagr != 0 else np.nan,
                "cash0_mdd": c0.maximum_drawdown,
                "cash1_mdd": c1.maximum_drawdown,
                "mdd_benefit": abs(c0.maximum_drawdown) - abs(c1.maximum_drawdown),
                "cash0_ulcer": c0.ulcer_index,
                "cash1_ulcer": c1.ulcer_index,
                "ulcer_reduction": 1.0 - c1.ulcer_index / c0.ulcer_index,
                "cash0_calmar": c0.calmar_mar,
                "cash1_calmar": c1.calmar_mar,
                "calmar_improvement": c1.calmar_mar / c0.calmar_mar - 1.0,
                "pool_excess": c1.excess_vs_pool,
                "double_cost_pool_excess": d1.excess_vs_pool,
                "average_cash_weight": c1.average_cash_weight,
                "time_partial_cash": c1.percentage_time_partially_invested,
                "time_full_cash": c1.percentage_time_completely_cash,
                "defensive_episode_count": episodes,
                "worst_rolling_six_months": c1.worst_rolling_six_months,
                "cash0_worst_rolling_six_months": c0.worst_rolling_six_months,
                "advancement_status": "PENDING_REGION_GATE",
                "warning": WARNING,
            }
            cash_rows.append(row)
    cash_confirmation = pd.DataFrame(cash_rows)
    full = cash_confirmation.loc[cash_confirmation["window_id"].eq("FULL_HISTORY")]
    latest5 = cash_confirmation.loc[cash_confirmation["window_id"].eq("LATEST_5Y")]
    exclude2025_checks = []
    for breadth in range(6, 10):
        c0 = excluded_comparison(rotation_cache[("M2_BASE", breadth, False, "BASE")], pool_sim, {2025})
        c1 = excluded_comparison(rotation_cache[("M2_BASE", breadth, True, "BASE")], pool_sim, {2025})
        exclude2025_checks.append({"breadth": breadth, "cash0_mdd": c0["selected_mdd"], "cash1_mdd": c1["selected_mdd"], "mdd_benefit": abs(c0["selected_mdd"]) - abs(c1["selected_mdd"]), "cash1_pool_excess": c1["excess"]})
    exclude2025_frame = pd.DataFrame(exclude2025_checks)
    cash1_gate_checks = {
        "full_history_median_cagr_retention": float(full["cagr_retention"].median()) >= 0.95,
        "latest5_median_cagr_retention": float(latest5["cagr_retention"].median()) >= 0.95,
        "mdd_or_ulcer": float(latest5["mdd_benefit"].median()) >= 0.03 or float(latest5["ulcer_reduction"].median()) >= 0.15,
        "calmar_improvement": float(latest5["calmar_improvement"].median()) >= 0.15,
        "baseline_pool_excess": float(latest5["pool_excess"].median()) > 0,
        "double_cost_pool_excess": float(latest5["double_cost_pool_excess"].median()) >= 0,
        "exclude2025_drawdown_benefit": float(exclude2025_frame["mdd_benefit"].median()) > 0,
        "multiple_defensive_episodes": int(latest5["defensive_episode_count"].median()) >= 2,
        "worst6_not_worse": bool((latest5["worst_rolling_six_months"] >= latest5["cash0_worst_rolling_six_months"] - 1e-12).all()),
    }
    cash1_advances = all(cash1_gate_checks.values())
    cash_confirmation["advancement_status"] = "PASS" if cash1_advances else "FAIL"
    write_csv("UKACTIVE_A4E_SIPP_CASH1_CONFIRMATION.csv", cash_confirmation)

    cash_episodes = representative_cash1.records.copy()
    cash_episodes["defensive"] = cash_episodes["target_cash_weight"].gt(1e-12)
    cash_episodes["episode_id"] = (cash_episodes["defensive"] & ~cash_episodes["defensive"].shift(1).fillna(False).astype(bool)).cumsum()
    cash_episodes = cash_episodes.loc[cash_episodes["defensive"]].copy()
    write_csv("UKACTIVE_A4E_SIPP_CASH_EPISODES.csv", cash_episodes)

    # Matched-exposure controls for TOP7 CASH1.
    cash1_full_eval = metric_row(eval_cache[("M2_BASE", 7, True, "BASE")], "FULL_HISTORY")
    avg_exposure = 1.0 - float(cash1_full_eval.average_cash_weight)
    cash0_targets = representative_cash0.targets
    rotation_static = same_exposure_control(data, cash0_targets, avg_exposure, "ROTATION_STATIC_SAME_AVERAGE_EXPOSURE")
    global_targets, global_records = core.static_global_targets(data, avg_exposure)
    global_static = core.simulate_targets(data, "GLOBAL_STATIC_SAME_AVERAGE_EXPOSURE", global_targets, global_records, force_every_review=True)
    cash0_full = metric_row(eval_cache[("M2_BASE", 7, False, "BASE")], "FULL_HISTORY")
    scale_rotation_vol = min(1.0, float(cash1_full_eval.annualised_volatility) / float(cash0_full.annualised_volatility))
    rotation_vol = same_exposure_control(data, cash0_targets, scale_rotation_vol, "ROTATION_MATCHED_VOLATILITY")
    global_metrics_full = core.metric_pack(global_sim, full_start, full_end)
    scale_global_vol = min(1.0, float(cash1_full_eval.annualised_volatility) / float(global_metrics_full["annualised_volatility"]))
    global_vol_targets, global_vol_records = core.static_global_targets(data, scale_global_vol)
    global_vol = core.simulate_targets(data, "GLOBAL_MATCHED_VOLATILITY", global_vol_targets, global_vol_records, force_every_review=True)
    matched_controls: dict[str, core.StrategyResult] = {
        rotation_static.strategy_id: rotation_static,
        global_static.strategy_id: global_static,
        rotation_vol.strategy_id: rotation_vol,
        global_vol.strategy_id: global_vol,
    }
    for weight in [0.25, 0.50, 0.75, 1.0]:
        targets, records = core.static_global_targets(data, weight)
        result = core.simulate_targets(data, f"GLOBAL_CASH_{int(weight*100)}_{int((1-weight)*100)}", targets, records, force_every_review=True)
        matched_controls[result.strategy_id] = result
    matched_rows = []
    candidate_eval = core.evaluation_rows(data, representative_cash1, global_sim, pool_sim)
    for control_id, control in matched_controls.items():
        control_eval = core.evaluation_rows(data, control, global_sim, pool_sim)
        for window in ["FULL_HISTORY", "LATEST_5Y"]:
            cand = metric_row(candidate_eval, window)
            comp = metric_row(control_eval, window)
            dimension = "AVERAGE_EXPOSURE" if "SAME_AVERAGE" in control_id else ("VOLATILITY" if "MATCHED_VOLATILITY" in control_id else "DRAWDOWN_FRONTIER")
            matched_rows.append({"candidate_id": representative_cash1.strategy_id, "control_id": control_id, "matching_dimension": dimension, "window_id": window, "candidate_cagr": cand.net_cagr, "control_cagr": comp.net_cagr, "candidate_terminal_wealth": cand.terminal_wealth_per_100k, "control_terminal_wealth": comp.terminal_wealth_per_100k, "candidate_mdd": cand.maximum_drawdown, "control_mdd": comp.maximum_drawdown, "candidate_volatility": cand.annualised_volatility, "control_volatility": comp.annualised_volatility, "candidate_average_exposure": 1.0 - cand.average_cash_weight, "control_average_exposure": 1.0 - comp.average_cash_weight, "terminal_wealth_advantage": cand.terminal_wealth_per_100k / comp.terminal_wealth_per_100k - 1.0, "timing_selection_benefit": cand.terminal_wealth_per_100k > comp.terminal_wealth_per_100k, "warning": WARNING})
    matched_exposure = pd.DataFrame(matched_rows)
    write_csv("UKACTIVE_A4E_SIPP_MATCHED_EXPOSURE_CONTROLS.csv", matched_exposure)
    matched_timing_pass = bool(matched_exposure.loc[(matched_exposure["window_id"].eq("FULL_HISTORY")) & matched_exposure["control_id"].isin(["ROTATION_STATIC_SAME_AVERAGE_EXPOSURE", "ROTATION_MATCHED_VOLATILITY"]), "timing_selection_benefit"].all())

    # Phase 3 turnover controls.
    variant_results: dict[str, core.StrategyResult] = {"R0_EXACT_CASH1": representative_cash1}
    ht, hr = core.hysteresis_targets(data)
    variant_results["R1_RANK_HYSTERESIS"] = core.simulate_targets(data, "R1_RANK_HYSTERESIS", ht, hr)
    wt, wr = core.weekly_exit_targets(data)
    variant_results["R2_WEEKLY_EXIT_ONLY"] = core.simulate_targets(data, "R2_WEEKLY_EXIT_ONLY", wt, wr)
    variant_double: dict[str, core.StrategyResult] = {"R0_EXACT_CASH1": rotation_cache[("M2_BASE", 7, True, "DOUBLE")]}
    variant_double["R1_RANK_HYSTERESIS"] = core.simulate_targets(data, "R1_RANK_HYSTERESIS|DOUBLE", ht, hr, cost_scenario="DOUBLE")
    variant_double["R2_WEEKLY_EXIT_ONLY"] = core.simulate_targets(data, "R2_WEEKLY_EXIT_ONLY|DOUBLE", wt, wr, cost_scenario="DOUBLE")
    variant_rows = []
    r0_eval = core.evaluation_rows(data, representative_cash1, global_sim, pool_sim)
    r0_full = metric_row(r0_eval, "FULL_HISTORY")
    r0_excl = excluded_comparison(representative_cash1, pool_sim, {2025})
    variant_passes: dict[str, bool] = {"R0_EXACT_CASH1": cash1_advances}
    for variant, result in variant_results.items():
        evaluated = core.evaluation_rows(data, result, global_sim, pool_sim)
        doubled_eval = core.evaluation_rows(data, variant_double[variant], global_sim, pool_sim)
        full_row = metric_row(evaluated, "FULL_HISTORY")
        double_full = metric_row(doubled_eval, "FULL_HISTORY")
        excl = excluded_comparison(result, pool_sim, {2025})
        materially_improves = full_row.annual_turnover_traded_notional <= r0_full.annual_turnover_traded_notional * 0.90 or abs(r0_full.maximum_drawdown) - abs(full_row.maximum_drawdown) >= 0.03
        passes = variant == "R0_EXACT_CASH1" and cash1_advances
        if variant != "R0_EXACT_CASH1":
            passes = bool(materially_improves and full_row.net_cagr / r0_full.net_cagr >= 0.95 and double_full.excess_vs_pool >= metric_row(core.evaluation_rows(data, variant_double["R0_EXACT_CASH1"], global_sim, pool_sim), "FULL_HISTORY").excess_vs_pool - 1e-12 and excl["excess"] >= 0 and cash1_advances)
        variant_passes[variant] = passes
        for row in evaluated.itertuples(index=False):
            drow = metric_row(doubled_eval, row.window_id)
            variant_rows.append({"variant_id": variant, "breadth": 7, "window_id": row.window_id, "cost_scenario": "BASE_WITH_DOUBLE_COST_DIAGNOSTIC", "net_cagr": row.net_cagr, "cagr_retention_vs_r0": row.net_cagr / metric_row(r0_eval, row.window_id).net_cagr if metric_row(r0_eval, row.window_id).net_cagr != 0 else np.nan, "maximum_drawdown": row.maximum_drawdown, "mdd_benefit_vs_r0": abs(metric_row(r0_eval, row.window_id).maximum_drawdown) - abs(row.maximum_drawdown), "ulcer_index": row.ulcer_index, "calmar": row.calmar_mar, "turnover": row.annual_turnover_traded_notional, "double_cost_pool_excess": drow.excess_vs_pool, "exclude_2025_status": "PASS" if excl["excess"] >= 0 else "FAIL", "breadth_consistency": "PASS" if cash1_advances else "FAIL_UNDERLYING_CASH1_REGION", "advancement_status": "PASS" if passes else "FAIL", "warning": WARNING})
    variant_table = pd.DataFrame(variant_rows)
    write_csv("UKACTIVE_A4E_SIPP_HYSTERESIS_AND_WEEKLY_EXIT.csv", variant_table)
    passing_variants = [name for name, passed in variant_passes.items() if passed]
    selected_variant = "R0_EXACT_CASH1"
    if passing_variants:
        scores = []
        for name in passing_variants:
            row = metric_row(core.evaluation_rows(data, variant_results[name], global_sim, pool_sim), "FULL_HISTORY")
            scores.append((name, row.calmar_mar, -row.annual_turnover_traded_notional, 0 if name == "R1_RANK_HYSTERESIS" else -1))
        selected_variant = sorted(scores, key=lambda item: item[1:], reverse=True)[0][0]
    selected_rotation = variant_results[selected_variant]

    # Phase 5 core selection and controlled blend frontier.
    core_results: dict[str, core.StrategyResult] = {}
    core_rows = []
    for core_id in ["CORE_0_GLOBAL", "CORE_1_GLOBAL_ABSOLUTE_MOMENTUM"]:
        targets, records = core.core_targets(data, core_id)
        result = core.simulate_targets(data, core_id, targets, records)
        core_results[core_id] = result
        evaluated = core.evaluation_rows(data, result, global_sim, pool_sim)
        for row in evaluated.itertuples(index=False):
            core_rows.append({"core_id": core_id, "window_id": row.window_id, "cost_scenario": "BASE", "net_cagr": row.net_cagr, "terminal_wealth_per_100k": row.terminal_wealth_per_100k, "maximum_drawdown": row.maximum_drawdown, "ulcer_index": row.ulcer_index, "calmar": row.calmar_mar, "annualised_volatility": row.annualised_volatility, "average_equity_exposure": 1.0 - row.average_cash_weight, "average_cash_exposure": row.average_cash_weight, "core_selection_status": "PENDING", "warning": WARNING})
    core_table = pd.DataFrame(core_rows)
    core0 = core_table.loc[(core_table["core_id"].eq("CORE_0_GLOBAL")) & core_table["window_id"].eq("FULL_HISTORY")].iloc[0]
    core1 = core_table.loc[(core_table["core_id"].eq("CORE_1_GLOBAL_ABSOLUTE_MOMENTUM")) & core_table["window_id"].eq("FULL_HISTORY")].iloc[0]
    core1_pass = bool(core1.net_cagr / core0.net_cagr >= 0.90 and (abs(core0.maximum_drawdown) - abs(core1.maximum_drawdown) >= 0.05 or 1.0 - core1.ulcer_index / core0.ulcer_index >= 0.20))
    selected_core_id = "CORE_1_GLOBAL_ABSOLUTE_MOMENTUM" if core1_pass else "CORE_0_GLOBAL"
    core_table["core_selection_status"] = np.where(core_table["core_id"].eq(selected_core_id), "SELECTED", "NOT_SELECTED")
    write_csv("UKACTIVE_A4E_SIPP_CORE_RESULTS.csv", core_table)
    selected_core = core_results[selected_core_id]

    blend_results: dict[str, core.StrategyResult] = {}
    blend_rows = []
    selected_core_targets = selected_core.targets
    for rotation_weight in [0.25, 0.50, 0.75, 1.0]:
        if rotation_weight == 1.0:
            result = selected_rotation
            strategy_id = f"ROTATION_{selected_variant}_100"
            result = core.StrategyResult(strategy_id, result.simulation, result.targets, result.records, {**result.metadata, "average_rotation_exposure": 1.0})
        else:
            targets, records = core.combine_target_maps(selected_rotation.targets, selected_core_targets, rotation_weight)
            strategy_id = f"ROTATION_{selected_variant}_{int(rotation_weight*100)}|CORE_{selected_core_id}_{int((1-rotation_weight)*100)}"
            result = core.simulate_targets(data, strategy_id, targets, records, force_every_review=True)
            result.metadata["average_rotation_exposure"] = rotation_weight
        blend_results[strategy_id] = result
        evaluated = core.evaluation_rows(data, result, global_sim, pool_sim)
        for row in evaluated.itertuples(index=False):
            blend_rows.append({"strategy_id": strategy_id, "rotation_weight": rotation_weight, "core_weight": 1.0 - rotation_weight, "window_id": row.window_id, "cost_scenario": "BASE", "net_cagr": row.net_cagr, "terminal_wealth_per_100k": row.terminal_wealth_per_100k, "maximum_drawdown": row.maximum_drawdown, "ulcer_index": row.ulcer_index, "calmar": row.calmar_mar, "turnover": row.annual_turnover_traded_notional, "average_rotation_exposure": rotation_weight * (1.0 - row.average_cash_weight), "average_core_exposure": (1.0 - rotation_weight) * (1.0 if selected_core_id == "CORE_0_GLOBAL" else np.nan), "average_cash_exposure": row.average_cash_weight, "return_edge": row.excess_vs_global > 0 and row.excess_vs_pool > 0, "risk_edge": False, "pareto_status": "PENDING", "warning": WARNING})
    blend_table = pd.DataFrame(blend_rows)

    # Add static global controls to whole-SIPP candidate set.
    candidate_results: dict[str, core.StrategyResult] = dict(blend_results)
    # Matched-exposure rotation portfolios are falsification controls, not
    # eligible whole-SIPP strategies.  The four preregistered static
    # global/cash allocations are both controls and mandatory fallbacks.
    candidate_results.update(
        {
            strategy_id: result
            for strategy_id, result in matched_controls.items()
            if strategy_id.startswith("GLOBAL_CASH_")
        }
    )
    candidate_results.update(core_results)
    full_candidate_rows = []
    global_full = core.metric_pack(global_sim, full_start, full_end)
    for strategy_id, result in candidate_results.items():
        evaluated = core.evaluation_rows(data, result, global_sim, pool_sim)
        full_row = metric_row(evaluated, "FULL_HISTORY")
        mdd_improvement = abs(global_full["maximum_drawdown"]) - abs(full_row.maximum_drawdown)
        ulcer_reduction = 1.0 - full_row.ulcer_index / global_full["ulcer_index"]
        risk_edge = bool((full_row.net_cagr >= global_full["net_cagr"] and (mdd_improvement >= 0.03 or ulcer_reduction >= 0.15)) or (full_row.net_cagr >= 0.90 * global_full["net_cagr"] and (mdd_improvement >= 0.05 or ulcer_reduction >= 0.20)))
        full_candidate_rows.append({"strategy_id": strategy_id, "net_cagr": full_row.net_cagr, "terminal_wealth_per_100k": full_row.terminal_wealth_per_100k, "maximum_drawdown": full_row.maximum_drawdown, "ulcer_index": full_row.ulcer_index, "longest_underwater_days": full_row.maximum_time_underwater_calendar_days, "turnover": full_row.annual_turnover_traded_notional, "calmar": full_row.calmar_mar, "average_exposure": 1.0 - full_row.average_cash_weight, "return_edge": full_row.excess_vs_global > 0, "risk_edge": risk_edge, "source_type": "UNSCALED"})
    unscaled_frontier = pd.DataFrame(full_candidate_rows)

    # Pareto roles before volatility scaling.
    return_id = unscaled_frontier.sort_values(["net_cagr", "maximum_drawdown"], ascending=[False, False]).iloc[0]["strategy_id"]
    eligible_drawdown = unscaled_frontier.loc[unscaled_frontier["net_cagr"].ge(0.90 * global_full["net_cagr"])]
    drawdown_id = (eligible_drawdown if len(eligible_drawdown) else unscaled_frontier).sort_values(["maximum_drawdown", "net_cagr"], ascending=[False, False]).iloc[0]["strategy_id"]
    unscaled_frontier["preferred_target_count"] = (
        unscaled_frontier["maximum_drawdown"].ge(-0.15).astype(int)
        + unscaled_frontier["ulcer_index"].le(0.08).astype(int)
        + unscaled_frontier["calmar"].ge(0.75).astype(int)
        + unscaled_frontier["longest_underwater_days"].le(36 * 30.4375).astype(int)
        + unscaled_frontier["net_cagr"].ge(0.90 * global_full["net_cagr"]).astype(int)
    )
    unscaled_frontier["acceptable_region"] = unscaled_frontier["maximum_drawdown"].ge(-0.20) & unscaled_frontier["net_cagr"].ge(global_full["net_cagr"] - 0.01)
    balance_pool = unscaled_frontier.loc[unscaled_frontier["acceptable_region"]]
    if balance_pool.empty:
        balance_pool = unscaled_frontier
    balanced_id = balance_pool.sort_values(["preferred_target_count", "net_cagr", "ulcer_index", "turnover"], ascending=[False, False, True, True]).iloc[0]["strategy_id"]
    pareto_seed_ids = list(dict.fromkeys([str(return_id), str(drawdown_id), str(balanced_id)]))[:3]

    # Phase 4: fixed volatility controls on no more than the three seed candidates.
    vol_results: dict[str, core.StrategyResult] = {}
    vol_rows = []
    for base_id in pareto_seed_ids:
        base_result = candidate_results[base_id]
        for target_vol in [0.10, 0.125, 0.15]:
            targets, records = core.volatility_scaled_targets(base_result, target_vol)
            strategy_id = f"{base_id}|VOL{target_vol:.3f}"
            result = core.simulate_targets(data, strategy_id, targets, records, force_every_review=True)
            vol_results[strategy_id] = result
            evaluated = core.evaluation_rows(data, result, global_sim, pool_sim)
            full_row = metric_row(evaluated, "FULL_HISTORY")
            average_exposure = 1.0 - full_row.average_cash_weight
            static_targets = core.scale_target_map(base_result.targets, average_exposure)
            static_records = pd.DataFrame([{"review_date": date, "target_weights_json": json.dumps(target, sort_keys=True), "target_risky_weight": sum(target.values()), "target_cash_weight": 1.0 - sum(target.values())} for date, target in static_targets.items()])
            static_result = core.simulate_targets(data, f"{base_id}|STATIC_EXPOSURE_{average_exposure:.4f}", static_targets, static_records, force_every_review=True)
            static_full = metric_row(core.evaluation_rows(data, static_result, global_sim, pool_sim), "FULL_HISTORY")
            for row in evaluated.itertuples(index=False):
                vol_rows.append({"base_strategy_id": base_id, "scaled_strategy_id": strategy_id, "target_volatility": target_vol, "window_id": row.window_id, "cost_scenario": "BASE", "net_cagr": row.net_cagr, "maximum_drawdown": row.maximum_drawdown, "ulcer_index": row.ulcer_index, "calmar": row.calmar_mar, "average_exposure": 1.0 - row.average_cash_weight, "static_same_exposure_cagr": static_full.net_cagr if row.window_id == "FULL_HISTORY" else np.nan, "static_same_exposure_mdd": static_full.maximum_drawdown if row.window_id == "FULL_HISTORY" else np.nan, "terminal_wealth_advantage": row.terminal_wealth_per_100k / static_full.terminal_wealth_per_100k - 1.0 if row.window_id == "FULL_HISTORY" else np.nan, "risk_edge_status": "PASS" if row.window_id == "FULL_HISTORY" and row.terminal_wealth_per_100k >= static_full.terminal_wealth_per_100k * 1.05 else "FAIL", "warning": WARNING})
    vol_table = pd.DataFrame(vol_rows)
    write_csv("UKACTIVE_A4E_SIPP_VOLATILITY_CONTROL.csv", vol_table)
    candidate_results.update(vol_results)

    # Full final Pareto table.
    pareto_rows = []
    for strategy_id, result in candidate_results.items():
        row = metric_row(core.evaluation_rows(data, result, global_sim, pool_sim), "FULL_HISTORY")
        preferred = int(row.maximum_drawdown >= -0.15) + int(row.ulcer_index <= 0.08) + int(row.calmar_mar >= 0.75) + int(row.maximum_time_underwater_calendar_days <= 36 * 30.4375) + int(row.net_cagr >= 0.90 * global_full["net_cagr"])
        acceptable = bool(row.maximum_drawdown >= -0.20 and row.net_cagr >= global_full["net_cagr"] - 0.01)
        pareto_rows.append({"strategy_id": strategy_id, "net_cagr": row.net_cagr, "terminal_wealth_per_100k": row.terminal_wealth_per_100k, "maximum_drawdown": row.maximum_drawdown, "ulcer_index": row.ulcer_index, "longest_underwater_days": row.maximum_time_underwater_calendar_days, "turnover": row.annual_turnover_traded_notional, "calmar": row.calmar_mar, "preferred_target_count": preferred, "acceptable_region": acceptable, "pareto_efficient": False, "candidate_role": "", "warning": WARNING})
    pareto = pd.DataFrame(pareto_rows)
    for idx, row in pareto.iterrows():
        dominated = ((pareto["net_cagr"] >= row.net_cagr) & (pareto["maximum_drawdown"] >= row.maximum_drawdown) & (pareto["ulcer_index"] <= row.ulcer_index) & (pareto["turnover"] <= row.turnover) & ((pareto[["net_cagr", "maximum_drawdown"]] != row[["net_cagr", "maximum_drawdown"]].to_numpy()).any(axis=1))).any()
        pareto.loc[idx, "pareto_efficient"] = not bool(dominated)
    return_id = pareto.sort_values(["net_cagr", "maximum_drawdown"], ascending=[False, False]).iloc[0]["strategy_id"]
    draw_pool = pareto.loc[pareto["net_cagr"].ge(0.90 * global_full["net_cagr"])]
    drawdown_id = (draw_pool if len(draw_pool) else pareto).sort_values(["maximum_drawdown", "net_cagr"], ascending=[False, False]).iloc[0]["strategy_id"]
    acceptable_pool = pareto.loc[pareto["acceptable_region"]]
    if len(acceptable_pool):
        balanced_id = acceptable_pool.sort_values(["preferred_target_count", "net_cagr", "ulcer_index", "turnover"], ascending=[False, False, True, True]).iloc[0]["strategy_id"]
    else:
        # Mandatory fallback: highest-return static global/cash allocation satisfying the -20% drawdown budget.
        static_ids = [value for value in pareto["strategy_id"] if str(value).startswith("GLOBAL_CASH_")]
        static_pool = pareto.loc[pareto["strategy_id"].isin(static_ids) & pareto["maximum_drawdown"].ge(-0.20)]
        if static_pool.empty:
            static_pool = pareto.loc[pareto["strategy_id"].isin(static_ids)]
        balanced_id = static_pool.sort_values(["net_cagr", "maximum_drawdown"], ascending=[False, False]).iloc[0]["strategy_id"]
    pareto.loc[pareto["strategy_id"].eq(return_id), "candidate_role"] += "RETURN_MAXIMISING;"
    pareto.loc[pareto["strategy_id"].eq(drawdown_id), "candidate_role"] += "DRAWDOWN_MINIMISING;"
    pareto.loc[pareto["strategy_id"].eq(balanced_id), "candidate_role"] += "BALANCED_SIPP_SELECTED;"
    write_csv("UKACTIVE_A4E_SIPP_PARETO_FRONTIER.csv", pareto)
    blend_table["pareto_status"] = np.where(blend_table["strategy_id"].isin(pareto.loc[pareto["pareto_efficient"], "strategy_id"]), "PARETO", "DOMINATED_OR_CONTEXT")
    write_csv("UKACTIVE_A4E_SIPP_CORE_SATELLITE_FRONTIER.csv", blend_table)

    selected_whole = candidate_results[str(balanced_id)]
    selected_eval = core.evaluation_rows(data, selected_whole, global_sim, pool_sim)

    # Active edge hierarchy.
    active_full = metric_row(candidate_eval, "FULL_HISTORY")
    active_double_full = metric_row(eval_cache[("M2_BASE", 7, True, "DOUBLE")], "FULL_HISTORY")
    active_excl2025 = excluded_comparison(representative_cash1, pool_sim, {2025})
    family_base, _ = core.a4d.contribution_tables(representative_cash1, data.base.research.calendar)
    leave_one_rows = []
    for family in data.members:
        result = core.simulate_rotation(data, "M2_BASE", 7, True, excluded_families={family})
        row = metric_row(core.evaluation_rows(data, result, global_sim, pool_sim), "FULL_HISTORY")
        leave_one_rows.append({"excluded_family": family, "net_cagr": row.net_cagr, "excess_vs_global": row.excess_vs_global, "excess_vs_pool": row.excess_vs_pool, "maximum_drawdown": row.maximum_drawdown, "calmar": row.calmar_mar, "single_family_explains_edge": row.excess_vs_pool < 0, "warning": WARNING})
    family_influence = pd.DataFrame(leave_one_rows)
    top_families = family_base.head(5)["economic_exposure_family_id"].tolist()
    for count in [1, 3, 5]:
        result = core.simulate_rotation(data, "M2_BASE", 7, True, excluded_families=set(top_families[:count]))
        row = metric_row(core.evaluation_rows(data, result, global_sim, pool_sim), "FULL_HISTORY")
        family_influence = pd.concat([family_influence, pd.DataFrame([{"excluded_family": f"TOP_{count}_CONTRIBUTORS", "net_cagr": row.net_cagr, "excess_vs_global": row.excess_vs_global, "excess_vs_pool": row.excess_vs_pool, "maximum_drawdown": row.maximum_drawdown, "calmar": row.calmar_mar, "single_family_explains_edge": False, "warning": WARNING}])], ignore_index=True)
    write_csv("UKACTIVE_A4E_SIPP_FAMILY_INFLUENCE.csv", family_influence)
    no_single_family = not bool(family_influence.loc[family_influence["excluded_family"].isin(data.members), "single_family_explains_edge"].any())
    breadth_coherent = bool((full["pool_excess"] > 0).all())
    active_edge = bool(active_full.excess_vs_pool > 0 and active_excl2025["excess"] >= 0 and active_double_full.excess_vs_pool >= 0 and breadth_coherent and no_single_family and matched_timing_pass)

    # Holding-spell falsification.
    spells = core.holding_spell_ledger(representative_cash1)
    write_csv("UKACTIVE_A4E_SIPP_HOLDING_SPELL_LEDGER.csv", spells)
    spell_rows = []
    for count in [1, 3, 5]:
        removed = spells.head(count)
        targets = core.targets_without_spells(representative_cash1.targets, removed)
        records = representative_cash1.records.copy()
        result = core.simulate_targets(data, f"REMOVE_TOP_{count}_SPELLS", targets, records)
        row = metric_row(core.evaluation_rows(data, result, global_sim, pool_sim), "FULL_HISTORY")
        spell_rows.append({"test_id": f"REMOVE_TOP_{count}_HOLDING_SPELLS", "removed_spell_ids": ";".join(removed["holding_spell_id"]), "removed_families": ";".join(removed["family"]), "net_cagr": row.net_cagr, "excess_vs_pool": row.excess_vs_pool, "maximum_drawdown": row.maximum_drawdown, "warning": WARNING})
    write_csv("UKACTIVE_A4E_SIPP_HOLDING_SPELL_INFLUENCE.csv", pd.DataFrame(spell_rows))

    # Year exclusions and leave-one-year-out.
    year_rows = []
    complete_years = list(range(2018, 2026))
    tests = [("EXCLUDE_2025", {2025}), ("EXCLUDE_2020", {2020}), ("EXCLUDE_2020_2025", {2020, 2025})] + [(f"LEAVE_OUT_{year}", {year}) for year in complete_years]
    for test_id, years in tests:
        selected_metrics = core.excluded_year_metrics(representative_cash1.simulation, years)
        global_metrics = core.excluded_year_metrics(global_sim, years)
        pool_metrics = core.excluded_year_metrics(pool_sim, years)
        year_rows.append({"test_id": test_id, "excluded_years": ";".join(map(str, sorted(years))), "net_cagr": selected_metrics["net_cagr"], "global_cagr": global_metrics["net_cagr"], "pool_cagr": pool_metrics["net_cagr"], "excess_vs_global": selected_metrics["net_cagr"] - global_metrics["net_cagr"], "excess_vs_pool": selected_metrics["net_cagr"] - pool_metrics["net_cagr"], "maximum_drawdown": selected_metrics["maximum_drawdown"], "terminal_wealth_per_100k": selected_metrics["terminal_wealth_per_100k"], "warning": WARNING})
    year_exclusions = pd.DataFrame(year_rows)
    write_csv("UKACTIVE_A4E_SIPP_YEAR_EXCLUSIONS.csv", year_exclusions)

    # Random and rank-shuffle controls.
    random_rows = [
        core.vectorised_randomisation_control(data, representative_cash1.targets, mode="RANDOM_SELECTION_SAME_RISKY_COUNT", seed=20260824, simulation_count=5000),
        core.vectorised_randomisation_control(data, representative_cash1.targets, mode="MONTHLY_RANK_SHUFFLE", seed=20260825, simulation_count=5000),
    ]
    random_table = pd.DataFrame(random_rows)
    write_csv("UKACTIVE_A4E_SIPP_RANDOM_SELECTION_CONTROL.csv", random_table)

    # Crisis stress: accepted primary data availability only.
    crisis_ranges = {
        "2000_2003": ("2000-01-01", "2003-12-31"),
        "2007_2009": ("2007-01-01", "2009-12-31"),
        "2011": ("2011-01-01", "2011-12-31"),
        "2015_2016": ("2015-01-01", "2016-12-31"),
        "2018": ("2018-01-01", "2018-12-31"),
        "2020": ("2020-01-01", "2020-12-31"),
        "2022": ("2022-01-01", "2022-12-31"),
    }
    crisis_rows = []
    for crisis_id, (start_text, end_text) in crisis_ranges.items():
        start, end = pd.Timestamp(start_text), pd.Timestamp(end_text)
        for strategy_id, simulation, evidence in [
            ("GLOBAL_DEVELOPED_WORLD", global_sim, "CAUSAL_IMPLEMENTATION_EVIDENCE"),
            ("CORE_1_GLOBAL_ABSOLUTE_MOMENTUM", core_results["CORE_1_GLOBAL_ABSOLUTE_MOMENTUM"].simulation, "CAUSAL_IMPLEMENTATION_EVIDENCE"),
            ("M2_BASE_TOP7_CASH1", representative_cash1.simulation, "CAUSAL_ROTATION_IMPLEMENTATION_EVIDENCE_FROM_2017_ONLY"),
        ]:
            available_start = pd.Timestamp(simulation.curve["date"].min())
            available_end = pd.Timestamp(simulation.curve["date"].max())
            if start < available_start or end > available_end:
                crisis_rows.append({"crisis_id": crisis_id, "strategy_id": strategy_id, "evidence_type": evidence, "status": "UNAVAILABLE_NO_ACCEPTED_HISTORY", "start": start, "end": end, "return": np.nan, "maximum_drawdown": np.nan})
            else:
                metrics = core.metric_pack(simulation, start, end)
                crisis_rows.append({"crisis_id": crisis_id, "strategy_id": strategy_id, "evidence_type": evidence, "status": "AVAILABLE", "start": start, "end": end, "return": metrics["terminal_wealth_per_100k"] / 100000.0 - 1.0, "maximum_drawdown": metrics["maximum_drawdown"]})
    crisis_table = pd.DataFrame(crisis_rows)
    write_csv("UKACTIVE_A4E_SIPP_CRISIS_STRESS.csv", crisis_table)
    write_text("UKACTIVE_A4E_SIPP_CRISIS_STRESS.md", f"""# UKACTIVE-A4E-SIPP crisis stress

The accepted programme calendar begins in 2000, but the validated `GLOBAL_DEVELOPED_WORLD` implementation wealth chain begins on {global_sim.curve['date'].min():%Y-%m-%d}; the primary rotation chain begins on {representative_cash1.simulation.curve['date'].min():%Y-%m-%d}. Therefore 2000–03 and 2007–09 cannot be tested with accepted causal implementation history. No vendor/index proxy was imported around the MDM controls and no unavailable return was manufactured.

The machine-readable table reports 2011, 2015–16, 2018, 2020 and 2022 where each strategy has accepted history. Rotation evidence is explicitly unavailable before 2017. This is a remaining retirement-risk evidence gap, not a reason to relabel later evidence as crisis confirmation.
""")

    # Retirement transition diagnostics for selected, core and rotation.
    retirement = retirement_rows({"BALANCED_SIPP_SELECTED": selected_whole, "CORE_0_GLOBAL": core_results["CORE_0_GLOBAL"], "M2_BASE_TOP7_CASH1": representative_cash1})
    write_csv("UKACTIVE_A4E_SIPP_RETIREMENT_TRANSITION.csv", retirement)

    # Current implementation and live-cost audit.
    instrument_map = build_implementation_map()
    write_csv("UKACTIVE_A4E_SIPP_LIVE_INSTRUMENT_MAP.csv", instrument_map)
    selected_full = metric_row(selected_eval, "FULL_HISTORY")
    live_strategies = [
        {"strategy_id": str(balanced_id), "turnover": selected_full.annual_turnover_traded_notional, "trade_legs_per_year": selected_full.trade_legs / max(selected_full.calendar_years, 1e-12), "rotation_weight": 0.0 if str(balanced_id).startswith("GLOBAL_CASH") or str(balanced_id).startswith("CORE") else float(selected_whole.metadata.get("average_rotation_exposure", 0.0)), "core_weight": 0.75 if str(balanced_id).startswith("GLOBAL_CASH_75") else (1.0 if str(balanced_id).startswith("CORE") else 1.0 - float(selected_whole.metadata.get("average_rotation_exposure", 0.0)))},
        {"strategy_id": "M2_BASE_TOP7_CASH1_ROTATION", "turnover": active_full.annual_turnover_traded_notional, "trade_legs_per_year": active_full.trade_legs / max(active_full.calendar_years, 1e-12), "rotation_weight": 1.0, "core_weight": 0.0},
        {"strategy_id": "CORE_0_GLOBAL", "turnover": core0.turnover if "turnover" in core0.index else 0.0, "trade_legs_per_year": 0.11, "rotation_weight": 0.0, "core_weight": 1.0},
    ]
    live_costs = live_cost_rows(live_strategies, instrument_map)
    write_csv("UKACTIVE_A4E_SIPP_LIVE_COSTS.csv", live_costs)

    write_text(
        "UKACTIVE_A4E_SIPP_IMPLEMENTATION_AUDIT.md",
        f"""# UKACTIVE-A4E-SIPP implementation audit

- Active map: 25/25 signal-ready industry/theme families are `CONFIRMED_BY_USER` in ii as of 2026-08-23; current-only evidence is not back-projected.
- Core: SWDA / IE00B4L5Y983 is user-confirmed in ii. Official iShares evidence reports Ireland domicile, UCITS, accumulating, physical optimised replication, 0.20% TER, ISA eligibility and SIPP availability.
- Active-family SIPP-specific availability remains `TO_CHECK_SIPP_SPECIFIC_ACCOUNT`; user-account tradability is not silently promoted to SIPP evidence.
- Missing current TER, AUM, tracking-difference, spread and traded-value fields remain explicit rather than estimated in the instrument map. Live-cost diagnostics use the median documented active TER only as a disclosed cost proxy and retain doubled historical cost stress.
- Preferred GBP/GBX lines are preserved. If a preferred line and its predeclared same-family alternate are unavailable, the affected slot is GBP cash. There is no discretionary substitute.
- Live cash is ii SIPP GBP broker cash for operating design. Historical research continues to use the accepted GBP cash series; current tiered ii rates are not back-projected.
""",
    )

    # Strategy-decision hierarchy and deployment tier.
    active_implementation_complete = bool(instrument_map.loc[instrument_map["economic_exposure_family_id"].isin(data.members), "broker_availability"].eq("CONFIRMED_BY_USER").all())
    sipp_specific_active_complete = bool(instrument_map.loc[instrument_map["economic_exposure_family_id"].isin(data.members), "sipp_availability"].eq("YES_OFFICIAL_ISHARES").all())
    if not active_edge:
        deployment_tier = "CORE_ONLY"
    elif active_edge and active_implementation_complete and sipp_specific_active_complete:
        deployment_tier = "CORE_PLUS_10_PERCENT_ROTATION_PILOT"
    else:
        deployment_tier = "SHADOW_ONLY_PENDING_IMPLEMENTATION"

    # A deployment-governance 10% diagnostic is explicitly authorised, but cannot change selection.
    deployment_result = selected_whole
    deployment_strategy_id = str(balanced_id)
    if deployment_tier == "CORE_PLUS_10_PERCENT_ROTATION_PILOT":
        targets, records = core.combine_target_maps(selected_rotation.targets, selected_core_targets, 0.10)
        deployment_strategy_id = f"ROTATION_{selected_variant}_10|CORE_{selected_core_id}_90"
        deployment_result = core.simulate_targets(data, deployment_strategy_id, targets, records, force_every_review=True)
    deployment_eval = core.evaluation_rows(data, deployment_result, global_sim, pool_sim)

    # Complete scorecard and Pareto outputs.
    architecture_rows = []
    for strategy_id, result in candidate_results.items():
        evaluated = core.evaluation_rows(data, result, global_sim, pool_sim)
        for row in evaluated.itertuples(index=False):
            architecture_rows.append(row._asdict())
    architecture_table = pd.DataFrame(architecture_rows)
    write_csv("UKACTIVE_A4E_SIPP_WHOLE_SIPP_SCORECARD.csv", architecture_table)

    # Correctness controls before final decision.
    current_prior_hashes = {name: sha256(ROOT / name) for name in ["UKACTIVE_A4D_DECISION.json", "UKACTIVE_A4D_MANIFEST.json", "UKACTIVE_A5_DECISION_LEDGER.csv", "UKACTIVE_A5_EXECUTION_LEDGER.csv", "UKACTIVE_A5_NAV_HISTORY.csv"]}
    expected_prior_hashes = {
        "UKACTIVE_A4D_DECISION.json": "6b72ec910b62505c3a83fb5f8c54ff2bb521579195c836b617fd4e450d245131",
        "UKACTIVE_A4D_MANIFEST.json": "a9770b7fca361fffd225df2f287efaef0e1019c4bdf516966192c5c134d04b0f",
        "UKACTIVE_A5_DECISION_LEDGER.csv": "68e9fb28d4acfb0be707ab313dc40d46158cb76aa789d1aed011d8e8b05eba67",
        "UKACTIVE_A5_EXECUTION_LEDGER.csv": "8c48625268167ff20f49cfcf7dd1859377469ac635cf3fc9e70d3a62d2cde200",
        "UKACTIVE_A5_NAV_HISTORY.csv": "3359a748cad99a56ee998b6471591a09191a3c814d239ce21238ce79c8e88c2d",
    }
    tests = [
        ("AUTHORITATIVE_CUTOFF", pd.Timestamp(data.base.research.calendar.max()) == cutoff, str(cutoff.date())),
        ("A4D_REPRODUCTION", audit_pass, f"{len(reconciliation)} deterministic comparisons"),
        ("NO_POST_CUTOFF_TARGETS", max(representative_cash1.targets) <= cutoff, str(max(representative_cash1.targets).date())),
        ("NEXT_SESSION_EXECUTION", bool((representative_cash1.simulation.trades.loc[representative_cash1.simulation.trades.execution_status.eq('EXECUTED'), 'execution_lag_xlon_sessions'] >= 1).all()), "lag >= 1"),
        ("MAX_EXECUTION_LAG", bool((representative_cash1.simulation.trades.loc[representative_cash1.simulation.trades.execution_status.eq('EXECUTED'), 'execution_lag_xlon_sessions'] <= 3).all()), "lag <= 3"),
        ("LONG_ONLY_NO_LEVERAGE", bool((selected_whole.simulation.curve['invested_fraction'] <= 1.0 + 1e-10).all()), "selected whole SIPP"),
        ("CASH_RECONCILES", bool(np.allclose(selected_whole.simulation.curve['invested_fraction'] + selected_whole.simulation.curve['cash_fraction'], 1.0, atol=1e-10)), "invested + cash = 1"),
        ("M2_WEIGHTS_FROZEN", core.SIGNAL_WEIGHTS["M2_BASE"] == [0.10, 0.15, 0.25, 0.30, 0.20], str(core.SIGNAL_WEIGHTS["M2_BASE"])),
        ("RANDOM_SEEDS_AND_COUNT", bool((random_table['simulation_count'] == 5000).all() and set(random_table['seed']) == {20260824, 20260825}), "5000 each"),
        ("PRIOR_OUTPUTS_IMMUTABLE", current_prior_hashes == expected_prior_hashes, json.dumps(current_prior_hashes, sort_keys=True)),
        ("NO_A5_PROSPECTIVE_EVENT", pd.read_csv(ROOT / "UKACTIVE_A5_DECISION_LEDGER.csv").empty and pd.read_csv(ROOT / "UKACTIVE_A5_EXECUTION_LEDGER.csv").empty and pd.read_csv(ROOT / "UKACTIVE_A5_NAV_HISTORY.csv").empty, "A5 ledgers header-only"),
        ("ACTIVE_CURRENT_MAP_25", int(instrument_map["economic_exposure_family_id"].isin(data.members).sum()) == 25, "25 signal-ready current implementations; 2 structural no-history families excluded"),
        ("CORE_IMPLEMENTATION", bool(((instrument_map["economic_exposure_family_id"] == "GLOBAL_DEVELOPED_WORLD") & (instrument_map["ticker"] == "SWDA") & (instrument_map["isin"] == "IE00B4L5Y983")).any()), "SWDA exact"),
        (
            "BALANCED_STRATEGY_IS_PREREGISTERED_CANDIDATE_NOT_FALSIFICATION_CONTROL",
            str(balanced_id) in candidate_results
            and not str(balanced_id).startswith("ROTATION_STATIC_SAME_AVERAGE_EXPOSURE")
            and not str(balanced_id).startswith("ROTATION_MATCHED_VOLATILITY"),
            str(balanced_id),
        ),
    ]
    test_rows = [{"test_id": test_id, "status": "PASS" if passed else "FAIL", "detail": detail} for test_id, passed, detail in tests]
    correctness = {"stage_id": "UKACTIVE-A4E-SIPP", "tests": test_rows, "summary": {"PASS": sum(row["status"] == "PASS" for row in test_rows), "FAIL": sum(row["status"] == "FAIL" for row in test_rows)}}
    write_json("UKACTIVE_A4E_SIPP_CORRECTNESS_TESTS.json", correctness)
    if correctness["summary"]["FAIL"]:
        raise AssertionError("Correctness controls failed")

    selected_full_row = metric_row(deployment_eval, "FULL_HISTORY")
    selected_latest5_row = metric_row(deployment_eval, "LATEST_5Y")
    selected_latest3_row = metric_row(deployment_eval, "LATEST_3Y")
    expected_cagr_low = min(selected_full_row.net_cagr, selected_latest5_row.net_cagr, selected_latest3_row.net_cagr)
    expected_cagr_high = max(selected_full_row.net_cagr, selected_latest5_row.net_cagr, selected_latest3_row.net_cagr)
    expected_mdd_low = min(selected_full_row.maximum_drawdown, selected_latest5_row.maximum_drawdown, selected_latest3_row.maximum_drawdown)
    expected_mdd_high = max(selected_full_row.maximum_drawdown, selected_latest5_row.maximum_drawdown, selected_latest3_row.maximum_drawdown)
    # Deliberately wider and lower than the observed 2017-2026 record.  This
    # is a governance planning range, not a fitted forecast interval.
    conservative_planning_range = {
        "net_cagr_low": 0.04,
        "net_cagr_high": 0.09,
        "maximum_drawdown_less_severe": -0.15,
        "maximum_drawdown_more_severe": -0.30,
        "strategic_cash_weight": 0.25,
        "observed_annual_turnover_reference": float(selected_full_row.annual_turnover_traded_notional),
        "status": "CONSERVATIVE_GOVERNANCE_RANGE_NOT_A_FORECAST_OR_GUARANTEE",
    }

    fallback_rule = {
        "strategy_id": deployment_strategy_id,
        "portfolio_sleeves": [{"sleeve": "GLOBAL_CORE", "target_weight": 0.75, "instrument": "SWDA|IE00B4L5Y983"}, {"sleeve": "GBP_CASH", "target_weight": 0.25, "instrument": "II_SIPP_GBP_BROKER_CASH"}] if deployment_strategy_id == "GLOBAL_CASH_75_25" else [{"sleeve": "SELECTED_STRATEGY", "target_weight": 1.0, "instrument": deployment_strategy_id}],
        "rebalance": "After the final valid XLON close of each calendar month; execute at first valid next XLON session within 3 sessions",
        "replacement": "SWDA unavailable -> do not buy a discretionary world ETF; allocate affected core to GBP cash until a separately evidenced same-exposure alternate is frozen",
        "cash_rule": "Fixed strategic GBP cash weight for GLOBAL_CASH fallback; cash earns broker SIPP rate operationally and accepted GBP cash series in research",
        "risk_scaling": "NONE",
        "cost_assumptions": "20 bp one-way + £3.99 per trade leg historically; live ii platform/product costs added separately",
        "permitted_instruments": ["SWDA|IE00B4L5Y983", "II_SIPP_GBP_BROKER_CASH"],
        "no_leverage": True,
        "no_shorting": True,
        "conservative_planning_range": conservative_planning_range,
    }
    selected_strategy = {
        "stage_id": "UKACTIVE-A4E-SIPP",
        "decision_date": RETRIEVAL_DATE,
        "historical_cutoff": "2026-08-21",
        "best_available_whole_sipp_strategy": fallback_rule,
        "active_rotation_sleeve": {"architecture": "M2_BASE|TOP7|MONTHLY|CASH1|EQUAL", "status": "SHADOW_OBSERVATION_ONLY" if not active_edge else "LIMITED_PILOT_ELIGIBLE", "allocation": 0.0 if deployment_tier == "CORE_ONLY" else (0.10 if "10_PERCENT" in deployment_tier else 0.25), "evidence": "E2_DEVELOPMENTAL"},
        "deployment_tier": deployment_tier,
        "defensive_fallback": fallback_rule,
        "automatic_broker_execution": False,
    }
    write_json("UKACTIVE_A4E_SIPP_SELECTED_STRATEGY.json", selected_strategy)

    decision = {
        "stage_id": "UKACTIVE-A4E-SIPP",
        "decision": "UKACTIVE_A4E_SIPP_STRATEGY_SELECTED",
        "reproduction_audit": "PASS",
        "cash1_advancement": "PASS" if cash1_advances else "FAIL",
        "cash1_gate_checks": cash1_gate_checks,
        "selected_rotation_variant": selected_variant,
        "active_edge": active_edge,
        "selected_core": selected_core_id,
        "balanced_research_candidate": str(balanced_id),
        "deployment_strategy": deployment_strategy_id,
        "deployment_tier": deployment_tier,
        "evidence_level": "E2_DEVELOPMENTAL",
        "historical_cutoff": "2026-08-21",
        "no_broker_execution": True,
        "selected_full_history_metrics": {
            "net_cagr": float(selected_full_row.net_cagr),
            "maximum_drawdown": float(selected_full_row.maximum_drawdown),
            "ulcer_index": float(selected_full_row.ulcer_index),
            "calmar": float(selected_full_row.calmar_mar),
            "annual_turnover": float(selected_full_row.annual_turnover_traded_notional),
        },
    }
    write_json("UKACTIVE_A4E_SIPP_DECISION.json", decision)

    # Monthly runbook and deployment governance.
    write_text("UKACTIVE_A4E_SIPP_MONTHLY_RUNBOOK.md", f"""# UKACTIVE-A4E-SIPP monthly runbook

## Whole-SIPP rule

Selected strategy: `{deployment_strategy_id}`.

1. After the final valid XLON close of each calendar month, validate the A2R2 calendar/data cutoff and current instrument status.
2. For the selected fixed fallback, calculate current sleeve values and set SWDA to 75% and ii SIPP GBP cash to 25% of total portfolio value.
3. Record the decision before the next eligible XLON close is available.
4. Execute hypothetically/operationally at the first valid next XLON session, within three sessions; never use the signal close.
5. If SWDA is unavailable, cancel the affected purchase and hold GBP cash. Do not choose a discretionary substitute.
6. Charge/record actual commission, spread, platform, TER and any cash-rate change. Never infer historical availability from the current account.
7. Reconcile positions, cash, costs, signal timestamp and input hashes. No automatic broker order is authorised.

## Rotation shadow

Continue `M2_BASE | TOP7 | MONTHLY | CASH1 | EQUAL` in shadow only. Rank economic families, not listings. A slot qualifies only when its accepted 252-session total return exceeds contemporaneous GBP-cash 252-session return. An unavailable preferred and predeclared alternate means cash, not substitution.
""")

    write_text("UKACTIVE_A4E_SIPP_DEPLOYMENT_PLAN.md", f"""# UKACTIVE-A4E-SIPP deployment plan

Current tier: `{deployment_tier}`.

The complete SIPP follows `{deployment_strategy_id}`. Active rotation receives {selected_strategy['active_rotation_sleeve']['allocation']:.0%}; it remains E2 developmental. Review the shadow ledger after 6, 12, 24 and 36 on-time monthly decisions. Six decisions are operational evidence only. No allocation increase is permitted solely because returns are positive.

Escalation requires correct signals, realised costs within the documented envelope, no implementation mismatch, turnover within expectation, directionally consistent matched-risk performance and drawdown inside the intended envelope. A material active sleeve requires prospective confirmation and a new frozen version.

Suspend new active allocation when a required instrument is unavailable, point-in-time membership or signals cannot be reproduced, source data fail validation, or realised costs materially exceed assumptions. Reopen research for systematic prospective/backtest divergence, failure versus matched-risk controls over a meaningful period, drawdown outside the modelled envelope, or a data/eligibility defect. Short-term underperformance alone is not an automatic stop.
""")

    # Final report with mandatory exact sections.
    matched_rotation_full = matched_exposure.loc[
        matched_exposure["window_id"].eq("FULL_HISTORY")
        & matched_exposure["control_id"].eq("ROTATION_STATIC_SAME_AVERAGE_EXPOSURE")
    ].iloc[0]
    matched_global_full = matched_exposure.loc[
        matched_exposure["window_id"].eq("FULL_HISTORY")
        & matched_exposure["control_id"].eq("GLOBAL_STATIC_SAME_AVERAGE_EXPOSURE")
    ].iloc[0]
    random_path = random_table.loc[
        random_table["control_id"].eq("RANDOM_SELECTION_SAME_RISKY_COUNT")
    ].iloc[0]
    rank_shuffle = random_table.loc[
        random_table["control_id"].eq("MONTHLY_RANK_SHUFFLE")
    ].iloc[0]
    selected_live_250 = live_costs.loc[
        live_costs["strategy_id"].eq("GLOBAL_CASH_75_25")
        & live_costs["sipp_size_gbp"].eq(250000)
    ].iloc[0]
    report = f"""# UKACTIVE-A4E-SIPP — final decision report

Historical cutoff: **2026-08-21**  
Evidence: **E2 developmental; no independent confirmation**  
Decision: **UKACTIVE_A4E_SIPP_STRATEGY_SELECTED**

## What we now know

A4D reproduced exactly. CASH1 retains the attractive five-year economics but fails the preregistered full-history retention and stability standard: full-history TOP7 CAGR falls from {cash0_full.net_cagr:.2%} CASH0 to {active_full.net_cagr:.2%} CASH1, and full-history drawdown changes from {cash0_full.maximum_drawdown:.2%} to {active_full.maximum_drawdown:.2%}. Its recent drawdown benefit is real economic information, but not a stable whole-period timing edge. CORE1 global absolute momentum also fails: it retains {core1.net_cagr/core0.net_cagr:.1%} of CORE0 CAGR and does not improve full-history maximum drawdown.

The final active-edge hierarchy is `{active_edge}`. Full-history equal-pool excess is {active_full.excess_vs_pool:.2%}; excluding 2025 it is {active_excl2025['excess']:.2%}; doubled-cost full-history excess is {active_double_full.excess_vs_pool:.2%}. Random/rank-shuffle percentiles are reported in the falsification table, but do not overcome the failed full-history cash/risk gate or missing E3 evidence.

Matched exposure rejects a timing claim for CASH1. A static version of the same rotation portfolio at CASH1's average exposure produced {matched_rotation_full.control_cagr:.2%} CAGR and {matched_rotation_full.control_mdd:.2%} drawdown versus CASH1's {matched_rotation_full.candidate_cagr:.2%} and {matched_rotation_full.candidate_mdd:.2%}; the same-exposure global/cash control produced {matched_global_full.control_cagr:.2%} and {matched_global_full.control_mdd:.2%}. CASH1 ranked at the {random_path.candidate_cagr_percentile:.1%} percentile of matched-count random selection and the {rank_shuffle.candidate_cagr_percentile:.1%} percentile of monthly rank shuffles, which is interesting E2 evidence but not enough to pass the mandatory active-edge hierarchy. M2_BASE and its bounded neighbours broadly retain an always-invested TOP6–TOP8 ranking effect; TOP9 and family-removal sensitivity show that it is not a sufficiently stable whole-SIPP alpha claim.

## What we can rule out

- M2 neighbourhood testing does not convert the exposed result into independent confirmation.
- Exact CASH1 is not a reliable full-history drawdown solution.
- The frozen 252-session global/cash rule is not a superior retirement core over the causal period.
- Weekly CASH1 exit-only monitoring and rank hysteresis cannot be promoted unless all frozen gates pass; failed rows remain disclosed.
- No accepted implementation data support 2000–03 or 2007–09 crisis claims.

## What looks economically interesting

CASH1’s post-2020 and final-five-year behaviour remains worth prospective shadow observation. It is selected before outcomes through the same family-level process and ranks unusually relative to the bounded random controls. This is a developmental mechanism lead, not a live alpha claim.

## BEST AVAILABLE WHOLE-SIPP STRATEGY

`{deployment_strategy_id}`

- 75% `GLOBAL_DEVELOPED_WORLD` through SWDA, ISIN IE00B4L5Y983.
- 25% Interactive Investor SIPP GBP broker cash.
- Rebalance after the final valid XLON close each month.
- Execute at the first valid next XLON session within three sessions; never same-close.
- No volatility scaling, leverage, shorting, discretionary replacement or active theme allocation.
- If SWDA is unavailable, leave the affected amount in GBP cash until a same-exposure alternate is separately evidenced and frozen.
- Historical cost convention: 20 bp one-way plus £3.99 per leg; live platform, TER and cash-rate economics are reported separately.

## WHY THIS STRATEGY WAS SELECTED

No active or dynamic global/cash candidate cleared the complete return/risk hierarchy. The mandatory fallback rule therefore selected the highest-return static global/cash allocation that remains inside the approximately -20% historical drawdown budget. It is simpler, cheaper and less dependent on 2025 or a small set of thematic winners than the rotation alternatives. It does not claim alpha and may sacrifice material equity upside; that is the explicit cost of the selected drawdown budget.

Full-history selected metrics: net CAGR **{selected_full_row.net_cagr:.2%}**, maximum drawdown **{selected_full_row.maximum_drawdown:.2%}**, Ulcer Index **{selected_full_row.ulcer_index:.2%}**, Calmar **{selected_full_row.calmar_mar:.2f}**, average cash **{selected_full_row.average_cash_weight:.1%}**.

At £250,000, the current live-cost audit estimates **£{selected_live_250.total_estimated_annual_cost:,.0f} ({selected_live_250.cost_as_percentage:.2%})** including platform fee, an explicit spread assumption and SWDA TER. TER is already economically embedded in realised ETF returns and is shown here for ownership-cost transparency, not added a second time to the historical total-return chain.

## EXPECTED PERFORMANCE RANGE

- Conservative governance planning range for net CAGR: **4% to 9% nominal after costs**.
- Conservative maximum-drawdown planning range: **approximately -15% to -30%**.
- Observed historical net-CAGR reference across full/five-/three-year windows: **{expected_cagr_low:.1%} to {expected_cagr_high:.1%}**; this short-sample range is not the expectation.
- Observed historical maximum-drawdown range: **{expected_mdd_low:.1%} to {expected_mdd_high:.1%}**; future drawdown can be worse.
- Strategic cash allocation: **25%**, with drift corrected monthly.
- Expected turnover: approximately **{selected_full_row.annual_turnover_traded_notional:.2f}x** annual traded notional under the historical engine.
- Likely underperformance: strong uninterrupted global-equity bull markets, rapid rebounds after cash has reduced beta, and periods when the global core substantially outpaces cash.
- Principal uncertainty: no accepted 2000–03/2007–09 implementation test, no inflation series, short 2017–2026 whole-portfolio history and no E3 evidence.

These are historical reference ranges, not forecasts or drawdown guarantees.

## ACTIVE ROTATION SLEEVE

Architecture: `M2_BASE | TOP7 | MONTHLY | CASH1 | EQUAL`. Evidence: **E2 developmental**. Allocation: **{selected_strategy['active_rotation_sleeve']['allocation']:.0%}**. Status: **shadow observation only** under `{deployment_tier}`. The current 25-family implementation map is ii-confirmed, but SIPP-specific evidence remains incomplete for active lines.

## CORE STRATEGY

Static 75% SWDA / 25% ii SIPP GBP cash, rebalanced monthly after the final valid XLON close and executed next session. The tested 252-session dynamic global/cash rule was rejected because it lost too much return without improving full-history maximum drawdown.

## CURRENT DEPLOYMENT TIER

`{deployment_tier}`

## MONTHLY OPERATING RULE

Validate data and instrument state after month-end close; freeze a 75/25 target; record it before next-session close; execute at the first valid next XLON session; book all legs/costs; leave unavailable exposure in GBP cash; reconcile holdings and audit hashes. Rotation rankings are telemetry/shadow only and cannot change the whole-SIPP allocation.

## FAILURE MODES

The strategy can lag badly in strong equity markets, cash rates can fall, monthly rebalancing can be late around gaps, SWDA remains exposed to global equity and currency risk, and a future drawdown can exceed the historical range. Inflation can erode the fixed cash sleeve. The active shadow can fail because its apparent edge is regime- and right-tail-dependent.

## SUSPENSION AND REVIEW RULES

Suspend affected purchases for unavailable instruments, unreproducible point-in-time membership, invalid prices/signals, or material cost overruns. Reopen research for systematic prospective divergence, meaningful matched-risk failure, risk-envelope breach or a discovered lineage defect. Review the rotation shadow at 6/12/24/36 valid monthly decisions; do not increase allocation based only on profitability.

## REMAINING EVIDENCE GAP

No untouched historical holdout, no prospective A4E lineage, no accepted 2000–09 implementation stress, incomplete active-line SIPP/product-cost evidence, no accepted UK inflation series and uncertain future broker cash rates. Rotation remains a shadow hypothesis rather than a material SIPP sleeve.
"""
    write_text("UKACTIVE_A4E_SIPP_FINAL_DECISION_REPORT.md", report)

    executive = f"""# UKACTIVE-A4E-SIPP executive handoff

- Whole-SIPP selection: **{deployment_strategy_id}** — 75% SWDA / 25% ii SIPP GBP cash, monthly next-session rebalance.
- Deployment tier: **{deployment_tier}**.
- Rotation: **0% allocation; shadow only** using M2_BASE TOP7 monthly CASH1 equal weight.
- A4D reproduction: **PASS**.
- CASH1 full-history advancement: **{'PASS' if cash1_advances else 'FAIL'}**.
- Global 252-session absolute-momentum core: **{'SELECTED' if selected_core_id != 'CORE_0_GLOBAL' else 'REJECTED'}**.
- No automatic broker execution.
"""
    write_text("UKACTIVE_A4E_SIPP_EXECUTIVE_HANDOFF.md", executive)

    write_text("UKACTIVE_A4E_SIPP_PROVENANCE.md", f"""# UKACTIVE-A4E-SIPP provenance

Parent commit: `48cb69ffbaae25eb0dccc3226f47f5a7491e8bd7`  
Parent tag: `ukactive-a4d-v1-20260824`  
Preregistration commit: `{PREREG_COMMIT}`  
Branch: `research/ukactive-a4e-sipp`  
Cutoff: `2026-08-21`

All primary input hashes are frozen in `UKACTIVE_A4E_SIPP_PREREGISTRATION.json`. The A2R2 panel, endpoint history, signal eligibility, cash series, A4D decision and A5 ledgers retained their original hashes. External current-only facts are dated and cannot alter historical selection.
""")
    write_text("UKACTIVE_A4E_SIPP_DATA_CUTOFF_AUDIT.md", f"""# UKACTIVE-A4E-SIPP data-cutoff audit

- Maximum authoritative XLON session: `{data.base.research.calendar.max():%Y-%m-%d}`.
- Maximum A4E target review: `{max(representative_cash1.targets):%Y-%m-%d}`.
- No observation after 2026-08-21 entered a signal, target, execution, robustness test or strategy gate.
- Current implementation evidence dated 2026-08-23/24 is operational metadata only and is not back-projected.
""")

    # Manifest after all substantive outputs.
    required_outputs = sorted(path for path in OUT.iterdir() if path.is_file() and path.name != "UKACTIVE_A4E_SIPP_MANIFEST.json")
    manifest = {
        "stage_id": "UKACTIVE-A4E-SIPP",
        "run_id": "UKACTIVE-A4E-SIPP-20260824-001",
        "parent_commit": "48cb69ffbaae25eb0dccc3226f47f5a7491e8bd7",
        "preregistration_commit": PREREG_COMMIT,
        "branch": "research/ukactive-a4e-sipp",
        "authoritative_cutoff": "2026-08-21",
        "decision": decision,
        "selected_strategy": selected_strategy,
        "environment": {"python": sys.version, "platform": platform.platform(), "pandas": pd.__version__, "numpy": np.__version__},
        "outputs": [{"path": path.name, "size_bytes": path.stat().st_size, "sha256": sha256(path)} for path in required_outputs],
        "source_hashes": prereg["source_hashes"],
        "immutable_prior_hashes_after": current_prior_hashes,
        "correctness": correctness["summary"],
        "warning": WARNING,
    }
    write_json("UKACTIVE_A4E_SIPP_MANIFEST.json", manifest)


if __name__ == "__main__":
    main()
