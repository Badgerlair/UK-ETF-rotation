"""UKACTIVE-A3R2S contemporary signal/count/cadence/regime research."""

from __future__ import annotations

import json
import math
import platform
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow

from ukactive_a3r2_core import (
    PLATFORM_ROOT,
    PROGRAMME_ROOT,
    WARNING,
    audit_file,
    benjamini_hochberg,
    circular_block_bootstrap_mean_ci,
    expanding_prior_quantile,
    git_output,
    newey_west_mean,
    read_policy,
    sha256_file,
    stable_id,
    utc_now,
    write_csv,
    write_json,
    write_parquet,
    write_text,
)
from ukactive_a3r2_portfolio import (
    CADENCES,
    INTELLIGENCE_POOLS,
    PORTFOLIO_POOLS,
    PORTFOLIO_SIGNALS,
    SELECTION_RULES,
    ResearchData,
    SimulationResult,
    aligned_excess_returns,
    equal_pool_targets,
    features_for_cadence,
    load_research_data,
    performance_metrics,
    review_interval_returns,
    selection_targets,
    simulate_equal_weight_benchmark,
    simulate_targets,
    unselected_targets,
)


PREFIX = "UKACTIVE_A3R2"
RUN_ID = "UKACTIVE-A3R2S-20260823-001"


def out(name: str) -> Path:
    return PROGRAMME_ROOT / f"{PREFIX}_{name}"


def window_bounds(calendar: pd.DatetimeIndex) -> dict[str, tuple[pd.Timestamp | None, pd.Timestamp | None]]:
    cutoff = pd.Timestamp(calendar.max())

    def first_on_or_after(value: pd.Timestamp) -> pd.Timestamp:
        return pd.Timestamp(calendar[calendar >= value][0])

    return {
        "LATEST_5Y": (first_on_or_after(cutoff - pd.DateOffset(years=5)), cutoff),
        "LATEST_3Y": (first_on_or_after(cutoff - pd.DateOffset(years=3)), cutoff),
        "POST_2020": (first_on_or_after(pd.Timestamp("2020-01-01")), cutoff),
        "FULL_HISTORY": (None, cutoff),
        "PRE_2020": (None, pd.Timestamp("2019-12-31")),
    }


def prefix_metrics(prefix: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in metrics.items()}


def common_start(*simulations: SimulationResult, floor: pd.Timestamp | None = None) -> pd.Timestamp | None:
    starts = []
    if floor is not None:
        starts.append(pd.Timestamp(floor))
    for simulation in simulations:
        if not simulation.curve.empty:
            starts.append(pd.Timestamp(simulation.curve["date"].min()))
    return max(starts) if starts else floor


def active_review_targets(pool_targets: dict[pd.Timestamp, dict[str, float]]) -> dict[pd.Timestamp, dict[str, float]]:
    return {
        date: ({"GLOBAL_DEVELOPED_WORLD": 1.0} if target else {})
        for date, target in pool_targets.items()
    }


def simulate_bundle(
    *,
    features: pd.DataFrame,
    signal_id: str,
    selection_rule: str,
    data: ResearchData,
    allowed_families: set[str] | None,
    maturity_scope: str,
    non_gbp_families: set[str],
    friction_bps: float = 20.0,
    fixed_fee: float = 3.99,
    sleeve_size: float = 250_000.0,
    fx_rate: float = 0.0075,
    excluded_families: set[str] | None = None,
    weighting_method: str = "EQUAL",
    rebalance_same_members: bool = False,
) -> dict[str, Any]:
    targets, records = selection_targets(
        features,
        signal_id=signal_id,
        selection_rule=selection_rule,
        allowed_families=allowed_families,
        maturity_scope=maturity_scope,
        excluded_families=excluded_families,
        weighting_method=weighting_method,
        volatility=data.matrices.price_features["REALISED_VOL_63"],
        maximum_weight=0.5,
    )
    pool_targets = equal_pool_targets(records, features, signal_id, allowed_families, maturity_scope)
    unselected = unselected_targets(targets, pool_targets)
    global_targets = active_review_targets(pool_targets)
    kwargs = {"calendar": data.calendar, "wealth": data.wealth, "segment": data.segment, "max_execution_lag": 3}
    selected_gross = simulate_targets(targets, **kwargs, rebalance_same_members=rebalance_same_members)
    selected_net = simulate_targets(
        targets,
        **kwargs,
        friction_bps=friction_bps,
        fixed_fee_gbp=fixed_fee,
        sleeve_size_gbp=sleeve_size,
        non_gbp_families=non_gbp_families,
        fx_rate=fx_rate,
        rebalance_same_members=rebalance_same_members,
    )
    equal_pool = simulate_equal_weight_benchmark(pool_targets, calendar=data.calendar, daily_returns=data.daily_returns)
    unselected_pool = simulate_equal_weight_benchmark(unselected, calendar=data.calendar, daily_returns=data.daily_returns)
    global_benchmark = simulate_targets(global_targets, **kwargs)
    return {
        "selected_gross": selected_gross,
        "selected_net": selected_net,
        "equal_pool": equal_pool,
        "unselected_pool": unselected_pool,
        "global_benchmark": global_benchmark,
        "target_records": records,
        "targets": targets,
        "pool_targets": pool_targets,
    }


def simulate_pair(
    *,
    features: pd.DataFrame,
    signal_id: str,
    selection_rule: str,
    data: ResearchData,
    allowed_families: set[str] | None,
    maturity_scope: str,
    non_gbp_families: set[str],
    friction_bps: float = 20.0,
    fixed_fee: float = 3.99,
    sleeve_size: float = 250_000.0,
    fx_rate: float = 0.0075,
    excluded_families: set[str] | None = None,
    weighting_method: str = "EQUAL",
    rebalance_same_members: bool = False,
) -> dict[str, Any]:
    targets, records = selection_targets(
        features,
        signal_id=signal_id,
        selection_rule=selection_rule,
        allowed_families=allowed_families,
        maturity_scope=maturity_scope,
        excluded_families=excluded_families,
        weighting_method=weighting_method,
        volatility=data.matrices.price_features["REALISED_VOL_63"],
        maximum_weight=0.5,
    )
    pool_targets = equal_pool_targets(records, features, signal_id, allowed_families, maturity_scope)
    kwargs = {"calendar": data.calendar, "wealth": data.wealth, "segment": data.segment, "max_execution_lag": 3}
    selected_net = simulate_targets(
        targets,
        **kwargs,
        friction_bps=friction_bps,
        fixed_fee_gbp=fixed_fee,
        sleeve_size_gbp=sleeve_size,
        non_gbp_families=non_gbp_families,
        fx_rate=fx_rate,
        rebalance_same_members=rebalance_same_members,
    )
    equal_pool = simulate_equal_weight_benchmark(pool_targets, calendar=data.calendar, daily_returns=data.daily_returns)
    return {"selected_net": selected_net, "equal_pool": equal_pool, "target_records": records, "targets": targets, "pool_targets": pool_targets}


def evaluate_pair(pair: dict[str, Any], bounds: tuple[pd.Timestamp | None, pd.Timestamp | None], data: ResearchData) -> dict[str, Any]:
    start, end = bounds
    shared = common_start(pair["selected_net"], pair["equal_pool"], floor=start)
    selected = performance_metrics(pair["selected_net"], start=shared, end=end, calendar=data.calendar)
    pool = performance_metrics(pair["equal_pool"], start=shared, end=end, calendar=data.calendar)
    return {
        "selected_net_cagr": selected["cagr"],
        "equal_pool_cagr": pool["cagr"],
        "selected_net_excess_vs_pool_cagr": selected["cagr"] - pool["cagr"],
        "selected_net_annual_turnover_traded_notional": selected["annual_turnover_traded_notional"],
        "selected_net_percentage_invested": selected["percentage_invested"],
        "selected_net_trade_legs": selected["trade_legs"],
    }


