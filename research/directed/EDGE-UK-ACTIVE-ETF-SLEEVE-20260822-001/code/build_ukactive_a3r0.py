from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import warnings
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests

HERE = Path(__file__).resolve().parent
PROGRAMME_ROOT = HERE.parent
CONFIG_PATH = PROGRAMME_ROOT / "config" / "UKACTIVE_A3R0_POLICY_v1.json"
EVIDENCE_DIR = PROGRAMME_ROOT / "evidence"
SOURCE_DIR = EVIDENCE_DIR / "sources" / "a3r0"
EXECUTED_SOURCE_DIR = SOURCE_DIR / "executed_source"
sys.path.insert(0, str(HERE))

from ukactive_a3r0_core import (  # noqa: E402
    WARNING,
    breadth_level,
    candidate_is_economically_valid,
    competition_pool,
    earliest_valid_observation_date,
    economic_beta_cluster,
    intended_rotation_role,
    json_default,
    lse_public_status,
    maturity_label,
    overlap_cluster,
    public_isa_status,
    retail_disclosure_status,
    semicolon_join,
    sha256_bytes,
    sha256_file,
    stable_id,
    synthetic_failure_tests,
    utc_now,
)


STAGE_ID = "UKACTIVE-A3R0"
RUN_ID = "UKACTIVE-A3R0-20260822-001"
PROGRAMME_ID = "EDGE-UK-ACTIVE-ETF-SLEEVE-20260822-001"


INPUTS = [
    "UKACTIVE_A0A1_ECONOMIC_EXPOSURE_MASTER.csv",
    "UKACTIVE_A0A1_DISCOVERY_REGISTRY.csv",
    "UKACTIVE_A0A1_IMPLEMENTATION_CANDIDATES.csv",
    "UKACTIVE_A0A1_CURRENT_INVESTABILITY.csv",
    "UKACTIVE_A0A1_LISTING_MASTER.csv",
    "UKACTIVE_A0A1_SHARE_CLASS_MASTER.csv",
    "UKACTIVE_A0A1_DUPLICATE_GROUPS.csv",
    "UKACTIVE_A0A1_DEEPVUE_THEME_CROSSWALK.csv",
    "UKACTIVE_A0A1_THEME_TAXONOMY.csv",
    "UKACTIVE_A0A1_MANIFEST.json",
    "UKACTIVE_A2_TOTAL_RETURN_PANEL_GBP.parquet",
    "UKACTIVE_A2_EXPOSURE_HISTORY_MASTER.parquet",
    "UKACTIVE_A2_CANONICAL_IMPLEMENTATION_HISTORY.parquet",
    "UKACTIVE_A2_FAMILY_COVERAGE_AND_READINESS.csv",
    "UKACTIVE_A2_MANIFEST.json",
    "UKACTIVE_A2_DATA_QUALITY_REPORT.md",
    "UKACTIVE_A2_A3_READINESS_REPORT.md",
    r"evidence\UKACTIVE_A0A1_EVIDENCE_LEDGER.jsonl",
    "config/UKACTIVE_A3R0_POLICY_v1.json",
]


REQUIRED_OUTPUTS = [
    "UKACTIVE_A3R0_SCOPE_AND_METHOD.md",
    "UKACTIVE_A3R0_ROTATION_ROLE_MASTER.csv",
    "UKACTIVE_A3R0_COMPETITION_POOLS.csv",
    "UKACTIVE_A3R0_PARENT_CHILD_MAP.csv",
    "UKACTIVE_A3R0_OVERLAP_CLUSTERS.csv",
    "UKACTIVE_A3R0_GLOBAL_BENCHMARK_MAP.csv",
    "UKACTIVE_A3R0_PARENT_BENCHMARK_MAP.csv",
    "UKACTIVE_A3R0_DYNAMIC_SIGNAL_ELIGIBILITY.parquet",
    "UKACTIVE_A3R0_THEME_COVERAGE_AUDIT.csv",
    "UKACTIVE_A3R0_THEME_COVERAGE_GAPS.md",
    "UKACTIVE_A3R0_SELECTABLE_ECONOMIC_UNIVERSE.csv",
    "UKACTIVE_A3R0_CURRENT_IMPLEMENTATION_LINES.csv",
    "UKACTIVE_A3R0_PUBLIC_UK_ELIGIBILITY.csv",
    "UKACTIVE_A3R0_CHATGPT_IBKR_VERIFICATION_QUEUE.csv",
    "UKACTIVE_A3R0_CLASSIFICATION_CORRECTIONS.csv",
    "UKACTIVE_A3R0_DATA_QUALITY_REPORT.md",
    "UKACTIVE_A3R0_AUTOMATED_TEST_RESULTS.csv",
    "UKACTIVE_A3R0_UNRESOLVED_ITEMS.csv",
    "UKACTIVE_A3R0_A3R1_READINESS_REPORT.md",
    "UKACTIVE_A3R0_DECISION.json",
    "UKACTIVE_A3R0_MANIFEST.json",
]


PUBLIC_SOURCES = {
    "FCA_CCI_TRANSITION": "https://handbook.fca.org.uk/handbook/disctp2",
    "HMRC_ISA_QUALIFYING_INVESTMENTS": "https://www.gov.uk/guidance/stocks-and-shares-investments-for-isa-managers",
    "HMRC_ISA_2026_AMENDMENT": "https://www.gov.uk/government/publications/amendment-to-individual-savings-account-regulations-2026/individual-savings-account-amendment-regulation-2026",
    "LSE_TRIP_CURRENT": "https://www.londonstockexchange.com/stock/TRIP/hanetf/company-page",
    "LSE_TELE_CURRENT": "https://www.londonstockexchange.com/stock/TELE/street-global-advisors",
    "LSE_SOCIAL_MEDIA_XLOM": "https://www.londonstockexchange.com/market-stock/0IX3/global-x-social-media-etf/overview",
}


POOL_DESCRIPTIONS = {
    "POOL_BROAD_GEOGRAPHY_PRIMARY": "Broad unhedged geographic leaders: major regions and large national markets that are economically meaningful peers",
    "POOL_REGIONAL_SATELLITES": "Narrower regional variants that must not multiply the broad-geography tournament",
    "POOL_COUNTRY_ROTATION": "Distinct single-country exposures outside the broad primary-region set",
    "POOL_COUNTRY_CHINA_IMPLEMENTATIONS": "China broad/A-share/hedged implementation variants assessed separately",
    "POOL_UK_MARKET_CAP_BREADTH": "UK broad, large-, mid- and small-cap breadth comparisons",
    "POOL_US_MARKET_BREADTH_STYLE": "US broad, total-market, Nasdaq and small-cap breadth/style comparisons",
    "POOL_HEDGED_GEOGRAPHY_VARIANTS": "Currency-hedged variants compared with their unhedged parent, not counted as extra regions",
    "POOL_GLOBAL_MARKET_CAP_SATELLITES": "Global size-segment satellites",
    "POOL_GLOBAL_BENCHMARK_REFERENCES": "Benchmark-only broad global equity references",
    "POOL_GLOBAL_BROAD_SECTORS": "Provider-neutral global broad sectors",
    "POOL_EUROPE_BROAD_SECTORS": "Provider-neutral Europe broad sectors",
    "POOL_US_BROAD_SECTORS": "Provider-neutral US broad sectors",
    "POOL_GLOBAL_INDUSTRIES": "Global industry and subsector opportunities",
    "POOL_EUROPE_INDUSTRIES": "Europe industry and subsector opportunities",
    "POOL_US_INDUSTRIES": "US industry and subsector opportunities",
    "POOL_GLOBAL_THEMES": "Global evidence-backed themes",
    "POOL_EUROPE_THEMES": "Europe-specific themes",
    "POOL_US_THEMES": "US-specific themes",
    "POOL_CHINA_THEMES": "China-specific themes",
    "POOL_DEFENSIVE_FIXED_INCOME": "Fixed-income defensive references; excluded from the primary equity tournament",
    "POOL_DEFENSIVE_CASH_LIKE": "Cash-like ETF references; actual GBP cash remains a separate A2 research asset",
    "POOL_DEFENSIVE_REAL_ASSETS": "Gold, silver and broad-commodity diversifiers",
    "POOL_STRUCTURALLY_EXCLUDED": "Structurally unsuitable products",
    "POOL_INSUFFICIENT_DATA": "Families blocked by absent history or material A2 economic-lineage mismatch",
}


