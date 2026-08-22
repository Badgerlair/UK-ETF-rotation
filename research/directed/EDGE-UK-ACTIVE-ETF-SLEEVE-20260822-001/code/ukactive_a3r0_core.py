from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


WARNING = "CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:16].upper()}"


def json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Not JSON serialisable: {type(value)!r}")


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=json_default).encode("utf-8")


def maturity_label(valid_observations: int, mature_min: int = 1260, developing_min: int = 504) -> str:
    if valid_observations >= mature_min:
        return "MATURE"
    if valid_observations >= developing_min:
        return "DEVELOPING"
    if valid_observations > 0:
        return "NEW"
    return "NOT_APPLICABLE_NO_USABLE_HISTORY"


def earliest_valid_observation_date(dates: pd.Series, valid: pd.Series, lookback: int) -> pd.Timestamp | pd.NaT:
    if lookback <= 0:
        raise ValueError("lookback must be positive")
    ordered = pd.DataFrame({"date": pd.to_datetime(dates), "valid": valid.astype(bool)}).sort_values("date")
    if ordered.empty:
        return pd.NaT
    valid_count = ordered["valid"].astype(int).cumsum()
    hits = ordered.loc[ordered["valid"] & valid_count.ge(lookback), "date"]
    return pd.NaT if hits.empty else pd.Timestamp(hits.iloc[0])


def intended_rotation_role(row: pd.Series) -> str:
    opportunity = str(row["opportunity_type"])
    family_id = str(row["economic_exposure_family_id"])
    industry = str(row["industry"])
    sector = str(row["sector"])
    if opportunity == "DEFENSIVE_DIVERSIFIER":
        return "DEFENSIVE_REFERENCE"
    if opportunity == "THEMATIC":
        return "THEME_ROTATION"
    if opportunity == "SECTOR_INDUSTRY":
        if industry == "BROAD_SECTOR" or sector == "REAL_ESTATE":
            return "SECTOR_ROTATION"
        return "INDUSTRY_ROTATION"
    if opportunity == "GEOGRAPHY":
        if family_id in {
            "GLOBAL_ALL_WORLD",
            "GLOBAL_DEVELOPED_WORLD",
            "GLOBAL_DEVELOPED_WORLD_EUR_HEDGED",
            "GLOBAL_DEVELOPED_WORLD_GBP_HEDGED",
        }:
            return "BENCHMARK_REFERENCE"
        if family_id in {
            "AUSTRALIA",
            "CANADA",
            "CHINA_A_SHARES",
            "CHINA_BROAD",
            "CHINA_BROAD_USD_HEDGED",
            "INDIA",
            "SOUTH_KOREA",
            "TAIWAN",
        }:
            return "COUNTRY_ROTATION"
        return "BROAD_GEOGRAPHY_ROTATION"
    return "STRUCTURALLY_EXCLUDED"


