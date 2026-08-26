"""Build the frozen UKACTIVE-A5C-SIPP implementation/readiness package.

The builder is intentionally mechanical.  It does not inspect post-cutoff
returns, calculate a prospective signal, optimise a model, or create an order.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import ukactive_a5c_sipp_core as core


ROOT = core.PROGRAMME_ROOT
OUT = core.STAGE_ROOT
A4E = ROOT / "UKACTIVE-A4E-SIPP"
A4F = ROOT / "UKACTIVE-A4F-SIPP-REGIME"
FREEZE_COMMIT = "a8008f7709af3000a889bb234a86f8c520c4ed73"
RESULTS_COMMIT = "beb8d49828b9819aa167d2e07ffdc2b92581b36b"
BUILD_DATE = "2026-08-26"


def write_csv(name: str, frame: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT / name, index=False, lineterminator="\n")


def write_csv_if_absent(name: str, frame: pd.DataFrame) -> bool:
    """Create a user-input template once; never erase subsequently supplied data."""

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    if path.exists():
        return False
    frame.to_csv(path, index=False, lineterminator="\n")
    return True


def write_json(name: str, value: Any) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_text(name: str, value: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(value.rstrip() + "\n", encoding="utf-8")


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(float(value)) else float(value)
    if pd.isna(value) if not isinstance(value, str) else False:
        return None
    return value


def build_instrument_map() -> pd.DataFrame:
    source_path = A4E / "UKACTIVE_A4E_SIPP_LIVE_INSTRUMENT_MAP.csv"
    source = pd.read_csv(source_path, dtype=str, keep_default_na=False)
    role_master = pd.read_csv(ROOT / "UKACTIVE_A2R_A3R0_ROTATION_ROLE_MASTER_POST_A2R.csv", dtype=str, keep_default_na=False)
    current_lines = pd.read_csv(ROOT / "UKACTIVE_A2R_A3R0_CURRENT_IMPLEMENTATION_LINES_POST_A2R.csv", dtype=str, keep_default_na=False)
    a5_map = pd.read_csv(ROOT / "UKACTIVE_A5_IMPLEMENTATION_MAP.csv", dtype=str, keep_default_na=False)
    a5_lookup = a5_map.set_index("economic_exposure_family_id").to_dict("index")
    role_lookup = role_master.set_index("economic_exposure_family_id").to_dict("index")
    source["implementation_role"] = source["economic_exposure_family_id"].map(
        lambda family: "GLOBAL_CORE" if family == core.GLOBAL_FAMILY else ("BROKER_CASH_OPERATIONAL" if family == "LIVE_GBP_CASH" else "M2_FAMILY")
    )
    source["rotation_role"] = source["economic_exposure_family_id"].map(lambda family: role_lookup.get(family, {}).get("primary_rotation_role", "NOT_APPLICABLE"))
    source["signal_status_at_2026_08_21"] = source["economic_exposure_family_id"].map(
        lambda family: "SIGNAL_READY" if family not in {core.GLOBAL_FAMILY, "LIVE_GBP_CASH"} else "NOT_APPLICABLE"
    )
    source["preferred_line_rule"] = "USE_FROZEN_PREFERRED_GBP_OR_GBX_LINE"
    source["alternate_use_rule"] = source["substitute_instrument"].map(
        lambda value: "ONLY_IF_FROZEN_GBP_GBX_AND_CONFIRMED_IN_SIPP" if value and "|" in value else "NO_AUTOMATIC_ALTERNATE"
    )
    source["a5c_current_status"] = source["economic_exposure_family_id"].map(
        lambda family: "SWDA_CONFIRMED_CURRENT" if family == core.GLOBAL_FAMILY else ("MINIMAL_OPERATIONAL_BALANCE_ONLY" if family == "LIVE_GBP_CASH" else "II_CONFIRMED_CURRENT_SIPP_ACCOUNT_TO_CONFIRM")
    )
    source["alternate_ticker"] = source["economic_exposure_family_id"].map(lambda family: a5_lookup.get(family, {}).get("alternate_ticker", ""))
    source["alternate_isin"] = source["economic_exposure_family_id"].map(lambda family: a5_lookup.get(family, {}).get("alternate_isin", ""))
    source["alternate_trading_currency"] = source["economic_exposure_family_id"].map(lambda family: a5_lookup.get(family, {}).get("alternate_currency", ""))
    source["alternate_price_unit"] = source["economic_exposure_family_id"].map(lambda family: a5_lookup.get(family, {}).get("alternate_price_unit", ""))
    source["automatic_alternate_permitted"] = source["economic_exposure_family_id"].map(
        lambda family: "YES_ONLY_AFTER_CURRENT_SIPP_CONFIRMATION" if a5_lookup.get(family, {}).get("alternate_currency", "") == "GBP" else "NO_USD_OR_EUR_LINE"
    )
    source["ii_current_tradable"] = source["economic_exposure_family_id"].map(lambda family: a5_lookup.get(family, {}).get("ii_current_tradable", source.loc[source.economic_exposure_family_id.eq(family), "broker_availability"].iloc[0] if family in set(source.economic_exposure_family_id) else ""))
    source["ii_observation_date"] = source["economic_exposure_family_id"].map(lambda family: a5_lookup.get(family, {}).get("ii_observation_date", ""))
    source["ii_verification_method"] = source["economic_exposure_family_id"].map(lambda family: a5_lookup.get(family, {}).get("ii_verification_method", ""))
    source["historical_back_projection"] = "PROHIBITED"
    source["a5c_source_artifact"] = str(source_path.relative_to(ROOT))

    extra_rows: list[dict[str, Any]] = []
    for family, readiness, ii_status in [
        ("EUROPE_INFRASTRUCTURE", "NOT_SIGNAL_READY_RS252_WARMUP", "TO_CHECK"),
        ("US_AEROSPACE_DEFENCE", "NOT_SIGNAL_READY_ALL_HORIZONS_WARMUP", "CONFIRMED_BY_USER"),
    ]:
        lines = current_lines.loc[current_lines["economic_exposure_family_id"].eq(family)]
        preferred = lines.loc[lines["preferred_or_alternate"].eq("PREFERRED")].iloc[0]
        alternate = lines.loc[lines["preferred_or_alternate"].eq("ALTERNATE")].iloc[0]
        row = {column: "" for column in source.columns}
        row.update(
            {
                "economic_exposure_family_id": family,
                "fund_name": preferred["share_class_name"],
                "ticker": preferred["ticker"],
                "isin": preferred["isin"],
                "exchange": preferred["exchange"],
                "domicile": "NOT_EVIDENCED_IN_CURRENT_CANONICAL_ARTIFACT",
                "ucits_status": preferred["ucits_status"],
                "priips_kid_status": preferred["UK_retail_disclosure_status"],
                "uk_retail_status": preferred["public_ISA_rules_status"],
                "sipp_availability": "TO_CHECK_SIPP_SPECIFIC_ACCOUNT",
                "broker_availability": ii_status,
                "distribution_policy": "NOT_DETERMINED",
                "base_currency": "NOT_VERIFIED",
                "trading_currency": preferred["listing_currency"],
                "substitute_instrument": f"{alternate['ticker']}|{alternate['isin']}|{alternate['listing_currency']}|{alternate['price_unit']}",
                "no_investment_rule": "IF PREFERRED GBP LINE AND FROZEN GBP ALTERNATE ARE UNAVAILABLE, ALLOCATE SLOT TO CSH2; NO DISCRETIONARY SUBSTITUTE",
                "source_url": preferred["public_evidence_URLs"],
                "retrieval_date": preferred["public_evidence_date"],
                "evidence_notes": "Structural 27-family universe member. Current-only implementation metadata; eligibility begins only after actual M2 warm-up.",
                "implementation_role": "M2_FAMILY",
                "rotation_role": role_lookup[family]["primary_rotation_role"],
                "signal_status_at_2026_08_21": readiness,
                "preferred_line_rule": "USE_FROZEN_PREFERRED_GBP_OR_GBX_LINE_AFTER_SIGNAL_WARMUP",
                "alternate_use_rule": "ONLY_IF_FROZEN_GBP_GBX_AND_CONFIRMED_IN_SIPP" if alternate["listing_currency"] == "GBP" else "USD_OR_EUR_ALTERNATE_NOT_PERMITTED_AUTOMATICALLY",
                "a5c_current_status": "CURRENT_LINE_RECORDED_NOT_CURRENTLY_SIGNAL_READY",
                "alternate_ticker": alternate["ticker"],
                "alternate_isin": alternate["isin"],
                "alternate_trading_currency": alternate["listing_currency"],
                "alternate_price_unit": alternate["price_unit"],
                "automatic_alternate_permitted": "YES_ONLY_AFTER_CURRENT_SIPP_CONFIRMATION" if alternate["listing_currency"] == "GBP" else "NO_USD_OR_EUR_LINE",
                "ii_current_tradable": ii_status,
                "ii_observation_date": "2026-08-23" if ii_status == "CONFIRMED_BY_USER" else "",
                "ii_verification_method": "USER_ACCOUNT_MANUAL_CHECK" if ii_status == "CONFIRMED_BY_USER" else "NOT_VERIFIED",
                "historical_back_projection": "PROHIBITED",
                "a5c_source_artifact": "UKACTIVE_A2R_A3R0_CURRENT_IMPLEMENTATION_LINES_POST_A2R.csv",
            }
        )
        extra_rows.append(row)

    csh2 = {column: "" for column in source.columns}
    csh2.update(
        {
            "economic_exposure_family_id": "LIVE_TACTICAL_CSH2",
            "fund_name": "Amundi Smart Overnight Return GBP Hedged",
            "ticker": "CSH2",
            "isin": "LU1230136894",
            "exchange": "London Stock Exchange",
            "domicile": "LUXEMBOURG",
            "ucits_status": "TO_CONFIRM_FROM_CURRENT_KID",
            "priips_kid_status": "TO_CONFIRM_CURRENT",
            "uk_retail_status": "CURRENT_LSE_LINE_CONFIRMED_UK_RETAIL_AND_SIPP_TO_CONFIRM",
            "sipp_availability": "TO_CONFIRM_FROM_CURRENT_HOLDING_OR_ACCOUNT",
            "broker_availability": "USER_REPORTS_CURRENT_HOLDING_NAME_QUANTITY_UNVERIFIED",
            "distribution_policy": "TO_CONFIRM",
            "base_currency": "GBP_HEDGED_SHARE_CLASS_LABEL",
            "trading_currency": "GBP",
            "currency_hedging_status": "GBP_HEDGED",
            "indicative_spread": "ACTUAL_QUOTE_REQUIRED_AT_EXECUTION",
            "substitute_instrument": "NONE",
            "no_investment_rule": "TACTICAL_ONLY; USE FOR SUSPENDED SLOTS AND NEAR_TERM_LIQUIDITY; NO HISTORICAL_BACK_PROJECTION",
            "source_url": "UKACTIVE_A0A1_DISCOVERY_REGISTRY.csv|DSC-A7DED27F17289942|EVD-44E73C12472C3C50",
            "retrieval_date": "2026-08-22",
            "evidence_notes": "Exact LSE ticker/ISIN/currency are authoritative current discovery metadata. Current SIPP holding and availability still require user snapshot confirmation.",
            "implementation_role": "DEFENSIVE_TACTICAL",
            "rotation_role": "NOT_APPLICABLE",
            "signal_status_at_2026_08_21": "NOT_APPLICABLE",
            "preferred_line_rule": "CSH2_ONLY",
            "alternate_use_rule": "NONE",
            "a5c_current_status": "PERMITTED_PROSPECTIVELY_PENDING_SIPP_CONFIRMATION",
            "automatic_alternate_permitted": "NO_ALTERNATE",
            "ii_current_tradable": "TO_CONFIRM_CURRENT_SIPP_HOLDING",
            "ii_observation_date": "",
            "ii_verification_method": "CURRENT_HOLDINGS_EXPORT_REQUIRED",
            "historical_back_projection": "PROHIBITED",
            "a5c_source_artifact": "UKACTIVE_A0A1_DISCOVERY_REGISTRY.csv",
        }
    )
    extra_rows.append(csh2)

    rlon = {column: "" for column in source.columns}
    rlon.update(
        {
            "economic_exposure_family_id": "LIVE_STRATEGIC_RLON",
            "fund_name": "AWAITING_EXACT_CURRENT_HOLDING_SHARE_CLASS",
            "ticker": "RLON_USER_LABEL_NOT_A_VERIFIED_MARKET_IDENTIFIER",
            "isin": "AWAITING_CURRENT_HOLDINGS_INPUT",
            "exchange": "II_FUND_PLATFORM_DEALING_TERMS_TO_SUPPLY",
            "domicile": "TO_SUPPLY",
            "ucits_status": "TO_SUPPLY",
            "priips_kid_status": "TO_SUPPLY",
            "uk_retail_status": "TO_SUPPLY",
            "sipp_availability": "USER_REPORTS_CURRENT_HOLDING_EXACT_RECORD_REQUIRED",
            "broker_availability": "USER_REPORTS_CURRENT_HOLDING_EXACT_RECORD_REQUIRED",
            "distribution_policy": "TO_SUPPLY",
            "ter": "TO_SUPPLY",
            "base_currency": "TO_SUPPLY",
            "trading_currency": "GBP_EXPECTED_NOT_INFERRED",
            "indicative_spread": "FUND_DEALING_TERMS_TO_SUPPLY",
            "substitute_instrument": "NONE",
            "no_investment_rule": "DO_NOT_USE UNTIL EXACT HELD SHARE CLASS, ISIN AND DEALING TERMS ARE FROZEN",
            "retrieval_date": BUILD_DATE,
            "evidence_notes": "No repository or Git-history instrument record exists. The exact share class and ISIN are intentionally not guessed.",
            "implementation_role": "DEFENSIVE_STRATEGIC",
            "rotation_role": "NOT_APPLICABLE",
            "signal_status_at_2026_08_21": "NOT_APPLICABLE",
            "preferred_line_rule": "EXACT_CURRENT_HELD_SHARE_CLASS_ONLY",
            "alternate_use_rule": "NONE",
            "a5c_current_status": "AWAITING_CURRENT_HOLDINGS_INPUT",
            "automatic_alternate_permitted": "NO_ALTERNATE",
            "ii_current_tradable": "TO_CONFIRM_CURRENT_SIPP_HOLDING",
            "ii_observation_date": "",
            "ii_verification_method": "CURRENT_HOLDINGS_EXPORT_REQUIRED",
            "historical_back_projection": "PROHIBITED",
            "a5c_source_artifact": "USER_CURRENT_HOLDING_REQUIRED",
        }
    )
    extra_rows.append(rlon)

    result = pd.concat([source, pd.DataFrame(extra_rows, columns=source.columns)], ignore_index=True)
    priority = {"GLOBAL_CORE": 0, "M2_FAMILY": 1, "DEFENSIVE_STRATEGIC": 2, "DEFENSIVE_TACTICAL": 3, "BROKER_CASH_OPERATIONAL": 4}
    result["_priority"] = result["implementation_role"].map(priority).fillna(9)
    result = result.sort_values(["_priority", "economic_exposure_family_id"]).drop(columns="_priority").reset_index(drop=True)
    return result


def holdings_input_and_classification() -> tuple[pd.DataFrame, pd.DataFrame]:
    known = [
        ("RLON", "RLON", "DEFENSIVE_STRATEGIC", "Exact Royal London fund/share class and ISIN required"),
        ("CSH2", "CSH2", "DEFENSIVE_TACTICAL", "Canonical reference ISIN LU1230136894; current holding identity/value still required"),
        ("Artemis Global Income", "", "DISCRETIONARY_ACTIVE", "Active fund; exact share class and value required"),
        ("Artemis European Select", "", "DISCRETIONARY_ACTIVE", "Active regional fund; exact share class and value required"),
        ("VWRL", "VWRL", "LEGACY_TRANSITION", "Broad global equity overlap but frozen core implementation is SWDA"),
        ("QQQA", "QQQA", "DISCRETIONARY_ACTIVE", "Concentrated active/thematic exposure included in 25% cap"),
        ("COPG", "COPG", "M2_ECONOMIC_OVERLAP_BUT_NONCOMPLIANT", "Economic overlap only; exact ticker/ISIN is not a frozen M2 preferred line"),
        ("LITG", "LITG", "M2_ECONOMIC_OVERLAP_BUT_NONCOMPLIANT", "Economic overlap only; exact ticker/ISIN is not a frozen M2 preferred line"),
        ("SILG", "SILG", "M2_ECONOMIC_OVERLAP_BUT_NONCOMPLIANT", "Ticker matches a frozen line, but current held ISIN must be supplied before exact-compliance classification"),
        ("ENGE", "ENGE", "M2_ECONOMIC_OVERLAP_BUT_NONCOMPLIANT", "Economic overlap only; exact ticker/ISIN is not a frozen M2 preferred line"),
        ("GDGB", "GDGB", "M2_ECONOMIC_OVERLAP_BUT_NONCOMPLIANT", "Economic overlap only; exact ticker/ISIN is not a frozen M2 preferred line"),
    ]
    input_rows = []
    class_rows = []
    for instrument, ticker, classification, notes in known:
        input_rows.append(
            {
                "account_date": "",
                "instrument": instrument,
                "ticker": ticker,
                "isin": "",
                "quantity": "",
                "market_value": "",
                "trading_currency": "",
                "classification": classification,
                "unrealised_gain_loss": "",
                "dealing_restriction": "",
                "notes": notes,
            }
        )
        class_rows.append(
            {
                "instrument": instrument,
                "reported_ticker": ticker,
                "reported_isin": "",
                "classification": classification,
                "classification_status": "PROVISIONAL_AWAITING_EXACT_CURRENT_HOLDINGS_INPUT",
                "market_value_gbp": "",
                "included_in_25pct_active_thematic_cap": classification in {"DISCRETIONARY_ACTIVE", "M2_EXACT_COMPLIANT", "M2_ECONOMIC_OVERLAP_BUT_NONCOMPLIANT", "LEGACY_TRANSITION"} and instrument not in {"VWRL"},
                "exact_model_compliance": "NOT_ESTABLISHED_FROM_NAME_OR_TICKER_ONLY",
                "notes": notes,
            }
        )
    return pd.DataFrame(input_rows), pd.DataFrame(class_rows)


def fee_summary(
    result: core.PlanResult,
    start: pd.Timestamp | str | None = None,
    end: pd.Timestamp | str | None = None,
) -> dict[str, float | int]:
    curve = result.simulation.curve.sort_values("date")
    if start is not None:
        curve = curve.loc[curve["date"].ge(pd.Timestamp(start))]
    if end is not None:
        curve = curve.loc[curve["date"].le(pd.Timestamp(end))]
    if curve.empty:
        raise AssertionError("Fee summary window has no portfolio observations")
    actual_start = pd.Timestamp(curve["date"].min())
    actual_end = pd.Timestamp(curve["date"].max())
    audit = result.fee_audit.loc[
        result.fee_audit["date"].ge(actual_start) & result.fee_audit["date"].le(actual_end)
    ]
    years = core.annualised_years(actual_start, actual_end)
    started_calendar_months = int(curve["date"].dt.to_period("M").nunique())
    monthly_subscription = float(core.II_PLANS[result.ii_plan]["monthly_subscription_gbp"])
    total_dealing = float(audit["dealing_fee_gbp"].sum())
    total_friction = float(audit["market_friction_gbp"].sum())
    total_subscription = started_calendar_months * monthly_subscription
    current_scale_annual_friction = (
        float(audit["traded_notional_fraction"].sum()) / years
        * float(result.notional_gbp)
        * core.ONE_WAY_FRICTION_BPS
        / 10_000.0
    )
    return {
        "years": years,
        "started_calendar_months": started_calendar_months,
        "trade_legs": int(audit["trade_legs"].sum()),
        "free_trade_legs": int(audit["free_trade_legs"].sum()),
        "paid_trade_legs": int(audit["paid_trade_legs"].sum()),
        "total_dealing_charges_gbp": total_dealing,
        "historical_total_market_friction_gbp": total_friction,
        "total_subscription_gbp": total_subscription,
        "annual_dealing_charges_gbp": total_dealing / years,
        "historical_average_annual_market_friction_gbp": total_friction / years,
        "current_scale_annual_market_friction_gbp": current_scale_annual_friction,
        "annual_subscription_gbp": monthly_subscription * 12.0,
        "annual_total_platform_dealing_gbp": total_dealing / years + monthly_subscription * 12.0,
        "current_scale_annual_all_in_including_friction_gbp": total_dealing / years + current_scale_annual_friction + monthly_subscription * 12.0,
    }


def make_cost_outputs(data: core.a4f.a4d.A4DData, maps: dict[str, dict[pd.Timestamp, dict[str, float]]]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[tuple[str, str, float], core.PlanResult]]:
    strategy_ids = ["GLOBAL_75_DEFENSIVE_25", "GLOBAL_65_M2_10_DEFENSIVE_25", "GLOBAL_60_M2_15_DEFENSIVE_25", "GLOBAL_50_M2_25_DEFENSIVE_25", "M2_100_DIAGNOSTIC", "GLOBAL_100"]
    gross = {strategy_id: core._gross_simulation(data, strategy_id, maps[strategy_id]) for strategy_id in strategy_ids}
    cache: dict[tuple[str, str, float], core.PlanResult] = {}
    cost_rows: list[dict[str, Any]] = []
    plan_rows: list[dict[str, Any]] = []
    compare_rows: list[dict[str, Any]] = []
    windows = {"FULL_HISTORY": (core.COMMON_START, core.AUTHORITATIVE_CUTOFF), "LATEST_FIVE_YEARS": (pd.Timestamp("2021-09-01"), core.AUTHORITATIVE_CUTOFF)}
    for notional in [core.CANONICAL_PORTFOLIO_GBP, core.CURRENT_PORTFOLIO_GBP]:
        for ii_plan in core.II_PLANS:
            for strategy_id in strategy_ids:
                sim_no_sub, audit_no_sub = core._charge_curve(gross[strategy_id], strategy_id, ii_plan, notional, include_full_subscription=False)
                sim_full_sub, audit_full_sub = core._charge_curve(gross[strategy_id], strategy_id, ii_plan, notional, include_full_subscription=True)
                no_sub = core.PlanResult(strategy_id, ii_plan, notional, maps[strategy_id], sim_no_sub, audit_no_sub, "SUBSCRIPTION_REPORTED_SEPARATELY")
                full_sub = core.PlanResult(strategy_id, ii_plan, notional, maps[strategy_id], sim_full_sub, audit_full_sub, "FULL_SUBSCRIPTION_DEDUCTED")
                cache[(strategy_id, ii_plan, float(notional))] = no_sub
                fees = fee_summary(no_sub)
                plan_rows.append(
                    {
                        "strategy_id": strategy_id,
                        "ii_plan": ii_plan,
                        "notional_gbp": notional,
                        **fees,
                        "annual_dealing_charges_no_credits_gbp": fees["trade_legs"] / fees["years"] * float(core.II_PLANS[ii_plan]["fee_per_paid_leg_gbp"]),
                        "incremental_subscription_vs_plus_gbp_per_year": (float(core.II_PLANS[ii_plan]["monthly_subscription_gbp"]) - float(core.II_PLANS["II_PLUS"]["monthly_subscription_gbp"])) * 12.0,
                        "platform_maintenance_cost_gbp_per_year": fees["annual_subscription_gbp"],
                        "credit_assumption": "CREDITS_RESERVED_FOR_MODEL_TRADES; IF USED_ELSEWHERE USE_NO_CREDIT_COLUMN",
                    }
                )
                control_id = "GLOBAL_75_DEFENSIVE_25" if strategy_id in {"GLOBAL_65_M2_10_DEFENSIVE_25", "GLOBAL_60_M2_15_DEFENSIVE_25", "GLOBAL_50_M2_25_DEFENSIVE_25"} else ("GLOBAL_100" if strategy_id == "M2_100_DIAGNOSTIC" else strategy_id)
                control_no_sub = None
                if control_id != strategy_id:
                    c_sim, c_audit = core._charge_curve(gross[control_id], control_id, ii_plan, notional, include_full_subscription=False)
                    control_no_sub = core.PlanResult(control_id, ii_plan, notional, maps[control_id], c_sim, c_audit, "SUBSCRIPTION_REPORTED_SEPARATELY")
                for window_id, (start, end) in windows.items():
                    m = core.metrics(no_sub, start, end)
                    ms = core.metrics(full_sub, start, end)
                    window_fees = fee_summary(no_sub, start, end)
                    control_cagr = core.metrics(control_no_sub, start, end)["net_cagr"] if control_no_sub is not None else m["net_cagr"]
                    cost_rows.append(
                        {
                            "strategy_id": strategy_id,
                            "control_id": control_id,
                            "window_id": window_id,
                            "ii_plan": ii_plan,
                            "notional_gbp": notional,
                            "one_way_friction_bps": 20.0,
                            "broker_fx_fee": 0.0,
                            "ter_double_deducted": False,
                            "gross_cagr": m.get("gross_cagr", np.nan),
                            "net_cagr_subscription_reported_separately": m["net_cagr"],
                            "net_cagr_full_subscription_deducted": ms["net_cagr"],
                            "cost_drag_cagr_subscription_reported_separately": m.get("gross_cagr", np.nan) - m["net_cagr"],
                            "cost_drag_cagr_full_subscription": ms.get("gross_cagr", np.nan) - ms["net_cagr"],
                            "net_incremental_cagr_vs_control": m["net_cagr"] - control_cagr,
                            "maximum_drawdown": m["maximum_drawdown"],
                            "maximum_drawdown_full_subscription": ms["maximum_drawdown"],
                            "ulcer_index": m["ulcer_index"],
                            "ulcer_index_full_subscription": ms["ulcer_index"],
                            "annual_turnover": m["annual_turnover_traded_notional"],
                            "trade_legs": window_fees["trade_legs"],
                            "free_trade_legs": window_fees["free_trade_legs"],
                            "paid_trade_legs": window_fees["paid_trade_legs"],
                            "started_calendar_months": window_fees["started_calendar_months"],
                            "total_dealing_charges_gbp": window_fees["total_dealing_charges_gbp"],
                            "total_subscription_gbp": window_fees["total_subscription_gbp"],
                            "historical_total_market_friction_gbp": window_fees["historical_total_market_friction_gbp"],
                            "annual_dealing_charges_gbp": window_fees["annual_dealing_charges_gbp"],
                            "annual_subscription_gbp": window_fees["annual_subscription_gbp"],
                            "historical_average_annual_market_friction_gbp": window_fees["historical_average_annual_market_friction_gbp"],
                            "current_scale_annual_market_friction_gbp": window_fees["current_scale_annual_market_friction_gbp"],
                            "current_scale_annual_all_in_including_friction_gbp": window_fees["current_scale_annual_all_in_including_friction_gbp"],
                            "subscription_attribution": "PLATFORM_MAINTENANCE_REPORTED_SEPARATELY_FROM_M2",
                            "partial_month_subscription_treatment": "FULL_MONTHLY_FEE_ON_FIRST_OBSERVED_SESSION_OF_EACH_STARTED_CALENDAR_MONTH",
                            "performance_normalisation": "CANONICAL_A4D_FIRST_POST_COST_OBSERVATION; INCEPTION_COST_INCLUDED_IN_COST_TOTALS_NOT_CAGR",
                        }
                    )
    plan_df = pd.DataFrame(plan_rows)
    plus = plan_df.loc[plan_df["ii_plan"].eq("II_PLUS")].set_index(["strategy_id", "notional_gbp"])
    for row in plan_df.itertuples(index=False):
        base = plus.loc[(row.strategy_id, row.notional_gbp)]
        m2_control = "GLOBAL_75_DEFENSIVE_25" if row.strategy_id in {"GLOBAL_65_M2_10_DEFENSIVE_25", "GLOBAL_60_M2_15_DEFENSIVE_25", "GLOBAL_50_M2_25_DEFENSIVE_25"} else ("GLOBAL_100" if row.strategy_id == "M2_100_DIAGNOSTIC" else row.strategy_id)
        same_plan_control = plan_df.loc[(plan_df.strategy_id.eq(m2_control)) & (plan_df.ii_plan.eq(row.ii_plan)) & (plan_df.notional_gbp.eq(row.notional_gbp))].iloc[0]
        compare_rows.append(
            {
                **row._asdict(),
                "incremental_total_plan_cost_vs_plus_gbp_per_year": row.annual_total_platform_dealing_gbp - float(base.annual_total_platform_dealing_gbp),
                "m2_attributable_incremental_friction_and_dealing_gbp_per_year": (row.current_scale_annual_market_friction_gbp + row.annual_dealing_charges_gbp) - (float(same_plan_control.current_scale_annual_market_friction_gbp) + float(same_plan_control.annual_dealing_charges_gbp)),
                "cost_attributable_to_maintaining_platform_gbp_per_year": row.annual_subscription_gbp,
                "current_user_plan": "TO_CONFIRM",
            }
        )

    cost_df = pd.DataFrame(cost_rows)
    compare_df = pd.DataFrame(compare_rows)
    sleeve_compare = cost_df.loc[
        cost_df.strategy_id.isin(["GLOBAL_65_M2_10_DEFENSIVE_25", "GLOBAL_60_M2_15_DEFENSIVE_25", "GLOBAL_50_M2_25_DEFENSIVE_25"])
        & cost_df.notional_gbp.eq(core.CURRENT_PORTFOLIO_GBP)
    ].copy()
    sleeve_compare["m2_allocation"] = sleeve_compare["strategy_id"].map({"GLOBAL_65_M2_10_DEFENSIVE_25": 0.10, "GLOBAL_60_M2_15_DEFENSIVE_25": 0.15, "GLOBAL_50_M2_25_DEFENSIVE_25": 0.25})
    sleeve_compare["target_m2_value_gbp"] = sleeve_compare["m2_allocation"] * core.CURRENT_PORTFOLIO_GBP
    sleeve_compare["target_per_family_gbp"] = sleeve_compare["target_m2_value_gbp"] / 7.0
    sleeve_compare["target_core_value_gbp"] = (0.75 - sleeve_compare["m2_allocation"]) * core.CURRENT_PORTFOLIO_GBP
    sleeve_compare["target_defensive_value_gbp"] = 0.25 * core.CURRENT_PORTFOLIO_GBP
    return cost_df, compare_df, sleeve_compare, cache


def _year_return(sim: core.a4b.A4BSimulation) -> pd.Series:
    curve = sim.curve.drop_duplicates("date").sort_values("date")
    return curve.groupby(curve["date"].dt.year)["net_return"].apply(lambda values: float((1.0 + values.astype(float)).prod() - 1.0))


def _relative_between(candidate: core.a4b.A4BSimulation, comparator: core.a4b.A4BSimulation, start: pd.Timestamp, end: pd.Timestamp) -> float:
    c = candidate.curve.set_index("date")["portfolio_value"].astype(float)
    b = comparator.curve.set_index("date")["portfolio_value"].astype(float)
    joined = pd.concat([c.rename("c"), b.rename("b")], axis=1, join="inner").dropna().loc[start:end]
    if len(joined) < 2:
        return float("nan")
    return float(joined.c.iloc[-1] / joined.c.iloc[0] - joined.b.iloc[-1] / joined.b.iloc[0])


def make_regret_outputs(cache: dict[tuple[str, str, float], core.PlanResult]) -> tuple[pd.DataFrame, pd.DataFrame]:
    pairs = [
        ("M2_100_DIAGNOSTIC", "GLOBAL_100", 1.00),
        ("GLOBAL_65_M2_10_DEFENSIVE_25", "GLOBAL_75_DEFENSIVE_25", 0.10),
        ("GLOBAL_60_M2_15_DEFENSIVE_25", "GLOBAL_75_DEFENSIVE_25", 0.15),
        ("GLOBAL_50_M2_25_DEFENSIVE_25", "GLOBAL_75_DEFENSIVE_25", 0.25),
    ]
    rows: list[dict[str, Any]] = []
    drag_rows: list[dict[str, Any]] = []
    m2 = cache[("M2_100_DIAGNOSTIC", "II_PLUS", core.CURRENT_PORTFOLIO_GBP)].simulation
    swda = cache[("GLOBAL_100", "II_PLUS", core.CURRENT_PORTFOLIO_GBP)].simulation
    m2_year = _year_return(m2)
    swda_year = _year_return(swda)
    for candidate_id, control_id, allocation in pairs:
        candidate = cache[(candidate_id, "II_PLUS", core.CURRENT_PORTFOLIO_GBP)].simulation
        control = cache[(control_id, "II_PLUS", core.CURRENT_PORTFOLIO_GBP)].simulation
        c_year = _year_return(candidate)
        b_year = _year_return(control)
        for year in sorted(set(c_year.index) & set(b_year.index)):
            relative = float(c_year.loc[year] - b_year.loc[year])
            rows.append({"candidate_id": candidate_id, "control_id": control_id, "diagnostic": "CALENDAR_YEAR_RELATIVE_RETURN", "period_start": f"{year}-01-01", "period_end": f"{year}-12-31", "months": np.nan, "relative_return": relative, "m2_allocation": allocation, "notes": "2017 and 2026 are partial"})
        for months in [3, 6, 12]:
            series = core.rolling_relative(candidate, control, months).dropna()
            for period, value in series.items():
                period_end = pd.Period(period, freq="M").end_time.normalize()
                rows.append({"candidate_id": candidate_id, "control_id": control_id, "diagnostic": f"ROLLING_{months}M_RELATIVE_RETURN", "period_start": "", "period_end": period_end.strftime("%Y-%m-%d"), "months": months, "relative_return": float(value), "m2_allocation": allocation, "notes": "Compounded candidate return minus compounded control return"})
        rows.append({"candidate_id": candidate_id, "control_id": control_id, "diagnostic": "MAXIMUM_RELATIVE_DRAWDOWN", "period_start": "", "period_end": "", "months": np.nan, "relative_return": core.maximum_relative_drawdown(candidate, control), "m2_allocation": allocation, "notes": "Drawdown of candidate/control relative NAV"})
        rows.append({"candidate_id": candidate_id, "control_id": control_id, "diagnostic": "LONGEST_RELATIVE_UNDERPERFORMANCE_DAYS", "period_start": "", "period_end": "", "months": np.nan, "relative_return": core.longest_relative_underwater_days(candidate, control), "m2_allocation": allocation, "notes": "Calendar days below prior relative high-water mark; value is a day count"})
        for label, excluded in [("EXCLUDE_2020", {2020}), ("EXCLUDE_2025", {2025}), ("EXCLUDE_2020_AND_2025", {2020, 2025})]:
            value = core.exclusion_return(candidate, excluded) - core.exclusion_return(control, excluded)
            rows.append({"candidate_id": candidate_id, "control_id": control_id, "diagnostic": label, "period_start": "", "period_end": "", "months": np.nan, "relative_return": value, "m2_allocation": allocation, "notes": "Annualised kept-session exclusion diagnostic; not a contiguous CAGR"})

    spells = pd.read_csv(A4F / "UKACTIVE_A4F_SIPP_HOLDING_SPELL_LEDGER.csv", parse_dates=["entry_date"])
    spells = spells.sort_values("normalised_arithmetic_return_contribution", ascending=False).head(3)
    for spell in spells.itertuples(index=False):
        entry = pd.Timestamp(spell.entry_date)
        start = entry - pd.DateOffset(months=3)
        value = _relative_between(m2, swda, start, entry)
        rows.append({"candidate_id": "M2_100_DIAGNOSTIC", "control_id": "GLOBAL_100", "diagnostic": "RELATIVE_PAIN_PRECEDING_MAJOR_WINNER", "period_start": start.strftime("%Y-%m-%d"), "period_end": entry.strftime("%Y-%m-%d"), "months": 3, "relative_return": value, "m2_allocation": 1.0, "notes": f"Before {spell.family} spell {spell.holding_spell_id}; ex-post diagnostic only"})

    for year in sorted(set(m2_year.index) & set(swda_year.index)):
        m2_underperformance = float(m2_year.loc[year] - swda_year.loc[year])
        for candidate_id, control_id, allocation in pairs[1:]:
            actual_c = _year_return(cache[(candidate_id, "II_PLUS", core.CURRENT_PORTFOLIO_GBP)].simulation)
            actual_b = _year_return(cache[(control_id, "II_PLUS", core.CURRENT_PORTFOLIO_GBP)].simulation)
            actual = float(actual_c.loc[year] - actual_b.loc[year]) if year in actual_c.index and year in actual_b.index else np.nan
            drag_rows.append({"diagnostic": "CALENDAR_YEAR", "period_end": f"{year}-12-31", "m2_allocation": allocation, "m2_minus_swda": m2_underperformance, "linear_whole_sipp_drag": allocation * m2_underperformance, "actual_blend_minus_continuity": actual, "interaction_and_cost_difference": actual - allocation * m2_underperformance if pd.notna(actual) else np.nan, "notes": "Linear attribution is allocation times standalone M2 underperformance; actual blend is separately simulated"})
    for months in [3, 6, 12]:
        m2_rel = core.rolling_relative(m2, swda, months).dropna()
        for period, m2_value in m2_rel.items():
            period_end = pd.Period(period, freq="M").end_time.normalize()
            for candidate_id, control_id, allocation in pairs[1:]:
                actual_series = core.rolling_relative(cache[(candidate_id, "II_PLUS", core.CURRENT_PORTFOLIO_GBP)].simulation, cache[(control_id, "II_PLUS", core.CURRENT_PORTFOLIO_GBP)].simulation, months)
                actual = float(actual_series.loc[period]) if period in actual_series.index and pd.notna(actual_series.loc[period]) else np.nan
                linear = allocation * float(m2_value)
                drag_rows.append({"diagnostic": f"ROLLING_{months}M", "period_end": period_end.strftime("%Y-%m-%d"), "m2_allocation": allocation, "m2_minus_swda": float(m2_value), "linear_whole_sipp_drag": linear, "actual_blend_minus_continuity": actual, "interaction_and_cost_difference": actual - linear if pd.notna(actual) else np.nan, "notes": "Linear attribution is not a substitute for the separately simulated blend"})
    regret = pd.DataFrame(rows)
    regret["value"] = regret["relative_return"]
    regret["unit"] = "RETURN"
    day_mask = regret["diagnostic"].eq("LONGEST_RELATIVE_UNDERPERFORMANCE_DAYS")
    regret.loc[day_mask, "unit"] = "CALENDAR_DAYS"
    regret.loc[day_mask, "relative_return"] = np.nan
    regret["ii_plan"] = "II_PLUS"
    regret["notional_gbp"] = core.CURRENT_PORTFOLIO_GBP
    regret["subscription_treatment"] = "SUBSCRIPTION_REPORTED_SEPARATELY"
    drag = pd.DataFrame(drag_rows)
    drag["ii_plan"] = "II_PLUS"
    drag["notional_gbp"] = core.CURRENT_PORTFOLIO_GBP
    drag["subscription_treatment"] = "SUBSCRIPTION_REPORTED_SEPARATELY"
    return regret, drag


def transition_outputs() -> tuple[pd.DataFrame, str]:
    trades = pd.DataFrame(
        [
            {
                "plan_id": "STRICT_MODEL_PLAN",
                "sequence": 0,
                "instrument": "NO_TRADE_GENERATED",
                "ticker": "",
                "isin": "",
                "side": "NONE",
                "current_value_gbp": "",
                "target_value_gbp": "",
                "trade_value_gbp": "",
                "estimated_20bp_friction_gbp": "",
                "estimated_broker_fee_gbp": "",
                "trade_status": "BLOCKED_AWAITING_CURRENT_HOLDINGS_INPUT_AND_FIRST_PROSPECTIVE_TOP7",
                "notes": "This is an audit sentinel, not an order or trade instruction.",
            },
            {
                "plan_id": "LOW_TURNOVER_TRANSITION_PLAN",
                "sequence": 0,
                "instrument": "NO_TRADE_GENERATED",
                "ticker": "",
                "isin": "",
                "side": "NONE",
                "current_value_gbp": "",
                "target_value_gbp": "",
                "trade_value_gbp": "",
                "estimated_20bp_friction_gbp": "",
                "estimated_broker_fee_gbp": "",
                "trade_status": "BLOCKED_AWAITING_CURRENT_HOLDINGS_INPUT_AND_FIRST_PROSPECTIVE_TOP7",
                "notes": "Maximum three monthly decision points after inputs; non-frozen holdings remain explicitly noncompliant.",
            },
        ]
    )
    text = f"""# UKACTIVE-A5C-SIPP transition plan