PARENT_MAP: dict[str, tuple[str, str]] = {
    "ASIA_PACIFIC_EX_JAPAN": ("GLOBAL_ALL_WORLD", "NOT_APPLICABLE"),
    "AUSTRALIA": ("DEVELOPED_ASIA_PACIFIC", "GLOBAL_DEVELOPED_WORLD"),
    "CANADA": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
    "CHINA_A_SHARES": ("CHINA_BROAD", "EMERGING_MARKETS"),
    "CHINA_BROAD": ("EMERGING_MARKETS", "GLOBAL_ALL_WORLD"),
    "CHINA_BROAD_USD_HEDGED": ("CHINA_BROAD", "NOT_APPLICABLE"),
    "DEVELOPED_ASIA_PACIFIC": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
    "EMERGING_ASIA": ("EMERGING_MARKETS", "NOT_APPLICABLE"),
    "EMERGING_MARKETS": ("GLOBAL_ALL_WORLD", "NOT_APPLICABLE"),
    "EUROPE_BROAD": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
    "EUROPE_EX_UK": ("EUROPE_BROAD", "GLOBAL_DEVELOPED_WORLD"),
    "EUROZONE": ("EUROPE_BROAD", "NOT_APPLICABLE"),
    "EUROZONE_USD_HEDGED": ("EUROZONE", "NOT_APPLICABLE"),
    "GLOBAL_DEVELOPED_WORLD": ("GLOBAL_ALL_WORLD", "NOT_APPLICABLE"),
    "GLOBAL_DEVELOPED_WORLD_EUR_HEDGED": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
    "GLOBAL_DEVELOPED_WORLD_GBP_HEDGED": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
    "GLOBAL_SMALL_CAP": ("GLOBAL_DEVELOPED_WORLD", "GLOBAL_ALL_WORLD"),
    "INDIA": ("EMERGING_MARKETS", "EMERGING_ASIA"),
    "JAPAN": ("GLOBAL_DEVELOPED_WORLD", "DEVELOPED_ASIA_PACIFIC"),
    "JAPAN_EUR_HEDGED": ("JAPAN", "NOT_APPLICABLE"),
    "JAPAN_GBP_HEDGED": ("JAPAN", "NOT_APPLICABLE"),
    "LATIN_AMERICA": ("EMERGING_MARKETS", "NOT_APPLICABLE"),
    "SOUTH_KOREA": ("EMERGING_MARKETS", "EMERGING_ASIA"),
    "TAIWAN": ("EMERGING_MARKETS", "EMERGING_ASIA"),
    "UK_BROAD_MARKET": ("EUROPE_BROAD", "GLOBAL_DEVELOPED_WORLD"),
    "UK_LARGE_CAP": ("UK_BROAD_MARKET", "NOT_APPLICABLE"),
    "UK_MID_CAP": ("UK_BROAD_MARKET", "NOT_APPLICABLE"),
    "UK_SMALL_CAP": ("UK_BROAD_MARKET", "NOT_APPLICABLE"),
    "US_BROAD_LARGE_CAP": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
    "US_BROAD_LARGE_CAP_EUR_HEDGED": ("US_BROAD_LARGE_CAP", "NOT_APPLICABLE"),
    "US_BROAD_LARGE_CAP_GBP_HEDGED": ("US_BROAD_LARGE_CAP", "NOT_APPLICABLE"),
    "US_NASDAQ_100": ("US_BROAD_LARGE_CAP", "NOT_APPLICABLE"),
    "US_SMALL_CAP": ("US_TOTAL_MARKET", "US_BROAD_LARGE_CAP"),
    "US_TOTAL_MARKET": ("GLOBAL_DEVELOPED_WORLD", "US_BROAD_LARGE_CAP"),
    "US_TOTAL_MARKET_GBP_HEDGED": ("US_TOTAL_MARKET", "NOT_APPLICABLE"),
    "EUROPE_BANKS": ("EUROPE_FINANCIALS", "NOT_APPLICABLE"),
    "EUROPE_CONSUMER_STAPLES": ("EUROPE_BROAD", "NOT_APPLICABLE"),
    "EUROPE_ENERGY": ("EUROPE_BROAD", "NOT_APPLICABLE"),
    "EUROPE_FINANCIALS": ("EUROPE_BROAD", "NOT_APPLICABLE"),
    "EUROPE_HEALTHCARE": ("EUROPE_BROAD", "NOT_APPLICABLE"),
    "EUROPE_INDUSTRIALS": ("EUROPE_BROAD", "NOT_APPLICABLE"),
    "EUROPE_MATERIALS": ("EUROPE_BROAD", "NOT_APPLICABLE"),
    "EUROPE_TECHNOLOGY": ("EUROPE_BROAD", "NOT_APPLICABLE"),
    "EUROPE_UTILITIES": ("EUROPE_BROAD", "NOT_APPLICABLE"),
    "GLOBAL_BANKS": ("GLOBAL_FINANCIALS", "NOT_APPLICABLE"),
    "GLOBAL_BIOTECHNOLOGY": ("GLOBAL_HEALTHCARE", "US_HEALTHCARE"),
    "GLOBAL_ENERGY": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
    "GLOBAL_FINANCIALS": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
    "GLOBAL_GOLD_MINERS": ("GLOBAL_MATERIALS", "GOLD"),
    "GLOBAL_HEALTHCARE": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
    "GLOBAL_INDUSTRIALS": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
    "GLOBAL_MATERIALS": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
    "GLOBAL_OIL_GAS": ("GLOBAL_ENERGY", "NOT_APPLICABLE"),
    "GLOBAL_REAL_ESTATE": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
    "GLOBAL_SILVER_MINERS": ("GLOBAL_MATERIALS", "SILVER_PHYSICAL"),
    "GLOBAL_SOFTWARE": ("GLOBAL_TECHNOLOGY", "NOT_APPLICABLE"),
    "GLOBAL_TECHNOLOGY": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
    "GLOBAL_TRANSPORTATION": ("GLOBAL_INDUSTRIALS", "NOT_APPLICABLE"),
    "GLOBAL_UTILITIES": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
    "US_BANKS": ("US_FINANCIALS", "NOT_APPLICABLE"),
    "US_COMMUNICATION_SERVICES": ("US_TOTAL_MARKET", "US_BROAD_LARGE_CAP"),
    "US_CONSUMER_STAPLES": ("US_TOTAL_MARKET", "US_BROAD_LARGE_CAP"),
    "US_FINANCIALS": ("US_TOTAL_MARKET", "US_BROAD_LARGE_CAP"),
    "US_HEALTHCARE": ("US_TOTAL_MARKET", "US_BROAD_LARGE_CAP"),
    "CHINA_INTERNET": ("CHINA_BROAD", "EMERGING_ASIA"),
    "EUROPE_AEROSPACE_DEFENCE": ("EUROPE_INDUSTRIALS", "EUROPE_BROAD"),
    "EUROPE_INFRASTRUCTURE": ("EUROPE_INDUSTRIALS", "EUROPE_BROAD"),
    "GLOBAL_AEROSPACE_DEFENCE": ("GLOBAL_INDUSTRIALS", "NOT_APPLICABLE"),
    "GLOBAL_AI": ("GLOBAL_TECHNOLOGY", "NOT_APPLICABLE"),
    "GLOBAL_BATTERY_EV": ("GLOBAL_INDUSTRIALS", "GLOBAL_MATERIALS"),
    "GLOBAL_CLEAN_ENERGY": ("GLOBAL_UTILITIES", "GLOBAL_ENERGY"),
    "GLOBAL_CYBERSECURITY": ("GLOBAL_TECHNOLOGY", "NOT_APPLICABLE"),
    "GLOBAL_GENOMICS": ("GLOBAL_BIOTECHNOLOGY", "GLOBAL_HEALTHCARE"),
    "GLOBAL_INFRASTRUCTURE": ("GLOBAL_INDUSTRIALS", "NOT_APPLICABLE"),
    "GLOBAL_QUANTUM_COMPUTING": ("GLOBAL_TECHNOLOGY", "NOT_APPLICABLE"),
    "GLOBAL_ROBOTICS_AUTOMATION": ("GLOBAL_INDUSTRIALS", "GLOBAL_TECHNOLOGY"),
    "GLOBAL_SEMICONDUCTORS": ("GLOBAL_TECHNOLOGY", "NOT_APPLICABLE"),
    "GLOBAL_SOLAR": ("GLOBAL_CLEAN_ENERGY", "GLOBAL_UTILITIES"),
    "GLOBAL_SPACE": ("GLOBAL_INDUSTRIALS", "NOT_APPLICABLE"),
    "GLOBAL_URANIUM_NUCLEAR": ("GLOBAL_ENERGY", "GLOBAL_MATERIALS"),
    "GLOBAL_WATER": ("GLOBAL_INDUSTRIALS", "GLOBAL_UTILITIES"),
    "US_AEROSPACE_DEFENCE": ("GLOBAL_INDUSTRIALS", "US_BROAD_LARGE_CAP"),
    "US_AI": ("GLOBAL_AI", "US_BROAD_LARGE_CAP"),
    "UK_GILTS_SHORT": ("UK_GILTS_ALL", "ACTUAL_GBP_CASH"),
    "UK_GILTS_LONG": ("UK_GILTS_ALL", "NOT_APPLICABLE"),
    "UK_INDEX_LINKED_GILTS": ("UK_GILTS_ALL", "NOT_APPLICABLE"),
    "GBP_OVERNIGHT_CASH": ("ACTUAL_GBP_CASH", "NOT_APPLICABLE"),
}


REGISTRY_CORRECTIONS = [
    ("IE00BKWQ0C77", "EUROPE_BROAD", "PROPOSED_EUROPE_CONSUMER_DISCRETIONARY", "Europe consumer-discretionary sector product"),
    ("IE00BKWQ0F09", "EUROPE_BROAD", "EUROPE_ENERGY", "Europe energy sector product"),
    ("IE00BKWQ0J47", "EUROPE_BROAD", "EUROPE_INDUSTRIALS", "Europe industrials sector product"),
    ("IE00BKWQ0K51", "EUROPE_BROAD", "EUROPE_TECHNOLOGY", "Europe technology sector product"),
    ("IE00BKWQ0L68", "EUROPE_BROAD", "EUROPE_MATERIALS", "Europe materials sector product"),
    ("IE00BKWQ0N82", "EUROPE_BROAD", "PROPOSED_EUROPE_COMMUNICATION_SERVICES", "Europe communication-services sector product"),
    ("IE00BKWQ0P07", "EUROPE_BROAD", "EUROPE_UTILITIES", "Europe utilities sector product"),
    ("IE00BYTRR863", "EUROPE_ENERGY", "GLOBAL_ENERGY", "MSCI World Energy implementation"),
    ("IE00BYTRR970", "EUROPE_FINANCIALS", "GLOBAL_FINANCIALS", "MSCI World Financials implementation"),
    ("IE00BYTRRB94", "EUROPE_HEALTHCARE", "GLOBAL_HEALTHCARE", "MSCI World Health Care implementation"),
    ("IE00BYTRRC02", "EUROPE_INDUSTRIALS", "GLOBAL_INDUSTRIALS", "MSCI World Industrials implementation"),
    ("IE00BYTRRD19", "EUROPE_TECHNOLOGY", "GLOBAL_TECHNOLOGY", "MSCI World Technology implementation"),
    ("IE00BYTRRF33", "EUROPE_MATERIALS", "GLOBAL_MATERIALS", "MSCI World Materials implementation"),
    ("IE00BYTRRH56", "EUROPE_UTILITIES", "GLOBAL_UTILITIES", "MSCI World Utilities implementation"),
    ("IE00B5MTWD60", "GLOBAL_BANKS", "EUROPE_BANKS", "STOXX Europe 600 Optimised Banks implementation"),
    ("IE00BXDZNQ90", "AUSTRALIA", "PROPOSED_AUSTRALIA_GBP_HEDGED", "GBP-hedged Australia share class"),
    ("IE00BKFB6K94", "CHINA_BROAD", "CHINA_A_SHARES", "MSCI China A implementation"),
    ("FR0011720911", "CHINA_BROAD", "CHINA_A_SHARES", "MSCI China A implementation"),
    ("IE000NFR7C63", "CHINA_BROAD", "PROPOSED_CHINA_TECHNOLOGY", "China technology implementation"),
    ("IE000U9ODG19", "US_AEROSPACE_DEFENCE", "GLOBAL_AEROSPACE_DEFENCE", "Global aerospace-and-defence implementation"),
    ("IE00BLCHJ641", "GLOBAL_INFRASTRUCTURE", "PROPOSED_US_INFRASTRUCTURE", "US infrastructure-development implementation"),
    ("IE000AFVONT7", "GLOBAL_INFRASTRUCTURE", "EUROPE_INFRASTRUCTURE", "Europe infrastructure implementation"),
    ("IE00BYZK4776", "GLOBAL_HEALTHCARE", "PROPOSED_GLOBAL_HEALTHCARE_INNOVATION", "Healthcare-innovation thematic implementation"),
    ("IE00BYZK4883", "GLOBAL_TECHNOLOGY", "PROPOSED_GLOBAL_DIGITALISATION", "Digitalisation thematic implementation"),
]


MISSING_DEEPVUE_OUTCOMES = {
    "Airlines": ("PRODUCT_EXISTS_ALREADY_IN_DISCOVERY_REGISTRY", "TRIP/TRYP is a mixed airlines, hotels and cruise-lines exposure; not an exact airlines-only family"),
    "Bitcoin": ("STRUCTURALLY_UNSUITABLE", "Direct Bitcoin cETNs in the registry are structurally excluded from this ordinary long-only sleeve and cannot be newly bought in a stocks-and-shares ISA from 6 April 2026"),
    "Bitcoin Miners": ("PRODUCT_EXISTS_ALREADY_IN_DISCOVERY_REGISTRY", "Blockchain/crypto-equity UCITS products exist, but a pure miners exposure and economic distinctness require manual review"),
    "Growth Stocks": ("PRODUCT_EXISTS_ALREADY_IN_DISCOVERY_REGISTRY", "US/global growth products exist in the registry but were deliberately outside the A0A1 style scope"),
    "Home Construction": ("NO_UK_RETAIL_PRODUCT_FOUND", "No exact current UK-retail UCITS home-construction product was established by registry plus targeted official-site search"),
    "Medical": ("NOT_DISTINCT_ECONOMIC_OPPORTUNITY", "Healthcare, biotechnology, genomics and medical-robotics exposures already cover the economics; the label alone does not justify another family"),
    "Social Media": ("NO_UK_RETAIL_PRODUCT_FOUND", "The LSE page found is a US ETF line on XLOM, not a validated XLON UK-retail UCITS implementation"),
    "Steel": ("NO_UK_RETAIL_PRODUCT_FOUND", "Industrial-metals/mining products exist, but no exact current UK-retail steel ETF was established"),
    "Telecom": ("PRODUCT_EXISTS_ALREADY_IN_DISCOVERY_REGISTRY", "The TELE Europe communication-services UCITS line already exists in the registry but was misclassified as EUROPE_BROAD"),
}


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROGRAMME_ROOT / name, keep_default_na=False)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        frame.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=json_default) + "\n", encoding="utf-8")


def write_parquet(path: Path, frame: pd.DataFrame, metadata: dict[str, str]) -> None:
    table = pa.Table.from_pandas(frame, preserve_index=False)
    current = dict(table.schema.metadata or {})
    current.update({str(key).encode(): str(value).encode() for key, value in metadata.items()})
    pq.write_table(table.replace_schema_metadata(current), path, compression="zstd")