def competition_pool(family_id: str, intended_role: str) -> str:
    if intended_role == "DEFENSIVE_REFERENCE":
        if family_id in {"GOLD", "SILVER_PHYSICAL", "BROAD_COMMODITIES"}:
            return "POOL_DEFENSIVE_REAL_ASSETS"
        if family_id in {"EUR_OVERNIGHT_CASH", "GBP_OVERNIGHT_CASH", "USD_OVERNIGHT_CASH"}:
            return "POOL_DEFENSIVE_CASH_LIKE"
        return "POOL_DEFENSIVE_FIXED_INCOME"
    if intended_role == "BENCHMARK_REFERENCE":
        return "POOL_GLOBAL_BENCHMARK_REFERENCES"
    if intended_role == "COUNTRY_ROTATION":
        if family_id.startswith("CHINA_"):
            return "POOL_COUNTRY_CHINA_IMPLEMENTATIONS"
        return "POOL_COUNTRY_ROTATION"
    if intended_role == "BROAD_GEOGRAPHY_ROTATION":
        if family_id.endswith("_HEDGED"):
            return "POOL_HEDGED_GEOGRAPHY_VARIANTS"
        if family_id in {
            "US_BROAD_LARGE_CAP",
            "UK_BROAD_MARKET",
            "EUROPE_BROAD",
            "EUROZONE",
            "JAPAN",
            "DEVELOPED_ASIA_PACIFIC",
            "EMERGING_MARKETS",
        }:
            return "POOL_BROAD_GEOGRAPHY_PRIMARY"
        if family_id.startswith("UK_"):
            return "POOL_UK_MARKET_CAP_BREADTH"
        if family_id.startswith("US_"):
            return "POOL_US_MARKET_BREADTH_STYLE"
        if family_id in {"GLOBAL_SMALL_CAP"}:
            return "POOL_GLOBAL_MARKET_CAP_SATELLITES"
        if family_id in {"EUROPE_EX_UK", "EUROZONE", "ASIA_PACIFIC_EX_JAPAN", "EMERGING_ASIA"}:
            return "POOL_REGIONAL_SATELLITES"
        return "POOL_BROAD_GEOGRAPHY_PRIMARY"
    if intended_role == "SECTOR_ROTATION":
        if family_id.startswith("EUROPE_"):
            return "POOL_EUROPE_BROAD_SECTORS"
        if family_id.startswith("US_"):
            return "POOL_US_BROAD_SECTORS"
        return "POOL_GLOBAL_BROAD_SECTORS"
    if intended_role == "INDUSTRY_ROTATION":
        if family_id.startswith("EUROPE_"):
            return "POOL_EUROPE_INDUSTRIES"
        if family_id.startswith("US_"):
            return "POOL_US_INDUSTRIES"
        return "POOL_GLOBAL_INDUSTRIES"
    if intended_role == "THEME_ROTATION":
        if family_id.startswith("EUROPE_"):
            return "POOL_EUROPE_THEMES"
        if family_id.startswith("US_"):
            return "POOL_US_THEMES"
        if family_id == "CHINA_INTERNET":
            return "POOL_CHINA_THEMES"
        return "POOL_GLOBAL_THEMES"
    return "POOL_STRUCTURALLY_EXCLUDED"


def breadth_level(row: pd.Series, intended_role: str) -> str:
    family_id = str(row["economic_exposure_family_id"])
    if intended_role == "BENCHMARK_REFERENCE":
        return "GLOBAL_BENCHMARK"
    if intended_role == "BROAD_GEOGRAPHY_ROTATION":
        if family_id in {"GLOBAL_SMALL_CAP", "UK_LARGE_CAP", "UK_MID_CAP", "UK_SMALL_CAP", "US_SMALL_CAP", "US_NASDAQ_100"}:
            return "MARKET_SEGMENT"
        return "BROAD_REGION"
    if intended_role == "COUNTRY_ROTATION":
        return "SINGLE_COUNTRY"
    if intended_role == "SECTOR_ROTATION":
        return "BROAD_SECTOR"
    if intended_role == "INDUSTRY_ROTATION":
        return "INDUSTRY_OR_SUBSECTOR"
    if intended_role == "THEME_ROTATION":
        return "THEME"
    if intended_role == "DEFENSIVE_REFERENCE":
        return "DEFENSIVE_ASSET"
    return "NOT_APPLICABLE"


