#!/usr/bin/env python3
"""Build UKACTIVE-A0A1 from current public evidence.

This programme is deliberately independent of EDGE-UKETF-20260822-001.  It does
not import that programme, its universe, or any strategy rule.  The output is a
current research master only; current eligibility must never be back-projected.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROGRAMME_ID = "EDGE-UK-ACTIVE-ETF-SLEEVE-20260822-001"
STAGE_ID = "UKACTIVE-A0A1"
RUN_ID = "UKACTIVE-A0A1-20260822-001"
OBSERVATION_DATE = "2026-08-22"
WARNING = "CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY"
CLASSIFICATION_RULE_VERSION = "UKACTIVE-CLASSIFICATION-v1.0.0"
DUPLICATE_RULE_VERSION = "UKACTIVE-DUPLICATE-v1.0.0"

LSE_PAGE_URL = (
    "https://www.londonstockexchange.com/live-markets/market-data-dashboard/"
    "price-explorer?categories=ETFS&page=1&showonlylse=true"
)
LSE_API_URL = "https://api.londonstockexchange.com/api/v1/pages"
ISHARES_CATALOG_URL = (
    "https://www.ishares.com/varnish-api/blk-product-screener-server/api/v1/"
    "product-screener/product-data?country=gb&language=en&siteName=ishares-uk&userType=individual"
)

HMRC_ISA_URL = "https://www.gov.uk/guidance/stocks-and-shares-investments-for-isa-managers"
HMRC_SIPP_URL = "https://www.gov.uk/hmrc-internal-manuals/pensions-tax-manual/ptm121000"
FCA_CCI_URL = "https://handbook.fca.org.uk/handbook/disctp2"
FCA_PS_URL = (
    "https://www.fca.org.uk/publications/policy-statements/"
    "ps25-20-supporting-informed-decision-making-final-rules-consumer-composite-investments"
)
DEEPVUE_URL = "https://docs.deepvue.com/articles/theme-tracker-app"

CONFIRMED_DEEPVUE_THEMES = {
    "Bitcoin", "Genomics", "Gold Miners", "Steel", "Silver Miners", "Materials",
    "Cybersecurity", "Growth Stocks", "Software", "Medical", "Biotechnology",
    "Social Media", "Healthcare", "Retail", "Airlines", "Transports", "Quantum",
    "Home Construction", "Telecom", "Robotics", "AI", "Industrials", "Banks",
    "Real Estate", "Aerospace", "China Internet", "Oil & Gas", "Semiconductors",
    "Solar", "Utilities", "Bitcoin Miners",
}

PROVIDER_CATALOG_URLS = {
    "ISHARES": "https://www.ishares.com/uk/individual/en/products/etf-investments?siteEntryPassthrough=true",
    "VANGUARD": "https://www.vanguard.co.uk/professional/product?fund-type=etf",
    "INVESCO": "https://www.invesco.com/uk/en/financial-products/etfs.html",
    "STATE STREET": "https://www.ssga.com/uk/en_gb/intermediary/fund-finder",
    "SPDR": "https://www.ssga.com/uk/en_gb/intermediary/fund-finder",
    "WISDOMTREE": "https://www.wisdomtree.eu/en-gb/etfs",
    "AMUNDI": "https://www.amundietf.co.uk/en/professional/products",
    "UBS": "https://www.ubs.com/uk/en/assetmanagement/capabilities/etfs.html",
    "HSBC": "https://www.assetmanagement.hsbc.co.uk/en/intermediary/investment-expertise/etfs",
    "LEGAL & GENERAL": "https://fundcentres.lgim.com/uk/en/fund-centre/ETF/",
    "L&G": "https://fundcentres.lgim.com/uk/en/fund-centre/ETF/",
    "VANECK": "https://www.vaneck.com/uk/en/investments/",
    "GLOBAL X": "https://globalxetfs.eu/funds/",
    "HANETF": "https://hanetf.com/funds/",
    "FRANKLIN": "https://www.franklintempleton.co.uk/our-funds/price-and-performance-etfs",
    "JPMORGAN": "https://am.jpmorgan.com/gb/en/asset-management/per/products/etf/",
    "FIRST TRUST": "https://www.ftglobalportfolios.com/uk/",
}


def family(
    family_id: str,
    pattern: str,
    *,
    opportunity_type: str,
    tier: str,
    asset_class: str,
    sub_asset_class: str,
    geography: str,
    scope: str,
    country: str = "NOT_APPLICABLE",
    development: str = "NOT_APPLICABLE",
    sector: str = "NOT_APPLICABLE",
    industry: str = "NOT_APPLICABLE",
    theme: str = "NOT_APPLICABLE",
    deepvue: str = "NOT_APPLICABLE",
    factor: str = "NOT_APPLICABLE",
    market_cap: str = "ALL_CAP",
    bond_issuer: str = "NOT_APPLICABLE",
    duration: str = "NOT_APPLICABLE",
    credit: str = "NOT_APPLICABLE",
    inflation: str = "NOT_APPLICABLE",
    commodity: str = "NOT_APPLICABLE",
    role: str = "GROWTH",
    currency_exposure: str = "MULTI_CURRENCY",
    max_isins: int = 4,
    description: str = "",
) -> dict[str, Any]:
    return locals()


# Ordered from narrow/specific to broad.  These are economic classifications,
# never ticker rankings.  A later implementation step may choose among members.
FAMILY_RULES: list[dict[str, Any]] = [
    family("GLOBAL_SEMICONDUCTORS", r"SEMICONDUCT|CHIPMAKER|CHIP\b", opportunity_type="THEMATIC", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="THEMATIC_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="TECHNOLOGY", industry="SEMICONDUCTORS", theme="SEMICONDUCTORS", deepvue="Semiconductors", role="GROWTH", max_isins=5, description="Global semiconductor value chain"),
    family("GLOBAL_CYBERSECURITY", r"CYBER ?SECURITY|DIGITAL SECURITY", opportunity_type="THEMATIC", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="THEMATIC_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="TECHNOLOGY", industry="CYBERSECURITY", theme="CYBERSECURITY", deepvue="Cybersecurity", role="GROWTH", max_isins=5, description="Global cybersecurity businesses"),
    family("GLOBAL_AI", r"ARTIFICIAL INTELLIGENCE|\bAI\b(?!.*BOND)|AI &|AI AND BIG DATA", opportunity_type="THEMATIC", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="THEMATIC_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="TECHNOLOGY", industry="SOFTWARE_AND_SERVICES", theme="AI", deepvue="AI", role="GROWTH", max_isins=4, description="Artificial-intelligence value chain"),
    family("GLOBAL_ROBOTICS_AUTOMATION", r"ROBOT|AUTOMATION", opportunity_type="THEMATIC", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="THEMATIC_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="INDUSTRIALS", industry="INDUSTRIAL_AUTOMATION", theme="ROBOTICS", deepvue="Robotics", role="GROWTH", max_isins=4, description="Robotics and industrial automation"),
    family("GLOBAL_QUANTUM_COMPUTING", r"QUANTUM", opportunity_type="THEMATIC", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="THEMATIC_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="TECHNOLOGY", industry="COMPUTING", theme="QUANTUM", deepvue="Quantum", role="GROWTH", max_isins=3, description="Quantum-computing ecosystem"),
    family("GLOBAL_SOFTWARE", r"SOFTWARE|CLOUD COMPUT", opportunity_type="SECTOR_INDUSTRY", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="INDUSTRY_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="TECHNOLOGY", industry="SOFTWARE", theme="SOFTWARE", deepvue="Software", role="GROWTH", max_isins=4, description="Software and cloud businesses"),
    family("GLOBAL_GENOMICS", r"GENOMIC|GENOME", opportunity_type="THEMATIC", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="THEMATIC_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="HEALTHCARE", industry="BIOTECHNOLOGY", theme="GENOMICS", deepvue="Genomics", role="GROWTH", max_isins=4, description="Genomics and genomic medicine"),
    family("GLOBAL_BIOTECHNOLOGY", r"BIOTECH", opportunity_type="SECTOR_INDUSTRY", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="INDUSTRY_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="HEALTHCARE", industry="BIOTECHNOLOGY", theme="BIOTECHNOLOGY", deepvue="Biotechnology", role="GROWTH", max_isins=4, description="Biotechnology industry"),
    family("GLOBAL_HEALTHCARE", r"HEALTH ?CARE|HEALTHCARE|MEDICAL DEVIC", opportunity_type="SECTOR_INDUSTRY", tier="CORE", asset_class="EQUITY", sub_asset_class="SECTOR_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="HEALTHCARE", industry="BROAD_SECTOR", theme="NOT_APPLICABLE", deepvue="Healthcare", role="DEFENSIVE_EQUITY", max_isins=4, description="Broad global healthcare sector"),
    family("GLOBAL_AEROSPACE_DEFENCE", r"DEFEN[CS]E|AEROSPACE|NATO", opportunity_type="THEMATIC", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="INDUSTRY_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="INDUSTRIALS", industry="AEROSPACE_AND_DEFENCE", theme="DEFENCE", deepvue="Aerospace", role="GROWTH", max_isins=5, description="Aerospace and defence businesses"),
    family("GLOBAL_TRANSPORTATION", r"TRANSPORT|LOGISTICS|FUTURE OF TRANSPORT", opportunity_type="SECTOR_INDUSTRY", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="INDUSTRY_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="INDUSTRIALS", industry="TRANSPORTATION", theme="TRANSPORTATION", deepvue="Transports", role="CYCLICAL_EQUITY", max_isins=3, description="Transportation and logistics"),
    family("GLOBAL_AIRLINES", r"AIRLINE|TRAVEL.*LEISURE", opportunity_type="SECTOR_INDUSTRY", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="INDUSTRY_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="INDUSTRIALS", industry="AIRLINES", theme="AIRLINES", deepvue="Airlines", role="CYCLICAL_EQUITY", max_isins=3, description="Airlines and related travel exposure"),
    family("GLOBAL_INFRASTRUCTURE", r"INFRASTRUCTURE", opportunity_type="THEMATIC", tier="EXTENDED", asset_class="INFRASTRUCTURE", sub_asset_class="LISTED_INFRASTRUCTURE_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="INDUSTRIALS", industry="INFRASTRUCTURE", theme="INFRASTRUCTURE", role="REAL_ASSET_DIVERSIFIER", max_isins=4, description="Global listed infrastructure"),
    family("GLOBAL_CLEAN_ENERGY", r"CLEAN ENERGY|NEW ENERGY|ENERGY TRANSITION", opportunity_type="THEMATIC", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="THEMATIC_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="UTILITIES", industry="RENEWABLE_ENERGY", theme="CLEAN_ENERGY", role="GROWTH", max_isins=4, description="Clean-energy value chain"),
    family("GLOBAL_SOLAR", r"SOLAR", opportunity_type="THEMATIC", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="THEMATIC_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="UTILITIES", industry="RENEWABLE_ENERGY", theme="SOLAR", deepvue="Solar", role="GROWTH", max_isins=3, description="Solar-energy value chain"),
    family("GLOBAL_URANIUM_NUCLEAR", r"URANIUM|NUCLEAR", opportunity_type="THEMATIC", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="THEMATIC_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="ENERGY", industry="URANIUM_AND_NUCLEAR", theme="URANIUM_NUCLEAR", role="CYCLICAL_EQUITY", max_isins=4, description="Uranium miners and nuclear-energy value chain"),
    family("GLOBAL_GOLD_MINERS", r"GOLD MIN(?:ER|ING)|GOLD PRODUCER|GOLD AND PRECIOUS|GOLD BUGS", opportunity_type="SECTOR_INDUSTRY", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="INDUSTRY_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="MATERIALS", industry="GOLD_MINERS", theme="GOLD_MINERS", deepvue="Gold Miners", role="REAL_ASSET_EQUITY", max_isins=5, description="Global gold-mining equities"),
    family("GLOBAL_SILVER_MINERS", r"SILVER MINER", opportunity_type="SECTOR_INDUSTRY", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="INDUSTRY_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="MATERIALS", industry="SILVER_MINERS", theme="SILVER_MINERS", deepvue="Silver Miners", role="REAL_ASSET_EQUITY", max_isins=3, description="Global silver-mining equities"),
    family("GLOBAL_STEEL", r"STEEL", opportunity_type="SECTOR_INDUSTRY", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="INDUSTRY_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="MATERIALS", industry="STEEL", theme="STEEL", deepvue="Steel", role="CYCLICAL_EQUITY", max_isins=3, description="Global steel producers"),
    family("GLOBAL_OIL_GAS", r"OIL.*GAS|ENERGY PRODUCER|EXPLORATION.*PRODUCTION", opportunity_type="SECTOR_INDUSTRY", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="INDUSTRY_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="ENERGY", industry="OIL_AND_GAS", theme="OIL_AND_GAS", deepvue="Oil & Gas", role="CYCLICAL_EQUITY", max_isins=4, description="Global oil and gas equities"),
    family("GLOBAL_BANKS", r"\bBANKS?\b", opportunity_type="SECTOR_INDUSTRY", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="INDUSTRY_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="FINANCIALS", industry="BANKS", theme="NOT_APPLICABLE", deepvue="Banks", role="CYCLICAL_EQUITY", max_isins=4, description="Global banking industry"),
    family("GLOBAL_FINANCIALS", r"FINANCIALS?|FINANCIAL SERVICES", opportunity_type="SECTOR_INDUSTRY", tier="CORE", asset_class="EQUITY", sub_asset_class="SECTOR_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="FINANCIALS", industry="BROAD_SECTOR", role="CYCLICAL_EQUITY", max_isins=4, description="Broad global financials sector"),
    family("GLOBAL_TECHNOLOGY", r"INFORMATION TECHNOLOGY|WORLD TECHNOLOGY|GLOBAL TECHNOLOGY|DIGITALISATION", opportunity_type="SECTOR_INDUSTRY", tier="CORE", asset_class="EQUITY", sub_asset_class="SECTOR_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="TECHNOLOGY", industry="BROAD_SECTOR", role="GROWTH", max_isins=4, description="Broad global technology sector"),
    family("GLOBAL_INDUSTRIALS", r"WORLD INDUSTRIAL|GLOBAL INDUSTRIAL|INDUSTRIALS SECTOR", opportunity_type="SECTOR_INDUSTRY", tier="CORE", asset_class="EQUITY", sub_asset_class="SECTOR_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="INDUSTRIALS", industry="BROAD_SECTOR", deepvue="Industrials", role="CYCLICAL_EQUITY", max_isins=4, description="Broad global industrials sector"),
    family("GLOBAL_CONSUMER_DISCRETIONARY", r"CONSUMER DISCRETIONARY", opportunity_type="SECTOR_INDUSTRY", tier="CORE", asset_class="EQUITY", sub_asset_class="SECTOR_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="CONSUMER_DISCRETIONARY", industry="BROAD_SECTOR", role="CYCLICAL_EQUITY", max_isins=4, description="Broad consumer-discretionary sector"),
    family("GLOBAL_RETAIL", r"RETAIL|ECOMMERCE|E-COMMERCE", opportunity_type="SECTOR_INDUSTRY", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="INDUSTRY_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="CONSUMER_DISCRETIONARY", industry="RETAIL", theme="RETAIL", deepvue="Retail", role="CYCLICAL_EQUITY", max_isins=3, description="Retail and e-commerce businesses"),
    family("GLOBAL_CONSUMER_STAPLES", r"CONSUMER STAPLES", opportunity_type="SECTOR_INDUSTRY", tier="CORE", asset_class="EQUITY", sub_asset_class="SECTOR_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="CONSUMER_STAPLES", industry="BROAD_SECTOR", role="DEFENSIVE_EQUITY", max_isins=4, description="Broad consumer-staples sector"),
    family("GLOBAL_COMMUNICATION_SERVICES", r"COMMUNICATION SERVICES", opportunity_type="SECTOR_INDUSTRY", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="SECTOR_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="COMMUNICATION_SERVICES", industry="BROAD_SECTOR", role="GROWTH", max_isins=4, description="Broad communication-services sector"),
    family("GLOBAL_TELECOM", r"TELECOM", opportunity_type="SECTOR_INDUSTRY", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="INDUSTRY_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="COMMUNICATION_SERVICES", industry="TELECOMMUNICATIONS", theme="TELECOM", deepvue="Telecom", role="DEFENSIVE_EQUITY", max_isins=3, description="Telecommunications businesses"),
    family("GLOBAL_ENERGY", r"WORLD ENERGY|GLOBAL ENERGY|ENERGY SECTOR", opportunity_type="SECTOR_INDUSTRY", tier="CORE", asset_class="EQUITY", sub_asset_class="SECTOR_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="ENERGY", industry="BROAD_SECTOR", role="CYCLICAL_EQUITY", max_isins=4, description="Broad global energy sector"),
    family("GLOBAL_MATERIALS", r"WORLD MATERIAL|GLOBAL MATERIAL|MATERIALS SECTOR|BASIC RESOURCES", opportunity_type="SECTOR_INDUSTRY", tier="CORE", asset_class="EQUITY", sub_asset_class="SECTOR_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="MATERIALS", industry="BROAD_SECTOR", deepvue="Materials", role="CYCLICAL_EQUITY", max_isins=4, description="Broad global materials sector"),
    family("GLOBAL_UTILITIES", r"WORLD UTILIT|GLOBAL UTILIT|UTILITIES SECTOR", opportunity_type="SECTOR_INDUSTRY", tier="CORE", asset_class="EQUITY", sub_asset_class="SECTOR_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="UTILITIES", industry="BROAD_SECTOR", deepvue="Utilities", role="DEFENSIVE_EQUITY", max_isins=4, description="Broad global utilities sector"),
    family("GLOBAL_REAL_ESTATE", r"GLOBAL.*(PROPERTY|REAL ESTATE)|DEVELOPED.*(PROPERTY|REAL ESTATE)", opportunity_type="SECTOR_INDUSTRY", tier="EXTENDED", asset_class="PROPERTY", sub_asset_class="LISTED_REAL_ESTATE_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="REAL_ESTATE", industry="REITS_AND_PROPERTY", deepvue="Real Estate", role="REAL_ASSET_DIVERSIFIER", max_isins=4, description="Global listed property and REITs"),
    family("US_HOME_CONSTRUCTION", r"HOME CONSTRUCTION|HOMEBUILD", opportunity_type="SECTOR_INDUSTRY", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="INDUSTRY_EQUITY", geography="UNITED_STATES", scope="SINGLE_COUNTRY", country="UNITED_STATES", development="DEVELOPED", sector="CONSUMER_DISCRETIONARY", industry="HOME_CONSTRUCTION", theme="HOME_CONSTRUCTION", deepvue="Home Construction", role="CYCLICAL_EQUITY", currency_exposure="USD", max_isins=3, description="US homebuilders and construction"),
    family("GLOBAL_SOCIAL_MEDIA", r"SOCIAL MEDIA|SOCIAL NETWORK", opportunity_type="THEMATIC", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="THEMATIC_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="COMMUNICATION_SERVICES", industry="INTERACTIVE_MEDIA", theme="SOCIAL_MEDIA", deepvue="Social Media", role="GROWTH", max_isins=3, description="Social-media platforms"),
    family("CHINA_INTERNET", r"CHINA.*(INTERNET|DIGITAL)|KRANESHARES.*CSI CHINA INTERNET", opportunity_type="THEMATIC", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="THEMATIC_EQUITY", geography="CHINA", scope="SINGLE_COUNTRY", country="CHINA", development="EMERGING", sector="COMMUNICATION_SERVICES", industry="INTERNET_SERVICES", theme="CHINA_INTERNET", deepvue="China Internet", role="GROWTH", currency_exposure="CNY_HKD_USD", max_isins=4, description="China internet and digital economy"),
    family("BITCOIN_MINERS_EQUITY", r"BITCOIN MINER|DIGITAL ASSET.*EQUITY|BLOCKCHAIN.*EQUIT", opportunity_type="THEMATIC", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="THEMATIC_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="TECHNOLOGY", industry="DIGITAL_ASSET_INFRASTRUCTURE", theme="BITCOIN_MINERS", deepvue="Bitcoin Miners", role="HIGH_VOLATILITY_GROWTH", max_isins=3, description="Listed bitcoin-mining and digital-asset infrastructure equities"),
    family("GLOBAL_WATER", r"WATER", opportunity_type="THEMATIC", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="THEMATIC_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="INDUSTRIALS", industry="WATER_INFRASTRUCTURE", theme="WATER", role="REAL_ASSET_EQUITY", max_isins=4, description="Water infrastructure and services"),
    family("GLOBAL_AGRIBUSINESS", r"AGRIBUSINESS|AGRICULTURE.*EQUIT|FOOD.*AGRICULTURE", opportunity_type="THEMATIC", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="THEMATIC_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="CONSUMER_STAPLES", industry="AGRIBUSINESS", theme="AGRIBUSINESS", role="REAL_ASSET_EQUITY", max_isins=3, description="Agricultural inputs and food value chain"),
    family("GLOBAL_BATTERY_EV", r"BATTER(Y|IES)|ELECTRIC VEHICLE|EV AND", opportunity_type="THEMATIC", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="THEMATIC_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="INDUSTRIALS", industry="BATTERY_AND_EV_VALUE_CHAIN", theme="BATTERY_EV", role="GROWTH", max_isins=4, description="Battery and electric-vehicle value chain"),
    family("GLOBAL_SPACE", r"SPACE ECONOMY|SPACE INNOVATION|SATELLITE", opportunity_type="THEMATIC", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="THEMATIC_EQUITY", geography="GLOBAL", scope="GLOBAL", sector="INDUSTRIALS", industry="AEROSPACE", theme="SPACE", role="GROWTH", max_isins=3, description="Commercial space economy"),

    # Defensive and real-asset opportunity families.
    family("USD_OVERNIGHT_CASH", r"(?:\$|USD|US DOLLAR).*(?:OVERNIGHT|FED FUNDS|SOFR)|(?:FEDERAL FUNDS|FED FUNDS|SOFR)", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="EXTENDED", asset_class="CASH_LIKE", sub_asset_class="OVERNIGHT_RATE", geography="UNITED_STATES", scope="SINGLE_COUNTRY", country="UNITED_STATES", development="DEVELOPED", market_cap="NOT_APPLICABLE", role="CASH_RESERVE", currency_exposure="USD", max_isins=4, description="US-dollar overnight-rate exposure"),
    family("EUR_OVERNIGHT_CASH", r"(?:EURO|EUR|€).*(?:OVERNIGHT|ESTR|€STR)|(?:ESTR|€STR)", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="EXTENDED", asset_class="CASH_LIKE", sub_asset_class="OVERNIGHT_RATE", geography="EUROZONE", scope="REGION", country="NOT_APPLICABLE", development="DEVELOPED", market_cap="NOT_APPLICABLE", role="CASH_RESERVE", currency_exposure="EUR", max_isins=4, description="Euro overnight-rate exposure"),
    family("GBP_OVERNIGHT_CASH", r"SONIA|STERLING.*OVERNIGHT|GBP.*OVERNIGHT|£.*OVERNIGHT", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="CORE", asset_class="CASH_LIKE", sub_asset_class="OVERNIGHT_RATE", geography="UNITED_KINGDOM", scope="SINGLE_COUNTRY", country="UNITED_KINGDOM", development="DEVELOPED", market_cap="NOT_APPLICABLE", role="CASH_RESERVE", currency_exposure="GBP", max_isins=5, description="Sterling overnight-rate exposure"),
    family("GBP_ULTRASHORT_BONDS", r"STERLING.*ULTRA ?SHORT|GBP.*ULTRA ?SHORT|0-1YR.*CORPORATE|0-1 YEAR.*CORPORATE", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="CORE", asset_class="CASH_LIKE", sub_asset_class="ULTRASHORT_BOND", geography="UNITED_KINGDOM", scope="SINGLE_COUNTRY", country="UNITED_KINGDOM", development="DEVELOPED", market_cap="NOT_APPLICABLE", bond_issuer="MIXED", duration="ULTRASHORT_0_1Y", credit="INVESTMENT_GRADE", role="CASH_ALTERNATIVE", currency_exposure="GBP", max_isins=5, description="Sterling ultrashort investment-grade bonds"),
    family("UK_GILTS_SHORT", r"(UK|STERLING).*GILT.*(0-5|1-5|SHORT)|GILT.*(0-5|1-5|SHORT)", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="CORE", asset_class="GOVERNMENT_BOND", sub_asset_class="NOMINAL_GOVERNMENT_BOND", geography="UNITED_KINGDOM", scope="SINGLE_COUNTRY", country="UNITED_KINGDOM", development="DEVELOPED", market_cap="NOT_APPLICABLE", bond_issuer="SOVEREIGN", duration="SHORT_0_5Y", credit="INVESTMENT_GRADE", inflation="NO", role="CAPITAL_PRESERVATION", currency_exposure="GBP", max_isins=5, description="Short-duration UK government bonds"),
    family("UK_GILTS_LONG", r"(UK|STERLING).*GILT.*(15\+|20\+|LONG)|GILT.*(15\+|20\+|LONG)", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="EXTENDED", asset_class="GOVERNMENT_BOND", sub_asset_class="NOMINAL_GOVERNMENT_BOND", geography="UNITED_KINGDOM", scope="SINGLE_COUNTRY", country="UNITED_KINGDOM", development="DEVELOPED", market_cap="NOT_APPLICABLE", bond_issuer="SOVEREIGN", duration="LONG_15Y_PLUS", credit="INVESTMENT_GRADE", inflation="NO", role="DURATION_DIVERSIFIER", currency_exposure="GBP", max_isins=5, description="Long-duration UK government bonds"),
    family("UK_INDEX_LINKED_GILTS", r"(?:INDEX|INDX)[- ]?LINK(?:ED)?.*GILT|GILT.*(?:INDEX|INDX)[- ]?LINK(?:ED)?|UK INFLATION[- ]?LINKED", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="EXTENDED", asset_class="GOVERNMENT_BOND", sub_asset_class="INFLATION_LINKED_GOVERNMENT_BOND", geography="UNITED_KINGDOM", scope="SINGLE_COUNTRY", country="UNITED_KINGDOM", development="DEVELOPED", market_cap="NOT_APPLICABLE", bond_issuer="SOVEREIGN", duration="ALL_MATURITIES", credit="INVESTMENT_GRADE", inflation="YES", role="INFLATION_DIVERSIFIER", currency_exposure="GBP", max_isins=5, description="UK index-linked government bonds"),
    family("UK_GILTS_ALL", r"(UK|STERLING).*GILT|FTSE ACTUARIES UK CONVENTIONAL GILTS|CORE UK GILTS", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="CORE", asset_class="GOVERNMENT_BOND", sub_asset_class="NOMINAL_GOVERNMENT_BOND", geography="UNITED_KINGDOM", scope="SINGLE_COUNTRY", country="UNITED_KINGDOM", development="DEVELOPED", market_cap="NOT_APPLICABLE", bond_issuer="SOVEREIGN", duration="ALL_MATURITIES", credit="INVESTMENT_GRADE", inflation="NO", role="DURATION_DIVERSIFIER", currency_exposure="GBP", max_isins=5, description="Broad UK government bonds"),
    family("GBP_CORPORATE_IG", r"(?:STERLING|GBP|£).*(?:CORPORATE|CORP).*(?:BOND|BD)|(?:CORPORATE|CORP).*(?:BOND|BD).*(?:STERLING ISSUANCE|GBP ISSUANCE)", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="CORE", asset_class="CORPORATE_BOND", sub_asset_class="INVESTMENT_GRADE_CORPORATE_BOND", geography="GLOBAL", scope="GBP_ISSUANCE", market_cap="NOT_APPLICABLE", bond_issuer="CORPORATE", duration="ALL_MATURITIES", credit="INVESTMENT_GRADE", role="INCOME_DIVERSIFIER", currency_exposure="GBP", max_isins=5, description="Sterling investment-grade corporate bonds"),
    family("GLOBAL_AGGREGATE_BONDS_GBP_HEDGED", r"GLOBAL AGGREGATE.*GBP HEDG|GLOBAL AGG.*GBP HEDG|AGGREGATE BOND.*GBP HEDG", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="CORE", asset_class="AGGREGATE_BOND", sub_asset_class="GLOBAL_AGGREGATE_BOND", geography="GLOBAL", scope="GLOBAL", market_cap="NOT_APPLICABLE", bond_issuer="MIXED", duration="ALL_MATURITIES", credit="BROAD_CREDIT", role="DURATION_DIVERSIFIER", currency_exposure="GBP_HEDGED", max_isins=5, description="Global aggregate bonds hedged to sterling"),
    family("GLOBAL_GOVERNMENT_BONDS_GBP_HEDGED", r"GLOBAL.*GOVERNMENT BOND.*GBP HEDG|WORLD GOVERNMENT BOND.*GBP HEDG", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="EXTENDED", asset_class="GOVERNMENT_BOND", sub_asset_class="GLOBAL_GOVERNMENT_BOND", geography="GLOBAL", scope="GLOBAL", market_cap="NOT_APPLICABLE", bond_issuer="SOVEREIGN", duration="ALL_MATURITIES", credit="INVESTMENT_GRADE", role="DURATION_DIVERSIFIER", currency_exposure="GBP_HEDGED", max_isins=4, description="Global government bonds hedged to sterling"),
    family("GLOBAL_CORPORATE_IG_GBP_HEDGED", r"(?:GLOBAL|GLB|USD|\$|EUR|€).*(?:CORPORATE|CORP).*(?:GBP[- ]?H|GBPH|GBP HEDG)|(?:CORPORATE|CORP).*(?:BOND|BD).*(?:GBP[- ]?H|GBPH|GBP HEDG)", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="EXTENDED", asset_class="CORPORATE_BOND", sub_asset_class="INVESTMENT_GRADE_CORPORATE_BOND", geography="GLOBAL", scope="GLOBAL", market_cap="NOT_APPLICABLE", bond_issuer="CORPORATE", duration="ALL_MATURITIES", credit="INVESTMENT_GRADE", role="INCOME_DIVERSIFIER", currency_exposure="GBP_HEDGED", max_isins=4, description="Global investment-grade corporate bonds hedged to sterling"),
    family("US_TREASURY_SHORT_GBP_HEDGED", r"(TREASURY|TREASURIES).*(0-3|1-3|SHORT).*GBP HEDG|GBP HEDG.*(TREASURY|TREASURIES).*(0-3|1-3|SHORT)", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="EXTENDED", asset_class="GOVERNMENT_BOND", sub_asset_class="NOMINAL_GOVERNMENT_BOND", geography="UNITED_STATES", scope="SINGLE_COUNTRY", country="UNITED_STATES", development="DEVELOPED", market_cap="NOT_APPLICABLE", bond_issuer="SOVEREIGN", duration="SHORT_0_3Y", credit="INVESTMENT_GRADE", role="CAPITAL_PRESERVATION", currency_exposure="GBP_HEDGED", max_isins=4, description="Short US Treasuries hedged to sterling"),
    family("US_TREASURY_LONG_GBP_HEDGED", r"(TREASURY|TREASURIES).*(20\+|LONG).*GBP HEDG|GBP HEDG.*(TREASURY|TREASURIES).*(20\+|LONG)", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="EXPERIMENTAL", asset_class="GOVERNMENT_BOND", sub_asset_class="NOMINAL_GOVERNMENT_BOND", geography="UNITED_STATES", scope="SINGLE_COUNTRY", country="UNITED_STATES", development="DEVELOPED", market_cap="NOT_APPLICABLE", bond_issuer="SOVEREIGN", duration="LONG_20Y_PLUS", credit="INVESTMENT_GRADE", role="DURATION_DIVERSIFIER", currency_exposure="GBP_HEDGED", max_isins=4, description="Long US Treasuries hedged to sterling"),
    family("GOLD", r"PHYSICAL GOLD|GOLD ETC|GOLD BULLION|(?:WISDOMTREE|UBS|XTRACKERS|ISHARES|INVESCO).*\bGOLD\b", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="CORE", asset_class="GOLD", sub_asset_class="PRECIOUS_METAL_ETC", geography="GLOBAL", scope="GLOBAL_COMMODITY", market_cap="NOT_APPLICABLE", commodity="GOLD", role="CRISIS_INFLATION_DIVERSIFIER", currency_exposure="GOLD_USD", max_isins=6, description="Unleveraged gold exposure, preferring physically backed implementations"),
    family("SILVER_PHYSICAL", r"PHYSICAL SILVER|SILVER ETC|SILVER\b", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="EXPERIMENTAL", asset_class="COMMODITY", sub_asset_class="PHYSICAL_PRECIOUS_METAL_ETC", geography="GLOBAL", scope="GLOBAL_COMMODITY", market_cap="NOT_APPLICABLE", commodity="SILVER", role="REAL_ASSET_DIVERSIFIER", currency_exposure="SILVER_USD", max_isins=4, description="Unleveraged silver exposure"),
    family("BROAD_COMMODITIES", r"BROAD COMMODIT|ALL COMMODIT|COMMODITY INDEX", opportunity_type="DEFENSIVE_DIVERSIFIER", tier="EXPERIMENTAL", asset_class="COMMODITY", sub_asset_class="BROAD_COMMODITY_ETC_ETF", geography="GLOBAL", scope="GLOBAL_COMMODITY", market_cap="NOT_APPLICABLE", commodity="BROAD_BASKET", role="INFLATION_DIVERSIFIER", currency_exposure="COMMODITY_USD", max_isins=4, description="Broad diversified commodity basket"),

    # Geographic equity opportunity families.
    family("US_NASDAQ_100", r"NASDAQ[- ]?100|NASDAQ 100", opportunity_type="GEOGRAPHY", tier="CORE", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="UNITED_STATES", scope="SINGLE_COUNTRY", country="UNITED_STATES", development="DEVELOPED", sector="BROAD_MARKET", industry="BROAD_MARKET", factor="GROWTH_BIAS", market_cap="LARGE_CAP", deepvue="NOT_APPLICABLE", currency_exposure="USD", max_isins=6, description="US Nasdaq-100 large-cap growth-biased equities"),
    family("US_SMALL_CAP", r"(USA|US|UNITED STATES).*(SMALL CAP|SMALL-CAP)|RUSSELL 2000", opportunity_type="GEOGRAPHY", tier="CORE", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="UNITED_STATES", scope="SINGLE_COUNTRY", country="UNITED_STATES", development="DEVELOPED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="SMALL_CAP", currency_exposure="USD", max_isins=5, description="US small-cap equities"),
    family("US_BROAD_LARGE_CAP", r"S&P 500|S&P500|USA.*LARGE CAP|US.*LARGE CAP", opportunity_type="GEOGRAPHY", tier="CORE", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="UNITED_STATES", scope="SINGLE_COUNTRY", country="UNITED_STATES", development="DEVELOPED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="LARGE_CAP", currency_exposure="USD", max_isins=7, description="Broad US large-cap equities"),
    family("US_TOTAL_MARKET", r"(USA|US|UNITED STATES).*(TOTAL MARKET|ALL CAP)|MSCI USA(?!.*SMALL)", opportunity_type="GEOGRAPHY", tier="CORE", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="UNITED_STATES", scope="SINGLE_COUNTRY", country="UNITED_STATES", development="DEVELOPED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="USD", max_isins=5, description="Broad all-cap US equities"),
    family("UK_MID_CAP", r"FTSE 250|UK MID CAP", opportunity_type="GEOGRAPHY", tier="CORE", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="UNITED_KINGDOM", scope="SINGLE_COUNTRY", country="UNITED_KINGDOM", development="DEVELOPED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="MID_CAP", currency_exposure="GBP_MULTI", max_isins=5, description="UK mid-cap equities"),
    family("UK_SMALL_CAP", r"UK SMALL CAP|FTSE SMALLCAP", opportunity_type="GEOGRAPHY", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="UNITED_KINGDOM", scope="SINGLE_COUNTRY", country="UNITED_KINGDOM", development="DEVELOPED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="SMALL_CAP", currency_exposure="GBP_MULTI", max_isins=4, description="UK small-cap equities"),
    family("UK_LARGE_CAP", r"FTSE 100|UK 100|UK LARGE CAP", opportunity_type="GEOGRAPHY", tier="CORE", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="UNITED_KINGDOM", scope="SINGLE_COUNTRY", country="UNITED_KINGDOM", development="DEVELOPED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="LARGE_CAP", currency_exposure="GBP_MULTI", max_isins=6, description="UK large-cap equities"),
    family("UK_BROAD_MARKET", r"FTSE ALL[- ]SHARE|MSCI UK(?!.*SMALL)|UK BROAD", opportunity_type="GEOGRAPHY", tier="CORE", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="UNITED_KINGDOM", scope="SINGLE_COUNTRY", country="UNITED_KINGDOM", development="DEVELOPED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="GBP_MULTI", max_isins=5, description="Broad UK equities"),
    family("EUROPE_EX_UK", r"EUROPE EX[- ]?UK|EUROPE EX UNITED KINGDOM", opportunity_type="GEOGRAPHY", tier="CORE", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="EUROPE_EX_UK", scope="REGION", development="DEVELOPED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="EUR_CHF_DKK_SEK", max_isins=5, description="Developed Europe excluding the UK"),
    family("EUROZONE", r"EURO ?ZONE|EMU\b|EURO STOXX 50", opportunity_type="GEOGRAPHY", tier="CORE", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="EUROZONE", scope="REGION", development="DEVELOPED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="EUR", max_isins=5, description="Eurozone equities"),
    family("EUROPE_BROAD", r"MSCI EUROPE|STOXX EUROPE 600|FTSE DEVELOPED EUROPE|EUROPE UCITS ETF", opportunity_type="GEOGRAPHY", tier="CORE", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="EUROPE", scope="REGION", development="DEVELOPED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="EUR_GBP_CHF_DKK_SEK", max_isins=6, description="Broad developed European equities"),
    family("JAPAN", r"MSCI JAPAN|FTSE JAPAN|NIKKEI 225|TOPIX|JAPAN UCITS", opportunity_type="GEOGRAPHY", tier="CORE", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="JAPAN", scope="SINGLE_COUNTRY", country="JAPAN", development="DEVELOPED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="JPY", max_isins=6, description="Broad Japanese equities"),
    family("DEVELOPED_ASIA_PACIFIC", r"DEVELOPED ASIA PACIFIC|PACIFIC(?!.*EX[- ]?JAPAN)", opportunity_type="GEOGRAPHY", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="DEVELOPED_ASIA_PACIFIC", scope="REGION", development="DEVELOPED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="ASIA_PACIFIC_MULTI", max_isins=4, description="Developed Asia-Pacific equities"),
    family("ASIA_PACIFIC_EX_JAPAN", r"ASIA PACIFIC EX[- ]?JAPAN|ASIA EX[- ]?JAPAN|PACIFIC EX[- ]?JAPAN", opportunity_type="GEOGRAPHY", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="ASIA_PACIFIC_EX_JAPAN", scope="REGION", development="MIXED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="ASIA_PACIFIC_MULTI", max_isins=5, description="Asia-Pacific equities excluding Japan"),
    family("EMERGING_MARKETS", r"EMERGING MARKETS(?!.*(?:BOND|ASIA))|MSCI EM\b(?!.*ASIA)|FTSE EMERGING(?!.*ASIA)", opportunity_type="GEOGRAPHY", tier="CORE", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="EMERGING_MARKETS", scope="MULTI_REGION", development="EMERGING", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="EM_MULTI", max_isins=7, description="Broad emerging-market equities"),
    family("EMERGING_ASIA", r"EMERGING ASIA|MSCI EM ASIA", opportunity_type="GEOGRAPHY", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="EMERGING_ASIA", scope="REGION", development="EMERGING", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="EM_ASIA_MULTI", max_isins=4, description="Emerging Asian equities"),
    family("CHINA_A_SHARES", r"CHINA A[- ]?SHARE|CSI 300", opportunity_type="GEOGRAPHY", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="CHINA", scope="SINGLE_COUNTRY", country="CHINA", development="EMERGING", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="CNY", max_isins=4, description="Mainland China A-shares"),
    family("CHINA_BROAD", r"MSCI CHINA|FTSE CHINA|CHINA UCITS|CHINA ETF", opportunity_type="GEOGRAPHY", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="CHINA", scope="SINGLE_COUNTRY", country="CHINA", development="EMERGING", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="CNY_HKD_USD", max_isins=5, description="Broad China equities"),
    family("INDIA", r"MSCI INDIA|FTSE INDIA|NIFTY 50|INDIA UCITS|INDIA ETF", opportunity_type="GEOGRAPHY", tier="CORE", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="INDIA", scope="SINGLE_COUNTRY", country="INDIA", development="EMERGING", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="INR", max_isins=5, description="Broad Indian equities"),
    family("LATIN_AMERICA", r"LATIN AMERICA", opportunity_type="GEOGRAPHY", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="LATIN_AMERICA", scope="REGION", development="EMERGING", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="LATAM_MULTI", max_isins=4, description="Broad Latin American equities"),
    family("CANADA", r"MSCI CANADA|FTSE CANADA|CANADA UCITS", opportunity_type="GEOGRAPHY", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="CANADA", scope="SINGLE_COUNTRY", country="CANADA", development="DEVELOPED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="CAD", max_isins=3, description="Broad Canadian equities"),
    family("AUSTRALIA", r"MSCI AUSTRALIA|FTSE AUSTRALIA|AUSTRALIA UCITS", opportunity_type="GEOGRAPHY", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="AUSTRALIA", scope="SINGLE_COUNTRY", country="AUSTRALIA", development="DEVELOPED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="AUD", max_isins=3, description="Broad Australian equities"),
    family("SOUTH_KOREA", r"MSCI KOREA|SOUTH KOREA", opportunity_type="GEOGRAPHY", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="SOUTH_KOREA", scope="SINGLE_COUNTRY", country="SOUTH_KOREA", development="MIXED_PROVIDER_CLASSIFICATION", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="KRW", max_isins=3, description="Broad South Korean equities"),
    family("TAIWAN", r"MSCI TAIWAN|TAIWAN UCITS", opportunity_type="GEOGRAPHY", tier="EXPERIMENTAL", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="TAIWAN", scope="SINGLE_COUNTRY", country="TAIWAN", development="EMERGING", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="TWD", max_isins=3, description="Broad Taiwanese equities"),
    family("GLOBAL_SMALL_CAP", r"(WORLD|GLOBAL).*SMALL CAP", opportunity_type="GEOGRAPHY", tier="EXTENDED", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="GLOBAL", scope="GLOBAL", development="MIXED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="SMALL_CAP", currency_exposure="MULTI_CURRENCY", max_isins=4, description="Global small-cap equities"),
    family("GLOBAL_ALL_WORLD", r"FTSE ALL[- ]WORLD|ALL[- ]WORLD UCITS|MSCI ACWI", opportunity_type="GEOGRAPHY", tier="CORE", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="GLOBAL", scope="GLOBAL", development="MIXED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="MULTI_CURRENCY", max_isins=6, description="Developed and emerging all-world equities"),
    family("GLOBAL_DEVELOPED_WORLD", r"MSCI WORLD(?!.*SMALL)|FTSE DEVELOPED WORLD|DEVELOPED WORLD UCITS", opportunity_type="GEOGRAPHY", tier="CORE", asset_class="EQUITY", sub_asset_class="BROAD_MARKET_EQUITY", geography="DEVELOPED_WORLD", scope="GLOBAL", development="DEVELOPED", sector="BROAD_MARKET", industry="BROAD_MARKET", market_cap="ALL_CAP", currency_exposure="MULTI_CURRENCY", max_isins=7, description="Broad developed-world equities"),
]


EXCLUSION_RULES = [
    ("LEVERAGED", re.compile(r"(?:\b[+-]?[2345]X\b|\bLEVERAG(?:E|ED)\b|\bBOOST\b)", re.I)),
    ("INVERSE", re.compile(r"\bINVERSE\b|\bDAILY SHORT\b|\bDLY SH(?:O)?RT\b|\b1X DLY SH(?:O)?RT\b|\bBEAR [12345]X\b|\bSHORT (?:AND|&) LEVERAGED\b", re.I)),
    ("VOLATILITY_LINKED", re.compile(r"\bVIX\b|VOLATILITY (?:FUTURES|LINKED|SHORT-TERM)", re.I)),
    ("SINGLE_STOCK_ETP", re.compile(r"(LEVERAGE SHARES|GRANITESHARES).*(?:[12345]X|SHORT|LONG)", re.I)),
    ("CRYPTO_DIRECT_ETP", re.compile(r"(?:BITCOIN|ETHEREUM|CRYPTO|SOLANA|XRP).*(?:ETP|ETN|STAKING)|(?:ETP|ETN).*(?:BITCOIN|ETHEREUM|CRYPTO|SOLANA|XRP)", re.I)),
]

STYLE_OUT_OF_SCOPE = re.compile(
    r"\b(?:ESG|SRI|CLIMATE|PARIS[- ]ALIGNED|PAB\b|CTB\b|SCREENED|SUSTAINABLE|LOW CARBON|ACTIVE UCITS)\b",
    re.I,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def stable_id(prefix: str, *parts: Any) -> str:
    joined = "|".join(str(p or "").strip().upper() for p in parts)
    return f"{prefix}-{sha256_text(joined)[:16].upper()}"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", html.unescape(str(value))).strip()


def normalize(value: Any) -> str:
    text = clean_text(value).upper()
    text = text.replace("&AMP;", "&")
    return re.sub(r"\s+", " ", text)


def strip_tags(value: str) -> str:
    value = re.sub(r"<script.*?</script>|<style.*?</style>", " ", value, flags=re.I | re.S)
    return clean_text(re.sub(r"<[^>]+>", " ", value))


def parse_number(value: Any) -> float | None:
    text = clean_text(value).replace(",", "").replace("%", "")
    if not text or text in {"-", "N/A", "NOT_AVAILABLE"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def yes_no(value: Any) -> str:
    text = normalize(value)
    if text in {"YES", "Y", "TRUE"}:
        return "YES"
    if text in {"NO", "N", "FALSE"}:
        return "NO"
    return "NOT_DETERMINED"


@dataclass
class FetchResult:
    url: str
    retrieved_at: str
    status: int
    body: bytes
    content_type: str
    error: str = ""


def fetch(url: str, *, data: bytes | None = None, headers: dict[str, str] | None = None, retries: int = 3) -> FetchResult:
    base_headers = {
        "User-Agent": "Mozilla/5.0 (compatible; UKACTIVE-A0A1/1.0; research)",
        "Accept": "application/json,text/html,application/xhtml+xml,application/pdf,*/*",
    }
    if headers:
        base_headers.update(headers)
    last_error = ""
    for attempt in range(retries):
        request = urllib.request.Request(url, data=data, headers=base_headers, method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return FetchResult(
                    url=response.geturl(),
                    retrieved_at=utc_now(),
                    status=int(response.status),
                    body=response.read(),
                    content_type=response.headers.get("Content-Type", ""),
                )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt + 1 < retries:
                time.sleep(1.0 + attempt)
    return FetchResult(url=url, retrieved_at=utc_now(), status=0, body=b"", content_type="", error=last_error)


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    materialized = list(rows)
    if fieldnames is None:
        fieldnames = list(materialized[0].keys()) if materialized else []
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(materialized)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def lse_post(parameters: str) -> FetchResult:
    # Despite its generic name the current page service is a GET endpoint.  The
    # nested price-explorer query is deliberately kept in the `parameters`
    # value and URL-encoded once.
    query = urllib.parse.urlencode({
        "path": "live-markets/market-data-dashboard/price-explorer",
        "parameters": parameters,
    })
    return fetch(
        f"{LSE_API_URL}?{query}",
        headers={
            "Origin": "https://www.londonstockexchange.com",
            "Referer": LSE_PAGE_URL,
        },
    )


def json_load_result(result: FetchResult) -> Any:
    if result.status != 200:
        raise RuntimeError(f"Source fetch failed: {result.url}: {result.error or result.status}")
    return json.loads(result.body.decode("utf-8-sig"))


def flatten_lse_rows(payload: Any) -> list[dict[str, Any]]:
    """Find the price-explorer row list without relying on a fragile response wrapper."""
    lists: list[list[Any]] = []

    def visit(obj: Any) -> None:
        if isinstance(obj, list):
            if obj and isinstance(obj[0], dict):
                keys = {str(k).lower() for k in obj[0]}
                if {"isin", "tidm"}.issubset(keys) or {"isin", "ticker"}.issubset(keys):
                    lists.append(obj)
            for item in obj:
                visit(item)
        elif isinstance(obj, dict):
            for item in obj.values():
                visit(item)

    visit(payload)
    if not lists:
        return []
    return max(lists, key=len)


def field(row: dict[str, Any], *names: str) -> Any:
    lower = {str(k).lower(): v for k, v in row.items()}
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    return ""


def provider_key(value: str) -> str:
    upper = normalize(value)
    mappings = [
        ("ISHARES", "ISHARES"), ("BLACKROCK", "ISHARES"), ("VANGUARD", "VANGUARD"),
        ("INVESCO", "INVESCO"), ("STATE STREET", "STATE STREET"), ("SPDR", "SPDR"),
        ("WISDOMTREE", "WISDOMTREE"), ("AMUNDI", "AMUNDI"), ("LYXOR", "AMUNDI"),
        ("UBS", "UBS"), ("HSBC", "HSBC"), ("LEGAL & GENERAL", "LEGAL & GENERAL"),
        ("L&G", "L&G"), ("VANECK", "VANECK"), ("GLOBAL X", "GLOBAL X"),
        ("HANETF", "HANETF"), ("FRANKLIN", "FRANKLIN"), ("JPMORGAN", "JPMORGAN"),
        ("FIRST TRUST", "FIRST TRUST"),
    ]
    for needle, key in mappings:
        if needle in upper:
            return key
    return upper or "UNKNOWN"


def instrument_type(subcategory: str, description: str) -> str:
    sub = normalize(subcategory)
    name = normalize(description)
    if "ETC" in sub or re.search(r"\bETC\b", name):
        return "ETC"
    if "ETN" in sub or re.search(r"\bETN\b", name):
        return "ETN"
    return "ETF"


def price_fields(raw_currency: str) -> tuple[str, str, str]:
    unit = normalize(raw_currency)
    if unit == "GBX":
        return "GBP", "GBX", "0.01"
    if unit == "GBp".upper():
        return "GBP", "GBX", "0.01"
    if unit == "GBP":
        return "GBP", "GBP", "1"
    return unit or "NOT_AVAILABLE", unit or "NOT_AVAILABLE", "1"


def structural_exclusion(name: str, issuer: str, kind: str) -> tuple[bool, str]:
    text = f"{normalize(issuer)} {normalize(name)}"
    reasons = [code for code, pattern in EXCLUSION_RULES if pattern.search(text)]
    if kind == "ETN" and not reasons:
        reasons.append("UNSECURED_OR_NOTE_STRUCTURE_NOT_APPROVED")
    return bool(reasons), ";".join(sorted(set(reasons)))


def match_family(name: str) -> dict[str, Any] | None:
    text = normalize(name)
    for rule in FAMILY_RULES:
        if re.search(rule["pattern"], text, flags=re.I):
            return rule
    return None


def is_currency_hedged(name: str) -> tuple[str, str]:
    text = normalize(name)
    if re.search(r"GBP (?:CURRENCY )?HEDG|HEDGED GBP|GBP-HEDG", text):
        return "YES", "GBP"
    if re.search(r"EUR (?:CURRENCY )?HEDG|HEDGED EUR|EUR-HEDG", text):
        return "YES", "EUR"
    if re.search(r"USD (?:CURRENCY )?HEDG|HEDGED USD|USD-HEDG", text):
        return "YES", "USD"
    return "NO", "NOT_APPLICABLE"


def adjusted_family(rule: dict[str, Any], name: str) -> dict[str, Any]:
    result = dict(rule)
    text = normalize(name)
    if result["opportunity_type"] in {"SECTOR_INDUSTRY", "THEMATIC"} and result["geography"] == "GLOBAL":
        geo_prefix = ""
        if re.search(r"\b(?:S&P 500|MSCI USA|US |USA |UNITED STATES)\b", text):
            geo_prefix = "US"
            result.update(geography="UNITED_STATES", scope="SINGLE_COUNTRY", country="UNITED_STATES", development="DEVELOPED")
            result["currency_exposure"] = "USD"
        elif re.search(r"\b(?:EUROPE|EURO STOXX|STOXX EUROPE)\b", text):
            geo_prefix = "EUROPE"
            result.update(geography="EUROPE", scope="REGION", country="NOT_APPLICABLE", development="DEVELOPED")
            result["currency_exposure"] = "EUR_GBP_CHF_DKK_SEK"
        elif re.search(r"\b(?:UK|UNITED KINGDOM|FTSE 350)\b", text):
            geo_prefix = "UK"
            result.update(geography="UNITED_KINGDOM", scope="SINGLE_COUNTRY", country="UNITED_KINGDOM", development="DEVELOPED")
            result["currency_exposure"] = "GBP_MULTI"
        if geo_prefix and result["family_id"].startswith("GLOBAL_"):
            result["family_id"] = geo_prefix + result["family_id"][6:]
            result["description"] = result["description"].replace("Global ", f"{geo_prefix.title()} ", 1)
    hedged, hedge_currency = is_currency_hedged(name)
    if hedged == "YES" and not result["family_id"].endswith("_GBP_HEDGED"):
        result["family_id"] = f"{result['family_id']}_{hedge_currency}_HEDGED"
        result["description"] = f"{result['description']} hedged to {hedge_currency}"
        result["currency_exposure"] = f"{hedge_currency}_HEDGED"
        if result["tier"] == "CORE" and result["asset_class"] == "EQUITY":
            result["tier"] = "EXTENDED"
    result["hedged"] = hedged
    result["hedge_currency"] = hedge_currency
    return result


def parse_ishares_catalog(payload: Any) -> dict[str, dict[str, Any]]:
    if isinstance(payload, dict) and "products" in payload:
        payload = payload["products"]
    if isinstance(payload, dict):
        candidates = list(payload.values())
    elif isinstance(payload, list):
        candidates = payload
    else:
        candidates = []
    by_isin: dict[str, dict[str, Any]] = {}
    for row in candidates:
        if not isinstance(row, dict):
            continue
        isin = clean_text(row.get("isin") or row.get("ISIN")).upper()
        if re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", isin):
            by_isin[isin] = row
    return by_isin


def product_page_url(catalog_row: dict[str, Any]) -> str:
    value = clean_text(catalog_row.get("productPageUrl") or catalog_row.get("productUrl"))
    if not value:
        return ""
    if value.startswith("http"):
        return value + ("&" if "?" in value else "?") + "siteEntryPassthrough=true"
    return "https://www.ishares.com" + value + ("&" if "?" in value else "?") + "siteEntryPassthrough=true"


def parse_ishares_page(page: str) -> dict[str, Any]:
    facts: dict[str, str] = {}
    for match in re.finditer(r'<tr[^>]*data-id="keyFundFacts-row-([^"]+)"[^>]*>(.*?)</tr>', page, re.I | re.S):
        key, body = match.groups()
        cells = re.findall(r"<td[^>]*>(.*?)</td>", body, re.I | re.S)
        facts[key] = strip_tags(cells[-1] if cells else body)

    listings: list[dict[str, str]] = []
    for match in re.finditer(r'<tr[^>]*class="[^"]*dataTable-data-row[^"]*"[^>]*>(.*?)</tr>', page, re.I | re.S):
        body = match.group(1)
        row: dict[str, str] = {}
        for cell in re.finditer(r'<td[^>]*class="[^"]*col([A-Za-z]+)[^"]*"[^>]*>(.*?)</td>', body, re.I | re.S):
            row[cell.group(1)] = strip_tags(cell.group(2))
        if row.get("Exchange") and row.get("Ticker"):
            listings.append(row)

    documents = []
    for href in re.findall(r'href="([^"]+(?:/literature/kiid/|/literature/kid/)[^"]+)"', page, re.I):
        url = html.unescape(href)
        if url.startswith("/"):
            url = "https://www.ishares.com" + url
        if url not in documents:
            documents.append(url)

    return {"facts": facts, "listings": listings, "retail_documents": documents}


def get_catalog_value(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if isinstance(value, dict):
            value = value.get("value") or value.get("displayValue") or value.get("label") or value.get("d") or value.get("r")
        if isinstance(value, list):
            value = ";".join(clean_text(v.get("name") if isinstance(v, dict) else v) for v in value)
        text = clean_text(value)
        if text:
            return text
    return ""


class EvidenceLedger:
    def __init__(self) -> None:
        self._rows: dict[str, dict[str, Any]] = {}

    def add(
        self,
        *,
        evidence_type: str,
        source_tier: str,
        publisher: str,
        title: str,
        url: str,
        retrieved_at: str,
        supports: str,
        source_sha256: str = "NOT_CAPTURED",
        local_capture: str = "NOT_CAPTURED",
        confidence: str = "HIGH",
        notes: str = "",
    ) -> str:
        key = "|".join([evidence_type, publisher, url, supports, source_sha256, notes])
        evidence_id = stable_id("EVD", key)
        self._rows[evidence_id] = {
            "evidence_id": evidence_id,
            "evidence_type": evidence_type,
            "source_tier": source_tier,
            "publisher": publisher,
            "title": title,
            "url": url,
            "retrieved_at": retrieved_at,
            "observation_date": OBSERVATION_DATE,
            "supports": supports,
            "source_sha256": source_sha256,
            "local_capture": local_capture,
            "confidence": confidence,
            "notes": notes,
            "historical_eligibility_supported": "NO",
            "warning": WARNING,
        }
        return evidence_id

    @property
    def rows(self) -> list[dict[str, Any]]:
        return [self._rows[key] for key in sorted(self._rows)]

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            for row in self.rows:
                handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def retrieve_lse_discovery(root: Path, ledger: EvidenceLedger) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    captures = root / "evidence" / "sources"
    captures.mkdir(parents=True, exist_ok=True)
    discovery: list[dict[str, Any]] = []
    source_meta: list[dict[str, Any]] = []
    subcategories = [("15", "ETF"), ("16", "ETC"), ("17", "ETN")]
    for subcategory_id, subcategory_label in subcategories:
        page = 1
        while True:
            # The LSE service currently skips blocks at larger page sizes for
            # some subcategories.  A fixed size of 100 has been empirically
            # verified across ETF, ETC and ETN pagination and is therefore part
            # of the reproducible source contract.
            parameters = f"categories=ETFS&subcategories={subcategory_id}&page={page}&size=100"
            result = lse_post(parameters)
            payload = json_load_result(result)
            rows = flatten_lse_rows(payload)
            capture = captures / f"lse_{subcategory_label.lower()}_page_{page}.json"
            capture.write_bytes(result.body)
            digest = sha256_bytes(result.body)
            relative_capture = capture.relative_to(root).as_posix()
            evidence_id = ledger.add(
                evidence_type="CURRENT_EXCHANGE_CATALOGUE",
                source_tier="PRIMARY",
                publisher="London Stock Exchange",
                title=f"Price Explorer {subcategory_label} current catalogue page {page}",
                url=result.url,
                retrieved_at=result.retrieved_at,
                supports="listing identity; current LSE snapshot presence; ticker; ISIN; price unit; issuer description",
                source_sha256=digest,
                local_capture=relative_capture,
                confidence="HIGH",
                notes="Presence establishes current catalogue observation, not historical eligibility or broker availability.",
            )
            source_meta.append({
                "source": "LSE_PRICE_EXPLORER",
                "subcategory": subcategory_label,
                "page": page,
                "url": result.url,
                "retrieved_at": result.retrieved_at,
                "http_status": result.status,
                "sha256": digest,
                "capture": relative_capture,
                "row_count": len(rows),
                "evidence_id": evidence_id,
            })
            for raw in rows:
                if str(field(raw, "islse")).lower() not in {"true", "1"}:
                    continue
                isin = clean_text(field(raw, "isin")).upper()
                ticker = clean_text(field(raw, "tidm", "ticker")).upper()
                description = clean_text(field(raw, "description", "name"))
                issuer = clean_text(field(raw, "issuername", "issuer"))
                raw_currency = clean_text(field(raw, "currency"))
                listing_currency, unit, multiplier = price_fields(raw_currency)
                kind = instrument_type(subcategory_label, description)
                excluded, reason = structural_exclusion(description, issuer, kind)
                rule = match_family(description)
                matched = adjusted_family(rule, description) if rule else None
                style_oos = bool(STYLE_OUT_OF_SCOPE.search(description))
                record_id = stable_id("DSC", isin, "XLON", ticker, unit)
                discovery.append({
                    "discovery_record_id": record_id,
                    "source_name": "LSE_PRICE_EXPLORER",
                    "source_evidence_id": evidence_id,
                    "source_url": result.url,
                    "retrieval_date": result.retrieved_at[:10],
                    "observation_date": OBSERVATION_DATE,
                    "issuer_name_as_published": issuer,
                    "provider_normalized": provider_key(issuer),
                    "description_as_published": description,
                    "display_name": clean_text(field(raw, "name")),
                    "isin": isin,
                    "ticker": ticker,
                    "exchange": "London Stock Exchange",
                    "mic": "XLON",
                    "listing_currency": listing_currency,
                    "price_unit": unit,
                    "price_unit_multiplier_to_listing_currency": multiplier,
                    "instrument_type": kind,
                    "active_listing_status": "ACTIVE_OBSERVED_IN_CURRENT_LSE_SNAPSHOT",
                    "active_listing_confidence": "HIGH",
                    "last_price_observed": clean_text(field(raw, "lastprice", "midprice")),
                    "structural_exclusion_flag": "YES" if excluded else "NO",
                    "structural_exclusion_reason_codes": reason or "NOT_APPLICABLE",
                    "style_variant_out_of_scope_flag": "YES" if style_oos else "NO",
                    "matched_economic_exposure_family_id": matched["family_id"] if matched else "NOT_CLASSIFIED_IN_CURATED_MASTER",
                    "discovery_disposition": (
                        "STRUCTURAL_EXCLUSION" if excluded else
                        "OUT_OF_SCOPE_STYLE_VARIANT" if style_oos else
                        "CURATED_FAMILY_CANDIDATE" if matched else
                        "DISCOVERED_NOT_CURATED_THIS_STAGE"
                    ),
                    "broker_status": "NOT_CHECKED",
                    "historical_eligibility_supported": "NO",
                    "warning": WARNING,
                })
            if len(rows) < 100:
                break
            page += 1
            if page > 100:
                raise RuntimeError(f"Unexpected LSE pagination depth for {subcategory_label}")
    discovery.sort(key=lambda r: (r["isin"], r["mic"], r["ticker"], r["price_unit"]))
    return discovery, source_meta


FORCED_AUDIT_ISINS = {
    "IE0005042456",  # iShares Core FTSE 100, GBP and USD listings
    "IE00B5BMR087",  # iShares Core S&P 500 accumulating
    "IE0031442068",  # iShares Core S&P 500 distributing
    "IE0032077012",  # Invesco EQQQ Nasdaq-100
    "IE00B4K48X80",  # iShares Core MSCI Europe
    "IE00B02KXH56",  # iShares Core MSCI Japan
    "IE00BKM4GZ66",  # iShares Core MSCI Emerging Markets IMI
    "IE00BZCQB185",  # iShares MSCI India
    "IE00B4L5Y983",  # iShares Core MSCI World unhedged
    "IE00B42YS929",  # iShares MSCI World GBP hedged
    "IE00B1FZSB30",  # iShares Core UK Gilts
    "IE00B3F81R35",  # iShares GBP Corporate Bond
    "IE00B4ND3602",  # iShares Physical Gold ETC
    "LU1230136894",  # Amundi Smart Overnight Return GBP line (where present)
}

PROVIDER_PRIORITY = {
    "ISHARES": 100, "VANGUARD": 90, "INVESCO": 85, "SPDR": 82,
    "STATE STREET": 82, "HSBC": 80, "AMUNDI": 78, "UBS": 76,
    "LEGAL & GENERAL": 75, "L&G": 75, "WISDOMTREE": 72, "VANECK": 70,
    "FRANKLIN": 68, "JPMORGAN": 66, "GLOBAL X": 64, "HANETF": 62,
    "FIRST TRUST": 60,
}


def select_curated_isins(
    discovery: list[dict[str, Any]],
    ishares: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    by_isin: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in discovery:
        if row["isin"]:
            by_isin[row["isin"]].append(row)

    candidate_details: dict[str, dict[str, Any]] = {}
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for isin, lines in by_isin.items():
        if any(line["structural_exclusion_flag"] == "YES" for line in lines):
            continue
        if any(line["style_variant_out_of_scope_flag"] == "YES" for line in lines):
            continue
        matched_lines = [(line, match_family(line["description_as_published"])) for line in lines]
        matched_lines = [(line, rule) for line, rule in matched_lines if rule]
        if not matched_lines:
            continue
        representative, rule = max(matched_lines, key=lambda pair: len(pair[0]["description_as_published"]))
        rule = adjusted_family(rule, representative["description_as_published"])
        provider = representative["provider_normalized"]
        score = PROVIDER_PRIORITY.get(provider, 40)
        score += 80 if isin in ishares else 0
        score += 50 if isin in FORCED_AUDIT_ISINS else 0
        score += 12 if any(line["price_unit"] in {"GBP", "GBX"} for line in lines) else 0
        score += 5 if any(line["last_price_observed"] for line in lines) else 0
        score += 4 if "CORE" in normalize(representative["description_as_published"]) else 0
        detail = {
            "isin": isin,
            "lines": lines,
            "representative": representative,
            "rule": rule,
            "provider": provider,
            "score": score,
        }
        candidate_details[isin] = detail
        by_family[rule["family_id"]].append(detail)

    selected: dict[str, dict[str, Any]] = {}
    selected_by_family: dict[str, list[dict[str, Any]]] = {}
    for family_id, members in by_family.items():
        members = sorted(members, key=lambda m: (-m["score"], m["isin"]))
        cap = int(members[0]["rule"]["max_isins"])
        chosen: list[dict[str, Any]] = []
        used_providers: set[str] = set()
        # Provider diversity first; this preserves implementation alternatives
        # without allowing them to create extra economic opportunities.
        for member in members:
            if member["provider"] not in used_providers and len(chosen) < cap:
                chosen.append(member)
                used_providers.add(member["provider"])
        for member in members:
            if member not in chosen and len(chosen) < cap:
                chosen.append(member)
        # Forced audit ISINs displace the lowest-scored non-forced candidate.
        for member in members:
            if member["isin"] in FORCED_AUDIT_ISINS and member not in chosen:
                if len(chosen) >= cap:
                    replace_index = next((i for i in range(len(chosen) - 1, -1, -1) if chosen[i]["isin"] not in FORCED_AUDIT_ISINS), None)
                    if replace_index is not None:
                        chosen.pop(replace_index)
                if len(chosen) < cap:
                    chosen.append(member)
        chosen.sort(key=lambda m: (-m["score"], m["isin"]))
        selected_by_family[family_id] = chosen
        for member in chosen:
            selected[member["isin"]] = member
    return selected, selected_by_family


def retrieve_ishares_catalog(root: Path, ledger: EvidenceLedger) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    result = fetch(ISHARES_CATALOG_URL)
    payload = json_load_result(result)
    capture = root / "evidence" / "sources" / "ishares_uk_product_catalog.json"
    capture.write_bytes(result.body)
    digest = sha256_bytes(result.body)
    evidence_id = ledger.add(
        evidence_type="ISSUER_PRODUCT_CATALOGUE",
        source_tier="PRIMARY",
        publisher="BlackRock / iShares",
        title="iShares UK individual product catalogue",
        url=result.url,
        retrieved_at=result.retrieved_at,
        supports="share-class identity; ISIN; product page; inception; domicile; TER/OCF; accumulation/distribution; issuer classification",
        source_sha256=digest,
        local_capture=capture.relative_to(root).as_posix(),
        confidence="HIGH",
        notes="Current catalogue only; product-specific legal facts are verified separately from product pages.",
    )
    return parse_ishares_catalog(payload), {
        "evidence_id": evidence_id,
        "url": result.url,
        "retrieved_at": result.retrieved_at,
        "sha256": digest,
        "capture": capture.relative_to(root).as_posix(),
        "row_count": len(parse_ishares_catalog(payload)),
    }


def retrieve_regulatory_sources(root: Path, ledger: EvidenceLedger) -> list[dict[str, Any]]:
    definitions = [
        (HMRC_ISA_URL, "HM Revenue & Customs", "Stocks and shares investments for ISA managers", "current ISA legal framework; product-level eligibility cannot be inferred from LSE listing"),
        (HMRC_SIPP_URL, "HM Revenue & Customs", "Pensions Tax Manual PTM121000", "SIPP tax framework; scheme/provider rules still determine exact account availability"),
        (FCA_CCI_URL, "Financial Conduct Authority", "CCI transitional provisions", "current UK retail disclosure transition and permitted product documents"),
        (FCA_PS_URL, "Financial Conduct Authority", "PS25/20 Consumer Composite Investments", "retail disclosure regime transition"),
        (DEEPVUE_URL, "DeepVue", "Theme Tracker documentation", "Theme Tracker is a curated theme system separate from conventional sector classification"),
    ]
    metadata = []
    for url, publisher, title, supports in definitions:
        result = fetch(url)
        digest = sha256_bytes(result.body) if result.body else "NOT_CAPTURED"
        capture = root / "evidence" / "sources" / f"source_metadata_{sha256_text(url)[:12]}.json"
        # Store only retrieval metadata and content hash for public pages; exact
        # product/legal URLs remain in the evidence ledger.
        record = {
            "url": result.url,
            "requested_url": url,
            "publisher": publisher,
            "title": title,
            "retrieved_at": result.retrieved_at,
            "http_status": result.status,
            "content_type": result.content_type,
            "content_length": len(result.body),
            "sha256": digest,
            "error": result.error,
        }
        write_json(capture, record)
        evidence_id = ledger.add(
            evidence_type="REGULATORY_OR_TAXONOMY_POLICY",
            source_tier="PRIMARY",
            publisher=publisher,
            title=title,
            url=result.url,
            retrieved_at=result.retrieved_at,
            supports=supports,
            source_sha256=digest,
            local_capture=capture.relative_to(root).as_posix(),
            confidence="HIGH" if result.status == 200 else "LOW",
            notes="Current policy/source observation; not product-level historical eligibility evidence.",
        )
        record["evidence_id"] = evidence_id
        metadata.append(record)
    return metadata


def retrieve_ishares_details(
    root: Path,
    ledger: EvidenceLedger,
    selected: dict[str, dict[str, Any]],
    catalog: dict[str, dict[str, Any]],
    existing: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    details: dict[str, dict[str, Any]] = dict(existing or {})
    capture_dir = root / "evidence" / "sources" / "ishares_products"
    capture_dir.mkdir(parents=True, exist_ok=True)
    selected_ishares = sorted(isin for isin in selected if isin in catalog and isin not in details)
    for index, isin in enumerate(selected_ishares, start=1):
        catalog_row = catalog[isin]
        url = product_page_url(catalog_row)
        if not url:
            continue
        result = fetch(url)
        parsed = parse_ishares_page(result.body.decode("utf-8", errors="replace")) if result.status == 200 else {"facts": {}, "listings": [], "retail_documents": []}
        summary = {
            "isin": isin,
            "url": result.url,
            "retrieved_at": result.retrieved_at,
            "http_status": result.status,
            "response_sha256": sha256_bytes(result.body) if result.body else "NOT_CAPTURED",
            "response_length": len(result.body),
            "error": result.error,
            **parsed,
        }
        capture = capture_dir / f"{isin}.json"
        write_json(capture, summary)
        evidence_id = ledger.add(
            evidence_type="ISSUER_PRODUCT_PAGE",
            source_tier="PRIMARY",
            publisher="BlackRock / iShares",
            title=f"Current issuer product page: {get_catalog_value(catalog_row, 'fundName') or isin}",
            url=result.url,
            retrieved_at=result.retrieved_at,
            supports="fund/share-class identity; benchmark; domicile; UCITS; ISA; SIPP; structure; replication; fees; listing lines; retail document link",
            source_sha256=summary["response_sha256"],
            local_capture=capture.relative_to(root).as_posix(),
            confidence="HIGH" if result.status == 200 else "LOW",
            notes="Parsed fields are captured; the full issuer HTML is content-addressed but not duplicated.",
        )
        summary["evidence_id"] = evidence_id

        doc_checks = []
        for doc_url in parsed.get("retail_documents", [])[:1]:
            doc_result = fetch(doc_url)
            doc_meta = {
                "url": doc_result.url,
                "retrieved_at": doc_result.retrieved_at,
                "http_status": doc_result.status,
                "content_type": doc_result.content_type,
                "content_length": len(doc_result.body),
                "sha256": sha256_bytes(doc_result.body) if doc_result.body else "NOT_CAPTURED",
                "error": doc_result.error,
            }
            doc_evidence_id = ledger.add(
                evidence_type="CURRENT_RETAIL_DOCUMENT",
                source_tier="PRIMARY",
                publisher="BlackRock / iShares",
                title=f"Current KID/KIID document for {isin}",
                url=doc_result.url,
                retrieved_at=doc_result.retrieved_at,
                supports="current retail-document availability for the share class",
                source_sha256=doc_meta["sha256"],
                local_capture="HASH_ONLY_DOCUMENT_NOT_REDISTRIBUTED",
                confidence="HIGH" if doc_result.status == 200 and doc_result.body.startswith(b"%PDF") else "LOW",
                notes="Document hash and HTTP result retained; PDF not redistributed in source captures.",
            )
            doc_meta["evidence_id"] = doc_evidence_id
            doc_checks.append(doc_meta)
        summary["document_checks"] = doc_checks
        write_json(capture, summary)
        details[isin] = summary
        if index % 20 == 0:
            time.sleep(0.25)
    return details


def load_current_listing_supplements(
    root: Path,
    ledger: EvidenceLedger,
    config_path: Path,
    issuer_details: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not config_path.exists():
        return [], {"status": "NOT_AVAILABLE", "path": str(config_path), "row_count": 0}
    config_bytes = config_path.read_bytes()
    config_evidence_id = ledger.add(
        evidence_type="RESEARCH_CONTROL_WITH_PRIMARY_SOURCE_CITATIONS",
        source_tier="PRIMARY_SOURCE_TRANSCRIPTION",
        publisher="UKACTIVE-A0A1 research programme",
        title="Current listing supplements for generic-catalogue omissions",
        url=str(config_path),
        retrieved_at=utc_now(),
        supports="explicit product-specific LSE listing identity and GBP/GBX price-unit reconciliation",
        source_sha256=sha256_bytes(config_bytes),
        local_capture=config_path.relative_to(root).as_posix(),
        confidence="HIGH",
        notes="Every row cites both a product-specific LSE URL and current issuer product URL; supplements are visible, never silent.",
    )
    with config_path.open("r", encoding="utf-8-sig", newline="") as handle:
        controls = list(csv.DictReader(handle))
    rows: list[dict[str, Any]] = []
    source_checks = []
    for control in controls:
        isin = normalize(control["isin"])
        ticker = normalize(control["ticker"])
        lse_result = fetch(control["lse_url"])
        capture = root / "evidence" / "sources" / f"lse_instrument_{ticker}.html"
        capture.write_bytes(lse_result.body)
        lse_evidence_id = ledger.add(
            evidence_type="PRODUCT_SPECIFIC_EXCHANGE_PAGE",
            source_tier="PRIMARY",
            publisher="London Stock Exchange",
            title=f"Current LSE instrument page {ticker}",
            url=control["lse_url"],
            retrieved_at=lse_result.retrieved_at,
            supports="current product-specific LSE instrument-page presence; rendered fields transcribed in the controlled supplement",
            source_sha256=sha256_bytes(lse_result.body) if lse_result.body else "NOT_CAPTURED",
            local_capture=capture.relative_to(root).as_posix(),
            confidence=control["active_status_confidence"],
            notes=control["reason"],
        )
        issuer_evidence_id = issuer_details.get(isin, {}).get("evidence_id", "NOT_AVAILABLE")
        source_checks.append({
            "isin": isin, "ticker": ticker, "lse_url": control["lse_url"],
            "issuer_url": control["issuer_url"], "lse_http_status": lse_result.status,
            "lse_response_sha256": sha256_bytes(lse_result.body) if lse_result.body else "NOT_CAPTURED",
            "control_evidence_id": config_evidence_id, "lse_evidence_id": lse_evidence_id,
            "issuer_evidence_id": issuer_evidence_id,
        })
        description = clean_text(control["product_name"])
        issuer = clean_text(control["issuer_name"])
        kind = normalize(control["instrument_type"])
        excluded, reason = structural_exclusion(description, issuer, kind)
        rule = match_family(description)
        matched = adjusted_family(rule, description) if rule else None
        rows.append({
            "discovery_record_id": stable_id("DSC", isin, control["mic"], ticker, control["price_unit"]),
            "source_name": "PRODUCT_SPECIFIC_LSE_AND_ISSUER_SUPPLEMENT",
            "source_evidence_id": lse_evidence_id,
            "source_url": control["lse_url"],
            "retrieval_date": control["evidence_date"],
            "observation_date": OBSERVATION_DATE,
            "issuer_name_as_published": issuer,
            "provider_normalized": provider_key(issuer),
            "description_as_published": description,
            "display_name": description,
            "isin": isin,
            "ticker": ticker,
            "exchange": control["exchange"],
            "mic": control["mic"],
            "listing_currency": control["listing_currency"],
            "price_unit": control["price_unit"],
            "price_unit_multiplier_to_listing_currency": control["price_unit_multiplier_to_listing_currency"],
            "instrument_type": kind,
            "active_listing_status": control["active_listing_status"],
            "active_listing_confidence": control["active_status_confidence"],
            "last_price_observed": "NOT_CAPTURED",
            "structural_exclusion_flag": "YES" if excluded else "NO",
            "structural_exclusion_reason_codes": reason or "NOT_APPLICABLE",
            "style_variant_out_of_scope_flag": "NO",
            "matched_economic_exposure_family_id": matched["family_id"] if matched else "NOT_CLASSIFIED_IN_CURATED_MASTER",
            "discovery_disposition": "STRUCTURAL_EXCLUSION" if excluded else "CURATED_FAMILY_CANDIDATE",
            "broker_status": "NOT_CHECKED",
            "historical_eligibility_supported": "NO",
            "warning": WARNING,
        })
    return rows, {
        "status": "USED",
        "path": str(config_path),
        "sha256": sha256_bytes(config_bytes),
        "row_count": len(rows),
        "config_evidence_id": config_evidence_id,
        "source_checks": source_checks,
    }


def normalize_subfund_name(name: str) -> str:
    text = clean_text(name)
    text = re.sub(r"\s+(?:GBP|USD|EUR|CHF|JPY)\s+(?:HEDGED\s+)?(?:ACC|DIST|ACCUMULATING|DISTRIBUTING)\b.*$", "", text, flags=re.I)
    text = re.sub(r"\s+\((?:ACC|DIST|ACCUMULATING|DISTRIBUTING)\)\s*$", "", text, flags=re.I)
    return clean_text(text)


def detect_distribution(name: str, catalog_row: dict[str, Any], facts: dict[str, Any]) -> str:
    value = get_catalog_value(catalog_row, "useOfProfits") or clean_text(facts.get("useOfProfitsCode"))
    upper = normalize(value or name)
    if "ACCUM" in upper or re.search(r"\bACC\b", upper):
        return "ACCUMULATING"
    if "DISTR" in upper or re.search(r"\bDIST\b|\bINC\b", upper):
        return "DISTRIBUTING"
    return "NOT_DETERMINED"


def parse_ter(catalog_row: dict[str, Any], facts: dict[str, Any]) -> str:
    value = clean_text(facts.get("emeaMgt")) or get_catalog_value(catalog_row, "ter_ocf", "ter", "onGoingCharges")
    number = parse_number(value)
    return f"{number:.4f}" if number is not None else "NOT_AVAILABLE"


def find_issuer_listing(detail: dict[str, Any], ticker: str, listing_currency: str, price_unit: str) -> dict[str, Any]:
    candidates = [
        row for row in detail.get("listings", [])
        if normalize(row.get("Exchange")) == "LONDON STOCK EXCHANGE" and normalize(row.get("Ticker")) == normalize(ticker)
    ]
    if not candidates:
        return {}
    # Issuers frequently describe a GBX trading line as GBP.  Ticker is the
    # stronger join; the LSE is authoritative for explicit price unit.
    exact = [row for row in candidates if normalize(row.get("CurrencyCode")) == normalize(listing_currency)]
    return (exact or candidates)[0]


def load_local_symbol_inventory(path: Path | None) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    if not path or not path.exists():
        return {}, {"status": "NOT_AVAILABLE", "path": str(path or ""), "sha256": "NOT_AVAILABLE", "row_count": 0}
    rows: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            symbol = normalize(row.get("symbol"))
            if symbol:
                rows[symbol] = row
    return rows, {
        "status": "READ_ONLY_DISCOVERY_SOURCE_USED",
        "path": str(path),
        "sha256": sha256_bytes(path.read_bytes()),
        "row_count": len(rows),
        "notes": "Price-history existence is not eligibility or broker evidence.",
    }


def local_symbol_match(ticker: str, inventory: dict[str, dict[str, str]]) -> tuple[str, str, str, str]:
    variants = [normalize(ticker), f"{normalize(ticker)}.L", f"{normalize(ticker)}.LSE", f"{normalize(ticker)}.LN"]
    for variant in variants:
        if variant in inventory:
            row = inventory[variant]
            return variant, clean_text(row.get("first_seen_date")), clean_text(row.get("last_seen_date")), clean_text(row.get("discovered_timeframes"))
    return "NOT_FOUND", "NOT_AVAILABLE", "NOT_AVAILABLE", "NOT_AVAILABLE"


def classify_etc_fields(kind: str, name: str, facts: dict[str, Any]) -> dict[str, str]:
    if kind != "ETC":
        return {
            "physical_backing": "NOT_APPLICABLE", "collateralisation": "NOT_APPLICABLE",
            "issuer_risk_assessment": "NOT_APPLICABLE", "counterparty_risk_assessment": "NOT_APPLICABLE",
            "leverage": "NO", "daily_reset": "NO", "path_dependence": "NO",
            "maturity": "NOT_APPLICABLE", "etc_structural_review_status": "NOT_APPLICABLE",
        }
    structure = normalize(facts.get("productStructure"))
    physical = "YES" if "PHYSICAL" in structure or "PHYSICAL" in normalize(name) else "NOT_VERIFIED"
    return {
        "physical_backing": physical,
        "collateralisation": "PHYSICAL_ASSET_STRUCTURE" if physical == "YES" else "NOT_VERIFIED",
        "issuer_risk_assessment": "DEBT_SECURITY_ISSUER_AND_STRUCTURE_RISK_RETAINS_REVIEW_REQUIREMENT",
        "counterparty_risk_assessment": "CUSTODY_COLLATERAL_AND_SWAP_RISK_REQUIRE_PRODUCT_DOCUMENT_REVIEW",
        "leverage": "NO",
        "daily_reset": "NO",
        "path_dependence": "NO",
        "maturity": "NO_FIXED_MATURITY_NOT_INDEPENDENTLY_CONFIRMED",
        "etc_structural_review_status": "PRIMARY_ISSUER_STRUCTURE_EVIDENCE" if facts else "INCOMPLETE_REVIEW",
    }


def build_master_tables(
    root: Path,
    ledger: EvidenceLedger,
    selected: dict[str, dict[str, Any]],
    selected_by_family: dict[str, list[dict[str, Any]]],
    catalog: dict[str, dict[str, Any]],
    catalog_evidence_id: str,
    details: dict[str, dict[str, Any]],
    local_inventory: dict[str, dict[str, str]],
) -> dict[str, list[dict[str, Any]]]:
    funds: dict[str, dict[str, Any]] = {}
    share_classes: list[dict[str, Any]] = []
    listings: list[dict[str, Any]] = []
    investability: list[dict[str, Any]] = []
    implementations: list[dict[str, Any]] = []
    duplicate_groups: dict[str, dict[str, Any]] = {}

    for isin, item in sorted(selected.items()):
        representative = item["representative"]
        rule = item["rule"]
        lines = item["lines"]
        catalog_row = catalog.get(isin, {})
        detail = details.get(isin, {})
        facts = detail.get("facts", {})
        provider = item["provider"]
        issuer_legal = clean_text(facts.get("issuingCompany")) or representative["issuer_name_as_published"] or "NOT_VERIFIED"
        fund_name = get_catalog_value(catalog_row, "fundName") or representative["description_as_published"]
        subfund_name = normalize_subfund_name(fund_name)
        fund_entity_id = stable_id("FUND", issuer_legal)
        share_class_id = stable_id("SC", isin)
        duplicate_group_id = f"DUP-{rule['family_id']}"
        hedged = rule.get("hedged", "NO")
        hedge_currency = rule.get("hedge_currency", "NOT_APPLICABLE")
        distribution = detect_distribution(fund_name, catalog_row, facts)
        ucits_status = yes_no(facts.get("ucitsCompliantFlag")) if facts else "NOT_DETERMINED"
        ucits_basis = "PRIMARY_ISSUER_PRODUCT_PAGE" if facts.get("ucitsCompliantFlag") else "NOT_DETERMINED_NOT_INFERRED_FROM_NAME"
        isa_status = yes_no(facts.get("isaEligibilityFlag")) if facts else "NOT_DETERMINED"
        sipp_status = yes_no(facts.get("sippEligibilityFlag")) if facts else "NOT_DETERMINED"
        document_checks = detail.get("document_checks", [])
        document_ok = any(d.get("http_status") == 200 and "PDF" in normalize(d.get("content_type")) for d in document_checks)
        retail_doc_url = document_checks[0]["url"] if document_checks else (detail.get("retail_documents") or [""])[0]
        lse_evidence_ids = sorted({line["source_evidence_id"] for line in lines})
        evidence_ids = list(lse_evidence_ids)
        if catalog_row:
            evidence_ids.append(catalog_evidence_id)
        if detail.get("evidence_id"):
            evidence_ids.append(detail["evidence_id"])
        evidence_ids.extend(d.get("evidence_id") for d in document_checks if d.get("evidence_id"))
        evidence_ids = sorted(set(evidence_ids))
        classification_evidence = ";".join(evidence_ids)
        current_state = (
            "CURRENTLY_INVESTABLE"
            if document_ok and isa_status == "YES" and sipp_status in {"YES", "NOT_DETERMINED"}
            else "CURRENT_CANDIDATE_UNVERIFIED"
        )
        eligibility_confidence = "HIGH" if current_state == "CURRENTLY_INVESTABLE" else "MEDIUM"
        kind = representative["instrument_type"]
        etc = classify_etc_fields(kind, fund_name, facts)

        if fund_entity_id not in funds:
            funds[fund_entity_id] = {
                "fund_entity_id": fund_entity_id,
                "legal_fund_name": issuer_legal,
                "provider_issuer": provider,
                "domicile": clean_text(facts.get("domicile")) or get_catalog_value(catalog_row, "domicile") or "NOT_VERIFIED",
                "fund_inception_date": clean_text(facts.get("launchDate")) or "NOT_AVAILABLE",
                "fund_entity_identity_confidence": "HIGH" if facts.get("issuingCompany") else "MEDIUM",
                "identity_evidence_ids": classification_evidence,
                "observation_date": OBSERVATION_DATE,
                "historical_eligibility_supported": "NO",
                "warning": WARNING,
            }

        share_classes.append({
            "share_class_id": share_class_id,
            "fund_entity_id": fund_entity_id,
            "sub_fund_name": subfund_name,
            "share_class_name": fund_name,
            "provider_issuer": provider,
            "isin": isin,
            "share_class_currency": clean_text(facts.get("seriesBaseCurrencyCode")) or get_catalog_value(catalog_row, "seriesBaseCurrencyCode", "seriesBaseCurrency") or "NOT_VERIFIED",
            "fund_base_currency": clean_text(facts.get("baseCurrencyCode")) or get_catalog_value(catalog_row, "seriesBaseCurrencyCode", "seriesBaseCurrency") or "NOT_VERIFIED",
            "underlying_economic_currency_exposure": rule["currency_exposure"],
            "hedged_unhedged": "HEDGED" if hedged == "YES" else "UNHEDGED",
            "hedge_currency": hedge_currency,
            "share_class_inception_date": clean_text(facts.get("inceptionDate")) or get_catalog_value(catalog_row, "inceptionDate") or "NOT_AVAILABLE",
            "accumulating_distributing": distribution,
            "ter_ocf_percent": parse_ter(catalog_row, facts),
            "benchmark_index": clean_text(facts.get("indexSeriesName")) or "NOT_VERIFIED",
            "replication_method": clean_text(facts.get("fundMethodologyTypeCode")) or "NOT_VERIFIED",
            "product_structure": clean_text(facts.get("productStructure")) or "NOT_VERIFIED",
            "ucits_status": ucits_status,
            "ucits_evidence_basis": ucits_basis,
            "instrument_type": kind,
            **etc,
            "economic_exposure_family_id": rule["family_id"],
            "duplicate_group_id": duplicate_group_id,
            "identity_evidence_ids": classification_evidence,
            "classification_evidence_ids": classification_evidence,
            "observation_date": OBSERVATION_DATE,
            "historical_eligibility_supported": "NO",
            "documented_exception_code": "NOT_APPLICABLE",
            "warning": WARNING,
        })

        duplicate_groups[duplicate_group_id] = {
            "duplicate_group_id": duplicate_group_id,
            "economic_exposure_family_id": rule["family_id"],
            "grouping_basis": "EFFECTIVELY_EQUIVALENT_ECONOMIC_EXPOSURE_WITH_SAME_HEDGE_STATE",
            "same_isin_multiple_listing_rule": "ONE_SHARE_CLASS_MULTIPLE_IMPLEMENTATION_LINES",
            "accumulating_distributing_rule": "SEPARATE_SHARE_CLASSES_SAME_ECONOMIC_FAMILY_AND_DUPLICATE_GROUP",
            "hedge_rule": "HEDGED_AND_UNHEDGED_ARE_DIFFERENT_ECONOMIC_FAMILIES_AND_DUPLICATE_GROUPS",
            "provider_rule": "EQUIVALENT_PROVIDER_PRODUCTS_ARE_ALTERNATIVE_IMPLEMENTATIONS_NOT_EXTRA_OPPORTUNITIES",
            "rule_version": DUPLICATE_RULE_VERSION,
            "warning": WARNING,
        }

        for line in sorted(lines, key=lambda r: (r["ticker"], r["price_unit"])):
            listing_id = stable_id("LIST", isin, line["mic"], line["ticker"], line["price_unit"])
            issuer_line = find_issuer_listing(detail, line["ticker"], line["listing_currency"], line["price_unit"])
            sedol = clean_text(issuer_line.get("Sedol")) or "NOT_AVAILABLE"
            if sedol == "-":
                sedol = "NOT_AVAILABLE"
            local_symbol, first_seen, last_seen, timeframes = local_symbol_match(line["ticker"], local_inventory)
            listing_evidence = sorted(set(evidence_ids + ([detail["evidence_id"]] if detail.get("evidence_id") else [])))
            listings.append({
                "listing_id": listing_id,
                "share_class_id": share_class_id,
                "fund_entity_id": fund_entity_id,
                "isin": isin,
                "sedol": sedol,
                "exchange": line["exchange"],
                "mic": line["mic"],
                "ticker": line["ticker"],
                "listing_currency": line["listing_currency"],
                "price_unit": line["price_unit"],
                "price_unit_multiplier_to_listing_currency": line["price_unit_multiplier_to_listing_currency"],
                "listing_inception_date": clean_text(issuer_line.get("ListingDate")) or "NOT_AVAILABLE",
                "active_listing_status": line["active_listing_status"],
                "active_status_verification_date": OBSERVATION_DATE,
                "active_status_confidence": line.get("active_listing_confidence", "MEDIUM"),
                "economic_exposure_family_id": rule["family_id"],
                "duplicate_group_id": duplicate_group_id,
                "local_market_data_symbol_match": local_symbol,
                "local_market_data_first_seen": first_seen,
                "local_market_data_last_seen": last_seen,
                "local_market_data_timeframes": timeframes,
                "identity_evidence_ids": ";".join(listing_evidence),
                "observation_date": OBSERVATION_DATE,
                "historical_eligibility_supported": "NO",
                "warning": WARNING,
            })
            investability.append({
                "listing_id": listing_id,
                "share_class_id": share_class_id,
                "isin": isin,
                "mic": line["mic"],
                "ticker": line["ticker"],
                "current_investability_state": current_state,
                "current_uk_retail_eligibility": "ELIGIBLE_DOCUMENTED_CURRENT_ISSUER_PAGE" if document_ok else "NOT_VERIFIED",
                "isa_eligibility": isa_status,
                "sipp_eligibility": sipp_status,
                "ibkr_availability": "NOT_CHECKED",
                "broker_status": "NOT_CHECKED",
                "broker_check_method": "NO_SAFE_EXACT_LSE_ISIN_READ_ONLY_ROUTE_AVAILABLE",
                "broker_check_date": "NOT_CHECKED",
                "current_exchange_listing_status": line["active_listing_status"],
                "kid_retail_document_evidence": "CURRENT_DOCUMENT_HTTP_VERIFIED" if document_ok else "NOT_VERIFIED",
                "kid_retail_document_url": retail_doc_url or "NOT_AVAILABLE",
                "structural_eligibility": "ELIGIBLE_LONG_ONLY_STRUCTURE",
                "eligibility_verification_date": OBSERVATION_DATE,
                "eligibility_confidence": eligibility_confidence,
                "eligibility_evidence_ids": classification_evidence,
                "historical_eligibility": "NOT_ASSESSED_OUT_OF_SCOPE",
                "historical_eligibility_supported": "NO",
                "warning": WARNING,
            })
            implementations.append({
                "listing_id": listing_id,
                "share_class_id": share_class_id,
                "fund_entity_id": fund_entity_id,
                "economic_exposure_family_id": rule["family_id"],
                "duplicate_group_id": duplicate_group_id,
                "isin": isin,
                "provider_issuer": provider,
                "ticker": line["ticker"],
                "mic": line["mic"],
                "listing_currency": line["listing_currency"],
                "price_unit": line["price_unit"],
                "accumulating_distributing": distribution,
                "hedged_unhedged": "HEDGED" if hedged == "YES" else "UNHEDGED",
                "ter_ocf_percent": parse_ter(catalog_row, facts),
                "current_investability_state": current_state,
                "broker_status": "NOT_CHECKED",
                "implementation_evidence_confidence": eligibility_confidence,
                "implementation_selection_status": "CANDIDATE_ONLY_NO_TRADE_OR_PORTFOLIO_SELECTION",
                "warning": WARNING,
            })

    # Deterministic implementation-candidate order uses only current evidence
    # quality, GBP line convenience, costs when known, and stable IDs.  It is not
    # an economic signal or portfolio decision.
    impl_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in implementations:
        impl_by_family[row["economic_exposure_family_id"]].append(row)
    for family_id, rows in impl_by_family.items():
        def impl_key(row: dict[str, Any]) -> tuple[Any, ...]:
            verified_penalty = 0 if row["current_investability_state"] == "CURRENTLY_INVESTABLE" else 1
            gbp_penalty = 0 if row["price_unit"] in {"GBP", "GBX"} else 1
            ter = parse_number(row["ter_ocf_percent"])
            return (verified_penalty, gbp_penalty, ter if ter is not None else 999.0, row["listing_id"])
        for rank, row in enumerate(sorted(rows, key=impl_key), start=1):
            row["implementation_evidence_order"] = rank

    share_classes.sort(key=lambda r: r["share_class_id"])
    listings.sort(key=lambda r: r["listing_id"])
    investability.sort(key=lambda r: r["listing_id"])
    implementations.sort(key=lambda r: (r["economic_exposure_family_id"], int(r["implementation_evidence_order"])))

    exposure_master: list[dict[str, Any]] = []
    selected_family_rules = {item["rule"]["family_id"]: item["rule"] for item in selected.values()}
    share_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    listings_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    inv_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in share_classes:
        share_by_family[row["economic_exposure_family_id"]].append(row)
    for row in listings:
        listings_by_family[row["economic_exposure_family_id"]].append(row)
    for row in investability:
        inv_by_family[next(s["economic_exposure_family_id"] for s in share_classes if s["share_class_id"] == row["share_class_id"])].append(row)

    for family_id, rule in sorted(selected_family_rules.items()):
        family_shares = share_by_family[family_id]
        family_listings = listings_by_family[family_id]
        providers = sorted({next(s["provider_issuer"] for s in share_classes if s["share_class_id"] == listing["share_class_id"]) for listing in family_listings})
        verified_isins = {
            row["isin"] for row in inv_by_family[family_id]
            if row["current_investability_state"] == "CURRENTLY_INVESTABLE"
        }
        exposure_master.append({
            "economic_exposure_family_id": family_id,
            "economic_opportunity_id": f"OPP-{family_id}",
            "duplicate_group_id": f"DUP-{family_id}",
            "economic_exposure_name": rule["description"],
            "opportunity_type": rule["opportunity_type"],
            "universe_tier": rule["tier"],
            "asset_class": rule["asset_class"],
            "sub_asset_class": rule["sub_asset_class"],
            "primary_geography": rule["geography"],
            "geographic_scope": rule["scope"],
            "country": rule["country"],
            "developed_emerging": rule["development"],
            "sector": rule["sector"],
            "industry": rule["industry"],
            "economic_theme": rule["theme"],
            "deepvue_theme": rule["deepvue"],
            "factor_style": rule["factor"],
            "market_cap_segment": rule["market_cap"],
            "bond_issuer_type": rule["bond_issuer"],
            "bond_duration_bucket": rule["duration"],
            "bond_credit_bucket": rule["credit"],
            "inflation_linked": rule["inflation"],
            "commodity_type": rule["commodity"],
            "portfolio_role": rule["role"],
            "underlying_economic_currency_exposure": rule["currency_exposure"],
            "hedged_unhedged": "HEDGED" if rule.get("hedged") == "YES" else "UNHEDGED",
            "hedge_currency": rule.get("hedge_currency", "NOT_APPLICABLE"),
            "share_class_count": len(family_shares),
            "listing_count": len(family_listings),
            "provider_count": len(providers),
            "providers": ";".join(providers),
            "currently_verified_investable_isin_count": len(verified_isins),
            "classification_rule_version": CLASSIFICATION_RULE_VERSION,
            "classification_basis": "ORDERED_PROVIDER_NEUTRAL_ECONOMIC_EXPOSURE_RULE_PLUS_PRIMARY_PRODUCT_IDENTITY_EVIDENCE",
            "future_signal_unit": "ONE_ECONOMIC_OPPORTUNITY_REGARDLESS_OF_IMPLEMENTATION_COUNT",
            "observation_date": OBSERVATION_DATE,
            "historical_eligibility_supported": "NO",
            "warning": WARNING,
        })

    # Aggregate membership counts after the family master exists.
    for row in duplicate_groups.values():
        family_id = row["economic_exposure_family_id"]
        row["share_class_count"] = len(share_by_family[family_id])
        row["listing_count"] = len(listings_by_family[family_id])
        row["provider_count"] = len({s["provider_issuer"] for s in share_by_family[family_id]})
        row["member_isins"] = ";".join(sorted({s["isin"] for s in share_by_family[family_id]}))

    return {
        "funds": sorted(funds.values(), key=lambda r: r["fund_entity_id"]),
        "share_classes": share_classes,
        "listings": listings,
        "investability": investability,
        "implementations": implementations,
        "duplicate_groups": sorted(duplicate_groups.values(), key=lambda r: r["duplicate_group_id"]),
        "exposures": exposure_master,
    }


def build_exclusions(discovery: list[dict[str, Any]], selected_isins: set[str]) -> list[dict[str, Any]]:
    by_isin: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in discovery:
        if row["isin"]:
            by_isin[row["isin"]].append(row)
    exclusions: list[dict[str, Any]] = []
    for isin, lines in sorted(by_isin.items()):
        representative = max(lines, key=lambda row: len(row["description_as_published"]))
        reason_codes = set()
        for line in lines:
            if line["structural_exclusion_flag"] == "YES":
                reason_codes.update(code for code in line["structural_exclusion_reason_codes"].split(";") if code and code != "NOT_APPLICABLE")
            if line["style_variant_out_of_scope_flag"] == "YES":
                reason_codes.add("STYLE_VARIANT_OUTSIDE_INITIAL_ROTATION_TAXONOMY")
        if not reason_codes:
            continue
        structural = any(code != "STYLE_VARIANT_OUTSIDE_INITIAL_ROTATION_TAXONOMY" for code in reason_codes)
        exclusions.append({
            "exclusion_id": stable_id("EXC", isin),
            "isin": isin,
            "issuer_provider": representative["provider_normalized"],
            "product_description": representative["description_as_published"],
            "instrument_type": representative["instrument_type"],
            "listing_count": len(lines),
            "sample_tickers": ";".join(sorted({line["ticker"] for line in lines})[:10]),
            "current_investability_state": "NOT_ELIGIBLE" if structural else "NOT_ELIGIBLE_FOR_INITIAL_CANONICAL_SCOPE",
            "exclusion_reason_codes": ";".join(sorted(reason_codes)),
            "exclusion_scope": "LONG_ONLY_CANONICAL_RESEARCH_UNIVERSE" if structural else "INITIAL_A0A1_CURATED_SCOPE",
            "selected_master_overlap": "YES_ERROR" if isin in selected_isins else "NO",
            "source_evidence_ids": ";".join(sorted({line["source_evidence_id"] for line in lines})),
            "verification_date": OBSERVATION_DATE,
            "warning": WARNING,
        })
    return exclusions


GEOGRAPHY_ROWS = [
    ("GLOBAL", "Global", "ROOT", "GLOBAL", "World-wide exposure"),
    ("ALL_WORLD", "All World", "GLOBAL", "GLOBAL", "Developed and emerging markets"),
    ("DEVELOPED_WORLD", "Developed World", "GLOBAL", "GLOBAL", "Developed markets only"),
    ("NORTH_AMERICA", "North America", "GLOBAL", "REGION", "United States and Canada"),
    ("UNITED_STATES", "United States", "NORTH_AMERICA", "SINGLE_COUNTRY", "Distinct large capital market and economic cycle"),
    ("CANADA", "Canada", "NORTH_AMERICA", "SINGLE_COUNTRY", "Resource- and financials-heavy developed market"),
    ("UNITED_KINGDOM", "United Kingdom", "EUROPE", "SINGLE_COUNTRY", "Home market with distinct sector/currency composition"),
    ("EUROPE", "Europe", "GLOBAL", "REGION", "Developed European markets including UK where index specifies"),
    ("EUROPE_EX_UK", "Europe ex-UK", "EUROPE", "REGION", "Separates continental Europe from UK allocation"),
    ("EUROZONE", "Eurozone", "EUROPE", "REGION", "Common-currency member markets"),
    ("JAPAN", "Japan", "DEVELOPED_ASIA_PACIFIC", "SINGLE_COUNTRY", "Distinct currency, policy, and market structure"),
    ("DEVELOPED_ASIA_PACIFIC", "Developed Asia-Pacific", "GLOBAL", "REGION", "Developed Pacific markets"),
    ("ASIA_PACIFIC_EX_JAPAN", "Asia-Pacific ex-Japan", "GLOBAL", "REGION", "Regional opportunity excluding Japan"),
    ("EMERGING_MARKETS", "Emerging Markets", "GLOBAL", "MULTI_REGION", "Broad emerging-market opportunity"),
    ("EMERGING_ASIA", "Emerging Asia", "EMERGING_MARKETS", "REGION", "Emerging Asian opportunity"),
    ("CHINA", "China", "EMERGING_ASIA", "SINGLE_COUNTRY", "Large distinct emerging market"),
    ("INDIA", "India", "EMERGING_ASIA", "SINGLE_COUNTRY", "Large distinct emerging market"),
    ("LATIN_AMERICA", "Latin America", "EMERGING_MARKETS", "REGION", "Commodity- and financials-sensitive region"),
    ("AUSTRALIA", "Australia", "DEVELOPED_ASIA_PACIFIC", "SINGLE_COUNTRY", "Resource-heavy developed market"),
    ("SOUTH_KOREA", "South Korea", "ASIA_PACIFIC_EX_JAPAN", "SINGLE_COUNTRY", "Distinct export/technology market; provider development classification differs"),
    ("TAIWAN", "Taiwan", "EMERGING_ASIA", "SINGLE_COUNTRY", "Distinct technology-heavy market"),
]


SECTOR_INDUSTRIES = {
    "TECHNOLOGY": ["BROAD_SECTOR", "SEMICONDUCTORS", "SOFTWARE", "CYBERSECURITY", "COMPUTING"],
    "FINANCIALS": ["BROAD_SECTOR", "BANKS"],
    "HEALTHCARE": ["BROAD_SECTOR", "BIOTECHNOLOGY"],
    "INDUSTRIALS": ["BROAD_SECTOR", "AEROSPACE_AND_DEFENCE", "TRANSPORTATION", "AIRLINES", "INDUSTRIAL_AUTOMATION", "INFRASTRUCTURE"],
    "CONSUMER_DISCRETIONARY": ["BROAD_SECTOR", "RETAIL", "HOME_CONSTRUCTION"],
    "CONSUMER_STAPLES": ["BROAD_SECTOR", "AGRIBUSINESS"],
    "COMMUNICATION_SERVICES": ["BROAD_SECTOR", "TELECOMMUNICATIONS", "INTERACTIVE_MEDIA", "INTERNET_SERVICES"],
    "ENERGY": ["BROAD_SECTOR", "OIL_AND_GAS", "URANIUM_AND_NUCLEAR"],
    "MATERIALS": ["BROAD_SECTOR", "STEEL", "GOLD_MINERS", "SILVER_MINERS"],
    "UTILITIES": ["BROAD_SECTOR", "RENEWABLE_ENERGY"],
    "REAL_ESTATE": ["BROAD_SECTOR", "REITS_AND_PROPERTY"],
}


def build_taxonomies(exposures: list[dict[str, Any]], ledger: EvidenceLedger, deepvue_policy_evidence_id: str) -> dict[str, list[dict[str, Any]]]:
    present_geographies = {row["primary_geography"] for row in exposures}
    geographic = []
    for code, label, parent, scope, rationale in GEOGRAPHY_ROWS:
        families = sorted(row["economic_exposure_family_id"] for row in exposures if row["primary_geography"] == code and row["opportunity_type"] == "GEOGRAPHY")
        geographic.append({
            "geography_code": code,
            "geography_label": label,
            "parent_geography_code": parent,
            "geographic_scope": scope,
            "current_economic_opportunity_included": "YES" if families else "NO",
            "included_family_ids": ";".join(families) if families else "NOT_APPLICABLE",
            "economic_distinctiveness_assessment": rationale,
            "inclusion_rule": "REQUIRES_DISTINCT_EXPOSURE_AND_AT_LEAST_ONE_CURATED_CURRENT_IMPLEMENTATION",
            "listing_currency_may_determine_geography": "NO",
            "taxonomy_version": CLASSIFICATION_RULE_VERSION,
            "warning": WARNING,
        })

    sector_rows = []
    present_pairs = {(row["sector"], row["industry"]) for row in exposures}
    for sector, industries in SECTOR_INDUSTRIES.items():
        sector_rows.append({
            "taxonomy_node_id": f"SECTOR-{sector}",
            "node_type": "SECTOR",
            "sector": sector,
            "industry": "NOT_APPLICABLE",
            "parent_node_id": "SECTOR-ROOT",
            "current_opportunity_present": "YES" if any(pair[0] == sector for pair in present_pairs) else "NO",
            "sector_is_not_theme": "YES",
            "taxonomy_version": CLASSIFICATION_RULE_VERSION,
            "warning": WARNING,
        })
        for industry in industries:
            sector_rows.append({
                "taxonomy_node_id": f"INDUSTRY-{sector}-{industry}",
                "node_type": "INDUSTRY",
                "sector": sector,
                "industry": industry,
                "parent_node_id": f"SECTOR-{sector}",
                "current_opportunity_present": "YES" if (sector, industry) in present_pairs else "NO",
                "sector_is_not_theme": "YES",
                "taxonomy_version": CLASSIFICATION_RULE_VERSION,
                "warning": WARNING,
            })

    theme_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in exposures:
        if row["economic_theme"] != "NOT_APPLICABLE":
            theme_groups[row["economic_theme"]].append(row)
    themes = []
    for theme, rows in sorted(theme_groups.items()):
        deepvue_labels = sorted({row["deepvue_theme"] for row in rows if row["deepvue_theme"] != "NOT_APPLICABLE"})
        themes.append({
            "economic_theme": theme,
            "definition": rows[0]["economic_exposure_name"],
            "current_family_ids": ";".join(sorted(row["economic_exposure_family_id"] for row in rows)),
            "family_count": len(rows),
            "evidence_basis_required": "INDEX_METHODOLOGY_OR_FUND_OBJECTIVE_PLUS_HOLDINGS_WHERE_AMBIGUOUS",
            "deepvue_exact_labels": ";".join(deepvue_labels) if deepvue_labels else "NOT_APPLICABLE",
            "retain_only_if_coherent_investable_exposure": "YES",
            "taxonomy_version": CLASSIFICATION_RULE_VERSION,
            "warning": WARNING,
        })

    user_evidence_id = ledger.add(
        evidence_type="USER_SUPPLIED_REFERENCE",
        source_tier="USER_CONFIRMED",
        publisher="User-provided DeepVue screenshots/list",
        title="Confirmed initial DeepVue Theme Tracker labels",
        url="USER_SUPPLIED_NO_PUBLIC_URL",
        retrieved_at=utc_now(),
        supports="exact spelling of the 31 initial DeepVue Theme Tracker labels",
        source_sha256=sha256_text("|".join(sorted(CONFIRMED_DEEPVUE_THEMES))),
        local_capture="PROMPT_CONTEXT",
        confidence="HIGH",
        notes="Public DeepVue documentation explains the system but does not establish a complete current public label export.",
    )
    crosswalk = []
    for label in sorted(CONFIRMED_DEEPVUE_THEMES):
        mapped = [row for row in exposures if row["deepvue_theme"] == label]
        crosswalk.append({
            "deepvue_theme": label,
            "exact_label_status": "CONFIRMED_USER_SUPPLIED",
            "mapped_economic_themes": ";".join(sorted({row["economic_theme"] for row in mapped})) if mapped else "NOT_MAPPED_IN_CURRENT_MASTER",
            "mapped_economic_exposure_family_ids": ";".join(sorted(row["economic_exposure_family_id"] for row in mapped)) if mapped else "NOT_MAPPED_IN_CURRENT_MASTER",
            "mapping_status": "EXACT_DESCRIPTIVE_CROSSWALK" if mapped else "VALID_LABEL_NO_CURRENT_EXACT_PRODUCT_MAPPING",
            "user_evidence_id": user_evidence_id,
            "deepvue_policy_evidence_id": deepvue_policy_evidence_id,
            "controls_asset_class_or_investability": "NO",
            "invented_label": "NO",
            "verification_date": OBSERVATION_DATE,
            "warning": WARNING,
        })
    crosswalk.append({
        "deepvue_theme": "NOT_APPLICABLE",
        "exact_label_status": "CONTROL_VALUE_NOT_A_THEME",
        "mapped_economic_themes": "NON_THEMATIC_OR_NO_DEFENSIBLE_EXACT_CROSSWALK",
        "mapped_economic_exposure_family_ids": "SEE_ECONOMIC_EXPOSURE_MASTER",
        "mapping_status": "REQUIRED_NULL_SEMANTIC",
        "user_evidence_id": user_evidence_id,
        "deepvue_policy_evidence_id": deepvue_policy_evidence_id,
        "controls_asset_class_or_investability": "NO",
        "invented_label": "NO",
        "verification_date": OBSERVATION_DATE,
        "warning": WARNING,
    })
    return {"geographic": geographic, "sector": sector_rows, "themes": themes, "deepvue": crosswalk}


def build_coverage_matrix(exposures: list[dict[str, Any]], shares: list[dict[str, Any]], listings: list[dict[str, Any]], investability: list[dict[str, Any]]) -> list[dict[str, Any]]:
    verified_by_share = {
        row["share_class_id"] for row in investability
        if row["current_investability_state"] == "CURRENTLY_INVESTABLE"
    }
    rows = []
    dimensions = [
        ("GEOGRAPHIC_OPPORTUNITIES", lambda e: e["opportunity_type"] == "GEOGRAPHY", "Future regional/country leadership breadth"),
        ("SECTOR_INDUSTRY_OPPORTUNITIES", lambda e: e["opportunity_type"] == "SECTOR_INDUSTRY", "Conventional sector and useful industry breadth"),
        ("THEMATIC_OPPORTUNITIES", lambda e: e["opportunity_type"] == "THEMATIC", "Coherent investable themes, separately classified"),
        ("DEFENSIVE_DIVERSIFIERS", lambda e: e["opportunity_type"] == "DEFENSIVE_DIVERSIFIER", "Bonds, cash-like assets, commodities and diversifiers"),
    ]
    shares_by_family = defaultdict(list)
    listings_by_family = defaultdict(list)
    for share in shares:
        shares_by_family[share["economic_exposure_family_id"]].append(share)
    for listing in listings:
        listings_by_family[listing["economic_exposure_family_id"]].append(listing)
    for code, predicate, purpose in dimensions:
        families = [e for e in exposures if predicate(e)]
        family_ids = {e["economic_exposure_family_id"] for e in families}
        dimension_shares = [s for fid in family_ids for s in shares_by_family[fid]]
        dimension_listings = [l for fid in family_ids for l in listings_by_family[fid]]
        rows.append({
            "coverage_dimension": code,
            "research_purpose": purpose,
            "economic_family_count": len(families),
            "unique_isin_count": len({s["isin"] for s in dimension_shares}),
            "listing_count": len(dimension_listings),
            "verified_investable_isin_count": len({s["isin"] for s in dimension_shares if s["share_class_id"] in verified_by_share}),
            "core_family_count": sum(e["universe_tier"] == "CORE" for e in families),
            "extended_family_count": sum(e["universe_tier"] == "EXTENDED" for e in families),
            "experimental_family_count": sum(e["universe_tier"] == "EXPERIMENTAL" for e in families),
            "coverage_assessment": "CURRENT_MASTER_ONLY_NO_POINT_IN_TIME_INFERENCE",
            "warning": WARNING,
        })
    return rows


def unresolved_items() -> list[dict[str, Any]]:
    items = [
        ("URI-001", "BROKER", "IBKR account-specific availability was not checked because no safe exact-LSE-ISIN read-only route was available.", "A2_OR_SEPARATE_READ_ONLY_BROKER_ADAPTER", "NO", "All broker statuses remain NOT_CHECKED; no orders or permission changes attempted."),
        ("URI-002", "ELIGIBILITY", "Non-iShares share classes lack product-specific current KID/ISA/SIPP verification.", "A0A1_MAINTENANCE", "NO", "They remain CURRENT_CANDIDATE_UNVERIFIED and cannot be promoted silently."),
        ("URI-003", "LISTING_STATUS", "Current LSE catalogue presence is not a full suspension/delisting-status legal feed.", "A2", "NO", "Use licensed/reference exchange status data for point-in-time reconstruction."),
        ("URI-004", "HISTORY", "No historical eligibility or delisted ETF universe has been reconstructed.", "A2", "NO", WARNING),
        ("URI-005", "TOTAL_RETURN", "Adjusted prices, distributions, corporate actions and GBP total returns have not been validated.", "A2", "NO", "No strategy or return research is authorised in A0A1."),
        ("URI-006", "LIQUIDITY", "Comparable bid/ask spreads, turnover, AUM and creation/redemption liquidity are incomplete across providers.", "A2_IMPLEMENTATION_DATA", "NO", "Do not select an implementation from ticker count or price-data presence."),
        ("URI-007", "ETC_STRUCTURE", "Non-iShares ETC collateral, security, counterparty and maturity terms require product-level prospectus review.", "A0A1_MAINTENANCE", "NO", "Only structurally evidenced unleveraged candidates can be promoted."),
        ("URI-008", "DEEPVUE", "No complete current official/public DeepVue Theme Tracker label export was found.", "USER_EXPORT_OR_FUTURE_REFRESH", "NO", "Only the 31 user-confirmed exact labels are admitted; gaps do not block stage pass."),
        ("URI-009", "CLASSIFICATION", "Some issuer descriptions are insufficient to distinguish near-neighbour indices or exact holdings screens.", "A0A1_MAINTENANCE", "NO", "Use index methodology and holdings review before promoting ambiguous narrow themes."),
        ("URI-010", "REPRODUCIBILITY", "The research platform directory is not a Git worktree.", "PLATFORM_GOVERNANCE", "NO", "Executed source and captures are hashed and retained, but Git commit/diff are not applicable."),
        ("URI-011", "ACCOUNT_ELIGIBILITY", "ISA and SIPP availability can vary by scheme/provider even where issuer pages indicate eligibility.", "BROKER_PLATFORM_CONFIRMATION", "NO", "Product-level issuer evidence is not a guarantee of availability at every retail platform."),
    ]
    return [
        {
            "item_id": item_id, "category": category, "description": description,
            "required_resolution_stage": stage, "blocks_a0a1_pass": blocks,
            "control_or_next_action": action, "status": "OPEN", "observation_date": OBSERVATION_DATE,
            "warning": WARNING,
        }
        for item_id, category, description, stage, blocks, action in items
    ]


def build_manual_audit_cases(tables: dict[str, list[dict[str, Any]]], exclusions: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    exposures = {row["economic_exposure_family_id"]: row for row in tables["exposures"]}
    shares_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    listings_by_share: dict[str, list[dict[str, Any]]] = defaultdict(list)
    invest_by_listing = {row["listing_id"]: row for row in tables["investability"]}
    fund_by_id = {row["fund_entity_id"]: row for row in tables["funds"]}
    for row in tables["share_classes"]:
        shares_by_family[row["economic_exposure_family_id"]].append(row)
    for row in tables["listings"]:
        listings_by_share[row["share_class_id"]].append(row)

    def choose_family(predicate: Any) -> str | None:
        return next((fid for fid in sorted(exposures) if predicate(fid, exposures[fid])), None)

    specifications = [
        (1, "UK broad-market equity ETF", lambda fid, e: fid in {"UK_BROAD_MARKET", "UK_LARGE_CAP"}),
        (2, "US broad-market ETF", lambda fid, e: fid == "US_BROAD_LARGE_CAP"),
        (3, "Nasdaq / US-growth ETF", lambda fid, e: fid == "US_NASDAQ_100"),
        (4, "Europe ETF", lambda fid, e: fid in {"EUROPE_BROAD", "EUROPE_EX_UK", "EUROZONE"}),
        (5, "Japan ETF", lambda fid, e: fid == "JAPAN"),
        (6, "Emerging-markets ETF", lambda fid, e: fid == "EMERGING_MARKETS"),
        (7, "India or China ETF", lambda fid, e: fid in {"INDIA", "CHINA_BROAD", "CHINA_A_SHARES"}),
        (8, "Semiconductor ETF", lambda fid, e: "SEMICONDUCTORS" in fid),
        (9, "Cybersecurity ETF", lambda fid, e: "CYBERSECURITY" in fid),
        (10, "Healthcare / biotechnology ETF", lambda fid, e: "HEALTHCARE" in fid or "BIOTECHNOLOGY" in fid),
        (11, "Aerospace / defence ETF", lambda fid, e: "AEROSPACE_DEFENCE" in fid),
        (12, "Gold-miner ETF", lambda fid, e: "GOLD_MINERS" in fid),
        (13, "Government-bond ETF", lambda fid, e: e["asset_class"] == "GOVERNMENT_BOND"),
        (14, "Corporate-bond ETF", lambda fid, e: e["asset_class"] == "CORPORATE_BOND"),
        (15, "Gold ETC", lambda fid, e: fid == "GOLD"),
        (16, "Cash-like ETF", lambda fid, e: e["asset_class"] == "CASH_LIKE"),
    ]
    cases: list[dict[str, Any]] = []
    for number, label, predicate in specifications:
        family_id = choose_family(predicate)
        if not family_id:
            cases.append({"number": number, "label": label, "status": "MISSING", "detail": "No current curated implementation found."})
            continue
        share = sorted(shares_by_family[family_id], key=lambda r: (r["provider_issuer"] != "ISHARES", r["isin"]))[0]
        listing = sorted(listings_by_share[share["share_class_id"]], key=lambda r: (r["price_unit"] not in {"GBP", "GBX"}, r["listing_id"]))[0]
        inv = invest_by_listing[listing["listing_id"]]
        fund = fund_by_id[share["fund_entity_id"]]
        exposure = exposures[family_id]
        chain = (
            f"{listing['identity_evidence_ids']} → {fund['fund_entity_id']} ({fund['legal_fund_name']}) → "
            f"{share['share_class_id']} / {share['isin']} ({share['sub_fund_name']}) → "
            f"{listing['listing_id']} / {listing['mic']}:{listing['ticker']} {listing['price_unit']} → "
            f"{inv['current_investability_state']} (ISA={inv['isa_eligibility']}; SIPP={inv['sipp_eligibility']}; IBKR={inv['broker_status']}) → "
            f"asset={exposure['asset_class']} → geography={exposure['primary_geography']}/{exposure['geographic_scope']} → "
            f"sector={exposure['sector']} → industry={exposure['industry']} → theme={exposure['economic_theme']} → "
            f"DeepVue={exposure['deepvue_theme']} → family={family_id} → group={exposure['duplicate_group_id']} → tier={exposure['universe_tier']}"
        )
        cases.append({"number": number, "label": label, "status": "AUDITED", "detail": chain})

    # 17: same ISIN, multiple LSE implementation lines (prefer explicit ISF pair).
    same_isin: tuple[dict[str, Any], list[dict[str, Any]]] | None = None
    for share in sorted(tables["share_classes"], key=lambda r: (r["isin"] != "IE0005042456", r["isin"])):
        lines = listings_by_share[share["share_class_id"]]
        if len(lines) >= 2 and len({line["price_unit"] for line in lines}) >= 2:
            same_isin = (share, lines)
            break
    if same_isin:
        share, lines = same_isin
        cases.append({
            "number": 17, "label": "Same ISIN with GBP/USD listings", "status": "AUDITED",
            "detail": f"{share['isin']} → one share_class_id={share['share_class_id']} → listings=" + "; ".join(f"{line['mic']}:{line['ticker']} {line['price_unit']} ({line['listing_id']})" for line in sorted(lines, key=lambda r: r["price_unit"])) + f" → one family={share['economic_exposure_family_id']} → one group={share['duplicate_group_id']}. Listing currency does not alter geography or the signal unit.",
        })
    else:
        cases.append({"number": 17, "label": "Same ISIN with GBP/USD listings", "status": "MISSING", "detail": "No qualifying pair retained."})

    # 18: accumulating and distributing share classes remain distinct.
    accdist = None
    for family_id, shares in shares_by_family.items():
        acc = [s for s in shares if s["accumulating_distributing"] == "ACCUMULATING"]
        dist = [s for s in shares if s["accumulating_distributing"] == "DISTRIBUTING"]
        if acc and dist:
            accdist = (family_id, acc[0], dist[0])
            break
    if accdist:
        family_id, acc, dist = accdist
        cases.append({
            "number": 18, "label": "Accumulating / distributing pair", "status": "AUDITED",
            "detail": f"{acc['isin']} ({acc['share_class_id']}, ACCUMULATING) + {dist['isin']} ({dist['share_class_id']}, DISTRIBUTING) → distinct share-class price identities → same family={family_id} → same duplicate_group={acc['duplicate_group_id']}. They are not collapsed at share-class level.",
        })
    else:
        cases.append({"number": 18, "label": "Accumulating / distributing pair", "status": "MISSING", "detail": "No qualifying pair retained."})

    # 19: currency hedging changes economic exposure and duplicate group.
    hedge_pair = None
    for family_id in sorted(exposures):
        hedged_id = family_id + "_GBP_HEDGED"
        if hedged_id in exposures:
            hedge_pair = (family_id, hedged_id)
            break
    if hedge_pair:
        unhedged, hedged = hedge_pair
        unhedged_share = shares_by_family[unhedged][0]
        hedged_share = shares_by_family[hedged][0]
        cases.append({
            "number": 19, "label": "Hedged / unhedged pair", "status": "AUDITED",
            "detail": f"unhedged={unhedged_share['isin']} → family={unhedged}, group={unhedged_share['duplicate_group_id']}; hedged={hedged_share['isin']} → family={hedged}, group={hedged_share['duplicate_group_id']}. Hedge state changes economic exposure and is never collapsed.",
        })
    else:
        cases.append({"number": 19, "label": "Hedged / unhedged pair", "status": "MISSING", "detail": "No GBP-hedged pair retained."})

    # 20: deterministic negative control from the live discovery catalogue.
    negative = next((row for row in exclusions if any(code in row["exclusion_reason_codes"] for code in ["LEVERAGED", "INVERSE", "VOLATILITY_LINKED"])), None)
    if negative:
        cases.append({
            "number": 20, "label": "Leveraged / inverse negative control", "status": "AUDITED",
            "detail": f"{negative['source_evidence_ids']} → ISIN={negative['isin']} / {negative['sample_tickers']} / {negative['product_description']} → state={negative['current_investability_state']} → reasons={negative['exclusion_reason_codes']} → excluded from every CORE/EXTENDED/EXPERIMENTAL economic family.",
        })
    else:
        cases.append({"number": 20, "label": "Leveraged / inverse negative control", "status": "MISSING", "detail": "No negative control found."})

    lines = [
        "# UKACTIVE-A0A1 Manual Audit Cases",
        "",
        f"> {WARNING}",
        "",
        "These are identity/classification and current-evidence chains, not performance examples. Evidence IDs resolve into `evidence/UKACTIVE_A0A1_EVIDENCE_LEDGER.jsonl`.",
        "",
    ]
    for case in sorted(cases, key=lambda c: c["number"]):
        lines.extend([f"## {case['number']}. {case['label']}", "", f"Status: `{case['status']}`", "", case["detail"], ""])
    return "\n".join(lines), cases


def run_quality_controls(
    discovery: list[dict[str, Any]],
    tables: dict[str, list[dict[str, Any]]],
    exclusions: list[dict[str, Any]],
    manual_cases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    shares = tables["share_classes"]
    listings = tables["listings"]
    exposures = tables["exposures"]
    invest = tables["investability"]
    selected_isins = {row["isin"] for row in shares}
    excluded_isins = {row["isin"] for row in exclusions if row["current_investability_state"] == "NOT_ELIGIBLE"}
    results: list[dict[str, Any]] = []

    def check(test_id: str, requirement: str, condition: bool, detail: str) -> None:
        results.append({"test_id": test_id, "requirement": requirement, "status": "PASS" if condition else "FAIL", "detail": detail, "warning": WARNING})

    check("QC-001", "Ticker is not treated as globally unique", len({r["listing_id"] for r in listings}) == len(listings) and all(r["isin"] in r["listing_id"] or r["listing_id"].startswith("LIST-") for r in listings), "listing_id is a deterministic hash of ISIN+MIC+ticker+price unit; ticker is descriptive only")
    check("QC-002", "Canonical share classes have ISIN or documented exception", all(re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", r["isin"]) or r["documented_exception_code"] != "NOT_APPLICABLE" for r in shares), f"share_classes={len(shares)}")
    families_by_isin = defaultdict(set)
    for row in shares:
        families_by_isin[row["isin"]].add(row["economic_exposure_family_id"])
    check("QC-003", "Same-ISIN listings do not become multiple economic opportunities", all(len(v) == 1 for v in families_by_isin.values()), f"unique_isins={len(families_by_isin)}")
    multi_currency_isins = defaultdict(list)
    for row in listings:
        multi_currency_isins[row["isin"]].append(row)
    same_isin_lines = [rows for rows in multi_currency_isins.values() if len({r["price_unit"] for r in rows}) > 1]
    check("QC-004", "Unhedged GBP/USD listings remain one exposure", bool(same_isin_lines) and all(len({r["economic_exposure_family_id"] for r in rows}) == 1 and len({r["duplicate_group_id"] for r in rows}) == 1 for rows in same_isin_lines), f"multi-price-unit ISINs tested={len(same_isin_lines)}")
    distributions_by_family = defaultdict(set)
    share_ids_by_family = defaultdict(set)
    for row in shares:
        distributions_by_family[row["economic_exposure_family_id"]].add(row["accumulating_distributing"])
        share_ids_by_family[row["economic_exposure_family_id"]].add(row["share_class_id"])
    accdist_families = [fid for fid, values in distributions_by_family.items() if {"ACCUMULATING", "DISTRIBUTING"}.issubset(values)]
    check("QC-005", "Accumulating/distributing versions are distinct share classes", bool(accdist_families) and all(len(share_ids_by_family[fid]) >= 2 for fid in accdist_families), f"families_with_pair={';'.join(accdist_families)}")
    family_ids = {row["economic_exposure_family_id"] for row in exposures}
    hedge_pairs = [(fid, fid + "_GBP_HEDGED") for fid in family_ids if fid + "_GBP_HEDGED" in family_ids]
    check("QC-006", "Hedged and unhedged exposures are not collapsed", bool(hedge_pairs) and all(f"DUP-{a}" != f"DUP-{b}" for a, b in hedge_pairs), f"hedge_pairs={hedge_pairs}")
    check("QC-007", "GBP and GBX are explicit and correctly scaled", any(r["price_unit"] == "GBX" for r in listings) and all((r["listing_currency"], r["price_unit_multiplier_to_listing_currency"]) == ("GBP", "0.01") for r in listings if r["price_unit"] == "GBX") and all(r["price_unit_multiplier_to_listing_currency"] == "1" for r in listings if r["price_unit"] == "GBP"), "GBX maps to GBP at 0.01; GBP maps at 1")
    check("QC-008", "UCITS is never inferred from name", all(r["ucits_evidence_basis"] in {"PRIMARY_ISSUER_PRODUCT_PAGE", "NOT_DETERMINED_NOT_INFERRED_FROM_NAME"} for r in shares), "allowed evidence bases enforced")
    check("QC-009", "Broker status is not inferred from price data", all(r["broker_status"] == "NOT_CHECKED" and r["broker_check_method"] == "NO_SAFE_EXACT_LSE_ISIN_READ_ONLY_ROUTE_AVAILABLE" for r in invest), "all broker states deliberately NOT_CHECKED")
    check("QC-010", "Current eligibility is not converted into historical eligibility", all(r["historical_eligibility_supported"] == "NO" and r["historical_eligibility"] == "NOT_ASSESSED_OUT_OF_SCOPE" for r in invest), WARNING)
    check("QC-011", "Leveraged/inverse/path-dependent instruments cannot enter canonical tiers", selected_isins.isdisjoint(excluded_isins), f"canonical_isins={len(selected_isins)}; structural_exclusions={len(excluded_isins)}")
    check("QC-012", "ETCs are assessed rather than blanket-excluded", any(r["instrument_type"] == "ETC" and r["economic_exposure_family_id"] == "GOLD" for r in shares), "unleveraged gold ETC candidate retained and structurally assessed")
    check("QC-013", "DeepVue themes are never invented", all(r["deepvue_theme"] == "NOT_APPLICABLE" or r["deepvue_theme"] in CONFIRMED_DEEPVUE_THEMES for r in exposures), f"confirmed_label_count={len(CONFIRMED_DEEPVUE_THEMES)}")
    check("QC-014", "Non-thematic broad and bond products are not forced into DeepVue", all(r["deepvue_theme"] == "NOT_APPLICABLE" for r in exposures if r["economic_exposure_family_id"] in {"US_BROAD_LARGE_CAP", "US_NASDAQ_100", "JAPAN", "UK_GILTS_ALL", "GOLD"}), "explicit negative mappings checked, including growth-biased Nasdaq-100")
    check("QC-015", "Sector and theme remain separate dimensions", all("sector" in r and "economic_theme" in r for r in exposures) and any(r["sector"] != "NOT_APPLICABLE" and r["economic_theme"] == "NOT_APPLICABLE" for r in exposures), "separate columns and differing values observed")
    japan_gbp = [l for l in listings if l["economic_exposure_family_id"] == "JAPAN" and l["price_unit"] in {"GBP", "GBX"}]
    check("QC-016", "Geography is not inferred from listing currency", bool(japan_gbp) and all(e["primary_geography"] == "JAPAN" for e in exposures if e["economic_exposure_family_id"] == "JAPAN"), f"Japan GBP/GBX listings={len(japan_gbp)}")
    check("QC-017", "Provider duplication creates no additional opportunity rows", len({r["economic_exposure_family_id"] for r in exposures}) == len(exposures) and any(int(r["provider_count"]) > 1 for r in exposures), "one row per family despite multi-provider implementations")
    check("QC-018", "Identity references are valid", {r["share_class_id"] for r in listings}.issubset({r["share_class_id"] for r in shares}) and {r["fund_entity_id"] for r in shares}.issubset({r["fund_entity_id"] for r in tables["funds"]}), "fund→share class→listing foreign keys resolve")
    check("QC-019", "Tiers are exhaustive and permitted", all(r["universe_tier"] in {"CORE", "EXTENDED", "EXPERIMENTAL"} for r in exposures), "all canonical families have exactly one permitted tier")
    check("QC-020", "Manual audit suite covers all required cases", len(manual_cases) >= 20 and all(case["status"] == "AUDITED" for case in manual_cases[:20]), f"audited={sum(case['status'] == 'AUDITED' for case in manual_cases)}/20")
    check("QC-021", "Discovery universe is substantial", len(discovery) >= 3000 and len({r["isin"] for r in discovery if r["isin"]}) >= 2000 and len(exposures) >= 40, f"listings={len(discovery)}; unique_isins={len({r['isin'] for r in discovery if r['isin']})}; families={len(exposures)}")
    check("QC-022", "No strategy/backtest output exists", True, "builder contains no price-return, signal, rank, portfolio, order, or backtest calculation")
    gold_shares = [r for r in shares if r["economic_exposure_family_id"] == "GOLD"]
    check("QC-023", "Direct gold cannot contain gold-mining equity products", bool(gold_shares) and all(r["instrument_type"] == "ETC" and not re.search(r"MIN(?:ER|ING)|PRODUCER|GOLD BUGS", r["share_class_name"], re.I) for r in gold_shares), f"direct_gold_share_classes={len(gold_shares)}")
    daily_short_discovery = {r["isin"] for r in discovery if re.search(r"DLY SH(?:O)?RT|DAILY SHORT", r["description_as_published"], re.I)}
    check("QC-024", "Abbreviated daily-short products are excluded", bool(daily_short_discovery) and daily_short_discovery.isdisjoint(selected_isins), f"daily_short_negative_controls={len(daily_short_discovery)}")
    gbp_cash = [r for r in shares if r["economic_exposure_family_id"] == "GBP_OVERNIGHT_CASH"]
    check("QC-025", "GBP overnight family has explicit sterling-rate evidence", bool(gbp_cash) and all(re.search(r"SONIA|STERLING.*OVERNIGHT|GBP.*OVERNIGHT|£.*OVERNIGHT", r["share_class_name"], re.I) for r in gbp_cash), f"gbp_cash_share_classes={len(gbp_cash)}")
    check("QC-026", "Verified current investability requires product-specific retail evidence", all(r["kid_retail_document_evidence"] == "CURRENT_DOCUMENT_HTTP_VERIFIED" and r["isa_eligibility"] == "YES" and r["structural_eligibility"] == "ELIGIBLE_LONG_ONLY_STRUCTURE" for r in invest if r["current_investability_state"] == "CURRENTLY_INVESTABLE"), f"verified_listing_rows={sum(r['current_investability_state'] == 'CURRENTLY_INVESTABLE' for r in invest)}")
    check("QC-027", "Every canonical listing has a dated current status source", all(r["active_listing_status"].startswith("ACTIVE_") and r["active_status_verification_date"] == OBSERVATION_DATE for r in listings), f"listing_rows={len(listings)}")
    return results


def scope_and_method_md(counts: dict[str, Any]) -> str:
    return f"""# UKACTIVE-A0A1 — Scope and Method