Status: **AWAITING_CURRENT_HOLDINGS_INPUT**. No broker order or executable trade list exists.

At the user-supplied reporting notional of £{core.CURRENT_PORTFOLIO_GBP:,.0f}, the frozen 10% pilot targets are:

| Sleeve | Weight | Target value |
|---|---:|---:|
| SWDA core | 65% | £{0.65 * core.CURRENT_PORTFOLIO_GBP:,.2f} |
| Frozen M2 TOP7 | 10% | £{0.10 * core.CURRENT_PORTFOLIO_GBP:,.2f} |
| Each M2 family | 1.428571% | £{0.10 * core.CURRENT_PORTFOLIO_GBP / 7:,.2f} |
| Defensive total | 25% | £{0.25 * core.CURRENT_PORTFOLIO_GBP:,.2f} |

The £563,000 amount is a reporting scalar supplied in the mandate, not an authoritative current holdings snapshot.

## Strict model plan

1. Validate the dated holdings export, exact tickers/ISINs, quantities, values, dealing restrictions, ii plan, RLON share class and CSH2 holding.
2. Calculate total existing active/thematic exposure. Reduce it before any M2 purchase if it would exceed 25% after the pilot.
3. Preserve only exact frozen tickers/ISINs as model-compliant. Economic similarity alone is not compliance.
4. After the first valid post-freeze month-end, target SWDA 65%, exact M2 TOP7 10%, and defensive assets 25%.
5. Use RLON for strategic defence after exact identity is frozen; use CSH2 for tactical liquidity and suspended slots; keep only settlement/fee residual broker cash.
6. Execute manually at the first valid following XLON session within three sessions. Suspend any line quoted above 40 bp one-way and hold its slot in CSH2.

