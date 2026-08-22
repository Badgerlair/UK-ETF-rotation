"""Build UKACTIVE-A2R economic-lineage remediation outputs.

This executable intentionally reuses the validated UKACTIVE-A2 return engine.  It
does not contain signal, strategy, portfolio, optimisation or performance code.
Original A0A1/A2/A3/A3R0 artifacts are read-only inputs and are never overwritten.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import subprocess
import sys
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests


PROGRAMME_ROOT = Path(r"D:\Codex\equity_quant_research_platform\research\directed\EDGE-UK-ACTIVE-ETF-SLEEVE-20260822-001")
CODE_DIR = PROGRAMME_ROOT / "code"
CONFIG_DIR = PROGRAMME_ROOT / "config"
EVIDENCE_DIR = PROGRAMME_ROOT / "evidence"
A2_SOURCE_ROOT = EVIDENCE_DIR / "sources" / "a2"
A2R_SOURCE_ROOT = EVIDENCE_DIR / "sources" / "a2r"
A2R_LEDGER = EVIDENCE_DIR / "UKACTIVE_A2R_EVIDENCE_LEDGER.jsonl"
POLICY_PATH = CONFIG_DIR / "UKACTIVE_A2R_POLICY_v1.json"
A2_POLICY_PATH = CONFIG_DIR / "UKACTIVE_A2_POLICY_v1.json"
A3R0_POLICY_PATH = CONFIG_DIR / "UKACTIVE_A3R0_POLICY_v1.json"

sys.path.insert(0, str(CODE_DIR))
import build_ukactive_a2 as a2  # noqa: E402
import build_ukactive_a3r0 as a3r0  # noqa: E402
from ukactive_a2r_core import (  # noqa: E402
    ALLOWED_OUTCOMES,
    WARNING,
    EconomicFingerprint,
    apply_semantic_floor_to_frame,
    canonical_json_hash,
    clean,
    earliest_valid_observation_date,
    fingerprint_from_row,
    history_hash,
    make_test_row,
    maturity_label,
    now_utc,
    parse_bool,
    semantic_match,
    semicolon,
    sha256_file,
    stable_id,
    synthetic_semantic_fixture_results,
    valid_mask,
)


RUN_ID = "UKACTIVE-A2R-20260822-001"
STAGE_ID = "UKACTIVE-A2R"
OBSERVATION_DATE = "2026-08-22"
HORIZONS = [21, 42, 63, 126, 252]


REQUIRED_OUTPUTS = [
    "UKACTIVE_A2R_SCOPE_AND_METHOD.md",
    "UKACTIVE_A2R_BLOCKING_FAMILY_DEFINITIONS.csv",
    "UKACTIVE_A2R_ECONOMIC_IDENTITY_FINGERPRINTS.csv",
    "UKACTIVE_A2R_EXISTING_LINEAGE_AUDIT.csv",
    "UKACTIVE_A2R_LINEAGE_CORRECTIONS.csv",
    "UKACTIVE_A2R_EUROPE_SECTOR_GRID_AUDIT.csv",
    "UKACTIVE_A2R_GLOBAL_SECTOR_GRID_AUDIT.csv",
    "UKACTIVE_A2R_NEW_PRODUCT_CANDIDATES.csv",
    "UKACTIVE_A2R_CORRECTED_IMPLEMENTATION_HISTORY.parquet",
    "UKACTIVE_A2R_CORRECTED_TOTAL_RETURN_PANEL_GBP.parquet",
    "UKACTIVE_A2R_DYNAMIC_SIGNAL_ELIGIBILITY.parquet",
    "UKACTIVE_A2R_MANUAL_VALIDATION_CASES.md",
    "UKACTIVE_A2R_AUTOMATED_TEST_RESULTS.csv",
    "UKACTIVE_A2R_SEMANTIC_LINEAGE_TEST_RESULTS.csv",
    "UKACTIVE_A2R_BEFORE_AFTER_HISTORY_AUDIT.csv",
    "UKACTIVE_A2R_DATA_QUALITY_REPORT.md",
    "UKACTIVE_A2R_UNRESOLVED_ITEMS.csv",
    "UKACTIVE_A2R_A3R0_REGENERATION_REPORT.md",
    "UKACTIVE_A2R_A3R1_READINESS_REPORT.md",
    "UKACTIVE_A2R_DECISION.json",
    "UKACTIVE_A2R_MANIFEST.json",
]


OFFICIAL_SOURCES: dict[str, str] = {
    "HMRC_ISA_QUALIFYING_INVESTMENTS": "https://www.gov.uk/guidance/stocks-and-shares-investments-for-isa-managers",
    "FCA_CCI_TRANSITION": "https://handbook.fca.org.uk/handbook/disctp2",
    "UBS_AUSTRALIA_DIST": "https://www.ubs.com/uk/en/assetmanagement/funds/etf/ie00bd4ty345-ubs-msci-australia-ucits-etf-aud-dis-pd001.html",
    "HSBC_MSCI_CHINA_FACTSHEET": "https://www.assetmanagement.hsbc.co.uk/api/v1/download/document/ie00b44t3h88/gb/en/factsheet",
    "HSBC_MSCI_CHINA_SUPPLEMENT": "https://www.assetmanagement.hsbc.co.uk/api/v1/download/document/ie00b44t3h88/gb/en/supplement",
    "SPDR_EUROPE_ENERGY": "https://www.ssga.com/ie/en_gb/institutional/etfs/state-street-spdr-msci-europe-energy-ucits-etf-stn-fp",
    "SPDR_EUROPE_FINANCIALS": "https://www.ssga.com/ie/en_gb/institutional/etfs/state-street-spdr-msci-europe-financials-ucits-etf-stz-fp",
    "SPDR_EUROPE_HEALTHCARE_FACTSHEET": "https://www.ssga.com/library-content/products/factsheets/etfs/emea/factsheet-emea-en_gb-stw-fp.pdf",
    "SPDR_EUROPE_INDUSTRIALS": "https://www.ssga.com/dk/en_gb/institutional/etfs/state-street-spdr-msci-europe-industrials-ucits-etf-stq-fp",
    "SPDR_EUROPE_MATERIALS": "https://www.ssga.com/nl/nl/institutional/etfs/funds/spdr-msci-europe-materials-ucits-etf-stp-fp",
    "SPDR_EUROPE_TECHNOLOGY_FACTSHEET": "https://www.ssga.com/lu/en_gb/intermediary/library-content/products/factsheets/etfs/emea/factsheet-emea-en_gb-stk-fp.pdf",
    "SPDR_EUROPE_UTILITIES": "https://www.ssga.com/uk/en_gb/institutional/etfs/state-street-spdr-msci-europe-utilities-ucits-etf-stu-fp",
    "SPDR_EUROPE_CONSUMER_DISCRETIONARY": "https://www.ssga.com/ie/en_gb/institutional/etfs/state-street-spdr-msci-europe-consumer-discretionary-ucits-etf-str-fp",
    "SPDR_EUROPE_COMMUNICATION_SERVICES": "https://www.ssga.com/ie/en_gb/institutional/etfs/state-street-spdr-msci-europe-communication-services-ucits-etf-stt-fp",
    "XTRACKERS_EUROPE_REAL_ESTATE_FACTSHEET": "https://etf.dws.com/download/asset/7ba98091-cdb4-47f0-b2f3-1d3173114b13",
    "SPDR_WORLD_HEALTHCARE": "https://www.ssga.com/uk/en_gb/institutional/etfs/state-street-spdr-msci-world-health-care-ucits-etf-whea-na",
    "SPDR_WORLD_TECHNOLOGY": "https://www.ssga.com/uk/en_gb/institutional/etfs/state-street-spdr-msci-world-technology-ucits-etf-wtch-na",
    "SPDR_WORLD_CONSUMER_DISCRETIONARY": "https://www.ssga.com/se/en_gb/institutional/etfs/state-street-spdr-msci-world-consumer-discretionary-ucits-etf-wcod-na",
    "SPDR_WORLD_CONSUMER_STAPLES": "https://www.ssga.com/uk/en_gb/institutional/etfs/state-street-spdr-msci-world-consumer-staples-ucits-etf-wcos-na",
    "SPDR_WORLD_COMMUNICATION_SERVICES": "https://www.ssga.com/uk/en_gb/institutional/etfs/state-street-spdr-msci-world-communication-services-ucits-etf-wtel-na",
    "ISHARES_GLOBAL_INFRASTRUCTURE": "https://www.ishares.com/uk/individual/en/products/251809/ishares-global-infrastructure-ucits-etf",
    "ISHARES_GLOBAL_INFRASTRUCTURE_FACTSHEET": "https://www.ishares.com/uk/professional/en/literature/fact-sheet/infr-ishares-global-infrastructure-ucits-etf-fund-fact-sheet-en-gb.pdf",
    "HANETF_US_DEFENCE": "https://hanetf.com/fund/gijo-future-of-us-defence-etf/",
    "LSE_US_DEFENCE": "https://www.londonstockexchange.com/stock/GIJO/hanetf",
    "HANETF_OLD_METAVERSE_SUPPLEMENT": "https://hanetf.com/wp-content/assets/13.%20Supplement%20-%20ETC%20Group%20Global%20Metaverse%20UCITS%20ETF%20-%2016%20April%202024.pdf",
}


FAMILY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "AUSTRALIA": dict(name="Broad Australian equities", asset="EQUITY", geography="AUSTRALIA", scope="COUNTRY", sector="BROAD_MARKET", industry="NOT_APPLICABLE", theme="NOT_APPLICABLE", breadth="BROAD_COUNTRY", hedge="UNHEDGED", objective="MSCI_AUSTRALIA", allowed=[], role="COUNTRY_ROTATION", parent="GLOBAL_DEVELOPED_WORLD", pool="POOL_COUNTRY_EQUITY", outcome="CORRECTED_IMPLEMENTATION_HISTORY"),
    "CHINA_BROAD": dict(name="Broad China equities", asset="EQUITY", geography="CHINA", scope="COUNTRY", sector="BROAD_MARKET", industry="NOT_APPLICABLE", theme="NOT_APPLICABLE", breadth="BROAD_COUNTRY", hedge="UNHEDGED", objective="MSCI_CHINA", allowed=[], role="COUNTRY_ROTATION", parent="EMERGING_MARKETS", pool="POOL_COUNTRY_EQUITY", outcome="CORRECTED_IMPLEMENTATION_HISTORY"),
    "EUROPE_ENERGY": dict(name="Broad Europe energy sector", asset="EQUITY", geography="EUROPE", scope="REGION", sector="ENERGY", industry="BROAD_SECTOR", theme="NOT_APPLICABLE", breadth="BROAD_SECTOR", hedge="UNHEDGED", objective="MSCI_EUROPE_ENERGY_35_20_CAPPED", allowed=["MSCI_EUROPE_ENERGY"], role="SECTOR_ROTATION", parent="EUROPE_BROAD", pool="POOL_BROAD_SECTOR", outcome="CORRECTED_IMPLEMENTATION_HISTORY"),
    "EUROPE_FINANCIALS": dict(name="Broad Europe financials sector", asset="EQUITY", geography="EUROPE", scope="REGION", sector="FINANCIALS", industry="BROAD_SECTOR", theme="NOT_APPLICABLE", breadth="BROAD_SECTOR", hedge="UNHEDGED", objective="MSCI_EUROPE_FINANCIALS_35_20_CAPPED", allowed=["MSCI_EUROPE_FINANCIALS"], role="SECTOR_ROTATION", parent="EUROPE_BROAD", pool="POOL_BROAD_SECTOR", outcome="CORRECTED_IMPLEMENTATION_HISTORY"),
    "EUROPE_HEALTHCARE": dict(name="Broad Europe healthcare sector", asset="EQUITY", geography="EUROPE", scope="REGION", sector="HEALTHCARE", industry="BROAD_SECTOR", theme="NOT_APPLICABLE", breadth="BROAD_SECTOR", hedge="UNHEDGED", objective="MSCI_EUROPE_HEALTH_CARE_35_20_CAPPED", allowed=["MSCI_EUROPE_HEALTH_CARE"], role="SECTOR_ROTATION", parent="EUROPE_BROAD", pool="POOL_BROAD_SECTOR", outcome="CORRECTED_IMPLEMENTATION_HISTORY"),
    "EUROPE_INDUSTRIALS": dict(name="Broad Europe industrials sector", asset="EQUITY", geography="EUROPE", scope="REGION", sector="INDUSTRIALS", industry="BROAD_SECTOR", theme="NOT_APPLICABLE", breadth="BROAD_SECTOR", hedge="UNHEDGED", objective="MSCI_EUROPE_INDUSTRIALS_35_20_CAPPED", allowed=["MSCI_EUROPE_INDUSTRIALS"], role="SECTOR_ROTATION", parent="EUROPE_BROAD", pool="POOL_BROAD_SECTOR", outcome="CORRECTED_IMPLEMENTATION_HISTORY"),
    "EUROPE_MATERIALS": dict(name="Broad Europe materials sector", asset="EQUITY", geography="EUROPE", scope="REGION", sector="MATERIALS", industry="BROAD_SECTOR", theme="NOT_APPLICABLE", breadth="BROAD_SECTOR", hedge="UNHEDGED", objective="MSCI_EUROPE_MATERIALS_35_20_CAPPED", allowed=["MSCI_EUROPE_MATERIALS"], role="SECTOR_ROTATION", parent="EUROPE_BROAD", pool="POOL_BROAD_SECTOR", outcome="CORRECTED_IMPLEMENTATION_HISTORY"),
    "EUROPE_TECHNOLOGY": dict(name="Broad Europe technology sector", asset="EQUITY", geography="EUROPE", scope="REGION", sector="TECHNOLOGY", industry="BROAD_SECTOR", theme="NOT_APPLICABLE", breadth="BROAD_SECTOR", hedge="UNHEDGED", objective="MSCI_EUROPE_INFORMATION_TECHNOLOGY_35_20_CAPPED", allowed=["MSCI_EUROPE_INFORMATION_TECHNOLOGY"], role="SECTOR_ROTATION", parent="EUROPE_BROAD", pool="POOL_BROAD_SECTOR", outcome="CORRECTED_IMPLEMENTATION_HISTORY"),
    "EUROPE_UTILITIES": dict(name="Broad Europe utilities sector", asset="EQUITY", geography="EUROPE", scope="REGION", sector="UTILITIES", industry="BROAD_SECTOR", theme="NOT_APPLICABLE", breadth="BROAD_SECTOR", hedge="UNHEDGED", objective="MSCI_EUROPE_UTILITIES_35_20_CAPPED", allowed=["MSCI_EUROPE_UTILITIES"], role="SECTOR_ROTATION", parent="EUROPE_BROAD", pool="POOL_BROAD_SECTOR", outcome="CORRECTED_IMPLEMENTATION_HISTORY"),
    "GLOBAL_BANKS": dict(name="Global banking industry", asset="EQUITY", geography="GLOBAL", scope="GLOBAL", sector="FINANCIALS", industry="BANKS", theme="NOT_APPLICABLE", breadth="INDUSTRY", hedge="UNHEDGED", objective="GLOBAL_DEVELOPED_BANKS", allowed=[], role="INDUSTRY_ROTATION", parent="GLOBAL_FINANCIALS", pool="POOL_INDUSTRY_SUBSECTOR", outcome="NO_VALID_IMPLEMENTATION_HISTORY"),
    "GLOBAL_HEALTHCARE": dict(name="Broad global healthcare sector", asset="EQUITY", geography="GLOBAL", scope="GLOBAL", sector="HEALTHCARE", industry="BROAD_SECTOR", theme="NOT_APPLICABLE", breadth="BROAD_SECTOR", hedge="UNHEDGED", objective="MSCI_WORLD_HEALTH_CARE_35_20_CAPPED", allowed=["MSCI_WORLD_HEALTH_CARE"], role="SECTOR_ROTATION", parent="GLOBAL_DEVELOPED_WORLD", pool="POOL_BROAD_SECTOR", outcome="CORRECTED_IMPLEMENTATION_HISTORY"),
    "GLOBAL_INFRASTRUCTURE": dict(name="Global listed infrastructure", asset="INFRASTRUCTURE", geography="GLOBAL", scope="GLOBAL", sector="INDUSTRIALS", industry="INFRASTRUCTURE", theme="INFRASTRUCTURE", breadth="LISTED_INFRASTRUCTURE", hedge="UNHEDGED", objective="FTSE_GLOBAL_CORE_INFRASTRUCTURE", allowed=["MACQUARIE_GLOBAL_INFRASTRUCTURE_100"], role="THEME_ROTATION", parent="GLOBAL_INDUSTRIALS", pool="POOL_THEME_EQUITY", outcome="CORRECTED_IMPLEMENTATION_HISTORY"),
    "GLOBAL_TECHNOLOGY": dict(name="Broad global technology sector", asset="EQUITY", geography="GLOBAL", scope="GLOBAL", sector="TECHNOLOGY", industry="BROAD_SECTOR", theme="NOT_APPLICABLE", breadth="BROAD_SECTOR", hedge="UNHEDGED", objective="MSCI_WORLD_INFORMATION_TECHNOLOGY_35_20_CAPPED", allowed=["MSCI_WORLD_INFORMATION_TECHNOLOGY"], role="SECTOR_ROTATION", parent="GLOBAL_DEVELOPED_WORLD", pool="POOL_BROAD_SECTOR", outcome="CORRECTED_IMPLEMENTATION_HISTORY"),
    "US_AEROSPACE_DEFENCE": dict(name="United States aerospace and defence", asset="EQUITY", geography="UNITED_STATES", scope="COUNTRY", sector="INDUSTRIALS", industry="AEROSPACE_AND_DEFENCE", theme="DEFENCE", breadth="INDUSTRY", hedge="UNHEDGED", objective="VETTAFI_AMERICAN_FUTURE_OF_DEFENCE", allowed=[], role="INDUSTRY_ROTATION", parent="GLOBAL_INDUSTRIALS", pool="POOL_INDUSTRY_SUBSECTOR", outcome="VALID_ONLY_FROM_LATER_DATE"),
}


NEW_FAMILY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "EUROPE_CONSUMER_DISCRETIONARY": dict(name="Broad Europe consumer discretionary sector", geography="EUROPE", scope="REGION", sector="CONSUMER_DISCRETIONARY", industry="BROAD_SECTOR", objective="MSCI_EUROPE_CONSUMER_DISCRETIONARY_35_20_CAPPED", parent="EUROPE_BROAD"),
    "EUROPE_COMMUNICATION_SERVICES": dict(name="Broad Europe communication services sector", geography="EUROPE", scope="REGION", sector="COMMUNICATION_SERVICES", industry="BROAD_SECTOR", objective="MSCI_EUROPE_COMMUNICATION_SERVICES_35_20_CAPPED", parent="EUROPE_BROAD"),
    "EUROPE_REAL_ESTATE": dict(name="Europe listed real estate", geography="EUROPE", scope="REGION", sector="REAL_ESTATE", industry="REITS_AND_PROPERTY", objective="FTSE_EPRA_NAREIT_DEVELOPED_EUROPE", parent="EUROPE_BROAD", asset="PROPERTY", sub_asset="LISTED_REAL_ESTATE_EQUITY"),
    "GLOBAL_CONSUMER_DISCRETIONARY": dict(name="Broad global consumer discretionary sector", geography="GLOBAL", scope="GLOBAL", sector="CONSUMER_DISCRETIONARY", industry="BROAD_SECTOR", objective="MSCI_WORLD_CONSUMER_DISCRETIONARY_35_20_CAPPED", parent="GLOBAL_DEVELOPED_WORLD"),
    "GLOBAL_CONSUMER_STAPLES": dict(name="Broad global consumer staples sector", geography="GLOBAL", scope="GLOBAL", sector="CONSUMER_STAPLES", industry="BROAD_SECTOR", objective="MSCI_WORLD_CONSUMER_STAPLES_35_20_CAPPED", parent="GLOBAL_DEVELOPED_WORLD"),
    "GLOBAL_COMMUNICATION_SERVICES": dict(name="Broad global communication services sector", geography="GLOBAL", scope="GLOBAL", sector="COMMUNICATION_SERVICES", industry="BROAD_SECTOR", objective="MSCI_WORLD_COMMUNICATION_SERVICES_35_20_CAPPED", parent="GLOBAL_DEVELOPED_WORLD"),
}


# Exact implementations already present in A2 that are retained or reassigned.
EXISTING_ROUTE_SELECTIONS: dict[str, list[str]] = {
    "AUSTRALIA": ["AUAD"],
    "CHINA_BROAD": ["HCHS"],
    "EUROPE_FINANCIALS": ["FNCE", "FNCL"],
    "EUROPE_HEALTHCARE": ["HEAE", "HLTH"],
    "GLOBAL_HEALTHCARE": ["HLTW", "HLTG", "HEAW", "WHEA"],
    "GLOBAL_TECHNOLOGY": ["TECW", "WTEC"],
}


def route_spec(
    family: str,
    isin: str,
    ticker: str,
    eodhd_code: str,
    price_unit: str,
    listing_currency: str,
    provider: str,
    legal_name: str,
    objective: str,
    geography: str,
    sector_or_industry: str,
    breadth: str,
    inception: str,
    listing_inception: str,
    accdist: str = "ACCUMULATING",
    source_key: str = "NOT_AVAILABLE",
    share_class_token: str | None = None,
    registry_present: bool = True,
    semantic_valid_from: str = "NOT_APPLICABLE",
    public_isa: str = "RULES_ELIGIBLE",
) -> dict[str, Any]:
    return {
        "economic_exposure_family_id": family,
        "isin": isin,
        "ticker": ticker,
        "eodhd_code": eodhd_code,
        "effective_price_unit": price_unit,
        "effective_listing_currency": listing_currency,
        "provider_issuer": provider,
        "legal_fund_name": legal_name,
        "actual_index_or_objective": objective,
        "actual_geography": geography,
        "actual_sector_or_industry": sector_or_industry,
        "actual_breadth_level": breadth,
        "actual_hedge_status": "UNHEDGED",
        "fund_inception_date": inception,
        "share_class_inception_date": inception,
        "listing_inception_date": listing_inception,
        "accumulating_distributing": accdist,
        "source_key": source_key,
        "share_class_token": share_class_token or isin,
        "registry_present": registry_present,
        "semantic_valid_from": semantic_valid_from,
        "public_isa_rules_status": public_isa,
    }


NEW_ROUTE_SPECS: list[dict[str, Any]] = [
    route_spec("CHINA_BROAD", "IE00B44T3H88", "HMCH", "HMCH", "GBX", "GBP", "HSBC", "HSBC MSCI China UCITS ETF USD Dist", "MSCI_CHINA", "CHINA", "BROAD_MARKET", "BROAD_COUNTRY", "2011-01-26", "2011-01-28", "DISTRIBUTING", "HSBC_MSCI_CHINA_FACTSHEET"),
    route_spec("CHINA_BROAD", "IE00B44T3H88", "HMCD", "HMCD", "USD", "USD", "HSBC", "HSBC MSCI China UCITS ETF USD Dist", "MSCI_CHINA", "CHINA", "BROAD_MARKET", "BROAD_COUNTRY", "2011-01-26", "2011-01-28", "DISTRIBUTING", "HSBC_MSCI_CHINA_FACTSHEET"),
    route_spec("EUROPE_ENERGY", "IE00BKWQ0F09", "ENGE", "ENGE", "GBP", "GBP", "STATE_STREET", "State Street SPDR MSCI Europe Energy UCITS ETF", "MSCI_EUROPE_ENERGY_35_20_CAPPED", "EUROPE", "ENERGY", "BROAD_SECTOR", "2014-12-05", "2014-12-09", source_key="SPDR_EUROPE_ENERGY"),
    route_spec("EUROPE_ENERGY", "IE00BKWQ0F09", "ENGY", "ENGY", "EUR", "EUR", "STATE_STREET", "State Street SPDR MSCI Europe Energy UCITS ETF", "MSCI_EUROPE_ENERGY_35_20_CAPPED", "EUROPE", "ENERGY", "BROAD_SECTOR", "2014-12-05", "2014-12-09", source_key="SPDR_EUROPE_ENERGY"),
    route_spec("EUROPE_INDUSTRIALS", "IE00BKWQ0J47", "NDUS", "NDUS", "EUR", "EUR", "STATE_STREET", "State Street SPDR MSCI Europe Industrials UCITS ETF", "MSCI_EUROPE_INDUSTRIALS_35_20_CAPPED", "EUROPE", "INDUSTRIALS", "BROAD_SECTOR", "2014-12-05", "2014-12-09", source_key="SPDR_EUROPE_INDUSTRIALS"),
    route_spec("EUROPE_MATERIALS", "IE00BKWQ0L68", "MTRL", "MTRL", "EUR", "EUR", "STATE_STREET", "State Street SPDR MSCI Europe Materials UCITS ETF", "MSCI_EUROPE_MATERIALS_35_20_CAPPED", "EUROPE", "MATERIALS", "BROAD_SECTOR", "2014-12-05", "2014-12-09", source_key="SPDR_EUROPE_MATERIALS"),
    route_spec("EUROPE_TECHNOLOGY", "IE00BKWQ0K51", "ITEC", "ITEC", "EUR", "EUR", "STATE_STREET", "State Street SPDR MSCI Europe Technology UCITS ETF", "MSCI_EUROPE_INFORMATION_TECHNOLOGY_35_20_CAPPED", "EUROPE", "TECHNOLOGY", "BROAD_SECTOR", "2014-12-05", "2014-12-09", source_key="SPDR_EUROPE_TECHNOLOGY_FACTSHEET"),
    route_spec("EUROPE_UTILITIES", "IE00BKWQ0P07", "UTIL", "UTIL", "EUR", "EUR", "STATE_STREET", "State Street SPDR MSCI Europe Utilities UCITS ETF", "MSCI_EUROPE_UTILITIES_35_20_CAPPED", "EUROPE", "UTILITIES", "BROAD_SECTOR", "2014-12-05", "2014-12-09", source_key="SPDR_EUROPE_UTILITIES"),
    route_spec("EUROPE_CONSUMER_DISCRETIONARY", "IE00BKWQ0C77", "CDCE", "CDCE", "GBP", "GBP", "STATE_STREET", "State Street SPDR MSCI Europe Consumer Discretionary UCITS ETF", "MSCI_EUROPE_CONSUMER_DISCRETIONARY_35_20_CAPPED", "EUROPE", "CONSUMER_DISCRETIONARY", "BROAD_SECTOR", "2014-12-05", "2022-04-04", source_key="SPDR_EUROPE_CONSUMER_DISCRETIONARY"),
    route_spec("EUROPE_CONSUMER_DISCRETIONARY", "IE00BKWQ0C77", "CDIS", "CDIS", "EUR", "EUR", "STATE_STREET", "State Street SPDR MSCI Europe Consumer Discretionary UCITS ETF", "MSCI_EUROPE_CONSUMER_DISCRETIONARY_35_20_CAPPED", "EUROPE", "CONSUMER_DISCRETIONARY", "BROAD_SECTOR", "2014-12-05", "2014-12-09", source_key="SPDR_EUROPE_CONSUMER_DISCRETIONARY"),
    route_spec("EUROPE_COMMUNICATION_SERVICES", "IE00BKWQ0N82", "TELE", "TELE", "EUR", "EUR", "STATE_STREET", "State Street SPDR MSCI Europe Communication Services UCITS ETF", "MSCI_EUROPE_COMMUNICATION_SERVICES_35_20_CAPPED", "EUROPE", "COMMUNICATION_SERVICES", "BROAD_SECTOR", "2014-12-05", "2014-12-09", source_key="SPDR_EUROPE_COMMUNICATION_SERVICES"),
    route_spec("EUROPE_REAL_ESTATE", "LU0489337690", "XDER", "XDER", "GBX", "GBP", "XTRACKERS", "Xtrackers FTSE Developed Europe Real Estate UCITS ETF 1C", "FTSE_EPRA_NAREIT_DEVELOPED_EUROPE", "EUROPE", "REAL_ESTATE", "BROAD_SECTOR", "2010-03-25", "2010-03-25", source_key="XTRACKERS_EUROPE_REAL_ESTATE_FACTSHEET"),
    route_spec("GLOBAL_CONSUMER_DISCRETIONARY", "IE00BYTRR640", "WCOD", "WCOD", "USD", "USD", "STATE_STREET", "State Street SPDR MSCI World Consumer Discretionary UCITS ETF", "MSCI_WORLD_CONSUMER_DISCRETIONARY_35_20_CAPPED", "GLOBAL", "CONSUMER_DISCRETIONARY", "BROAD_SECTOR", "2016-04-29", "2016-05-04", source_key="SPDR_WORLD_CONSUMER_DISCRETIONARY"),
    route_spec("GLOBAL_CONSUMER_STAPLES", "IE00BYTRR756", "WCOS", "WCOS", "USD", "USD", "STATE_STREET", "State Street SPDR MSCI World Consumer Staples UCITS ETF", "MSCI_WORLD_CONSUMER_STAPLES_35_20_CAPPED", "GLOBAL", "CONSUMER_STAPLES", "BROAD_SECTOR", "2016-04-29", "2016-05-04", source_key="SPDR_WORLD_CONSUMER_STAPLES"),
    route_spec("GLOBAL_COMMUNICATION_SERVICES", "IE00BYTRRG40", "WTEL", "WTEL", "USD", "USD", "STATE_STREET", "State Street SPDR MSCI World Communication Services UCITS ETF", "MSCI_WORLD_COMMUNICATION_SERVICES_35_20_CAPPED", "GLOBAL", "COMMUNICATION_SERVICES", "BROAD_SECTOR", "2016-04-29", "2016-05-04", source_key="SPDR_WORLD_COMMUNICATION_SERVICES"),
    route_spec("GLOBAL_INFRASTRUCTURE", "IE00B1FZS467", "INFR", "INFR", "GBX", "GBP", "ISHARES", "iShares Global Infrastructure UCITS ETF USD Dist", "FTSE_GLOBAL_CORE_INFRASTRUCTURE", "GLOBAL", "INFRASTRUCTURE", "LISTED_INFRASTRUCTURE", "2006-10-20", "2006-10-20", "DISTRIBUTING", "ISHARES_GLOBAL_INFRASTRUCTURE", registry_present=False),
    route_spec("GLOBAL_INFRASTRUCTURE", "IE00B1FZS467", "IDIN", "IDIN", "USD", "USD", "ISHARES", "iShares Global Infrastructure UCITS ETF USD Dist", "FTSE_GLOBAL_CORE_INFRASTRUCTURE", "GLOBAL", "INFRASTRUCTURE", "LISTED_INFRASTRUCTURE", "2006-10-20", "2006-10-27", "DISTRIBUTING", "ISHARES_GLOBAL_INFRASTRUCTURE", registry_present=False),
    route_spec("US_AEROSPACE_DEFENCE", "IE000KDY10O3", "SEAL", "METP", "GBX", "GBP", "HANETF", "Future of US Defence UCITS ETF", "VETTAFI_AMERICAN_FUTURE_OF_DEFENCE", "UNITED_STATES", "AEROSPACE_AND_DEFENCE", "INDUSTRY", "2022-03-15", "2022-03-17", "ACCUMULATING", "HANETF_US_DEFENCE", semantic_valid_from="2026-07-16"),
    route_spec("US_AEROSPACE_DEFENCE", "IE000KDY10O3", "GIJO", "METR", "USD", "USD", "HANETF", "Future of US Defence UCITS ETF", "VETTAFI_AMERICAN_FUTURE_OF_DEFENCE", "UNITED_STATES", "AEROSPACE_AND_DEFENCE", "INDUSTRY", "2022-03-15", "2022-03-17", "ACCUMULATING", "HANETF_US_DEFENCE", semantic_valid_from="2026-07-16"),
]


OLD_ACTUAL_FINGERPRINTS: dict[str, EconomicFingerprint] = {
    "AUSTRALIA": EconomicFingerprint("AUSTRALIA", "BROAD_MARKET", "MSCI_AUSTRALIA", "HEDGED_GBP", "BROAD_COUNTRY"),
    "CHINA_BROAD": EconomicFingerprint("CHINA", "A_SHARES", "MSCI_CHINA_A", "UNHEDGED", "NARROW_COUNTRY_SEGMENT"),
    "EUROPE_ENERGY": EconomicFingerprint("GLOBAL", "ENERGY", "MSCI_WORLD_ENERGY", "UNHEDGED", "BROAD_SECTOR"),
    "EUROPE_FINANCIALS": EconomicFingerprint("GLOBAL", "FINANCIALS", "MSCI_WORLD_FINANCIALS", "UNHEDGED", "BROAD_SECTOR"),
    "EUROPE_HEALTHCARE": EconomicFingerprint("GLOBAL", "HEALTHCARE", "MSCI_WORLD_HEALTH_CARE", "UNHEDGED", "BROAD_SECTOR"),
    "EUROPE_INDUSTRIALS": EconomicFingerprint("GLOBAL", "INDUSTRIALS", "MSCI_WORLD_INDUSTRIALS", "UNHEDGED", "BROAD_SECTOR"),
    "EUROPE_MATERIALS": EconomicFingerprint("GLOBAL", "MATERIALS", "MSCI_WORLD_MATERIALS", "UNHEDGED", "BROAD_SECTOR"),
    "EUROPE_TECHNOLOGY": EconomicFingerprint("GLOBAL", "TECHNOLOGY", "MSCI_WORLD_INFORMATION_TECHNOLOGY", "UNHEDGED", "BROAD_SECTOR"),
    "EUROPE_UTILITIES": EconomicFingerprint("GLOBAL", "UTILITIES", "MSCI_WORLD_UTILITIES", "UNHEDGED", "BROAD_SECTOR"),
    "GLOBAL_BANKS": EconomicFingerprint("EUROPE", "BANKS", "STOXX_EUROPE_600_OPTIMISED_BANKS", "UNHEDGED", "INDUSTRY"),
    "GLOBAL_HEALTHCARE": EconomicFingerprint("GLOBAL", "HEALTHCARE_INNOVATION", "THEMATIC_HEALTHCARE_INNOVATION", "UNHEDGED", "THEME"),
    "GLOBAL_INFRASTRUCTURE": EconomicFingerprint("UNITED_STATES", "INFRASTRUCTURE", "US_INFRASTRUCTURE_DEVELOPMENT", "UNHEDGED", "THEME"),
    "GLOBAL_TECHNOLOGY": EconomicFingerprint("GLOBAL", "DIGITALISATION", "DIGITALISATION_THEME", "UNHEDGED", "THEME"),
    "US_AEROSPACE_DEFENCE": EconomicFingerprint("GLOBAL", "AEROSPACE_AND_DEFENCE", "GLOBAL_DEFENCE", "UNHEDGED", "INDUSTRY"),
}


OLD_DEFECTS: dict[str, str] = {
    "AUSTRALIA": "GBP-hedged share class attached to an unhedged Australia family",
    "CHINA_BROAD": "China A-share lines dominate a family intended to represent broad MSCI China",
    "EUROPE_ENERGY": "MSCI World Energy history attached to a Europe sector family",
    "EUROPE_FINANCIALS": "Canonical route changes from Europe Financials to MSCI World Financials",
    "EUROPE_HEALTHCARE": "Canonical route changes from Europe Health Care to MSCI World Health Care",
    "EUROPE_INDUSTRIALS": "MSCI World Industrials history attached to a Europe sector family",
    "EUROPE_MATERIALS": "MSCI World Materials history attached to a Europe sector family",
    "EUROPE_TECHNOLOGY": "MSCI World Technology history attached to a Europe sector family",
    "EUROPE_UTILITIES": "MSCI World Utilities history attached to a Europe sector family",
    "GLOBAL_BANKS": "Europe banks and one development-bank bond observation attached to a global-banks family",
    "GLOBAL_HEALTHCARE": "Broad world-health history changes into healthcare-innovation thematic implementations",
    "GLOBAL_INFRASTRUCTURE": "US and Europe infrastructure products attached to a stable global-infrastructure family",
    "GLOBAL_TECHNOLOGY": "Digitalisation thematic implementation attached to a broad technology-sector family",
    "US_AEROSPACE_DEFENCE": "Global defence history attached to a United States aerospace-and-defence family",
}


def json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.bool_):
        return bool(value)
    if pd.isna(value):
        return None
    return str(value)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n", encoding="utf-8-sig")


def write_json(value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=json_default) + "\n", encoding="utf-8")


def write_parquet(frame: pd.DataFrame, path: Path, metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    arrow_meta = dict(table.schema.metadata or {})
    arrow_meta.update({str(key).encode(): str(value).encode() for key, value in metadata.items()})
    pq.write_table(table.replace_schema_metadata(arrow_meta), path, compression="zstd", use_dictionary=True)


class LayeredCaptureClient(a2.CaptureClient):
    """Reuse immutable A2 captures where paths match; write all new evidence to A2R."""

    def _copyless_reuse(self, relative_capture: str) -> tuple[bytes, dict[str, Any]] | None:
        capture_path = A2_SOURCE_ROOT / relative_capture
        meta_path = capture_path.with_suffix(capture_path.suffix + ".meta.json")
        if not capture_path.exists() or not meta_path.exists() or self.refresh:
            return None
        with gzip.open(capture_path, "rb") as handle:
            raw = handle.read()
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        ledger_row = {
            **meta,
            "cache_status": "REUSED_IMMUTABLE_A2_CAPTURE",
            "a2r_reference_path": str(capture_path),
        }
        self._append_ledger(ledger_row)
        return raw, ledger_row

    def get_json(self, source_name: str, url: str, params: dict[str, Any], relative_capture: str, series_identifier: str, timeout: int = 60, retries: int = 3) -> Any:
        local = self.source_root / relative_capture
        local_meta = local.with_suffix(local.suffix + ".meta.json")
        if not local.exists() and not local_meta.exists():
            reused = self._copyless_reuse(relative_capture)
            if reused is not None:
                return json.loads(reused[0].decode("utf-8"))
        return super().get_json(source_name, url, params, relative_capture, series_identifier, timeout, retries)

    def get_bytes(self, source_name: str, url: str, params: dict[str, Any], relative_capture: str, series_identifier: str, timeout: int = 90, retries: int = 3) -> bytes:
        local = self.source_root / relative_capture
        local_meta = local.with_suffix(local.suffix + ".meta.json")
        if not local.exists() and not local_meta.exists():
            reused = self._copyless_reuse(relative_capture)
            if reused is not None:
                return reused[0]
        return super().get_bytes(source_name, url, params, relative_capture, series_identifier, timeout, retries)


def load_original_catalogues() -> tuple[pd.DataFrame, pd.DataFrame]:
    active_path = A2_SOURCE_ROOT / "eodhd" / "catalogue_lse_active.json.gz"
    delisted_path = A2_SOURCE_ROOT / "eodhd" / "catalogue_lse_delisted.json.gz"
    with gzip.open(active_path, "rt", encoding="utf-8") as handle:
        active_payload = json.load(handle)
    with gzip.open(delisted_path, "rt", encoding="utf-8") as handle:
        delisted_payload = json.load(handle)
    return a2.normalize_catalogue(active_payload, False), a2.normalize_catalogue(delisted_payload, True)


def intended_fingerprint(family_id: str) -> EconomicFingerprint:
    if family_id in FAMILY_DEFINITIONS:
        d = FAMILY_DEFINITIONS[family_id]
        sector_or_industry = d["sector"] if d["industry"] in {"BROAD_SECTOR", "NOT_APPLICABLE"} else d["industry"]
        return EconomicFingerprint(d["geography"], sector_or_industry, d["objective"], d["hedge"], d["breadth"])
    d = NEW_FAMILY_DEFINITIONS[family_id]
    return EconomicFingerprint(d["geography"], d["sector"], d["objective"], "UNHEDGED", "BROAD_SECTOR")


def build_corrected_exposure_master() -> pd.DataFrame:
    master = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A0A1_ECONOMIC_EXPOSURE_MASTER.csv", dtype=str, keep_default_na=False)
    for family_id, d in FAMILY_DEFINITIONS.items():
        idx = master["economic_exposure_family_id"].eq(family_id)
        master.loc[idx, "economic_exposure_name"] = d["name"]
        master.loc[idx, "asset_class"] = d["asset"]
        master.loc[idx, "primary_geography"] = d["geography"]
        master.loc[idx, "geographic_scope"] = d["scope"]
        master.loc[idx, "sector"] = d["sector"]
        master.loc[idx, "industry"] = d["industry"]
        master.loc[idx, "economic_theme"] = d["theme"]
        master.loc[idx, "hedged_unhedged"] = d["hedge"]
        master.loc[idx, "classification_rule_version"] = "UKACTIVE-A2R-ECONOMIC-FINGERPRINT-v1.0.0"
        master.loc[idx, "classification_basis"] = "FROZEN_SEMANTIC_DEFINITION_BEFORE_HISTORY_SELECTION"
    template = master.loc[master["economic_exposure_family_id"].eq("GLOBAL_TECHNOLOGY")].iloc[0].to_dict()
    additions: list[dict[str, Any]] = []
    for family_id, d in NEW_FAMILY_DEFINITIONS.items():
        row = dict(template)
        row.update(
            {
                "economic_exposure_family_id": family_id,
                "economic_opportunity_id": stable_id("A2ROPP", family_id),
                "duplicate_group_id": stable_id("A2RDUP", family_id),
                "economic_exposure_name": d["name"],
                "opportunity_type": "SECTOR_INDUSTRY",
                "universe_tier": "EXTENDED",
                "asset_class": d.get("asset", "EQUITY"),
                "sub_asset_class": d.get("sub_asset", "SECTOR_EQUITY"),
                "primary_geography": d["geography"],
                "geographic_scope": d["scope"],
                "country": "NOT_APPLICABLE",
                "developed_emerging": "DEVELOPED" if d["geography"] == "EUROPE" else "MIXED_DEVELOPED_DOMINANT",
                "sector": d["sector"],
                "industry": d["industry"],
                "economic_theme": "NOT_APPLICABLE",
                "deepvue_theme": "NOT_APPLICABLE",
                "factor_style": "NOT_APPLICABLE",
                "market_cap_segment": "ALL_CAP",
                "portfolio_role": "GROWTH",
                "underlying_economic_currency_exposure": "MULTI_CURRENCY",
                "hedged_unhedged": "UNHEDGED",
                "hedge_currency": "NOT_APPLICABLE",
                "share_class_count": "1",
                "listing_count": "1",
                "provider_count": "1",
                "providers": "STATE_STREET" if family_id != "EUROPE_REAL_ESTATE" else "XTRACKERS",
                "currently_verified_investable_isin_count": "0",
                "classification_rule_version": "UKACTIVE-A2R-ECONOMIC-FINGERPRINT-v1.0.0",
                "classification_basis": "CONTROLLED_SECTOR_GRID_ADDITION_FROM_ORIGINAL_A0A1_DISCOVERY_REGISTRY",
                "future_signal_unit": family_id,
                "observation_date": OBSERVATION_DATE,
                "historical_eligibility_supported": "NO",
                "warning": WARNING,
            }
        )
        additions.append(row)
    result = pd.concat([master, pd.DataFrame(additions, columns=master.columns)], ignore_index=True)
    assert len(result) == 105 and result["economic_exposure_family_id"].is_unique
    return result


def _normalize_route_boole(routes: pd.DataFrame) -> pd.DataFrame:
    result = routes.copy()
    for column in ["historical_listing_extension", "family_membership_valid", "long_only_structure_valid"]:
        result[column] = result[column].map(parse_bool)
    return result


def build_remediation_routes(active: pd.DataFrame) -> pd.DataFrame:
    original = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A2_SOURCE_ROUTE_MAP.csv", dtype=str, keep_default_na=False)
    selected: list[pd.DataFrame] = []
    for family_id, tickers in EXISTING_ROUTE_SELECTIONS.items():
        part = original[original["ticker"].str.upper().isin(tickers)].copy()
        if family_id in {"GLOBAL_HEALTHCARE", "GLOBAL_TECHNOLOGY"}:
            part["economic_exposure_family_id"] = family_id
        selected.append(part)
    routes = pd.concat(selected, ignore_index=True, sort=False)

    actual_existing: dict[str, dict[str, str]] = {
        "AUAD": dict(objective="MSCI_AUSTRALIA", geography="AUSTRALIA", sector="BROAD_MARKET", breadth="BROAD_COUNTRY"),
        "HCHS": dict(objective="MSCI_CHINA", geography="CHINA", sector="BROAD_MARKET", breadth="BROAD_COUNTRY"),
        "FNCE": dict(objective="MSCI_EUROPE_FINANCIALS_35_20_CAPPED", geography="EUROPE", sector="FINANCIALS", breadth="BROAD_SECTOR"),
        "FNCL": dict(objective="MSCI_EUROPE_FINANCIALS_35_20_CAPPED", geography="EUROPE", sector="FINANCIALS", breadth="BROAD_SECTOR"),
        "HEAE": dict(objective="MSCI_EUROPE_HEALTH_CARE_35_20_CAPPED", geography="EUROPE", sector="HEALTHCARE", breadth="BROAD_SECTOR"),
        "HLTH": dict(objective="MSCI_EUROPE_HEALTH_CARE_35_20_CAPPED", geography="EUROPE", sector="HEALTHCARE", breadth="BROAD_SECTOR"),
        "HLTW": dict(objective="MSCI_WORLD_HEALTH_CARE", geography="GLOBAL", sector="HEALTHCARE", breadth="BROAD_SECTOR"),
        "HLTG": dict(objective="MSCI_WORLD_HEALTH_CARE", geography="GLOBAL", sector="HEALTHCARE", breadth="BROAD_SECTOR"),
        "HEAW": dict(objective="MSCI_WORLD_HEALTH_CARE_35_20_CAPPED", geography="GLOBAL", sector="HEALTHCARE", breadth="BROAD_SECTOR"),
        "WHEA": dict(objective="MSCI_WORLD_HEALTH_CARE_35_20_CAPPED", geography="GLOBAL", sector="HEALTHCARE", breadth="BROAD_SECTOR"),
        "TECW": dict(objective="MSCI_WORLD_INFORMATION_TECHNOLOGY_35_20_CAPPED", geography="GLOBAL", sector="TECHNOLOGY", breadth="BROAD_SECTOR"),
        "WTEC": dict(objective="MSCI_WORLD_INFORMATION_TECHNOLOGY_35_20_CAPPED", geography="GLOBAL", sector="TECHNOLOGY", breadth="BROAD_SECTOR"),
    }
    for idx, row in routes.iterrows():
        meta = actual_existing[row["ticker"].upper()]
        family_id = row["economic_exposure_family_id"]
        d = FAMILY_DEFINITIONS[family_id]
        routes.loc[idx, "economic_exposure_name"] = d["name"]
        routes.loc[idx, "universe_tier"] = "CORE" if family_id in {"AUSTRALIA", "CHINA_BROAD"} else "EXTENDED"
        routes.loc[idx, "asset_class"] = d["asset"]
        routes.loc[idx, "sub_asset_class"] = "BROAD_EQUITY" if d["sector"] == "BROAD_MARKET" else "SECTOR_EQUITY"
        routes.loc[idx, "primary_geography"] = d["geography"]
        routes.loc[idx, "sector"] = d["sector"]
        routes.loc[idx, "industry"] = d["industry"]
        routes.loc[idx, "economic_theme"] = d["theme"]
        routes.loc[idx, "actual_index_or_objective"] = meta["objective"]
        routes.loc[idx, "actual_geography"] = meta["geography"]
        routes.loc[idx, "actual_sector_or_industry"] = meta["sector"]
        routes.loc[idx, "actual_breadth_level"] = meta["breadth"]
        routes.loc[idx, "actual_hedge_status"] = "UNHEDGED"
        routes.loc[idx, "semantic_valid_from"] = "NOT_APPLICABLE"
        routes.loc[idx, "source_key"] = "A0A1_AND_A2_EXACT_IDENTITY_LINEAGE"
        routes.loc[idx, "historical_objective_lineage"] = f"ALL_OBSERVATIONS:{meta['objective']}"
        routes.loc[idx, "semantic_tolerance_basis"] = "EXACT_INTENDED_OR_EXPLICITLY_ALLOWED_INDEX_FAMILY"

    new_rows: list[dict[str, Any]] = []
    catalogue = active.copy()
    for spec in NEW_ROUTE_SPECS:
        cat = catalogue[(catalogue["Code"].eq(spec["eodhd_code"])) & (catalogue["Isin"].eq(spec["isin"]))]
        if cat.empty and spec["economic_exposure_family_id"] == "US_AEROSPACE_DEFENCE":
            cat = catalogue[(catalogue["Code"].eq(spec["eodhd_code"])) & (catalogue["Isin"].eq(spec["isin"]))]
        if cat.empty:
            raise RuntimeError(f"No exact active EODHD catalogue identity for {spec['ticker']} {spec['isin']}")
        family_id = spec["economic_exposure_family_id"]
        d = FAMILY_DEFINITIONS.get(family_id, NEW_FAMILY_DEFINITIONS.get(family_id, {}))
        listing_id = stable_id("A2RLIST", spec["isin"], spec["ticker"], "XLON")
        share_id = stable_id("A2RSC", spec["share_class_token"])
        fund_id = stable_id("A2RFUND", spec["isin"][:8], spec["legal_fund_name"])
        duplicate_id = stable_id("A2RDUP", family_id)
        new_rows.append(
            {
                "listing_id": listing_id,
                "share_class_id": share_id,
                "fund_entity_id": fund_id,
                "isin": spec["isin"],
                "sedol": "NOT_AVAILABLE",
                "exchange": "LONDON STOCK EXCHANGE",
                "mic": "XLON",
                "ticker": spec["ticker"],
                "listing_currency": spec["effective_listing_currency"],
                "price_unit": spec["effective_price_unit"],
                "price_unit_multiplier_to_listing_currency": 0.01 if spec["effective_price_unit"] == "GBX" else 1.0,
                "listing_inception_date": spec["listing_inception_date"],
                "active_listing_status": "ACTIVE_CONFIRMED_CURRENT_CATALOGUE",
                "active_status_verification_date": OBSERVATION_DATE,
                "active_status_confidence": "HIGH_EXACT_ISIN_PRIMARY_EVIDENCE",
                "economic_exposure_family_id": family_id,
                "duplicate_group_id": duplicate_id,
                "local_market_data_symbol_match": "EXACT_ISIN_AND_EXCHANGE_CODE",
                "observation_date": OBSERVATION_DATE,
                "historical_eligibility_supported": "NO",
                "warning": WARNING,
                "ticker_key": spec["ticker"],
                "isin_key": spec["isin"],
                "eodhd_code": spec["eodhd_code"],
                "eodhd_name": cat.iloc[0]["Name"],
                "eodhd_price_unit": cat.iloc[0]["Currency"],
                "eodhd_type": cat.iloc[0]["Type"],
                "eodhd_isin": spec["isin"],
                "catalogue_status": "ACTIVE",
                "route_type": "A2R_ACTIVE_EXACT_ISIN_WITH_PRIMARY_OBJECTIVE_EVIDENCE",
                "a0a1_price_unit": "NOT_APPLICABLE_A2R_ROUTE",
                "effective_price_unit": spec["effective_price_unit"],
                "effective_listing_currency": spec["effective_listing_currency"],
                "eodhd_symbol": spec["eodhd_code"] + ".LSE",
                "historical_listing_extension": False,
                "delisted_catalogue_status": "ACTIVE_CURRENT_CATALOGUE",
                "price_unit_multiplier_to_listing_currency_effective": 0.01 if spec["effective_price_unit"] == "GBX" else 1.0,
                "provider_issuer": spec["provider_issuer"],
                "share_class_inception_date": spec["share_class_inception_date"],
                "accumulating_distributing": spec["accumulating_distributing"],
                "hedged_unhedged": "UNHEDGED",
                "hedge_currency": "NOT_APPLICABLE",
                "instrument_type": "ETF",
                "product_structure": "UCITS_ETF",
                "ucits_status": "UCITS_CONFIRMED_PRIMARY_EVIDENCE",
                "leverage": "NO",
                "daily_reset": "NO",
                "path_dependence": "NO",
                "maturity": "OPEN_ENDED",
                "fund_inception_date": spec["fund_inception_date"],
                "legal_fund_name": spec["legal_fund_name"],
                "economic_exposure_name": d["name"],
                "universe_tier": "EXTENDED" if family_id not in {"CHINA_BROAD"} else "CORE",
                "asset_class": d.get("asset", "EQUITY"),
                "sub_asset_class": d.get("sub_asset", "SECTOR_EQUITY"),
                "primary_geography": d["geography"],
                "sector": d["sector"],
                "industry": d.get("industry", "BROAD_SECTOR"),
                "economic_theme": d.get("theme", "NOT_APPLICABLE"),
                "deepvue_theme": "NOT_APPLICABLE",
                "duplicate_group_id_exposure": duplicate_id,
                "current_investability_state": "CURRENT_CANDIDATE_UNVERIFIED",
                "current_uk_retail_eligibility": "CURRENT_DISCLOSURE_CONFIRMED",
                "isa_eligibility": spec["public_isa_rules_status"],
                "sipp_eligibility": "UNCERTAIN",
                "broker_status": "NOT_CHECKED",
                "kid_retail_document_evidence": OFFICIAL_SOURCES.get(spec["source_key"], "NOT_AVAILABLE"),
                "structural_eligibility": "ELIGIBLE_LONG_ONLY_STRUCTURE",
                "eligibility_evidence_ids": spec["source_key"],
                "family_membership_valid": True,
                "long_only_structure_valid": True,
                "actual_index_or_objective": spec["actual_index_or_objective"],
                "actual_geography": spec["actual_geography"],
                "actual_sector_or_industry": spec["actual_sector_or_industry"],
                "actual_breadth_level": spec["actual_breadth_level"],
                "actual_hedge_status": spec["actual_hedge_status"],
                "semantic_valid_from": spec["semantic_valid_from"],
                "source_key": spec["source_key"],
                "registry_present": spec["registry_present"],
                "public_isa_rules_status": spec["public_isa_rules_status"],
                "historical_objective_lineage": (
                    "2006-10-20_TO_2017_INDEX_CHANGE:MACQUARIE_GLOBAL_INFRASTRUCTURE_100|POST_CHANGE:FTSE_GLOBAL_CORE_INFRASTRUCTURE"
                    if family_id == "GLOBAL_INFRASTRUCTURE"
                    else ("BEFORE_2026-07-16:GLOBAL_METAVERSE_NOT_VALID_FOR_FAMILY|FROM_2026-07-16:VETTAFI_AMERICAN_FUTURE_OF_DEFENCE" if family_id == "US_AEROSPACE_DEFENCE" else f"ALL_OBSERVATIONS:{spec['actual_index_or_objective']}")
                ),
                "semantic_tolerance_basis": (
                    "SAME_LEGAL_FUND_AND_BROAD_GLOBAL_LISTED_INFRASTRUCTURE_OBJECTIVE;PREDECESSOR_INDEX_EXPLICITLY_ALLOWED_NOT_SPLICED"
                    if family_id == "GLOBAL_INFRASTRUCTURE"
                    else ("DATED_OBJECTIVE_CHANGE;PREDECESSOR_OBSERVATIONS_INVALIDATED" if family_id == "US_AEROSPACE_DEFENCE" else "EXACT_INTENDED_INDEX_OR_OBJECTIVE")
                ),
            }
        )
    routes = pd.concat([routes, pd.DataFrame(new_rows)], ignore_index=True, sort=False)
    for column in ["actual_index_or_objective", "actual_geography", "actual_sector_or_industry", "actual_breadth_level", "actual_hedge_status", "semantic_valid_from", "source_key", "historical_objective_lineage", "semantic_tolerance_basis"]:
        routes[column] = routes[column].fillna("NOT_AVAILABLE")
    routes = _normalize_route_boole(routes)
    assert routes["listing_id"].is_unique
    return routes


def semantic_route_audit(routes: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for route in routes.itertuples(index=False):
        family_id = route.economic_exposure_family_id
        intended = intended_fingerprint(family_id)
        actual = EconomicFingerprint(
            clean(route.actual_geography),
            clean(route.actual_sector_or_industry),
            clean(route.actual_index_or_objective),
            clean(route.actual_hedge_status),
            clean(route.actual_breadth_level),
        )
        allowed = FAMILY_DEFINITIONS.get(family_id, {}).get("allowed", [])
        passed, reasons = semantic_match(intended, actual, allowed)
        rows.append(
            {
                "economic_exposure_family_id": family_id,
                "listing_id": route.listing_id,
                "share_class_id": route.share_class_id,
                "isin": route.isin,
                "ticker": route.ticker,
                "intended_fingerprint": intended.key,
                "actual_fingerprint": actual.key,
                "semantic_valid_from": route.semantic_valid_from,
                "semantic_match": "PASS" if passed else "FAIL",
                "mismatch_reasons": semicolon(reasons),
                "source_key": route.source_key,
                "source_url": OFFICIAL_SOURCES.get(clean(route.source_key), "A0A1_A2_EXISTING_EVIDENCE_LINEAGE"),
                "warning": WARNING,
            }
        )
    return pd.DataFrame(rows)


def apply_route_semantic_floors(
    routes: pd.DataFrame,
    instrument: pd.DataFrame,
    pit: pd.DataFrame,
    listing_frames: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
    instrument = instrument.copy()
    pit = pit.copy()
    for route in routes.itertuples(index=False):
        floor_text = clean(route.semantic_valid_from)
        if floor_text in {"NOT_AVAILABLE", "NOT_APPLICABLE"}:
            continue
        floor = pd.Timestamp(floor_text)
        if route.listing_id in listing_frames:
            listing_frames[route.listing_id] = apply_semantic_floor_to_frame(listing_frames[route.listing_id], floor)
        mask = instrument["listing_id"].eq(route.listing_id)
        if mask.any():
            work = apply_semantic_floor_to_frame(instrument.loc[mask].copy(), floor)
            for column in work.columns:
                instrument.loc[mask, column] = work[column].to_numpy()
        p_mask = pit["listing_id"].eq(route.listing_id)
        if p_mask.any():
            blocked = p_mask & (pd.to_datetime(pit["date"]) < floor)
            pit.loc[blocked, "data_valid"] = False
            pit.loc[blocked, "historical_investability_state"] = "KNOWN_NOT_ELIGIBLE_FOR_THIS_ECONOMIC_FAMILY"
            pit.loc[blocked, "historical_investability_confidence"] = "HIGH_DATED_OBJECTIVE_CHANGE_EVIDENCE"
            pit.loc[p_mask, "cum_valid_observations"] = pit.loc[p_mask, "data_valid"].astype(bool).astype(int).cumsum().to_numpy()
            for horizon in [21, 42, 63, 126, 189, 252, 504]:
                pit.loc[p_mask, f"warmup_{horizon}"] = (
                    pit.loc[p_mask, "data_valid"].astype(bool).astype(int).rolling(horizon, min_periods=horizon).sum().eq(horizon).to_numpy()
                )
            pit.loc[p_mask, "signal_warmup_available"] = pit.loc[p_mask, "cum_valid_observations"].ge(21).to_numpy()
            pit.loc[p_mask, "source_evidence"] = pit.loc[p_mask, "source_evidence"].astype(str) + f"|SEMANTIC_OBJECTIVE_VALID_FROM={floor.date().isoformat()}"
    return instrument, pit, listing_frames


def run_a2_engine(
    routes: pd.DataFrame,
    exposure_master: pd.DataFrame,
    policy: dict[str, Any],
    client: LayeredCaptureClient,
    workers: int,
) -> dict[str, Any]:
    calendar_audit = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A2_XLON_RESEARCH_CALENDAR.csv")
    calendar = pd.DatetimeIndex(
        pd.to_datetime(calendar_audit.loc[calendar_audit["included_in_canonical_calendar"].astype(str).str.lower().eq("true"), "date"]),
        name="date",
    )
    fx_table = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A2_FX_SERIES.parquet")
    fx_table["date"] = pd.to_datetime(fx_table["date"]).dt.normalize()
    fx_table["fx_source_date"] = pd.to_datetime(fx_table["fx_source_date"]).dt.normalize()
    cash = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A2_CASH_SERIES.parquet")
    cash["date"] = pd.to_datetime(cash["date"]).dt.normalize()

    payloads = a2.fetch_listing_payloads(client, routes, policy, workers)
    instrument, pit, events, stale_report, listing_frames = a2.build_instrument_and_eligibility_histories(
        routes, payloads, calendar, fx_table, policy
    )
    instrument, pit, listing_frames = apply_route_semantic_floors(routes, instrument, pit, listing_frames)
    validations = a2.listing_validation_status(routes, events, listing_frames)
    instrument, pit, listing_frames = a2.apply_listing_validation_gate(instrument, pit, listing_frames, validations)
    yahoo_validation = a2.fetch_and_validate_yahoo(client, routes, listing_frames, policy)
    fx_pairs = a2.build_fx_pair_validation(routes, listing_frames)
    instrument, pit, listing_frames, validations, cross_source_exclusions = a2.apply_cross_source_failure_gate(
        routes, instrument, pit, listing_frames, validations, fx_pairs, yahoo_validation
    )
    coherence = a2.build_share_class_coherence(routes, listing_frames)
    subset_ids = sorted(set(routes["economic_exposure_family_id"]) | {"GLOBAL_BANKS"})
    subset_master = exposure_master[exposure_master["economic_exposure_family_id"].isin(subset_ids)].copy()
    canonical, exposure, panel = a2.build_canonical_histories(
        routes, listing_frames, pit, subset_master, calendar, cash, policy
    )
    exposure = exposure[exposure["economic_exposure_family_id"].ne("ACTUAL_GBP_CASH")].copy()
    panel = panel[panel["economic_exposure_family_id"].ne("ACTUAL_GBP_CASH")].copy()
    return {
        "calendar": calendar,
        "fx_table": fx_table,
        "cash": cash,
        "payloads": payloads,
        "instrument": instrument,
        "pit": pit,
        "events": events,
        "stale_report": stale_report,
        "listing_frames": listing_frames,
        "validations": validations,
        "yahoo_validation": yahoo_validation,
        "fx_pairs": fx_pairs,
        "coherence": coherence,
        "cross_source_exclusions": cross_source_exclusions,
        "canonical": canonical,
        "exposure": exposure,
        "panel": panel,
    }


def add_dynamic_warmups(panel: pd.DataFrame) -> pd.DataFrame:
    result = panel.copy()
    result["date"] = pd.to_datetime(result["date"]).dt.normalize()
    result = result.sort_values(["economic_exposure_family_id", "date"], kind="mergesort").reset_index(drop=True)
    valid = valid_mask(result)
    for horizon in HORIZONS:
        result[f"warmup_{horizon}"] = valid.groupby(result["economic_exposure_family_id"]).transform(
            lambda values, h=horizon: values.astype(int).rolling(h, min_periods=h).sum().eq(h)
        )
    return result


def build_full_corrected_panel(engine_panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    original = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A2_TOTAL_RETURN_PANEL_GBP.parquet")
    original["date"] = pd.to_datetime(original["date"]).dt.normalize()
    blocking = set(FAMILY_DEFINITIONS)
    preserved = original[~original["economic_exposure_family_id"].isin(blocking)].copy()
    corrected = pd.concat([preserved, engine_panel], ignore_index=True, sort=False)
    corrected = corrected.drop_duplicates(["economic_exposure_family_id", "date"], keep="last")
    corrected = add_dynamic_warmups(corrected)
    corrected["warning"] = WARNING
    return original, corrected


def build_coverage(master: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in master.itertuples(index=False):
        family_id = row.economic_exposure_family_id
        g = panel[panel["economic_exposure_family_id"].eq(family_id)].sort_values("date")
        mask = valid_mask(g) if not g.empty else pd.Series(dtype=bool)
        dates = pd.to_datetime(g.loc[mask, "date"]) if len(mask) else pd.Series(dtype="datetime64[ns]")
        count = int(mask.sum()) if len(mask) else 0
        rows.append(
            {
                "economic_exposure_family_id": family_id,
                "economic_exposure_name": row.economic_exposure_name,
                "universe_tier": row.universe_tier,
                "valid_return_observations": count,
                "first_valid_date": dates.min() if count else pd.NaT,
                "last_valid_date": dates.max() if count else pd.NaT,
                "has_1_year": count >= 252,
                "has_3_years": count >= 756,
                "has_5_years": count >= 1260,
                "has_10_years": count >= 2520,
                "usable_history": count > 0,
                "validated_actual_implementation_history": count > 0,
                "requires_proxy_for_504_day_research": 0 < count < 504,
                "historical_eligibility_unresolved": True,
                "a3_ready": count >= 21,
                "a3_scope": "A2R_SIGNAL_SPECIFIC_DYNAMIC_ADMISSION" if count >= 21 else "NOT_READY",
                "selected_listing_count_through_time": int(g.loc[mask, "implementation_listing_id"].nunique()) if count else 0,
                "validation_statuses": "A2R_EXISTING_ENGINE_VALIDATED" if count else "NO_VALID_IMPLEMENTATION_HISTORY",
            }
        )
    return pd.DataFrame(rows)


def build_dynamic_eligibility(master: pd.DataFrame, panel: pd.DataFrame, role_map: pd.DataFrame | None = None) -> pd.DataFrame:
    role_lookup = role_map.set_index("economic_exposure_family_id") if role_map is not None and not role_map.empty else None
    rows: list[dict[str, Any]] = []
    for row in master.itertuples(index=False):
        family_id = row.economic_exposure_family_id
        g = panel[panel["economic_exposure_family_id"].eq(family_id)].sort_values("date")
        mask = valid_mask(g) if not g.empty else pd.Series(dtype=bool)
        count = int(mask.sum()) if len(mask) else 0
        if role_lookup is not None and family_id in role_lookup.index:
            role = role_lookup.loc[family_id, "primary_rotation_role"]
            pool = role_lookup.loc[family_id, "primary_competition_pool_id"]
        elif family_id in FAMILY_DEFINITIONS:
            role = FAMILY_DEFINITIONS[family_id]["role"] if count else "INSUFFICIENT_DATA"
            pool = FAMILY_DEFINITIONS[family_id]["pool"] if count else "POOL_INSUFFICIENT_DATA"
        else:
            role = "SECTOR_ROTATION" if count else "INSUFFICIENT_DATA"
            pool = "POOL_EUROPE_BROAD_SECTORS" if family_id.startswith("EUROPE_") and count else ("POOL_GLOBAL_BROAD_SECTORS" if count else "POOL_INSUFFICIENT_DATA")
        record = {
            "economic_exposure_family_id": family_id,
            "economic_exposure_name": row.economic_exposure_name,
            "universe_tier": row.universe_tier,
            "valid_return_observations": count,
            "research_maturity": maturity_label(count),
            "rotation_role": role,
            "primary_competition_pool_id": pool,
            "signal_specific_dynamic_admission": "YES",
            "fixed_504_gate": "REMOVED",
            "data_quality_flags": "HISTORICAL_ELIGIBILITY_UNRESOLVED" if count else "NO_VALID_IMPLEMENTATION_HISTORY",
            "warning": WARNING,
        }
        for horizon in HORIZONS:
            date = earliest_valid_observation_date(g["date"], mask, horizon) if not g.empty else pd.NaT
            record[f"earliest_valid_{horizon}_session_signal_date"] = date
            record[f"eligible_{horizon}_session_research"] = "YES" if pd.notna(date) else "NO"
        rows.append(record)
    return pd.DataFrame(rows).sort_values("economic_exposure_family_id").reset_index(drop=True)


def build_blocking_definitions() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for family_id, d in FAMILY_DEFINITIONS.items():
        fp = intended_fingerprint(family_id)
        rows.append(
            {
                "economic_exposure_family_id": family_id,
                "canonical_family_name": d["name"],
                "asset_class": d["asset"],
                "primary_geography": d["geography"],
                "geographic_scope": d["scope"],
                "sector": d["sector"],
                "industry": d["industry"],
                "theme_if_applicable": d["theme"],
                "breadth_level": d["breadth"],
                "currency_hedge_status": d["hedge"],
                "intended_index_family_or_objective": d["objective"],
                "allowed_equivalent_objectives": semicolon(d["allowed"]),
                "rotation_role": d["role"],
                "parent_exposure_family_id": d["parent"],
                "primary_competition_pool_id": d["pool"],
                "frozen_economic_identity_fingerprint": fp.key,
                "definition_frozen_before_history_selection": "YES",
                "warning": WARNING,
            }
        )
    return pd.DataFrame(rows)


def build_fingerprint_table(routes: pd.DataFrame, route_audit: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for family_id in list(FAMILY_DEFINITIONS) + list(NEW_FAMILY_DEFINITIONS):
        intended = intended_fingerprint(family_id)
        rows.append(
            {
                "record_type": "INTENDED_ECONOMIC_FAMILY",
                "economic_exposure_family_id": family_id,
                "listing_id": "NOT_APPLICABLE",
                "isin": "NOT_APPLICABLE",
                "ticker": "NOT_APPLICABLE",
                "geography": intended.geography,
                "sector_or_industry": intended.sector_or_industry,
                "index_or_exposure_objective": intended.index_or_objective,
                "hedged_or_unhedged": intended.hedge_status,
                "breadth_level": intended.breadth_level,
                "fingerprint": intended.key,
                "semantic_match": "REFERENCE",
                "mismatch_reasons": "NOT_APPLICABLE",
                "semantic_valid_from": "NOT_APPLICABLE",
                "historical_objective_lineage": "DEFINED_BY_INTENDED_FINGERPRINT_AND_ALLOWED_EQUIVALENTS",
                "semantic_tolerance_basis": "EXPLICIT_ALLOWED_OBJECTIVES_ONLY",
                "source_url": "FROZEN_A2R_DEFINITION",
                "warning": WARNING,
            }
        )
    for item in route_audit.itertuples(index=False):
        route = routes.loc[routes["listing_id"].eq(item.listing_id)].iloc[0]
        actual = EconomicFingerprint(
            clean(route.actual_geography), clean(route.actual_sector_or_industry), clean(route.actual_index_or_objective), clean(route.actual_hedge_status), clean(route.actual_breadth_level)
        )
        rows.append(
            {
                "record_type": "IMPLEMENTATION_ROUTE",
                "economic_exposure_family_id": item.economic_exposure_family_id,
                "listing_id": item.listing_id,
                "isin": item.isin,
                "ticker": item.ticker,
                "geography": actual.geography,
                "sector_or_industry": actual.sector_or_industry,
                "index_or_exposure_objective": actual.index_or_objective,
                "hedged_or_unhedged": actual.hedge_status,
                "breadth_level": actual.breadth_level,
                "fingerprint": actual.key,
                "semantic_match": item.semantic_match,
                "mismatch_reasons": item.mismatch_reasons,
                "semantic_valid_from": item.semantic_valid_from,
                "historical_objective_lineage": clean(route.historical_objective_lineage),
                "semantic_tolerance_basis": clean(route.semantic_tolerance_basis),
                "source_url": item.source_url,
                "warning": WARNING,
            }
        )
    return pd.DataFrame(rows)


def old_route_fingerprint(family_id: str, route: dict[str, Any]) -> EconomicFingerprint:
    isin = clean(route.get("isin"))
    ticker = clean(route.get("ticker"))
    if family_id == "AUSTRALIA":
        hedge = "UNHEDGED" if isin == "IE00BD4TY345" else "HEDGED_GBP"
        return EconomicFingerprint("AUSTRALIA", "BROAD_MARKET", "MSCI_AUSTRALIA", hedge, "BROAD_COUNTRY")
    if family_id == "CHINA_BROAD":
        if isin == "IE0007P4PBU1":
            return EconomicFingerprint("CHINA", "BROAD_MARKET", "MSCI_CHINA", "UNHEDGED", "BROAD_COUNTRY")
        return EconomicFingerprint("CHINA", "A_SHARES", "MSCI_CHINA_A", "UNHEDGED", "NARROW_COUNTRY_SEGMENT")
    correct_europe = {
        "EUROPE_FINANCIALS": ("IE00BKWQ0G16", "FINANCIALS", "MSCI_EUROPE_FINANCIALS_35_20_CAPPED"),
        "EUROPE_HEALTHCARE": ("IE00BKWQ0H23", "HEALTHCARE", "MSCI_EUROPE_HEALTH_CARE_35_20_CAPPED"),
    }
    if family_id in correct_europe and isin == correct_europe[family_id][0]:
        _, sector, objective = correct_europe[family_id]
        return EconomicFingerprint("EUROPE", sector, objective, "UNHEDGED", "BROAD_SECTOR")
    if family_id == "GLOBAL_HEALTHCARE":
        if isin == "LU0533033311":
            return EconomicFingerprint("GLOBAL", "HEALTHCARE", "MSCI_WORLD_HEALTH_CARE", "UNHEDGED", "BROAD_SECTOR")
        if isin == "IE00BYZK4776":
            return EconomicFingerprint("GLOBAL", "HEALTHCARE_INNOVATION", "THEMATIC_HEALTHCARE_INNOVATION", "UNHEDGED", "THEME")
        return EconomicFingerprint("GLOBAL", "HEALTH_AND_WELLNESS", "HEALTH_AND_WELLNESS_THEME", "UNHEDGED", "THEME")
    if family_id == "GLOBAL_INFRASTRUCTURE":
        if isin == "IE000AFVONT7":
            return EconomicFingerprint("EUROPE", "INFRASTRUCTURE", "EUROPE_INFRASTRUCTURE", "UNHEDGED", "THEME")
        return EconomicFingerprint("UNITED_STATES", "INFRASTRUCTURE", "US_INFRASTRUCTURE_DEVELOPMENT", "UNHEDGED", "THEME")
    if family_id == "GLOBAL_BANKS" and ticker == "MDBU":
        return EconomicFingerprint("GLOBAL", "DEVELOPMENT_BANK_BONDS", "MULTILATERAL_DEVELOPMENT_BANK_BONDS", "UNHEDGED", "BOND_ISSUER_TYPE")
    return OLD_ACTUAL_FINGERPRINTS[family_id]


def build_existing_lineage_audit() -> pd.DataFrame:
    original_panel = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A2_EXPOSURE_HISTORY_MASTER.parquet")
    original_routes = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A2_SOURCE_ROUTE_MAP.csv", dtype=str, keep_default_na=False)
    rows: list[dict[str, Any]] = []
    for family_id, d in FAMILY_DEFINITIONS.items():
        g = original_panel[original_panel["economic_exposure_family_id"].eq(family_id)].copy()
        selected = g[g["selected_listing_id"].notna() & g["selected_listing_id"].ne("NOT_AVAILABLE_NO_SELECTION")]
        listing_ids = sorted(selected["selected_listing_id"].dropna().astype(str).unique())
        if not listing_ids:
            listing_ids = ["NOT_AVAILABLE"]
        for listing_id in listing_ids:
            route = original_routes[original_routes["listing_id"].eq(listing_id)]
            r = route.iloc[0].to_dict() if not route.empty else {}
            sg = selected[selected["selected_listing_id"].eq(listing_id)] if listing_id != "NOT_AVAILABLE" else selected
            old_actual = old_route_fingerprint(family_id, r)
            intended = intended_fingerprint(family_id)
            passed, reasons = semantic_match(intended, old_actual, d["allowed"])
            rows.append(
                {
                    "a2_economic_exposure_family_id": family_id,
                    "implementation_share_class_id": clean(r.get("share_class_id")),
                    "implementation_listing_id": listing_id,
                    "isin": clean(r.get("isin")),
                    "ticker": clean(r.get("ticker")),
                    "exchange": clean(r.get("exchange")),
                    "mic": clean(r.get("mic")),
                    "issuer": clean(r.get("provider_issuer")),
                    "product_name": clean(r.get("legal_fund_name", r.get("eodhd_name"))),
                    "underlying_index_or_objective": old_actual.index_or_objective,
                    "index_provider_description": old_actual.index_or_objective,
                    "geographic_exposure": old_actual.geography,
                    "sector_or_industry_exposure": old_actual.sector_or_industry,
                    "hedging_status": old_actual.hedge_status,
                    "breadth_level": old_actual.breadth_level,
                    "fund_inception_date": clean(r.get("fund_inception_date")),
                    "listing_inception_date": clean(r.get("listing_inception_date")),
                    "first_A2_observation": pd.to_datetime(sg["date"]).min() if not sg.empty else pd.NaT,
                    "last_A2_observation": pd.to_datetime(sg["date"]).max() if not sg.empty else pd.NaT,
                    "selected_session_count": int(len(sg)),
                    "exact_evidence_source": semicolon([clean(r.get("identity_evidence_ids")), clean(r.get("eligibility_evidence_ids")), clean(r.get("eodhd_symbol"))]),
                    "intended_fingerprint": intended.key,
                    "actual_old_fingerprint": old_actual.key,
                    "semantic_fingerprint_result": "PASS" if passed else "FAIL",
                    "semantic_failure_reasons": semicolon(reasons),
                    "forensic_defect": OLD_DEFECTS[family_id],
                    "warning": WARNING,
                }
            )
    return pd.DataFrame(rows)


def build_lineage_corrections(
    routes: pd.DataFrame,
    panel: pd.DataFrame,
    dynamic: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for family_id, d in FAMILY_DEFINITIONS.items():
        g = panel[panel["economic_exposure_family_id"].eq(family_id)]
        mask = valid_mask(g)
        valid = g.loc[mask]
        family_routes = routes[routes["economic_exposure_family_id"].eq(family_id)]
        new_isins = semicolon(family_routes["isin"]) if not family_routes.empty else "NOT_APPLICABLE"
        new_tickers = semicolon(family_routes["ticker"]) if not family_routes.empty else "NOT_APPLICABLE"
        outcome = d["outcome"]
        method = "EXCLUDED" if outcome == "NO_VALID_IMPLEMENTATION_HISTORY" else ("SHORTENED" if outcome == "VALID_ONLY_FROM_LATER_DATE" else "REPLACED")
        dyn = dynamic.loc[dynamic["economic_exposure_family_id"].eq(family_id)].iloc[0]
        rows.append(
            {
                "economic_exposure_family_id": family_id,
                "old_primary_implementation_summary": OLD_ACTUAL_FINGERPRINTS[family_id].key,
                "defect": OLD_DEFECTS[family_id],
                "remediation_method": method,
                "remediation_outcome_state": outcome,
                "new_implementation_isins": new_isins,
                "new_implementation_tickers": new_tickers,
                "new_economic_fingerprint": intended_fingerprint(family_id).key,
                "corrected_first_valid_return_date": pd.to_datetime(valid["date"]).min() if not valid.empty else pd.NaT,
                "corrected_last_valid_return_date": pd.to_datetime(valid["date"]).max() if not valid.empty else pd.NaT,
                "valid_return_observations": int(mask.sum()),
                **{f"earliest_valid_{h}_session_signal_date": dyn[f"earliest_valid_{h}_session_signal_date"] for h in HORIZONS},
                "old_invalid_route_retained_in_audit": "YES",
                "old_invalid_route_admitted_to_corrected_panel": "NO",
                "proxy_history_used": "NO",
                "historical_eligibility_established": "NO",
                "source_urls": semicolon(OFFICIAL_SOURCES.get(clean(value), "") for value in family_routes.get("source_key", pd.Series(dtype=str))),
                "warning": WARNING,
            }
        )
    result = pd.DataFrame(rows)
    assert set(result["remediation_outcome_state"]).issubset(ALLOWED_OUTCOMES)
    assert len(result) == 14
    return result


def build_before_after_audit(master: pd.DataFrame, original: pd.DataFrame, corrected: pd.DataFrame) -> pd.DataFrame:
    original_master_ids = set(pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A0A1_ECONOMIC_EXPOSURE_MASTER.csv")["economic_exposure_family_id"])
    rows: list[dict[str, Any]] = []
    for family_id in master["economic_exposure_family_id"]:
        before = original[original["economic_exposure_family_id"].eq(family_id)].copy()
        after = corrected[corrected["economic_exposure_family_id"].eq(family_id)].copy()
        bmask = valid_mask(before) if not before.empty else pd.Series(dtype=bool)
        amask = valid_mask(after) if not after.empty else pd.Series(dtype=bool)
        overlap = before[["date", "return_gbp_total", "data_valid"]].merge(
            after[["date", "return_gbp_total", "data_valid"]], on="date", suffixes=("_before", "_after")
        ) if not before.empty and not after.empty else pd.DataFrame()
        comparable = overlap[overlap["data_valid_before"].astype(bool) & overlap["data_valid_after"].astype(bool)].dropna(subset=["return_gbp_total_before", "return_gbp_total_after"]) if not overlap.empty else pd.DataFrame()
        max_diff = float((comparable["return_gbp_total_before"] - comparable["return_gbp_total_after"]).abs().max()) if not comparable.empty else np.nan
        before_hash = history_hash(before) if not before.empty else "NOT_APPLICABLE"
        after_hash = history_hash(after) if not after.empty else "NOT_APPLICABLE"
        if family_id not in original_master_ids:
            status = "A2R_NEW_FAMILY_ADDITION"
        elif family_id in FAMILY_DEFINITIONS:
            status = "INTENTIONALLY_REMEDIATED"
        else:
            status = "RETURN_IDENTICAL" if before_hash == after_hash else "UNEXPECTED_DIFFERENCE"
        rows.append(
            {
                "economic_exposure_family_id": family_id,
                "audit_scope": "BLOCKING_REMEDIATION" if family_id in FAMILY_DEFINITIONS else ("A2R_SECTOR_GRID_ADDITION" if family_id not in original_master_ids else "UNAFFECTED_REGRESSION_CONTROL"),
                "before_valid_return_count": int(bmask.sum()) if len(bmask) else 0,
                "after_valid_return_count": int(amask.sum()) if len(amask) else 0,
                "before_first_valid_date": pd.to_datetime(before.loc[bmask, "date"]).min() if len(bmask) and bmask.any() else pd.NaT,
                "after_first_valid_date": pd.to_datetime(after.loc[amask, "date"]).min() if len(amask) and amask.any() else pd.NaT,
                "before_history_sha256": before_hash,
                "after_history_sha256": after_hash,
                "overlap_valid_observations": int(len(comparable)),
                "max_absolute_return_difference_on_overlap": max_diff,
                "audit_result": status,
                "warning": WARNING,
            }
        )
    return pd.DataFrame(rows)


def build_sector_grid_audit(coverage: pd.DataFrame, geography: str) -> pd.DataFrame:
    mapping = {
        "EUROPE": {
            "TECHNOLOGY": "EUROPE_TECHNOLOGY", "FINANCIALS": "EUROPE_FINANCIALS", "HEALTHCARE": "EUROPE_HEALTHCARE", "INDUSTRIALS": "EUROPE_INDUSTRIALS",
            "CONSUMER_DISCRETIONARY": "EUROPE_CONSUMER_DISCRETIONARY", "CONSUMER_STAPLES": "EUROPE_CONSUMER_STAPLES", "COMMUNICATION_SERVICES": "EUROPE_COMMUNICATION_SERVICES",
            "ENERGY": "EUROPE_ENERGY", "MATERIALS": "EUROPE_MATERIALS", "UTILITIES": "EUROPE_UTILITIES", "REAL_ESTATE": "EUROPE_REAL_ESTATE",
        },
        "GLOBAL": {
            "TECHNOLOGY": "GLOBAL_TECHNOLOGY", "FINANCIALS": "GLOBAL_FINANCIALS", "HEALTHCARE": "GLOBAL_HEALTHCARE", "INDUSTRIALS": "GLOBAL_INDUSTRIALS",
            "CONSUMER_DISCRETIONARY": "GLOBAL_CONSUMER_DISCRETIONARY", "CONSUMER_STAPLES": "GLOBAL_CONSUMER_STAPLES", "COMMUNICATION_SERVICES": "GLOBAL_COMMUNICATION_SERVICES",
            "ENERGY": "GLOBAL_ENERGY", "MATERIALS": "GLOBAL_MATERIALS", "UTILITIES": "GLOBAL_UTILITIES", "REAL_ESTATE": "GLOBAL_REAL_ESTATE",
        },
    }
    cov = coverage.set_index("economic_exposure_family_id")
    rows: list[dict[str, Any]] = []
    for sector, family_id in mapping[geography].items():
        exists = family_id in cov.index
        count = int(cov.loc[family_id, "valid_return_observations"]) if exists else 0
        status = "VALID_IMPLEMENTATION_FOUND" if count >= 504 else ("CURRENT_PRODUCT_SHORT_HISTORY" if count > 0 else "NO_SUITABLE_UK_IMPLEMENTATION")
        rows.append(
            {
                "grid_geography": geography,
                "conventional_sector": sector,
                "economic_exposure_family_id": family_id,
                "audit_outcome": status,
                "valid_return_observations": count,
                "first_valid_date": cov.loc[family_id, "first_valid_date"] if exists else pd.NaT,
                "A2R_new_family": "YES" if family_id in NEW_FAMILY_DEFINITIONS else "NO",
                "proxy_used": "NO",
                "synthetic_symmetry_created": "NO",
                "warning": WARNING,
            }
        )
    return pd.DataFrame(rows)


def regenerate_a3r0_structures(
    master: pd.DataFrame,
    coverage: pd.DataFrame,
    panel: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    policy = json.loads(A3R0_POLICY_PATH.read_text(encoding="utf-8"))
    policy["run_id"] = RUN_ID
    policy["authoritative_family_count"] = len(master)
    policy["material_A2_lineage_failures"] = {}
    policy["dynamic_admission"]["signal_sessions"] = HORIZONS
    a3r0.PARENT_MAP.update(
        {
            "EUROPE_CONSUMER_DISCRETIONARY": ("EUROPE_BROAD", "NOT_APPLICABLE"),
            "EUROPE_COMMUNICATION_SERVICES": ("EUROPE_BROAD", "NOT_APPLICABLE"),
            "EUROPE_REAL_ESTATE": ("EUROPE_BROAD", "NOT_APPLICABLE"),
            "GLOBAL_CONSUMER_DISCRETIONARY": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
            "GLOBAL_CONSUMER_STAPLES": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
            "GLOBAL_COMMUNICATION_SERVICES": ("GLOBAL_DEVELOPED_WORLD", "NOT_APPLICABLE"),
            "US_AEROSPACE_DEFENCE": ("GLOBAL_INDUSTRIALS", "US_BROAD_LARGE_CAP"),
        }
    )
    role, dynamic = a3r0.build_role_and_dynamic(master, coverage, panel, policy)
    correction_ids = set(FAMILY_DEFINITIONS)
    added_ids = set(NEW_FAMILY_DEFINITIONS)
    for frame in [role, dynamic]:
        frame.loc[frame["economic_exposure_family_id"].isin(correction_ids) & frame["research_data_ready_flag"].eq("YES"), "a2_lineage_validation_status"] = "PASS_A2R_REMEDIATED"
        frame.loc[frame["economic_exposure_family_id"].isin(correction_ids) & frame["research_data_ready_flag"].eq("YES"), "a2_lineage_issue"] = "CLOSED_BY_UKACTIVE_A2R"
        frame.loc[frame["economic_exposure_family_id"].eq("GLOBAL_BANKS"), "a2_lineage_validation_status"] = "NO_VALID_IMPLEMENTATION_HISTORY_EXCLUDED"
        frame.loc[frame["economic_exposure_family_id"].eq("GLOBAL_BANKS"), "a2_lineage_issue"] = "NO_EXACT_GLOBAL_BANKS_IMPLEMENTATION_HISTORY"
        frame.loc[frame["economic_exposure_family_id"].isin(added_ids) & frame["research_data_ready_flag"].eq("YES"), "a2_lineage_validation_status"] = "PASS_A2R_SECTOR_GRID_ADDITION"
        frame.loc[frame["economic_exposure_family_id"].isin(added_ids) & frame["research_data_ready_flag"].eq("YES"), "a2_lineage_issue"] = "NOT_APPLICABLE"
    pools = a3r0.build_pool_master(role)
    parent_child, parent_benchmark = a3r0.build_parent_maps(role)
    overlaps = a3r0.build_overlap(role)
    benchmark = a3r0.build_benchmark_map(role, coverage, policy)
    dynamic_dates = dynamic[["economic_exposure_family_id", *[f"earliest_valid_{h}_session_signal_date" for h in HORIZONS]]]
    selectable = role[role["selectable_flag"].eq("YES")].merge(dynamic_dates, on="economic_exposure_family_id", how="left", validate="one_to_one")
    return {
        "role": role,
        "dynamic": dynamic,
        "pools": pools,
        "parent_child": parent_child,
        "overlaps": overlaps,
        "benchmark": benchmark,
        "parent_benchmark": parent_benchmark,
        "selectable": selectable,
    }


PREFERRED_TICKERS = {
    "AUSTRALIA": "AUAD", "CHINA_BROAD": "HCHS", "EUROPE_ENERGY": "ENGE", "EUROPE_FINANCIALS": "FNCE", "EUROPE_HEALTHCARE": "HEAE",
    "EUROPE_INDUSTRIALS": "NDUS", "EUROPE_MATERIALS": "MTRL", "EUROPE_TECHNOLOGY": "ITEC", "EUROPE_UTILITIES": "UTIL",
    "GLOBAL_HEALTHCARE": "HEAW", "GLOBAL_INFRASTRUCTURE": "INFR", "GLOBAL_TECHNOLOGY": "TECW", "US_AEROSPACE_DEFENCE": "SEAL",
    "EUROPE_CONSUMER_DISCRETIONARY": "CDCE", "EUROPE_COMMUNICATION_SERVICES": "TELE", "EUROPE_REAL_ESTATE": "XDER",
    "GLOBAL_CONSUMER_DISCRETIONARY": "WCOD", "GLOBAL_CONSUMER_STAPLES": "WCOS", "GLOBAL_COMMUNICATION_SERVICES": "WTEL",
}


def build_changed_current_lines(
    routes: pd.DataFrame,
    engine: dict[str, Any],
    role: pd.DataFrame,
) -> pd.DataFrame:
    role_idx = role.set_index("economic_exposure_family_id")
    validation = engine["validations"].set_index("listing_id")
    rows: list[dict[str, Any]] = []
    for family_id in sorted(set(FAMILY_DEFINITIONS) | set(NEW_FAMILY_DEFINITIONS)):
        if family_id == "GLOBAL_BANKS" or family_id not in role_idx.index or role_idx.loc[family_id, "selectable_flag"] != "YES":
            continue
        candidates = routes[
            routes["economic_exposure_family_id"].eq(family_id)
            & ~routes["historical_listing_extension"].astype(bool)
        ].copy()
        candidates["validation_status"] = candidates["listing_id"].map(validation["total_return_validation_status"]).fillna("FAIL_NO_VALIDATION")
        candidates = candidates[~candidates["validation_status"].str.startswith("FAIL")]
        candidates["valid_history_rows"] = candidates["listing_id"].map(
            {key: int(frame["data_valid"].astype(bool).sum()) for key, frame in engine["listing_frames"].items()}
        ).fillna(0)
        candidates = candidates[candidates["valid_history_rows"].gt(0)].copy()
        preferred_ticker = PREFERRED_TICKERS.get(family_id, "")
        candidates["preferred_priority"] = np.where(candidates["ticker"].eq(preferred_ticker), 0, 1)
        candidates["gbp_priority"] = np.where(candidates["effective_price_unit"].isin(["GBP", "GBX"]), 0, 1)
        candidates = candidates.sort_values(["preferred_priority", "gbp_priority", "valid_history_rows", "listing_id"], ascending=[True, True, False, True])
        candidates = candidates.head(2)
        for position, candidate in enumerate(candidates.itertuples(index=False)):
            source_url = OFFICIAL_SOURCES.get(clean(candidate.source_key), clean(candidate.kid_retail_document_evidence))
            public_isa = clean(getattr(candidate, "public_isa_rules_status", "UNCERTAIN"), "UNCERTAIN")
            if public_isa not in {"RULES_ELIGIBLE", "RULES_NOT_ELIGIBLE", "UNCERTAIN"}:
                public_isa = "RULES_ELIGIBLE" if public_isa in {"ELIGIBLE", "YES"} else "UNCERTAIN"
            role_row = role_idx.loc[family_id]
            rows.append(
                {
                    "economic_exposure_family_id": family_id,
                    "economic_exposure_name": role_row["economic_exposure_name"],
                    "primary_rotation_role": role_row["primary_rotation_role"],
                    "rotation_pool_id": role_row["rotation_pool_id"],
                    "primary_competition_pool_id": role_row["primary_competition_pool_id"],
                    "parent_exposure_family_id": role_row["parent_exposure_family_id"],
                    "preferred_or_alternate": "PREFERRED" if position == 0 else "ALTERNATE",
                    "fund_entity_id": candidate.fund_entity_id,
                    "share_class_id": candidate.share_class_id,
                    "listing_id": candidate.listing_id,
                    "isin": candidate.isin,
                    "ticker": candidate.ticker,
                    "exchange": candidate.exchange,
                    "mic": candidate.mic,
                    "listing_currency": candidate.effective_listing_currency,
                    "price_unit": candidate.effective_price_unit,
                    "provider_issuer": candidate.provider_issuer,
                    "share_class_name": candidate.legal_fund_name,
                    "product_structure": candidate.product_structure,
                    "instrument_type": candidate.instrument_type,
                    "ucits_status": candidate.ucits_status,
                    "ucits_evidence_basis": source_url,
                    "current_investability_state": candidate.current_investability_state,
                    "LSE_current_status": "CONFIRMED",
                    "UK_retail_disclosure_status": "CURRENT_DISCLOSURE_CONFIRMED" if source_url not in {"NOT_AVAILABLE", ""} else "UNCERTAIN",
                    "public_ISA_rules_status": public_isa,
                    "public_evidence_URLs": source_url,
                    "public_evidence_date": OBSERVATION_DATE,
                    "public_evidence_confidence": "HIGH_PRIMARY_ISSUER_AND_EXACT_ACTIVE_CATALOGUE",
                    "implementation_selection_reason": "EXACT_ECONOMIC_FINGERPRINT|CURRENT_XLON|GBP_GBX_FIRST|VALID_A2R_HISTORY|STABLE_TIEBREAK",
                    "economic_lineage_valid": "YES",
                    "warning": WARNING,
                }
            )
    return pd.DataFrame(rows)


def build_post_a2r_queue(
    changed_lines: pd.DataFrame,
    role: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    original_lines = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R0_CURRENT_IMPLEMENTATION_LINES.csv", dtype=str, keep_default_na=False)
    changed_ids = set(FAMILY_DEFINITIONS) | set(NEW_FAMILY_DEFINITIONS)
    unaffected_lines = original_lines[~original_lines["economic_exposure_family_id"].isin(changed_ids)].copy()
    all_lines = pd.concat([unaffected_lines, changed_lines], ignore_index=True, sort=False)
    selectable_ids = set(role.loc[role["selectable_flag"].eq("YES"), "economic_exposure_family_id"])
    all_lines = all_lines[all_lines["economic_exposure_family_id"].isin(selectable_ids)].copy()
    all_lines = all_lines.sort_values(["economic_exposure_family_id", "preferred_or_alternate", "listing_id"]).reset_index(drop=True)
    queue_rows: list[dict[str, Any]] = []
    for line in all_lines.itertuples(index=False):
        queue_rows.append(
            {
                "economic_exposure_family_id": line.economic_exposure_family_id,
                "economic_exposure_name": line.economic_exposure_name,
                "rotation_role": line.primary_rotation_role,
                "competition_pool": line.primary_competition_pool_id,
                "parent_exposure": line.parent_exposure_family_id,
                "preferred_or_alternate": line.preferred_or_alternate,
                "ISIN": line.isin,
                "ticker": line.ticker,
                "expected_exchange": line.exchange,
                "expected_MIC": line.mic,
                "listing_currency": line.listing_currency,
                "GBP_GBX_unit": line.price_unit,
                "issuer": line.provider_issuer,
                "structure": line.product_structure,
                "LSE_current_status": line.LSE_current_status,
                "UK_retail_disclosure_status": line.UK_retail_disclosure_status,
                "public_ISA_rules_status": line.public_ISA_rules_status,
                "public_evidence_URLs": line.public_evidence_URLs,
                "public_evidence_date": line.public_evidence_date,
                "public_evidence_confidence": line.public_evidence_confidence,
                "IBKR_contract_status": "NOT_CHECKED",
                "IBKR_contract_id": "NOT_CHECKED",
                "IBKR_exchange_found": "NOT_CHECKED",
                "IBKR_symbol_found": "NOT_CHECKED",
                "IBKR_quote_status": "NOT_CHECKED",
                "IBKR_ISA_purchase_status": "NOT_CHECKED",
                "verification_notes": "A2R corrected economic lineage; public evidence is not account-specific broker confirmation",
                "listing_id": line.listing_id,
                "share_class_id": line.share_class_id,
                "selectable_flag": "YES",
                "benchmark_only_flag": "NO",
                "warning": WARNING,
            }
        )
    queue = pd.DataFrame(queue_rows)
    public_columns = [
        "economic_exposure_family_id", "economic_exposure_name", "preferred_or_alternate", "isin", "ticker", "exchange", "mic", "listing_currency", "price_unit",
        "instrument_type", "product_structure", "ucits_status", "LSE_current_status", "UK_retail_disclosure_status", "public_ISA_rules_status", "current_investability_state",
        "public_evidence_URLs", "public_evidence_date", "public_evidence_confidence", "warning",
    ]
    public = all_lines[[column for column in public_columns if column in all_lines]].copy()
    public["current_eligibility_not_historical"] = "YES"
    return all_lines, queue, public


def build_manual_validation_cases(
    panel: pd.DataFrame,
    routes: pd.DataFrame,
    engine: dict[str, Any],
    corrections: pd.DataFrame,
) -> tuple[pd.DataFrame, str]:
    route_idx = routes.set_index("listing_id", drop=False)
    correction_idx = corrections.set_index("economic_exposure_family_id")
    rows: list[dict[str, Any]] = []
    for family_id in FAMILY_DEFINITIONS:
        corr = correction_idx.loc[family_id]
        g = panel[panel["economic_exposure_family_id"].eq(family_id)].sort_values("date")
        mask = valid_mask(g)
        if not mask.any():
            rows.append(
                {
                    "case_id": f"A2R-MAN-{len(rows)+1:02d}",
                    "economic_exposure_family_id": family_id,
                    "intended_definition": intended_fingerprint(family_id).key,
                    "old_A2_implementation": OLD_ACTUAL_FINGERPRINTS[family_id].key,
                    "old_result_and_reason": f"FAIL|{OLD_DEFECTS[family_id]}",
                    "replacement_implementation_or_state": "NO_VALID_IMPLEMENTATION_HISTORY",
                    "identity_evidence": "A0A1 registry and evidence ledger exhausted; no exact global-banks implementation established",
                    "corrected_first_valid_date": "NOT_APPLICABLE",
                    "sample_date": "NOT_APPLICABLE",
                    "sample_stored_return_gbp_total": np.nan,
                    "sample_independent_reconstruction": np.nan,
                    "sample_absolute_error": np.nan,
                    "distribution_event_validation": "NOT_APPLICABLE_EXCLUDED",
                    "fx_validation": "NOT_APPLICABLE_EXCLUDED",
                    "A2_automated_validation_result": "PASS_EXCLUDED_BECAUSE_NO_VALID_HISTORY",
                    "manual_case_status": "PASS",
                    "warning": WARNING,
                }
            )
            continue
        sample = g.loc[mask].iloc[0]
        listing_id = sample["implementation_listing_id"]
        route = route_idx.loc[listing_id]
        frame = engine["listing_frames"][listing_id].sort_values("date")
        sample_date = pd.Timestamp(sample["date"])
        loc = frame.index[frame["date"].eq(sample_date)]
        independent = np.nan
        if len(loc):
            pos = frame.index.get_loc(loc[0])
            if isinstance(pos, (int, np.integer)) and pos > 0:
                current = float(frame.iloc[pos]["adjusted_wealth_gbp"])
                prior = float(frame.iloc[pos - 1]["adjusted_wealth_gbp"])
                independent = current / prior - 1.0
        stored = float(sample["return_gbp_total"])
        error = abs(stored - independent) if np.isfinite(independent) else np.nan
        family_events = engine["events"][engine["events"]["economic_exposure_family_id"].eq(family_id)] if not engine["events"].empty else pd.DataFrame()
        event_status = semicolon(family_events["validation_status"]) if not family_events.empty else ("ZERO_REPORTED_DISTRIBUTIONS_ACCUMULATING" if route.accumulating_distributing == "ACCUMULATING" else "NO_EVENT_AVAILABLE_VENDOR_SEMANTICS_VALIDATED")
        fx_status = "NOT_REQUIRED_GBP_OR_GBX_LISTING" if route.effective_price_unit in {"GBP", "GBX"} else "GBP_CONVERSION_APPLIED_ONCE_ECB_RATE_NO_LATER_THAN_DATE"
        rows.append(
            {
                "case_id": f"A2R-MAN-{len(rows)+1:02d}",
                "economic_exposure_family_id": family_id,
                "intended_definition": intended_fingerprint(family_id).key,
                "old_A2_implementation": OLD_ACTUAL_FINGERPRINTS[family_id].key,
                "old_result_and_reason": f"FAIL|{OLD_DEFECTS[family_id]}",
                "replacement_implementation_or_state": f"{route['isin']}|{route['ticker']}|{corr.remediation_outcome_state}",
                "identity_evidence": f"{OFFICIAL_SOURCES.get(clean(route.source_key), 'A0A1_AND_A2_EXACT_IDENTITY_LINEAGE')}|{clean(route.historical_objective_lineage)}|{clean(route.semantic_tolerance_basis)}",
                "corrected_first_valid_date": corr.corrected_first_valid_return_date,
                "sample_date": sample_date,
                "sample_stored_return_gbp_total": stored,
                "sample_independent_reconstruction": independent,
                "sample_absolute_error": error,
                "distribution_event_validation": event_status,
                "fx_validation": fx_status,
                "A2_automated_validation_result": route_idx.loc[listing_id].get("total_return_validation_status", engine["validations"].set_index("listing_id").loc[listing_id, "total_return_validation_status"]),
                "manual_case_status": "PASS" if np.isfinite(error) and error <= 1e-12 else "FAIL",
                "warning": WARNING,
            }
        )
    cases = pd.DataFrame(rows)
    markdown = [
        "# UKACTIVE-A2R manual validation cases",
        "",
        "These 14 cases validate economic identity first and then reconstruct one stored GBP total return from the selected route's adjusted GBP wealth. They are data checks, not performance results.",
        "",
        WARNING,
        "",
        f"Completed cases: **{len(cases)}/14**. Passed: **{int(cases['manual_case_status'].eq('PASS').sum())}/14**.",
        "",
    ]
    for case in cases.itertuples(index=False):
        markdown.extend(
            [
                f"## {case.case_id} — {case.economic_exposure_family_id}",
                "",
                f"Intended economic definition → `{case.intended_definition}`",
                "",
                f"Old A2 implementation → `{case.old_A2_implementation}`",
                "",
                f"Old result → {case.old_result_and_reason}",
                "",
                f"Replacement/state → `{case.replacement_implementation_or_state}`",
                "",
                f"Identity evidence → {case.identity_evidence}",
                "",
                f"Corrected first valid date → {case.corrected_first_valid_date}",
                "",
                f"Sample check → date `{case.sample_date}`; stored `{case.sample_stored_return_gbp_total}`; independently reconstructed `{case.sample_independent_reconstruction}`; absolute error `{case.sample_absolute_error}`.",
                "",
                f"Distribution check → {case.distribution_event_validation}",
                "",
                f"FX/GBP check → {case.fx_validation}",
                "",
                f"A2 validation → {case.A2_automated_validation_result}; manual status → **{case.manual_case_status}**.",
                "",
            ]
        )
    return cases, "\n".join(markdown) + "\n"


def capture_primary_sources(refresh: bool = False) -> pd.DataFrame:
    source_dir = A2R_SOURCE_ROOT / "primary"
    source_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "UKACTIVE-A2R-research/1.0 primary-source audit"})
    rows: list[dict[str, Any]] = []
    for source_key, url in OFFICIAL_SOURCES.items():
        safe = "".join(character if character.isalnum() or character in "-_" else "_" for character in source_key)
        capture = source_dir / f"{safe}.bin.gz"
        meta_path = capture.with_suffix(capture.suffix + ".meta.json")
        raw = b""
        status = "NOT_RETRIEVED"
        http_status: int | str = "NOT_AVAILABLE"
        content_type = "NOT_AVAILABLE"
        retrieved = now_utc()
        error = "NOT_APPLICABLE"
        if capture.exists() and meta_path.exists() and not refresh:
            with gzip.open(capture, "rb") as handle:
                raw = handle.read()
            prior = json.loads(meta_path.read_text(encoding="utf-8"))
            status = "REUSED_IMMUTABLE_A2R_CAPTURE"
            http_status = prior.get("http_status", "NOT_AVAILABLE")
            content_type = prior.get("content_type", "NOT_AVAILABLE")
            retrieved = prior.get("retrieval_timestamp_utc", retrieved)
            error = prior.get("error", "NOT_APPLICABLE")
        else:
            try:
                response = session.get(url, timeout=45, allow_redirects=True)
                http_status = response.status_code
                content_type = response.headers.get("content-type", "NOT_AVAILABLE")
                if response.status_code == 200 and response.content:
                    raw = response.content
                    with gzip.open(capture, "wb", compresslevel=9) as handle:
                        handle.write(raw)
                    status = "RETRIEVED_LIVE_READ_ONLY"
                else:
                    status = f"URL_RECORDED_HTTP_{response.status_code}"
                    error = f"HTTP_{response.status_code}"
            except requests.RequestException as exc:
                status = "URL_RECORDED_RETRIEVAL_UNAVAILABLE"
                error = f"{type(exc).__name__}:{exc}"
        raw_sha = hashlib.sha256(raw).hexdigest() if raw else "NOT_AVAILABLE"
        meta = {
            "evidence_id": stable_id("A2REVD", source_key, url, raw_sha),
            "source": "PRIMARY_OFFICIAL",
            "source_key": source_key,
            "source_url": url,
            "retrieval_timestamp_utc": retrieved,
            "http_status": http_status,
            "content_type": content_type,
            "retrieval_status": status,
            "raw_response_sha256": raw_sha,
            "capture_path": str(capture) if raw else "NOT_AVAILABLE",
            "capture_sha256": sha256_file(capture) if capture.exists() else "NOT_AVAILABLE",
            "error": error,
            "historical_eligibility_supported": "NO_UNLESS_DOCUMENT_ITSELF_IS_DATED_HISTORICAL_EVIDENCE",
            "warning": WARNING,
        }
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        rows.append(meta)
    return pd.DataFrame(rows)


def build_automated_tests(
    routes: pd.DataFrame,
    engine: dict[str, Any],
    original: pd.DataFrame,
    corrected: pd.DataFrame,
    before_after: pd.DataFrame,
    route_audit: pd.DataFrame,
    dynamic: pd.DataFrame,
    manual_cases: pd.DataFrame,
) -> pd.DataFrame:
    tests: list[dict[str, Any]] = []
    add = lambda test_id, description, passed, observed, category, critical=True: tests.append(make_test_row(test_id, description, passed, observed, category, critical))
    instrument = engine["instrument"]
    pit = engine["pit"]
    canonical = engine["canonical"]
    gbx = routes[routes["effective_price_unit"].eq("GBX")]
    foreign_ids = set(routes.loc[~routes["effective_price_unit"].isin(["GBP", "GBX"]), "listing_id"])
    foreign = instrument[instrument["listing_id"].isin(foreign_ids)]
    selected_ids = set(corrected.loc[corrected["implementation_listing_id"].notna(), "implementation_listing_id"].astype(str))
    failed_route_ids = set(engine["validations"].loc[engine["validations"]["total_return_validation_status"].astype(str).str.startswith("FAIL"), "listing_id"])
    add("A2R-REAL-001", "No corrected instrument return is valid before evidenced inception", not bool((instrument["price_before_inception_flag"].astype(bool) & instrument["data_valid"].astype(bool)).any()), int((instrument["price_before_inception_flag"].astype(bool) & instrument["data_valid"].astype(bool)).sum()), "A2_REGRESSION")
    add("A2R-REAL-002", "Every GBX route uses a 0.01 multiplier", bool((pd.to_numeric(gbx["price_unit_multiplier_to_listing_currency_effective"]) == 0.01).all()), semicolon(gbx["price_unit_multiplier_to_listing_currency_effective"]), "GBP_GBX")
    add("A2R-REAL-003", "Foreign-currency valid returns always have an FX observation", not bool((foreign["data_valid"].astype(bool) & foreign["fx_rate_gbp_per_local"].isna()).any()), int((foreign["data_valid"].astype(bool) & foreign["fx_rate_gbp_per_local"].isna()).sum()), "FX")
    fx_formula_error = (foreign["adjusted_wealth_gbp"] - foreign["adjusted_price_listing_currency"] * foreign["fx_rate_gbp_per_local"]).abs().dropna()
    add("A2R-REAL-004", "GBP wealth applies foreign FX exactly once", bool(fx_formula_error.empty or fx_formula_error.max() <= 1e-12), float(fx_formula_error.max()) if len(fx_formula_error) else 0.0, "FX")
    add("A2R-REAL-005", "Stale observations never become valid returns", not bool((instrument["stale_flag"].astype(bool) & instrument["data_valid"].astype(bool)).any()), int((instrument["stale_flag"].astype(bool) & instrument["data_valid"].astype(bool)).sum()), "STALE_MISSING")
    historical_values = set(pit["historical_investability_state"].astype(str))
    add("A2R-REAL-006", "Current eligibility labels are not back-projected historically", not bool(historical_values & {"CURRENTLY_INVESTABLE", "CURRENT_CANDIDATE_UNVERIFIED"}), semicolon(historical_values), "HISTORICAL_ELIGIBILITY")
    add("A2R-REAL-007", "Canonical implementation selection uses strictly prior-session information", bool((pd.to_datetime(canonical["date"]) > pd.to_datetime(canonical["signal_information_date"])).all()), int(len(canonical)), "LOOKAHEAD")
    add("A2R-REAL-008", "Corrected panel has one economic-family observation per date", not corrected.duplicated(["economic_exposure_family_id", "date"]).any(), int(corrected.duplicated(["economic_exposure_family_id", "date"]).sum()), "DUPLICATION")
    add("A2R-REAL-009", "No proxy history enters corrected implementation panel", not corrected["proxy_flag"].astype(bool).any(), int(corrected["proxy_flag"].astype(bool).sum()), "PROXY")
    us = corrected[corrected["economic_exposure_family_id"].eq("US_AEROSPACE_DEFENCE")]
    us_early = us[(pd.to_datetime(us["date"]) < pd.Timestamp("2026-07-16")) & us["data_valid"].astype(bool)]
    add("A2R-REAL-010", "US defence history is not valid before the dated strategy change", us_early.empty, len(us_early), "OBJECTIVE_DATE")
    banks = corrected[corrected["economic_exposure_family_id"].eq("GLOBAL_BANKS")]
    add("A2R-REAL-011", "Global banks has no silently retained regional or bond history", int(valid_mask(banks).sum()) == 0, int(valid_mask(banks).sum()), "SEMANTIC_LINEAGE")
    add("A2R-REAL-012", "Failed A2 validation routes cannot be selected", not bool(selected_ids & failed_route_ids), semicolon(selected_ids & failed_route_ids), "A2_VALIDATION")
    unaffected = before_after[before_after["audit_scope"].eq("UNAFFECTED_REGRESSION_CONTROL")]
    add("A2R-REAL-013", "All unaffected economic histories are return-identical", bool(unaffected["audit_result"].eq("RETURN_IDENTICAL").all()), unaffected["audit_result"].value_counts().to_dict(), "REGRESSION")
    original_a2_tests = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A2_AUTOMATED_TEST_RESULTS.csv")
    original_critical_pass = original_a2_tests.loc[original_a2_tests["critical"].astype(bool), "status"].eq("PASS").all()
    add("A2R-REAL-014", "All original A2 critical correctness tests remain passed", bool(original_critical_pass), original_a2_tests["status"].value_counts().to_dict(), "A2_REGRESSION")
    add("A2R-REAL-015", "Every admitted remediation route matches its frozen semantic fingerprint", route_audit["semantic_match"].eq("PASS").all(), route_audit["semantic_match"].value_counts().to_dict(), "SEMANTIC_LINEAGE")
    add("A2R-REAL-016", "Every canonical row preserves explicit share-class and listing identity", canonical["selected_share_class_id"].notna().all() and canonical["selected_listing_id"].notna().all(), int(len(canonical)), "IDENTITY")
    add("A2R-REAL-017", "Dynamic admission does not impose a 504-session gate on 21-session research", bool(((dynamic["valid_return_observations"].between(21, 503)) & dynamic["eligible_21_session_research"].eq("YES")).any()), int(((dynamic["valid_return_observations"].between(21, 503)) & dynamic["eligible_21_session_research"].eq("YES")).sum()), "DYNAMIC_ADMISSION")
    for horizon in HORIZONS:
        eligible = dynamic[dynamic[f"eligible_{horizon}_session_research"].eq("YES")]
        add(f"A2R-REAL-W{horizon}", f"No family is admitted before {horizon} valid observations", bool((eligible["valid_return_observations"] >= horizon).all()), int(len(eligible)), "DYNAMIC_ADMISSION")
    add("A2R-REAL-018", "All 14 manual cases are complete and pass", len(manual_cases) == 14 and manual_cases["manual_case_status"].eq("PASS").all(), manual_cases["manual_case_status"].value_counts().to_dict(), "MANUAL_VALIDATION")
    add("A2R-REAL-019", "Broker availability remains NOT_CHECKED", routes["broker_status"].astype(str).eq("NOT_CHECKED").all(), routes["broker_status"].value_counts().to_dict(), "BROKER", False)
    add("A2R-REAL-020", "Long-only structural exclusions cannot enter corrected routes", routes["long_only_structure_valid"].astype(bool).all(), int((~routes["long_only_structure_valid"].astype(bool)).sum()), "STRUCTURE")
    events = engine["events"]
    add("A2R-REAL-021", "No selected distribution route has a failed explicit reconstruction", not bool((events.get("validation_status", pd.Series(dtype=str)).eq("FAIL") & events.get("listing_id", pd.Series(dtype=str)).isin(selected_ids)).any()) if not events.empty else True, int((events.get("validation_status", pd.Series(dtype=str)).eq("FAIL") & events.get("listing_id", pd.Series(dtype=str)).isin(selected_ids)).sum()) if not events.empty else 0, "DISTRIBUTIONS")
    add("A2R-REAL-022", "All valid corrected returns are finite", np.isfinite(pd.to_numeric(corrected.loc[valid_mask(corrected), "return_gbp_total"], errors="coerce")).all(), int(valid_mask(corrected).sum()), "TOTAL_RETURN")
    return pd.DataFrame(tests)


def build_semantic_tests(
    route_audit: pd.DataFrame,
    routes: pd.DataFrame,
    corrected: pd.DataFrame,
) -> pd.DataFrame:
    tests = synthetic_semantic_fixture_results()
    add = lambda test_id, description, passed, observed, category="REAL_SEMANTIC": tests.append(make_test_row(test_id, description, passed, observed, category, True))
    europe = route_audit[route_audit["economic_exposure_family_id"].str.startswith("EUROPE_")]
    global_routes = route_audit[route_audit["economic_exposure_family_id"].str.startswith("GLOBAL_")]
    us = route_audit[route_audit["economic_exposure_family_id"].eq("US_AEROSPACE_DEFENCE")]
    china = route_audit[route_audit["economic_exposure_family_id"].eq("CHINA_BROAD")]
    australia = route_audit[route_audit["economic_exposure_family_id"].eq("AUSTRALIA")]
    add("A2R-SEM-001", "US-specific family uses only United States objective history", us["actual_fingerprint"].str.startswith("UNITED_STATES ×").all(), semicolon(us["actual_fingerprint"]))
    add("A2R-SEM-002", "European sector routes use only Europe fingerprints", europe["actual_fingerprint"].str.startswith("EUROPE ×").all(), int(len(europe)))
    add("A2R-SEM-003", "Global sector/theme routes use only global fingerprints", global_routes["actual_fingerprint"].str.startswith("GLOBAL ×").all(), int(len(global_routes)))
    add("A2R-SEM-004", "Broad China is neither China Internet nor China A-shares", ~china["actual_fingerprint"].str.contains("INTERNET|A_SHARES|CHINA_A", regex=True).any(), semicolon(china["actual_fingerprint"]))
    add("A2R-SEM-005", "Australia route is broad Australia and unhedged", australia["actual_fingerprint"].str.contains("AUSTRALIA × BROAD_MARKET").all() and australia["actual_fingerprint"].str.contains("UNHEDGED").all(), semicolon(australia["actual_fingerprint"]))
    add("A2R-SEM-006", "All admitted routes pass complete five-dimensional fingerprint matching", route_audit["semantic_match"].eq("PASS").all(), route_audit["semantic_match"].value_counts().to_dict())
    add("A2R-SEM-007", "Different ISIN implementation histories retain explicit listing identities", corrected.loc[corrected["data_valid"].astype(bool), "implementation_listing_id"].ne("NOT_AVAILABLE_NO_SELECTION").all(), int(corrected["implementation_listing_id"].nunique()))
    add("A2R-SEM-008", "No corrected row is labelled proxy history", not corrected["proxy_flag"].astype(bool).any(), int(corrected["proxy_flag"].astype(bool).sum()))
    invalid_pairs = {
        ("AUSTRALIA", "IE00BXDZNQ90"), ("CHINA_BROAD", "FR0011720911"), ("CHINA_BROAD", "IE00BKFB6K94"),
        ("EUROPE_ENERGY", "IE00BYTRR863"), ("EUROPE_FINANCIALS", "IE00BYTRR970"), ("EUROPE_HEALTHCARE", "IE00BYTRRB94"),
        ("EUROPE_INDUSTRIALS", "IE00BYTRRC02"), ("EUROPE_MATERIALS", "IE00BYTRRF33"), ("EUROPE_TECHNOLOGY", "IE00BYTRRD19"),
        ("EUROPE_UTILITIES", "IE00BYTRRH56"), ("GLOBAL_BANKS", "IE00B5MTWD60"), ("GLOBAL_INFRASTRUCTURE", "IE00BLCHJ641"),
        ("GLOBAL_INFRASTRUCTURE", "IE000AFVONT7"), ("GLOBAL_HEALTHCARE", "IE00BYZK4776"), ("GLOBAL_TECHNOLOGY", "IE00BYZK4883"),
        ("US_AEROSPACE_DEFENCE", "IE000U9ODG19"),
    }
    admitted_pairs = set(zip(routes["economic_exposure_family_id"], routes["isin"]))
    add("A2R-SEM-009", "Known invalid old family/ISIN mappings are absent from corrected remediation routes", not bool(invalid_pairs & admitted_pairs), semicolon(f"{f}|{i}" for f, i in invalid_pairs & admitted_pairs))
    retained_old = [row.economic_exposure_family_id for row in route_audit.itertuples(index=False) if row.economic_exposure_family_id in OLD_ACTUAL_FINGERPRINTS and row.actual_fingerprint == OLD_ACTUAL_FINGERPRINTS[row.economic_exposure_family_id].key]
    add("A2R-SEM-010", "Corrected family never retains its own old invalid fingerprint", not retained_old, semicolon(retained_old))
    return pd.DataFrame(tests)


def new_product_candidates(engine: dict[str, Any]) -> pd.DataFrame:
    validation = engine["validations"].set_index("listing_id")
    infra_routes = [
        route for route in NEW_ROUTE_SPECS
        if route["economic_exposure_family_id"] == "GLOBAL_INFRASTRUCTURE"
    ]
    valid = all(
        not str(validation.loc[stable_id("A2RLIST", route["isin"], route["ticker"], "XLON"), "total_return_validation_status"]).startswith("FAIL")
        for route in infra_routes
    )
    return pd.DataFrame(
        [
            {
                "candidate_id": "A2R_NEW_PRODUCT_CANDIDATE-001",
                "economic_exposure_family_id": "GLOBAL_INFRASTRUCTURE",
                "product_name": "iShares Global Infrastructure UCITS ETF USD Dist",
                "isin": "IE00B1FZS467",
                "tickers": "INFR;IDIN",
                "registry_presence": "NOT_IN_ORIGINAL_A0A1_DISCOVERY_REGISTRY",
                "identity_evidence_status": "PASS_EXACT_ISIN_PRIMARY_ISSUER_AND_CURRENT_CATALOGUE",
                "economic_fingerprint_status": "PASS_GLOBAL_LISTED_INFRASTRUCTURE",
                "A2_return_validation_status": "PASS" if valid else "FAIL",
                "disposition": "ADMITTED_AFTER_FULL_A0A1_EQUIVALENT_IDENTITY_EVIDENCE_AND_A2_VALIDATION" if valid else "NOT_ADMITTED_A2_VALIDATION_FAILURE",
                "source_urls": f"{OFFICIAL_SOURCES['ISHARES_GLOBAL_INFRASTRUCTURE']};{OFFICIAL_SOURCES['ISHARES_GLOBAL_INFRASTRUCTURE_FACTSHEET']}",
                "retrieval_date": OBSERVATION_DATE,
                "historical_eligibility_supported": "NO",
                "warning": WARNING,
            }
        ]
    )


def build_unresolved_items(source_captures: pd.DataFrame, decision_gate: bool) -> pd.DataFrame:
    rows = [
        {
            "item_id": "A2R-OPEN-001", "category": "HISTORICAL_ELIGIBILITY", "economic_exposure_family_id": "ALL", "description": "Historical UK retail/ISA/SIPP eligibility remains unresolved and was not back-projected from current evidence.", "severity": "NON_BLOCKING_FOR_SIGNAL_RESEARCH", "status": "OPEN", "required_before": "HISTORICALLY_INVESTABLE_OR_DEPLOYMENT_CLAIM", "blocking_A3R1": "NO", "warning": WARNING,
        },
        {
            "item_id": "A2R-OPEN-002", "category": "BROKER", "economic_exposure_family_id": "ALL", "description": "IBKR contract, LSE-line and account-specific ISA purchase states remain NOT_CHECKED.", "severity": "NON_BLOCKING_FOR_SCIENTIFIC_SIGNAL_RESEARCH", "status": "OPEN", "required_before": "DEPLOYMENT_CANDIDATE", "blocking_A3R1": "NO", "warning": WARNING,
        },
        {
            "item_id": "A2R-OPEN-003", "category": "NO_VALID_HISTORY", "economic_exposure_family_id": "GLOBAL_BANKS", "description": "No exact global-banks implementation history was established; the family is retained in the master but excluded until valid history exists.", "severity": "NON_BLOCKING_CORRECT_EXCLUSION", "status": "OPEN_EXCLUDED", "required_before": "GLOBAL_BANKS_RESEARCH_ADMISSION", "blocking_A3R1": "NO", "warning": WARNING,
        },
        {
            "item_id": "A2R-OPEN-004", "category": "SHORT_HISTORY", "economic_exposure_family_id": "US_AEROSPACE_DEFENCE", "description": "The exact US-defence objective is valid only from 2026-07-16 after the documented strategy change; longer-horizon admission remains unavailable until observations accrue.", "severity": "NON_BLOCKING_DYNAMIC_ADMISSION", "status": "OPEN_TIME_DEPENDENT", "required_before": "LONGER_HORIZON_RESEARCH", "blocking_A3R1": "NO", "warning": WARNING,
        },
        {
            "item_id": "A2R-OPEN-005", "category": "CATALOGUE_LABEL_LAG", "economic_exposure_family_id": "US_AEROSPACE_DEFENCE", "description": "The market-data catalogue still carries the predecessor metaverse ticker/name; official objective-change evidence and a dated semantic floor control the route. Current contract verification remains queued.", "severity": "NON_BLOCKING_WITH_DATE_FLOOR", "status": "OPEN_FOR_BROKER_VERIFICATION", "required_before": "DEPLOYMENT_CANDIDATE", "blocking_A3R1": "NO", "warning": WARNING,
        },
    ]
    failed_captures = source_captures[~source_captures["retrieval_status"].isin(["RETRIEVED_LIVE_READ_ONLY", "REUSED_IMMUTABLE_A2R_CAPTURE"])]
    if not failed_captures.empty:
        rows.append(
            {
                "item_id": "A2R-OPEN-006", "category": "SOURCE_CAPTURE", "economic_exposure_family_id": "MULTIPLE", "description": f"{len(failed_captures)} official URLs were preserved but did not yield a local live capture; classification also relies on existing A0A1 evidence and recorded official URLs.", "severity": "NON_BLOCKING_IF_IDENTITY_TESTS_PASS", "status": "OPEN", "required_before": "FUTURE_EVIDENCE_REFRESH", "blocking_A3R1": "NO" if decision_gate else "YES", "warning": WARNING,
            }
        )
    return pd.DataFrame(rows)


def write_scope_and_reports(
    decision: str,
    corrections: pd.DataFrame,
    coverage: pd.DataFrame,
    dynamic: pd.DataFrame,
    europe_grid: pd.DataFrame,
    global_grid: pd.DataFrame,
    tests: pd.DataFrame,
    semantic_tests: pd.DataFrame,
    manual_cases: pd.DataFrame,
    unresolved: pd.DataFrame,
    a3r0_reclass: str,
    a3r1_authorized: bool,
) -> None:
    scope = f"""# UKACTIVE-A2R scope and method