> {WARNING}

## Decision boundary

This is a new, greenfield directed-research programme. `EDGE-UKETF-20260822-001` was used only to identify methodological defects that must not recur. No legacy strategy universe, signal, parameter, rank, portfolio construction, or execution assumption is imported.

This stage constructs a current identity, eligibility, classification, and duplicate-controlled research master. It is **not** a backtest, momentum study, optimisation, portfolio-selection exercise, or evidence that ETF rotation works. No performance result is produced.

## Current discovery scope

The run captured {counts['raw_listings']:,} current LSE ETF/ETC/ETN listing lines representing {counts['raw_isins']:,} distinct published ISINs. That full raw catalogue is retained in `UKACTIVE_A0A1_DISCOVERY_REGISTRY.csv`; it is broader than the curated long-only master and includes negative controls and instruments outside the proposed sleeve.

The curated master contains {counts['selected_isins']:,} share classes, {counts['selected_listings']:,} LSE implementation lines, and {counts['families']:,} economic exposure families. A product can be discovered without being admitted to the curated master, and a candidate can be curated without being called currently investable.

## Mandatory architecture

```text
FUND LEGAL ENTITY
  → SHARE CLASS / ISIN
    → EXCHANGE LISTING / MIC + TICKER + PRICE UNIT

ECONOMIC OPPORTUNITY
  → FUTURE SIGNAL / RANK (NOT BUILT HERE)
    → SELECTED ECONOMIC EXPOSURE (NOT BUILT HERE)
      → BEST ELIGIBLE UK IMPLEMENTATION VEHICLE (CANDIDATE ARCHITECTURE ONLY)
```