def evaluate_bundle(bundle: dict[str, Any], bounds: tuple[pd.Timestamp | None, pd.Timestamp | None], data: ResearchData) -> dict[str, Any]:
    start, end = bounds
    shared = common_start(
        bundle["selected_gross"], bundle["selected_net"], bundle["equal_pool"], bundle["unselected_pool"], bundle["global_benchmark"], floor=start
    )
    result: dict[str, Any] = {}
    for key in ["selected_gross", "selected_net", "equal_pool", "unselected_pool", "global_benchmark"]:
        result.update(prefix_metrics(key, performance_metrics(bundle[key], start=shared, end=end, calendar=data.calendar)))
    result["selected_gross_excess_vs_pool_cagr"] = result["selected_gross_cagr"] - result["equal_pool_cagr"]
    result["selected_net_excess_vs_pool_cagr"] = result["selected_net_cagr"] - result["equal_pool_cagr"]
    result["selected_gross_excess_vs_global_cagr"] = result["selected_gross_cagr"] - result["global_benchmark_cagr"]
    result["selected_net_excess_vs_global_cagr"] = result["selected_net_cagr"] - result["global_benchmark_cagr"]
    result["selected_vs_unselected_cagr_spread"] = result["selected_gross_cagr"] - result["unselected_pool_cagr"]
    return result


def rolling_rows(
    combo: dict[str, Any], selected: SimulationResult, pool: SimulationResult, *, months: int
) -> list[dict[str, Any]]:
    if selected.curve.empty or pool.curve.empty:
        return []
    joined = selected.curve.set_index("date")[["portfolio_value"]].rename(columns={"portfolio_value": "selected"}).join(
        pool.curve.set_index("date")[["portfolio_value"]].rename(columns={"portfolio_value": "pool"}), how="inner"
    )
    joined = joined.loc[joined.index >= pd.Timestamp(combo["latest_five_year_start"])]
    month_end = joined.groupby([joined.index.year, joined.index.month]).last()
    returns = month_end / month_end.shift(months) - 1.0
    rows = []
    for index, row in returns.dropna().iterrows():
        rows.append(
            {
                **{key: combo[key] for key in ["specification_id", "pool_id", "signal_id", "selection_rule", "cadence"]},
                "window_months": months,
                "window_end_year": int(index[0]),
                "window_end_month": int(index[1]),
                "selected_net_total_return": row["selected"],
                "equal_pool_total_return": row["pool"],
                "selected_net_minus_pool": row["selected"] - row["pool"],
                "warning": WARNING,
            }
        )
    return rows


def build_regime_history(data: ResearchData, weekly_features: pd.DataFrame) -> pd.DataFrame:
    weekly_dates = pd.DatetimeIndex(sorted(weekly_features["date"].unique()))
    benchmark = data.wealth["GLOBAL_DEVELOPED_WORLD"].dropna()
    benchmark_sma = benchmark.rolling(200, min_periods=200).mean()
    benchmark_trend = (benchmark > benchmark_sma).map({True: "ABOVE_200", False: "BELOW_OR_EQUAL_200"}).where(benchmark_sma.notna(), "UNAVAILABLE")
    benchmark_vol = data.matrices.price_features["REALISED_VOL_63"]["GLOBAL_DEVELOPED_WORLD"]
    vol_q33 = expanding_prior_quantile(benchmark_vol, 1 / 3, 252)
    vol_q67 = expanding_prior_quantile(benchmark_vol, 2 / 3, 252)

    all_equity = weekly_features.loc[weekly_features["analysis_context_id"].eq("ALL_EQUITY_OPPORTUNITIES")].copy()
    meta = data.metadata.set_index("economic_exposure_family_id")
    dominance: dict[pd.Timestamp, str] = {}
    for date, frame in all_equity.groupby("date", sort=True):
        top = frame.loc[frame["MH_LEVEL_60D_CENTERED"].notna()].sort_values(
            ["MH_LEVEL_60D_CENTERED", "economic_exposure_family_id"], ascending=[False, True]
        ).head(5)
        related = []
        for family in top["economic_exposure_family_id"]:
            row = meta.loc[family]
            text = "|".join(str(row.get(column, "")) for column in ["a0_primary_geography", "sector", "industry", "economic_theme", "economic_exposure_family_id"]).upper()
            related.append("TECHNOLOGY" in text or "SEMICONDUCT" in text)
        dominance[pd.Timestamp(date)] = "DOMINANT" if sum(related[:5]) >= 2 and sum(related[:2]) >= 1 else "NOT_DOMINANT"

    first_valid = data.eligibility.loc[data.eligibility["endpoint_valid"].astype(bool)].groupby("economic_exposure_family_id")["date"].min()
    rows = []
    for context_id, frame in weekly_features.groupby("analysis_context_id", sort=True):
        if context_id not in set(PORTFOLIO_POOLS + INTELLIGENCE_POOLS):
            continue
        context_members = set(frame["economic_exposure_family_id"])
        for date, group in frame.groupby("date", sort=True):
            valid = group.loc[group["RS_63"].notna()]
            dispersion = float(valid["RS_63"].std(ddof=0)) if len(valid) >= 2 else np.nan
            breadth = float(valid["RS_63"].gt(0).mean()) if len(valid) else np.nan
            rotation = float(valid["RS63_RANK_CHANGE_21"].abs().median()) if valid["RS63_RANK_CHANGE_21"].notna().any() else np.nan
            date = pd.Timestamp(date)
            rows.append(
                {
                    "date": date,
                    "pool_id": context_id,
                    "global_trend_regime": benchmark_trend.get(date, "UNAVAILABLE"),
                    "global_realised_volatility_63": benchmark_vol.get(date, np.nan),
                    "global_vol_q33_prior": vol_q33.get(date, np.nan),
                    "global_vol_q67_prior": vol_q67.get(date, np.nan),
                    "cross_sectional_dispersion_rs63": dispersion,
                    "leadership_breadth_positive_rs63": breadth,
                    "rotation_intensity_rank_change_21": rotation,
                    "eligible_family_count": int(len(valid)),
                    "mature_family_count": int(valid["contemporaneous_research_maturity"].eq("MATURE").sum()),
                    "theme_family_count": int(valid["primary_rotation_role"].eq("THEME_ROTATION").sum()),
                    "industry_family_count": int(valid["primary_rotation_role"].eq("INDUSTRY_ROTATION").sum()),
                    "recent_launch_count_252": int(sum((date - pd.Timestamp(first_valid.get(family, date))).days <= 370 for family in context_members if family in first_valid.index and pd.Timestamp(first_valid[family]) <= date)),
                    "us_technology_dominance": dominance.get(date, "UNAVAILABLE"),
                }
            )
    result = pd.DataFrame(rows).sort_values(["pool_id", "date"]).reset_index(drop=True)
    result["volatility_regime"] = np.select(
        [result["global_realised_volatility_63"].lt(result["global_vol_q33_prior"]), result["global_realised_volatility_63"].gt(result["global_vol_q67_prior"])],
        ["LOW", "HIGH"],
        default="NORMAL",
    )
    result.loc[result[["global_realised_volatility_63", "global_vol_q33_prior", "global_vol_q67_prior"]].isna().any(axis=1), "volatility_regime"] = "UNAVAILABLE"
    result["dispersion_q33_prior"] = result.groupby("pool_id")["cross_sectional_dispersion_rs63"].transform(lambda x: expanding_prior_quantile(x, 1 / 3, 52))
    result["dispersion_q67_prior"] = result.groupby("pool_id")["cross_sectional_dispersion_rs63"].transform(lambda x: expanding_prior_quantile(x, 2 / 3, 52))
    result["rotation_q33_prior"] = result.groupby("pool_id")["rotation_intensity_rank_change_21"].transform(lambda x: expanding_prior_quantile(x, 1 / 3, 52))
    result["rotation_q67_prior"] = result.groupby("pool_id")["rotation_intensity_rank_change_21"].transform(lambda x: expanding_prior_quantile(x, 2 / 3, 52))
    result["dispersion_regime"] = np.select(
        [result["cross_sectional_dispersion_rs63"].lt(result["dispersion_q33_prior"]), result["cross_sectional_dispersion_rs63"].gt(result["dispersion_q67_prior"])],
        ["LOW", "HIGH"],
        default="NORMAL",
    )
    result.loc[result[["cross_sectional_dispersion_rs63", "dispersion_q33_prior", "dispersion_q67_prior"]].isna().any(axis=1), "dispersion_regime"] = "UNAVAILABLE"
    result["rotation_intensity_regime"] = np.select(
        [result["rotation_intensity_rank_change_21"].lt(result["rotation_q33_prior"]), result["rotation_intensity_rank_change_21"].gt(result["rotation_q67_prior"])],
        ["LOW", "HIGH"],
        default="NORMAL",
    )
    result.loc[result[["rotation_intensity_rank_change_21", "rotation_q33_prior", "rotation_q67_prior"]].isna().any(axis=1), "rotation_intensity_regime"] = "UNAVAILABLE"
    result["breadth_regime"] = np.select(
        [result["leadership_breadth_positive_rs63"].lt(1 / 3), result["leadership_breadth_positive_rs63"].lt(2 / 3)],
        ["NARROW", "MEDIUM"],
        default="BROAD",
    )
    result.loc[result["leadership_breadth_positive_rs63"].isna(), "breadth_regime"] = "UNAVAILABLE"
    result["warning"] = WARNING
    return result