def fetch_public_sources() -> tuple[list[dict[str, Any]], dict[str, str]]:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    ledger: list[dict[str, Any]] = []
    timestamps: dict[str, str] = {}
    session = requests.Session()
    session.headers.update({"User-Agent": "UKACTIVE-A3R0-research/1.0 evidence capture"})
    for source_id, url in PUBLIC_SOURCES.items():
        capture_path = SOURCE_DIR / f"{source_id.lower()}.html"
        retrieved_at = utc_now()
        status = "NOT_RETRIEVED"
        raw = b""
        http_status: int | str = "NOT_AVAILABLE"
        try:
            response = session.get(url, timeout=45)
            http_status = response.status_code
            raw = response.content
            if response.status_code == 200 and raw:
                capture_path.write_bytes(raw)
                status = "RETRIEVED_LIVE_READ_ONLY"
            else:
                status = f"HTTP_{response.status_code}"
        except requests.RequestException as exc:
            status = f"REQUEST_ERROR_{type(exc).__name__}"
        timestamps[source_id] = retrieved_at
        ledger.append(
            {
                "evidence_id": stable_id("A3R0EVD", source_id, url, sha256_bytes(raw) if raw else status),
                "evidence_type": "CURRENT_PUBLIC_RULE_OR_PRODUCT_PAGE",
                "source_tier": "PRIMARY",
                "publisher": source_id.split("_")[0],
                "title": source_id,
                "url": url,
                "retrieved_at": retrieved_at,
                "observation_date": "2026-08-22",
                "http_status": http_status,
                "retrieval_status": status,
                "source_sha256": sha256_bytes(raw) if raw else "NOT_AVAILABLE",
                "local_capture": str(capture_path.relative_to(PROGRAMME_ROOT)) if capture_path.exists() else "NOT_AVAILABLE",
                "supports": "Current CCI disclosure transition, ISA rules, or targeted current LSE coverage audit",
                "historical_eligibility_supported": "NO",
                "confidence": "HIGH" if status == "RETRIEVED_LIVE_READ_ONLY" else "MEDIUM_URL_VERIFIED_VIA_WEB_RESEARCH",
                "warning": WARNING,
            }
        )
    return ledger, timestamps