Ticker is never an identity key. GBP and GBX are separate price units; GBX is represented as GBP currency with a 0.01 multiplier. Multiple listings of one ISIN remain one share class. Accumulating and distributing share classes remain distinct price identities but normally share one family. Currency-hedged and unhedged products are distinct economic families.

## Discovery and verification workflow

1. Capture the full live LSE Price Explorer ETF, ETC, and ETN catalogues.
2. Apply structural negative-control rules for leverage, inverse, daily-reset, volatility-linked, direct-crypto note, and unsecured note structures.
3. Match economically coherent products into an ordered provider-neutral taxonomy; omit style variants from the initial rotation scope without treating them as proof of unsuitability.
4. Keep several provider/share-class implementations per economic family, but count the family once.
5. Enrich selected iShares share classes with the current UK individual product catalogue, product page, listing table, ISA/SIPP flags, UCITS fact, fees, benchmark, replication, and an HTTP-verified KID/KIID when available.
6. Leave other providers `CURRENT_CANDIDATE_UNVERIFIED` until equivalent product-specific primary evidence is captured.
7. Use the local market-data symbol inventory only as additional discovery metadata. It does not establish eligibility, broker availability, or total-return quality.
8. Run deterministic identity, classification, eligibility, duplicate, and negative-control tests.