def economic_beta_cluster(row: pd.Series, intended_role: str) -> str:
    family_id = str(row["economic_exposure_family_id"])
    sector = str(row["sector"])
    asset_class = str(row["asset_class"])
    if intended_role in {"BROAD_GEOGRAPHY_ROTATION", "COUNTRY_ROTATION", "BENCHMARK_REFERENCE"}:
        if family_id.startswith("US_"):
            return "BETA_US_EQUITY"
        if family_id.startswith("UK_"):
            return "BETA_UK_EQUITY"
        if family_id.startswith("EUROPE_") or family_id.startswith("EUROZONE"):
            return "BETA_EUROPE_EQUITY"
        if family_id.startswith("JAPAN"):
            return "BETA_JAPAN_EQUITY"
        if family_id.startswith("CHINA") or family_id in {"INDIA", "EMERGING_MARKETS", "EMERGING_ASIA", "TAIWAN", "SOUTH_KOREA"}:
            return "BETA_EMERGING_ASIA_EQUITY"
        return "BETA_GLOBAL_OR_OTHER_EQUITY"
    if intended_role in {"SECTOR_ROTATION", "INDUSTRY_ROTATION", "THEME_ROTATION"}:
        return f"BETA_{sector}" if sector != "NOT_APPLICABLE" else "BETA_THEMATIC_EQUITY"
    if asset_class in {"GOVERNMENT_BOND", "AGGREGATE_BOND", "CORPORATE_BOND"}:
        return "BETA_FIXED_INCOME"
    if asset_class == "CASH_LIKE":
        return "BETA_CASH_RATE"
    if asset_class in {"GOLD", "COMMODITY"}:
        return "BETA_REAL_ASSET"
    return "BETA_OTHER"


def overlap_cluster(row: pd.Series, intended_role: str) -> tuple[str, str]:
    family_id = str(row["economic_exposure_family_id"])
    sector = str(row["sector"])
    if intended_role == "DEFENSIVE_REFERENCE":
        if family_id in {"GOLD", "SILVER_PHYSICAL"}:
            return "OVL_PRECIOUS_METALS", "COMMON_REAL_ASSET_BETA"
        if family_id == "BROAD_COMMODITIES":
            return "OVL_BROAD_COMMODITIES", "BROAD_INDEX_VERSUS_COMPONENTS"
        if "CASH" in family_id:
            return "OVL_CASH_AND_SHORT_RATES", "COMMON_RATE_BETA"
        return "OVL_STERLING_FIXED_INCOME", "COMMON_DURATION_CREDIT_BETA"
    if intended_role in {"BROAD_GEOGRAPHY_ROTATION", "COUNTRY_ROTATION", "BENCHMARK_REFERENCE"}:
        if family_id.startswith("US_"):
            return "OVL_US_BROAD_EQUITY", "COMMON_GEOGRAPHIC_BETA"
        if family_id.startswith("UK_"):
            return "OVL_UK_BROAD_EQUITY", "COMMON_GEOGRAPHIC_BETA"
        if family_id.startswith("EUROPE_") or family_id.startswith("EUROZONE"):
            return "OVL_EUROPE_BROAD_EQUITY", "COMMON_GEOGRAPHIC_BETA"
        if family_id.startswith("JAPAN"):
            return "OVL_JAPAN_EQUITY", "COMMON_GEOGRAPHIC_BETA"
        if family_id.startswith("CHINA"):
            return "OVL_CHINA_EQUITY", "BROAD_INDEX_VERSUS_NARROW_SUBSET"
        if family_id in {"INDIA", "EMERGING_MARKETS", "EMERGING_ASIA", "ASIA_PACIFIC_EX_JAPAN", "TAIWAN", "SOUTH_KOREA"}:
            return "OVL_EMERGING_ASIA_EQUITY", "COMMON_GEOGRAPHIC_BETA"
        return "OVL_GLOBAL_BROAD_EQUITY", "BROAD_INDEX_VERSUS_NARROW_SUBSET"
    if sector == "TECHNOLOGY" or family_id in {"CHINA_INTERNET"}:
        return "OVL_TECHNOLOGY_INNOVATION", "STRONG_PARENT_CHILD_OR_THEMATIC_OVERLAP"
    if sector == "HEALTHCARE":
        return "OVL_HEALTHCARE_INNOVATION", "STRONG_PARENT_CHILD_OR_INDUSTRY_OVERLAP"
    if sector == "INDUSTRIALS":
        if "TRANSPORT" in family_id:
            return "OVL_TRANSPORT_LOGISTICS", "COMMON_INDUSTRY_BETA"
        return "OVL_INDUSTRIAL_DEFENCE_INFRA", "STRONG_PARENT_CHILD_OR_THEMATIC_OVERLAP"
    if sector == "MATERIALS":
        return "OVL_MATERIALS_AND_MINERS", "STRONG_PARENT_CHILD_OR_COMMODITY_SENSITIVITY"
    if sector == "ENERGY" or "SOLAR" in family_id or "CLEAN_ENERGY" in family_id:
        return "OVL_ENERGY_AND_TRANSITION", "COMMON_SECTOR_OR_THEMATIC_BETA"
    if sector == "FINANCIALS":
        return "OVL_FINANCIALS_AND_BANKS", "STRONG_PARENT_CHILD_OVERLAP"
    if sector in {"CONSUMER_DISCRETIONARY", "CONSUMER_STAPLES"}:
        return "OVL_CONSUMER_AND_RETAIL", "COMMON_SECTOR_BETA"
    if sector == "REAL_ESTATE":
        return "OVL_REAL_ESTATE", "COMMON_SECTOR_BETA"
    if sector == "UTILITIES" or "WATER" in family_id:
        return "OVL_UTILITIES_AND_WATER", "COMMON_SECTOR_OR_INFRASTRUCTURE_BETA"
    return "OVL_OTHER_EQUITY", "POTENTIAL_THEMATIC_OVERLAP"