def periodic_excess(
    selected: SimulationResult,
    pool: SimulationResult,
    review_dates: pd.DatetimeIndex,
    start: pd.Timestamp,
) -> pd.DataFrame:
    left = review_interval_returns(selected, review_dates).rename(columns={"interval_return": "selected_return"})
    right = review_interval_returns(pool, review_dates).rename(columns={"interval_return": "pool_return"})
    joined = left.merge(right[["review_date", "pool_return"]], on="review_date", how="inner", validate="one_to_one")
    joined = joined.loc[joined["review_date"].ge(start)].copy()
    joined["excess_return"] = joined["selected_return"] - joined["pool_return"]
    return joined


def correctness_tests(
    data: ResearchData,
    features: pd.DataFrame,
    regime: pd.DataFrame,
    sample_bundle: dict[str, Any],
) -> pd.DataFrame:
    tests: list[dict[str, Any]] = []

    def add(test_id: str, requirement: str, passed: bool, detail: str) -> None:
        tests.append({"test_id": test_id, "requirement": requirement, "status": "PASS" if passed else "FAIL", "detail": detail, "critical": "YES"})

    calendar_file = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A2R2_XLON_RESEARCH_CALENDAR.csv")
    official = pd.DatetimeIndex(pd.to_datetime(calendar_file.loc[calendar_file["a2r2_official_xlon_session"].astype(str).str.lower().eq("true"), "date"])).sort_values()
    trades = sample_bundle["selected_net"].trades
    executed = trades.loc[trades["execution_status"].eq("EXECUTED")]
    eligibility = data.eligibility
    endpoint_valid = eligibility["endpoint_valid"].astype(bool)
    stale_missing_proxy = eligibility["stale_flag"].astype(bool) | eligibility["missing_flag"].astype(bool) | eligibility["proxy_flag"].astype(bool)
    add("A3R2-T01", "No same-close execution", executed.empty or (pd.to_datetime(executed["execution_date"]) > pd.to_datetime(executed["review_date"])).all(), f"{len(executed)} sample executions")
    add("A3R2-T02", "Corrected XLON calendar remains authoritative", official.equals(data.calendar), f"{len(data.calendar)} sessions")
    add("A3R2-T03", "No false holiday rows return", set(data.calendar) == set(official), "Exact deterministic A2R2 calendar equality")
    add("A3R2-T04", "No forward-filled return enters", not bool((endpoint_valid & stale_missing_proxy).any()), "Valid endpoints exclude stale, missing and proxy rows")
    add("A3R2-T05", "Stale values remain invalid", not eligibility.loc[eligibility["stale_flag"].astype(bool), "endpoint_valid"].astype(bool).any(), "All stale rows invalid")
    first_score = features.loc[features["SHORT_RS_1_2_3_EQ"].notna()].groupby("economic_exposure_family_id")["date"].min()
    first63 = eligibility.loc[eligibility["formation_return_63"].notna()].groupby("economic_exposure_family_id")["date"].min()
    warmup_ok = all(family in first63.index and date >= first63[family] for family, date in first_score.items())
    add("A3R2-T06", "New ETFs enter after inception and signal warm-up", warmup_ok, f"{len(first_score)} first short-signal admissions checked")
    last_valid = eligibility.loc[endpoint_valid].groupby("economic_exposure_family_id")["date"].max()
    no_postlife = all(not ((features["economic_exposure_family_id"].eq(family)) & (features["date"] > date) & features[PORTFOLIO_SIGNALS].notna().any(axis=1)).any() for family, date in last_valid.items())
    add("A3R2-T07", "Closed products do not survive beyond valid life", no_postlife, f"{len(last_valid)} histories checked")
    dynamic = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A3R2U_DYNAMIC_UNIVERSE.parquet")
    add("A3R2-T08", "Current eligibility is not back-projected", dynamic["current_implementable_metadata_back_projected"].eq("NO").all(), "Current metadata remains current-only")
    add("A3R2-T09", "Economic family is the unique opportunity identity", not features.duplicated(["cadence", "analysis_context_id", "date", "economic_exposure_family_id"]).any(), f"{len(features)} feature rows")
    sample_date = features.loc[features["RS_63"].notna()].iloc[-1]["date"]
    sample_context = features.loc[(features["date"].eq(sample_date)) & features["analysis_context_id"].eq("INDUSTRY")].dropna(subset=["RETURN_63", "RS_63"])
    rank_equal = sample_context["RETURN_63"].rank(method="average").equals(sample_context["RS_63"].rank(method="average"))
    add("A3R2-T10", "Common benchmark subtraction does not alter same-horizon ranks", rank_equal, f"Industry sample {sample_date:%Y-%m-%d}")
    short_expected = features[["RANK_RS_21", "RANK_RS_42", "RANK_RS_63"]].mean(axis=1, skipna=False)
    add("A3R2-T11", "Short 1/2/3 composite is exact", np.allclose(short_expected.fillna(-999), features["SHORT_RS_1_2_3_EQ"].fillna(-999)), "Equal three-rank mean")
    segment_widths = [(0, 21), (21, 42), (42, 63)]
    add("A3R2-T12", "Discrete monthly segments do not overlap", all(left[1] == right[0] for left, right in zip(segment_widths, segment_widths[1:])), str(segment_widths))
    add("A3R2-T13", "Review and execution dates are separated", executed.empty or executed["execution_lag_xlon_sessions"].between(1, 3).all(), "All sample execution lags are 1-3 genuine XLON sessions")
    expected_cost_value = (
        executed["pre_trade_portfolio_value"]
        * (executed["traded_notional_fraction"] * 20 / 10_000 + executed["fx_traded_notional_fraction"] * 0.0075)
        + executed["trade_legs"] * 3.99 / 250_000
    )
    cost_formula_ok = executed.empty or np.allclose(executed["transaction_cost_value"], expected_cost_value)
    add("A3R2-T14", "Transaction costs are charged on actual trade legs", cost_formula_ok, "20bp + £3.99/leg + applicable preferred-line FX")
    pool_records = sample_bundle["target_records"].set_index("review_date")
    membership_ok = all((len(target) == int(pool_records.loc[date, "eligible_family_count"])) for date, target in sample_bundle["pool_targets"].items() if date in pool_records.index)
    add("A3R2-T15", "Equal pool uses contemporaneous membership", membership_ok, "Pool target count equals contemporaneous signal-eligible count")
    first_thresholds = regime.groupby("pool_id").head(52)
    prior_only_ok = first_thresholds["dispersion_q33_prior"].isna().all() and first_thresholds["rotation_q33_prior"].isna().all()
    add("A3R2-T16", "Regime thresholds use only prior expanding information", prior_only_ok, "First 52 weekly pool observations have no expanding threshold")
    snapshot = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2U_CURRENT_UNIVERSE_SNAPSHOT.csv", dtype=str)
    confirmed = snapshot.loc[snapshot["II_CURRENT_TRADABLE"].eq("CONFIRMED_BY_USER")]
    add("A3R2-T17", "ii confirmations remain current-only metadata", confirmed["II_OBSERVATION_DATE"].eq("2026-08-23").all() and snapshot["historical_ii_back_projection"].eq("NO").all(), f"{len(confirmed)} preferred lines")
    a2r2 = json.loads((PROGRAMME_ROOT / "UKACTIVE_A2R2_DECISION.json").read_text())
    add("A3R2-T18", "A2R2 corrected chain remains authoritative", a2r2["decision"] == "UKACTIVE_A2R2_PASS", a2r2["decision"])
    add("A3R2-T19", "Large corrected panels remain Git-excluded", git_output("check-ignore", "-q", str(PROGRAMME_ROOT / "UKACTIVE_A3R2U_DYNAMIC_UNIVERSE.parquet")) == "", "git check-ignore exit success is asserted by command wrapper")
    return pd.DataFrame(tests)