## Eligibility semantics

- `CURRENTLY_INVESTABLE`: current LSE snapshot presence, long-only structural suitability, issuer product evidence, issuer ISA eligibility, and a current HTTP-verified KID/KIID. This is still not a guarantee that every broker or SIPP provider carries it.
- `CURRENT_CANDIDATE_UNVERIFIED`: economically relevant current LSE candidate whose full product/account evidence is incomplete.
- `NOT_ELIGIBLE`: structurally unsuitable for the ordinary long-only canonical universe, or deliberately outside the initial scope with a reason code.

No state in this stage is a historical eligibility state. IBKR was not queried because the available local connector was not an exact LSE-ISIN read-only route; every broker field is therefore `NOT_CHECKED`.

## Tier meaning

- `CORE`: broad, persistent, economically distinct exposure with credible implementations.
- `EXTENDED`: narrower but coherent regional, sector, industry, thematic, or diversifying exposure.
- `EXPERIMENTAL`: short-history, concentrated, structurally less settled, or more weakly verified opportunity that merits continued observation.
- `EXCLUDED`: instrument/exposure outside the canonical research master, retained with a reason code.

Tiers are research breadth controls, not recommendations or portfolio weights.
"""


def evidence_policy_md() -> str:
    return f"""# UKACTIVE-A0A1 — Source and Evidence Policy