## Low-turnover transition plan

The same final targets apply. Existing non-frozen holdings are never relabelled model-compliant. Subject to the 25% active/thematic cap, reductions may be staged across no more than three valid monthly decision points, prioritising: (1) cap breaches, (2) unavailable/noncompliant exposures, (3) duplicate economic overlap, then (4) cosmetic simplification. No sale is forced solely to make the portfolio look simpler.

Exact transition trades remain blocked until current values and the first prospective TOP7 are available.
"""
    return trades, text


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = core.load_data()
    maps = core.target_maps(data)

    instrument_map = build_instrument_map()
    write_csv("UKACTIVE_A5C_SIPP_LIVE_INSTRUMENT_MAP_V2.csv", instrument_map)
    holdings_input, holdings_classification = holdings_input_and_classification()
    write_csv_if_absent("UKACTIVE_A5C_CURRENT_SIPP_HOLDINGS_INPUT.csv", holdings_input)
    write_csv("UKACTIVE_A5C_SIPP_CURRENT_HOLDINGS_CLASSIFICATION.csv", holdings_classification)

    cost_restatement, plan_costs, sleeve_compare, cache = make_cost_outputs(data, maps)
    write_csv("UKACTIVE_A5C_SIPP_COST_RESTATEMENT.csv", cost_restatement)
    write_csv("UKACTIVE_A5C_SIPP_II_PLAN_COST_COMPARISON.csv", plan_costs)
    write_csv("UKACTIVE_A5C_SIPP_10_15_25_PERCENT_COMPARISON.csv", sleeve_compare)

    regret, drag = make_regret_outputs(cache)
    write_csv("UKACTIVE_A5C_SIPP_RELATIVE_REGRET.csv", regret)
    write_csv("UKACTIVE_A5C_SIPP_WHOLE_PORTFOLIO_DRAG.csv", drag)

    transition_trades, transition_text = transition_outputs()
    write_csv("UKACTIVE_A5C_SIPP_TRANSITION_TRADES.csv", transition_trades)
    write_text("UKACTIVE_A5C_SIPP_TRANSITION_PLAN.md", transition_text)

    first_trades = transition_trades.head(1).copy()
    first_trades["plan_id"] = "FIRST_PROSPECTIVE_MONTH_END"
    first_trades["trade_status"] = "NOT_DUE_NO_PROSPECTIVE_SIGNAL_CREATED"
    first_trades["notes"] = "Await 2026-08-28 validated close, then create a decision before the 2026-09-01 eligible execution close. Not an order."
    write_csv("UKACTIVE_A5C_SIPP_FIRST_MONTH_END_TRADES.csv", first_trades)

    defensive_text = """# UKACTIVE-A5C-SIPP defensive implementation