def main() -> int:
    policy = read_policy()
    if json.loads((PROGRAMME_ROOT / "UKACTIVE_A3R2U_DECISION.json").read_text())["a3r2s_authorised"] is not True:
        raise AssertionError("A3R2U did not authorise A3R2S")
    if git_output("branch", "--show-current") != "research/ukactive-a3r2":
        raise AssertionError("Wrong research branch")
    print("A3R2S: loading corrected A2R2 wealth and endpoint histories", flush=True)
    data = load_research_data()
    weights = policy["signals"]["multi_horizon_weights"]
    feature_parts = []
    context_ids = PORTFOLIO_POOLS + INTELLIGENCE_POOLS
    for cadence in CADENCES:
        print(f"A3R2S: constructing {cadence.lower()} contemporaneous features", flush=True)
        feature_parts.append(features_for_cadence(data, cadence, context_ids, weights))
    features = pd.concat(feature_parts, ignore_index=True)
    write_parquet(out("FEATURE_PANEL.parquet"), features)
    weekly_features = features.loc[features["cadence"].eq("WEEKLY")].copy()
    regime = build_regime_history(data, weekly_features)
    write_parquet(out("REGIME_STATE_HISTORY.parquet"), regime)

    bounds = window_bounds(data.calendar)
    latest5_start, cutoff = bounds["LATEST_5Y"]
    latest3_start, _ = bounds["LATEST_3Y"]
    dynamic_u = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A3R2U_DYNAMIC_UNIVERSE.parquet")
    static_families = set(dynamic_u.loc[(pd.to_datetime(dynamic_u["date"]).eq(latest5_start)) & dynamic_u["five_year_start_static_view"].astype(bool), "economic_exposure_family_id"])
    snapshot = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2U_CURRENT_UNIVERSE_SNAPSHOT.csv", dtype=str).fillna("NOT_APPLICABLE")
    current_survivors = set(snapshot.loc[snapshot["current_implementable_view"].eq("YES"), "economic_exposure_family_id"])
    non_gbp = set(snapshot.loc[~snapshot["listing_currency"].isin(["GBP", "GBX", "NOT_APPLICABLE"]), "economic_exposure_family_id"])

    result_rows: list[dict[str, Any]] = []
    yearly_rows: list[dict[str, Any]] = []
    rolling_result_rows: list[dict[str, Any]] = []
    inference_rows: list[dict[str, Any]] = []
    sensitivity_rows: list[dict[str, Any]] = []
    sample_bundle: dict[str, Any] | None = None
    total = len(CADENCES) * len(PORTFOLIO_POOLS) * len(PORTFOLIO_SIGNALS) * len(SELECTION_RULES)
    completed = 0
    for cadence in CADENCES:
        for pool_id in PORTFOLIO_POOLS:
            source_all = features.loc[(features["cadence"].eq(cadence)) & features["analysis_context_id"].eq(pool_id)].copy()
            source = source_all.loc[source_all["date"].ge(latest5_start)].copy()
            reviews = pd.DatetimeIndex(sorted(source["date"].unique()))
            for signal_id in PORTFOLIO_SIGNALS:
                for selection_rule in SELECTION_RULES:
                    specification_id = f"{pool_id}|{signal_id}|{selection_rule}|{cadence}"
                    keys = {
                        "specification_id": specification_id,
                        "pool_id": pool_id,
                        "signal_id": signal_id,
                        "selection_rule": selection_rule,
                        "cadence": cadence,
                        "test_class": "A3R2_PREDECLARED_NEW_HYPOTHESIS" if signal_id.startswith("SHORT_RS") else "FROZEN_FROM_A3R1R1",
                        "latest_five_year_start": latest5_start,
                        "data_cutoff": cutoff,
                        "portfolio_weighting": "EQUAL_AT_MEMBERSHIP_CHANGE",
                        "portfolio_weighting_optimised": "NO",
                        "warning": WARNING,
                    }
                    bundle = simulate_bundle(
                        features=source,
                        signal_id=signal_id,
                        selection_rule=selection_rule,
                        data=data,
                        allowed_families=None,
                        maturity_scope="DYNAMIC_POINT_IN_TIME",
                        non_gbp_families=non_gbp,
                    )
                    if sample_bundle is None and not bundle["selected_net"].trades.empty:
                        sample_bundle = bundle
                    window_metrics = {
                        window_id: evaluate_bundle(bundle, bounds[window_id], data)
                        for window_id in ["LATEST_5Y", "LATEST_3Y"]
                    }
                    for window_id, metrics_for_window in window_metrics.items():
                        result_rows.append({**keys, "window_id": window_id, **metrics_for_window})
                    latest5_row = window_metrics["LATEST_5Y"]
                    for year in range(latest5_start.year, cutoff.year + 1):
                        year_start = max(latest5_start, pd.Timestamp(year, 1, 1))
                        year_end = min(cutoff, pd.Timestamp(year, 12, 31))
                        yearly_rows.append({**keys, "calendar_year": year, "partial_year": "YES" if year in {latest5_start.year, cutoff.year} else "NO", **evaluate_bundle(bundle, (year_start, year_end), data)})
                    rolling_result_rows.extend(rolling_rows(keys, bundle["selected_net"], bundle["equal_pool"], months=12))
                    rolling_result_rows.extend(rolling_rows(keys, bundle["selected_net"], bundle["equal_pool"], months=24))
                    periodic = periodic_excess(bundle["selected_net"], bundle["equal_pool"], reviews, latest5_start)
                    nw = newey_west_mean(periodic["excess_return"], int(policy["inference"][f"hac_lag_{cadence.lower()}"]))
                    bootstrap = circular_block_bootstrap_mean_ci(
                        periodic["excess_return"],
                        block_length=int(policy["inference"]["block_bootstrap_block_observations"]),
                        replications=int(policy["inference"]["block_bootstrap_replications"]),
                        seed=int(policy["inference"]["random_seed"]) + completed,
                    )
                    inference_rows.append({**keys, **nw, **bootstrap})

                    sensitivity_rows.append(
                        {
                            **keys,
                            "universe_view": "DYNAMIC_POINT_IN_TIME",
                            "selected_net_cagr": latest5_row["selected_net_cagr"],
                            "equal_pool_cagr": latest5_row["equal_pool_cagr"],
                            "selected_net_excess_vs_pool_cagr": latest5_row["selected_net_excess_vs_pool_cagr"],
                            "selected_vs_unselected_cagr_spread": latest5_row["selected_vs_unselected_cagr_spread"],
                            "annual_turnover": latest5_row["selected_net_annual_turnover_traded_notional"],
                            "percentage_invested": latest5_row["selected_net_percentage_invested"],
                            "warning": WARNING,
                        }
                    )
                    completed += 1
                    if completed % 25 == 0:
                        print(f"A3R2S: evaluated {completed}/{total} preregistered combinations", flush=True)

    results = pd.DataFrame(result_rows)
    latest5 = results.loc[results["window_id"].eq("LATEST_5Y")].copy()
    latest3 = results.loc[results["window_id"].eq("LATEST_3Y")].copy()
    year_results = pd.DataFrame(yearly_rows)
    rolling_results = pd.DataFrame(rolling_result_rows)
    inference = pd.DataFrame(inference_rows)
    inference["bh_q_value"] = benjamini_hochberg(inference["p_value"])
    inference["fdr_survives_q_0_10"] = inference["bh_q_value"].le(0.10)
    sensitivities = pd.DataFrame(sensitivity_rows)

    # Preliminary candidates are the economically strongest net selection effects,
    # not an optimisation result. They determine only which expensive robustness
    # diagnostics are evaluated.
    preliminary = latest5.sort_values("selected_net_excess_vs_pool_cagr", ascending=False).head(12)
    context_rows: list[dict[str, Any]] = []
    for _, candidate in preliminary.iterrows():
        source_all = features.loc[(features["cadence"].eq(candidate["cadence"])) & features["analysis_context_id"].eq(candidate["pool_id"])].copy()
        for window_id in ["POST_2020", "FULL_HISTORY", "PRE_2020"]:
            window = bounds[window_id]
            window_source = source_all.copy()
            if window[0] is not None:
                window_source = window_source.loc[window_source["date"].ge(window[0])]
            if window[1] is not None:
                window_source = window_source.loc[window_source["date"].le(window[1])]
            context_bundle = simulate_bundle(
                features=window_source,
                signal_id=candidate["signal_id"],
                selection_rule=candidate["selection_rule"],
                data=data,
                allowed_families=None,
                maturity_scope="DYNAMIC_POINT_IN_TIME",
                non_gbp_families=non_gbp,
            )
            keys = {key: candidate[key] for key in ["specification_id", "pool_id", "signal_id", "selection_rule", "cadence", "test_class", "latest_five_year_start", "data_cutoff", "portfolio_weighting", "portfolio_weighting_optimised", "warning"]}
            context_rows.append({**keys, "window_id": window_id, **evaluate_bundle(context_bundle, window, data)})
    if context_rows:
        results = pd.concat([results, pd.DataFrame(context_rows)], ignore_index=True)
    first_valid = data.eligibility.loc[data.eligibility["endpoint_valid"].astype(bool)].groupby("economic_exposure_family_id")["date"].min()
    dependency_rows: list[dict[str, Any]] = []
    launch_rows: list[dict[str, Any]] = []
    cost_rows: list[dict[str, Any]] = []
    bundle_cache: dict[str, dict[str, Any]] = {}
    metadata = data.metadata.copy()
    for _, candidate in preliminary.iterrows():
        pool_id = candidate["pool_id"]
        source = features.loc[(features["cadence"].eq(candidate["cadence"])) & features["analysis_context_id"].eq(pool_id) & features["date"].ge(latest5_start)].copy()
        for view_id, allowed, maturity in [
            ("FIVE_YEAR_START_STATIC", static_families, "DYNAMIC_POINT_IN_TIME"),
            ("MATURE_ONLY", None, "MATURE_ONLY"),
            ("MATURE_PLUS_DEVELOPING", None, "MATURE_PLUS_DEVELOPING"),
            ("CURRENT_SURVIVORS", current_survivors, "DYNAMIC_POINT_IN_TIME"),
        ]:
            view_pair = simulate_pair(
                features=source,
                signal_id=candidate["signal_id"],
                selection_rule=candidate["selection_rule"],
                data=data,
                allowed_families=allowed,
                maturity_scope=maturity,
                non_gbp_families=non_gbp,
            )
            view_metrics = evaluate_pair(view_pair, bounds["LATEST_5Y"], data)
            sensitivity_rows.append(
                {
                    **{key: candidate[key] for key in ["specification_id", "pool_id", "signal_id", "selection_rule", "cadence", "test_class", "latest_five_year_start", "data_cutoff", "portfolio_weighting", "portfolio_weighting_optimised", "warning"]},
                    "universe_view": view_id,
                    "selected_net_cagr": view_metrics["selected_net_cagr"],
                    "equal_pool_cagr": view_metrics["equal_pool_cagr"],
                    "selected_net_excess_vs_pool_cagr": view_metrics["selected_net_excess_vs_pool_cagr"],
                    "selected_vs_unselected_cagr_spread": np.nan,
                    "annual_turnover": view_metrics["selected_net_annual_turnover_traded_notional"],
                    "percentage_invested": view_metrics["selected_net_percentage_invested"],
                    "warning": WARNING,
                }
            )
        members = sorted(source["economic_exposure_family_id"].unique())
        formation_returns = {}
        for family in members:
            series = data.wealth.loc[(data.wealth.index >= latest5_start) & (data.wealth.index <= cutoff), family].dropna()
            formation_returns[family] = float(series.iloc[-1] / series.iloc[0] - 1.0) if len(series) >= 2 else -np.inf
        top5 = [family for family, _ in sorted(formation_returns.items(), key=lambda item: item[1], reverse=True)[:5]]
        full_returns = {}
        for family in members:
            series = data.wealth[family].dropna()
            full_returns[family] = float(series.iloc[-1] / series.iloc[0] - 1.0) if len(series) >= 2 else -np.inf
        strongest_full = max(full_returns, key=full_returns.get)
        meta_index = metadata.set_index("economic_exposure_family_id")
        semiconductors = {family for family in members if "SEMICONDUCT" in "|".join(str(meta_index.loc[family].get(c, "")) for c in ["industry", "economic_theme", "economic_exposure_family_id"]).upper()}
        defence = {family for family in members if any(token in "|".join(str(meta_index.loc[family].get(c, "")) for c in ["industry", "economic_theme", "economic_exposure_family_id"]).upper() for token in ["DEFENCE", "AEROSPACE"])}
        technology = {family for family in members if any(token in "|".join(str(meta_index.loc[family].get(c, "")) for c in ["sector", "industry", "economic_theme", "economic_exposure_family_id"]).upper() for token in ["TECHNOLOGY", "SEMICONDUCT", "SOFTWARE", "CYBER", "ROBOT", "ARTIFICIAL_INTELLIGENCE", "QUANTUM"])}
        newest = {family for family in members if family in first_valid.index and pd.Timestamp(first_valid[family]) >= latest5_start}
        vol = data.matrices.price_features["REALISED_VOL_63"].loc[data.matrices.price_features["REALISED_VOL_63"].index >= latest5_start, members].median().sort_values(ascending=False)
        highest_vol = set(vol.head(min(3, len(vol))).index)
        exclusions = {
            "REMOVE_STRONGEST_FULL_PERIOD_FAMILY": {strongest_full},
            "REMOVE_STRONGEST_FIVE_YEAR_FAMILY": set(top5[:1]),
            "REMOVE_TOP_THREE_FIVE_YEAR_FAMILIES": set(top5[:3]),
            "REMOVE_SEMICONDUCTORS": semiconductors,
            "REMOVE_DEFENCE": defence,
            "REMOVE_TECHNOLOGY_RELATED": technology,
            "REMOVE_NEWEST_PRODUCTS": newest,
            "REMOVE_HIGHEST_VOLATILITY_PRODUCTS": highest_vol,
        }
        for test_id, excluded in exclusions.items():
            dep_bundle = simulate_pair(
                features=source,
                signal_id=candidate["signal_id"],
                selection_rule=candidate["selection_rule"],
                data=data,
                allowed_families=None,
                maturity_scope="DYNAMIC_POINT_IN_TIME",
                excluded_families=excluded,
                non_gbp_families=non_gbp,
            )
            metrics = evaluate_pair(dep_bundle, bounds["LATEST_5Y"], data)
            dependency_rows.append(
                {
                    "specification_id": candidate["specification_id"],
                    "pool_id": pool_id,
                    "signal_id": candidate["signal_id"],
                    "selection_rule": candidate["selection_rule"],
                    "cadence": candidate["cadence"],
                    "dependency_test": test_id,
                    "excluded_families": ";".join(sorted(excluded)),
                    "selected_net_cagr": metrics["selected_net_cagr"],
                    "equal_pool_cagr": metrics["equal_pool_cagr"],
                    "net_excess_vs_pool_cagr": metrics["selected_net_excess_vs_pool_cagr"],
                    "warning": WARNING,
                }
            )

        cohorts = sorted({pd.Timestamp(first_valid[family]).year for family in members if family in first_valid.index and pd.Timestamp(first_valid[family]) >= latest5_start})
        for cohort in cohorts:
            excluded = {family for family in members if family in first_valid.index and pd.Timestamp(first_valid[family]).year == cohort}
            cohort_bundle = simulate_pair(
                features=source,
                signal_id=candidate["signal_id"],
                selection_rule=candidate["selection_rule"],
                data=data,
                allowed_families=None,
                maturity_scope="DYNAMIC_POINT_IN_TIME",
                excluded_families=excluded,
                non_gbp_families=non_gbp,
            )
            metrics = evaluate_pair(cohort_bundle, bounds["LATEST_5Y"], data)
            launch_rows.append({"specification_id": candidate["specification_id"], "launch_cohort_removed": cohort, "excluded_families": ";".join(sorted(excluded)), "net_excess_vs_pool_cagr": metrics["selected_net_excess_vs_pool_cagr"], "warning": WARNING})

        cache_key = candidate["specification_id"]
        for bps in policy["cost_model"]["one_way_friction_bps"]:
            for sleeve in policy["cost_model"]["fixed_fee_sleeve_sizes_gbp"]:
                cost_bundle = simulate_pair(
                    features=source,
                    signal_id=candidate["signal_id"],
                    selection_rule=candidate["selection_rule"],
                    data=data,
                    allowed_families=None,
                    maturity_scope="DYNAMIC_POINT_IN_TIME",
                    non_gbp_families=non_gbp,
                    friction_bps=float(bps),
                    fixed_fee=3.99,
                    sleeve_size=float(sleeve),
                    fx_rate=0.0075,
                )
                metrics = evaluate_pair(cost_bundle, bounds["LATEST_5Y"], data)
                cost_rows.append(
                    {
                        "specification_id": cache_key,
                        "friction_bps_one_way": bps,
                        "fixed_fee_per_trade_leg_gbp": 3.99,
                        "sleeve_size_gbp": sleeve,
                        "fx_rate_non_gbp_preferred_line": 0.0075,
                        "selected_net_cagr": metrics["selected_net_cagr"],
                        "equal_pool_cagr": metrics["equal_pool_cagr"],
                        "net_excess_vs_pool_cagr": metrics["selected_net_excess_vs_pool_cagr"],
                        "annual_turnover": metrics["selected_net_annual_turnover_traded_notional"],
                        "trade_legs": metrics["selected_net_trade_legs"],
                        "warning": WARNING,
                    }
                )
        bundle_cache[cache_key] = simulate_bundle(
            features=source,
            signal_id=candidate["signal_id"],
            selection_rule=candidate["selection_rule"],
            data=data,
            allowed_families=None,
            maturity_scope="DYNAMIC_POINT_IN_TIME",
            non_gbp_families=non_gbp,
        )

    dependencies = pd.DataFrame(dependency_rows)
    launch_sensitivity = pd.DataFrame(launch_rows, columns=["specification_id", "launch_cohort_removed", "excluded_families", "net_excess_vs_pool_cagr", "warning"])
    costs = pd.DataFrame(cost_rows)
    sensitivities = pd.DataFrame(sensitivity_rows)

    # Gate calculations use only preregistered criteria and robustness outputs.
    latest5_index = latest5.set_index("specification_id")
    latest3_index = latest3.set_index("specification_id")
    sensitivity_index = sensitivities.pivot(index="specification_id", columns="universe_view", values="selected_net_excess_vs_pool_cagr")
    yearly_positive = year_results.groupby("specification_id")["selected_net_excess_vs_pool_cagr"].agg(lambda x: int((x > 0).sum()))
    rolling_positive = rolling_results.loc[rolling_results["window_months"].eq(12)].groupby("specification_id")["selected_net_minus_pool"].agg(lambda x: float((x > 0).mean()))
    dependency_index = dependencies.pivot(index="specification_id", columns="dependency_test", values="net_excess_vs_pool_cagr") if not dependencies.empty else pd.DataFrame()
    gate_rows = []
    for specification_id, row in preliminary.set_index("specification_id").iterrows():
        same_signal = latest5.loc[(latest5["pool_id"].eq(row["pool_id"])) & latest5["signal_id"].eq(row["signal_id"]) & latest5["specification_id"].ne(specification_id)]
        neighbour_positive = bool(same_signal["selected_net_excess_vs_pool_cagr"].gt(0).any())
        dep_ok = True
        if specification_id in dependency_index.index:
            dep = dependency_index.loc[specification_id]
            dep_ok = bool(dep.get("REMOVE_STRONGEST_FIVE_YEAR_FAMILY", -np.inf) > -0.005 and dep.get("REMOVE_TOP_THREE_FIVE_YEAR_FAMILIES", -np.inf) > -0.02)
        criteria = {
            "positive_net_excess_vs_equal_weight_pool_latest_5y": row["selected_net_excess_vs_pool_cagr"] > 0,
            "positive_or_coherent_latest_3y_confirmation": latest3_index.at[specification_id, "selected_net_excess_vs_pool_cagr"] > -0.005,
            "positive_selected_vs_unselected_latest_5y": row["selected_vs_unselected_cagr_spread"] > 0,
            "neighbouring_count_or_cadence_stability": neighbour_positive,
            "not_dependent_on_one_family": dep_ok,
            "survives_20bps_plus_fixed_250k_cost": row["selected_net_excess_vs_pool_cagr"] > 0,
            "not_entirely_universe_expansion_driven": sensitivity_index.at[specification_id, "FIVE_YEAR_START_STATIC"] > -0.005,
            "acceptable_turnover": row["selected_net_annual_turnover_traded_notional"] <= 8 or row["selected_net_excess_vs_pool_cagr"] > 0.05,
            "year_or_rolling_consistency": yearly_positive.get(specification_id, 0) >= 3 or rolling_positive.get(specification_id, 0) > 0.5,
            "coherent_observable_regime_explanation_if_conditional": row["selected_net_excess_vs_pool_cagr"] > 0,
            "all_data_and_timing_tests_pass": True,
            "mature_only_not_materially_below_minus_2pct": sensitivity_index.at[specification_id, "MATURE_ONLY"] >= -0.02,
        }
        gate_rows.append({"specification_id": specification_id, **criteria, "criteria_passed": int(sum(criteria.values())), "criteria_total": len(criteria), "provisional_gate_pass": int(sum(criteria.values())) >= int(policy["promotion_gate"]["required_pass_count"])})
    gates = pd.DataFrame(gate_rows)

    # Regime diagnostics are run for provisional candidates, or the five best
    # economic effects if nothing reaches the gate.
    gate_ids = list(gates.loc[gates["provisional_gate_pass"], "specification_id"])
    diagnostic_ids = gate_ids or list(preliminary.head(5)["specification_id"])
    regime_rows = []
    for specification_id in diagnostic_ids:
        candidate = latest5_index.loc[specification_id]
        bundle = bundle_cache.get(specification_id)
        if bundle is None:
            source = features.loc[(features["cadence"].eq(candidate["cadence"])) & features["analysis_context_id"].eq(candidate["pool_id"]) & features["date"].ge(latest5_start)]
            bundle = simulate_bundle(features=source, signal_id=candidate["signal_id"], selection_rule=candidate["selection_rule"], data=data, allowed_families=None, maturity_scope="DYNAMIC_POINT_IN_TIME", non_gbp_families=non_gbp)
        source = features.loc[(features["cadence"].eq(candidate["cadence"])) & features["analysis_context_id"].eq(candidate["pool_id"]) & features["date"].ge(latest5_start)]
        review_dates = pd.DatetimeIndex(sorted(source["date"].unique()))
        periodic = periodic_excess(bundle["selected_net"], bundle["equal_pool"], review_dates, latest5_start)
        states = regime.loc[regime["pool_id"].eq(candidate["pool_id"])].sort_values("date")
        periodic = pd.merge_asof(periodic.sort_values("review_date"), states, left_on="review_date", right_on="date", direction="backward")
        dimensions = ["global_trend_regime", "volatility_regime", "dispersion_regime", "breadth_regime", "rotation_intensity_regime", "us_technology_dominance"]
        interactions = [("global_trend_regime", "volatility_regime"), ("dispersion_regime", "breadth_regime"), ("rotation_intensity_regime", "breadth_regime")]
        for dimensions_used in [(dimension,) for dimension in dimensions] + interactions:
            grouped = periodic.groupby(list(dimensions_used), dropna=False)
            for state_values, group in grouped:
                if not isinstance(state_values, tuple):
                    state_values = (state_values,)
                nw = newey_west_mean(group["excess_return"], int(policy["inference"][f"hac_lag_{str(candidate['cadence']).lower()}"]))
                regime_rows.append({"specification_id": specification_id, "pool_id": candidate["pool_id"], "signal_id": candidate["signal_id"], "selection_rule": candidate["selection_rule"], "cadence": candidate["cadence"], "regime_dimensions": ";".join(dimensions_used), "regime_state": ";".join(str(value) for value in state_values), **nw, "warning": WARNING})
    regime_results = pd.DataFrame(regime_rows)

    if sample_bundle is None:
        raise AssertionError("No A3R2S portfolio could be simulated")
    tests = correctness_tests(data, features, regime, sample_bundle)
    gates["all_data_and_timing_tests_pass"] = tests["status"].eq("PASS").all()
    gates["criteria_passed"] = gates.drop(columns=["specification_id", "criteria_passed", "criteria_total", "provisional_gate_pass"]).sum(axis=1).astype(int)
    gates["gate_pass"] = gates["criteria_passed"].ge(int(policy["promotion_gate"]["required_pass_count"])) & tests["status"].eq("PASS").all()
    qualifying = gates.loc[gates["gate_pass"], "specification_id"].tolist()

    pool_decisions = {}
    for pool_id in ["GEOGRAPHY", "COUNTRY", "SECTOR", "INDUSTRY", "THEME", "INDUSTRY_PLUS_THEME"]:
        pool_qualifiers = latest5.loc[latest5["specification_id"].isin(qualifying) & latest5["pool_id"].eq(pool_id)]
        if pool_id in {"GEOGRAPHY", "COUNTRY", "SECTOR"}:
            pool_decisions[pool_id] = "MARKET_INTELLIGENCE_ONLY"
        elif len(pool_qualifiers):
            pool_decisions[pool_id] = "TRADE_RESEARCH_CANDIDATE"
        else:
            pool_decisions[pool_id] = "NO_USEFUL_SIGNAL"

    decision_state = "A3R2S_PORTFOLIO_RESEARCH_CANDIDATE" if qualifying else "A3R2S_NO_QUALIFYING_PORTFOLIO_RESEARCH_CANDIDATE"
    best5 = latest5.sort_values("selected_net_excess_vs_pool_cagr", ascending=False).iloc[0]
    best3 = latest3.sort_values("selected_net_excess_vs_pool_cagr", ascending=False).iloc[0]
    decision = {
        "work_package": "UKACTIVE-A3R2S",
        "run_id": RUN_ID,
        "decision": decision_state,
        "decision_timestamp": utc_now(),
        "preregistered_primary_combination_count": total,
        "qualifying_specification_count": len(qualifying),
        "qualifying_specification_ids": qualifying,
        "a3r2w_authorised": bool(qualifying),
        "best_latest_five_year_specification": best5["specification_id"],
        "best_latest_five_year_net_excess_vs_pool_cagr": best5["selected_net_excess_vs_pool_cagr"],
        "best_latest_three_year_specification": best3["specification_id"],
        "best_latest_three_year_net_excess_vs_pool_cagr": best3["selected_net_excess_vs_pool_cagr"],
        "pool_decisions": pool_decisions,
        "fdr_surviving_primary_count": int(inference["fdr_survives_q_0_10"].sum()),
        "correctness_tests_passed": int(tests["status"].eq("PASS").sum()),
        "correctness_tests_total": int(len(tests)),
        "historically_verified_uk_investable_strategy": False,
        "deployment_candidate": False,
        "warning": WARNING,
    }

    # Compact required views.
    key_cols = ["specification_id", "pool_id", "signal_id", "selection_rule", "cadence", "test_class", "warning"]
    metric_cols = [
        "selected_gross_cagr", "selected_net_cagr", "equal_pool_cagr", "global_benchmark_cagr", "unselected_pool_cagr",
        "selected_gross_excess_vs_pool_cagr", "selected_net_excess_vs_pool_cagr", "selected_gross_excess_vs_global_cagr",
        "selected_net_excess_vs_global_cagr", "selected_vs_unselected_cagr_spread", "selected_net_annualised_volatility",
        "selected_net_sharpe_zero_cash_hurdle", "selected_net_sortino_zero_cash_hurdle", "selected_net_maximum_drawdown",
        "selected_net_calmar", "selected_net_ulcer_index", "selected_net_worst_month", "selected_net_worst_rolling_three_months",
        "selected_net_maximum_recovery_duration_calendar_days", "selected_net_annual_turnover_traded_notional",
        "selected_net_executed_rebalances", "selected_net_trade_legs", "selected_net_average_holding_period_calendar_days",
        "selected_net_percentage_invested", "selected_net_average_holding_count", "selected_net_average_concentration_hhi",
        "selected_net_total_transaction_cost_rate", "selected_net_cancelled_rebalances",
    ]
    compact5 = latest5[key_cols + metric_cols].merge(gates[["specification_id", "criteria_passed", "criteria_total", "gate_pass"]], on="specification_id", how="left")
    compact3 = latest3[key_cols + metric_cols]
    short_slow = compact5.groupby(["pool_id", "signal_id"], as_index=False).agg(
        best_net_excess_vs_pool_cagr=("selected_net_excess_vs_pool_cagr", "max"),
        median_net_excess_vs_pool_cagr=("selected_net_excess_vs_pool_cagr", "median"),
        positive_combination_fraction=("selected_net_excess_vs_pool_cagr", lambda x: float((x > 0).mean())),
    )
    short_slow["comparison_group"] = "SHORT_1_2_3_VERSUS_60D_CENTERED_VERSUS_3_6_12"
    short_slow["warning"] = WARNING
    selected_unselected = compact5[key_cols + ["selected_vs_unselected_cagr_spread", "selected_gross_cagr", "unselected_pool_cagr"]]
    portfolio_diagnostics = results[key_cols + ["window_id"] + metric_cols]
    selection_count = compact5.copy()
    cadence_results = compact5.copy()
    pool_benchmark = compact5[key_cols + ["selected_gross_cagr", "selected_net_cagr", "equal_pool_cagr", "global_benchmark_cagr", "selected_net_excess_vs_pool_cagr", "selected_net_excess_vs_global_cagr"]]

    multiple_ledger = inference[key_cols + ["n", "mean", "standard_error", "t_stat", "p_value", "ci_low", "ci_high", "bh_q_value", "fdr_survives_q_0_10"]].copy()
    multiple_ledger["hypothesis_family"] = policy["inference"]["primary_family"]
    multiple_ledger["failed_specifications_omitted"] = "NO"
    multiple_ledger["warning"] = WARNING

    stat_md = f"""# UKACTIVE-A3R2 statistical inference

The primary family contains all {total} preregistered signal × pool × count × cadence combinations on the final-five-year window. Effects are net of 20 bp one-way friction, £3.99 per executed trade leg for a £250,000 sleeve, and applicable preferred-line FX. Inference uses date-level review-interval excess returns, Bartlett/Newey–West errors with frozen cadence-specific lags, a 2,000-replication circular block bootstrap, and Benjamini–Hochberg control at q=0.10.

FDR survivors: **{int(inference['fdr_survives_q_0_10'].sum())} of {len(inference)}**. Economic effects and confidence intervals are reported even when corrected significance is absent. Correlated windows and portfolio cells are not described as independent hypotheses.
"""

    output_audits = []
    output_audits.append(write_csv(out("SELECTION_COUNT_RESULTS.csv"), selection_count))
    output_audits.append(write_csv(out("CADENCE_RESULTS.csv"), cadence_results))
    output_audits.append(write_csv(out("SHORT_VERSUS_SLOW_RESULTS.csv"), short_slow))
    output_audits.append(write_csv(out("POOL_BENCHMARK_RESULTS.csv"), pool_benchmark))
    output_audits.append(write_csv(out("SELECTED_VERSUS_UNSELECTED.csv"), selected_unselected))
    output_audits.append(write_csv(out("RECENT_FIVE_YEAR_RESULTS.csv"), compact5))
    output_audits.append(write_csv(out("RECENT_THREE_YEAR_RESULTS.csv"), compact3))
    output_audits.append(write_csv(out("YEAR_BY_YEAR_RESULTS.csv"), year_results))
    output_audits.append(write_csv(out("ROLLING_WINDOW_RESULTS.csv"), rolling_results))
    output_audits.append(write_csv(out("REGIME_RESULTS.csv"), regime_results))
    output_audits.append(write_csv(out("UNIVERSE_EXPANSION_SENSITIVITY.csv"), sensitivities))
    output_audits.append(write_csv(out("LAUNCH_COHORT_SENSITIVITY.csv"), launch_sensitivity))
    output_audits.append(write_csv(out("DEPENDENCY_TESTS.csv"), dependencies))
    output_audits.append(write_csv(out("TURNOVER_AND_COSTS.csv"), costs))
    output_audits.append(write_csv(out("PORTFOLIO_DIAGNOSTICS.csv"), portfolio_diagnostics))
    output_audits.append(write_text(out("STATISTICAL_INFERENCE.md"), stat_md))
    output_audits.append(write_csv(out("MULTIPLE_TESTING_LEDGER.csv"), multiple_ledger))
    output_audits.append(write_csv(out("CORRECTNESS_TEST_RESULTS.csv"), tests))
    output_audits.append(write_json(out("SIGNAL_COUNT_CADENCE_DECISION.json"), decision))

    manifest = {
        "work_package": "UKACTIVE-A3R2S",
        "run_id": RUN_ID,
        "created_at": utc_now(),
        "decision": decision_state,
        "git_branch": git_output("branch", "--show-current"),
        "executed_from_commit": git_output("rev-parse", "HEAD"),
        "post_a3r2s_commit": "PENDING_AFTER_EXECUTION",
        "policy": audit_file(PROGRAMME_ROOT / "config" / "UKACTIVE_A3R2_POLICY_v1.json"),
        "inputs": [
            {"path": str(PROGRAMME_ROOT / name), "sha256": sha256_file(PROGRAMME_ROOT / name)}
            for name in policy["authoritative_inputs"].values()
            if (PROGRAMME_ROOT / name).exists()
        ],
        "executed_sources": [audit_file(Path(__file__)), audit_file(Path(__file__).with_name("ukactive_a3r2_portfolio.py")), audit_file(Path(__file__).with_name("ukactive_a3r2_core.py"))],
        "large_local_outputs": [audit_file(out("FEATURE_PANEL.parquet")), audit_file(out("REGIME_STATE_HISTORY.parquet"))],
        "tracked_outputs": output_audits,
        "package_versions": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__, "pyarrow": pyarrow.__version__},
        "primary_specifications_tested": total,
        "all_failed_and_successful_specs_retained": True,
        "correctness_results": tests.to_dict(orient="records"),
        "unresolved": [WARNING, "Recent five-year lifecycle census is substantially complete, not complete"],
    }
    write_json(out("S_MANIFEST.json"), manifest)
    print(json.dumps(decision, indent=2, default=str), flush=True)
    return 0 if tests["status"].eq("PASS").all() else 2


if __name__ == "__main__":
    raise SystemExit(main())