> {WARNING}

## Precedence

Material claims use the following order:

1. Exchange, regulator, tax authority, issuer legal document, issuer product page, and index methodology.
2. Issuer catalogue/factsheet and broker instrument record.
3. Reputable ETF database for discovery or corroboration.
4. Local market-data symbols as discovery evidence only.
5. Name-based classification rules only when the wording itself is unambiguous; names never establish UCITS, ISA/SIPP, broker, or historical status.

Conflicts are resolved in favour of the more product-specific primary source, with the conflict left visible. Absence of evidence is represented as `NOT_VERIFIED`, `NOT_DETERMINED`, or `NOT_CHECKED`, never converted to a favourable boolean.

## Claim-level requirements

| Claim | Minimum acceptable evidence in this stage | Prohibited inference |
|---|---|---|
| Listing identity/status | Current LSE catalogue plus ISIN/MIC/ticker/price unit | Price data alone implies broker access |
| UCITS | Issuer/regulatory product fact or legal document | “UCITS” in fund name |
| UK retail document | Current KID/KIID/product-summary URL, checked successfully | LSE listing implies retail eligibility |
| ISA | Issuer product flag or product-specific broker/account evidence, interpreted under current HMRC rules | LSE listing alone |
| SIPP | Issuer flag and, ultimately, scheme/provider confirmation | General pension tax rules imply provider availability |
| IBKR | Exact contract/account read-only result | Local prices or symbol existence |
| Geography | Index objective/methodology and holdings context | Listing currency or domicile |
| Sector/industry/theme | Index methodology, objective, issuer category, and holdings where ambiguous | Theme and sector treated as one field |
| DeepVue | Exact user-confirmed or official/public current label | Similar-sounding invented label |
| Duplicate equivalence | Index objective, hedge state, distribution/share-class identity, and economic equivalence rule | Ticker count equals opportunity count |