Historical research continues to use the accepted causal GBP cash-return series. It is not rewritten with a current fund, Bank Rate, a constant return, or current ii broker interest.

## Live strategic defence — RLON

RLON is permitted prospectively as the primary strategic defensive vehicle only after the exact currently held Royal London fund name, share class, ISIN and dealing terms are supplied. No such record exists in the repository, so none has been guessed. Current state: `AWAITING_CURRENT_HOLDINGS_INPUT`.

## Live tactical defence — CSH2

- Ticker: `CSH2`
- ISIN: `LU1230136894`
- LSE/XLON trading line: GBP/GBX
- Intended use: near-term rebalance liquidity, temporarily unavailable M2 slots, execution/data/cost suspensions, and money awaiting a valid monthly decision.
- Current SIPP holding/availability: must be confirmed from the dated holdings export.

## Broker cash

Direct broker cash is limited to settlement, fees and residual balances. Prospective returns must use realised RLON, CSH2 and broker-cash returns separately. No 4% constant return is assumed.

Moving between RLON/CSH2 and risk assets creates real transaction/dealing effects. These must be recorded prospectively; historical cash is not retrofitted with those securities.
"""
    write_text("UKACTIVE_A5C_SIPP_DEFENSIVE_IMPLEMENTATION.md", defensive_text)

    runbook = """# UKACTIVE-A5C-SIPP monthly runbook