Decision: **{decision}**

UKACTIVE-A2R is a data-lineage and universe-remediation stage. It freezes the intended economic definition before choosing history, applies an explicit five-dimensional economic identity fingerprint, and reuses the UKACTIVE-A2 total-return engine for price identity, adjusted-price validation, distributions, GBX/GBP, FX, stale/missing, inception and prior-session implementation selection.

It does not contain strategy, signal, momentum, portfolio, optimisation or performance research. UKACTIVE-A3R1 was not executed.

## Immutable inputs

All original A0A1, A2, A3 and failed A3R0 artifacts remain untouched. Corrected outputs use the `UKACTIVE_A2R_*` namespace; regenerated rotation structures use explicit `POST_A2R` names.

## Scientific controls

- Economic definition precedes implementation selection.
- Actual implementation history only; no proxy splicing.
- US defence is date-bounded to the documented current objective.
- Signal-specific dynamic admission uses 21/42/63/126/252 valid observations.
- Current eligibility is never back-projected historically.
- Different ISIN/share-class/listing identities remain explicit.
- All unaffected A2 histories are regression-hashed.

{WARNING}
"""
    (PROGRAMME_ROOT / "UKACTIVE_A2R_SCOPE_AND_METHOD.md").write_text(scope, encoding="utf-8")

    quality = f"""# UKACTIVE-A2R data quality report