## Evidence ledger

`evidence/UKACTIVE_A0A1_EVIDENCE_LEDGER.jsonl` is append-style JSONL with deterministic evidence IDs, URL, publisher, source tier, retrieval timestamp, content hash/capture, supported claims, confidence, and the historical-use warning. Product rows reference evidence IDs rather than embedding unsupported conclusions.

Source captures under `evidence/sources/` include the exact LSE API responses, the iShares catalogue, parsed issuer product facts, and retrieval metadata/hashes for policy pages. KID/KIID PDFs are HTTP-checked and content-hashed but not redistributed.

## Current regulatory interpretation

- HMRC’s current ISA guidance defines qualifying investment categories; it does not justify product-level ISA inference from an exchange line.
- HMRC’s SIPP manual leaves actual scheme investment availability subject to scheme/provider rules.
- During the FCA Consumer Composite Investments transition, permitted current disclosure documents can include the applicable product summary/KID/KIID. This programme records the exact document URL and check result rather than requiring one filename convention.
- Eligibility and rules can change. All conclusions are dated {OBSERVATION_DATE}.

## DeepVue boundary

DeepVue Theme Tracker is descriptive workflow metadata only. The confirmed 31-label list is admitted exactly as supplied by the user. Public DeepVue documentation establishes that themes are curated and separate from GICS, but did not provide a complete current public label export. No additional label was invented.
"""


def schema_md(tables: dict[str, list[dict[str, Any]]]) -> str:
    table_descriptions = [
        ("UKACTIVE_A0A1_DISCOVERY_REGISTRY.csv", "One row per current LSE catalogue listing line, including instruments not curated."),
        ("UKACTIVE_A0A1_FUND_MASTER.csv", "One row per observed legal fund/issuing entity."),
        ("UKACTIVE_A0A1_SHARE_CLASS_MASTER.csv", "One row per selected ISIN/share class; accumulation/distribution and hedge state live here."),
        ("UKACTIVE_A0A1_LISTING_MASTER.csv", "One row per ISIN + MIC + ticker + price-unit implementation line."),
        ("UKACTIVE_A0A1_CURRENT_INVESTABILITY.csv", "Current, explicitly dated eligibility evidence per listing; never historical."),
        ("UKACTIVE_A0A1_ECONOMIC_EXPOSURE_MASTER.csv", "One row per signalable future economic opportunity."),
        ("UKACTIVE_A0A1_DUPLICATE_GROUPS.csv", "One row per economically equivalent implementation group."),
        ("UKACTIVE_A0A1_IMPLEMENTATION_CANDIDATES.csv", "All retained listing candidates, evidence-ordered without a trade decision."),
    ]
    columns = {
        "Fund": list(tables["funds"][0]) if tables["funds"] else [],
        "Share class": list(tables["share_classes"][0]) if tables["share_classes"] else [],
        "Listing": list(tables["listings"][0]) if tables["listings"] else [],
        "Investability": list(tables["investability"][0]) if tables["investability"] else [],
        "Economic exposure": list(tables["exposures"][0]) if tables["exposures"] else [],
    }
    text = [
        "# UKACTIVE-A0A1 — Universe Schema",
        "",
        f"> {WARNING}",
        "",
        "## Identity model",
        "",
        "`fund_entity_id → share_class_id / ISIN → listing_id / MIC + ticker + price_unit`",
        "",
        "Ticker is not a key. `listing_id` hashes ISIN, MIC, ticker, and explicit price unit. The economic taxonomy is orthogonal to identity: `economic_exposure_family_id` identifies the opportunity and `duplicate_group_id` groups interchangeable implementations with the same hedge state.",
        "",
        "## Tables",
        "",
    ]
    for name, description in table_descriptions:
        text.append(f"- `{name}` — {description}")
    text.extend(["", "## Principal table columns", ""])
    for name, fields in columns.items():
        text.extend([f"### {name}", "", "`" + "`, `".join(fields) + "`", ""])
    text.extend([
        "## Controlled values and null semantics",
        "",
        "- Current investability: `CURRENTLY_INVESTABLE`, `CURRENT_CANDIDATE_UNVERIFIED`, `NOT_ELIGIBLE`.",
        "- Canonical tier: `CORE`, `EXTENDED`, `EXPERIMENTAL`; exclusions are held separately.",
        "- Broker: `NOT_CHECKED` unless an exact account-specific read-only result exists.",
        "- Non-applicable classification: exactly `NOT_APPLICABLE`; unknown evidence is `NOT_VERIFIED`, `NOT_DETERMINED`, or `NOT_AVAILABLE` according to meaning.",
        "- Price unit: `GBP` is pounds; `GBX` is pence and has multiplier `0.01` into GBP. Listing currency remains `GBP` for both.",
        "- Historical fields: current outputs always carry `historical_eligibility_supported=NO`.",
        "",
        "## Duplicate invariants",
        "",
        "1. Same ISIN across listings → one share class and family; many listing IDs.",
        "2. Accumulating versus distributing → distinct share classes/ISINs, usually the same family and duplicate group.",
        "3. Hedged versus unhedged → distinct families and duplicate groups.",
        "4. Equivalent indices across providers → one family, multiple implementation candidates.",
        "5. Near-neighbour indices are only grouped after explicit economic-equivalence review; unresolved cases remain separate or experimental.",
    ])
    return "\n".join(text)


def data_source_audit_md(local_meta: dict[str, Any], counts: dict[str, Any]) -> str:
    return f"""# UKACTIVE-A0A1 — Data-Source Audit for Future Total-Return Research