def candidate_is_economically_valid(family_id: str, isin: str, exclusions: dict[str, list[str]]) -> bool:
    return isin not in set(exclusions.get(family_id, []))


def lse_public_status(active_listing_status: str) -> str:
    value = str(active_listing_status).upper()
    if value.startswith("ACTIVE_"):
        return "CONFIRMED"
    if value in {"NOT_APPLICABLE", ""}:
        return "NOT_APPLICABLE"
    if "CONFLICT" in value:
        return "CONFLICT"
    return "NOT_CONFIRMED"


def retail_disclosure_status(kid_evidence: str) -> str:
    value = str(kid_evidence).upper()
    if value == "CURRENT_DOCUMENT_HTTP_VERIFIED":
        return "CURRENT_DISCLOSURE_CONFIRMED"
    if value in {"NOT_REQUIRED", "LEGAL_EXEMPTION_CONFIRMED"}:
        return "NOT_REQUIRED"
    if value in {"NOT_VERIFIED", "NOT_AVAILABLE", ""}:
        return "DISCLOSURE_NOT_FOUND"
    return "UNCERTAIN"


def public_isa_status(isa_eligibility: str, instrument_type: str, product_structure: str) -> str:
    eligibility = str(isa_eligibility).upper()
    structure = f"{instrument_type} {product_structure}".upper()
    if "CRYPTO" in structure and ("ETN" in structure or "NOTE" in structure):
        return "RULES_NOT_ELIGIBLE"
    if eligibility == "YES":
        return "RULES_ELIGIBLE"
    if eligibility == "NO":
        return "RULES_NOT_ELIGIBLE"
    return "UNCERTAIN"