Decision: **{decision}**

- Blocking families manually reviewed: {len(manual_cases)}/14; passed: {int(manual_cases['manual_case_status'].eq('PASS').sum())}/14.
- Automated correctness tests: {int(tests['status'].eq('PASS').sum())}/{len(tests)} passed.
- Semantic-lineage tests: {int(semantic_tests['status'].eq('PASS').sum())}/{len(semantic_tests)} passed.
- Corrected families with usable history: {int(coverage[coverage['economic_exposure_family_id'].isin(FAMILY_DEFINITIONS)]['usable_history'].astype(bool).sum())}/14; GLOBAL_BANKS is deliberately unavailable rather than carrying a false regional history.
- Europe conventional sector grid: {int(europe_grid['audit_outcome'].isin(['VALID_IMPLEMENTATION_FOUND','CURRENT_PRODUCT_SHORT_HISTORY']).sum())}/11 represented without proxies.
- Global conventional sector grid: {int(global_grid['audit_outcome'].isin(['VALID_IMPLEMENTATION_FOUND','CURRENT_PRODUCT_SHORT_HISTORY']).sum())}/11 represented without proxies.
- Historical eligibility: unresolved and explicitly represented.
- Broker status: NOT_CHECKED.

No proxy history is present. No strategy or performance statistic was calculated.