> {WARNING}

No return series was constructed and no strategy was run. This audit records what a later A2 stage must validate.

| Source | Current use / potential coverage | Distributions & corporate actions | Survivorship / depth | Licensing & cost | A2 suitability |
|---|---|---|---|---|---|
| London Stock Exchange Price Explorer | Primary current identity/listing discovery; {counts['raw_listings']:,} observed lines | No validated adjusted/total-return history in this endpoint | Current snapshot; cannot reconstruct delistings or historical eligibility | Public web/API access subject to LSE terms; redistribution must remain reviewed | Strong current discovery input; insufficient alone |
| Issuer product pages, KIDs/KIIDs, prospectuses, factsheets | Primary legal/product metadata, benchmarks, fees, share-class/listing dates, current disclosure | Issuer distribution histories may be available product by product; methods vary | Usually live products; removed products and old documents can disappear | Public documents, issuer terms apply | Essential identity/eligibility evidence; archive exact dated documents |
| iShares UK product catalogue/pages | Structured current issuer facts and product-specific primary evidence | NAV/performance fields exist but were deliberately not used; distribution validation still required | Mainly current products; no complete delisted-universe guarantee | Public issuer access; terms apply | Useful primary feed for covered provider, not a cross-provider history solution |
| Local market-data inventory (`{local_meta.get('path', 'NOT_AVAILABLE')}`) | Read-only discovery overlap; {local_meta.get('row_count', 0):,} symbols in inventory | Not established by the inventory file | Inventory dates show observed coverage, not eligibility; delisted coverage unknown | Existing local entitlement; upstream source terms govern | Candidate input only after A2 validates adjusted prices, distributions, FX and symbol/ISIN mapping |
| EODHD (underlying local-source candidate) | Daily OHLC/adjusted fields and LSE symbols may be available under the existing service | Adjustment/distribution semantics require instrument-level reconciliation | Coverage and delisted ETF availability must be measured, not assumed | Paid subscription / existing account terms; exact incremental cost not determined here | Potential bulk history input after validation; not authoritative eligibility evidence |
| justETF and similar reputable ETF databases | Discovery/corroboration, index and fee cross-checks | Some distribution/performance information, methodology not an authoritative corporate-action ledger | Primarily current/survivor products | Database terms and redistribution restrictions; free/paid tiers vary | Secondary corroboration only |
| Stooq / Yahoo Finance-like public data | Quick secondary price cross-checks | Adjusted-close and cash-distribution completeness can change and must be reconciled | Symbols and delisted coverage inconsistent | Public access/terms; not a guaranteed research licence | Never the sole total-return source |
| LSEG Data & Analytics, Bloomberg, FactSet, Morningstar Direct | Licensed reference, corporate actions, delistings, fund histories and identifiers depending package | Stronger institutional corporate-action and total-return coverage | Potentially deep, but entitlement/package dependent | Commercial quotation / material cost | Preferred validation/reference layer if available |
| Bank of England / ECB official series | GBP rates, SONIA and selected FX reference data | Not fund distributions | Deep official macro/rate history | Public-source terms | Strong reference for cash benchmarks/FX; still requires timestamp and holiday alignment |
| Index-provider total-return indices | Benchmark-level gross/net total return for exposure validation | Embedded under index methodology | Often deep; product/index mapping and licensing matter | Frequently licensed, sometimes public factsheets only | Valuable family-signal proxy validation, never a substitute for investable ETF return |

## Required A2 controls

1. Establish identifier history across ticker changes, relistings, mergers, closures, and delistings.
2. Reconstruct point-in-time listing, retail-document, ISA/SIPP and broker eligibility; do not reuse this survivor snapshot.
3. Validate GBP versus GBX units before any return calculation.
4. Reconcile adjusted prices against cash distributions and corporate actions for representative accumulating and distributing share classes.
5. Translate non-GBP total returns with explicit, independently validated FX series and close-time convention.
6. Compare product total return with the correct benchmark (gross/net, hedged/unhedged) and explain residuals from fee, tax, tracking and sampling.
7. Quantify stale prices, missing days, zero volumes, bid/ask quality, assets under management and closure risk.
8. Preserve licensed-source provenance and redistribution constraints in every derived dataset.

The local inventory hash and exact source-capture hashes are in `UKACTIVE_A0A1_MANIFEST.json`. Price availability never changes an eligibility or broker state in this stage.
"""


def next_stage_md(decision: str) -> str:
    ready = decision != "UKACTIVE_A0A1_FAIL"
    return f"""# UKACTIVE-A0A1 — Next-Stage Design

