"""UKACTIVE-A4 scoped implementation and eligibility reconstruction.

The module reconstructs the exact implementation identities used by the frozen
A4 candidates.  It intentionally keeps three questions separate:

1. Was the historical implementation/return line economically valid?
2. Is there evidence that the exact line was UK-retail / ISA eligible then?
3. Is a current implementation confirmed by Interactive Investor now?

No current answer is back-projected.  No order, broker query, or portfolio-rule
change is performed.
"""

from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow

from build_ukactive_a3r2s import evaluate_bundle, window_bounds
from build_ukactive_a4_forensics import make_bundle, next_valid_endpoint
from ukactive_a3r2_core import (
    PROGRAMME_ROOT,
    audit_file,
    git_output,
    sha256_file,
    stable_id,
    utc_now,
    write_csv,
    write_json,
    write_text,
)
from ukactive_a3r2_portfolio import load_research_data


RUN_ID = "UKACTIVE-A4-IMPLEMENTATION-20260823-001"
PREFIX = "UKACTIVE_A4"
EVIDENCE_CONFIG = PROGRAMME_ROOT / "config" / "UKACTIVE_A4_IMPLEMENTATION_EVIDENCE_v1.json"
FEATURE_PATH = PROGRAMME_ROOT / "UKACTIVE_A3R2_FEATURE_PANEL.parquet"
SNAPSHOT_PATH = PROGRAMME_ROOT / "UKACTIVE_A3R2U_CURRENT_UNIVERSE_SNAPSHOT.csv"
QUEUE_PATH = PROGRAMME_ROOT / "UKACTIVE_A3R0_CHATGPT_IBKR_VERIFICATION_QUEUE_POST_A2R.csv"
PANEL_PATH = PROGRAMME_ROOT / "UKACTIVE_A2R2_CORRECTED_TOTAL_RETURN_PANEL_GBP.parquet"
ENDPOINT_PATH = PROGRAMME_ROOT / "UKACTIVE_A2R2_SIGNAL_ENDPOINT_HISTORY.parquet"
A2_INSTRUMENT_PATH = PROGRAMME_ROOT / "UKACTIVE_A2_INSTRUMENT_HISTORY_MASTER.parquet"
A2R_INSTRUMENT_PATH = PROGRAMME_ROOT / "UKACTIVE_A2R_CORRECTED_IMPLEMENTATION_HISTORY.parquet"


MODEL_SPECS = [
    {
        "model_id": "A4_PRIMARY",
        "scope": "FROZEN_PRIMARY",
        "pool_id": "INDUSTRY_PLUS_THEME",
        "signal_id": "MH_LEVEL_3_6_12_REFERENCE",
        "selection_rule": "TOP_1",
    },
    {
        "model_id": "A4_CONCENTRATION_TOP_2",
        "scope": "FROZEN_CONCENTRATION_CONTROL",
        "pool_id": "INDUSTRY_PLUS_THEME",
        "signal_id": "MH_LEVEL_3_6_12_REFERENCE",
        "selection_rule": "TOP_2",
    },
    {
        "model_id": "A4_CONCENTRATION_TOP_3",
        "scope": "FROZEN_CONCENTRATION_CONTROL",
        "pool_id": "INDUSTRY_PLUS_THEME",
        "signal_id": "MH_LEVEL_3_6_12_REFERENCE",
        "selection_rule": "TOP_3",
    },
    {
        "model_id": "A4_NEIGHBOUR_1",
        "scope": "FROZEN_NEIGHBOUR",
        "pool_id": "INDUSTRY",
        "signal_id": "MH_LEVEL_3_6_12_REFERENCE",
        "selection_rule": "TOP_1",
    },
    {
        "model_id": "A4_NEIGHBOUR_2",
        "scope": "FROZEN_NEIGHBOUR",
        "pool_id": "INDUSTRY",
        "signal_id": "PAIRWISE_MAJORITY_5H",
        "selection_rule": "TOP_1",
    },
]


def out(name: str) -> Path:
    return PROGRAMME_ROOT / f"{PREFIX}_{name}"


def _normalise_date(value: Any) -> pd.Timestamp | pd.NaT:
    return pd.to_datetime(value, errors="coerce")


def _identity_master() -> pd.DataFrame:
    columns = [
        "date",
        "listing_id",
        "share_class_id",
        "fund_entity_id",
        "economic_exposure_family_id",
        "ticker",
        "isin",
        "mic",
        "listing_currency",
        "price_unit",
        "first_observed_date",
        "last_observed_date",
        "route_type",
        "source_vendor",
        "source_series_identifier",
        "listing_active",
        "total_return_validation_status",
    ]
    frames = []
    for path, lineage_source in [(A2_INSTRUMENT_PATH, "A2"), (A2R_INSTRUMENT_PATH, "A2R")]:
        frame = pd.read_parquet(path, columns=columns)
        frame["lineage_source"] = lineage_source
        frames.append(frame)
    combined = pd.concat(frames, ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"])
    combined["first_observed_date"] = pd.to_datetime(combined["first_observed_date"], errors="coerce")
    combined["last_observed_date"] = pd.to_datetime(combined["last_observed_date"], errors="coerce")
    combined = combined.sort_values(["listing_id", "share_class_id", "date", "lineage_source"])
    return combined.drop_duplicates(["listing_id", "share_class_id"], keep="last").reset_index(drop=True)


def _identity_lookup(identity: pd.DataFrame, listing_id: str, share_class_id: str) -> dict[str, Any]:
    match = identity.loc[
        identity["listing_id"].astype(str).eq(str(listing_id))
        & identity["share_class_id"].astype(str).eq(str(share_class_id))
    ]
    if match.empty:
        return {}
    return match.iloc[0].to_dict()


def _share_and_fund_metadata() -> tuple[pd.DataFrame, pd.DataFrame]:
    share = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A0A1_SHARE_CLASS_MASTER.csv", dtype=str).set_index("share_class_id")
    fund = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A0A1_FUND_MASTER.csv", dtype=str).set_index("fund_entity_id")
    return share, fund


def _metadata_for_identity(
    identity_row: dict[str, Any], share: pd.DataFrame, fund: pd.DataFrame, evidence: dict[str, Any]
) -> dict[str, Any]:
    share_id = str(identity_row.get("share_class_id", ""))
    fund_id = str(identity_row.get("fund_entity_id", ""))
    isin = str(identity_row.get("isin", ""))
    share_row = share.loc[share_id] if share_id in share.index else None
    fund_row = fund.loc[fund_id] if fund_id in fund.index else None
    exact = evidence["exact_historical_isin_evidence"].get(isin, {})
    return {
        "legal_fund_name": (
            str(fund_row.get("legal_fund_name")) if fund_row is not None else exact.get("product", "NOT_AVAILABLE")
        ),
        "share_class_name": (
            str(share_row.get("share_class_name")) if share_row is not None else exact.get("product", "NOT_AVAILABLE")
        ),
        "provider_issuer": (
            str(share_row.get("provider_issuer"))
            if share_row is not None
            else (str(fund_row.get("provider_issuer")) if fund_row is not None else "NOT_AVAILABLE")
        ),
        "product_structure": str(share_row.get("product_structure")) if share_row is not None else "NOT_VERIFIED",
        "instrument_type": str(share_row.get("instrument_type")) if share_row is not None else "ETF",
        "ucits_status_local_master": str(share_row.get("ucits_status")) if share_row is not None else "NOT_DETERMINED",
        "benchmark_index": str(share_row.get("benchmark_index")) if share_row is not None else "NOT_AVAILABLE",
        "share_class_inception_date": (
            str(share_row.get("share_class_inception_date")) if share_row is not None else "NOT_AVAILABLE"
        ),
    }


def _historical_evidence(
    isin: str, execution_date: pd.Timestamp | pd.NaT, evidence: dict[str, Any]
) -> dict[str, Any]:
    exact = evidence["exact_historical_isin_evidence"].get(str(isin))
    if exact is None or pd.isna(execution_date):
        return {
            "historical_uk_retail_status": "HISTORICALLY_UNCERTAIN" if pd.notna(execution_date) else "NOT_APPLICABLE_NOT_EXECUTED",
            "historical_isa_status": "HISTORICALLY_UNCERTAIN_ISA" if pd.notna(execution_date) else "NOT_APPLICABLE_NOT_EXECUTED",
            "historical_platform_status": "HISTORICALLY_UNCERTAIN",
            "historical_evidence_basis": "No date-matched public eligibility evidence captured for this exact implementation route.",
            "historical_isa_basis": "No product/account-specific historical ISA evidence captured.",
            "historical_evidence_urls": "NOT_AVAILABLE",
            "official_issue_date": pd.NaT,
            "ucits_evidence_status": "NOT_DETERMINED",
        }
    issue_date = pd.Timestamp(exact["issue_date"])
    if pd.Timestamp(execution_date) < issue_date:
        retail = "KNOWN_NOT_ELIGIBLE"
        isa = "KNOWN_NOT_ISA_ELIGIBLE"
    else:
        retail = exact["historical_uk_retail_status"]
        isa = exact["historical_isa_status"]
        document_date = _normalise_date(exact.get("retail_document_date"))
        if retail == "HISTORICALLY_VERIFIED_UK_RETAIL" and (pd.isna(document_date) or document_date > execution_date):
            retail = "HISTORICALLY_PROBABLE_UK_RETAIL"
    return {
        "historical_uk_retail_status": retail,
        "historical_isa_status": isa,
        "historical_platform_status": "HISTORICALLY_UNCERTAIN",
        "historical_evidence_basis": exact["retail_basis"],
        "historical_isa_basis": exact["isa_basis"],
        "historical_evidence_urls": ";".join(exact["source_urls"]),
        "official_issue_date": issue_date,
        "ucits_evidence_status": exact["ucits_status"],
    }


def _bundle_set(data: Any, features: pd.DataFrame, snapshot: pd.DataFrame, start: pd.Timestamp) -> dict[str, dict[str, Any]]:
    bundles = {}
    for spec in MODEL_SPECS:
        bundles[spec["model_id"]] = make_bundle(
            data,
            features,
            snapshot,
            pool_id=spec["pool_id"],
            signal_id=spec["signal_id"],
            selection_rule=spec["selection_rule"],
            start=start,
        )
    return bundles


def build_selected_instrument_history(
    bundles: dict[str, dict[str, Any]],
    data: Any,
    panel: pd.DataFrame,
    endpoint: pd.DataFrame,
    identity: pd.DataFrame,
    share: pd.DataFrame,
    fund: pd.DataFrame,
    evidence: dict[str, Any],
) -> pd.DataFrame:
    panel_index = panel.set_index(["date", "economic_exposure_family_id"])
    endpoint_index = endpoint.set_index(["date", "economic_exposure_family_id"])
    spec_index = {spec["model_id"]: spec for spec in MODEL_SPECS}
    rows: list[dict[str, Any]] = []
    for model_id, bundle in bundles.items():
        spec = spec_index[model_id]
        trades = bundle["selected_net"].trades.copy()
        trades["review_date"] = pd.to_datetime(trades["review_date"])
        trade_index = trades.set_index("review_date")
        for review_date, targets in sorted(bundle["targets"].items()):
            review_date = pd.Timestamp(review_date)
            trade = trade_index.loc[review_date] if review_date in trade_index.index else None
            if trade is not None:
                execution_date = _normalise_date(trade["execution_date"])
                execution_status = str(trade["execution_status"])
            else:
                execution_date, _ = next_valid_endpoint(data, review_date, targets.keys())
                execution_status = "NO_SWITCH_REVIEW" if pd.notna(execution_date) else "CANCELLED_PANEL_END_NO_EXECUTION_SESSION"
            for family, weight in sorted(targets.items()):
                panel_row: dict[str, Any] = {}
                endpoint_row: dict[str, Any] = {}
                if pd.notna(execution_date) and (execution_date, family) in panel_index.index:
                    value = panel_index.loc[(execution_date, family)]
                    if isinstance(value, pd.DataFrame):
                        value = value.iloc[0]
                    panel_row = value.to_dict()
                if pd.notna(execution_date) and (execution_date, family) in endpoint_index.index:
                    value = endpoint_index.loc[(execution_date, family)]
                    if isinstance(value, pd.DataFrame):
                        value = value.iloc[0]
                    endpoint_row = value.to_dict()
                listing_id = str(endpoint_row.get("listing_id", panel_row.get("implementation_listing_id", "NOT_APPLICABLE_NOT_EXECUTED")))
                share_id = str(endpoint_row.get("share_class_id", panel_row.get("implementation_share_class_id", "NOT_APPLICABLE_NOT_EXECUTED")))
                identity_row = _identity_lookup(identity, listing_id, share_id)
                metadata = _metadata_for_identity(identity_row, share, fund, evidence) if identity_row else {
                    "legal_fund_name": "NOT_APPLICABLE_NOT_EXECUTED",
                    "share_class_name": "NOT_APPLICABLE_NOT_EXECUTED",
                    "provider_issuer": "NOT_APPLICABLE_NOT_EXECUTED",
                    "product_structure": "NOT_APPLICABLE_NOT_EXECUTED",
                    "instrument_type": "NOT_APPLICABLE_NOT_EXECUTED",
                    "ucits_status_local_master": "NOT_APPLICABLE_NOT_EXECUTED",
                    "benchmark_index": "NOT_APPLICABLE_NOT_EXECUTED",
                    "share_class_inception_date": "NOT_APPLICABLE_NOT_EXECUTED",
                }
                isin = str(identity_row.get("isin", "NOT_APPLICABLE_NOT_EXECUTED")) if identity_row else "NOT_APPLICABLE_NOT_EXECUTED"
                historical = _historical_evidence(isin, execution_date, evidence)
                first_observed = _normalise_date(identity_row.get("first_observed_date")) if identity_row else pd.NaT
                instrument_existed = bool(pd.notna(execution_date) and pd.notna(first_observed) and execution_date >= first_observed)
                rows.append(
                    {
                        "model_id": model_id,
                        "model_scope": spec["scope"],
                        "pool_id": spec["pool_id"],
                        "signal_id": spec["signal_id"],
                        "selection_rule": spec["selection_rule"],
                        "signal_date": review_date,
                        "execution_date": execution_date,
                        "execution_status": execution_status,
                        "economic_exposure_family_id": family,
                        "target_weight": float(weight),
                        "implementation_share_class_id": share_id,
                        "implementation_listing_id": listing_id,
                        "fund_entity_id": str(identity_row.get("fund_entity_id", "NOT_APPLICABLE_NOT_EXECUTED")) if identity_row else "NOT_APPLICABLE_NOT_EXECUTED",
                        "legal_fund_name": metadata["legal_fund_name"],
                        "share_class_name": metadata["share_class_name"],
                        "provider_issuer": metadata["provider_issuer"],
                        "isin": isin,
                        "ticker": str(identity_row.get("ticker", "NOT_APPLICABLE_NOT_EXECUTED")) if identity_row else "NOT_APPLICABLE_NOT_EXECUTED",
                        "mic": str(identity_row.get("mic", "NOT_APPLICABLE_NOT_EXECUTED")) if identity_row else "NOT_APPLICABLE_NOT_EXECUTED",
                        "listing_currency": str(identity_row.get("listing_currency", "NOT_APPLICABLE_NOT_EXECUTED")) if identity_row else "NOT_APPLICABLE_NOT_EXECUTED",
                        "price_unit": str(identity_row.get("price_unit", "NOT_APPLICABLE_NOT_EXECUTED")) if identity_row else "NOT_APPLICABLE_NOT_EXECUTED",
                        "product_structure": metadata["product_structure"],
                        "instrument_type": metadata["instrument_type"],
                        "ucits_status_local_master": metadata["ucits_status_local_master"],
                        "ucits_evidence_status": historical["ucits_evidence_status"],
                        "benchmark_index": metadata["benchmark_index"],
                        "share_class_inception_date": metadata["share_class_inception_date"],
                        "official_issue_date": historical["official_issue_date"],
                        "first_valid_implementation_observation": first_observed,
                        "last_valid_implementation_observation": _normalise_date(identity_row.get("last_observed_date")) if identity_row else pd.NaT,
                        "fund_exists": instrument_existed,
                        "share_class_exists": instrument_existed,
                        "lse_listing_exists": instrument_existed and str(identity_row.get("mic")) == "XLON" if identity_row else False,
                        "a2r2_eligible_state": str(panel_row.get("eligible_state", "NOT_APPLICABLE_NOT_EXECUTED")),
                        "a2r2_eligibility_confidence": str(panel_row.get("eligibility_confidence", "NOT_APPLICABLE_NOT_EXECUTED")),
                        "a2r2_endpoint_selection_source": str(endpoint_row.get("selection_source", "NOT_APPLICABLE_NOT_EXECUTED")),
                        "a2r2_endpoint_continuity_reason": str(endpoint_row.get("continuity_reason", "NOT_APPLICABLE_NOT_EXECUTED")),
                        "a2r2_data_valid": bool(endpoint_row.get("endpoint_valid", panel_row.get("data_valid", False))),
                        "a2r2_stale_flag": bool(endpoint_row.get("stale_flag", panel_row.get("stale_flag", False))),
                        "a2r2_missing_flag": bool(endpoint_row.get("missing_flag", panel_row.get("missing_flag", False))),
                        "a2r2_proxy_flag": bool(endpoint_row.get("proxy_flag", panel_row.get("proxy_flag", False))),
                        "source_vendor": str(identity_row.get("source_vendor", "NOT_APPLICABLE_NOT_EXECUTED")) if identity_row else "NOT_APPLICABLE_NOT_EXECUTED",
                        "source_series_identifier": str(identity_row.get("source_series_identifier", "NOT_APPLICABLE_NOT_EXECUTED")) if identity_row else "NOT_APPLICABLE_NOT_EXECUTED",
                        "return_validation_status": str(identity_row.get("total_return_validation_status", "NOT_APPLICABLE_NOT_EXECUTED")) if identity_row else "NOT_APPLICABLE_NOT_EXECUTED",
                        "historical_uk_retail_status": historical["historical_uk_retail_status"],
                        "historical_isa_status": historical["historical_isa_status"],
                        "historical_platform_status": historical["historical_platform_status"],
                        "historical_evidence_basis": historical["historical_evidence_basis"],
                        "historical_isa_basis": historical["historical_isa_basis"],
                        "historical_evidence_urls": historical["historical_evidence_urls"],
                        "current_status_back_projected": "NO",
                        "warning": "CURRENT ELIGIBILITY AND CURRENT II STATUS MUST NOT BE BACK-PROJECTED HISTORICALLY",
                    }
                )
    result = pd.DataFrame(rows).sort_values(["model_id", "signal_date", "economic_exposure_family_id"]).reset_index(drop=True)
    return result


def build_evidence_tables(history: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    columns = [
        "model_id",
        "signal_date",
        "execution_date",
        "economic_exposure_family_id",
        "isin",
        "ticker",
        "mic",
        "official_issue_date",
        "first_valid_implementation_observation",
        "historical_platform_status",
        "historical_evidence_urls",
        "current_status_back_projected",
        "warning",
    ]
    retail = history[columns + ["historical_uk_retail_status", "historical_evidence_basis", "ucits_evidence_status"]].copy()
    retail = retail.rename(columns={"historical_evidence_basis": "status_basis"})
    isa = history[columns + ["historical_isa_status", "historical_isa_basis", "ucits_evidence_status"]].copy()
    isa = isa.rename(columns={"historical_isa_basis": "status_basis"})
    return retail, isa


def build_current_implementation(
    features: pd.DataFrame, snapshot: pd.DataFrame, queue: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    combined = features.loc[
        features["cadence"].eq("MONTHLY") & features["analysis_context_id"].eq("INDUSTRY_PLUS_THEME")
    ].copy()
    last_date = pd.Timestamp(combined["date"].max())
    current_features = combined.loc[combined["date"].eq(last_date), [
        "economic_exposure_family_id", "primary_rotation_role", "MH_LEVEL_3_6_12_REFERENCE"
    ]].drop_duplicates("economic_exposure_family_id")
    current_features["current_pool_member"] = True
    current_features["current_signal_eligible"] = current_features["MH_LEVEL_3_6_12_REFERENCE"].notna()
    reference = pd.DataFrame(
        {
            "economic_exposure_family_id": ["GLOBAL_DEVELOPED_WORLD", "GLOBAL_ALL_WORLD"],
            "primary_rotation_role": ["BENCHMARK_REFERENCE", "BENCHMARK_REFERENCE"],
            "MH_LEVEL_3_6_12_REFERENCE": [np.nan, np.nan],
            "current_pool_member": [False, False],
            "current_signal_eligible": [False, False],
        }
    )
    scope = pd.concat([current_features, reference], ignore_index=True)
    preferred_queue = queue.loc[queue["preferred_or_alternate"].eq("PREFERRED")].drop_duplicates("economic_exposure_family_id")
    alternate_queue = queue.loc[queue["preferred_or_alternate"].eq("ALTERNATE")].drop_duplicates("economic_exposure_family_id")
    snapshot_index = snapshot.set_index("economic_exposure_family_id")
    preferred_index = preferred_queue.set_index("economic_exposure_family_id")
    alternate_index = alternate_queue.set_index("economic_exposure_family_id")
    rows = []
    for item in scope.itertuples(index=False):
        family = item.economic_exposure_family_id
        snap = snapshot_index.loc[family] if family in snapshot_index.index else pd.Series(dtype=object)
        pref = preferred_index.loc[family] if family in preferred_index.index else pd.Series(dtype=object)
        alt = alternate_index.loc[family] if family in alternate_index.index else pd.Series(dtype=object)
        ii_status = str(snap.get("II_CURRENT_TRADABLE", "NOT_CHECKED"))
        lse_status = str(snap.get("LSE_current_status", "NOT_CONFIRMED"))
        disclosure = str(snap.get("UK_retail_disclosure_status", "UNCERTAIN"))
        isa_rules = str(snap.get("public_ISA_rules_status", "UNCERTAIN"))
        if ii_status == "CONFIRMED_BY_USER":
            implementation_state = "CURRENT_II_CONFIRMED"
        elif lse_status == "CONFIRMED" and disclosure == "CURRENT_DISCLOSURE_CONFIRMED" and isa_rules == "RULES_ELIGIBLE":
            implementation_state = "CURRENT_PUBLIC_UK_ELIGIBLE_II_UNCHECKED"
        else:
            implementation_state = "CURRENT_IMPLEMENTATION_UNRESOLVED"
        rows.append(
            {
                "economic_exposure_family_id": family,
                "economic_exposure_name": str(snap.get("economic_exposure_name", family)),
                "rotation_role": item.primary_rotation_role,
                "current_pool_member": bool(item.current_pool_member),
                "current_signal_eligible": bool(item.current_signal_eligible),
                "as_of_date": last_date,
                "preferred_ticker": str(snap.get("ticker", pref.get("ticker", "NOT_AVAILABLE"))),
                "preferred_isin": str(snap.get("isin", pref.get("ISIN", "NOT_AVAILABLE"))),
                "preferred_listing_id": str(snap.get("listing_id", pref.get("listing_id", "NOT_AVAILABLE"))),
                "preferred_share_class_id": str(snap.get("share_class_id", pref.get("share_class_id", "NOT_AVAILABLE"))),
                "preferred_mic": str(snap.get("mic", pref.get("expected_MIC", "NOT_AVAILABLE"))),
                "preferred_listing_currency": str(snap.get("listing_currency", pref.get("listing_currency", "NOT_AVAILABLE"))),
                "preferred_price_unit": str(snap.get("price_unit", pref.get("GBP_GBX_unit", "NOT_AVAILABLE"))),
                "alternate_ticker": str(alt.get("ticker", "NOT_AVAILABLE")),
                "alternate_isin": str(alt.get("ISIN", "NOT_AVAILABLE")),
                "alternate_mic": str(alt.get("expected_MIC", "NOT_AVAILABLE")),
                "alternate_listing_currency": str(alt.get("listing_currency", "NOT_AVAILABLE")),
                "alternate_price_unit": str(alt.get("GBP_GBX_unit", "NOT_AVAILABLE")),
                "lse_current_status": lse_status,
                "uk_retail_disclosure_status": disclosure,
                "public_isa_rules_status": isa_rules,
                "ii_current_tradable": ii_status,
                "ii_observation_date": str(snap.get("II_OBSERVATION_DATE", "NOT_APPLICABLE")),
                "ii_confirmed_alternate_tickers": str(snap.get("II_CONFIRMED_ALTERNATE_TICKERS", "NOT_APPLICABLE")),
                "ii_user_implementation_preference": str(snap.get("II_USER_IMPLEMENTATION_PREFERENCE", "NOT_STATED")),
                "current_implementation_state": implementation_state,
                "public_evidence_urls": str(snap.get("public_evidence_URLs", pref.get("public_evidence_URLs", "NOT_AVAILABLE"))),
                "public_evidence_date": str(snap.get("public_evidence_date", pref.get("public_evidence_date", "NOT_AVAILABLE"))),
                "public_evidence_confidence": str(snap.get("public_evidence_confidence", pref.get("public_evidence_confidence", "NOT_AVAILABLE"))),
                "deployment_confirmation_required": implementation_state != "CURRENT_II_CONFIRMED",
                "current_only_metadata": "YES",
                "historical_back_projection": "PROHIBITED",
                "warning": "CURRENT II CONFIRMATION IS USER-SUPPLIED AS OF 2026-08-23 AND IS NOT HISTORICAL EVIDENCE",
            }
        )
    current = pd.DataFrame(rows).sort_values(["current_pool_member", "economic_exposure_family_id"], ascending=[False, True]).reset_index(drop=True)
    gaps = current.loc[current["current_signal_eligible"] & ~current["current_implementation_state"].eq("CURRENT_II_CONFIRMED")].copy()
    gaps["gap_reason"] = np.where(
        gaps["current_implementation_state"].eq("CURRENT_PUBLIC_UK_ELIGIBLE_II_UNCHECKED"),
        "PUBLIC_RULES_AND_DISCLOSURE_SUPPORT_EXISTS_BUT_II_NOT_CHECKED",
        "CURRENT_RETAIL_OR_ISA_OR_II_EVIDENCE_INCOMPLETE",
    )
    gaps["deployment_effect"] = "BLOCKS_DEPLOYMENT; DOES_NOT_BLOCK_PROSPECTIVE_RESEARCH_SHADOW"
    return current, gaps


def build_cost_and_execution_results(
    data: Any,
    features: pd.DataFrame,
    snapshot: pd.DataFrame,
    bounds: tuple[pd.Timestamp, pd.Timestamp],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    cost_rows = []
    baseline_bundle = None
    for bps in [10.0, 20.0, 40.0]:
        for sleeve in [100_000.0, 250_000.0, 500_000.0]:
            bundle = make_bundle(
                data,
                features,
                snapshot,
                pool_id="INDUSTRY_PLUS_THEME",
                signal_id="MH_LEVEL_3_6_12_REFERENCE",
                selection_rule="TOP_1",
                start=bounds[0],
                friction_bps=bps,
                fixed_fee=3.99,
                sleeve_size=sleeve,
                fx_rate=0.0075,
            )
            metrics = evaluate_bundle(bundle, bounds, data)
            if bps == 20.0 and sleeve == 250_000.0:
                baseline_bundle = bundle
            cost_rows.append(
                {
                    "candidate_id": "A4_PRIMARY",
                    "window": "LATEST_5Y",
                    "one_way_friction_bps": bps,
                    "ii_fixed_fee_gbp_per_trade_leg": 3.99,
                    "sleeve_size_gbp": sleeve,
                    "non_gbp_fx_rate": 0.0075,
                    "preferred_lines_non_gbp_in_frozen_snapshot": 0,
                    "gross_cagr": metrics["selected_gross_cagr"],
                    "net_cagr": metrics["selected_net_cagr"],
                    "global_benchmark_cagr": metrics["global_benchmark_cagr"],
                    "equal_weight_pool_cagr": metrics["equal_pool_cagr"],
                    "net_excess_vs_global_cagr": metrics["selected_net_excess_vs_global_cagr"],
                    "net_excess_vs_equal_pool_cagr": metrics["selected_net_excess_vs_pool_cagr"],
                    "maximum_drawdown": metrics["selected_net_maximum_drawdown"],
                    "annual_turnover_traded_notional": metrics["selected_net_annual_turnover_traded_notional"],
                    "executed_trade_legs": metrics["selected_net_trade_legs"],
                    "total_transaction_cost_rate": metrics["selected_net_total_transaction_cost_rate"],
                    "cost_evidence": "CURRENT_II_CHARGES_SENSITIVITY_NOT_REALIZED_HISTORICAL_SPREAD",
                }
            )
    assert baseline_bundle is not None
    baseline_metrics = evaluate_bundle(baseline_bundle, bounds, data)
    execution = pd.DataFrame(
        [
            {
                "execution_model": "CANONICAL_NEXT_ELIGIBLE_SESSION_ENDPOINT",
                "status": "VALIDATED_AND_EXECUTED",
                "same_close_allowed": False,
                "gross_cagr": baseline_metrics["selected_gross_cagr"],
                "net_cagr_20bps_250k": baseline_metrics["selected_net_cagr"],
                "maximum_execution_lag_xlon_sessions": 3,
                "reason": "Frozen A2R2/A3R2 next-eligible-session endpoint contract retained exactly.",
            },
            {
                "execution_model": "NEXT_OPEN",
                "status": "NOT_RUN_NO_VALIDATED_NEXT_OPEN_ROUTE",
                "same_close_allowed": False,
                "gross_cagr": np.nan,
                "net_cagr_20bps_250k": np.nan,
                "maximum_execution_lag_xlon_sessions": np.nan,
                "reason": "Raw open fields have not passed an execution-price validation chain; no fabricated open result is reported.",
            },
            {
                "execution_model": "CONSERVATIVE_LATER_SESSION_PRICE",
                "status": "NOT_RUN_NOT_PREDECLARED_AND_NO_VALIDATED_FILL_POLICY",
                "same_close_allowed": False,
                "gross_cagr": np.nan,
                "net_cagr_20bps_250k": np.nan,
                "maximum_execution_lag_xlon_sessions": np.nan,
                "reason": "A later-session fill policy was not invented after observing A3R2/A4 results.",
            },
        ]
    )
    return pd.DataFrame(cost_rows), execution, baseline_bundle


def evidence_ledger(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    retrieved_at = utc_now()
    rows = []
    for isin, item in evidence["exact_historical_isin_evidence"].items():
        for url in item["source_urls"]:
            rows.append(
                {
                    "evidence_id": stable_id("A4-EVD", isin, url),
                    "evidence_type": "A4_EXACT_IMPLEMENTATION_PRIMARY_OR_OFFICIAL_MARKET_REFERENCE",
                    "source_tier": "PRIMARY_OR_OFFICIAL_MARKET",
                    "publisher": url.split("/")[2],
                    "title": f"Exact implementation evidence: {item['product']}",
                    "url": url,
                    "retrieved_at": retrieved_at,
                    "observation_date": evidence["observation_date"],
                    "source_sha256": "NOT_CAPTURED_REMOTE_REFERENCE",
                    "local_capture": "URL_AND_RETRIEVAL_METADATA_ONLY",
                    "supports": f"Identity, issue/listing or retail-document evidence for {isin}",
                    "historical_eligibility_supported": "LIMITED_AS_CLASSIFIED_IN_A4_TABLES",
                    "confidence": "HIGH_IDENTITY_VARIABLE_ELIGIBILITY",
                    "warning": "CURRENT EVIDENCE IS NOT BACK-PROJECTED; SEE EPISODE STATUS",
                }
            )
    for item in evidence["common_primary_sources"]:
        rows.append(
            {
                "evidence_id": item["source_id"],
                "evidence_type": "A4_COMMON_POLICY_SOURCE",
                "source_tier": "PRIMARY",
                "publisher": item["publisher"],
                "title": item["title"],
                "url": item["url"],
                "retrieved_at": retrieved_at,
                "observation_date": evidence["observation_date"],
                "source_sha256": "NOT_CAPTURED_REMOTE_REFERENCE",
                "local_capture": "URL_AND_RETRIEVAL_METADATA_ONLY",
                "supports": item["supports"],
                "historical_eligibility_supported": "NO_AUTOMATIC_BACK_PROJECTION",
                "confidence": "HIGH",
                "warning": "CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY",
            }
        )
    rows.append(
        {
            "evidence_id": "EVD-A4-USER-II-20260823",
            "evidence_type": "USER_SUPPLIED_CURRENT_PLATFORM_OBSERVATION",
            "source_tier": "USER_OBSERVATION",
            "publisher": "User / Interactive Investor account view",
            "title": "Current ii visibility/tradability observations",
            "url": "USER_SUPPLIED_NO_PUBLIC_URL",
            "retrieved_at": retrieved_at,
            "observation_date": "2026-08-23",
            "source_sha256": "NOT_APPLICABLE",
            "local_capture": "USER_INSTRUCTION_AND_A3R2_LEDGER",
            "supports": "Current-only ii metadata for CUKS, TELE, NDUS, MTRL, ITEC, UTIL, SEAL, EBIG and CSUK; EBIZ is USD alternate.",
            "historical_eligibility_supported": "NO",
            "confidence": "HIGH_CURRENT_ONLY",
            "warning": "DO NOT BACK-PROJECT CURRENT II STATUS",
        }
    )
    return rows


def correctness_tests(
    history: pd.DataFrame,
    current: pd.DataFrame,
    gaps: pd.DataFrame,
    costs: pd.DataFrame,
    execution: pd.DataFrame,
    baseline_bundle: dict[str, Any],
) -> pd.DataFrame:
    tests: list[dict[str, Any]] = []

    def add(test_id: str, test: str, passed: bool, detail: str) -> None:
        tests.append({"test_id": test_id, "test": test, "status": "PASS" if passed else "FAIL", "detail": detail})

    executed = history.loc[history["execution_date"].notna()].copy()
    primary = history.loc[history["model_id"].eq("A4_PRIMARY")]
    union_families = history["economic_exposure_family_id"].nunique()
    trades = baseline_bundle["selected_net"].trades
    add("A4-I01", "All five frozen implementation scopes were reconstructed", history["model_id"].nunique() == 5, str(sorted(history["model_id"].unique())))
    add("A4-I02", "All 22 historically selected economic families were investigated", union_families == 22, f"families={union_families}")
    add("A4-I03", "Executed selections retain exact A2R2 implementation IDs", executed["implementation_listing_id"].str.startswith(("LIST-", "A2RLIST-")).all(), f"executed_rows={len(executed)}")
    add("A4-I04", "Executed selections use valid non-stale, non-proxy A2R2 rows", bool((executed["a2r2_data_valid"] & ~executed["a2r2_stale_flag"] & ~executed["a2r2_proxy_flag"]).all()), f"executed_rows={len(executed)}")
    add("A4-I05", "No current status is back-projected", history["current_status_back_projected"].eq("NO").all(), "all historical rows explicitly NO")
    add("A4-I06", "Current ii observations retain 2026-08-23 current-only metadata", bool(current.loc[current["ii_current_tradable"].eq("CONFIRMED_BY_USER"), "ii_observation_date"].eq("2026-08-23").all()), f"confirmed={current['ii_current_tradable'].eq('CONFIRMED_BY_USER').sum()}")
    add("A4-I07", "LSE listing alone never creates verified ISA history", not history["historical_isa_status"].eq("HISTORICALLY_VERIFIED_ISA_ELIGIBLE").any(), "verified ISA count=0")
    add("A4-I08", "FCBR—not current CYSE—is preserved for the 2021 cybersecurity episode", bool(((primary["economic_exposure_family_id"].eq("GLOBAL_CYBERSECURITY")) & primary["isin"].eq("IE00BF16M727") & primary["ticker"].eq("FCBR")).any()), "exact historical line check")
    add("A4-I09", "Panel-end GLOBAL_GENOMICS decision is not fabricated as executed", bool(((primary["economic_exposure_family_id"].eq("GLOBAL_GENOMICS")) & primary["execution_date"].isna()).any()), "2026-08-21 decision has no next session")
    add("A4-I10", "No same-close execution enters", not trades["same_close_execution"].fillna(False).any(), f"trade_rows={len(trades)}")
    add("A4-I11", "NEXT_OPEN results were not fabricated", execution.loc[execution["execution_model"].eq("NEXT_OPEN"), "status"].eq("NOT_RUN_NO_VALIDATED_NEXT_OPEN_ROUTE").all(), "validated open route absent")
    add("A4-I12", "Cost stress contains every frozen bps/sleeve combination", len(costs) == 9 and set(costs["one_way_friction_bps"]) == {10.0, 20.0, 40.0} and set(costs["sleeve_size_gbp"]) == {100000.0, 250000.0, 500000.0}, f"rows={len(costs)}")
    add("A4-I13", "Current candidate universe plus two reference benchmarks is covered", len(current) == 29 and current["current_pool_member"].sum() == 27, f"rows={len(current)}; pool={current['current_pool_member'].sum()}")
    add("A4-I14", "Implementation gaps are current signal-eligible and never silently dropped", len(gaps) == int((current["current_signal_eligible"] & ~current["current_implementation_state"].eq("CURRENT_II_CONFIRMED")).sum()), f"gaps={len(gaps)}")
    add("A4-I15", "Current ii confirmation does not masquerade as historical platform evidence", not executed["historical_platform_status"].str.contains("CONFIRMED", na=False).any(), "all historical platform states uncertain")
    return pd.DataFrame(tests)


def main() -> int:
    generated_at = utc_now()
    evidence = json.loads(EVIDENCE_CONFIG.read_text(encoding="utf-8"))
    data = load_research_data()
    features = pd.read_parquet(FEATURE_PATH)
    features["date"] = pd.to_datetime(features["date"])
    snapshot = pd.read_csv(SNAPSHOT_PATH, dtype=str)
    queue = pd.read_csv(QUEUE_PATH, dtype=str)
    panel = pd.read_parquet(PANEL_PATH, columns=[
        "date", "economic_exposure_family_id", "implementation_share_class_id", "implementation_listing_id",
        "eligible_state", "eligibility_confidence", "data_valid", "stale_flag", "missing_flag", "proxy_flag",
    ])
    panel["date"] = pd.to_datetime(panel["date"])
    endpoint = pd.read_parquet(ENDPOINT_PATH, columns=[
        "date", "economic_exposure_family_id", "listing_id", "share_class_id", "isin", "ticker", "mic",
        "endpoint_valid", "selection_source", "continuity_reason", "stale_flag", "missing_flag", "proxy_flag",
    ])
    endpoint["date"] = pd.to_datetime(endpoint["date"])
    identity = _identity_master()
    share, fund = _share_and_fund_metadata()
    bounds = window_bounds(data.calendar)["LATEST_5Y"]
    assert bounds[0] is not None and bounds[1] is not None
    bundles = _bundle_set(data, features, snapshot, bounds[0])
    history = build_selected_instrument_history(bundles, data, panel, endpoint, identity, share, fund, evidence)
    retail, isa = build_evidence_tables(history)
    current, gaps = build_current_implementation(features, snapshot, queue)
    costs, execution, baseline_bundle = build_cost_and_execution_results(data, features, snapshot, bounds)
    tests = correctness_tests(history, current, gaps, costs, execution, baseline_bundle)
    if not tests["status"].eq("PASS").all():
        failed = tests.loc[~tests["status"].eq("PASS")]
        raise AssertionError(f"A4 implementation correctness failure:\n{failed.to_string(index=False)}")

    output_audits = [
        write_csv(out("SELECTED_INSTRUMENT_HISTORY.csv"), history),
        write_csv(out("HISTORICAL_UK_RETAIL_EVIDENCE.csv"), retail),
        write_csv(out("HISTORICAL_ISA_EVIDENCE.csv"), isa),
        write_csv(out("CURRENT_II_IMPLEMENTATION.csv"), current),
        write_csv(out("CURRENT_IMPLEMENTABILITY_GAPS.csv"), gaps),
        write_csv(out("EXECUTION_MODEL_RESULTS.csv"), execution),
        write_csv(out("COST_STRESS_RESULTS.csv"), costs),
        write_csv(out("IMPLEMENTATION_CORRECTNESS_TEST_RESULTS.csv"), tests),
    ]

    primary_executed = history.loc[history["model_id"].eq("A4_PRIMARY") & history["execution_date"].notna()].copy()
    episodes = pd.read_csv(
        PROGRAMME_ROOT / "UKACTIVE_A4_HOLDING_EPISODES.csv",
        parse_dates=["entry_signal_date", "entry_execution_date"],
    )
    primary_episode_route = episodes.merge(
        primary_executed,
        left_on=["entry_signal_date", "family"],
        right_on=["signal_date", "economic_exposure_family_id"],
        how="left",
        validate="one_to_one",
        suffixes=("_episode", ""),
    )
    retail_counts = primary_episode_route["historical_uk_retail_status"].value_counts().to_dict()
    isa_counts = primary_episode_route["historical_isa_status"].value_counts().to_dict()
    current_pool = current.loc[current["current_pool_member"]]
    current_eligible = current.loc[current["current_signal_eligible"]]
    report = f"""# UKACTIVE-A4 implementation reconstruction

Generated: {generated_at}

## Scope and result

The reconstruction covers all {history['economic_exposure_family_id'].nunique()} families selected by A4_PRIMARY, TOP_2, TOP_3 and the two frozen neighbours during the contemporary window. It uses the exact A2R2 share-class/listing IDs at each execution date. It does not substitute the current preferred line retrospectively.

The primary model has {len(primary_executed)} executed monthly decisions, which form {len(primary_episode_route)} holding episodes across {primary_episode_route['economic_exposure_family_id'].nunique()} distinct executed families. Historical UK-retail episode states are {json.dumps(retail_counts, sort_keys=True)}. Historical ISA episode states are {json.dumps(isa_counts, sort_keys=True)}. Account/platform history remains HISTORICALLY_UNCERTAIN throughout.

## Current implementability

The frozen industry-plus-theme pool contains {len(current_pool)} families, of which {int(current_pool['current_signal_eligible'].sum())} have a current 3/6/12 score. User-confirmed current ii coverage is {int(current_pool['ii_current_tradable'].eq('CONFIRMED_BY_USER').sum())}/{len(current_pool)} families ({'; '.join(current_pool.loc[current_pool['ii_current_tradable'].eq('CONFIRMED_BY_USER'), 'preferred_ticker']) or 'none'}). Among currently signal-eligible families, {int(current_eligible['current_implementation_state'].eq('CURRENT_II_CONFIRMED').sum())} are ii-confirmed, {int(current_eligible['current_implementation_state'].eq('CURRENT_PUBLIC_UK_ELIGIBLE_II_UNCHECKED').sum())} have complete public rules/disclosure support but remain ii-unchecked, and {int(current_eligible['current_implementation_state'].eq('CURRENT_IMPLEMENTATION_UNRESOLVED').sum())} remain unresolved.

This is not sufficient for deployment. It does not prevent an economic-signal shadow test, provided any unconfirmed selection is recorded as non-executable rather than silently substituted or reranked.

## Execution and costs

The only reported execution result uses the frozen next-eligible-session endpoint contract. NEXT_OPEN is not reported because the raw open field has not passed an execution-price validation chain. No current spread is represented as a historical realised spread. The 10/20/40 bp and £100k/£250k/£500k tables are sensitivities; the £3.99 charge and 0.75% non-GBP FX assumption are sourced from the current ii tariff and are not claims about historical charges.

## Evidence boundary

An exact instrument’s validated price lineage proves neither historical retail-document availability nor ISA/platform eligibility. A dated exact-ISIN KIID supports one verified retail episode route (URNP after the document date); the remaining exact primary routes are classified probable rather than verified. ISA classifications are probable where exact UCITS structure plus recognised-exchange admission and HMRC rules align, but no account-specific history was found. Current ii observations remain dated 2026-08-23 only.
"""
    output_audits.append(write_text(out("IMPLEMENTATION_RECONSTRUCTION_REPORT.md"), report))

    ledger_rows = evidence_ledger(evidence)
    ledger_path = PROGRAMME_ROOT / "evidence" / "UKACTIVE_A4_EVIDENCE_LEDGER.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in ledger_rows), encoding="utf-8")
    output_audits.append(audit_file(ledger_path, rows=len(ledger_rows)))

    manifest = {
        "stage": "UKACTIVE-A4_IMPLEMENTATION_RECONSTRUCTION",
        "run_id": RUN_ID,
        "generated_at": generated_at,
        "git_commit_at_execution": git_output("rev-parse", "HEAD"),
        "git_branch": git_output("branch", "--show-current"),
        "inputs": [
            audit_file(EVIDENCE_CONFIG), audit_file(FEATURE_PATH), audit_file(SNAPSHOT_PATH), audit_file(QUEUE_PATH),
            audit_file(PANEL_PATH), audit_file(ENDPOINT_PATH), audit_file(A2_INSTRUMENT_PATH), audit_file(A2R_INSTRUMENT_PATH),
        ],
        "outputs": output_audits,
        "scope": {
            "historically_selected_families": int(history["economic_exposure_family_id"].nunique()),
            "current_industry_theme_pool_families": int(current_pool.shape[0]),
            "current_signal_eligible_families": int(current_eligible.shape[0]),
        },
        "evidence_counts": {
            "primary_route_retail": retail_counts,
            "primary_route_isa": isa_counts,
            "current_ii_confirmed_pool": int(current_pool["ii_current_tradable"].eq("CONFIRMED_BY_USER").sum()),
            "current_signal_eligible_gaps": int(len(gaps)),
        },
        "policies": {
            "execution": "A2R2_FROZEN_NEXT_ELIGIBLE_SESSION_ENDPOINT",
            "next_open": "NOT_RUN_NO_VALIDATED_ROUTE",
            "historical_eligibility": "NO_CURRENT_BACK_PROJECTION",
            "broker": "NO_BROKER_QUERY_OR_ORDER_ACTION",
        },
        "automated_tests": tests.to_dict(orient="records"),
        "package_versions": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__, "pyarrow": pyarrow.__version__},
        "warning": "HISTORICAL UK RETAIL, ISA, ACCOUNT AND BROKER ELIGIBILITY REMAIN PARTLY UNRESOLVED",
    }
    write_json(out("IMPLEMENTATION_MANIFEST.json"), manifest)
    print(json.dumps({
        "historically_selected_families": int(history["economic_exposure_family_id"].nunique()),
        "primary_monthly_decision_rows": int(len(primary_executed)),
        "primary_holding_episodes": int(len(primary_episode_route)),
        "retail_counts": retail_counts,
        "isa_counts": isa_counts,
        "current_pool": int(len(current_pool)),
        "current_signal_eligible": int(len(current_eligible)),
        "current_ii_confirmed_pool": int(current_pool["ii_current_tradable"].eq("CONFIRMED_BY_USER").sum()),
        "current_gaps": int(len(gaps)),
        "tests": tests["status"].value_counts().to_dict(),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