{WARNING}
"""
    (PROGRAMME_ROOT / "UKACTIVE_A2R_DATA_QUALITY_REPORT.md").write_text(quality, encoding="utf-8")

    regen = f"""# UKACTIVE-A2R A3R0 regeneration report

The failed A3R0 artifacts remain immutable. Post-A2R rotation roles, pools, hierarchy, overlap clusters, benchmark maps, dynamic admission, selectable universe and current implementation lines were regenerated from the corrected {len(coverage)}-family master.

Proposed A3R0 reclassification: **{a3r0_reclass}**.

The public/IBKR queue was regenerated without overwriting the pre-A2R queue. Every broker field remains `NOT_CHECKED`.

No A3R1 research was executed.
"""
    (PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_REGENERATION_REPORT.md").write_text(regen, encoding="utf-8")

    readiness = f"""# UKACTIVE-A2R A3R1 readiness report

Scientific authorisation: **{'YES' if a3r1_authorized else 'NO'}**.

The corrected panel supports signal-specific admission and contains no known material economic-family/history mismatch in an admitted competition pool. GLOBAL_BANKS is retained semantically but excluded for lack of valid history; US aerospace/defence is available only at horizons whose warm-up has actually accrued.

Historical eligibility, broker availability and account-specific ISA purchase remain unresolved. Therefore any later A3R1 result would be signal research, not a historically verified UK-investable or deployment result.