def build_role_and_dynamic(
    master: pd.DataFrame,
    coverage: pd.DataFrame,
    panel: pd.DataFrame,
    policy: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    material_failures = policy["material_A2_lineage_failures"]
    scope_limited = policy["scope_limited_but_retained"]
    horizons = policy["dynamic_admission"]["signal_sessions"]
    merged = master.merge(coverage, on=["economic_exposure_family_id", "economic_exposure_name", "universe_tier"], how="left", validate="one_to_one")
    dynamic_rows: list[dict[str, Any]] = []
    for row in merged.itertuples(index=False):
        family_id = row.economic_exposure_family_id
        g = panel.loc[panel["economic_exposure_family_id"].eq(family_id)].sort_values("date")
        valid = (
            g["data_valid"].astype(bool)
            & ~g["stale_flag"].astype(bool)
            & ~g["missing_flag"].astype(bool)
            & ~g["proxy_flag"].astype(bool)
            & g["return_gbp_total"].notna()
        )
        raw_dates = {
            horizon: earliest_valid_observation_date(g["date"], valid, horizon)
            for horizon in horizons
        }
        valid_obs = int(row.valid_return_observations)
        material_failure = family_id in material_failures
        usable = bool(row.usable_history) if isinstance(row.usable_history, (bool, np.bool_)) else str(row.usable_history).lower() == "true"
        research_ready = usable and not material_failure
        intended = intended_rotation_role(pd.Series(row._asdict()))
        primary_role = intended if research_ready else "INSUFFICIENT_DATA"
        rotation_pool_id = competition_pool(family_id, intended)
        primary_pool_id = rotation_pool_id if research_ready else "POOL_INSUFFICIENT_DATA"
        benchmark_only = intended == "BENCHMARK_REFERENCE"
        selectable = research_ready and not benchmark_only and intended not in {"STRUCTURALLY_EXCLUDED"}
        equity_primary = research_ready and intended in {
            "BROAD_GEOGRAPHY_ROTATION",
            "COUNTRY_ROTATION",
            "SECTOR_ROTATION",
            "INDUSTRY_ROTATION",
            "THEME_ROTATION",
        }
        parent, secondary_parent = PARENT_MAP.get(family_id, ("NOT_APPLICABLE", "NOT_APPLICABLE"))
        overlap_id, overlap_basis = overlap_cluster(pd.Series(row._asdict()), intended)
        result: dict[str, Any] = {
            "economic_exposure_family_id": family_id,
            "economic_exposure_name": row.economic_exposure_name,
            "universe_tier": row.universe_tier,
            "opportunity_type": row.opportunity_type,
            "asset_class": row.asset_class,
            "sub_asset_class": row.sub_asset_class,
            "a0_primary_geography": row.primary_geography,
            "a0_geographic_scope": row.geographic_scope,
            "sector": row.sector,
            "industry": row.industry,
            "economic_theme": row.economic_theme,
            "deepvue_theme": row.deepvue_theme,
            "intended_rotation_role": intended,
            "primary_rotation_role": primary_role,
            "rotation_pool_id": rotation_pool_id,
            "primary_competition_pool_id": primary_pool_id,
            "parent_exposure_family_id": parent,
            "secondary_parent_exposure_family_id": secondary_parent,
            "overlap_cluster_id": overlap_id,
            "overlap_basis": overlap_basis,
            "breadth_level": breadth_level(pd.Series(row._asdict()), intended),
            "economic_beta_cluster": economic_beta_cluster(pd.Series(row._asdict()), intended),
            "selectable_flag": "YES" if selectable else "NO",
            "benchmark_only_flag": "YES" if benchmark_only else "NO",
            "primary_equity_competition_flag": "YES" if equity_primary else "NO",
            "research_data_ready_flag": "YES" if research_ready else "NO",
            "a2_lineage_validation_status": "FAIL_MATERIAL_MISCLASSIFICATION" if material_failure else ("PASS_WITH_SCOPE_LIMITATION" if family_id in scope_limited else ("PASS" if usable else "NO_USABLE_HISTORY")),
            "a2_lineage_issue": material_failures.get(family_id, scope_limited.get(family_id, "NOT_APPLICABLE" if usable else "NO_USABLE_IMPLEMENTATION_HISTORY")),
            "valid_return_observations": valid_obs,
            "first_valid_date": row.first_valid_date,
            "last_valid_date": row.last_valid_date,
            "research_maturity": maturity_label(valid_obs),
            "shorter_than_504_observations": "YES" if 0 < valid_obs < 504 else "NO",
            "recovered_by_dynamic_admission": "YES" if research_ready and 0 < valid_obs < 504 and pd.notna(raw_dates[21]) else "NO",
            "data_quality_flags": semicolon_join(
                [
                    "MATERIAL_A2_ECONOMIC_LINEAGE_MISMATCH" if material_failure else "NOT_APPLICABLE",
                    "SCOPE_LIMITED_IMPLEMENTATION" if family_id in scope_limited else "NOT_APPLICABLE",
                    "NO_USABLE_HISTORY" if not usable else "NOT_APPLICABLE",
                    "HISTORICAL_ELIGIBILITY_UNRESOLVED",
                ]
            ),
            "dynamic_admission_rule": "L_CUMULATIVE_VALID_A2_OBSERVATIONS_NO_STALE_MISSING_PROXY",
            "current_eligibility_back_projected": "NO",
            "warning": WARNING,
        }
        for horizon in horizons:
            raw_date = raw_dates[horizon]
            admitted_date = raw_date if research_ready else pd.NaT
            result[f"raw_earliest_valid_{horizon}_session_signal_date"] = raw_date
            result[f"earliest_valid_{horizon}_session_signal_date"] = admitted_date
            result[f"eligible_{horizon}_session_research"] = "YES" if pd.notna(admitted_date) else "NO"
        dynamic_rows.append(result)
    dynamic = pd.DataFrame(dynamic_rows).sort_values("economic_exposure_family_id").reset_index(drop=True)
    role_columns = [
        "economic_exposure_family_id",
        "economic_exposure_name",
        "universe_tier",
        "opportunity_type",
        "asset_class",
        "sub_asset_class",
        "a0_primary_geography",
        "a0_geographic_scope",
        "sector",
        "industry",
        "economic_theme",
        "deepvue_theme",
        "intended_rotation_role",
        "primary_rotation_role",
        "rotation_pool_id",
        "primary_competition_pool_id",
        "parent_exposure_family_id",
        "secondary_parent_exposure_family_id",
        "overlap_cluster_id",
        "overlap_basis",
        "breadth_level",
        "economic_beta_cluster",
        "selectable_flag",
        "benchmark_only_flag",
        "primary_equity_competition_flag",
        "research_data_ready_flag",
        "a2_lineage_validation_status",
        "a2_lineage_issue",
        "valid_return_observations",
        "research_maturity",
        "shorter_than_504_observations",
        "recovered_by_dynamic_admission",
        "data_quality_flags",
        "warning",
    ]
    return dynamic[role_columns].copy(), dynamic


def build_pool_master(role: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    all_pool_ids = sorted(set(role["rotation_pool_id"]) | set(role["primary_competition_pool_id"]))
    for pool_id in all_pool_ids:
        descriptive = role.loc[role["rotation_pool_id"].eq(pool_id)]
        effective = role.loc[role["primary_competition_pool_id"].eq(pool_id)]
        roles = semicolon_join(descriptive["intended_rotation_role"])
        primary_equity = pool_id not in {
            "POOL_DEFENSIVE_FIXED_INCOME",
            "POOL_DEFENSIVE_CASH_LIKE",
            "POOL_DEFENSIVE_REAL_ASSETS",
            "POOL_GLOBAL_BENCHMARK_REFERENCES",
            "POOL_INSUFFICIENT_DATA",
            "POOL_STRUCTURALLY_EXCLUDED",
        }
        rows.append(
            {
                "rotation_pool_id": pool_id,
                "pool_description": POOL_DESCRIPTIONS.get(pool_id, "Deterministic A3R0 competition pool"),
                "intended_rotation_roles": roles,
                "descriptive_family_count": len(descriptive),
                "effective_research_family_count": len(effective),
                "selectable_family_count": int(effective["selectable_flag"].eq("YES").sum()),
                "benchmark_only_family_count": int(effective["benchmark_only_flag"].eq("YES").sum()),
                "primary_equity_tournament_pool": "YES" if primary_equity else "NO",
                "descriptive_member_family_ids": semicolon_join(descriptive["economic_exposure_family_id"]),
                "effective_member_family_ids": semicolon_join(effective["economic_exposure_family_id"]),
                "external_reference_assets": "ACTUAL_GBP_CASH" if pool_id == "POOL_DEFENSIVE_CASH_LIKE" else "NOT_APPLICABLE",
                "deepvue_controls_membership": "NO",
                "warning": WARNING,
            }
        )
    return pd.DataFrame(rows)


def build_parent_maps(role: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    role_idx = role.set_index("economic_exposure_family_id")
    relationships: list[dict[str, Any]] = []
    parent_benchmarks: list[dict[str, Any]] = []
    for row in role.itertuples(index=False):
        family_id = row.economic_exposure_family_id
        parents = [
            ("PRIMARY", row.parent_exposure_family_id),
            ("SECONDARY", row.secondary_parent_exposure_family_id),
        ]
        for relation_type, parent_id in parents:
            if parent_id == "NOT_APPLICABLE":
                continue
            parent_exists = parent_id in role_idx.index
            parent_duplicate = parent_id if parent_exists else "EXTERNAL_REFERENCE"
            relationships.append(
                {
                    "child_exposure_family_id": family_id,
                    "child_exposure_name": row.economic_exposure_name,
                    "parent_relation_type": relation_type,
                    "parent_exposure_family_id": parent_id,
                    "parent_exists_in_A0A1_master": "YES" if parent_exists else "NO_EXTERNAL_REFERENCE",
                    "relationship_basis": "ECONOMIC_HIERARCHY_NOT_DUPLICATION",
                    "child_duplicate_group_id": "PRESERVED_IN_A0A1_MASTER",
                    "parent_duplicate_identity": parent_duplicate,
                    "labelled_duplicate_due_only_to_overlap": "NO",
                    "relationship_status": "ACTIVE_MAP" if parent_exists else "EXTERNAL_REFERENCE_MAP",
                    "warning": WARNING,
                }
            )
        primary = row.parent_exposure_family_id
        secondary = row.secondary_parent_exposure_family_id
        if row.asset_class in {"EQUITY", "PROPERTY", "INFRASTRUCTURE"}:
            status = "PARENT_MAPPED" if primary != "NOT_APPLICABLE" else "GLOBAL_BENCHMARK_ONLY_NO_JUSTIFIED_PARENT"
        else:
            status = "NOT_APPLICABLE_NON_EQUITY"
        parent_benchmarks.append(
            {
                "economic_exposure_family_id": family_id,
                "economic_exposure_name": row.economic_exposure_name,
                "parent_benchmark_family_id": primary,
                "secondary_parent_benchmark_family_id": secondary,
                "parent_benchmark_map_status": status,
                "parent_history_research_ready": "YES" if primary in role_idx.index and role_idx.loc[primary, "research_data_ready_flag"] == "YES" else ("NOT_APPLICABLE" if primary == "NOT_APPLICABLE" else "NO"),
                "global_fallback_benchmark_family_id": "GLOBAL_DEVELOPED_WORLD" if row.asset_class in {"EQUITY", "PROPERTY", "INFRASTRUCTURE"} else "NOT_APPLICABLE",
                "mapping_uses_deepvue": "NO",
                "warning": WARNING,
            }
        )
    return pd.DataFrame(relationships), pd.DataFrame(parent_benchmarks)


def build_overlap(role: pd.DataFrame) -> pd.DataFrame:
    out = role[
        [
            "economic_exposure_family_id",
            "economic_exposure_name",
            "overlap_cluster_id",
            "overlap_basis",
            "parent_exposure_family_id",
            "secondary_parent_exposure_family_id",
            "economic_beta_cluster",
            "rotation_pool_id",
        ]
    ].copy()
    out["holdings_overlap_metric_status"] = "NOT_MEASURED_A3R0_NOT_REQUIRED_FOR_PASS"
    out["exact_holdings_overlap_percent"] = "NOT_AVAILABLE"
    out["overlap_does_not_imply_duplicate"] = "YES"
    out["common_beta_control_available_for_later_research"] = "YES"
    out["evidence_basis"] = "A0A1_CLASSIFICATION_PLUS_EXPLICIT_A3R0_ECONOMIC_HIERARCHY"
    out["warning"] = WARNING
    return out


def build_benchmark_map(role: pd.DataFrame, coverage: pd.DataFrame, policy: dict[str, Any]) -> pd.DataFrame:
    bench_id = policy["global_benchmark"]["research_family_id"]
    comparator = policy["global_benchmark"]["recognisable_live_comparator_family_id"]
    bench_cov = coverage.set_index("economic_exposure_family_id").loc[bench_id]
    rows: list[dict[str, Any]] = []
    for row in role.itertuples(index=False):
        applicable = row.asset_class in {"EQUITY", "PROPERTY", "INFRASTRUCTURE"}
        rows.append(
            {
                "economic_exposure_family_id": row.economic_exposure_family_id,
                "economic_exposure_name": row.economic_exposure_name,
                "global_benchmark_family_id": bench_id if applicable else "NOT_APPLICABLE",
                "global_benchmark_name": "Developed-world broad equities" if applicable else "NOT_APPLICABLE",
                "global_benchmark_valid_return_observations": int(bench_cov.valid_return_observations) if applicable else 0,
                "global_benchmark_first_valid_date": bench_cov.first_valid_date if applicable else "NOT_APPLICABLE",
                "global_benchmark_last_valid_date": bench_cov.last_valid_date if applicable else "NOT_APPLICABLE",
                "global_benchmark_A2_lineage_status": "PASS" if applicable else "NOT_APPLICABLE",
                "recognisable_live_comparator_family_id": comparator if applicable else "NOT_APPLICABLE",
                "benchmark_frozen_for_A3R1": "YES" if applicable else "NOT_APPLICABLE",
                "selection_basis": policy["global_benchmark"]["reason"] if applicable else "NOT_APPLICABLE",
                "GBP_total_return_validated_in_A2": "YES" if applicable else "NOT_APPLICABLE",
                "warning": WARNING,
            }
        )
    return pd.DataFrame(rows)


def prepare_candidate_table(
    implementation: pd.DataFrame,
    listing: pd.DataFrame,
    share_class: pd.DataFrame,
    investability: pd.DataFrame,
    registry: pd.DataFrame,
    policy: dict[str, Any],
) -> pd.DataFrame:
    listing_cols = [
        "listing_id",
        "exchange",
        "active_listing_status",
        "active_status_verification_date",
        "active_status_confidence",
        "listing_inception_date",
        "identity_evidence_ids",
    ]
    sc_cols = [
        "share_class_id",
        "share_class_name",
        "sub_fund_name",
        "share_class_currency",
        "fund_base_currency",
        "product_structure",
        "ucits_status",
        "ucits_evidence_basis",
        "instrument_type",
        "physical_backing",
        "collateralisation",
        "issuer_risk_assessment",
        "counterparty_risk_assessment",
        "leverage",
        "daily_reset",
        "path_dependence",
        "maturity",
    ]
    inv_cols = [
        "listing_id",
        "current_uk_retail_eligibility",
        "isa_eligibility",
        "sipp_eligibility",
        "kid_retail_document_evidence",
        "kid_retail_document_url",
        "structural_eligibility",
        "eligibility_verification_date",
        "eligibility_confidence",
        "eligibility_evidence_ids",
    ]
    candidates = implementation.merge(listing[listing_cols], on="listing_id", how="left", validate="many_to_one")
    candidates = candidates.merge(share_class[sc_cols], on="share_class_id", how="left", validate="many_to_one")
    candidates = candidates.merge(investability[inv_cols], on="listing_id", how="left", validate="one_to_one")
    source_map = (
        registry.groupby(["isin", "ticker"], dropna=False)
        .agg(
            registry_source_urls=("source_url", semicolon_join),
            registry_evidence_ids=("source_evidence_id", semicolon_join),
            registry_discovery_record_ids=("discovery_record_id", semicolon_join),
        )
        .reset_index()
    )
    candidates = candidates.merge(source_map, on=["isin", "ticker"], how="left")
    exclusions = policy["family_candidate_exclusions"]
    candidates["economic_lineage_valid"] = [
        candidate_is_economically_valid(family_id, isin, exclusions)
        for family_id, isin in zip(candidates["economic_exposure_family_id"], candidates["isin"], strict=True)
    ]
    candidates["LSE_current_status"] = candidates["active_listing_status"].map(lse_public_status)
    candidates["UK_retail_disclosure_status"] = candidates["kid_retail_document_evidence"].map(retail_disclosure_status)
    candidates["public_ISA_rules_status"] = [
        public_isa_status(isa, instrument, structure)
        for isa, instrument, structure in zip(
            candidates["isa_eligibility"], candidates["instrument_type"], candidates["product_structure"], strict=True
        )
    ]
    candidates["public_evidence_URLs"] = [
        semicolon_join([kid, source])
        for kid, source in zip(candidates["kid_retail_document_url"], candidates["registry_source_urls"], strict=True)
    ]
    candidates["public_evidence_date"] = candidates["eligibility_verification_date"].where(
        candidates["eligibility_verification_date"].ne(""), candidates["active_status_verification_date"]
    )
    candidates["public_evidence_confidence"] = candidates["eligibility_confidence"].where(
        candidates["eligibility_confidence"].ne(""), candidates["active_status_confidence"]
    )
    candidates["rank_verified"] = candidates["current_investability_state"].ne("CURRENTLY_INVESTABLE").astype(int)
    candidates["rank_active"] = candidates["LSE_current_status"].ne("CONFIRMED").astype(int)
    candidates["rank_gbp"] = ~(
        candidates["listing_currency"].eq("GBP") & candidates["price_unit"].isin(["GBP", "GBX"])
    )
    confidence_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    candidates["rank_confidence"] = candidates["implementation_evidence_confidence"].map(confidence_rank).fillna(3)
    preferred_isin_overrides = policy.get("preferred_current_isin_overrides", {})
    candidates["rank_family_override"] = [
        0 if family_id not in preferred_isin_overrides or isin == preferred_isin_overrides[family_id] else 1
        for family_id, isin in zip(candidates["economic_exposure_family_id"], candidates["isin"], strict=True)
    ]
    return candidates


def select_current_lines(candidates: pd.DataFrame, role: pd.DataFrame) -> pd.DataFrame:
    role_idx = role.set_index("economic_exposure_family_id")
    queue_families = set(role.loc[role["research_data_ready_flag"].eq("YES"), "economic_exposure_family_id"])
    rows: list[pd.Series] = []
    for family_id in sorted(queue_families):
        g = candidates.loc[
            candidates["economic_exposure_family_id"].eq(family_id)
            & candidates["economic_lineage_valid"]
            & candidates["LSE_current_status"].eq("CONFIRMED")
        ].copy()
        if g.empty:
            continue
        g = g.sort_values(
            [
                "rank_family_override",
                "rank_verified",
                "rank_active",
                "rank_gbp",
                "rank_confidence",
                "implementation_evidence_order",
                "listing_id",
            ],
            kind="stable",
        )
        preferred = g.iloc[0].copy()
        preferred["preferred_or_alternate"] = "PREFERRED"
        preferred["implementation_selection_reason"] = "FAMILY_SCOPE_OVERRIDE_IF_DECLARED|CURRENT_STATUS|ACTIVE_XLON|GBP_GBX|EVIDENCE_CONFIDENCE|A0_ORDER|STABLE_ID"
        rows.append(preferred)
        remainder = g.iloc[1:].copy()
        if not remainder.empty:
            same_isin = remainder.loc[remainder["isin"].eq(preferred["isin"])]
            alternate = (same_isin.iloc[0] if not same_isin.empty else remainder.iloc[0]).copy()
            alternate["preferred_or_alternate"] = "ALTERNATE"
            alternate["implementation_selection_reason"] = "NEXT_VALID_LINE|SAME_ISIN_ALTERNATE_LISTING_FIRST|STABLE_ORDER"
            rows.append(alternate)
    selected = pd.DataFrame(rows)
    if selected.empty:
        return selected
    role_cols = [
        "economic_exposure_family_id",
        "economic_exposure_name",
        "primary_rotation_role",
        "rotation_pool_id",
        "primary_competition_pool_id",
        "parent_exposure_family_id",
        "selectable_flag",
        "benchmark_only_flag",
        "research_data_ready_flag",
    ]
    selected = selected.merge(role[role_cols], on="economic_exposure_family_id", how="left", validate="many_to_one")
    selected["IBKR_contract_status"] = "NOT_CHECKED"
    selected["IBKR_contract_id"] = "NOT_CHECKED"
    selected["IBKR_exchange_found"] = "NOT_CHECKED"
    selected["IBKR_symbol_found"] = "NOT_CHECKED"
    selected["IBKR_quote_status"] = "NOT_CHECKED"
    selected["IBKR_LSE_listing_status"] = "NOT_CHECKED"
    selected["IBKR_ISA_purchase_status"] = "NOT_CHECKED"
    selected["verification_notes"] = "PUBLIC EVIDENCE ONLY; CHATGPT/IBKR READ-ONLY VERIFICATION PENDING; ACCOUNT-SPECIFIC ISA PURCHASE NOT ESTABLISHED"
    selected["current_eligibility_not_historical"] = "YES"
    selected["warning"] = WARNING
    return selected.sort_values(["economic_exposure_family_id", "preferred_or_alternate"]).reset_index(drop=True)


def build_theme_audit(
    deepvue: pd.DataFrame,
    theme_taxonomy: pd.DataFrame,
    master: pd.DataFrame,
    role: pd.DataFrame,
    registry: pd.DataFrame,
) -> pd.DataFrame:
    role_idx = role.set_index("economic_exposure_family_id")
    rows: list[dict[str, Any]] = []
    registry_text = (registry["description_as_published"] + " " + registry["display_name"]).str.upper()

    keyword_map = {
        "Airlines": "TRAVEL|AIRLINE",
        "Bitcoin": "BITCOIN",
        "Bitcoin Miners": "BLOCKCHAIN|CRYPTO",
        "Growth Stocks": "GROWTH",
        "Home Construction": "HOME CONSTRUCTION|HOMEBUILD|HOUSING",
        "Medical": "MEDICAL",
        "Social Media": "SOCIAL MEDIA",
        "Steel": "STEEL",
        "Telecom": "COMM SERV|TELECOM",
    }
    for item in deepvue.itertuples(index=False):
        if item.deepvue_theme == "NOT_APPLICABLE":
            continue
        mapped = [value for value in str(item.mapped_economic_exposure_family_ids).split(";") if value and not value.startswith("NOT_")]
        if mapped:
            ready = [family for family in mapped if family in role_idx.index and role_idx.loc[family, "research_data_ready_flag"] == "YES"]
            outcome = "COVERED_BY_EXISTING_FAMILY" if ready else "NO_USABLE_HISTORY"
            note = f"Mapped families: {';'.join(mapped)}; research-ready after A3R0 lineage control: {semicolon_join(ready)}"
        else:
            outcome, note = MISSING_DEEPVUE_OUTCOMES[item.deepvue_theme]
        pattern = keyword_map.get(item.deepvue_theme)
        matches = registry.loc[registry_text.str.contains(pattern, regex=True, na=False)] if pattern else registry.loc[registry["matched_economic_exposure_family_id"].isin(mapped)]
        rows.append(
            {
                "audit_category_type": "DEEPVUE_CONFIRMED_LABEL",
                "audit_label": item.deepvue_theme,
                "coverage_outcome": outcome,
                "existing_family_ids": semicolon_join(mapped),
                "research_ready_family_ids": semicolon_join([family for family in mapped if family in role_idx.index and role_idx.loc[family, "research_data_ready_flag"] == "YES"]),
                "registry_match_count": len(matches),
                "registry_match_ISINs": semicolon_join(matches["isin"]),
                "registry_match_tickers": semicolon_join(matches["ticker"]),
                "new_product_added_to_master": "NO",
                "manual_review_required": "YES" if outcome in {"PRODUCT_EXISTS_ALREADY_IN_DISCOVERY_REGISTRY", "REQUIRES_MANUAL_REVIEW"} else "NO",
                "deepvue_controls_competition": "NO",
                "evidence_basis": "A0A1_DEEPVUE_CROSSWALK|A0A1_DISCOVERY_REGISTRY|TARGETED_PUBLIC_SEARCH_WHERE_NEEDED",
                "assessment_notes": note,
                "warning": WARNING,
            }
        )

    for item in theme_taxonomy.itertuples(index=False):
        mapped = [value for value in str(item.current_family_ids).split(";") if value and value != "NOT_APPLICABLE"]
        ready = [family for family in mapped if family in role_idx.index and role_idx.loc[family, "research_data_ready_flag"] == "YES"]
        outcome = "COVERED_BY_EXISTING_FAMILY" if ready else "NO_USABLE_HISTORY"
        rows.append(
            {
                "audit_category_type": "ECONOMIC_THEME_TAXONOMY",
                "audit_label": item.economic_theme,
                "coverage_outcome": outcome,
                "existing_family_ids": semicolon_join(mapped),
                "research_ready_family_ids": semicolon_join(ready),
                "registry_match_count": int(registry["matched_economic_exposure_family_id"].isin(mapped).sum()),
                "registry_match_ISINs": semicolon_join(registry.loc[registry["matched_economic_exposure_family_id"].isin(mapped), "isin"]),
                "registry_match_tickers": semicolon_join(registry.loc[registry["matched_economic_exposure_family_id"].isin(mapped), "ticker"]),
                "new_product_added_to_master": "NO",
                "manual_review_required": "YES" if not ready else "NO",
                "deepvue_controls_competition": "NO",
                "evidence_basis": "A0A1_THEME_TAXONOMY|A3R0_LINEAGE_CONTROL",
                "assessment_notes": "Existing economic-theme taxonomy audited without inventing new labels",
                "warning": WARNING,
            }
        )

    conventional_sectors = [
        "TECHNOLOGY",
        "FINANCIALS",
        "HEALTHCARE",
        "INDUSTRIALS",
        "CONSUMER_DISCRETIONARY",
        "CONSUMER_STAPLES",
        "COMMUNICATION_SERVICES",
        "ENERGY",
        "MATERIALS",
        "UTILITIES",
        "REAL_ESTATE",
    ]
    for sector in conventional_sectors:
        mapped = master.loc[master["sector"].eq(sector), "economic_exposure_family_id"].tolist()
        ready = [family for family in mapped if family in role_idx.index and role_idx.loc[family, "research_data_ready_flag"] == "YES"]
        pattern = sector.replace("_", " ")
        aliases = {
            "CONSUMER_DISCRETIONARY": "CONS DIS|CONSUMER DIS",
            "CONSUMER_STAPLES": "CONS STAP|CONSUMER STAP",
            "COMMUNICATION_SERVICES": "COMM SERV|COMMUNICATION",
            "REAL_ESTATE": "REAL ESTATE",
        }
        matches = registry.loc[registry_text.str.contains(aliases.get(sector, pattern), regex=True, na=False) & registry["structural_exclusion_flag"].eq("NO")]
        if ready:
            outcome = "COVERED_BY_EXISTING_FAMILY"
        elif not matches.empty:
            outcome = "PRODUCT_EXISTS_ALREADY_IN_DISCOVERY_REGISTRY"
        else:
            outcome = "NO_UK_RETAIL_PRODUCT_FOUND"
        rows.append(
            {
                "audit_category_type": "CONVENTIONAL_SECTOR_ROTATION",
                "audit_label": sector,
                "coverage_outcome": outcome,
                "existing_family_ids": semicolon_join(mapped),
                "research_ready_family_ids": semicolon_join(ready),
                "registry_match_count": len(matches),
                "registry_match_ISINs": semicolon_join(matches["isin"]),
                "registry_match_tickers": semicolon_join(matches["ticker"]),
                "new_product_added_to_master": "NO",
                "manual_review_required": "YES" if not ready else "NO",
                "deepvue_controls_competition": "NO",
                "evidence_basis": "A0A1_MASTER|A0A1_DISCOVERY_REGISTRY|A3R0_LINEAGE_CONTROL",
                "assessment_notes": "Coverage means at least one clean family; it does not imply a complete global/Europe/US sector grid",
                "warning": WARNING,
            }
        )
    return pd.DataFrame(rows).sort_values(["audit_category_type", "audit_label"]).reset_index(drop=True)


def build_corrections(policy: dict[str, Any], registry: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for family_id, issue in policy["material_A2_lineage_failures"].items():
        rows.append(
            {
                "correction_id": stable_id("A3R0COR", "FAMILY_HISTORY", family_id),
                "affected_object_type": "ECONOMIC_EXPOSURE_FAMILY_HISTORY",
                "affected_id": family_id,
                "source_stage": "A0A1_AND_A2",
                "existing_value": "A2_CANONICAL_HISTORY_ACCEPTED_UNDER_A0A1_FAMILY",
                "corrected_value": "BLOCK_FROM_A3R0_DYNAMIC_ADMISSION_PENDING_LINEAGE_REPAIR",
                "correction_status": "APPLIED_AS_A3R0_RESEARCH_GUARD_ONLY_NOT_REWRITTEN_UPSTREAM",
                "materiality": "CRITICAL_FOR_ROTATION_RESEARCH",
                "A2_history_impacted": "YES",
                "remediation_required": "RECLASSIFY_IMPLEMENTATIONS_AND_REBUILD_A2_CANONICAL_HISTORY",
                "evidence_ids": "A2_CANONICAL_IMPLEMENTATION_HISTORY|A0A1_SHARE_CLASS_MASTER",
                "source_urls": "NOT_APPLICABLE_LOCAL_AUTHORITATIVE_DATA",
                "notes": issue,
                "warning": WARNING,
            }
        )
    for family_id, issue in policy["scope_limited_but_retained"].items():
        rows.append(
            {
                "correction_id": stable_id("A3R0COR", "SCOPE_LIMIT", family_id),
                "affected_object_type": "ECONOMIC_EXPOSURE_SCOPE_DISCLOSURE",
                "affected_id": family_id,
                "source_stage": "A0A1_AND_A2",
                "existing_value": "BROAD_FAMILY_LABEL",
                "corrected_value": "RETAIN_ID_WITH_EXPLICIT_SCOPE_LIMITATION",
                "correction_status": "APPLIED_AS_A3R0_DISPLAY_AND_RESEARCH_WARNING",
                "materiality": "OPEN_ITEM_NOT_AUTOMATIC_EXCLUSION",
                "A2_history_impacted": "YES_SCOPE_ONLY",
                "remediation_required": "REVIEW_BEFORE_PROMOTION_OR_DEPLOYMENT",
                "evidence_ids": "A2_CANONICAL_IMPLEMENTATION_HISTORY|A0A1_SHARE_CLASS_MASTER",
                "source_urls": "NOT_APPLICABLE_LOCAL_AUTHORITATIVE_DATA",
                "notes": issue,
                "warning": WARNING,
            }
        )
    for isin, old, new, note in REGISTRY_CORRECTIONS:
        matches = registry.loc[registry["isin"].eq(isin)]
        rows.append(
            {
                "correction_id": stable_id("A3R0COR", "REGISTRY_ISIN", isin, old, new),
                "affected_object_type": "DISCOVERY_REGISTRY_ISIN_CLASSIFICATION",
                "affected_id": isin,
                "source_stage": "A0A1_DISCOVERY_REGISTRY",
                "existing_value": old,
                "corrected_value": new,
                "correction_status": "PROPOSED_NOT_APPLIED_TO_IMMUTABLE_A0A1_OR_A2_OUTPUTS",
                "materiality": "MATERIAL_IF_USED_IN_ROTATION_POOL",
                "A2_history_impacted": "YES" if isin in set(sum(policy["family_candidate_exclusions"].values(), [])) else "POTENTIAL",
                "remediation_required": "REBUILD_FUND_SHARE_CLASS_LISTING_ASSIGNMENT_AND_ANY_A2_HISTORY",
                "evidence_ids": semicolon_join(matches["source_evidence_id"]),
                "source_urls": semicolon_join(matches["source_url"]),
                "notes": note,
                "warning": WARNING,
            }
        )
    return pd.DataFrame(rows).sort_values(["materiality", "affected_object_type", "affected_id"]).reset_index(drop=True)


def current_lines_outputs(selected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    current_cols = [
        "economic_exposure_family_id",
        "economic_exposure_name",
        "primary_rotation_role",
        "rotation_pool_id",
        "primary_competition_pool_id",
        "parent_exposure_family_id",
        "preferred_or_alternate",
        "fund_entity_id",
        "share_class_id",
        "listing_id",
        "isin",
        "ticker",
        "exchange",
        "mic",
        "listing_currency",
        "price_unit",
        "provider_issuer",
        "share_class_name",
        "product_structure",
        "instrument_type",
        "ucits_status",
        "ucits_evidence_basis",
        "current_investability_state",
        "LSE_current_status",
        "UK_retail_disclosure_status",
        "public_ISA_rules_status",
        "public_evidence_URLs",
        "public_evidence_date",
        "public_evidence_confidence",
        "implementation_selection_reason",
        "economic_lineage_valid",
        "warning",
    ]
    current = selected[current_cols].copy()
    public_cols = [
        "economic_exposure_family_id",
        "economic_exposure_name",
        "preferred_or_alternate",
        "isin",
        "ticker",
        "exchange",
        "mic",
        "listing_currency",
        "price_unit",
        "instrument_type",
        "product_structure",
        "ucits_status",
        "LSE_current_status",
        "UK_retail_disclosure_status",
        "public_ISA_rules_status",
        "current_uk_retail_eligibility",
        "isa_eligibility",
        "kid_retail_document_evidence",
        "kid_retail_document_url",
        "structural_eligibility",
        "eligibility_evidence_ids",
        "public_evidence_URLs",
        "public_evidence_date",
        "public_evidence_confidence",
        "current_eligibility_not_historical",
        "warning",
    ]
    public = selected[public_cols].copy()
    queue = pd.DataFrame(
        {
            "economic_exposure_family_id": selected["economic_exposure_family_id"],
            "economic_exposure_name": selected["economic_exposure_name"],
            "rotation_role": selected["primary_rotation_role"],
            "competition_pool": selected["primary_competition_pool_id"],
            "parent_exposure": selected["parent_exposure_family_id"],
            "preferred_or_alternate": selected["preferred_or_alternate"],
            "ISIN": selected["isin"],
            "ticker": selected["ticker"],
            "expected_exchange": selected["exchange"],
            "expected_MIC": selected["mic"],
            "listing_currency": selected["listing_currency"],
            "GBP_GBX_unit": selected["price_unit"],
            "issuer": selected["provider_issuer"],
            "structure": selected["product_structure"],
            "LSE_current_status": selected["LSE_current_status"],
            "UK_retail_disclosure_status": selected["UK_retail_disclosure_status"],
            "public_ISA_rules_status": selected["public_ISA_rules_status"],
            "public_evidence_URLs": selected["public_evidence_URLs"],
            "public_evidence_date": selected["public_evidence_date"],
            "public_evidence_confidence": selected["public_evidence_confidence"],
            "IBKR_contract_status": selected["IBKR_contract_status"],
            "IBKR_contract_id": selected["IBKR_contract_id"],
            "IBKR_exchange_found": selected["IBKR_exchange_found"],
            "IBKR_symbol_found": selected["IBKR_symbol_found"],
            "IBKR_quote_status": selected["IBKR_quote_status"],
            "IBKR_ISA_purchase_status": selected["IBKR_ISA_purchase_status"],
            "verification_notes": selected["verification_notes"],
            "listing_id": selected["listing_id"],
            "share_class_id": selected["share_class_id"],
            "selectable_flag": selected["selectable_flag"],
            "benchmark_only_flag": selected["benchmark_only_flag"],
            "warning": selected["warning"],
        }
    )
    return current, public, queue


def git_state() -> dict[str, Any]:
    try:
        top = subprocess.run(
            ["git", "-C", str(PROGRAMME_ROOT), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if top.returncode != 0:
            return {
                "commit": "NOT_AVAILABLE_NOT_A_GIT_WORKTREE",
                "worktree_state": "NOT_APPLICABLE_NOT_A_GIT_WORKTREE",
                "complete_patch_if_dirty": "NOT_APPLICABLE_NOT_A_GIT_WORKTREE",
            }
        root = top.stdout.strip()
        commit = subprocess.check_output(["git", "-C", root, "rev-parse", "HEAD"], text=True).strip()
        status = subprocess.check_output(["git", "-C", root, "status", "--porcelain"], text=True)
        patch = subprocess.check_output(["git", "-C", root, "diff", "--binary", "HEAD"], text=True)
        return {
            "commit": commit,
            "worktree_state": "CLEAN" if not status else "DIRTY",
            "status_porcelain": status,
            "complete_patch_if_dirty": patch if status else "NOT_APPLICABLE_CLEAN",
        }
    except (subprocess.SubprocessError, OSError) as exc:
        return {
            "commit": "NOT_AVAILABLE_GIT_QUERY_ERROR",
            "worktree_state": "UNKNOWN",
            "complete_patch_if_dirty": f"NOT_AVAILABLE_{type(exc).__name__}",
        }


def package_versions() -> dict[str, str]:
    names = ["numpy", "pandas", "pyarrow", "requests"]
    out = {"python": platform.python_version(), "platform": platform.platform()}
    for name in names:
        try:
            out[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            out[name] = "NOT_INSTALLED"
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Build UKACTIVE-A3R0 rotation universe validation outputs")
    parser.parse_args()
    started_at = utc_now()
    policy = read_json(CONFIG_PATH)

    master = read_csv("UKACTIVE_A0A1_ECONOMIC_EXPOSURE_MASTER.csv")
    registry = read_csv("UKACTIVE_A0A1_DISCOVERY_REGISTRY.csv")
    implementation = read_csv("UKACTIVE_A0A1_IMPLEMENTATION_CANDIDATES.csv")
    investability = read_csv("UKACTIVE_A0A1_CURRENT_INVESTABILITY.csv")
    listing = read_csv("UKACTIVE_A0A1_LISTING_MASTER.csv")
    share_class = read_csv("UKACTIVE_A0A1_SHARE_CLASS_MASTER.csv")
    duplicate_groups = read_csv("UKACTIVE_A0A1_DUPLICATE_GROUPS.csv")
    deepvue = read_csv("UKACTIVE_A0A1_DEEPVUE_THEME_CROSSWALK.csv")
    theme_taxonomy = read_csv("UKACTIVE_A0A1_THEME_TAXONOMY.csv")
    coverage = read_csv("UKACTIVE_A2_FAMILY_COVERAGE_AND_READINESS.csv")
    panel = pd.read_parquet(
        PROGRAMME_ROOT / "UKACTIVE_A2_TOTAL_RETURN_PANEL_GBP.parquet",
        columns=[
            "date",
            "economic_exposure_family_id",
            "return_gbp_total",
            "data_valid",
            "stale_flag",
            "missing_flag",
            "proxy_flag",
            "next_execution_eligible_date",
        ],
    )
    panel["date"] = pd.to_datetime(panel["date"])

    if len(master) != policy["authoritative_family_count"]:
        raise AssertionError(f"Expected 99 families, found {len(master)}")
    if master["economic_exposure_family_id"].duplicated().any():
        raise AssertionError("A0A1 economic exposure family IDs are not unique")

    evidence_ledger, source_timestamps = fetch_public_sources()
    role, dynamic = build_role_and_dynamic(master, coverage, panel, policy)
    pools = build_pool_master(role)
    parent_child, parent_benchmark = build_parent_maps(role)
    overlaps = build_overlap(role)
    global_benchmark = build_benchmark_map(role, coverage, policy)
    candidates = prepare_candidate_table(implementation, listing, share_class, investability, registry, policy)
    selected = select_current_lines(candidates, role)
    current_lines, public_eligibility, ibkr_queue = current_lines_outputs(selected)
    theme_audit = build_theme_audit(deepvue, theme_taxonomy, master, role, registry)
    corrections = build_corrections(policy, registry)

    selectable = role.loc[role["selectable_flag"].eq("YES")].copy()
    selectable = selectable.merge(
        dynamic[
            ["economic_exposure_family_id"]
            + [f"earliest_valid_{horizon}_session_signal_date" for horizon in policy["dynamic_admission"]["signal_sessions"]]
        ],
        on="economic_exposure_family_id",
        how="left",
        validate="one_to_one",
    )

    preferred_families = set(selected.loc[selected["preferred_or_alternate"].eq("PREFERRED"), "economic_exposure_family_id"])
    research_ready_families = set(role.loc[role["research_data_ready_flag"].eq("YES"), "economic_exposure_family_id"])
    missing_preferred = sorted(research_ready_families - preferred_families)

    tests = synthetic_failure_tests()

    def add_test(test_id: str, condition: bool, failure_mode: str, detail: str) -> None:
        tests.append(
            {
                "test_id": test_id,
                "test_type": "OBSERVED_DATA_ASSERTION",
                "failure_mode": failure_mode,
                "status": "PASS" if condition else "FAIL",
                "detail": detail,
            }
        )

    add_test("A3R0-T016", len(role) == 99, "existing family count changes", f"Retained families={len(role)}")
    add_test("A3R0-T017", set(role["economic_exposure_family_id"]) == set(master["economic_exposure_family_id"]), "family IDs deleted or renumbered", "Exact A0A1 ID set retained")
    add_test("A3R0-T018", len(dynamic) == 99, "dynamic table omits family", f"Dynamic rows={len(dynamic)}")
    add_test("A3R0-T019", not role.loc[role["primary_rotation_role"].eq("DEFENSIVE_REFERENCE"), "primary_equity_competition_flag"].eq("YES").any(), "defensive enters primary equity tournament", "No defensive family is in primary equity competition")
    add_test("A3R0-T020", not role.loc[role["a2_lineage_validation_status"].eq("FAIL_MATERIAL_MISCLASSIFICATION"), "research_data_ready_flag"].eq("YES").any(), "materially misclassified A2 history admitted", "All 14 material mismatches are blocked")
    add_test("A3R0-T021", len(role.loc[role["a2_lineage_validation_status"].eq("FAIL_MATERIAL_MISCLASSIFICATION")]) == 14, "known lineage failures omitted", "Fourteen material failures recorded")
    add_test("A3R0-T022", dynamic.loc[dynamic["recovered_by_dynamic_admission"].eq("YES"), "valid_return_observations"].lt(504).all(), "504 gate retained", "Recovered families all have under 504 observations")
    add_test("A3R0-T023", dynamic.loc[dynamic["eligible_21_session_research"].eq("YES"), "valid_return_observations"].ge(21).all(), "21-session warm-up violated", "All admitted 21-session families have enough valid returns")
    add_test("A3R0-T024", not dynamic.loc[dynamic["a2_lineage_validation_status"].eq("NO_USABLE_HISTORY"), "eligible_21_session_research"].eq("YES").any(), "zero-history family admitted", "No zero-history family admitted")
    add_test("A3R0-T025", selected["IBKR_contract_status"].eq("NOT_CHECKED").all(), "IBKR inferred from public/local data", "All contract statuses remain NOT_CHECKED")
    add_test("A3R0-T026", selected["IBKR_ISA_purchase_status"].eq("NOT_CHECKED").all(), "public eligibility becomes IBKR ISA confirmation", "All ISA purchase statuses remain NOT_CHECKED")
    add_test("A3R0-T027", public_eligibility.loc[public_eligibility["LSE_current_status"].eq("CONFIRMED") & public_eligibility["isa_eligibility"].eq("NOT_DETERMINED"), "public_ISA_rules_status"].eq("UNCERTAIN").all(), "ISA inferred only from LSE listing", "Undetermined A0 ISA evidence remains uncertain")
    add_test("A3R0-T028", theme_audit["deepvue_controls_competition"].eq("NO").all(), "DeepVue controls competition", "DeepVue is descriptive only")
    add_test("A3R0-T029", parent_child["labelled_duplicate_due_only_to_overlap"].eq("NO").all(), "parent/child collapsed as duplicate", "All relationships remain economic hierarchy")
    add_test("A3R0-T030", global_benchmark.loc[global_benchmark["global_benchmark_family_id"].eq("GLOBAL_DEVELOPED_WORLD"), "global_benchmark_A2_lineage_status"].eq("PASS").all(), "unvalidated global benchmark selected", "Global benchmark has clean A2 lineage")
    add_test("A3R0-T031", not missing_preferred, "research-ready family lacks preferred current line", f"Missing preferred={semicolon_join(missing_preferred)}")
    add_test("A3R0-T032", selected["economic_lineage_valid"].all(), "misclassified current line enters verification queue", "Every queued line passes A3R0 family-lineage filter")
    add_test("A3R0-T033", ibkr_queue["ISIN"].notna().all() and ibkr_queue["ISIN"].ne("").all(), "queue row lacks ISIN", "Every queue row has ISIN")
    add_test("A3R0-T034", role["warning"].eq(WARNING).all(), "current eligibility warning omitted", "Warning is present on all families")
    add_test("A3R0-T035", len(registry) == 4359, "targeted audit rebuilds registry", "Original 4,359-row registry was read without replacement")
    add_test("A3R0-T036", theme_audit["new_product_added_to_master"].eq("NO").all(), "internet product enters without full lineage", "No internet-discovered product added to master")
    add_test("A3R0-T037", not panel["proxy_flag"].astype(bool).any(), "proxy history enters admission", "A2 panel contains no proxy rows")
    add_test("A3R0-T038", duplicate_groups["economic_exposure_family_id"].nunique() == 99, "duplicate structure loses a family", "Duplicate groups cover all retained families")
    tests_df = pd.DataFrame(tests)

    unresolved_rows = [
        {
            "item_id": "A3R0-OPEN-001",
            "severity": "BLOCKING",
            "category": "A2_ECONOMIC_LINEAGE",
            "affected_count": 14,
            "affected_ids": semicolon_join(policy["material_A2_lineage_failures"].keys()),
            "issue": "Material family/implementation mismatches invalidate those canonical histories for rotation research",
            "required_action": "Repair A0A1 listing-family assignments and rebuild/validate the affected A2 canonical histories",
            "blocks_A3R1": "YES",
            "status": "OPEN",
        },
        {
            "item_id": "A3R0-OPEN-002",
            "severity": "HIGH",
            "category": "NO_USABLE_HISTORY",
            "affected_count": int(role["a2_lineage_validation_status"].eq("NO_USABLE_HISTORY").sum()),
            "affected_ids": semicolon_join(role.loc[role["a2_lineage_validation_status"].eq("NO_USABLE_HISTORY"), "economic_exposure_family_id"]),
            "issue": "Nine retained families still have no usable implementation history",
            "required_action": "Find properly evidenced live implementation data or keep them unavailable; do not splice proxies",
            "blocks_A3R1": "NO_FOR_OTHER_FAMILIES",
            "status": "OPEN",
        },
        {
            "item_id": "A3R0-OPEN-003",
            "severity": "BLOCKING",
            "category": "SECTOR_GRID",
            "affected_count": 1,
            "affected_ids": "POOL_GLOBAL_BROAD_SECTORS;POOL_EUROPE_BROAD_SECTORS;POOL_US_BROAD_SECTORS",
            "issue": "The conventional sector grid is incomplete and several Europe/global sector histories are mislabelled",
            "required_action": "Create corrected sector families/lineage from products already in the registry and rebuild A2 histories before a full sector tournament",
            "blocks_A3R1": "YES",
            "status": "OPEN",
        },
        {
            "item_id": "A3R0-OPEN-004",
            "severity": "MEDIUM",
            "category": "PUBLIC_DISCLOSURE",
            "affected_count": int(public_eligibility["UK_retail_disclosure_status"].ne("CURRENT_DISCLOSURE_CONFIRMED").sum()),
            "affected_ids": semicolon_join(public_eligibility.loc[public_eligibility["UK_retail_disclosure_status"].ne("CURRENT_DISCLOSURE_CONFIRMED"), "economic_exposure_family_id"]),
            "issue": "Current public retail disclosure remains unverified for many queued lines",
            "required_action": "Use issuer product summary/KID/KIID evidence under the 2026 CCI transition",
            "blocks_A3R1": "NO_RESEARCH_ONLY",
            "status": "OPEN",
        },
        {
            "item_id": "A3R0-OPEN-005",
            "severity": "MEDIUM",
            "category": "PUBLIC_ISA_RULES",
            "affected_count": int(public_eligibility["public_ISA_rules_status"].eq("UNCERTAIN").sum()),
            "affected_ids": semicolon_join(public_eligibility.loc[public_eligibility["public_ISA_rules_status"].eq("UNCERTAIN"), "economic_exposure_family_id"]),
            "issue": "Public ISA-rules status remains uncertain where A0A1 did not establish recognised-fund/security structure",
            "required_action": "Verify product recognition/structure under current HMRC rules; do not infer from LSE listing",
            "blocks_A3R1": "NO_RESEARCH_ONLY",
            "status": "OPEN",
        },
        {
            "item_id": "A3R0-OPEN-006",
            "severity": "MEDIUM",
            "category": "BROKER",
            "affected_count": len(ibkr_queue),
            "affected_ids": "ALL_QUEUE_ROWS",
            "issue": "IBKR contract, LSE listing and quote checks have not been performed",
            "required_action": "Upload UKACTIVE_A3R0_CHATGPT_IBKR_VERIFICATION_QUEUE.csv for a read-only ChatGPT/IBKR verification pass",
            "blocks_A3R1": "NO_RESEARCH_ONLY",
            "status": "OPEN",
        },
        {
            "item_id": "A3R0-OPEN-007",
            "severity": "LOW",
            "category": "OVERLAP",
            "affected_count": int(overlaps["overlap_cluster_id"].nunique()),
            "affected_ids": semicolon_join(overlaps["overlap_cluster_id"]),
            "issue": "Overlap clusters are economic classifications; exact holdings-overlap percentages are not yet measured",
            "required_action": "Collect point-in-time holdings only if later concentration research requires it",
            "blocks_A3R1": "NO",
            "status": "OPEN",
        },
        {
            "item_id": "A3R0-OPEN-008",
            "severity": "MEDIUM",
            "category": "THEME_COVERAGE",
            "affected_count": int(theme_audit["coverage_outcome"].ne("COVERED_BY_EXISTING_FAMILY").sum()),
            "affected_ids": semicolon_join(theme_audit.loc[theme_audit["coverage_outcome"].ne("COVERED_BY_EXISTING_FAMILY"), "audit_label"]),
            "issue": "Several DeepVue/theme/sector labels are absent, structurally unsuitable, unlineaged, or lack usable history",
            "required_action": "Resolve only economically distinct gaps; do not add products solely to mirror labels",
            "blocks_A3R1": "NO_FOR_CLEAN_EXISTING_POOLS",
            "status": "OPEN",
        },
    ]
    unresolved = pd.DataFrame(unresolved_rows)

    test_failures = tests_df.loc[tests_df["status"].eq("FAIL")]
    blocking_unresolved = unresolved.loc[unresolved["blocks_A3R1"].eq("YES")]
    decision = "UKACTIVE_A3R0_FAIL" if not blocking_unresolved.empty or not test_failures.empty else ("UKACTIVE_A3R0_PASS_WITH_OPEN_ITEMS" if len(unresolved) else "UKACTIVE_A3R0_PASS")
    a3r1_ready = False if decision == "UKACTIVE_A3R0_FAIL" else True

    metadata = {
        "stage_id": STAGE_ID,
        "run_id": RUN_ID,
        "policy_id": policy["policy_id"],
        "warning": WARNING,
    }
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R0_ROTATION_ROLE_MASTER.csv", role)
    write_parquet(PROGRAMME_ROOT / "UKACTIVE_A3R0_ROTATION_ROLE_MASTER.parquet", role, metadata)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R0_COMPETITION_POOLS.csv", pools)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R0_PARENT_CHILD_MAP.csv", parent_child)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R0_OVERLAP_CLUSTERS.csv", overlaps)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R0_GLOBAL_BENCHMARK_MAP.csv", global_benchmark)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R0_PARENT_BENCHMARK_MAP.csv", parent_benchmark)
    write_parquet(PROGRAMME_ROOT / "UKACTIVE_A3R0_DYNAMIC_SIGNAL_ELIGIBILITY.parquet", dynamic, metadata)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R0_DYNAMIC_SIGNAL_ELIGIBILITY.csv", dynamic)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R0_THEME_COVERAGE_AUDIT.csv", theme_audit)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R0_SELECTABLE_ECONOMIC_UNIVERSE.csv", selectable)
    write_parquet(PROGRAMME_ROOT / "UKACTIVE_A3R0_SELECTABLE_ECONOMIC_UNIVERSE.parquet", selectable, metadata)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R0_CURRENT_IMPLEMENTATION_LINES.csv", current_lines)
    write_parquet(PROGRAMME_ROOT / "UKACTIVE_A3R0_CURRENT_IMPLEMENTATION_LINES.parquet", current_lines, metadata)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R0_PUBLIC_UK_ELIGIBILITY.csv", public_eligibility)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R0_CHATGPT_IBKR_VERIFICATION_QUEUE.csv", ibkr_queue)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R0_CLASSIFICATION_CORRECTIONS.csv", corrections)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R0_AUTOMATED_TEST_RESULTS.csv", tests_df)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R0_UNRESOLVED_ITEMS.csv", unresolved)

    horizon_counts = {
        str(horizon): int(dynamic[f"eligible_{horizon}_session_research"].eq("YES").sum())
        for horizon in policy["dynamic_admission"]["signal_sessions"]
    }
    maturity_counts = Counter(role["research_maturity"])
    role_counts = Counter(role["primary_rotation_role"])
    intended_role_counts = Counter(role["intended_rotation_role"])
    pool_counts = Counter(role["primary_competition_pool_id"])
    preferred_count = int(selected["preferred_or_alternate"].eq("PREFERRED").sum())
    alternate_count = int(selected["preferred_or_alternate"].eq("ALTERNATE").sum())
    public_disclosure_confirmed = int(public_eligibility["UK_retail_disclosure_status"].eq("CURRENT_DISCLOSURE_CONFIRMED").sum())
    public_isa_eligible = int(public_eligibility["public_ISA_rules_status"].eq("RULES_ELIGIBLE").sum())
    public_uncertain = int(
        (
            public_eligibility["UK_retail_disclosure_status"].isin(["DISCLOSURE_NOT_FOUND", "UNCERTAIN"])
            | public_eligibility["public_ISA_rules_status"].eq("UNCERTAIN")
            | public_eligibility["LSE_current_status"].isin(["NOT_CONFIRMED", "CONFLICT"])
        ).sum()
    )
    coverage_gap_count = int(theme_audit["coverage_outcome"].ne("COVERED_BY_EXISTING_FAMILY").sum())
    exact_deepvue_gap_count = int(
        theme_audit.loc[theme_audit["audit_category_type"].eq("DEEPVUE_CONFIRMED_LABEL"), "coverage_outcome"].ne("COVERED_BY_EXISTING_FAMILY").sum()
    )

    scope_md = f"""# UKACTIVE-A3R0 — Scope and method

## Decision boundary

This stage validates and restructures the retained A0A1/A2 universe for later relative-strength rotation research. It does **not** run a strategy, calculate portfolio returns, optimise signals, choose holdings, or authorise A3R1.

All {len(role)} original `economic_exposure_family_id` values are retained without deletion or renumbering. Ticker, ISIN, share class and listing remain implementation identities only.

## Dynamic admission

The fixed 504-session A3 gate is removed. Each 21/42/63/126/252-session model receives its own earliest admission date after that many valid A2 observations. Invalid, stale, missing and proxy rows never count. A3R1 must still validate the complete inputs on every actual signal date; admission is not permission to fill gaps. Current eligibility is never back-projected.

Raw A2 observation count alone is insufficient: {len(policy['material_A2_lineage_failures'])} histories are blocked because their selected implementations do not match the economic family. The four histories below 504 observations were reconsidered; {int(role['recovered_by_dynamic_admission'].eq('YES').sum())} pass short-horizon admission and `US_AEROSPACE_DEFENCE` is blocked because its A2 history is global rather than US-specific.

## Research architecture

`ECONOMIC EXPOSURE FAMILY → ROTATION ROLE → COMPETITION POOL → FUTURE SIGNAL → SELECTED ECONOMIC EXPOSURE → CURRENT IMPLEMENTATION`.

DeepVue remains descriptive metadata only. Defensive assets and benchmark references do not enter the primary equity tournament. Parent/child overlap is not duplicate equivalence.

## Current public evidence

The current public layer preserves three separate states: LSE status, retail-disclosure status, and public ISA-rules status. During the FCA CCI transition a product summary, KID, KIID or another permitted disclosure route can be valid; the filename `KID` is not required. ISA status is carried from A0A1 evidence and current HMRC structural rules, never inferred from LSE listing. All IBKR fields remain `NOT_CHECKED`.

## Scientific result

The structure is generated, but the stage decision is `{decision}` because material A0A1/A2 economic-lineage defects prevent a clean full geography/sector/theme tournament. No A3R1 execution is authorised.

{WARNING}
"""
    (PROGRAMME_ROOT / "UKACTIVE_A3R0_SCOPE_AND_METHOD.md").write_text(scope_md, encoding="utf-8")

    gaps = theme_audit.loc[theme_audit["coverage_outcome"].ne("COVERED_BY_EXISTING_FAMILY")]
    gap_lines = "\n".join(
        f"- **{row.audit_category_type} / {row.audit_label}:** `{row.coverage_outcome}` — {row.assessment_notes}"
        for row in gaps.itertuples(index=False)
    )
    theme_gaps_md = f"""# UKACTIVE-A3R0 — Theme and category coverage gaps

The targeted audit began with the immutable 4,359-row A0A1 discovery registry. Wider public research was limited to genuine unresolved gaps and current rules. No new product or family was added to the authoritative master.

Non-covered or incomplete audit rows: **{len(gaps)}**. Exact confirmed DeepVue labels not cleanly covered: **{exact_deepvue_gap_count}**.

{gap_lines}

## Material registry classification findings

The registry already contains conventional Europe sector products such as energy, industrials, technology, materials, communication services and utilities, but several were assigned to `EUROPE_BROAD`. Conversely, several MSCI World sector products were assigned to Europe sector families. These are explicit corrections, not silent edits. See `UKACTIVE_A3R0_CLASSIFICATION_CORRECTIONS.csv`.

DeepVue labels do not create competition pools or new economic opportunities.
"""
    (PROGRAMME_ROOT / "UKACTIVE_A3R0_THEME_COVERAGE_GAPS.md").write_text(theme_gaps_md, encoding="utf-8")

    quality_md = f"""# UKACTIVE-A3R0 — Data quality report

## Outcome

Decision: **{decision}**.

- A0A1 families retained: {len(role)}.
- A2 families with raw usable implementation histories: {int(coverage['usable_history'].astype(str).str.lower().eq('true').sum())}.
- Material A2 family/implementation lineage failures found and blocked: {len(policy['material_A2_lineage_failures'])}.
- Families admitted after lineage control: {int(role['research_data_ready_flag'].eq('YES').sum())}.
- Proposed selectable non-benchmark families: {len(selectable)}.
- Shorter-than-504 histories recovered: {int(role['recovered_by_dynamic_admission'].eq('YES').sum())}.
- Families with no usable A2 history: {int(role['a2_lineage_validation_status'].eq('NO_USABLE_HISTORY').sum())}.
- Automated controls passed: {int(tests_df['status'].eq('PASS').sum())}; failed: {int(tests_df['status'].eq('FAIL').sum())}.

## Critical lineage findings

{chr(10).join(f'- `{family}` — {issue}' for family, issue in policy['material_A2_lineage_failures'].items())}

These rows are not dynamically admitted. The source A0A1/A2 artifacts remain immutable; the corrections ledger records the required repair.

## Dynamic eligibility

Eligible family counts by signal sessions: {json.dumps(horizon_counts, sort_keys=True)}. Dynamic dates count only valid observations and never use proxy data; later signal-date windows must independently remain valid.

## Public evidence and broker boundary

Queued public lines: {len(public_eligibility)}. Retail-disclosure confirmed: {public_disclosure_confirmed}. Public ISA-rules eligible: {public_isa_eligible}. Lines with at least one public uncertainty: {public_uncertain}. IBKR-confirmed lines: 0.

## Reproducibility

The programme directory is not a Git worktree. Exact executed source/config snapshots, hashes, input hashes, output hashes, package versions and command line are retained in the manifest and evidence directory. No strategy-performance output exists.

{WARNING}
"""
    (PROGRAMME_ROOT / "UKACTIVE_A3R0_DATA_QUALITY_REPORT.md").write_text(quality_md, encoding="utf-8")

    readiness_md = f"""# UKACTIVE-A3R0 — A3R1 readiness

## Status: NOT READY

The competition-map architecture, dynamic admission logic, parent/child hierarchy, overlap clusters, benchmark mappings and broker-verification queue are present. However, A3R1 is **not scientifically authorised**.

Blocking reasons:

1. {len(policy['material_A2_lineage_failures'])} A2 family histories contain material economic-identity or scope mismatches and are blocked.
2. The conventional sector grid is incomplete and key global/Europe sector histories are mislabelled.
3. An A0A1 lineage repair followed by a targeted A2 history rebuild is required before a full relative-strength rotation tournament.

The clean subsets may be described, but running A3R1 on them now would answer a narrower question than the authorised geography/sector/industry/theme hypothesis. Do not execute A3R1 automatically.

The universe is ready for a separate read-only ChatGPT/IBKR verification pass using `UKACTIVE_A3R0_CHATGPT_IBKR_VERIFICATION_QUEUE.csv`; broker verification does not cure historical lineage.
"""
    (PROGRAMME_ROOT / "UKACTIVE_A3R0_A3R1_READINESS_REPORT.md").write_text(readiness_md, encoding="utf-8")

    completed_at = utc_now()
    decision_payload = {
        "stage_id": STAGE_ID,
        "run_id": RUN_ID,
        "decision": decision,
        "total_economic_exposure_families_retained": len(role),
        "primary_rotation_role_counts": dict(sorted(role_counts.items())),
        "intended_rotation_role_counts": dict(sorted(intended_role_counts.items())),
        "primary_competition_pool_counts": dict(sorted(pool_counts.items())),
        "dynamic_eligible_family_counts": horizon_counts,
        "shorter_history_families_recovered": int(role["recovered_by_dynamic_admission"].eq("YES").sum()),
        "shorter_history_recovered_ids": role.loc[role["recovered_by_dynamic_admission"].eq("YES"), "economic_exposure_family_id"].tolist(),
        "research_maturity_counts": dict(sorted(maturity_counts.items())),
        "parent_child_relationship_count": len(parent_child),
        "overlap_cluster_count": int(overlaps["overlap_cluster_id"].nunique()),
        "theme_category_gap_count": coverage_gap_count,
        "exact_deepvue_gap_count": exact_deepvue_gap_count,
        "new_products_added": 0,
        "public_retail_disclosure_confirmed_line_count": public_disclosure_confirmed,
        "public_ISA_rules_eligible_line_count": public_isa_eligible,
        "public_eligibility_uncertain_line_count": public_uncertain,
        "preferred_implementation_line_count": preferred_count,
        "alternate_implementation_line_count": alternate_count,
        "broker_confirmed_count": 0,
        "material_A2_lineage_failure_count": len(policy["material_A2_lineage_failures"]),
        "material_A2_lineage_failure_ids": sorted(policy["material_A2_lineage_failures"]),
        "automated_tests": {
            "passed": int(tests_df["status"].eq("PASS").sum()),
            "failed": int(tests_df["status"].eq("FAIL").sum()),
        },
        "chatgpt_ibkr_verification_ready": True,
        "A3R1_scientifically_ready": a3r1_ready,
        "A3R1_authorised": False,
        "strategy_results_produced": False,
        "warning": WARNING,
    }
    write_json(PROGRAMME_ROOT / "UKACTIVE_A3R0_DECISION.json", decision_payload)

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    evidence_path = EVIDENCE_DIR / "UKACTIVE_A3R0_EVIDENCE_LEDGER.jsonl"
    with evidence_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in evidence_ledger:
            handle.write(json.dumps(record, default=json_default, sort_keys=True) + "\n")

    EXECUTED_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    for source in [HERE / "build_ukactive_a3r0.py", HERE / "ukactive_a3r0_core.py", CONFIG_PATH]:
        shutil.copy2(source, EXECUTED_SOURCE_DIR / source.name)

    output_paths = [PROGRAMME_ROOT / name for name in REQUIRED_OUTPUTS if name != "UKACTIVE_A3R0_MANIFEST.json"]
    output_paths += [
        PROGRAMME_ROOT / "UKACTIVE_A3R0_ROTATION_ROLE_MASTER.parquet",
        PROGRAMME_ROOT / "UKACTIVE_A3R0_DYNAMIC_SIGNAL_ELIGIBILITY.csv",
        PROGRAMME_ROOT / "UKACTIVE_A3R0_SELECTABLE_ECONOMIC_UNIVERSE.parquet",
        PROGRAMME_ROOT / "UKACTIVE_A3R0_CURRENT_IMPLEMENTATION_LINES.parquet",
        evidence_path,
    ]
    missing_outputs = [str(path) for path in output_paths if not path.exists()]
    if missing_outputs:
        raise AssertionError(f"Missing outputs before manifest: {missing_outputs}")

    input_hashes = {
        str(PROGRAMME_ROOT / name): sha256_file(PROGRAMME_ROOT / name)
        for name in INPUTS
        if (PROGRAMME_ROOT / name).exists()
    }
    source_hashes = {
        str(path): sha256_file(path)
        for path in [HERE / "build_ukactive_a3r0.py", HERE / "ukactive_a3r0_core.py", CONFIG_PATH]
    }
    output_hashes = {str(path): sha256_file(path) for path in sorted(set(output_paths))}
    manifest = {
        "programme_id": PROGRAMME_ID,
        "programme_root": str(PROGRAMME_ROOT),
        "stage_id": STAGE_ID,
        "run_id": RUN_ID,
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "decision": decision,
        "git": git_state(),
        "reproducibility_status": "PASS_COMPLETE_EXECUTED_SOURCE_SNAPSHOT_NON_GIT",
        "executed_command_line": [sys.executable, str(HERE / "build_ukactive_a3r0.py")],
        "input_hashes": input_hashes,
        "source_code_and_policy_hashes": source_hashes,
        "executed_source_snapshot_paths": [str(path) for path in sorted(EXECUTED_SOURCE_DIR.iterdir())],
        "executed_source_snapshot_hashes": {str(path): sha256_file(path) for path in sorted(EXECUTED_SOURCE_DIR.iterdir())},
        "output_hashes_excluding_manifest_itself": output_hashes,
        "source_urls": PUBLIC_SOURCES,
        "source_retrieval_timestamps": source_timestamps,
        "evidence_counts": {
            "A3R0_ledger_records": len(evidence_ledger),
            "A0A1_registry_records_used": len(registry),
            "classification_corrections": len(corrections),
            "public_implementation_lines": len(public_eligibility),
        },
        "broker_check_method": "NOT_CHECKED_QUEUE_CREATED_FOR_LATER_READ_ONLY_CHATGPT_IBKR_PASS",
        "package_versions": package_versions(),
        "policy": policy,
        "classification_rule_version": policy["classification_rule_version"],
        "competition_pool_rule_version": policy["competition_pool_rule_version"],
        "overlap_rule_version": policy["overlap_rule_version"],
        "benchmark_map_rule_version": policy["benchmark_map_rule_version"],
        "coverage_statistics": {
            "families_retained": len(role),
            "research_data_ready": int(role["research_data_ready_flag"].eq("YES").sum()),
            "selectable": len(selectable),
            "dynamic_eligible": horizon_counts,
            "maturity": dict(sorted(maturity_counts.items())),
            "material_lineage_failures": len(policy["material_A2_lineage_failures"]),
            "no_usable_history": int(role["a2_lineage_validation_status"].eq("NO_USABLE_HISTORY").sum()),
        },
        "automated_test_results": tests_df.to_dict("records"),
        "unresolved_items": unresolved.to_dict("records"),
        "required_outputs": REQUIRED_OUTPUTS,
        "strategy_results_produced": False,
        "A3R1_executed": False,
        "warning": WARNING,
    }
    write_json(PROGRAMME_ROOT / "UKACTIVE_A3R0_MANIFEST.json", manifest)

    print(json.dumps(decision_payload, indent=2, default=json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