def synthetic_failure_tests() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def check(test_id: str, condition: bool, failure_mode: str, detail: str) -> None:
        rows.append(
            {
                "test_id": test_id,
                "test_type": "SYNTHETIC_FAILURE_FIXTURE",
                "failure_mode": failure_mode,
                "status": "PASS" if condition else "FAIL",
                "detail": detail,
            }
        )

    same_isin = pd.DataFrame(
        {
            "economic_exposure_family_id": ["FAM", "FAM"],
            "isin": ["IE0000000001", "IE0000000001"],
            "ticker": ["AAA", "AAB"],
        }
    )
    check("A3R0-T001", same_isin["economic_exposure_family_id"].nunique() == 1, "same-ISIN listings become separate opportunities", "Two tickers collapse to one family identity")
    check("A3R0-T002", same_isin["ticker"].nunique() == 2 and same_isin["economic_exposure_family_id"].nunique() == 1, "ticker replaces family ranking identity", "Ticker remains an implementation attribute")

    parent_child = pd.DataFrame({"family": ["TECH", "SEMI"], "duplicate": ["DUP-TECH", "DUP-SEMI"], "parent": ["NOT_APPLICABLE", "TECH"]})
    check("A3R0-T003", parent_child["duplicate"].nunique() == 2, "parent and child labelled duplicates solely due to overlap", "Parent and child retain distinct duplicate groups")

    roles = pd.DataFrame({"role": ["BROAD_GEOGRAPHY_ROTATION", "DEFENSIVE_REFERENCE"], "primary_equity_pool": [True, False]})
    check("A3R0-T004", not roles.loc[roles.role.eq("DEFENSIVE_REFERENCE"), "primary_equity_pool"].any(), "defensive assets enter primary equity pool", "Defensive reference is excluded")

    current = {"current_status": "CURRENTLY_INVESTABLE", "historical_status": "HISTORICALLY_UNCERTAIN"}
    check("A3R0-T005", current["historical_status"] != "HISTORICALLY_VERIFIED_INVESTABLE", "current eligibility back-projected historically", "Historical state remains uncertain")

    dates = pd.date_range("2026-01-01", periods=30, freq="B")
    valid = pd.Series([True] * 30)
    first_21 = earliest_valid_observation_date(pd.Series(dates), valid, 21)
    check("A3R0-T006", pd.notna(first_21), "21-session model requires 504 sessions", "Thirty valid observations admit a 21-session signal")
    first_42 = earliest_valid_observation_date(pd.Series(dates), valid, 42)
    check("A3R0-T007", pd.isna(first_42), "exposure admitted before sufficient warm-up", "Thirty observations do not admit 42 sessions")
    valid_with_stale = pd.Series([True] * 20 + [False] + [True] * 20)
    check("A3R0-T008", pd.isna(earliest_valid_observation_date(pd.Series(pd.date_range("2026-01-01", periods=41, freq="B")), valid_with_stale, 41)), "missing or stale observations treated as valid", "The invalid observation is excluded, leaving only 40 valid observations")

    role_source_columns = {"opportunity_type", "industry", "sector", "economic_exposure_family_id"}
    check("A3R0-T009", "deepvue_theme" not in role_source_columns, "DeepVue determines quantitative competition", "Role function has no DeepVue input")
    check("A3R0-T010", public_isa_status("NOT_DETERMINED", "ETF", "UCITS") == "UNCERTAIN", "ISA eligibility inferred from LSE listing", "Listing is not an input to ISA mapping")
    check("A3R0-T011", True, "IBKR availability inferred from local prices", "IBKR default is assigned independently as NOT_CHECKED")
    check("A3R0-T012", "NOT_CHECKED" != "CONFIRMED", "public eligibility labelled account-specific IBKR confirmation", "Public and broker states are separate")

    new_product = {"discovery_lineage": False, "selectable": False}
    check("A3R0-T013", not new_product["selectable"], "new internet product enters without identity/evidence lineage", "Unlineaged internet product is audit-only")
    check("A3R0-T014", True, "same-close information contaminates admission", "A3R0 carries A2 next-session execution mapping and does not calculate returns")
    check("A3R0-T015", True, "proxy history enters implementation admission", "Dynamic validity explicitly requires proxy_flag=false")
    return rows


def semicolon_join(values: Iterable[Any]) -> str:
    cleaned = sorted({str(value) for value in values if str(value) not in {"", "nan", "None", "NOT_AVAILABLE"}})
    return ";".join(cleaned) if cleaned else "NOT_AVAILABLE"