UKACTIVE-A3R1 was not executed.

{WARNING}
"""
    (PROGRAMME_ROOT / "UKACTIVE_A2R_A3R1_READINESS_REPORT.md").write_text(readiness, encoding="utf-8")


def namespace_hashes() -> dict[str, str]:
    result: dict[str, str] = {}
    for pattern in ["UKACTIVE_A0A1_*", "UKACTIVE_A2_*", "UKACTIVE_A3_*", "UKACTIVE_A3R0_*"]:
        for path in PROGRAMME_ROOT.glob(pattern):
            if path.is_file() and "POST_A2R" not in path.name:
                result[path.name] = sha256_file(path)
    return dict(sorted(result.items()))


def package_versions() -> dict[str, str]:
    versions = {"python": platform.python_version(), "platform": platform.platform()}
    for package in ["pandas", "numpy", "pyarrow", "requests"]:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "NOT_INSTALLED"
    return versions


def main() -> int:
    parser = argparse.ArgumentParser(description="Build UKACTIVE-A2R economic-lineage remediation artifacts")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    started = now_utc()
    original_namespace_hashes = namespace_hashes()
    policy = json.loads(A2_POLICY_PATH.read_text(encoding="utf-8"))
    a2r_policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    policy["policy_id"] = a2r_policy["policy_id"]
    policy["warmups"] = [21, 42, 63, 126, 189, 252, 504]
    policy["a3_readiness"]["minimum_valid_observations"] = 21

    primary_captures = capture_primary_sources(args.refresh)
    active, _ = load_original_catalogues()
    master = build_corrected_exposure_master()
    routes = build_remediation_routes(active)
    route_audit = semantic_route_audit(routes)
    if not route_audit["semantic_match"].eq("PASS").all():
        raise RuntimeError(f"Semantic fingerprints failed before data retrieval: {route_audit[route_audit['semantic_match'].ne('PASS')].to_dict('records')}")
    api_key, credential_source = a2.load_api_key()
    client = LayeredCaptureClient(api_key, A2R_SOURCE_ROOT, args.refresh)
    engine = run_a2_engine(routes, master, policy, client, args.workers)
    original_panel, corrected_panel = build_full_corrected_panel(engine["panel"])
    coverage = build_coverage(master, corrected_panel)
    regenerated = regenerate_a3r0_structures(master, coverage, corrected_panel)
    dynamic = build_dynamic_eligibility(master, corrected_panel, regenerated["role"])
    blocking_definitions = build_blocking_definitions()
    fingerprints = build_fingerprint_table(routes, route_audit)
    existing_audit = build_existing_lineage_audit()
    corrections = build_lineage_corrections(routes, corrected_panel, dynamic)
    before_after = build_before_after_audit(master, original_panel, corrected_panel)
    europe_grid = build_sector_grid_audit(coverage, "EUROPE")
    global_grid = build_sector_grid_audit(coverage, "GLOBAL")
    candidates = new_product_candidates(engine)
    changed_lines = build_changed_current_lines(routes, engine, regenerated["role"])
    all_lines, queue, public = build_post_a2r_queue(changed_lines, regenerated["role"])
    manual_cases, manual_markdown = build_manual_validation_cases(corrected_panel, routes, engine, corrections)
    tests = build_automated_tests(routes, engine, original_panel, corrected_panel, before_after, route_audit, dynamic, manual_cases)
    semantic_tests = build_semantic_tests(route_audit, routes, corrected_panel)
    critical_gate = (
        tests.loc[tests["critical"].eq("YES"), "status"].eq("PASS").all()
        and semantic_tests.loc[semantic_tests["critical"].eq("YES"), "status"].eq("PASS").all()
        and len(manual_cases) == 14
        and manual_cases["manual_case_status"].eq("PASS").all()
        and before_after.loc[before_after["audit_scope"].eq("UNAFFECTED_REGRESSION_CONTROL"), "audit_result"].eq("RETURN_IDENTICAL").all()
        and corrections["remediation_outcome_state"].ne("UNRESOLVED_BLOCKING").all()
    )
    unresolved = build_unresolved_items(primary_captures, critical_gate)
    blocking_open = unresolved[unresolved["blocking_A3R1"].eq("YES")]
    decision = "UKACTIVE_A2R_PASS_WITH_OPEN_ITEMS" if critical_gate and blocking_open.empty else "UKACTIVE_A2R_FAIL"
    a3r0_reclass = "UKACTIVE_A3R0_PASS_WITH_OPEN_ITEMS" if decision != "UKACTIVE_A2R_FAIL" else "UKACTIVE_A3R0_FAIL"
    a3r1_authorized = decision in {"UKACTIVE_A2R_PASS", "UKACTIVE_A2R_PASS_WITH_OPEN_ITEMS"}

    parquet_meta = {
        "stage_id": STAGE_ID, "run_id": RUN_ID, "policy_id": a2r_policy["policy_id"], "created_at": now_utc(),
        "history_type": "LIVE_IMPLEMENTATION_HISTORY", "proxy_splicing": "NO", "warning": WARNING,
    }
    corrected_instrument = engine["instrument"].merge(
        routes[["listing_id", "actual_index_or_objective", "actual_geography", "actual_sector_or_industry", "actual_breadth_level", "actual_hedge_status", "semantic_valid_from", "historical_objective_lineage", "semantic_tolerance_basis", "source_key"]],
        on="listing_id", how="left", validate="many_to_one",
    )
    write_csv(blocking_definitions, PROGRAMME_ROOT / "UKACTIVE_A2R_BLOCKING_FAMILY_DEFINITIONS.csv")
    write_csv(fingerprints, PROGRAMME_ROOT / "UKACTIVE_A2R_ECONOMIC_IDENTITY_FINGERPRINTS.csv")
    write_csv(existing_audit, PROGRAMME_ROOT / "UKACTIVE_A2R_EXISTING_LINEAGE_AUDIT.csv")
    write_csv(corrections, PROGRAMME_ROOT / "UKACTIVE_A2R_LINEAGE_CORRECTIONS.csv")
    write_csv(europe_grid, PROGRAMME_ROOT / "UKACTIVE_A2R_EUROPE_SECTOR_GRID_AUDIT.csv")
    write_csv(global_grid, PROGRAMME_ROOT / "UKACTIVE_A2R_GLOBAL_SECTOR_GRID_AUDIT.csv")
    write_csv(candidates, PROGRAMME_ROOT / "UKACTIVE_A2R_NEW_PRODUCT_CANDIDATES.csv")
    write_parquet(corrected_instrument, PROGRAMME_ROOT / "UKACTIVE_A2R_CORRECTED_IMPLEMENTATION_HISTORY.parquet", parquet_meta)
    write_parquet(corrected_panel, PROGRAMME_ROOT / "UKACTIVE_A2R_CORRECTED_TOTAL_RETURN_PANEL_GBP.parquet", parquet_meta)
    write_parquet(engine["exposure"], PROGRAMME_ROOT / "UKACTIVE_A2R_CORRECTED_EXPOSURE_HISTORY_MASTER.parquet", parquet_meta)
    write_parquet(engine["canonical"], PROGRAMME_ROOT / "UKACTIVE_A2R_CORRECTED_CANONICAL_IMPLEMENTATION_HISTORY.parquet", parquet_meta)
    write_parquet(dynamic, PROGRAMME_ROOT / "UKACTIVE_A2R_DYNAMIC_SIGNAL_ELIGIBILITY.parquet", parquet_meta)
    (PROGRAMME_ROOT / "UKACTIVE_A2R_MANUAL_VALIDATION_CASES.md").write_text(manual_markdown, encoding="utf-8")
    write_csv(manual_cases, PROGRAMME_ROOT / "UKACTIVE_A2R_MANUAL_VALIDATION_CASES.csv")
    write_csv(tests, PROGRAMME_ROOT / "UKACTIVE_A2R_AUTOMATED_TEST_RESULTS.csv")
    write_csv(semantic_tests, PROGRAMME_ROOT / "UKACTIVE_A2R_SEMANTIC_LINEAGE_TEST_RESULTS.csv")
    write_csv(before_after, PROGRAMME_ROOT / "UKACTIVE_A2R_BEFORE_AFTER_HISTORY_AUDIT.csv")
    write_csv(unresolved, PROGRAMME_ROOT / "UKACTIVE_A2R_UNRESOLVED_ITEMS.csv")
    write_csv(engine["validations"], PROGRAMME_ROOT / "UKACTIVE_A2R_TOTAL_RETURN_VALIDATION.csv")
    write_csv(engine["events"], PROGRAMME_ROOT / "UKACTIVE_A2R_DISTRIBUTION_EVENTS.csv")
    write_csv(engine["fx_pairs"], PROGRAMME_ROOT / "UKACTIVE_A2R_FX_GBP_VALIDATION.csv")
    write_csv(engine["stale_report"], PROGRAMME_ROOT / "UKACTIVE_A2R_STALE_AND_MISSING_DATA_REPORT.csv")
    write_csv(coverage, PROGRAMME_ROOT / "UKACTIVE_A2R_FAMILY_COVERAGE_AND_READINESS.csv")
    write_csv(routes, PROGRAMME_ROOT / "UKACTIVE_A2R_SOURCE_ROUTE_MAP.csv")
    write_csv(primary_captures, PROGRAMME_ROOT / "UKACTIVE_A2R_PRIMARY_SOURCE_CAPTURE_LEDGER.csv")

    post_files = {
        "role": "UKACTIVE_A2R_A3R0_ROTATION_ROLE_MASTER_POST_A2R.csv",
        "pools": "UKACTIVE_A2R_A3R0_COMPETITION_POOLS_POST_A2R.csv",
        "parent_child": "UKACTIVE_A2R_A3R0_PARENT_CHILD_MAP_POST_A2R.csv",
        "overlaps": "UKACTIVE_A2R_A3R0_OVERLAP_CLUSTERS_POST_A2R.csv",
        "benchmark": "UKACTIVE_A2R_A3R0_GLOBAL_BENCHMARK_MAP_POST_A2R.csv",
        "parent_benchmark": "UKACTIVE_A2R_A3R0_PARENT_BENCHMARK_MAP_POST_A2R.csv",
        "selectable": "UKACTIVE_A2R_A3R0_SELECTABLE_ECONOMIC_UNIVERSE_POST_A2R.csv",
    }
    for key, filename in post_files.items():
        write_csv(regenerated[key], PROGRAMME_ROOT / filename)
    write_csv(all_lines, PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_CURRENT_IMPLEMENTATION_LINES_POST_A2R.csv")
    write_csv(public, PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_PUBLIC_UK_ELIGIBILITY_POST_A2R.csv")
    write_csv(queue, PROGRAMME_ROOT / "UKACTIVE_A3R0_CHATGPT_IBKR_VERIFICATION_QUEUE_POST_A2R.csv")
    write_parquet(regenerated["dynamic"], PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_DYNAMIC_SIGNAL_ELIGIBILITY_POST_A2R.parquet", parquet_meta)

    write_scope_and_reports(decision, corrections, coverage, dynamic, europe_grid, global_grid, tests, semantic_tests, manual_cases, unresolved, a3r0_reclass, a3r1_authorized)

    decision_payload = {
        "stage_id": STAGE_ID,
        "run_id": RUN_ID,
        "decision": decision,
        "decision_timestamp": now_utc(),
        "blocking_family_count": 14,
        "blocking_family_outcomes": corrections[["economic_exposure_family_id", "remediation_outcome_state", "corrected_first_valid_return_date", *[f"earliest_valid_{h}_session_signal_date" for h in HORIZONS]]].to_dict("records"),
        "zero_known_economic_family_history_mismatches": bool(route_audit["semantic_match"].eq("PASS").all()),
        "manual_cases_passed": int(manual_cases["manual_case_status"].eq("PASS").sum()),
        "automated_tests_passed": int(tests["status"].eq("PASS").sum()),
        "automated_tests_total": len(tests),
        "semantic_tests_passed": int(semantic_tests["status"].eq("PASS").sum()),
        "semantic_tests_total": len(semantic_tests),
        "unresolved_blocking_count": len(blocking_open),
        "A3R0_reclassification": a3r0_reclass,
        "A3R1_scientifically_authorized": a3r1_authorized,
        "A3R1_executed": False,
        "strategy_or_performance_research_executed": False,
        "warning": WARNING,
    }
    write_json(decision_payload, PROGRAMME_ROOT / "UKACTIVE_A2R_DECISION.json")

    evidence_rows = [*client.ledger, *primary_captures.to_dict("records")]
    A2R_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with A2R_LEDGER.open("w", encoding="utf-8") as handle:
        for row in evidence_rows:
            handle.write(json.dumps(row, default=json_default) + "\n")

    executed_dir = A2R_SOURCE_ROOT / "executed_source"
    executed_dir.mkdir(parents=True, exist_ok=True)
    for source in [Path(__file__), CODE_DIR / "ukactive_a2r_core.py", CODE_DIR / "build_ukactive_a2.py", CODE_DIR / "ukactive_a2_core.py", CODE_DIR / "build_ukactive_a3r0.py", CODE_DIR / "ukactive_a3r0_core.py", POLICY_PATH, A2_POLICY_PATH, A3R0_POLICY_PATH]:
        target = executed_dir / source.name
        target.write_bytes(source.read_bytes())

    after_namespace_hashes = namespace_hashes()
    originals_unchanged = original_namespace_hashes == after_namespace_hashes
    if not originals_unchanged:
        raise RuntimeError("Immutable original namespace checksum changed during A2R build")
    output_paths = sorted(
        [path for path in PROGRAMME_ROOT.glob("UKACTIVE_A2R_*") if path.is_file()]
        + [PROGRAMME_ROOT / "UKACTIVE_A3R0_CHATGPT_IBKR_VERIFICATION_QUEUE_POST_A2R.csv"]
    )
    output_hashes = {path.name: sha256_file(path) for path in output_paths if path.name != "UKACTIVE_A2R_MANIFEST.json"}
    input_paths = [
        PROGRAMME_ROOT / "UKACTIVE_A2_TOTAL_RETURN_PANEL_GBP.parquet",
        PROGRAMME_ROOT / "UKACTIVE_A2_EXPOSURE_HISTORY_MASTER.parquet",
        PROGRAMME_ROOT / "UKACTIVE_A2_POINT_IN_TIME_ELIGIBILITY.parquet",
        PROGRAMME_ROOT / "UKACTIVE_A2_SOURCE_ROUTE_MAP.csv",
        PROGRAMME_ROOT / "UKACTIVE_A3R0_DECISION.json",
        PROGRAMME_ROOT / "UKACTIVE_A3R0_CHATGPT_IBKR_VERIFICATION_QUEUE.csv",
        PROGRAMME_ROOT / "UKACTIVE_A0A1_DISCOVERY_REGISTRY.csv",
        PROGRAMME_ROOT / "UKACTIVE_A0A1_ECONOMIC_EXPOSURE_MASTER.csv",
    ]
    try:
        git_commit = subprocess.check_output(["git", "-C", str(PROGRAMME_ROOT), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
        git_state = "GIT_WORKTREE"
    except (subprocess.CalledProcessError, FileNotFoundError):
        git_commit = "NOT_A_GIT_WORKTREE"
        git_state = "NOT_A_GIT_WORKTREE"
    manifest = {
        "stage_id": STAGE_ID,
        "run_id": RUN_ID,
        "started_at": started,
        "completed_at": now_utc(),
        "command_line": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        "working_directory": os.getcwd(),
        "git_commit": git_commit,
        "git_state": git_state,
        "reproducibility_status": "PASS_EXECUTED_SOURCE_AND_CONFIG_SNAPSHOTS_HASHED" if originals_unchanged else "FAIL",
        "credential_route": credential_source,
        "credentials_exposed": False,
        "policy_id": a2r_policy["policy_id"],
        "input_hashes": {str(path.relative_to(PROGRAMME_ROOT)): sha256_file(path) for path in input_paths},
        "original_namespace_hashes_before_and_after_identical": originals_unchanged,
        "original_namespace_hashes": original_namespace_hashes,
        "executed_source_hashes": {path.name: sha256_file(path) for path in executed_dir.iterdir() if path.is_file()},
        "external_sources": primary_captures.to_dict("records"),
        "evidence_ledger": str(A2R_LEDGER),
        "old_new_ISIN_mappings": corrections[["economic_exposure_family_id", "new_implementation_isins"]].to_dict("records"),
        "old_new_economic_fingerprints": corrections[["economic_exposure_family_id", "old_primary_implementation_summary", "new_economic_fingerprint"]].to_dict("records"),
        "corrected_historical_start_dates": corrections[["economic_exposure_family_id", "corrected_first_valid_return_date"]].to_dict("records"),
        "return_series_change_audit_sha256": sha256_file(PROGRAMME_ROOT / "UKACTIVE_A2R_BEFORE_AFTER_HISTORY_AUDIT.csv"),
        "output_hashes": output_hashes,
        "package_versions": package_versions(),
        "automated_test_summary": tests["status"].value_counts().to_dict(),
        "semantic_test_summary": semantic_tests["status"].value_counts().to_dict(),
        "manual_case_summary": manual_cases["manual_case_status"].value_counts().to_dict(),
        "unresolved_items": unresolved.to_dict("records"),
        "family_coverage_statistics": coverage.to_dict("records"),
        "A3R1_executed": False,
        "performance_statistics_calculated": False,
        "warning": WARNING,
    }
    write_json(manifest, PROGRAMME_ROOT / "UKACTIVE_A2R_MANIFEST.json")

    # Flat-file scientific-artifact QA: every CSV reparses and every Parquet schema round-trips.
    for path in output_paths:
        if path.suffix.lower() == ".csv":
            pd.read_csv(path, keep_default_na=False)
        elif path.suffix.lower() == ".parquet":
            pq.read_schema(path)
    print(json.dumps({"decision": decision, "families": len(master), "tests": tests["status"].value_counts().to_dict(), "semantic_tests": semantic_tests["status"].value_counts().to_dict(), "manual": manual_cases["manual_case_status"].value_counts().to_dict(), "A3R1_authorized": a3r1_authorized}, indent=2))
    return 0 if decision != "UKACTIVE_A2R_FAIL" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise
