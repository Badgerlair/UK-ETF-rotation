"""Query the deterministic UKACTIVE leadership panel.

Historical requests resolve to the last frozen weekly XLON observation at or
before the requested date.  No future family, current ii metadata, price, or
return is made available to a genuinely historical query.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
POOL_MAP = {
    "geography": "GEOGRAPHY",
    "country": "COUNTRY",
    "sector": "SECTOR",
    "industry": "INDUSTRY",
    "theme": "THEME",
    "industry_theme": "INDUSTRY_PLUS_THEME",
    "all": "ALL_EQUITY_OPPORTUNITIES",
}
ROLE_POOL = {
    "BROAD_GEOGRAPHY_ROTATION": "GEOGRAPHY",
    "COUNTRY_ROTATION": "COUNTRY",
    "SECTOR_ROTATION": "SECTOR",
    "INDUSTRY_ROTATION": "INDUSTRY",
    "THEME_ROTATION": "THEME",
}
INTELLIGENCE = {
    "GEOGRAPHY": "MARKET_INTELLIGENCE_ONLY",
    "COUNTRY": "MARKET_INTELLIGENCE_ONLY",
    "SECTOR": "MARKET_INTELLIGENCE_ONLY",
    "ALL_EQUITY_OPPORTUNITIES": "MARKET_INTELLIGENCE_ONLY",
    "INDUSTRY": "TRADE_RESEARCH_CANDIDATE",
    "THEME": "TRADE_RESEARCH_CANDIDATE",
    "INDUSTRY_PLUS_THEME": "TRADE_RESEARCH_CANDIDATE",
}
DEFAULT_SORT = "short_1_2_3_composite"


def _read_parquet(name: str) -> pd.DataFrame:
    frame = pd.read_parquet(PROGRAMME_ROOT / name)
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"])
    return frame


def weekly_history() -> pd.DataFrame:
    frame = _read_parquet("UKACTIVE_A3R2_FEATURE_PANEL.parquet")
    frame = frame.loc[frame["cadence"].eq("WEEKLY") & frame["analysis_context_id"].isin(POOL_MAP.values())].copy()
    frame = frame.sort_values(["analysis_context_id", "economic_exposure_family_id", "date"])
    group = frame.groupby(["analysis_context_id", "economic_exposure_family_id"], sort=False)
    frame["one_week_rank_change"] = group["SHORT_RS_1_2_3_EQ"].diff(1)
    frame["one_month_rank_change"] = group["SHORT_RS_1_2_3_EQ"].diff(4)
    prior_state = group["ROTATION_STATE"].shift(1).fillna("")
    current_state = frame["ROTATION_STATE"].fillna("")
    frame["state_transition"] = np.where(
        current_state.eq(""),
        "NOT_AVAILABLE",
        np.where(prior_state.eq(""), "INITIAL->" + current_state, prior_state + "->" + current_state),
    )
    state_change = current_state.ne(prior_state)
    state_run = state_change.groupby([frame["analysis_context_id"], frame["economic_exposure_family_id"]]).cumsum()
    frame["leadership_duration_weeks"] = (
        frame.groupby(["analysis_context_id", "economic_exposure_family_id", state_run], sort=False).cumcount() + 1
    ).where(current_state.ne(""), 0)
    frame["pairwise_rank"] = frame.groupby(["analysis_context_id", "date"])["PAIRWISE_MAJORITY_5H"].rank(method="min", ascending=False)
    return frame


def available_dates() -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(weekly_history()["date"].unique()))


def resolve_asof(asof: str | pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
    dates = available_dates()
    requested = dates[-1] if str(asof).lower() == "latest" else pd.Timestamp(asof).normalize()
    eligible = dates[dates <= requested]
    if len(eligible) == 0:
        raise ValueError(f"No frozen weekly observation exists on or before {requested.date()}")
    return requested, pd.Timestamp(eligible[-1])


def _canonical_context(universe: pd.DataFrame) -> pd.Series:
    return universe["primary_rotation_role"].map(ROLE_POOL).fillna("NOT_QUERYABLE")


def build_snapshot(asof: str | pd.Timestamp = "latest", pool: str | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    requested, resolved = resolve_asof(asof)
    history = weekly_history()
    universe = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2U_CURRENT_UNIVERSE_SNAPSHOT.csv")
    universe["first_valid_date"] = pd.to_datetime(universe["first_valid_date"], errors="coerce")
    universe["canonical_query_pool"] = _canonical_context(universe)
    current_cutoff = history["date"].max()
    requested_pool = POOL_MAP.get(pool, pool.upper() if isinstance(pool, str) else None)

    if requested_pool:
        selected = history.loc[history["date"].eq(resolved) & history["analysis_context_id"].eq(requested_pool)].copy()
    else:
        selected = history.loc[history["date"].eq(resolved)].merge(
            universe[["economic_exposure_family_id", "canonical_query_pool"]],
            on="economic_exposure_family_id",
            how="left",
        )
        selected = selected.loc[selected["analysis_context_id"].eq(selected["canonical_query_pool"])].drop(columns="canonical_query_pool")
    selected = selected.merge(
        universe.drop(columns=[column for column in ["economic_exposure_name", "parent_exposure_family_id", "overlap_cluster_id", "sector", "industry", "economic_theme", "research_maturity"] if column in universe.columns]),
        on="economic_exposure_family_id",
        how="left",
        validate="many_to_one",
        suffixes=("", "_current"),
    )
    selected = selected.loc[selected["first_valid_date"].notna() & selected["first_valid_date"].le(resolved)].copy()

    parent = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_PARENT_BENCHMARK_MAP_POST_A2R.csv")
    global_map = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_GLOBAL_BENCHMARK_MAP_POST_A2R.csv")
    selected = selected.merge(parent[["economic_exposure_family_id", "parent_benchmark_family_id"]], on="economic_exposure_family_id", how="left", suffixes=("", "_map"))
    if "parent_benchmark_family_id_map" in selected.columns:
        selected["parent_benchmark_family_id"] = selected["parent_benchmark_family_id_map"].combine_first(selected.get("parent_benchmark_family_id"))
        selected = selected.drop(columns="parent_benchmark_family_id_map")
    selected = selected.merge(global_map[["economic_exposure_family_id", "global_benchmark_family_id"]], on="economic_exposure_family_id", how="left")

    relative = _read_parquet("UKACTIVE_A3R1R1_RELATIVE_LINE_FEATURES.parquet")
    relative = relative.loc[relative["date"].eq(resolved)].drop_duplicates(["date", "economic_exposure_family_id"])
    selected = selected.merge(relative[["date", "economic_exposure_family_id", "REL_SLOPE_63", "REL_R2_63"]], on=["date", "economic_exposure_family_id"], how="left")
    segments = _read_parquet("UKACTIVE_A3R1R1_DISCRETE_RELATIVE_SEGMENTS.parquet")
    segments = segments.loc[segments["date"].eq(resolved)].drop_duplicates(["date", "economic_exposure_family_id"])
    segment_columns = ["REL_SEG_0_1M", "REL_SEG_1_2M", "REL_SEG_2_3M", "REL_SEG_3_6M", "REL_SEG_6_12M"]
    selected = selected.merge(segments[["date", "economic_exposure_family_id", *segment_columns]], on=["date", "economic_exposure_family_id"], how="left")

    regime = _read_parquet("UKACTIVE_A3R2_REGIME_STATE_HISTORY.parquet")
    regime = regime.loc[regime["date"].eq(resolved)].copy()
    regime_columns = ["pool_id", "global_trend_regime", "volatility_regime", "dispersion_regime", "breadth_regime", "rotation_intensity_regime", "us_technology_dominance"]
    selected = selected.merge(regime[["date", *regime_columns]], left_on=["date", "analysis_context_id"], right_on=["date", "pool_id"], how="left")

    # A4B is a display-only overlay generated after the historical experiment.
    # It exposes lifecycle diagnostics but cannot feed A3R2/A4/A4B decisions.
    a4b_overlay_path = PROGRAMME_ROOT / "UKACTIVE_A4B_QUERY_OVERLAY.parquet"
    if a4b_overlay_path.exists():
        a4b = pd.read_parquet(a4b_overlay_path)
        a4b["date"] = pd.to_datetime(a4b["date"])
        a4b = a4b.loc[a4b["date"].eq(resolved)].drop_duplicates(["date", "economic_exposure_family_id"])
        a4b_fields = [
            "date", "economic_exposure_family_id", "FAST_RS", "SLOW_RS",
            "LEADERSHIP_STATE", "challenger_status", "incumbent_status",
            "REGIME_SCORE", "REGIME_STATE", "REGIME_PEAK_DETECTED",
            "REGIME_PEAK_OR_MATURITY_FLAG", "target_leadership_allocation",
            "regime_multiplier", "final_target_risky_allocation", "cash_allocation",
            "MFE", "current_giveback", "profit_lock_state", "a4b_portfolio_status",
        ]
        selected = selected.merge(
            a4b[[column for column in a4b_fields if column in a4b.columns]],
            on=["date", "economic_exposure_family_id"], how="left", validate="many_to_one",
        )

    current_view = resolved == current_cutoff
    if not current_view:
        selected["II_CURRENT_TRADABLE"] = "NOT_APPLICABLE_HISTORICAL_ASOF"
        selected["II_OBSERVATION_DATE"] = pd.NA
        selected["ticker"] = "HISTORICAL_CURRENT_LINE_NOT_BACK_PROJECTED"
        selected["isin"] = "HISTORICAL_CURRENT_LINE_NOT_BACK_PROJECTED"
    selected["current_universe_status"] = np.where(
        selected["MH_LEVEL_3_6_12_REFERENCE"].notna(),
        "SIGNAL_ELIGIBLE_AT_ASOF",
        "EXISTS_WARMUP_OR_DATA_INCOMPLETE_AT_ASOF",
    )
    selected["market_intelligence_classification"] = selected["analysis_context_id"].map(INTELLIGENCE)
    selected["market_data_asof"] = resolved
    selected["requested_asof"] = requested

    rename = {
        "date": "as_of_date",
        "economic_exposure_name": "economic_exposure_family",
        "analysis_context_id": "rotation_pool",
        "RANK_RS_21": "rank_1m",
        "RANK_RS_42": "rank_2m",
        "RANK_RS_63": "rank_3m",
        "RANK_RS_126": "rank_6m",
        "RANK_RS_252": "rank_12m",
        "SHORT_RS_1_2_3_EQ": "short_1_2_3_composite",
        "MH_LEVEL_EQ": "equal_five_horizon_composite",
        "MH_LEVEL_60D_CENTERED": "60_day_centred_composite",
        "MH_LEVEL_3_6_12_REFERENCE": "3_6_12_composite",
        "PAIRWISE_MAJORITY_5H": "pairwise_win_rate",
        "REL_SLOPE_63": "relative_line_slope_63",
        "REL_R2_63": "relative_line_r2_63",
        "ROTATION_STATE": "relative_strength_state",
        "LEADERSHIP_STATE": "leadership_state",
        "REGIME_SCORE": "regime_score",
        "REGIME_STATE": "regime_state",
        "REGIME_PEAK_DETECTED": "regime_peak_flag",
        "REGIME_PEAK_OR_MATURITY_FLAG": "regime_peak_maturity_flag",
        "contemporaneous_research_maturity": "research_maturity_asof",
        "data_quality_flags": "data_quality_status",
    }
    selected = selected.rename(columns=rename)
    output_columns = [
        "as_of_date", "requested_asof", "economic_exposure_family_id", "economic_exposure_family", "ticker", "isin",
        "II_CURRENT_TRADABLE", "II_OBSERVATION_DATE", "rotation_pool", "primary_competition_pool_id",
        "parent_exposure_family_id", "global_benchmark_family_id", "parent_benchmark_family_id", "a0_primary_geography",
        "sector", "industry", "economic_theme", "deepvue_theme", "RS_21", "RS_42", "RS_63", "RS_126", "RS_252",
        "rank_1m", "rank_2m", "rank_3m", "rank_6m", "rank_12m", "short_1_2_3_composite",
        "equal_five_horizon_composite", "60_day_centred_composite", "3_6_12_composite", "pairwise_win_rate", "pairwise_rank",
        *segment_columns, "one_week_rank_change", "one_month_rank_change", "relative_line_slope_63", "relative_line_r2_63",
        "relative_strength_state", "state_transition", "leadership_duration_weeks", "global_trend_regime", "volatility_regime",
        "dispersion_regime", "breadth_regime", "rotation_intensity_regime", "us_technology_dominance", "research_maturity_asof",
        "FAST_RS", "SLOW_RS", "leadership_state", "challenger_status", "incumbent_status",
        "regime_score", "regime_state", "regime_peak_flag", "regime_peak_maturity_flag",
        "target_leadership_allocation", "regime_multiplier", "final_target_risky_allocation",
        "cash_allocation", "MFE", "current_giveback", "profit_lock_state", "a4b_portfolio_status",
        "data_quality_status", "current_universe_status", "current_implementable_view", "market_intelligence_classification",
        "public_ISA_rules_status", "UK_retail_disclosure_status", "LSE_current_status", "current_observation_date", "warning",
    ]
    for column in output_columns:
        if column not in selected.columns:
            selected[column] = pd.NA
    selected = selected[output_columns].sort_values(["rotation_pool", DEFAULT_SORT, "economic_exposure_family_id"], ascending=[True, False, True]).reset_index(drop=True)
    regime_row = regime.loc[regime["pool_id"].eq("ALL_EQUITY_OPPORTUNITIES")]
    regime_payload = regime_row.iloc[0].to_dict() if len(regime_row) else {"date": resolved, "status": "NOT_AVAILABLE"}
    regime_payload = {key: (value.isoformat() if isinstance(value, pd.Timestamp) else value) for key, value in regime_payload.items()}
    return selected, regime_payload


def query(asof: str, pool: str | None, family: str | None, top: int, sort_by: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    snapshot, regime = build_snapshot(asof, pool)
    if family:
        target = family.strip().upper()
        snapshot = snapshot.loc[
            snapshot["economic_exposure_family_id"].astype(str).str.upper().eq(target)
            | snapshot["economic_exposure_family"].astype(str).str.upper().eq(target)
        ]
    elif sort_by in snapshot.columns:
        snapshot = snapshot.loc[snapshot[sort_by].notna()].sort_values([sort_by, "economic_exposure_family_id"], ascending=[False, True]).head(max(1, int(top)))
    return snapshot.reset_index(drop=True), regime


def _json_ready(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Query UKACTIVE rotation leadership")
    parser.add_argument("--asof", default="latest", help="latest or YYYY-MM-DD; resolves to last frozen weekly XLON observation")
    parser.add_argument("--pool", choices=sorted(POOL_MAP), default=None)
    parser.add_argument("--family", default=None)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--sort-by", default=DEFAULT_SORT)
    parser.add_argument("--show-regime", action="store_true")
    parser.add_argument("--format", choices=["table", "csv", "json"], default="table")
    args = parser.parse_args()
    frame, regime = query(args.asof, args.pool, args.family, args.top, args.sort_by)
    if args.format == "csv":
        print(frame.to_csv(index=False), end="")
    elif args.format == "json":
        print(json.dumps({"results": _json_ready(frame), "regime": regime if args.show_regime else None}, indent=2, default=str))
    else:
        display = [column for column in ["as_of_date", "economic_exposure_family_id", "ticker", "rotation_pool", "RS_21", "RS_42", "RS_63", "short_1_2_3_composite", "3_6_12_composite", "pairwise_rank", "relative_strength_state", "one_month_rank_change"] if column in frame]
        print(frame[display].to_string(index=False))
        if args.show_regime:
            print("\nREGIME")
            print(json.dumps(regime, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