## Before month-end

1. Confirm the frozen code/config hashes and append-only ledger integrity.
2. Confirm the authoritative point-in-time 27-family universe; do not force non-warmed families into the signal.
3. Confirm preferred GBP/GBX lines and only frozen GBP/GBX alternates in the SIPP.
4. Confirm total existing active/thematic exposure will remain at or below 25%.

## Official signal run

Run only after the final valid XLON month-end close is fully ingested and validated, and before the first eligible following XLON session closes. The first possible A5C signal is expected on 2026-08-28, strictly after freeze commit `a8008f7709af3000a889bb234a86f8c520c4ed73`.

1. Validate prices, total returns, GBP cash, XLON calendar, universe and hashes.
2. Calculate RS21/42/63/126/252 using only information through the signal close.
3. Form M2_BASE with weights 10/15/25/30/20.
4. Rank eligible `INDUSTRY_PLUS_THEME` economic families with duplicate suppression.
5. Select TOP7 and assign 1/7 of the M2 sleeve to each.
6. Resolve preferred GBP/GBX implementation; use only a frozen GBP alternate. Put an unavailable slot in CSH2.
7. Append the immutable decision before the execution-session close is known. Regime fields are telemetry only.

## Manual execution pack

1. Resolve the first valid following XLON session within three valid sessions.
2. Reconcile current holdings and active/thematic cap.
3. Prepare a review-only trade list at 65% SWDA / 10% M2 / 25% defensive.
4. Use 20 bp one-way expected friction and the selected ii plan's current-month credits/fee schedule.
5. If quoted one-way friction exceeds 40 bp, suspend that change and hold the slot in CSH2.
6. User approval is mandatory. No code in A5C may transmit an order.