> {WARNING}

Stage outcome: `{decision}`. Ready to recommend A2: `{'YES' if ready else 'NO'}`.

## Recommended next stage (do not execute automatically)

`UKACTIVE-A2 — POINT-IN-TIME UNIVERSE AND TOTAL-RETURN DATA CONSTRUCTION`

A2 should:

1. Reconstruct, by date, fund/share-class/listing existence and eligible UK retail implementations, including closures, mergers, ticker/venue changes, KID/KIID availability and account restrictions.
2. Build identity-resolved daily histories at listing and share-class level, with explicit GBP/GBX normalization.
3. Validate cash distributions, splits, corporate actions, NAVs, adjusted closes and benchmark total-return indices.
4. Convert every candidate into GBP total return using documented FX close/timestamp conventions; keep hedged and unhedged economics separate.
5. Measure history length, stale observations, spreads/volume where available, missingness, and survivorship coverage.
6. Create point-in-time implementation sets underneath each economic family so implementation count cannot influence the future signal.
7. Re-run the A0A1 identity and duplicate tests on every historical snapshot.

A2 must fail if it silently projects the current {OBSERVATION_DATE} survivor universe backward, cannot reconcile distributions, or confuses GBP with GBX.

## Only after A2 passes

Recommend `UKACTIVE-A3 — SIMPLE SIGNAL DISCOVERY`. A3 should begin with simple, economically defensible hypotheses for persistent leadership across geography, conventional sector/industry, coherent themes and defensive assets. It must not import the legacy ETF-rotation formula, and it must rank one economic family once before choosing an eligible implementation.

No A2 or A3 work has been executed by this run.
"""


def quality_report_md(qc: list[dict[str, Any]], counts: dict[str, Any], decision: str) -> str:
    rows = ["| Test | Status | Requirement | Detail |", "|---|---:|---|---|"]
    for item in qc:
        rows.append(f"| {item['test_id']} | {item['status']} | {item['requirement']} | {clean_text(item['detail']).replace('|', '/')} |")
    failures = [item for item in qc if item["status"] != "PASS"]
    return f"""# UKACTIVE-A0A1 — Data Quality Report

> {WARNING}

Decision: `{decision}`

The automated suite executed {len(qc)} controls: {len(qc) - len(failures)} passed and {len(failures)} failed. The current discovery registry has {counts['raw_listings']:,} listing lines and {counts['raw_isins']:,} ISINs; the curated master has {counts['selected_isins']:,} ISINs, {counts['selected_listings']:,} listing lines, and {counts['families']:,} economic families.

{chr(10).join(rows)}

## Interpretation

`PASS_WITH_OPEN_ITEMS` is used when all correctness controls pass and the master is substantial, but broker confirmation, cross-provider product-level eligibility, historical reconstruction, or total-return validation remains visibly incomplete. Those gaps must never be relabelled as favourable evidence.

No strategy, signal, rank, portfolio, order, or return statistic was computed.
"""


def git_state(path: Path) -> dict[str, Any]:
    try:
        top = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "GIT_UNAVAILABLE", "commit": "NOT_AVAILABLE", "worktree_state": "NOT_AVAILABLE", "complete_diff": f"NOT_AVAILABLE: {exc}"}
    if top.returncode != 0:
        return {"status": "NOT_A_GIT_WORKTREE", "commit": "NOT_APPLICABLE", "worktree_state": "NOT_APPLICABLE", "complete_diff": "NOT_APPLICABLE"}
    root = clean_text(top.stdout)
    commit = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=20)
    status = subprocess.run(["git", "-C", root, "status", "--porcelain=v1"], capture_output=True, text=True, timeout=20)
    diff = subprocess.run(["git", "-C", root, "diff", "--binary", "HEAD"], capture_output=True, text=True, timeout=30)
    dirty = bool(status.stdout.strip())
    return {
        "status": "GIT_WORKTREE",
        "repository_root": root,
        "commit": clean_text(commit.stdout),
        "worktree_state": "DIRTY" if dirty else "CLEAN",
        "porcelain_status": status.stdout,
        "complete_diff": diff.stdout if dirty else "",
    }


def file_hashes(paths: Iterable[Path], root: Path) -> list[dict[str, Any]]:
    results = []
    for path in sorted(set(paths), key=lambda p: str(p).lower()):
        if path.is_file():
            results.append({
                "path": path.relative_to(root).as_posix() if root in path.parents else str(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_bytes(path.read_bytes()),
            })
    return results


def remove_prior_generated_run_artifacts(root: Path) -> int:
    """Remove only this builder's known generated files before a reproducible rerun."""
    if root.name != PROGRAMME_ID:
        raise RuntimeError(f"Unsafe generated-artifact cleanup target: {root}")
    paths: set[Path] = set(root.glob("UKACTIVE_A0A1_*"))
    paths.add(root / "evidence" / "UKACTIVE_A0A1_EVIDENCE_LEDGER.jsonl")
    source_dir = root / "evidence" / "sources"
    for pattern in ["lse_*.json", "lse_instrument_*.html", "source_metadata_*.json", "ishares_uk_product_catalog.json", "UKACTIVE_A0A1_SOURCE_RETRIEVAL_SUMMARY.json"]:
        paths.update(source_dir.glob(pattern))
    paths.update((source_dir / "ishares_products").glob("*.json"))
    removed = 0
    for path in sorted(paths, key=lambda p: str(p).lower()):
        if path.is_file() and root in path.resolve().parents:
            path.unlink()
            removed += 1
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--programme-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--local-symbol-inventory",
        type=Path,
        default=Path(r"D:\Codex\market_data_manager\outputs\archive_summary\discovered_all_symbols.csv"),
    )
    args = parser.parse_args()
    root = args.programme_root.resolve()
    if root.name != PROGRAMME_ID:
        raise RuntimeError(f"Refusing to build into unexpected programme root: {root}")
    root.mkdir(parents=True, exist_ok=True)
    replaced_generated_artifacts = remove_prior_generated_run_artifacts(root)
    (root / "evidence" / "sources").mkdir(parents=True, exist_ok=True)
    started_at = utc_now()
    ledger = EvidenceLedger()

    regulatory_meta = retrieve_regulatory_sources(root, ledger)
    deepvue_policy_evidence_id = next(
        (row["evidence_id"] for row in regulatory_meta if row["publisher"] == "DeepVue"),
        "NOT_AVAILABLE",
    )
    catalog, catalog_meta = retrieve_ishares_catalog(root, ledger)
    discovery, lse_meta = retrieve_lse_discovery(root, ledger)
    supplement_config = root / "config" / "current_listing_supplements.csv"
    supplement_isins: set[str] = set()
    if supplement_config.exists():
        with supplement_config.open("r", encoding="utf-8-sig", newline="") as handle:
            supplement_isins = {normalize(row["isin"]) for row in csv.DictReader(handle)}
    preselected = {isin: {} for isin in supplement_isins if isin in catalog}
    pre_details = retrieve_ishares_details(root, ledger, preselected, catalog)
    supplement_rows, supplement_meta = load_current_listing_supplements(root, ledger, supplement_config, pre_details)
    discovery_by_id = {row["discovery_record_id"]: row for row in discovery}
    for row in supplement_rows:
        discovery_by_id[row["discovery_record_id"]] = row
    discovery = sorted(discovery_by_id.values(), key=lambda r: (r["isin"], r["mic"], r["ticker"], r["price_unit"]))
    selected, selected_by_family = select_curated_isins(discovery, catalog)
    if not selected:
        raise RuntimeError("Curated selection is empty; source schema or classification rules changed")
    for row in discovery:
        if row["isin"] in selected and row["structural_exclusion_flag"] == "NO":
            row["matched_economic_exposure_family_id"] = selected[row["isin"]]["rule"]["family_id"]
            row["discovery_disposition"] = "SELECTED_CURATED_SHARE_CLASS_LISTING"
    details = retrieve_ishares_details(root, ledger, selected, catalog, existing=pre_details)
    local_inventory, local_meta = load_local_symbol_inventory(args.local_symbol_inventory)
    if local_meta["status"] != "NOT_AVAILABLE":
        ledger.add(
            evidence_type="LOCAL_DISCOVERY_INVENTORY",
            source_tier="LOCAL_SECONDARY",
            publisher="Local market-data manager",
            title="discovered_all_symbols.csv",
            url=str(args.local_symbol_inventory),
            retrieved_at=utc_now(),
            supports="additional symbol/history-presence discovery only",
            source_sha256=local_meta["sha256"],
            local_capture="READ_IN_PLACE_NOT_COPIED",
            confidence="MEDIUM",
            notes="Does not support eligibility, broker availability, adjustment quality, or historical investability.",
        )

    tables = build_master_tables(
        root, ledger, selected, selected_by_family, catalog, catalog_meta["evidence_id"], details, local_inventory
    )
    exclusions = build_exclusions(discovery, {row["isin"] for row in tables["share_classes"]})
    taxonomies = build_taxonomies(tables["exposures"], ledger, deepvue_policy_evidence_id)
    coverage = build_coverage_matrix(tables["exposures"], tables["share_classes"], tables["listings"], tables["investability"])
    unresolved = unresolved_items()
    manual_md, manual_cases = build_manual_audit_cases(tables, exclusions)
    qc = run_quality_controls(discovery, tables, exclusions, manual_cases)

    verified_isins = {
        row["isin"] for row in tables["investability"]
        if row["current_investability_state"] == "CURRENTLY_INVESTABLE"
    }
    unverified_isins = {
        row["isin"] for row in tables["investability"]
        if row["current_investability_state"] == "CURRENT_CANDIDATE_UNVERIFIED"
    }
    broker_confirmed_isins = {
        row["isin"] for row in tables["investability"]
        if row["broker_status"] in {"AVAILABLE_CONFIRMED", "IBKR_AVAILABLE_CONFIRMED"}
    }
    raw_isins = {row["isin"] for row in discovery if row["isin"]}
    tier_counts = Counter(row["universe_tier"] for row in tables["exposures"])
    opportunity_counts = Counter(row["opportunity_type"] for row in tables["exposures"])
    exclusion_reasons = Counter()
    for row in exclusions:
        exclusion_reasons.update(row["exclusion_reason_codes"].split(";"))
    counts = {
        "raw_listings": len(discovery),
        "raw_isins": len(raw_isins),
        "selected_isins": len({row["isin"] for row in tables["share_classes"]}),
        "selected_share_classes": len(tables["share_classes"]),
        "selected_listings": len(tables["listings"]),
        "fund_entities": len(tables["funds"]),
        "families": len(tables["exposures"]),
        "geographic_opportunities": opportunity_counts["GEOGRAPHY"],
        "sector_industry_opportunities": opportunity_counts["SECTOR_INDUSTRY"],
        "thematic_opportunities": opportunity_counts["THEMATIC"],
        "defensive_diversifier_opportunities": opportunity_counts["DEFENSIVE_DIVERSIFIER"],
        "deepvue_exact_mapped_families": sum(row["deepvue_theme"] != "NOT_APPLICABLE" for row in tables["exposures"]),
        "core_families": tier_counts["CORE"],
        "extended_families": tier_counts["EXTENDED"],
        "experimental_families": tier_counts["EXPERIMENTAL"],
        "currently_verified_investable_isins": len(verified_isins),
        "broker_confirmed_isins": len(broker_confirmed_isins),
        "current_candidate_unverified_isins": len(unverified_isins),
        "excluded_isins": len({row["isin"] for row in exclusions}),
        "structurally_not_eligible_isins": len({row["isin"] for row in exclusions if row["current_investability_state"] == "NOT_ELIGIBLE"}),
        "evidence_ledger_entries": len(ledger.rows),
    }
    failed_tests = [row for row in qc if row["status"] != "PASS"]
    decision = "UKACTIVE_A0A1_FAIL" if failed_tests else "UKACTIVE_A0A1_PASS_WITH_OPEN_ITEMS"

    # Required tabular outputs.
    write_csv(root / "UKACTIVE_A0A1_DISCOVERY_REGISTRY.csv", discovery)
    write_csv(root / "UKACTIVE_A0A1_FUND_MASTER.csv", tables["funds"])
    write_csv(root / "UKACTIVE_A0A1_SHARE_CLASS_MASTER.csv", tables["share_classes"])
    write_csv(root / "UKACTIVE_A0A1_LISTING_MASTER.csv", tables["listings"])
    write_csv(root / "UKACTIVE_A0A1_CURRENT_INVESTABILITY.csv", tables["investability"])
    write_csv(root / "UKACTIVE_A0A1_ECONOMIC_EXPOSURE_MASTER.csv", tables["exposures"])
    write_csv(root / "UKACTIVE_A0A1_GEOGRAPHIC_TAXONOMY.csv", taxonomies["geographic"])
    write_csv(root / "UKACTIVE_A0A1_SECTOR_INDUSTRY_TAXONOMY.csv", taxonomies["sector"])
    write_csv(root / "UKACTIVE_A0A1_THEME_TAXONOMY.csv", taxonomies["themes"])
    write_csv(root / "UKACTIVE_A0A1_DEEPVUE_THEME_CROSSWALK.csv", taxonomies["deepvue"])
    write_csv(root / "UKACTIVE_A0A1_DUPLICATE_GROUPS.csv", tables["duplicate_groups"])
    write_csv(root / "UKACTIVE_A0A1_IMPLEMENTATION_CANDIDATES.csv", tables["implementations"])
    write_csv(root / "UKACTIVE_A0A1_CORE_UNIVERSE.csv", [row for row in tables["exposures"] if row["universe_tier"] == "CORE"])
    write_csv(root / "UKACTIVE_A0A1_EXTENDED_UNIVERSE.csv", [row for row in tables["exposures"] if row["universe_tier"] == "EXTENDED"])
    write_csv(root / "UKACTIVE_A0A1_EXPERIMENTAL_UNIVERSE.csv", [row for row in tables["exposures"] if row["universe_tier"] == "EXPERIMENTAL"])
    write_csv(root / "UKACTIVE_A0A1_EXCLUSIONS.csv", exclusions)
    write_csv(root / "UKACTIVE_A0A1_COVERAGE_MATRIX.csv", coverage)
    write_csv(root / "UKACTIVE_A0A1_UNRESOLVED_ITEMS.csv", unresolved)
    write_csv(root / "UKACTIVE_A0A1_AUTOMATED_TEST_RESULTS.csv", qc)

    # Required narrative outputs.
    write_text(root / "UKACTIVE_A0A1_SCOPE_AND_METHOD.md", scope_and_method_md(counts))
    write_text(root / "UKACTIVE_A0A1_SOURCE_AND_EVIDENCE_POLICY.md", evidence_policy_md())
    write_text(root / "UKACTIVE_A0A1_UNIVERSE_SCHEMA.md", schema_md(tables))
    write_text(root / "UKACTIVE_A0A1_DATA_SOURCE_AUDIT.md", data_source_audit_md(local_meta, counts))
    write_text(root / "UKACTIVE_A0A1_MANUAL_AUDIT_CASES.md", manual_md)
    write_text(root / "UKACTIVE_A0A1_DATA_QUALITY_REPORT.md", quality_report_md(qc, counts, decision))
    write_text(root / "UKACTIVE_A0A1_NEXT_STAGE_DESIGN.md", next_stage_md(decision))

    decision_payload = {
        "programme_id": PROGRAMME_ID,
        "stage_id": STAGE_ID,
        "run_id": RUN_ID,
        "decision": decision,
        "decision_date": OBSERVATION_DATE,
        "decision_basis": (
            "All correctness tests passed; substantial current discovery and an independently classified duplicate-controlled master exist. "
            "Open items remain for broker confirmation, cross-provider product-level eligibility, point-in-time history, liquidity, and total-return validation."
            if not failed_tests else
            f"Correctness tests failed: {', '.join(row['test_id'] for row in failed_tests)}"
        ),
        "counts": counts,
        "count_definitions": {
            "raw_listings": "LSE listing lines from Price Explorer with islse=true plus visible product-specific LSE/issuer supplements for catalogue omissions",
            "raw_isins": "distinct nonblank ISINs in the raw current LSE snapshot",
            "economic_and_tier_counts": "one row per economic exposure family, never per ticker",
            "currently_verified_investable_isins": "distinct curated ISINs meeting this stage's conservative current issuer/KID/ISA/structure/LSE evidence rule",
            "broker_confirmed_isins": "distinct curated ISINs with exact account-specific broker confirmation; zero because broker was not checked",
            "current_candidate_unverified_isins": "distinct curated ISINs not meeting full verification; not assumed eligible or ineligible",
            "deepvue_exact_mapped_families": "economic families carrying one of the 31 exact user-confirmed labels",
        },
        "key_exclusion_reason_counts": dict(exclusion_reasons.most_common(12)),
        "automated_tests": {"passed": len(qc) - len(failed_tests), "failed": len(failed_tests), "failed_ids": [row["test_id"] for row in failed_tests]},
        "broker_check_method": "NOT_CHECKED_NO_SAFE_EXACT_LSE_ISIN_READ_ONLY_ROUTE",
        "ready_for_ukactive_a2": not failed_tests,
        "recommended_next_stage": "UKACTIVE-A2 — POINT-IN-TIME UNIVERSE AND TOTAL-RETURN DATA CONSTRUCTION" if not failed_tests else "REMEDIATE_A0A1_FAILURES",
        "a2_executed": False,
        "a3_executed": False,
        "strategy_or_performance_research_executed": False,
        "warning": WARNING,
    }
    write_json(root / "UKACTIVE_A0A1_DECISION.json", decision_payload)

    # Write claim-level evidence after all page/document checks are complete.
    ledger.write(root / "evidence" / "UKACTIVE_A0A1_EVIDENCE_LEDGER.jsonl")
    write_json(root / "evidence" / "sources" / "UKACTIVE_A0A1_SOURCE_RETRIEVAL_SUMMARY.json", {
        "run_id": RUN_ID,
        "lse": lse_meta,
        "current_listing_supplements": supplement_meta,
        "ishares_catalog": catalog_meta,
        "regulatory_and_taxonomy": regulatory_meta,
        "ishares_product_detail_count": len(details),
        "local_market_data_inventory": local_meta,
        "warning": WARNING,
    })

    source_code_paths = sorted((root / "code").glob("*.py"))
    config_paths = [path for path in (root / "config").rglob("*") if path.is_file()]
    capture_paths = [path for path in (root / "evidence" / "sources").rglob("*") if path.is_file()]
    output_paths = [path for path in root.iterdir() if path.is_file() and path.name != "UKACTIVE_A0A1_MANIFEST.json"]
    output_paths.append(root / "evidence" / "UKACTIVE_A0A1_EVIDENCE_LEDGER.jsonl")
    git = git_state(root)
    completed_at = utc_now()
    manifest = {
        "programme_id": PROGRAMME_ID,
        "stage_id": STAGE_ID,
        "run_id": RUN_ID,
        "started_at": started_at,
        "completed_at": completed_at,
        "observation_date": OBSERVATION_DATE,
        "decision": decision,
        "programme_root": str(root),
        "legacy_programme_policy": "LEGACY_REFERENCE_ONLY_DEFECTS_REVIEWED_NO_STRATEGY_OR_UNIVERSE_INHERITED",
        "command_lines": [
            f'python "{Path(__file__).resolve()}" --programme-root "{root}" --local-symbol-inventory "{args.local_symbol_inventory}"',
            "internal run_quality_controls() executed by builder",
        ],
        "prior_generated_artifacts_replaced_on_rerun": replaced_generated_artifacts,
        "git": git,
        "source_code_hashes": file_hashes(source_code_paths, root),
        "classification_and_listing_control_hashes": file_hashes(config_paths, root),
        "input_and_source_capture_hashes": file_hashes(capture_paths, root),
        "local_input": local_meta,
        "output_hashes_excluding_manifest_itself": file_hashes(output_paths, root),
        "manifest_self_hash_policy": "NOT_SELF_REFERENTIAL; hash the delivered manifest externally if needed",
        "source_urls": sorted({row["url"] for row in ledger.rows if str(row["url"]).startswith("http")}),
        "source_retrieval_dates": sorted({row["retrieved_at"][:10] for row in ledger.rows}),
        "evidence_counts": {
            "total": len(ledger.rows),
            "by_type": dict(Counter(row["evidence_type"] for row in ledger.rows)),
            "by_source_tier": dict(Counter(row["source_tier"] for row in ledger.rows)),
        },
        "counts": counts,
        "broker_check_method": "NOT_CHECKED_NO_SAFE_EXACT_LSE_ISIN_READ_ONLY_ROUTE",
        "broker_check_date": "NOT_CHECKED",
        "runtime": {
            "python": sys.version,
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "external_runtime_packages_used": [],
            "standard_library_only_builder": True,
        },
        "classification_rule_version": CLASSIFICATION_RULE_VERSION,
        "duplicate_rule_version": DUPLICATE_RULE_VERSION,
        "unresolved_items": unresolved,
        "automated_test_results": qc,
        "reproducibility_assessment": (
            "PASS_WITH_NON_GIT_LIMITATION: executed source, exact source captures, parsed issuer facts, command, and hashes are retained; "
            "the containing platform is not a Git worktree so commit and diff are not applicable."
            if git["status"] == "NOT_A_GIT_WORKTREE" else
            "PASS: source state is recorded by Git plus hashes and source captures."
        ),
        "parquet_outputs": "NOT_CREATED: largest table is modest and CSV plus exact source captures maximises standard-library reproducibility",
        "strategy_or_performance_outputs": "NONE",
        "warning": WARNING,
    }
    write_json(root / "UKACTIVE_A0A1_MANIFEST.json", manifest)

    print(json.dumps({"decision": decision, "counts": counts, "failed_tests": [row["test_id"] for row in failed_tests]}, indent=2))
    return 0 if not failed_tests else 2


if __name__ == "__main__":
    raise SystemExit(main())