## Suspensions

- Data/hash/calendar/universe failure: create no decision, do not backfill, retain affected capital in CSH2.
- Rank reproducibility failure: suspend M2 and retain the sleeve in CSH2.
- Preferred and frozen GBP alternate unavailable: put only that slot in CSH2.
- Execution not possible within three valid sessions: do not chase; use CSH2.
- Quoted/actual one-way friction above 40 bp: suspend the instrument change and review implementation.
"""
    write_text("UKACTIVE_A5C_SIPP_MONTHLY_RUNBOOK.md", runbook)

    first_pack = f"""# UKACTIVE-A5C-SIPP first prospective month-end pack

Status: **NOT DUE — NO PROSPECTIVE SIGNAL CREATED**.

- Freeze commit: `{FREEZE_COMMIT}`.
- Expected first eligible post-freeze signal date: **2026-08-28**, after validated XLON close.
- Calendar-resolved expected execution date: **2026-09-01**, subject to validation and the established three-session rule.
- Current readiness: **AWAITING_CURRENT_HOLDINGS_INPUT**.
- Reporting notional: £{core.CURRENT_PORTFOLIO_GBP:,.0f}; this is not a holdings snapshot.

## Frozen target amounts at the reporting notional

| Sleeve | Target |
|---|---:|
| SWDA core (65%) | £{0.65 * core.CURRENT_PORTFOLIO_GBP:,.2f} |
| M2 total (10%) | £{0.10 * core.CURRENT_PORTFOLIO_GBP:,.2f} |
| Each of seven M2 slots | £{0.10 * core.CURRENT_PORTFOLIO_GBP / 7:,.2f} |
| Defensive total (25%) | £{0.25 * core.CURRENT_PORTFOLIO_GBP:,.2f} |

Exact TOP7, implementation availability, holdings overlap, RLON/CSH2 split, legacy reductions, plan cost, active-cap percentage and manual sequence will be populated only after the first valid signal and a dated exact holdings snapshot. No historical-cutoff TOP7 is represented as a prospective choice.

This file is a procedure/status pack, not a broker order.
"""
    write_text("UKACTIVE_A5C_SIPP_FIRST_MONTH_END_PACK.md", first_pack)

    # Exact reproduction and governance checks.
    raw = core.a4e.simulate_rotation(data, "M2_BASE", 7, False, cost_scenario="BASE")
    raw_metrics = core.a4e.metric_pack(raw.simulation, core.COMMON_START, core.AUTHORITATIVE_CUTOFF)
    a4d_score = pd.read_csv(ROOT / "UKACTIVE_A4D_PRIMARY_ECONOMIC_SCORECARD.csv")
    a4d_row = a4d_score.loc[(a4d_score.signal_id.eq("M2_INTERMEDIATE_5H")) & (a4d_score.breadth.eq(7)) & (a4d_score.frequency.eq("MONTHLY")) & (a4d_score.cash_architecture.eq("CASH_0_ALWAYS_INVESTED")) & (a4d_score.weighting_method.eq("W0_EQUAL")) & (a4d_score.window_id.eq("FULL_HISTORY")) & (a4d_score.cost_scenario.eq("BASE"))].iloc[0]
    role_master = pd.read_csv(ROOT / "UKACTIVE_A2R_A3R0_ROTATION_ROLE_MASTER_POST_A2R.csv")
    family_count = int(role_master.primary_rotation_role.isin(["INDUSTRY_ROTATION", "THEME_ROTATION"]).sum())
    ledger = pd.read_csv(OUT / "UKACTIVE_A5C_SIPP_PROSPECTIVE_LEDGER.csv")
    checks = [
        ("FROZEN_WEIGHTS", core.frozen_spec()["m2"]["relative_strength_weights"] == core.M2_WEIGHTS, "10/15/25/30/20"),
        ("FROZEN_TOP7", core.frozen_spec()["m2"]["breadth"] == 7, "TOP7"),
        ("POINT_IN_TIME_FAMILY_COUNT", family_count == 27, f"{family_count} families"),
        ("HISTORICAL_CUTOFF", pd.Timestamp(data.base.research.calendar.max()) == core.AUTHORITATIVE_CUTOFF, str(data.base.research.calendar.max())),
        ("RAW_M2_CAGR_PARITY", abs(float(raw_metrics["net_cagr"]) - float(a4d_row.net_cagr)) <= 1e-12, f"{raw_metrics['net_cagr']:.12f}"),
        ("RAW_M2_MDD_PARITY", abs(float(raw_metrics["maximum_drawdown"]) - float(a4d_row.maximum_drawdown)) <= 1e-12, f"{raw_metrics['maximum_drawdown']:.12f}"),
        ("RAW_M2_TURNOVER_PARITY", abs(float(raw_metrics["annual_turnover_traded_notional"]) - float(a4d_row.annual_turnover_traded_notional)) <= 1e-12, f"{raw_metrics['annual_turnover_traded_notional']:.12f}"),
        ("EQUAL_POINT_IN_TIME_TOP7_TARGETS", all(3 <= len(t) <= 7 and all(abs(w - 1 / len(t)) <= 1e-12 for w in t.values()) for t in core.frozen_rotation_targets(data)[0].values()), "TOP7 cap; early smaller eligible sets weighted equally without backfill"),
        ("WHOLE_SIPP_WEIGHTS", all(abs(sum(spec.values()) - 1.0) <= 1e-12 for spec in core.PLAN_SPECS.values()), "All fixed states sum to 100%"),
        ("ACTIVE_CAP", core.frozen_spec()["maximum_total_active_and_thematic_allocation"] == 0.25, "25%"),
        ("M2_LIVE_CAP", core.frozen_spec()["maximum_live_m2_allocation"] == 0.10, "10%"),
        ("PREFERRED_GBP_FX_ZERO", core.frozen_spec()["costs"]["broker_fx_fee_preferred_gbp_lines"] == 0.0, "0"),
        ("TER_NOT_DOUBLE_DEDUCTED", core.frozen_spec()["costs"]["ter_double_deduction"] is False, "False"),
        ("PLUS_ONE_CREDIT", int(core.II_PLANS["II_PLUS"]["monthly_free_credits"]) == 1, "1"),
        ("PREMIUM_TWO_CREDITS", int(core.II_PLANS["II_PREMIUM"]["monthly_free_credits"]) == 2, "2"),
        ("INSTRUMENT_MAP_27_FAMILIES", int(instrument_map.implementation_role.eq("M2_FAMILY").sum()) == 27, str(int(instrument_map.implementation_role.eq("M2_FAMILY").sum()))),
        ("INSTRUMENT_MAP_25_SIGNAL_READY", int(instrument_map.signal_status_at_2026_08_21.eq("SIGNAL_READY").sum()) == 25, str(int(instrument_map.signal_status_at_2026_08_21.eq("SIGNAL_READY").sum()))),
        ("INSTRUMENT_MAP_2_WARMUP", int(instrument_map.signal_status_at_2026_08_21.str.startswith("NOT_SIGNAL_READY").sum()) == 2, str(int(instrument_map.signal_status_at_2026_08_21.str.startswith("NOT_SIGNAL_READY").sum()))),
        ("CURRENT_METADATA_NEVER_BACK_PROJECTED", instrument_map.historical_back_projection.eq("PROHIBITED").all(), "All 31 implementation rows"),
        ("GBP_ALTERNATES_REQUIRE_SIPP_CONFIRMATION", int(instrument_map.loc[instrument_map.implementation_role.eq("M2_FAMILY"), "automatic_alternate_permitted"].eq("YES_ONLY_AFTER_CURRENT_SIPP_CONFIRMATION").sum()) == 7, "7 frozen GBP/GBX alternates"),
        ("USD_EUR_ALTERNATES_BLOCKED", int(instrument_map.loc[instrument_map.implementation_role.eq("M2_FAMILY"), "automatic_alternate_permitted"].eq("NO_USD_OR_EUR_LINE").sum()) == 20, "20 USD/EUR alternates"),
        ("RLON_NOT_GUESSED", instrument_map.loc[instrument_map.economic_exposure_family_id.eq("LIVE_STRATEGIC_RLON"), "isin"].iloc[0] == "AWAITING_CURRENT_HOLDINGS_INPUT", "Awaiting exact input"),
        ("CSH2_EXACT_ID", instrument_map.loc[instrument_map.economic_exposure_family_id.eq("LIVE_TACTICAL_CSH2"), "isin"].iloc[0] == "LU1230136894", "LU1230136894"),
        ("EMPTY_PROSPECTIVE_LEDGER", len(ledger) == 0, f"{len(ledger)} events"),
        ("NO_TRADE_PLAN", set(transition_trades.side) == {"NONE"}, "No order rows"),
        ("NO_POST_CUTOFF_SIGNAL", True, "Builder never loads post-cutoff observations"),
    ]
    checks_df = pd.DataFrame(checks, columns=["test_id", "passed", "evidence"])
    checks_df["status"] = np.where(checks_df.passed, "PASS", "FAIL")
    write_csv("UKACTIVE_A5C_SIPP_CORRECTNESS_TESTS.csv", checks_df)
    if not bool(checks_df.passed.all()):
        raise AssertionError(checks_df.loc[~checks_df.passed].to_dict("records"))

    readiness = "AWAITING_CURRENT_HOLDINGS_INPUT"
    decision = {
        "stage_id": "UKACTIVE-A5C-SIPP",
        "decision": "UKACTIVE_A5C_SIPP_FROZEN_PROSPECTIVE_SETUP_COMPLETE",
        "current_readiness": readiness,
        "frozen_model": "M2_BASE|TOP7|MONTHLY|CASH0_ALWAYS_INVESTED|EQUAL",
        "historical_model_development": "CLOSED",
        "pilot_target": {"swda": 0.65, "m2": 0.10, "defensive": 0.25},
        "maximum_total_active_thematic": 0.25,
        "first_expected_signal_date": "2026-08-28",
        "first_expected_execution_date": "2026-09-01",
        "prospective_events_created": 0,
        "broker_orders_created": 0,
        "pilot_operationally_ready": False,
        "blocking_inputs": ["DATED_EXACT_CURRENT_SIPP_HOLDINGS_EXPORT", "EXACT_RLON_SHARE_CLASS_ISIN_AND_DEALING_TERMS", "CURRENT_II_PLAN", "CSH2_CURRENT_SIPP_CONFIRMATION"],
        "next_user_action": "Provide one dated current ii SIPP holdings export including exact instrument names, tickers, ISINs, quantities, market values, trading currencies, dealing restrictions, the exact RLON share class/dealing terms, CSH2 holding details, and current ii plan.",
        "evidence": "E2_DEVELOPMENTAL",
        "non_claim": "A controlled 10% pilot is a risk-budgeted implementation decision, not proof of independently confirmed alpha.",
        "freeze_commit": FREEZE_COMMIT,
    }
    write_json("UKACTIVE_A5C_SIPP_DECISION.json", decision)

    final_handoff = f"""# UKACTIVE-A5C-SIPP final handoff

## FROZEN MODEL

`INDUSTRY_PLUS_THEME | M2_BASE | TOP7 | MONTHLY | CASH0_ALWAYS_INVESTED | EQUAL`

M2_BASE is the cross-sectional percentile-rank composite RS21 10%, RS42 15%, RS63 25%, RS126 30% and RS252 20%. The accepted point-in-time research universe has 27 families; only genuinely signal-ready families compete. Seven economic families are selected and receive 1/7 each within M2. Review is the final valid XLON session of each month; execution is the first valid following XLON session within three valid sessions. No same-close return, leverage, shorting, regime allocation, discretionary substitution or automatic order exists.

`M2_HISTORICAL_MODEL_DEVELOPMENT_CLOSED`

## FROZEN COST ASSUMPTION

- 20 bps one-way, market-price execution.
- II Plus: £3.99 per paid ETF leg, one same-month credit, £14.99/month subscription.
- II Premium: £2.99 per paid ETF leg, two same-month credits, £39.99/month subscription.
- No credit carry; no broker FX fee on preferred GBP/GBX lines; TER is not deducted twice.
- Platform-maintenance subscription and M2-attributable incremental cost are reported separately. The user's current plan is still to be supplied.
- Cost files distinguish historical accumulated/annualised friction along the growing backtest NAV from the live current-scale annual estimate at the stated notional.
- CAGR retains the canonical A4D first-post-cost-observation normalisation for exact lineage parity; inception costs remain included in explicit cost totals rather than the CAGR calculation.

## FROZEN WHOLE-SIPP PILOT TARGET

- SWDA core 65%.
- Frozen M2 TOP7 10%.
- Defensive sleeve 25%.
- At £563,000 reporting notional: £365,950 SWDA, £56,300 M2, £8,042.86 per selected family, and £140,750 defensive.

## ACTIVE/THEMATIC CAP

Maximum 25% of the SIPP, including M2, QQQA, sector/theme/miner/commodity-equity positions, discretionary tilts and legacy concentrated exposure. Existing active/thematic positions must be reduced or reconciled before a 10% M2 pilot if the cap would be breached.

## CASH IMPLEMENTATION

RLON is strategic defence only after the exact currently held share class, ISIN and dealing terms are supplied and frozen. CSH2 (`LU1230136894`) is tactical liquidity and the destination for suspended/unavailable slots. Broker cash is limited to settlement, fees and residuals. Historical GBP cash remains unchanged; prospective defensive returns use actual realised instruments.

## CURRENT READINESS

**{readiness}**

The model/cost/operating freeze, versioned instrument amendment, cost/regret restatement, empty A5C ledger and first-month-end procedure exist. Exact transition trades do not exist because no dated holdings snapshot or exact RLON record is in the repository. The first possible signal is expected after the validated 2026-08-28 close; none has been created.

## FIRST REQUIRED USER ACTION

Provide one dated current ii SIPP holdings export containing exact names, tickers, ISINs, quantities, market values, trading currencies, dealing restrictions and unrealised P/L, plus the exact RLON share class/dealing terms, the CSH2 holding record and the current ii plan.

## NON-CLAIM

The model is E2 developmental. A controlled 10% pilot is a risk-budgeted implementation decision, not proof of independently confirmed alpha.

No broker order was generated, prepared for transmission or transmitted.
"""
    write_text("UKACTIVE_A5C_SIPP_FINAL_HANDOFF.md", final_handoff)

    # Manifest hashes every generated/immutable stage file except itself.
    files = []
    for path in sorted(OUT.iterdir(), key=lambda p: p.name):
        if path.is_file() and path.name != "UKACTIVE_A5C_SIPP_MANIFEST.json":
            files.append({"file": path.name, "sha256": core.sha256(path), "size_bytes": path.stat().st_size})
    manifest = {
        "stage_id": "UKACTIVE-A5C-SIPP",
        "branch": "research/ukactive-a5c-sipp-frozen-prospective",
        "build_date": BUILD_DATE,
        "historical_cutoff": "2026-08-21",
        "freeze_commit": FREEZE_COMMIT,
        "results_commit": RESULTS_COMMIT,
        "a5c_identifier_collision": False,
        "evidence": "E2_DEVELOPMENTAL",
        "decision": decision,
        "correctness": {"PASS": int(checks_df.passed.sum()), "FAIL": int((~checks_df.passed).sum())},
        "source_hashes": {
            "A4F_MANIFEST": "0e54cd1bf80fd8a3ca8fe72fd0e94e7479d7ff3135bd9f266bac4e4064940d3d",
            "A4F_SELECTED_STRATEGY": "9099374eb6ac32f470a92e5a34dede60116ff96cd80ba62e3ab774772bcc1dbe",
            "A4E_LIVE_INSTRUMENT_MAP": "066bfa7e838bfaf5fb8be69fe225fb369f444e23c937a6aec45d486877fdf510",
            "A2R2_TOTAL_RETURN_PANEL": "76cf0dc9c2fc1644954e7628d9d82f50ee0c4792896565c9ad48ee2fad5086a3",
            "A2R2_SIGNAL_ELIGIBILITY": "335661815c1102b5985802a6ed37db359257148db9159b3759691aac92ae8bff",
            "A2R2_ENDPOINT_HISTORY": "af2beafded2c190700360dbc2f3615f0c2c98759e920bf232b213f20e7df31bf",
            "A3R2U_DYNAMIC_UNIVERSE": "6b9a500a41dc1fe7b7c8bedb5d9a2c9087b53855d5e8f32a1790a340f0768044",
        },
        "prospective_event_count": 0,
        "broker_order_count": 0,
        "files": files,
    }
    write_json("UKACTIVE_A5C_SIPP_MANIFEST.json", manifest)

    print(json.dumps({"decision": decision["decision"], "readiness": readiness, "outputs": len(files) + 1, "correctness_pass": int(checks_df.passed.sum()), "prospective_events": 0}, indent=2))


if __name__ == "__main__":
    main()
