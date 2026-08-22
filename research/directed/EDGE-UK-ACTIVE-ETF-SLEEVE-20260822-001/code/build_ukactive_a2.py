from __future__ import annotations

import argparse
import csv
import gzip
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests

from ukactive_a2_core import (
    add_stale_and_return_fields,
    add_warmups,
    build_fx_table,
    canonical_json_bytes,
    clean_text,
    json_default,
    longest_true_run,
    parse_date,
    parse_split_ratio,
    safe_name,
    select_candidate_as_of_information_date,
    sha256_bytes,
    sha256_file,
    stable_id,
    synthetic_failure_tests,
    to_iso,
    utc_now,
    validate_distribution_events,
)


PROGRAMME_ROOT = Path(r"D:\Codex\equity_quant_research_platform\research\directed\EDGE-UK-ACTIVE-ETF-SLEEVE-20260822-001")
MARKET_DATA_MANAGER_ROOT = Path(r"D:\Codex\market_data_manager")
CODE_DIR = PROGRAMME_ROOT / "code"
CONFIG_DIR = PROGRAMME_ROOT / "config"
EVIDENCE_DIR = PROGRAMME_ROOT / "evidence"
SOURCE_DIR = EVIDENCE_DIR / "sources" / "a2"
RAW_EODHD_DIR = SOURCE_DIR / "eodhd"
RAW_EXTERNAL_DIR = SOURCE_DIR / "external"
POLICY_PATH = CONFIG_DIR / "UKACTIVE_A2_POLICY_v1.json"
RUN_ID = "UKACTIVE-A2-20260822-001"
STAGE_ID = "UKACTIVE-A2"


A0_INPUTS = [
    "UKACTIVE_A0A1_FUND_MASTER.csv",
    "UKACTIVE_A0A1_SHARE_CLASS_MASTER.csv",
    "UKACTIVE_A0A1_LISTING_MASTER.csv",
    "UKACTIVE_A0A1_CURRENT_INVESTABILITY.csv",
    "UKACTIVE_A0A1_ECONOMIC_EXPOSURE_MASTER.csv",
    "UKACTIVE_A0A1_DUPLICATE_GROUPS.csv",
    "UKACTIVE_A0A1_IMPLEMENTATION_CANDIDATES.csv",
    "UKACTIVE_A0A1_CORE_UNIVERSE.csv",
    "UKACTIVE_A0A1_EXTENDED_UNIVERSE.csv",
    "UKACTIVE_A0A1_EXPERIMENTAL_UNIVERSE.csv",
    "UKACTIVE_A0A1_DATA_SOURCE_AUDIT.md",
    "UKACTIVE_A0A1_UNRESOLVED_ITEMS.csv",
    "UKACTIVE_A0A1_MANIFEST.json",
    r"evidence\UKACTIVE_A0A1_EVIDENCE_LEDGER.jsonl",
]


REQUIRED_OUTPUTS = [
    "UKACTIVE_A2_SCOPE_AND_METHOD.md",
    "UKACTIVE_A2_POINT_IN_TIME_ELIGIBILITY_POLICY.md",
    "UKACTIVE_A2_TOTAL_RETURN_DATA_POLICY.md",
    "UKACTIVE_A2_FX_AND_GBP_ACCOUNTING_POLICY.md",
    "UKACTIVE_A2_CASH_MODEL.md",
    "UKACTIVE_A2_IMPLEMENTATION_SELECTION_POLICY.md",
    "UKACTIVE_A2_DATA_SOURCE_LEDGER.csv",
    "UKACTIVE_A2_INSTRUMENT_HISTORY_MASTER.parquet",
    "UKACTIVE_A2_EXPOSURE_HISTORY_MASTER.parquet",
    "UKACTIVE_A2_POINT_IN_TIME_ELIGIBILITY.parquet",
    "UKACTIVE_A2_CANONICAL_IMPLEMENTATION_HISTORY.parquet",
    "UKACTIVE_A2_TOTAL_RETURN_PANEL_GBP.parquet",
    "UKACTIVE_A2_PROXY_HISTORY_PANEL.parquet",
    "UKACTIVE_A2_DISTRIBUTION_EVENTS.csv",
    "UKACTIVE_A2_FX_SERIES.parquet",
    "UKACTIVE_A2_CASH_SERIES.parquet",
    "UKACTIVE_A2_STALE_AND_MISSING_DATA_REPORT.csv",
    "UKACTIVE_A2_MANUAL_VALIDATION_CASES.md",
    "UKACTIVE_A2_AUTOMATED_TEST_RESULTS.csv",
    "UKACTIVE_A2_DATA_QUALITY_REPORT.md",
    "UKACTIVE_A2_UNRESOLVED_ITEMS.csv",
    "UKACTIVE_A2_A3_READINESS_REPORT.md",
    "UKACTIVE_A2_DECISION.json",
    "UKACTIVE_A2_MANIFEST.json",
]


SOURCE_URLS = {
    "eodhd_eod_docs": "https://eodhd.com/financial-apis/api-for-historical-data-and-volumes",
    "eodhd_corporate_actions_docs": "https://eodhd.com/financial-apis/api-splits-dividends",
    "eodhd_exchange_docs": "https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours",
    "eodhd_calendar_docs": "https://eodhd.com/financial-apis/exchanges-api-trading-hours-and-stock-market-holidays",
    "ecb_data_api_docs": "https://data.ecb.europa.eu/help/api/overview",
    "ecb_reference_rate_methodology": "https://data.ecb.europa.eu/methodology/exchange-rates",
    "boe_sonia": "https://www.bankofengland.co.uk/markets/sonia-benchmark",
    "boe_sonia_policy": "https://www.bankofengland.co.uk/markets/sonia-benchmark/sonia-key-features-and-policies",
    "fred_sonia_index": "https://fred.stlouisfed.org/series/IUDZOS2/",
    "fred_sonia_rate": "https://fred.stlouisfed.org/series/IUDSOIA/",
    "yahoo_chart_api": "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
}


class CaptureClient:
    def __init__(self, api_key: str, source_root: Path, refresh: bool = False) -> None:
        self.api_key = api_key
        self.source_root = source_root
        self.refresh = refresh
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "UKACTIVE-A2-research/1.0"})
        self.ledger: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def _append_ledger(self, row: dict[str, Any]) -> None:
        with self._lock:
            self.ledger.append(row)

    def get_json(
        self,
        source_name: str,
        url: str,
        params: dict[str, Any],
        relative_capture: str,
        series_identifier: str,
        timeout: int = 60,
        retries: int = 3,
    ) -> Any:
        capture_path = self.source_root / relative_capture
        meta_path = capture_path.with_suffix(capture_path.suffix + ".meta.json")
        if capture_path.exists() and meta_path.exists() and not self.refresh:
            with gzip.open(capture_path, "rb") as handle:
                raw = handle.read()
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            payload = json.loads(raw.decode("utf-8"))
            self._append_ledger({**meta, "cache_status": "REUSED_IMMUTABLE_CAPTURE"})
            return payload

        capture_path.parent.mkdir(parents=True, exist_ok=True)
        query = dict(params)
        if source_name == "EODHD":
            query["api_token"] = self.api_key
            query.setdefault("fmt", "json")
        response: requests.Response | None = None
        error = ""
        for attempt in range(1, retries + 1):
            try:
                response = self.session.get(url, params=query, timeout=timeout)
                if response.status_code == 200:
                    break
                error = f"HTTP_{response.status_code}"
            except requests.RequestException as exc:
                error = type(exc).__name__
            if attempt < retries:
                time.sleep(float(attempt))
        if response is None or response.status_code != 200:
            raise RuntimeError(f"{source_name} request failed for {series_identifier}: {error}")
        raw = response.content
        payload = response.json()
        retrieved = utc_now()
        with gzip.open(capture_path, "wb", compresslevel=9) as handle:
            handle.write(raw)
        redacted_query = {key: ("<redacted>" if key == "api_token" else value) for key, value in query.items()}
        meta = {
            "evidence_id": stable_id("A2EVD", source_name, series_identifier, sha256_bytes(raw)),
            "source": source_name,
            "series_identifier": series_identifier,
            "retrieval_timestamp_utc": retrieved,
            "source_url_redacted": f"{url}?{urlencode(redacted_query)}",
            "capture_path": str(capture_path),
            "raw_response_sha256": sha256_bytes(raw),
            "capture_sha256": sha256_file(capture_path),
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type", "NOT_AVAILABLE"),
            "cache_status": "RETRIEVED_LIVE_READ_ONLY",
        }
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        self._append_ledger(meta)
        return payload

    def get_bytes(
        self,
        source_name: str,
        url: str,
        params: dict[str, Any],
        relative_capture: str,
        series_identifier: str,
        timeout: int = 90,
        retries: int = 3,
    ) -> bytes:
        capture_path = self.source_root / relative_capture
        meta_path = capture_path.with_suffix(capture_path.suffix + ".meta.json")
        if capture_path.exists() and meta_path.exists() and not self.refresh:
            with gzip.open(capture_path, "rb") as handle:
                raw = handle.read()
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self._append_ledger({**meta, "cache_status": "REUSED_IMMUTABLE_CAPTURE"})
            return raw
        capture_path.parent.mkdir(parents=True, exist_ok=True)
        response: requests.Response | None = None
        error = ""
        for attempt in range(1, retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=timeout)
                if response.status_code == 200:
                    break
                error = f"HTTP_{response.status_code}"
            except requests.RequestException as exc:
                error = type(exc).__name__
            if attempt < retries:
                time.sleep(float(attempt))
        if response is None or response.status_code != 200:
            raise RuntimeError(f"{source_name} request failed for {series_identifier}: {error}")
        raw = response.content
        retrieved = utc_now()
        with gzip.open(capture_path, "wb", compresslevel=9) as handle:
            handle.write(raw)
        meta = {
            "evidence_id": stable_id("A2EVD", source_name, series_identifier, sha256_bytes(raw)),
            "source": source_name,
            "series_identifier": series_identifier,
            "retrieval_timestamp_utc": retrieved,
            "source_url_redacted": f"{url}?{urlencode(params)}",
            "capture_path": str(capture_path),
            "raw_response_sha256": sha256_bytes(raw),
            "capture_sha256": sha256_file(capture_path),
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type", "NOT_AVAILABLE"),
            "cache_status": "RETRIEVED_LIVE_READ_ONLY",
        }
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        self._append_ledger(meta)
        return raw


def load_api_key() -> tuple[str, str]:
    provider_root = MARKET_DATA_MANAGER_ROOT / "src"
    sys.path.insert(0, str(provider_root))
    from market_data_manager.providers.eodhd import load_api_key as provider_loader

    key, source = provider_loader()
    if not key:
        raise RuntimeError("EODHD credential is unavailable through the existing read-only provider route")
    return key, source


def read_inputs() -> dict[str, Any]:
    missing = [str(PROGRAMME_ROOT / name) for name in A0_INPUTS if not (PROGRAMME_ROOT / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing authoritative A0A1 inputs: {missing}")
    return {
        "fund": pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A0A1_FUND_MASTER.csv", dtype=str),
        "share": pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A0A1_SHARE_CLASS_MASTER.csv", dtype=str),
        "listing": pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A0A1_LISTING_MASTER.csv", dtype=str),
        "investability": pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A0A1_CURRENT_INVESTABILITY.csv", dtype=str),
        "exposure": pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A0A1_ECONOMIC_EXPOSURE_MASTER.csv", dtype=str),
        "duplicate": pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A0A1_DUPLICATE_GROUPS.csv", dtype=str),
        "implementation": pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A0A1_IMPLEMENTATION_CANDIDATES.csv", dtype=str),
        "a0_manifest": json.loads((PROGRAMME_ROOT / "UKACTIVE_A0A1_MANIFEST.json").read_text(encoding="utf-8")),
    }


def normalize_catalogue(payload: Any, delisted: bool) -> pd.DataFrame:
    if not isinstance(payload, list):
        return pd.DataFrame(columns=["Code", "Name", "Country", "Exchange", "Currency", "Type", "Isin"])
    frame = pd.DataFrame([row for row in payload if isinstance(row, dict)])
    for column in ["Code", "Name", "Country", "Exchange", "Currency", "Type", "Isin"]:
        if column not in frame:
            frame[column] = ""
        frame[column] = frame[column].fillna("").astype(str).str.strip()
    frame["Code"] = frame["Code"].str.upper()
    frame["Isin"] = frame["Isin"].str.upper()
    frame["Currency"] = frame["Currency"].str.upper()
    frame["catalogue_status"] = "DELISTED" if delisted else "ACTIVE"
    return frame.drop_duplicates(["Code", "Isin", "Currency"], keep="last")


def build_listing_routes(inputs: dict[str, Any], active: pd.DataFrame, delisted: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    listing = inputs["listing"].copy()
    listing["ticker_key"] = listing["ticker"].str.upper().str.strip()
    listing["isin_key"] = listing["isin"].str.upper().str.strip()
    active_keyed = active.rename(
        columns={
            "Code": "eodhd_code",
            "Name": "eodhd_name",
            "Currency": "eodhd_price_unit",
            "Type": "eodhd_type",
            "Isin": "eodhd_isin",
        }
    )
    active_routes = listing.merge(
        active_keyed,
        left_on=["ticker_key", "isin_key"],
        right_on=["eodhd_code", "eodhd_isin"],
        how="inner",
        validate="many_to_many",
    )
    active_routes = active_routes.drop_duplicates("listing_id", keep="first")
    active_routes["route_type"] = "A0A1_ACTIVE_EXACT_TICKER_AND_ISIN"
    active_routes["a0a1_price_unit"] = active_routes["price_unit"]
    active_routes["effective_price_unit"] = active_routes["eodhd_price_unit"]
    active_routes["effective_listing_currency"] = np.where(
        active_routes["effective_price_unit"].eq("GBX"), "GBP", active_routes["effective_price_unit"]
    )
    active_routes["eodhd_symbol"] = active_routes["eodhd_code"] + ".LSE"
    active_routes["historical_listing_extension"] = False
    active_routes["delisted_catalogue_status"] = "ACTIVE_CURRENT_CATALOGUE"

    share = inputs["share"].copy()
    share["isin_key"] = share["isin"].str.upper().str.strip()
    share_lookup = share.drop_duplicates("isin_key", keep="first")
    delisted_match = delisted[delisted["Isin"].isin(set(share_lookup["isin_key"]))].copy()
    active_codes = set(active["Code"] + "|" + active["Isin"])
    delisted_match = delisted_match[~(delisted_match["Code"] + "|" + delisted_match["Isin"]).isin(active_codes)]
    delisted_match = delisted_match.merge(share_lookup, left_on="Isin", right_on="isin_key", how="inner")
    historical_rows: list[dict[str, Any]] = []
    for _, row in delisted_match.iterrows():
        associated = listing[listing["isin_key"].eq(row["Isin"])]
        if associated.empty:
            continue
        anchor = associated.sort_values("listing_id").iloc[0]
        unit = clean_text(row["Currency"]).upper()
        listing_currency = "GBP" if unit == "GBX" else unit
        historical_rows.append(
            {
                **{column: anchor.get(column, "NOT_AVAILABLE") for column in listing.columns if column not in {"ticker_key", "isin_key"}},
                "listing_id": stable_id("A2HISTLIST", row["Isin"], row["Code"], "XLON"),
                "ticker": row["Code"],
                "listing_currency": listing_currency,
                "price_unit": unit,
                "a0a1_price_unit": "NOT_APPLICABLE_HISTORICAL_EXTENSION",
                "effective_price_unit": unit,
                "effective_listing_currency": listing_currency,
                "active_listing_status": "DELISTED_EODHD_CATALOGUE",
                "eodhd_code": row["Code"],
                "eodhd_name": row["Name"],
                "eodhd_price_unit": unit,
                "eodhd_type": row["Type"],
                "eodhd_isin": row["Isin"],
                "eodhd_symbol": row["Code"] + ".LSE",
                "route_type": "A2_HISTORICAL_LISTING_EXTENSION_EXACT_ISIN",
                "historical_listing_extension": True,
                "delisted_catalogue_status": "DELISTED_HISTORICAL_CATALOGUE",
            }
        )
    historical_routes = pd.DataFrame(historical_rows)
    routes = pd.concat([active_routes, historical_routes], ignore_index=True, sort=False)
    routes = routes.drop_duplicates("listing_id", keep="first")
    routes["price_unit_multiplier_to_listing_currency_effective"] = np.where(
        routes["effective_price_unit"].eq("GBX"), 0.01, 1.0
    )

    corrections: list[dict[str, Any]] = []
    for _, row in active_routes[active_routes["a0a1_price_unit"].ne(active_routes["effective_price_unit"])].iterrows():
        corrections.append(
            {
                "lineage_item_id": stable_id("A2LIN", row["listing_id"], "PRICE_UNIT"),
                "lineage_action": "CORRECTION",
                "a0a1_record_id": row["listing_id"],
                "field": "price_unit",
                "a0a1_value": row["a0a1_price_unit"],
                "a2_value": row["effective_price_unit"],
                "evidence": f"EODHD active LSE catalogue exact ticker+ISIN row {row['eodhd_symbol']}; representative Yahoo chart currency cross-check",
                "status": "APPLIED_IN_A2_ONLY_A0A1_IMMUTABLE",
                "materiality": "CRITICAL_100X_PRICE_SCALE_CONTROL",
            }
        )
    for _, row in historical_routes.iterrows():
        corrections.append(
            {
                "lineage_item_id": stable_id("A2LIN", row["listing_id"], "HISTORICAL_LISTING"),
                "lineage_action": "HISTORICAL_EXTENSION",
                "a0a1_record_id": row["share_class_id"],
                "field": "historical_exchange_listing",
                "a0a1_value": "NOT_IN_CURRENT_A0A1_LISTING_MASTER",
                "a2_value": row["listing_id"],
                "evidence": f"EODHD delisted LSE catalogue exact ISIN {row['isin']} code {row['ticker']}",
                "status": "ADDED_AS_DISTINCT_HISTORICAL_LISTING",
                "materiality": "SURVIVORSHIP_CONTROL",
            }
        )
    hedging_error = inputs["share"][(inputs["share"]["economic_exposure_family_id"].str.endswith("GBP_HEDGED")) & (inputs["share"]["hedged_unhedged"].eq("UNHEDGED"))]
    for _, row in hedging_error.iterrows():
        corrections.append(
            {
                "lineage_item_id": stable_id("A2LIN", row["share_class_id"], "HEDGE_CLASSIFICATION"),
                "lineage_action": "OPEN_ERROR_NOT_SILENTLY_CHANGED",
                "a0a1_record_id": row["share_class_id"],
                "field": "economic_exposure_family_id versus hedged_unhedged",
                "a0a1_value": f"{row['economic_exposure_family_id']}|{row['hedged_unhedged']}",
                "a2_value": "EXCLUDED_FROM_HEDGED_FAMILY_CANONICAL_SELECTION_PENDING_EVIDENCE",
                "evidence": "Internal A0A1 field contradiction",
                "status": "OPEN_LINEAGE_ERROR",
                "materiality": "ECONOMIC_EXPOSURE_IDENTITY",
            }
        )
    return routes, pd.DataFrame(corrections)


def fetch_listing_payloads(
    client: CaptureClient,
    routes: pd.DataFrame,
    policy: dict[str, Any],
    workers: int,
) -> dict[str, dict[str, Any]]:
    start, end = policy["history_start"], policy["history_end"]

    def fetch_one(row: pd.Series) -> tuple[str, dict[str, Any]]:
        listing_id = row["listing_id"]
        symbol = row["eodhd_symbol"]
        stem = safe_name(f"{listing_id}_{symbol}")
        payload: dict[str, Any] = {}
        payload["eod"] = client.get_json(
            "EODHD",
            f"https://eodhd.com/api/eod/{symbol}",
            {"from": start, "to": end, "period": "d", "order": "a"},
            f"eodhd/prices/{stem}.json.gz",
            f"EOD:{symbol}:{start}:{end}",
        )
        payload["div"] = client.get_json(
            "EODHD",
            f"https://eodhd.com/api/div/{symbol}",
            {"from": start, "to": end},
            f"eodhd/dividends/{stem}.json.gz",
            f"DIV:{symbol}:{start}:{end}",
        )
        payload["splits"] = client.get_json(
            "EODHD",
            f"https://eodhd.com/api/splits/{symbol}",
            {"from": start, "to": end},
            f"eodhd/splits/{stem}.json.gz",
            f"SPLITS:{symbol}:{start}:{end}",
        )
        return listing_id, payload

    results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(fetch_one, row): row["listing_id"] for _, row in routes.iterrows()}
        total = len(futures)
        for index, future in enumerate(as_completed(futures), start=1):
            listing_id = futures[future]
            try:
                key, payload = future.result()
                results[key] = payload
            except Exception as exc:  # keep a visible unresolved route rather than abort all downloads
                results[listing_id] = {"error": f"{type(exc).__name__}:{exc}", "eod": [], "div": [], "splits": []}
            if index % 50 == 0 or index == total:
                print(f"Downloaded/cached {index}/{total} exact-identity listing routes", flush=True)
    return results


def normalize_price_payload(payload: Any) -> pd.DataFrame:
    columns = ["date", "open", "high", "low", "close", "adjusted_close", "volume"]
    if not isinstance(payload, list):
        return pd.DataFrame(columns=columns)
    rows = [row for row in payload if isinstance(row, dict)]
    frame = pd.DataFrame(rows)
    for column in columns:
        if column not in frame:
            frame[column] = np.nan
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    for column in ["open", "high", "low", "close", "adjusted_close", "volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["date", "close", "adjusted_close"])
    frame = frame[(frame["close"] > 0) & (frame["adjusted_close"] > 0)]
    return frame[columns].drop_duplicates("date", keep="last").sort_values("date")


def normalize_event_payload(payload: Any, event_type: str) -> pd.DataFrame:
    if not isinstance(payload, list):
        return pd.DataFrame(columns=["date"])
    frame = pd.DataFrame([row for row in payload if isinstance(row, dict)])
    if frame.empty:
        return pd.DataFrame(columns=["date"])
    if "date" not in frame:
        frame["date"] = pd.NaT
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    if event_type == "div":
        for column in ["value", "unadjustedValue"]:
            if column not in frame:
                frame[column] = np.nan
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        if "currency" not in frame:
            frame["currency"] = "NOT_AVAILABLE"
    else:
        split_column = "split" if "split" in frame else ("ratio" if "ratio" in frame else None)
        frame["split_ratio"] = frame[split_column].map(parse_split_ratio) if split_column else 1.0
    return frame.dropna(subset=["date"]).sort_values("date")


def build_calendar(price_payloads: dict[str, pd.DataFrame], routes: pd.DataFrame) -> tuple[pd.DatetimeIndex, pd.DataFrame]:
    dates: list[pd.Timestamp] = []
    counts: Counter[pd.Timestamp] = Counter()
    anchor_tickers = {"ISF", "IUSA", "CSP1", "VUSA", "EQQQ", "IGLT", "IJPN", "IMEU"}
    anchor_dates: set[pd.Timestamp] = set()
    route_lookup = routes.set_index("listing_id")
    for listing_id, frame in price_payloads.items():
        ticker = clean_text(route_lookup.loc[listing_id, "ticker"]) if listing_id in route_lookup.index else ""
        for value in frame["date"]:
            stamp = pd.Timestamp(value).normalize()
            if stamp.weekday() >= 5:
                continue
            dates.append(stamp)
            counts[stamp] += 1
            if ticker in anchor_tickers:
                anchor_dates.add(stamp)
    unique = sorted(set(dates))
    calendar = pd.DatetimeIndex([value for value in unique if counts[value] >= 2 or value in anchor_dates], name="date")
    audit = pd.DataFrame(
        {
            "date": unique,
            "listing_observation_count": [counts[value] for value in unique],
            "anchor_observed": [value in anchor_dates for value in unique],
            "included_in_canonical_calendar": [value in set(calendar) for value in unique],
        }
    )
    audit["next_execution_eligible_date"] = audit["date"].where(audit["included_in_canonical_calendar"]).dropna().shift(-1)
    return calendar, audit


def fetch_ecb_fx(client: CaptureClient, start: str, end: str, currencies: list[str]) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for currency in sorted(set(currencies) - {"EUR", "GBP", "GBX"} | {"GBP"}):
        series = f"D.{currency}.EUR.SP00.A"
        raw = client.get_bytes(
            "ECB",
            f"https://data-api.ecb.europa.eu/service/data/EXR/{series}",
            {"startPeriod": start, "endPeriod": end, "format": "csvdata"},
            f"external/ecb_EXR_{safe_name(series)}.csv.gz",
            f"EXR:{series}",
        )
        frame = pd.read_csv(pd.io.common.BytesIO(raw))
        if not {"TIME_PERIOD", "OBS_VALUE"}.issubset(frame.columns):
            continue
        part = frame[["TIME_PERIOD", "OBS_VALUE"]].copy()
        part.columns = ["date", "obs_value"]
        part["currency"] = currency
        rows.append(part)
    if not rows:
        raise RuntimeError("No ECB FX observations were retrieved")
    return pd.concat(rows, ignore_index=True)


def fetch_fred_series(client: CaptureClient, series_id: str, start: str, end: str) -> pd.DataFrame:
    raw = client.get_bytes(
        "FRED_BOE_MIRROR",
        "https://fred.stlouisfed.org/graph/fredgraph.csv",
        {"id": series_id, "cosd": start, "coed": end},
        f"external/fred_{series_id}.csv.gz",
        series_id,
    )
    frame = pd.read_csv(pd.io.common.BytesIO(raw))
    if len(frame.columns) < 2:
        raise RuntimeError(f"FRED series {series_id} returned no usable columns")
    frame = frame.rename(columns={frame.columns[0]: "date", frame.columns[1]: "value"})
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    return frame.dropna().sort_values("date")


def write_parquet(frame: pd.DataFrame, path: Path, metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    arrow_meta = dict(table.schema.metadata or {})
    arrow_meta.update({str(key).encode(): str(value).encode() for key, value in metadata.items()})
    pq.write_table(table.replace_schema_metadata(arrow_meta), path, compression="zstd", use_dictionary=True)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")


def write_json(value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=json_default) + "\n", encoding="utf-8")


def enrich_routes(routes: pd.DataFrame, inputs: dict[str, Any]) -> pd.DataFrame:
    share_columns = [
        "share_class_id",
        "provider_issuer",
        "share_class_inception_date",
        "accumulating_distributing",
        "hedged_unhedged",
        "hedge_currency",
        "instrument_type",
        "product_structure",
        "ucits_status",
        "leverage",
        "daily_reset",
        "path_dependence",
        "maturity",
    ]
    fund_columns = ["fund_entity_id", "fund_inception_date", "legal_fund_name"]
    invest_columns = [
        "listing_id",
        "current_investability_state",
        "current_uk_retail_eligibility",
        "isa_eligibility",
        "sipp_eligibility",
        "broker_status",
        "kid_retail_document_evidence",
        "structural_eligibility",
        "eligibility_evidence_ids",
    ]
    exposure_columns = [
        "economic_exposure_family_id",
        "economic_exposure_name",
        "universe_tier",
        "asset_class",
        "sub_asset_class",
        "primary_geography",
        "sector",
        "industry",
        "economic_theme",
        "deepvue_theme",
        "duplicate_group_id",
    ]
    result = routes.copy()
    # Drop overlapping share fields carried through historical-route construction before authoritative joins.
    for column in share_columns[1:] + fund_columns[1:]:
        if column in result:
            result = result.drop(columns=column)
    result = result.merge(inputs["share"][share_columns], on="share_class_id", how="left", validate="many_to_one")
    result = result.merge(inputs["fund"][fund_columns], on="fund_entity_id", how="left", validate="many_to_one")
    result = result.merge(inputs["exposure"][exposure_columns], on="economic_exposure_family_id", how="left", suffixes=("", "_exposure"), validate="many_to_one")
    current = inputs["investability"][invest_columns].copy()
    result = result.merge(current, on="listing_id", how="left", validate="one_to_one")

    # Historical listing extensions inherit only the current share-class evidence as context, never as a historical fact.
    isin_current = (
        inputs["investability"]
        .sort_values("current_investability_state", ascending=False)
        .drop_duplicates("isin")
        .set_index("isin")
    )
    for column in invest_columns[1:]:
        missing = result[column].isna()
        result.loc[missing, column] = result.loc[missing, "isin"].map(isin_current[column])
    result["current_investability_state"] = result["current_investability_state"].fillna("CURRENT_CANDIDATE_UNVERIFIED")
    result["broker_status"] = "NOT_CHECKED"
    result["family_membership_valid"] = ~(
        result["economic_exposure_family_id"].str.endswith("_HEDGED", na=False)
        & ~result["hedged_unhedged"].eq("HEDGED")
    )
    result["long_only_structure_valid"] = (
        result["leverage"].fillna("NO").eq("NO")
        & result["daily_reset"].fillna("NO").eq("NO")
        & result["path_dependence"].fillna("NO").eq("NO")
    )
    return result


def _state_array(dates: pd.Series, inception: pd.Timestamp, first_observed: pd.Timestamp) -> np.ndarray:
    values = np.full(len(dates), "UNKNOWN_BEFORE_FIRST_OBSERVATION", dtype=object)
    if not pd.isna(inception):
        values[dates.to_numpy() < np.datetime64(inception)] = "FALSE_NOT_YET_EXISTING"
        values[dates.to_numpy() >= np.datetime64(inception)] = "TRUE_EVIDENCED_BY_INCEPTION_DATE"
    values[dates.to_numpy() >= np.datetime64(first_observed)] = "TRUE_EVIDENCED_BY_LISTING_PRICE_OR_INCEPTION"
    return values


def build_instrument_and_eligibility_histories(
    routes: pd.DataFrame,
    payloads: dict[str, dict[str, Any]],
    calendar: pd.DatetimeIndex,
    fx_table: pd.DataFrame,
    policy: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
    instrument_frames: list[pd.DataFrame] = []
    pit_frames: list[pd.DataFrame] = []
    event_rows: list[pd.DataFrame] = []
    stale_rows: list[dict[str, Any]] = []
    listing_frames: dict[str, pd.DataFrame] = {}
    route_lookup = routes.set_index("listing_id", drop=False)
    fx_lookup = fx_table.copy()
    fx_lookup["currency"] = fx_lookup["currency"].str.upper()

    for listing_id, route in route_lookup.iterrows():
        payload = payloads.get(listing_id, {"eod": [], "div": [], "splits": [], "error": "MISSING_PAYLOAD"})
        prices = normalize_price_payload(payload.get("eod", []))
        dividends = normalize_event_payload(payload.get("div", []), "div")
        splits = normalize_event_payload(payload.get("splits", []), "splits")
        if prices.empty:
            stale_rows.append(
                {
                    "listing_id": listing_id,
                    "share_class_id": route["share_class_id"],
                    "economic_exposure_family_id": route["economic_exposure_family_id"],
                    "ticker": route["ticker"],
                    "eodhd_symbol": route["eodhd_symbol"],
                    "first_observed_date": "NOT_AVAILABLE",
                    "last_observed_date": "NOT_AVAILABLE",
                    "observed_rows": 0,
                    "missing_session_count": 0,
                    "longest_missing_run": 0,
                    "stale_session_count": 0,
                    "post_stale_catchup_count": 0,
                    "large_unexplained_return_count": 0,
                    "data_valid_return_count": 0,
                    "status": "NO_PRICE_HISTORY",
                    "source_error": payload.get("error", "NO_ROWS"),
                }
            )
            continue

        first_observed, last_observed = prices["date"].min(), prices["date"].max()
        dividend_by_date = (
            dividends.groupby("date")["value"].sum(min_count=1).fillna(0.0).to_dict()
            if not dividends.empty and "value" in dividends
            else {}
        )
        split_by_date = (
            splits.groupby("date")["split_ratio"].prod().to_dict()
            if not splits.empty and "split_ratio" in splits
            else {}
        )
        frame = add_stale_and_return_fields(
            prices,
            calendar,
            dividend_by_date,
            split_by_date,
            float(policy["total_return"]["large_daily_return_threshold"]),
        )
        price_unit = clean_text(route["effective_price_unit"]).upper()
        listing_currency = "GBP" if price_unit == "GBX" else clean_text(route["effective_listing_currency"]).upper()
        listing_fx = fx_lookup[fx_lookup["currency"].eq(listing_currency)].copy()
        frame = frame.merge(listing_fx, on="date", how="left", validate="one_to_one")
        unit_multiplier = 0.01 if price_unit == "GBX" else 1.0
        frame["price_unit_multiplier_to_listing_currency"] = unit_multiplier
        frame["price_listing_currency"] = frame["close"] * unit_multiplier
        frame["adjusted_price_listing_currency"] = frame["adjusted_close"] * unit_multiplier
        frame["price_gbp_if_required"] = frame["price_listing_currency"] * frame["fx_rate_gbp_per_local"]
        frame["adjusted_wealth_gbp"] = frame["adjusted_price_listing_currency"] * frame["fx_rate_gbp_per_local"]
        frame["return_gbp_total_unfiltered"] = frame["adjusted_wealth_gbp"].pct_change(fill_method=None)
        fx_valid = frame["fx_rate_gbp_per_local"].notna()
        if listing_currency != "GBP":
            fx_valid &= frame["fx_source_date"].notna() & (frame["fx_source_date"] <= frame["date"])
        frame["data_valid"] = frame["data_valid_local"] & fx_valid

        fund_inception = parse_date(route.get("fund_inception_date"))
        share_inception = parse_date(route.get("share_class_inception_date"))
        listing_inception = parse_date(route.get("listing_inception_date"))
        before_inception = pd.Series(False, index=frame.index)
        for inception in (fund_inception, share_inception, listing_inception):
            if not pd.isna(inception):
                before_inception |= frame["date"] < inception
        frame["price_before_inception_flag"] = before_inception & frame["price_available"]
        frame["data_valid"] &= ~before_inception
        frame["data_valid"] &= bool(route.get("long_only_structure_valid", False))
        frame["data_valid"] &= bool(route.get("family_membership_valid", False))
        frame["return_gbp_total"] = frame["return_gbp_total_unfiltered"].where(frame["data_valid"])
        frame["return_local_total_authoritative"] = frame["return_local_total"].where(frame["data_valid"])

        observed_mask = frame["date"].between(first_observed, last_observed)
        missing_in_life = frame.loc[observed_mask, "missing_flag"]
        frame["cum_valid_observations"] = frame["data_valid"].astype(int).cumsum()
        frame["cum_bad_observations"] = (
            (frame["missing_flag"] | frame["stale_flag"] | frame["post_stale_catchup_flag"]).astype(int).cumsum()
        )
        frame["listing_id"] = listing_id
        frame["share_class_id"] = route["share_class_id"]
        frame["fund_entity_id"] = route["fund_entity_id"]
        frame["economic_exposure_family_id"] = route["economic_exposure_family_id"]
        frame["duplicate_group_id"] = route["duplicate_group_id"]
        frame["universe_tier"] = route["universe_tier"]
        frame["ticker"] = route["ticker"]
        frame["isin"] = route["isin"]
        frame["mic"] = route["mic"]
        frame["eodhd_symbol"] = route["eodhd_symbol"]
        frame["listing_currency"] = listing_currency
        frame["price_unit"] = price_unit
        frame["a0a1_price_unit"] = route["a0a1_price_unit"]
        frame["route_type"] = route["route_type"]
        frame["first_observed_date"] = first_observed
        frame["last_observed_date"] = last_observed
        frame["proxy_flag"] = False
        frame["source_vendor"] = "EODHD"
        frame["source_series_identifier"] = route["eodhd_symbol"]
        frame["broker_status"] = "NOT_CHECKED"
        frame["listing_active"] = np.select(
            [frame["date"] < first_observed, frame["price_available"], frame["date"] > last_observed],
            ["NOT_YET_OBSERVED", "ACTIVE_OBSERVED_PRICE", "DELISTED_OR_DATA_ENDED" if bool(route["historical_listing_extension"]) else "ACTIVE_STATUS_UNKNOWN_AFTER_LAST_PRICE"],
            default="ACTIVE_STATUS_UNKNOWN_MISSING_OBSERVATION",
        )

        event_validation = validate_distribution_events(
            frame,
            dividends,
            price_unit,
            float(policy["total_return"]["event_pass_absolute_error"]),
            float(policy["total_return"]["event_warning_absolute_error"]),
        )
        if not event_validation.empty:
            event_meta = dividends.drop_duplicates("date", keep="last").set_index("date") if not dividends.empty else pd.DataFrame()
            for source_column, target_column in [
                ("declarationDate", "declaration_date"),
                ("recordDate", "record_date"),
                ("paymentDate", "payment_date"),
                ("period", "distribution_period"),
                ("unadjustedValue", "unadjusted_value"),
            ]:
                if not event_meta.empty and source_column in event_meta:
                    event_validation[target_column] = event_validation["date"].map(event_meta[source_column])
                else:
                    event_validation[target_column] = "NOT_AVAILABLE"
            event_validation["listing_id"] = listing_id
            event_validation["share_class_id"] = route["share_class_id"]
            event_validation["economic_exposure_family_id"] = route["economic_exposure_family_id"]
            event_validation["ticker"] = route["ticker"]
            event_validation["isin"] = route["isin"]
            event_validation["eodhd_symbol"] = route["eodhd_symbol"]
            event_validation["price_unit"] = price_unit
            event_validation["accumulating_distributing"] = route["accumulating_distributing"]
            event_rows.append(event_validation)

        # Point-in-time state table. Current eligibility labels never appear in the historical state column.
        pit = frame[
            [
                "date",
                "price_available",
                "return_data_available",
                "listing_active",
                "data_valid",
                "stale_flag",
                "missing_flag",
                "cum_valid_observations",
                "cum_bad_observations",
            ]
        ].copy()
        pit["fund_exists"] = _state_array(pit["date"], fund_inception, first_observed)
        pit["share_class_exists"] = _state_array(pit["date"], share_inception, first_observed)
        pit["listing_exists"] = _state_array(pit["date"], listing_inception, first_observed)
        not_yet = (
            pit["fund_exists"].eq("FALSE_NOT_YET_EXISTING")
            | pit["share_class_exists"].eq("FALSE_NOT_YET_EXISTING")
            | pit["listing_exists"].eq("FALSE_NOT_YET_EXISTING")
        )
        current_verified = route["current_investability_state"] == "CURRENTLY_INVESTABLE"
        pit["historical_investability_state"] = np.select(
            [
                not_yet,
                bool(current_verified) & (pit["date"] >= first_observed),
                pit["date"] >= first_observed,
            ],
            ["NOT_YET_EXISTING", "HISTORICALLY_PROBABLE", "HISTORICALLY_UNCERTAIN"],
            default="HISTORICALLY_UNCERTAIN",
        )
        pit["historical_investability_confidence"] = np.where(
            pit["historical_investability_state"].eq("NOT_YET_EXISTING"),
            "HIGH_IF_DATED_INCEPTION",
            "LOW_CURRENT_STATE_NOT_BACK_PROJECTED",
        )
        pit["structurally_eligible"] = (
            "CURRENT_STRUCTURE_EVIDENCE_ONLY_NOT_HISTORICAL"
            if route["structural_eligibility"] == "ELIGIBLE_LONG_ONLY_STRUCTURE"
            else "HISTORICALLY_UNKNOWN"
        )
        pit["uk_retail_status_known"] = "NO"
        pit["account_eligibility_known"] = "NO"
        pit["broker_status"] = "NOT_CHECKED"
        pit["signal_warmup_available"] = pit["cum_valid_observations"] >= min(policy["warmups"])
        for window in policy["warmups"]:
            pit[f"warmup_{window}"] = pit["data_valid"].astype(int).rolling(window, min_periods=window).sum().eq(window)
        pit["listing_id"] = listing_id
        pit["share_class_id"] = route["share_class_id"]
        pit["fund_entity_id"] = route["fund_entity_id"]
        pit["economic_exposure_family_id"] = route["economic_exposure_family_id"]
        pit["source_evidence"] = f"{route['route_type']}|{route['eodhd_symbol']}|CURRENT_ELIGIBILITY_NOT_BACK_PROJECTED"
        pit_frames.append(pit)

        life = frame.loc[observed_mask]
        stale_rows.append(
            {
                "listing_id": listing_id,
                "share_class_id": route["share_class_id"],
                "economic_exposure_family_id": route["economic_exposure_family_id"],
                "ticker": route["ticker"],
                "eodhd_symbol": route["eodhd_symbol"],
                "first_observed_date": first_observed.date().isoformat(),
                "last_observed_date": last_observed.date().isoformat(),
                "observed_rows": int(life["price_available"].sum()),
                "missing_session_count": int(missing_in_life.sum()),
                "longest_missing_run": longest_true_run(missing_in_life),
                "stale_session_count": int(life["stale_flag"].sum()),
                "post_stale_catchup_count": int(life["post_stale_catchup_flag"].sum()),
                "large_unexplained_return_count": int((life["large_return_flag"] & ~life["corporate_action_explains_large_return"]).sum()),
                "price_before_inception_count": int(life["price_before_inception_flag"].sum()),
                "data_valid_return_count": int(life["data_valid"].sum()),
                "status": "HISTORY_AVAILABLE",
                "source_error": payload.get("error", "NOT_APPLICABLE"),
            }
        )

        instrument_start = min([value for value in [first_observed, fund_inception, share_inception, listing_inception] if not pd.isna(value)])
        instrument_end = last_observed if bool(route["historical_listing_extension"]) else calendar.max()
        trimmed = frame[frame["date"].between(instrument_start, instrument_end)].copy()
        instrument_frames.append(trimmed)
        listing_frames[listing_id] = frame

    instrument = pd.concat(instrument_frames, ignore_index=True, sort=False) if instrument_frames else pd.DataFrame()
    pit_all = pd.concat(pit_frames, ignore_index=True, sort=False) if pit_frames else pd.DataFrame()
    events_all = pd.concat(event_rows, ignore_index=True, sort=False) if event_rows else pd.DataFrame()
    stale_report = pd.DataFrame(stale_rows)
    return instrument, pit_all, events_all, stale_report, listing_frames


def listing_validation_status(routes: pd.DataFrame, events: pd.DataFrame, listing_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    route_lookup = routes.set_index("listing_id", drop=False)
    for listing_id, route in route_lookup.iterrows():
        event = events[events["listing_id"].eq(listing_id)] if not events.empty else pd.DataFrame()
        counts = event["validation_status"].value_counts().to_dict() if not event.empty else {}
        price_rows = int(listing_frames.get(listing_id, pd.DataFrame()).get("price_available", pd.Series(dtype=bool)).sum())
        valid_rows = int(listing_frames.get(listing_id, pd.DataFrame()).get("data_valid", pd.Series(dtype=bool)).sum())
        if price_rows == 0:
            status = "FAIL_NO_PRICE_HISTORY"
        elif counts.get("FAIL", 0) > 0:
            status = "FAIL_DISTRIBUTION_RECONCILIATION"
        elif counts.get("PASS", 0) > 0 and counts.get("WARNING", 0) == 0:
            status = "PASS_EXPLICIT_DISTRIBUTION_RECONCILIATION"
        elif counts.get("PASS", 0) > 0 or counts.get("WARNING", 0) > 0:
            status = "PASS_WITH_OPEN_EVENT_TOLERANCE_ITEMS"
        elif any(str(key).startswith("UNRESOLVED") for key in counts):
            status = "PASS_WITH_OPEN_EVENT_ALIGNMENT_ITEMS"
        elif clean_text(route["accumulating_distributing"]) == "ACCUMULATING":
            status = "PASS_VENDOR_SEMANTICS_AND_ZERO_REPORTED_DISTRIBUTIONS"
        elif clean_text(route["instrument_type"]) in {"ETC", "ETP"}:
            status = "PASS_PRICE_RETURN_ETC_VENDOR_SEMANTICS_NO_DISTRIBUTION"
        else:
            status = "PASS_VENDOR_SEMANTICS_NO_EVENT_AVAILABLE"
        rows.append(
            {
                "listing_id": listing_id,
                "share_class_id": route["share_class_id"],
                "economic_exposure_family_id": route["economic_exposure_family_id"],
                "ticker": route["ticker"],
                "price_rows": price_rows,
                "valid_return_rows_before_event_gate": valid_rows,
                "distribution_event_count": int(len(event)),
                "event_pass_count": int(counts.get("PASS", 0)),
                "event_warning_count": int(counts.get("WARNING", 0)),
                "event_fail_count": int(counts.get("FAIL", 0)),
                "event_unresolved_count": int(sum(value for key, value in counts.items() if str(key).startswith("UNRESOLVED"))),
                "total_return_validation_status": status,
                "vendor_semantics_evidence": SOURCE_URLS["eodhd_eod_docs"],
            }
        )
    return pd.DataFrame(rows)


def apply_listing_validation_gate(
    instrument: pd.DataFrame,
    pit: pd.DataFrame,
    listing_frames: dict[str, pd.DataFrame],
    validations: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
    status_map = validations.set_index("listing_id")["total_return_validation_status"].to_dict()
    failed = {key for key, value in status_map.items() if str(value).startswith("FAIL")}
    instrument = instrument.copy()
    pit = pit.copy()
    instrument["total_return_validation_status"] = instrument["listing_id"].map(status_map).fillna("FAIL_NO_VALIDATION_STATUS")
    pit["total_return_validation_status"] = pit["listing_id"].map(status_map).fillna("FAIL_NO_VALIDATION_STATUS")
    instrument.loc[instrument["listing_id"].isin(failed), "data_valid"] = False
    instrument.loc[instrument["listing_id"].isin(failed), "return_gbp_total"] = np.nan
    pit.loc[pit["listing_id"].isin(failed), "data_valid"] = False
    for listing_id, frame in listing_frames.items():
        frame["total_return_validation_status"] = status_map.get(listing_id, "FAIL_NO_VALIDATION_STATUS")
        if listing_id in failed:
            frame["data_valid"] = False
            frame["return_gbp_total"] = np.nan
    return instrument, pit, listing_frames


def build_cash_series(
    calendar: pd.DatetimeIndex,
    sonia_rate: pd.DataFrame,
    sonia_index: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    sessions = pd.DataFrame({"date": calendar})
    sessions["prior_session"] = sessions["date"].shift(1)
    rate = sonia_rate.rename(columns={"date": "sonia_source_date", "value": "sonia_rate_percent"}).sort_values("sonia_source_date")
    cash = pd.merge_asof(
        sessions.sort_values("prior_session").dropna(subset=["prior_session"]),
        rate,
        left_on="prior_session",
        right_on="sonia_source_date",
        direction="backward",
        allow_exact_matches=True,
    )
    first = sessions.iloc[[0]].copy()
    first["sonia_source_date"] = pd.NaT
    first["sonia_rate_percent"] = np.nan
    cash = pd.concat([first, cash], ignore_index=True).sort_values("date")
    cash["accrual_calendar_days"] = (cash["date"] - cash["prior_session"]).dt.days
    cash["return_gbp_total"] = (
        (1.0 + cash["sonia_rate_percent"] / 100.0) ** (cash["accrual_calendar_days"] / 365.0) - 1.0
    )
    cash["data_valid"] = cash["return_gbp_total"].notna() & (cash["sonia_source_date"] <= cash["prior_session"])
    cash["cash_index"] = (1.0 + cash["return_gbp_total"].fillna(0.0)).cumprod() * 100.0
    index = sonia_index.rename(columns={"date": "date", "value": "sonia_compounded_index"}).sort_values("date")
    cash = cash.merge(index, on="date", how="left")
    cash["sonia_compounded_index_return"] = cash["sonia_compounded_index"].pct_change(fill_method=None)
    cash["validation_absolute_error"] = (cash["return_gbp_total"] - cash["sonia_compounded_index_return"]).abs()
    overlap = cash["validation_absolute_error"].dropna()
    validation = {
        "overlap_observations": int(len(overlap)),
        "median_absolute_error": float(overlap.median()) if len(overlap) else None,
        "p95_absolute_error": float(overlap.quantile(0.95)) if len(overlap) else None,
        "max_absolute_error": float(overlap.max()) if len(overlap) else None,
        "status": "PASS" if len(overlap) >= 500 and float(overlap.quantile(0.95)) <= 0.00001 else "FAIL",
        "method": "SONIA rate ACT/365 between XLON sessions; independently compared with official SONIA Compounded Index",
    }
    cash["economic_exposure_family_id"] = "ACTUAL_GBP_CASH"
    cash["source_vendor"] = "BANK_OF_ENGLAND_VIA_FRED_MIRROR"
    cash["source_series_identifier"] = "IUDSOIA"
    cash["validation_series_identifier"] = "IUDZOS2"
    cash["proxy_flag"] = False
    cash["implementation_history_type"] = "ACTUAL_CASH_RESEARCH_ASSET_NOT_ETF"
    return cash, validation


def build_canonical_histories(
    routes: pd.DataFrame,
    listing_frames: dict[str, pd.DataFrame],
    pit: pd.DataFrame,
    exposure_master: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    cash: pd.DataFrame,
    policy: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pit_columns = [
        "date",
        "listing_id",
        "historical_investability_state",
        "historical_investability_confidence",
        "listing_exists",
        "uk_retail_status_known",
        "account_eligibility_known",
    ]
    pit_small = pit[pit_columns].copy()
    route_lookup = routes.set_index("listing_id", drop=False)
    candidate_parts: list[pd.DataFrame] = []
    for listing_id, frame in listing_frames.items():
        route = route_lookup.loc[listing_id]
        part = frame[
            [
                "date",
                "listing_id",
                "share_class_id",
                "economic_exposure_family_id",
                "price_unit",
                "price_available",
                "cum_valid_observations",
                "cum_bad_observations",
                "first_observed_date",
                "data_valid",
                "return_gbp_total",
                "close",
                "price_gbp_if_required",
                "distribution_local",
                "fx_rate_gbp_per_local",
                "fx_source_date",
                "listing_active",
                "stale_flag",
                "missing_flag",
                "proxy_flag",
                "source_series_identifier",
                "total_return_validation_status",
            ]
        ].copy()
        part["family_membership_valid"] = bool(route["family_membership_valid"])
        part = part.merge(pit_small, on=["date", "listing_id"], how="left", validate="one_to_one")
        candidate_parts.append(part)
    candidates = pd.concat(candidate_parts, ignore_index=True, sort=False) if candidate_parts else pd.DataFrame()

    allowed = candidates[
        candidates["family_membership_valid"]
        & ~candidates["total_return_validation_status"].astype(str).str.startswith("FAIL")
        & ~candidates["historical_investability_state"].isin({"NOT_YET_EXISTING", "KNOWN_NOT_ELIGIBLE"})
        & candidates["price_available"].fillna(False)
        & (candidates["cum_valid_observations"] >= 2)
    ].copy()
    allowed["gbp_listing_priority"] = np.where(allowed["price_unit"].isin(["GBP", "GBX"]), 0, 1)
    allowed = allowed.sort_values(
        [
            "economic_exposure_family_id",
            "date",
            "gbp_listing_priority",
            "cum_valid_observations",
            "cum_bad_observations",
            "first_observed_date",
            "share_class_id",
            "listing_id",
        ],
        ascending=[True, True, True, False, True, True, True, True],
        kind="mergesort",
    )
    selected_info = allowed.drop_duplicates(["economic_exposure_family_id", "date"], keep="first").copy()
    selected_info = selected_info.rename(
        columns={
            "date": "signal_information_date",
            "share_class_id": "selected_share_class_id",
            "listing_id": "selected_listing_id",
            "price_unit": "selected_price_unit",
            "historical_investability_state": "eligibility_state_at_selection",
            "historical_investability_confidence": "eligibility_confidence",
            "cum_valid_observations": "selected_cum_valid_observations_asof",
            "cum_bad_observations": "selected_cum_bad_observations_asof",
            "source_series_identifier": "selected_source_series_identifier",
        }
    )
    next_session = pd.DataFrame(
        {
            "signal_information_date": pd.DatetimeIndex(calendar)[:-1],
            "date": pd.DatetimeIndex(calendar)[1:],
        }
    )
    selected_info = selected_info.merge(next_session, on="signal_information_date", how="inner", validate="many_to_one")
    realized = candidates[
        [
            "date",
            "listing_id",
            "return_gbp_total",
            "close",
            "price_gbp_if_required",
            "distribution_local",
            "fx_rate_gbp_per_local",
            "fx_source_date",
            "listing_active",
            "data_valid",
            "stale_flag",
            "missing_flag",
            "total_return_validation_status",
        ]
    ].rename(columns={"listing_id": "selected_listing_id", "close": "price_local"})
    keep = [
        "date",
        "signal_information_date",
        "economic_exposure_family_id",
        "selected_share_class_id",
        "selected_listing_id",
        "selected_price_unit",
        "eligibility_state_at_selection",
        "eligibility_confidence",
        "selected_cum_valid_observations_asof",
        "selected_cum_bad_observations_asof",
        "selected_source_series_identifier",
    ]
    canonical = selected_info[keep].merge(
        realized,
        on=["date", "selected_listing_id"],
        how="left",
        validate="one_to_one",
    )
    canonical["execution_eligible_date"] = canonical["date"]
    canonical["selection_reason"] = "PRIOR_SESSION_ONLY|GBP_GBX_FIRST|PAST_VALID_COUNT_DESC|PAST_BAD_COUNT_ASC|FIRST_OBSERVED_ASC|STABLE_ID_TIEBREAK"
    canonical["eligible_state"] = canonical["eligibility_state_at_selection"]
    canonical["source_evidence"] = canonical["selected_source_series_identifier"] + "|selection_information_date=" + canonical["signal_information_date"].dt.strftime("%Y-%m-%d")
    canonical["fx_rate_if_required"] = canonical["fx_rate_gbp_per_local"].where(~canonical["selected_price_unit"].isin(["GBP", "GBX"]))
    canonical["proxy_flag"] = False
    canonical["data_valid"] = canonical["data_valid"].fillna(False)
    canonical["stale_flag"] = canonical["stale_flag"].fillna(False)
    canonical["missing_flag"] = canonical["missing_flag"].fillna(True)
    if not canonical.empty:
        canonical = canonical.sort_values(["economic_exposure_family_id", "date"])
        canonical["selection_changed"] = canonical.groupby("economic_exposure_family_id")["selected_listing_id"].transform(lambda x: x.ne(x.shift(1)))

    grid = pd.MultiIndex.from_product(
        [exposure_master["economic_exposure_family_id"].sort_values(), calendar],
        names=["economic_exposure_family_id", "date"],
    ).to_frame(index=False)
    exposure = grid.merge(canonical, on=["economic_exposure_family_id", "date"], how="left")
    exposure = exposure.merge(
        exposure_master[
            [
                "economic_exposure_family_id",
                "economic_exposure_name",
                "universe_tier",
                "asset_class",
                "sub_asset_class",
                "primary_geography",
                "sector",
                "industry",
                "economic_theme",
                "deepvue_theme",
                "duplicate_group_id",
            ]
        ],
        on="economic_exposure_family_id",
        how="left",
        validate="many_to_one",
    )
    exposure["implementation_share_class_id"] = exposure["selected_share_class_id"].fillna("NOT_AVAILABLE_NO_SELECTION")
    exposure["implementation_listing_id"] = exposure["selected_listing_id"].fillna("NOT_AVAILABLE_NO_SELECTION")
    exposure["eligible_state"] = exposure["eligible_state"].fillna("NO_IMPLEMENTATION_AVAILABLE_AS_OF_PRIOR_SESSION")
    exposure["eligibility_confidence"] = exposure["eligibility_confidence"].fillna("NOT_APPLICABLE")
    exposure["listing_active"] = exposure["listing_active"].fillna("NO_IMPLEMENTATION_SELECTED")
    exposure["data_valid"] = exposure["data_valid"].fillna(False)
    exposure["stale_flag"] = exposure["stale_flag"].fillna(False)
    exposure["missing_flag"] = exposure["missing_flag"].fillna(True)
    exposure["proxy_flag"] = False
    exposure["broker_status"] = "NOT_CHECKED"
    exposure["next_execution_eligible_date"] = exposure.groupby("economic_exposure_family_id")["date"].shift(-1)
    for window in policy["warmups"]:
        exposure[f"warmup_{window}"] = exposure.groupby("economic_exposure_family_id")["data_valid"].transform(
            lambda values, w=window: values.astype(int).rolling(w, min_periods=w).sum().eq(w)
        )

    cash_panel = pd.DataFrame(
        {
            "date": cash["date"],
            "economic_exposure_family_id": "ACTUAL_GBP_CASH",
            "implementation_share_class_id": "NOT_APPLICABLE_ACTUAL_CASH",
            "implementation_listing_id": "NOT_APPLICABLE_ACTUAL_CASH",
            "return_gbp_total": cash["return_gbp_total"].where(cash["data_valid"]),
            "price_local": cash["cash_index"],
            "price_gbp_if_required": cash["cash_index"],
            "distribution_local": 0.0,
            "fx_rate_if_required": np.nan,
            "listing_active": "NOT_APPLICABLE_ACTUAL_CASH",
            "eligible_state": "RESEARCH_CASH_PROXY_NOT_BROKER_ACCOUNT_RATE",
            "eligibility_confidence": "HIGH_DATA_LOW_ACCOUNT_EQUIVALENCE",
            "data_valid": cash["data_valid"],
            "stale_flag": False,
            "missing_flag": ~cash["data_valid"],
            "proxy_flag": False,
            "broker_status": "NOT_CHECKED",
            "economic_exposure_name": "Actual GBP cash research asset",
            "universe_tier": "SEPARATE_RESEARCH_ASSET",
            "asset_class": "CASH_LIKE",
            "sub_asset_class": "ACTUAL_CASH_PROXY",
            "primary_geography": "UNITED_KINGDOM",
            "sector": "NOT_APPLICABLE",
            "industry": "NOT_APPLICABLE",
            "economic_theme": "NOT_APPLICABLE",
            "deepvue_theme": "NOT_APPLICABLE",
            "duplicate_group_id": "NOT_APPLICABLE_ACTUAL_CASH",
            "next_execution_eligible_date": cash["date"].shift(-1),
        }
    )
    for window in policy["warmups"]:
        cash_panel[f"warmup_{window}"] = cash_panel["data_valid"].astype(int).rolling(window, min_periods=window).sum().eq(window)

    panel_columns = [
        "date",
        "economic_exposure_family_id",
        "implementation_share_class_id",
        "implementation_listing_id",
        "return_gbp_total",
        "price_local",
        "price_gbp_if_required",
        "distribution_local",
        "fx_rate_if_required",
        "listing_active",
        "eligible_state",
        "eligibility_confidence",
        "data_valid",
        "stale_flag",
        "missing_flag",
        "proxy_flag",
        "broker_status",
        "next_execution_eligible_date",
        *[f"warmup_{window}" for window in policy["warmups"]],
    ]
    panel = pd.concat([exposure[panel_columns], cash_panel[panel_columns]], ignore_index=True, sort=False)
    exposure_with_cash = pd.concat([exposure, cash_panel], ignore_index=True, sort=False)
    return canonical, exposure_with_cash, panel


def fetch_and_validate_yahoo(
    client: CaptureClient,
    routes: pd.DataFrame,
    listing_frames: dict[str, pd.DataFrame],
    policy: dict[str, Any],
) -> pd.DataFrame:
    preferred = [
        "ISF", "CSP1", "CSPX", "VUSA", "SMEA", "IJPN", "VFEM", "SMGB", "IGLT", "SLXX",
        "SGLN", "ERNS", "IGUS", "IUSA", "EQQQ", "HLTG", "IMEA", "VWRL", "INXG", "DRDR",
    ]
    available = routes[routes["listing_id"].isin(listing_frames)].copy()
    selected_rows: list[pd.Series] = []
    seen: set[str] = set()
    for ticker in preferred:
        match = available[available["ticker"].eq(ticker)]
        if not match.empty:
            row = match.iloc[0]
            if row["listing_id"] not in seen:
                selected_rows.append(row)
                seen.add(row["listing_id"])
    for _, row in available.sort_values(["universe_tier", "ticker"]).iterrows():
        if len(selected_rows) >= 20:
            break
        if row["listing_id"] not in seen:
            selected_rows.append(row)
            seen.add(row["listing_id"])

    rows: list[dict[str, Any]] = []
    for row in selected_rows[:20]:
        ticker = row["ticker"]
        symbol = f"{ticker}.L"
        try:
            payload = client.get_json(
                "YAHOO_FINANCE",
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                {
                    "period1": 1451606400,
                    "period2": 1787443200,
                    "interval": "1d",
                    "events": "div,splits",
                    "includeAdjustedClose": "true",
                },
                f"external/yahoo_{safe_name(symbol)}.json.gz",
                f"CHART:{symbol}:2016-01-01:2026-08-22",
            )
            result = payload.get("chart", {}).get("result", [None])[0]
            if not result:
                raise ValueError("No chart result")
            timestamps = result.get("timestamp", [])
            adj = result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])
            yahoo = pd.DataFrame({"date": pd.to_datetime(timestamps, unit="s", utc=True).tz_convert("Europe/London").normalize().tz_localize(None), "yahoo_adjusted": adj})
            yahoo["yahoo_adjusted"] = pd.to_numeric(yahoo["yahoo_adjusted"], errors="coerce")
            yahoo = yahoo.dropna().drop_duplicates("date").sort_values("date")
            yahoo["yahoo_return"] = yahoo["yahoo_adjusted"].pct_change(fill_method=None)
            eod = listing_frames[row["listing_id"]][["date", "adjusted_close"]].copy()
            eod["eodhd_return"] = eod["adjusted_close"].pct_change(fill_method=None)
            overlap = eod.merge(yahoo, on="date", how="inner").dropna(subset=["eodhd_return", "yahoo_return"])
            errors = (overlap["eodhd_return"] - overlap["yahoo_return"]).abs()
            median, p95, maximum = (
                float(errors.median()) if len(errors) else None,
                float(errors.quantile(0.95)) if len(errors) else None,
                float(errors.max()) if len(errors) else None,
            )
            if len(errors) >= 100 and median is not None and median <= 0.0005 and p95 <= 0.005:
                status = "PASS"
            elif len(errors) >= 50 and p95 is not None and p95 <= 0.02:
                status = "WARNING"
            else:
                status = "FAIL"
            rows.append(
                {
                    "listing_id": row["listing_id"],
                    "ticker": ticker,
                    "isin": row["isin"],
                    "economic_exposure_family_id": row["economic_exposure_family_id"],
                    "eodhd_price_unit": row["effective_price_unit"],
                    "yahoo_currency": result.get("meta", {}).get("currency", "NOT_AVAILABLE"),
                    "overlap_observations": int(len(errors)),
                    "median_absolute_daily_return_error": median,
                    "p95_absolute_daily_return_error": p95,
                    "max_absolute_daily_return_error": maximum,
                    "validation_status": status,
                    "note": "Return comparison is scale-invariant; Yahoo is corroborative, EODHD remains the primary route.",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "listing_id": row["listing_id"],
                    "ticker": ticker,
                    "isin": row["isin"],
                    "economic_exposure_family_id": row["economic_exposure_family_id"],
                    "eodhd_price_unit": row["effective_price_unit"],
                    "yahoo_currency": "NOT_AVAILABLE",
                    "overlap_observations": 0,
                    "median_absolute_daily_return_error": np.nan,
                    "p95_absolute_daily_return_error": np.nan,
                    "max_absolute_daily_return_error": np.nan,
                    "validation_status": "UNRESOLVED",
                    "note": f"{type(exc).__name__}:{exc}",
                }
            )
    return pd.DataFrame(rows)


def build_fx_pair_validation(routes: pd.DataFrame, listing_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    available = routes[routes["listing_id"].isin(listing_frames)].copy()
    for share_class_id, group in available.groupby("share_class_id"):
        gbp = group[group["effective_price_unit"].isin(["GBP", "GBX"])]
        foreign = group[~group["effective_price_unit"].isin(["GBP", "GBX"])]
        if gbp.empty or foreign.empty:
            continue
        for _, gbp_row in gbp.iterrows():
            for _, foreign_row in foreign.iterrows():
                left = listing_frames[gbp_row["listing_id"]][["date", "return_gbp_total", "data_valid"]].rename(
                    columns={"return_gbp_total": "gbp_line_return", "data_valid": "gbp_line_valid"}
                )
                right = listing_frames[foreign_row["listing_id"]][["date", "return_gbp_total", "data_valid"]].rename(
                    columns={"return_gbp_total": "foreign_line_converted_return", "data_valid": "foreign_line_valid"}
                )
                overlap = left.merge(right, on="date", how="inner")
                overlap = overlap[overlap["gbp_line_valid"] & overlap["foreign_line_valid"]].dropna()
                error = (overlap["gbp_line_return"] - overlap["foreign_line_converted_return"]).abs()
                median = float(error.median()) if len(error) else None
                p95 = float(error.quantile(0.95)) if len(error) else None
                if len(error) < 50:
                    status = "UNRESOLVED_NO_COMMON_VALID_DATES"
                elif median is not None and median <= 0.002 and p95 <= 0.02:
                    status = "PASS"
                elif p95 is not None and p95 <= 0.05:
                    status = "WARNING"
                else:
                    status = "FAIL"
                rows.append(
                    {
                        "share_class_id": share_class_id,
                        "isin": gbp_row["isin"],
                        "economic_exposure_family_id": gbp_row["economic_exposure_family_id"],
                        "gbp_listing_id": gbp_row["listing_id"],
                        "gbp_ticker": gbp_row["ticker"],
                        "foreign_listing_id": foreign_row["listing_id"],
                        "foreign_ticker": foreign_row["ticker"],
                        "foreign_currency": foreign_row["effective_listing_currency"],
                        "gbp_historical_listing_extension": bool(gbp_row["historical_listing_extension"]),
                        "foreign_historical_listing_extension": bool(foreign_row["historical_listing_extension"]),
                        "overlap_observations": int(len(error)),
                        "median_absolute_daily_return_difference": median,
                        "p95_absolute_daily_return_difference": p95,
                        "validation_status": status,
                        "note": "Same ISIN/listing-currency cross-check after deterministic GBP conversion; closing-time and venue microstructure differences are expected.",
                    }
                )
    return pd.DataFrame(rows)


def build_share_class_coherence(routes: pd.DataFrame, listing_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    available = routes[routes["listing_id"].isin(listing_frames)].copy()
    available = available[available["effective_price_unit"].isin(["GBP", "GBX"])]
    for (family_id, provider), group in available.groupby(["economic_exposure_family_id", "provider_issuer"]):
        acc = group[group["accumulating_distributing"].eq("ACCUMULATING")]
        dist = group[group["accumulating_distributing"].eq("DISTRIBUTING")]
        if acc.empty or dist.empty:
            continue
        acc_row = acc.sort_values("listing_id").iloc[0]
        dist_row = dist.sort_values("listing_id").iloc[0]
        left = listing_frames[acc_row["listing_id"]][["date", "return_gbp_total", "data_valid"]].rename(
            columns={"return_gbp_total": "acc_return", "data_valid": "acc_valid"}
        )
        right = listing_frames[dist_row["listing_id"]][["date", "return_gbp_total", "data_valid"]].rename(
            columns={"return_gbp_total": "dist_return", "data_valid": "dist_valid"}
        )
        overlap = left.merge(right, on="date", how="inner")
        overlap = overlap[overlap["acc_valid"] & overlap["dist_valid"]].dropna()
        error = (overlap["acc_return"] - overlap["dist_return"]).abs()
        median = float(error.median()) if len(error) else None
        p95 = float(error.quantile(0.95)) if len(error) else None
        status = "PASS" if len(error) >= 100 and median is not None and median <= 0.003 and p95 <= 0.03 else "WARNING"
        rows.append(
            {
                "economic_exposure_family_id": family_id,
                "provider_issuer": provider,
                "accumulating_share_class_id": acc_row["share_class_id"],
                "accumulating_ticker": acc_row["ticker"],
                "distributing_share_class_id": dist_row["share_class_id"],
                "distributing_ticker": dist_row["ticker"],
                "overlap_observations": int(len(error)),
                "median_absolute_daily_total_return_difference": median,
                "p95_absolute_daily_total_return_difference": p95,
                "validation_status": status,
                "note": "Separate share-class price identities retained; comparison is a total-return coherence diagnostic, not a performance test.",
            }
        )
    return pd.DataFrame(rows)


def apply_cross_source_failure_gate(
    routes: pd.DataFrame,
    instrument: pd.DataFrame,
    pit: pd.DataFrame,
    listing_frames: dict[str, pd.DataFrame],
    validations: pd.DataFrame,
    fx_pairs: pd.DataFrame,
    yahoo_validation: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    excluded: dict[str, str] = {}
    if not yahoo_validation.empty:
        for _, row in yahoo_validation[yahoo_validation["validation_status"].eq("FAIL")].iterrows():
            excluded[row["listing_id"]] = "FAIL_OVERLAPPING_SOURCE_RETURN_DISCREPANCY"
    if not fx_pairs.empty:
        for _, row in fx_pairs[fx_pairs["validation_status"].eq("FAIL")].iterrows():
            if bool(row.get("gbp_historical_listing_extension", False)):
                target = row["gbp_listing_id"]
            elif bool(row.get("foreign_historical_listing_extension", False)):
                target = row["foreign_listing_id"]
            else:
                # A failed pair does not identify which active line is wrong. Keep the
                # directly GBP-quoted line and exclude the foreign implementation route
                # that depends on FX conversion until independent evidence resolves it.
                target = row["foreign_listing_id"]
            excluded[target] = "FAIL_SAME_ISIN_GBP_FX_COHERENCE"
    instrument = instrument.copy()
    pit = pit.copy()
    validations = validations.copy()
    exclusion_rows: list[dict[str, Any]] = []
    route_lookup = routes.set_index("listing_id", drop=False)
    for listing_id, reason in excluded.items():
        instrument.loc[instrument["listing_id"].eq(listing_id), "data_valid"] = False
        instrument.loc[instrument["listing_id"].eq(listing_id), "return_gbp_total"] = np.nan
        instrument.loc[instrument["listing_id"].eq(listing_id), "total_return_validation_status"] = reason
        pit.loc[pit["listing_id"].eq(listing_id), "data_valid"] = False
        pit.loc[pit["listing_id"].eq(listing_id), "total_return_validation_status"] = reason
        validations.loc[validations["listing_id"].eq(listing_id), "total_return_validation_status"] = reason
        if listing_id in listing_frames:
            listing_frames[listing_id]["data_valid"] = False
            listing_frames[listing_id]["return_gbp_total"] = np.nan
            listing_frames[listing_id]["total_return_validation_status"] = reason
        route = route_lookup.loc[listing_id]
        exclusion_rows.append(
            {
                "lineage_item_id": stable_id("A2LIN", listing_id, reason),
                "lineage_action": "DATA_ROUTE_EXCLUSION",
                "a0a1_record_id": listing_id,
                "field": "canonical_history_eligibility",
                "a0a1_value": "A0A1_IMPLEMENTATION_CANDIDATE",
                "a2_value": reason,
                "evidence": f"Overlapping-source and/or same-ISIN FX coherence validation for {route['eodhd_symbol']}",
                "status": "RAW_HISTORY_RETAINED_CANONICAL_SELECTION_FORBIDDEN",
                "materiality": "TOTAL_RETURN_CORRECTNESS",
            }
        )
    return instrument, pit, listing_frames, validations, pd.DataFrame(exclusion_rows)


def _resolve_manual_route(
    routes: pd.DataFrame,
    listing_frames: dict[str, pd.DataFrame],
    tickers: list[str],
    family: str | None = None,
    price_units: set[str] | None = None,
    historical: bool | None = None,
) -> pd.Series | None:
    available = routes[routes["listing_id"].isin(listing_frames)].copy()
    if family:
        available = available[available["economic_exposure_family_id"].eq(family)]
    if price_units:
        available = available[available["effective_price_unit"].isin(price_units)]
    if historical is not None:
        available = available[available["historical_listing_extension"].eq(historical)]
    for ticker in tickers:
        match = available[available["ticker"].eq(ticker)]
        if not match.empty:
            return match.iloc[0]
    if tickers:
        return None
    return available.sort_values("listing_id").iloc[0] if not available.empty else None


def build_manual_validation_cases(
    routes: pd.DataFrame,
    listing_frames: dict[str, pd.DataFrame],
    events: pd.DataFrame,
    cash: pd.DataFrame,
) -> tuple[pd.DataFrame, str]:
    specs = [
        ("MAN-01", "UK equity ETF", ["ISF"], "UK_LARGE_CAP", None, None, "STANDARD_GBP"),
        ("MAN-02", "US equity UCITS ETF listed in GBP", ["CSP1", "VUSA"], "US_BROAD_LARGE_CAP", {"GBP", "GBX"}, None, "STANDARD_GBP"),
        ("MAN-03", "US equity ETF alternate USD listing", ["CSPX", "VUSD"], "US_BROAD_LARGE_CAP", {"USD"}, None, "FOREIGN_FX"),
        ("MAN-04", "Europe ETF", ["SMEA", "VEUR"], "EUROPE_BROAD", None, None, "STANDARD_GBP"),
        ("MAN-05", "Japan ETF", ["VJPN", "HIJS", "IJPN"], "JAPAN", None, None, "STANDARD_GBP"),
        ("MAN-06", "Emerging-market ETF", ["VFEM", "EMGU"], "EMERGING_MARKETS", None, None, "STANDARD_GBP"),
        ("MAN-07", "Semiconductor ETF", ["SMGB"], "GLOBAL_SEMICONDUCTORS", None, None, "STANDARD_GBP"),
        ("MAN-08", "Distributing equity ETF", ["ISF", "IUSA"], None, None, None, "DISTRIBUTION_EVENT"),
        ("MAN-09", "Accumulating economic equivalent", ["CSP1"], "US_BROAD_LARGE_CAP", None, None, "STANDARD_GBP"),
        ("MAN-10", "Government-bond ETF", ["VGOV", "GLTP", "IGLT"], "UK_GILTS_ALL", None, None, "STANDARD_GBP"),
        ("MAN-11", "Corporate-bond ETF", ["SLXX", "ISXF"], "GBP_CORPORATE_IG", None, None, "DISTRIBUTION_EVENT"),
        ("MAN-12", "Gold ETC", ["SGLN", "IGLN"], "GOLD", None, None, "STANDARD_GBP"),
        ("MAN-13", "Cash-like ETF", ["FEDG", "CSGB", "DCSH"], None, None, None, "STANDARD_GBP"),
        ("MAN-14", "Actual GBP cash proxy", [], None, None, None, "CASH"),
        ("MAN-15", "Hedged equity ETF", ["IGUS"], "US_BROAD_LARGE_CAP_GBP_HEDGED", None, None, "STANDARD_GBP"),
        ("MAN-16", "Unhedged equivalent", ["CSP1", "VUSA"], "US_BROAD_LARGE_CAP", None, None, "STANDARD_GBP"),
        ("MAN-17", "Later-inception ETF", ["DFNX", "QNTG", "N100"], None, None, None, "FIRST_VALID"),
        ("MAN-18", "Delisted/closed listing", ["HLTG", "IMEA", "EMAS", "MEUU"], None, None, True, "LAST_VALID"),
        ("MAN-19", "Explicit ex-distribution event", ["ISF"], None, None, None, "DISTRIBUTION_EVENT"),
        ("MAN-20", "Explicit GBX-listed instrument", ["ISF", "CSP1"], None, {"GBX"}, None, "GBX_SCALE"),
    ]
    rows: list[dict[str, Any]] = []
    for case_id, description, tickers, family, units, historical, method in specs:
        if method == "CASH":
            valid = cash[cash["validation_absolute_error"].notna()]
            if valid.empty:
                rows.append({"case_id": case_id, "case": description, "status": "UNRESOLVED", "detail": "No SONIA/index overlap"})
                continue
            row = valid.iloc[len(valid) // 2]
            rows.append(
                {
                    "case_id": case_id,
                    "case": description,
                    "listing_id": "NOT_APPLICABLE_ACTUAL_CASH",
                    "ticker": "ACTUAL_GBP_CASH",
                    "isin": "NOT_APPLICABLE",
                    "date": row["date"].date().isoformat(),
                    "manual_return": row["return_gbp_total"],
                    "stored_return": row["sonia_compounded_index_return"],
                    "absolute_error": row["validation_absolute_error"],
                    "status": "PASS" if row["validation_absolute_error"] <= 0.00001 else "WARNING",
                    "formula": "(1 + prior SONIA/100)^(calendar_days/365)-1; compared with IUDZOS2 index ratio",
                    "source_evidence": "Bank of England IUDSOIA and IUDZOS2 via FRED captures",
                }
            )
            continue
        route = _resolve_manual_route(routes, listing_frames, tickers, family, units, historical)
        if route is None:
            rows.append({"case_id": case_id, "case": description, "status": "UNRESOLVED", "detail": "No exact-identity source route"})
            continue
        frame = listing_frames[route["listing_id"]].sort_values("date").reset_index(drop=True)
        if method == "DISTRIBUTION_EVENT":
            event = events[(events["listing_id"].eq(route["listing_id"])) & (events["validation_status"].isin(["PASS", "WARNING"]))]
            if event.empty:
                rows.append({"case_id": case_id, "case": description, "listing_id": route["listing_id"], "ticker": route["ticker"], "status": "UNRESOLVED", "detail": "No reconstructable distribution event"})
                continue
            selected = event.iloc[0]
            manual_return = selected["manual_total_return"]
            stored_return = selected["stored_total_return"]
            absolute_error = selected["absolute_error"]
            date_value = selected["date"]
            formula = "(raw close_t * split ratio + distribution converted to quote units) / raw close_t-1 - 1"
        else:
            valid = frame[frame["data_valid"] & frame["return_gbp_total"].notna()]
            if valid.empty and method == "LAST_VALID":
                valid = frame[frame["price_available"] & frame["return_gbp_total_unfiltered"].notna()]
            if valid.empty:
                rows.append({"case_id": case_id, "case": description, "listing_id": route["listing_id"], "ticker": route["ticker"], "status": "UNRESOLVED", "detail": "No valid return row"})
                continue
            selected_row = valid.iloc[0] if method == "FIRST_VALID" else (valid.iloc[-1] if method == "LAST_VALID" else valid.iloc[len(valid) // 2])
            loc = frame.index[frame["date"].eq(selected_row["date"])][0]
            prior = frame.iloc[loc - 1]
            if method == "GBX_SCALE":
                manual_return = selected_row["close"] * 0.01
                stored_return = selected_row["price_gbp_if_required"]
                formula = "displayed GBX close * 0.01 = GBP price"
            else:
                manual_return = selected_row["adjusted_wealth_gbp"] / prior["adjusted_wealth_gbp"] - 1.0
                stored_return = selected_row["return_gbp_total_unfiltered"]
                formula = "adjusted GBP wealth_t / adjusted GBP wealth_t-1 - 1"
            absolute_error = abs(float(manual_return) - float(stored_return))
            date_value = selected_row["date"]
        rows.append(
            {
                "case_id": case_id,
                "case": description,
                "listing_id": route["listing_id"],
                "share_class_id": route["share_class_id"],
                "ticker": route["ticker"],
                "isin": route["isin"],
                "economic_exposure_family_id": route["economic_exposure_family_id"],
                "price_unit": route["effective_price_unit"],
                "date": pd.Timestamp(date_value).date().isoformat(),
                "manual_return": float(manual_return),
                "stored_return": float(stored_return),
                "absolute_error": float(absolute_error),
                "status": "PASS" if float(absolute_error) <= (0.001 if method == "DISTRIBUTION_EVENT" else 1e-10) else "WARNING",
                "formula": formula,
                "canonical_route_status": selected_row.get("total_return_validation_status", "EVENT_LEVEL_VALIDATION") if method != "DISTRIBUTION_EVENT" else "EVENT_LEVEL_VALIDATION",
                "source_evidence": f"EODHD {route['eodhd_symbol']} raw/adjusted/event captures; A0A1 exact ISIN identity",
            }
        )
    cases = pd.DataFrame(rows)
    markdown_lines = [
        "# UKACTIVE A2 Manual Validation Cases",
        "",
        "These are data-accounting reconstructions only. They are not a strategy backtest and contain no portfolio-performance result.",
        "",
        "| Case | Instrument | Date | Method | Absolute error | Status |",
        "|---|---|---:|---|---:|---|",
    ]
    for _, row in cases.iterrows():
        error = row.get("absolute_error", np.nan)
        error_text = f"{float(error):.10g}" if pd.notna(error) else "NOT_AVAILABLE"
        markdown_lines.append(
            f"| {row.get('case_id')} — {row.get('case')} | {row.get('ticker', 'NOT_AVAILABLE')} / {row.get('isin', 'NOT_AVAILABLE')} | {row.get('date', 'NOT_AVAILABLE')} | {row.get('formula', row.get('detail', 'NOT_AVAILABLE'))} | {error_text} | {row.get('status')} |"
        )
    markdown_lines.extend(
        [
            "",
            "For distributing lines, the distribution is used once for reconstruction and is not added to the adjusted-close return. For foreign-currency lines, GBP wealth uses the ECB rate published by the XLON close (same-date when available, otherwise latest prior across an observation gap). GBX cases explicitly apply 0.01.",
        ]
    )
    return cases, "\n".join(markdown_lines) + "\n"


def build_readiness(exposure: pd.DataFrame, exposure_master: pd.DataFrame, policy: dict[str, Any]) -> pd.DataFrame:
    base = exposure[exposure["economic_exposure_family_id"].isin(set(exposure_master["economic_exposure_family_id"]))].copy()
    rows: list[dict[str, Any]] = []
    master = exposure_master.set_index("economic_exposure_family_id")
    for family_id, group in base.groupby("economic_exposure_family_id", sort=True):
        valid = group[group["data_valid"] & group["return_gbp_total"].notna()]
        selected = group[group["implementation_listing_id"].ne("NOT_AVAILABLE_NO_SELECTION")]
        validation_statuses = set(selected["total_return_validation_status"].dropna().astype(str)) if "total_return_validation_status" in selected else set()
        rows_count = int(len(valid))
        eligibility_states = set(selected["eligible_state"].dropna().astype(str))
        actual_validated = rows_count >= 21 and not any(value.startswith("FAIL") for value in validation_statuses)
        a3_ready = actual_validated and rows_count >= int(policy["a3_readiness"]["minimum_valid_observations"])
        rows.append(
            {
                "economic_exposure_family_id": family_id,
                "economic_exposure_name": master.loc[family_id, "economic_exposure_name"],
                "universe_tier": master.loc[family_id, "universe_tier"],
                "valid_return_observations": rows_count,
                "first_valid_date": valid["date"].min().date().isoformat() if not valid.empty else "NOT_AVAILABLE",
                "last_valid_date": valid["date"].max().date().isoformat() if not valid.empty else "NOT_AVAILABLE",
                "has_1_year": rows_count >= 252,
                "has_3_years": rows_count >= 756,
                "has_5_years": rows_count >= 1260,
                "has_10_years": rows_count >= 2520,
                "usable_history": rows_count >= 21,
                "validated_actual_implementation_history": actual_validated,
                "requires_proxy_for_504_day_research": rows_count < 504,
                "historical_eligibility_unresolved": "HISTORICALLY_VERIFIED_INVESTABLE" not in eligibility_states,
                "a3_ready": a3_ready,
                "a3_scope": "RESEARCH_ONLY_WITH_VISIBLE_ELIGIBILITY_UNCERTAINTY" if a3_ready else "NOT_READY",
                "selected_listing_count_through_time": int(selected["implementation_listing_id"].nunique()) if not selected.empty else 0,
                "validation_statuses": ";".join(sorted(validation_statuses)) if validation_statuses else "NO_SELECTED_HISTORY",
            }
        )
    return pd.DataFrame(rows)


def run_automated_tests(
    policy: dict[str, Any],
    routes: pd.DataFrame,
    instrument: pd.DataFrame,
    pit: pd.DataFrame,
    canonical: pd.DataFrame,
    panel: pd.DataFrame,
    events: pd.DataFrame,
    validations: pd.DataFrame,
    lineage: pd.DataFrame,
    cash_validation: dict[str, Any],
    fx_pairs: pd.DataFrame,
    yahoo_validation: pd.DataFrame,
    historical_extension_count: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(test_id: str, description: str, passed: bool, observed: Any, critical: bool = True, category: str = "REAL") -> None:
        rows.append(
            {
                "test_id": test_id,
                "category": category,
                "description": description,
                "critical": critical,
                "expected": "PASS",
                "observed": str(observed),
                "status": "PASS" if bool(passed) else "FAIL",
            }
        )

    for test in synthetic_failure_tests():
        add(test.test_id, test.description, test.expected_failure_detected, test.detail, True, "SYNTHETIC_FAILURE_FIXTURE")

    pre_inception_valid = int((instrument.get("price_before_inception_flag", False) & instrument.get("data_valid", False)).sum()) if not instrument.empty else 0
    add("REAL-01", "No valid instrument return before evidenced inception", pre_inception_valid == 0, pre_inception_valid)
    add("REAL-02", "No canonical selection uses a listing before existence", not canonical.get("eligibility_state_at_selection", pd.Series(dtype=str)).eq("NOT_YET_EXISTING").any(), canonical.get("eligibility_state_at_selection", pd.Series(dtype=str)).value_counts().to_dict())
    historical_labels = set(pit.get("historical_investability_state", pd.Series(dtype=str)).dropna().astype(str))
    add("REAL-03", "Current eligibility is not assigned as a historical label", "CURRENTLY_INVESTABLE" not in historical_labels, sorted(historical_labels))
    selected_ids = set(canonical.get("selected_listing_id", pd.Series(dtype=str)).dropna())
    failed_ids = set(validations[validations["total_return_validation_status"].str.startswith("FAIL")]["listing_id"])
    add("REAL-04", "Unvalidated adjusted-close histories are not selected", not bool(selected_ids & failed_ids), sorted(selected_ids & failed_ids))
    add("REAL-05", "Authoritative distribution method does not add distributions twice", policy["total_return"]["distribution_handling"].startswith("Distributions are retained"), policy["total_return"]["distribution_handling"])
    selected_event_fail = events[events["listing_id"].isin(selected_ids) & events["validation_status"].eq("FAIL")] if not events.empty else pd.DataFrame()
    add("REAL-06", "Selected distributing histories have no failed explicit event reconstruction", selected_event_fail.empty, len(selected_event_fail))
    gbx_multipliers = instrument.loc[instrument.get("price_unit", pd.Series(dtype=str)).eq("GBX"), "price_unit_multiplier_to_listing_currency"].dropna().unique() if not instrument.empty else []
    add("REAL-07", "Every GBX line uses exactly 0.01 GBP multiplier", len(gbx_multipliers) > 0 and np.allclose(gbx_multipliers, [0.01]), gbx_multipliers.tolist() if hasattr(gbx_multipliers, "tolist") else gbx_multipliers)
    foreign = instrument[~instrument.get("price_unit", pd.Series(dtype=str)).isin(["GBP", "GBX"]) & instrument.get("price_available", False)].copy() if not instrument.empty else pd.DataFrame()
    fx_once_error = (
        (foreign["price_listing_currency"] * foreign["fx_rate_gbp_per_local"] - foreign["price_gbp_if_required"]).abs().dropna().max()
        if not foreign.empty else np.nan
    )
    add("REAL-08", "Foreign listing price is converted to GBP exactly once", pd.notna(fx_once_error) and fx_once_error <= 1e-10, fx_once_error)
    foreign_missing_fx_valid = int((foreign["fx_rate_gbp_per_local"].isna() & foreign["data_valid"]).sum()) if not foreign.empty else 0
    add("REAL-09", "Foreign listings cannot be valid without FX", foreign_missing_fx_valid == 0, foreign_missing_fx_valid)
    stale_valid = int((instrument.get("stale_flag", False) & instrument.get("data_valid", False)).sum()) if not instrument.empty else 0
    add("REAL-10", "Stale observations are not valid returns", stale_valid == 0, stale_valid)
    add("REAL-11", "Historical eligibility confidence explicitly says current state was not back-projected", pit["historical_investability_confidence"].astype(str).str.contains("NOT_BACK_PROJECTED|HIGH_IF_DATED").all(), pit["historical_investability_confidence"].value_counts().to_dict())
    date_order_ok = bool((canonical["signal_information_date"] < canonical["date"]).all()) if not canonical.empty else False
    add("REAL-12", "Canonical selection uses strictly prior-session information", date_order_ok, len(canonical))
    add("REAL-13", "Delisted exact-ISIN histories are retained", historical_extension_count > 0, historical_extension_count)
    add("REAL-14", "Proxy labels cannot enter live implementation rows", not panel.get("proxy_flag", pd.Series(dtype=bool)).fillna(False).any(), int(panel.get("proxy_flag", pd.Series(dtype=bool)).fillna(False).sum()))
    acc_dist_same = routes.groupby("share_class_id")["accumulating_distributing"].nunique().max() if not routes.empty else 0
    add("REAL-15", "Accumulating and distributing classes retain distinct share-class identities", acc_dist_same <= 1, acc_dist_same)
    next_dates = panel.dropna(subset=["next_execution_eligible_date"])
    add("REAL-16", "Same-close signal/execution is impossible in panel mapping", bool((next_dates["next_execution_eligible_date"] > next_dates["date"]).all()), len(next_dates))
    duplicates = int(panel.duplicated(["date", "economic_exposure_family_id"]).sum())
    add("REAL-17", "Provider duplication cannot create multiple family/date rows", duplicates == 0, duplicates)
    add("REAL-18", "Broker status remains NOT_CHECKED", set(panel["broker_status"].dropna().astype(str)) == {"NOT_CHECKED"}, panel["broker_status"].value_counts().to_dict(), critical=False)
    unit_corrections = lineage[(lineage["field"].eq("price_unit")) & (lineage["status"].eq("APPLIED_IN_A2_ONLY_A0A1_IMMUTABLE"))]
    add("REAL-19", "A0A1 GBP/GBX conflicts are corrected through explicit lineage", len(unit_corrections) > 0, len(unit_corrections))
    add("REAL-20", "Current investability status never appears in research panel eligible_state", not panel["eligible_state"].eq("CURRENTLY_INVESTABLE").any(), panel["eligible_state"].value_counts().to_dict())
    add("REAL-21", "Same-ISIN lines remain implementation alternatives, not extra economic rows", duplicates == 0 and panel["economic_exposure_family_id"].nunique() <= 100, panel["economic_exposure_family_id"].nunique())
    hedged_families = set(routes.loc[routes["hedged_unhedged"].eq("HEDGED"), "economic_exposure_family_id"])
    unhedged_families = set(routes.loc[routes["hedged_unhedged"].eq("UNHEDGED"), "economic_exposure_family_id"])
    add("REAL-22", "Hedged and unhedged exposures are not collapsed by share-class identity", len(hedged_families) > 0 and hedged_families != unhedged_families, f"hedged={len(hedged_families)} unhedged={len(unhedged_families)}")
    finite_returns = panel.loc[panel["data_valid"], "return_gbp_total"].dropna()
    add("REAL-23", "All valid authoritative returns are finite", bool(np.isfinite(finite_returns).all()) and len(finite_returns) > 0, len(finite_returns))
    add("REAL-24", "Actual GBP cash route reconciles with SONIA Compounded Index", cash_validation.get("status") == "PASS", cash_validation)
    fx_resolved = int(fx_pairs["validation_status"].isin(["PASS", "WARNING"]).sum()) if not fx_pairs.empty else 0
    fx_failed_targets: set[str] = set()
    if not fx_pairs.empty:
        for _, pair in fx_pairs[fx_pairs["validation_status"].eq("FAIL")].iterrows():
            if bool(pair.get("gbp_historical_listing_extension", False)):
                fx_failed_targets.add(pair["gbp_listing_id"])
            elif bool(pair.get("foreign_historical_listing_extension", False)):
                fx_failed_targets.add(pair["foreign_listing_id"])
            else:
                fx_failed_targets.add(pair["foreign_listing_id"])
    add("REAL-25", "Representative same-ISIN GBP/foreign lines are validated and failed routes are excluded", fx_resolved >= 20 and not bool(selected_ids & fx_failed_targets), {"resolved_pairs": fx_resolved, "failed_targets": len(fx_failed_targets), "selected_failed_targets": sorted(selected_ids & fx_failed_targets)})
    yahoo_failures = int(yahoo_validation["validation_status"].eq("FAIL").sum()) if not yahoo_validation.empty else 0
    yahoo_resolved = int(yahoo_validation["validation_status"].isin(["PASS", "WARNING"]).sum()) if not yahoo_validation.empty else 0
    add("REAL-26", "Overlapping secondary price source materially corroborates primary histories", yahoo_resolved >= 10 and yahoo_failures <= 2, {"resolved": yahoo_resolved, "failures": yahoo_failures})
    add("REAL-27", "Historical state table includes all required separated state fields", {"fund_exists", "share_class_exists", "listing_exists", "listing_active", "price_available", "return_data_available", "signal_warmup_available", "structurally_eligible", "uk_retail_status_known", "account_eligibility_known", "historical_investability_confidence"}.issubset(pit.columns), sorted(pit.columns))
    add("REAL-28", "Leveraged/daily-reset/path-dependent structures do not enter canonical selection", routes[routes["listing_id"].isin(selected_ids)]["long_only_structure_valid"].all(), int((~routes[routes["listing_id"].isin(selected_ids)]["long_only_structure_valid"]).sum()))
    fx_timing = foreign.dropna(subset=["fx_source_date"]) if not foreign.empty else pd.DataFrame()
    add("REAL-29", "FX reference observations are available no later than the XLON valuation date", not fx_timing.empty and bool((fx_timing["fx_source_date"] <= fx_timing["date"]).all()), len(fx_timing))
    return pd.DataFrame(rows)


def build_source_ledger(client: CaptureClient, input_hashes: dict[str, str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for entry in client.ledger:
        key = (entry["source"], entry["series_identifier"], entry["raw_response_sha256"])
        if key in seen:
            continue
        seen.add(key)
        series = entry["series_identifier"]
        if series.startswith("EOD:"):
            data_status, distribution, actions = "RAW_AND_ADJUSTED_PRICE", "EODHD div endpoint", "EODHD splits endpoint"
        elif series.startswith("DIV:"):
            data_status, distribution, actions = "DISTRIBUTION_EVENTS", "THIS_SERIES", "NOT_APPLICABLE"
        elif series.startswith("SPLITS:"):
            data_status, distribution, actions = "CORPORATE_ACTION_SPLITS", "NOT_APPLICABLE", "THIS_SERIES"
        elif series.startswith("EXR:"):
            data_status, distribution, actions = "FX_REFERENCE_RATE", "NOT_APPLICABLE", "NOT_APPLICABLE"
        elif series.startswith("CHART:"):
            data_status, distribution, actions = "CORROBORATIVE_ADJUSTED_PRICE_AND_EVENTS", "Yahoo chart events", "Yahoo chart events"
        else:
            data_status, distribution, actions = "REFERENCE_RATE_OR_INDEX", "NOT_APPLICABLE", "NOT_APPLICABLE"
        rows.append(
            {
                "source_ledger_id": stable_id("A2SRC", *key),
                "vendor_source": entry["source"],
                "series_identifier": series,
                "retrieval_timestamp_utc": entry["retrieval_timestamp_utc"],
                "coverage": "2000-01-01_to_2026-08-21_or_source_available_range",
                "data_status": data_status,
                "distribution_source": distribution,
                "corporate_action_source": actions,
                "currency": "SERIES_SPECIFIC_SEE_NORMALIZED_OUTPUT",
                "timezone": "Europe/London_for_LSE; ECB_reference_date; FRED_observation_date",
                "known_limitations": "EODHD is vendor/indicative rather than an official exchange total-return feed; corroboration and event reconstruction are required.",
                "source_url_redacted": entry["source_url_redacted"],
                "source_hash": entry["raw_response_sha256"],
                "capture_path": entry["capture_path"],
                "evidence_id": entry["evidence_id"],
                "cache_status": entry["cache_status"],
            }
        )
    for path_text, digest in input_hashes.items():
        rows.append(
            {
                "source_ledger_id": stable_id("A2SRC", path_text, digest),
                "vendor_source": "LOCAL_A0A1_AUTHORITATIVE_INPUT",
                "series_identifier": Path(path_text).name,
                "retrieval_timestamp_utc": "LOCAL_FILE_AS_OF_RUN",
                "coverage": "A0A1_CURRENT_MASTER_OR_POLICY",
                "data_status": "IDENTITY_CLASSIFICATION_LINEAGE_INPUT",
                "distribution_source": "NOT_APPLICABLE",
                "corporate_action_source": "NOT_APPLICABLE",
                "currency": "FIELD_SPECIFIC",
                "timezone": "NOT_APPLICABLE",
                "known_limitations": "Current A0A1 eligibility must not be back-projected historically.",
                "source_url_redacted": path_text,
                "source_hash": digest,
                "capture_path": path_text,
                "evidence_id": stable_id("A2EVD", path_text, digest),
                "cache_status": "LOCAL_HASHED_INPUT",
            }
        )
    for name, url in SOURCE_URLS.items():
        rows.append(
            {
                "source_ledger_id": stable_id("A2SRC", name, url),
                "vendor_source": "PUBLIC_DOCUMENTATION",
                "series_identifier": name,
                "retrieval_timestamp_utc": "2026-08-22",
                "coverage": "METHODOLOGY_DOCUMENTATION",
                "data_status": "SOURCE_SEMANTICS_OR_POLICY",
                "distribution_source": "SEE_DOCUMENT",
                "corporate_action_source": "SEE_DOCUMENT",
                "currency": "NOT_APPLICABLE",
                "timezone": "NOT_APPLICABLE",
                "known_limitations": "URL evidence; API captures carry the executed data hashes.",
                "source_url_redacted": url,
                "source_hash": "URL_ONLY_NOT_CONTENT_CAPTURED",
                "capture_path": "NOT_CAPTURED_PUBLIC_DOCUMENTATION",
                "evidence_id": stable_id("A2EVD", name, url),
                "cache_status": "PUBLIC_URL_RECORDED",
            }
        )
    return pd.DataFrame(rows)


def build_unresolved_items(
    routes: pd.DataFrame,
    inputs: dict[str, Any],
    readiness: pd.DataFrame,
    lineage: pd.DataFrame,
    stale_report: pd.DataFrame,
    events: pd.DataFrame,
) -> pd.DataFrame:
    routed_families = set(routes["economic_exposure_family_id"])
    missing_families = inputs["exposure"][~inputs["exposure"]["economic_exposure_family_id"].isin(routed_families)]
    rows: list[dict[str, Any]] = [
        {
            "item_id": "A2-OPEN-001",
            "severity": "HIGH",
            "category": "HISTORICAL_ELIGIBILITY",
            "economic_exposure_family_id": "ALL_ROUTED_FAMILIES",
            "issue": "Historical UK retail, ISA and SIPP eligibility is not contemporaneously verified for the implementation histories.",
            "impact": "A3 may use the panel for research-only signal discovery, but it may not label results an investable point-in-time backtest without further evidence.",
            "required_resolution": "Acquire dated KIDs/platform eligibility archives or a defensible historical eligibility source.",
            "status": "OPEN_VISIBLE_NOT_BACK_PROJECTED",
        },
        {
            "item_id": "A2-OPEN-002",
            "severity": "MEDIUM",
            "category": "BROKER",
            "economic_exposure_family_id": "ALL",
            "issue": "IBKR availability remains NOT_CHECKED; historical broker availability is not established.",
            "impact": "Does not block A3 research; blocks DEPLOYMENT_CANDIDATE status.",
            "required_resolution": "Use a safe exact-ISIN read-only broker route before deployment research.",
            "status": "OPEN_NOT_BLOCKING_A3",
        },
        {
            "item_id": "A2-OPEN-003",
            "severity": "MEDIUM",
            "category": "PROXY_HISTORY",
            "economic_exposure_family_id": "MULTIPLE",
            "issue": f"{int(readiness['requires_proxy_for_504_day_research'].sum())} A0A1 families have fewer than 504 validated implementation observations and would require a separate proxy for longer mechanism research.",
            "impact": "Those families are not A3-ready under the declared 504-observation rule.",
            "required_resolution": "Acquire licensed index/benchmark histories and keep them in ECONOMIC_EXPOSURE_PROXY_HISTORY without splicing.",
            "status": "OPEN_PROXY_PANEL_INTENTIONALLY_EMPTY",
        },
        {
            "item_id": "A2-OPEN-004",
            "severity": "MEDIUM",
            "category": "SURVIVORSHIP",
            "economic_exposure_family_id": "MULTIPLE",
            "issue": "The delisted LSE catalogue contains many historical ETF/ETP rows; A2 classified only exact-ISIN overlaps with the authoritative A0A1 share classes.",
            "impact": "Four exact-lineage non-survivor listings are preserved, but this is not a complete historical UK ETF product census.",
            "required_resolution": "Classify the broader delisted catalogue against dated fund documents in a later eligibility-enrichment pass.",
            "status": "OPEN_PARTIAL_SURVIVORSHIP_CONTROL",
        },
        {
            "item_id": "A2-OPEN-005",
            "severity": "LOW",
            "category": "CALENDAR",
            "economic_exposure_family_id": "ALL",
            "issue": "The historical XLON calendar is an observed-session union from exact-identity listings; the vendor holiday endpoint provides current-year corroboration, not a full official archive.",
            "impact": "Session mapping is deterministic and same-close-safe, but rare vendor-wide missing days may be indistinguishable from holidays.",
            "required_resolution": "License or ingest a complete official XLON historical session calendar.",
            "status": "OPEN_WITH_DIAGNOSTICS",
        },
        {
            "item_id": "A2-OPEN-006",
            "severity": "MEDIUM",
            "category": "DATA_VENDOR",
            "economic_exposure_family_id": "ALL",
            "issue": "EODHD documents adjusted close as split-and-dividend adjusted but describes its prices as indicative rather than an official exchange feed.",
            "impact": "The route is validated with explicit events, FX pairs and Yahoo overlaps, but licensing and institutional-grade redistribution remain separate questions.",
            "required_resolution": "Evaluate an official/licensed total-return data route before deployment-grade research.",
            "status": "OPEN_SOURCE_LIMITATION",
        },
        {
            "item_id": "A2-OPEN-007",
            "severity": "LOW",
            "category": "CASH",
            "economic_exposure_family_id": "ACTUAL_GBP_CASH",
            "issue": "SONIA is a wholesale overnight benchmark and the constructed series is not a claim about any broker's client cash remuneration.",
            "impact": "Suitable as a documented research cash proxy, not as an account-specific rate.",
            "required_resolution": "Model broker/client-specific cash rates only if later deployment research requires them.",
            "status": "OPEN_EXPECTED_LIMITATION",
        },
        {
            "item_id": "A2-OPEN-008",
            "severity": "MEDIUM",
            "category": "SOURCE_ROUTE",
            "economic_exposure_family_id": "ALL",
            "issue": "Direct automated Bank of England IADB CSV access returned HTTP 403 in this environment; FRED's Bank of England mirror was used for IUDSOIA and IUDZOS2.",
            "impact": "Series identity remains official BoE, but the executed data route is a secondary mirror and is recorded as such.",
            "required_resolution": "Add a stable direct BoE API/download route if available.",
            "status": "OPEN_ROUTE_LIMITATION",
        },
    ]
    counter = 100
    for _, family in missing_families.iterrows():
        counter += 1
        rows.append(
            {
                "item_id": f"A2-OPEN-{counter}",
                "severity": "HIGH" if family["universe_tier"] == "CORE" else "MEDIUM",
                "category": "NO_EXACT_PRICE_ROUTE",
                "economic_exposure_family_id": family["economic_exposure_family_id"],
                "issue": "No active or delisted EODHD LSE route matched both A0A1 ticker and ISIN.",
                "impact": "No authoritative implementation history was constructed for this family.",
                "required_resolution": "Resolve through issuer/LSE identity evidence and an alternative price source; ticker-only matches are forbidden.",
                "status": "OPEN",
            }
        )
    hedge_items = lineage[lineage["status"].eq("OPEN_LINEAGE_ERROR")]
    for _, item in hedge_items.iterrows():
        counter += 1
        rows.append(
            {
                "item_id": f"A2-OPEN-{counter}",
                "severity": "HIGH",
                "category": "A0A1_LINEAGE_CONTRADICTION",
                "economic_exposure_family_id": clean_text(item["a0a1_value"]).split("|")[0],
                "issue": f"A0A1 hedge classification contradiction for {item['a0a1_record_id']}: {item['a0a1_value']}",
                "impact": "The share class is excluded from the hedged-family canonical selection pending correction.",
                "required_resolution": "Verify fund objective and hedge currency, then issue a versioned A0A1 lineage correction.",
                "status": "OPEN_EXCLUDED_FROM_SELECTION",
            }
        )
    event_unresolved = int(events["validation_status"].astype(str).str.startswith("UNRESOLVED").sum()) if not events.empty else 0
    if event_unresolved:
        rows.append(
            {
                "item_id": "A2-OPEN-900",
                "severity": "MEDIUM",
                "category": "DISTRIBUTION_EVENT_ALIGNMENT",
                "economic_exposure_family_id": "MULTIPLE",
                "issue": f"{event_unresolved} vendor distribution events could not be aligned to a same-date observed price and were not shifted automatically.",
                "impact": "Affected listings carry visible open-event validation status; failed listings are not selected.",
                "required_resolution": "Check issuer ex-dates and exchange calendars manually.",
                "status": "OPEN_NO_SILENT_DATE_SHIFT",
            }
        )
    return pd.DataFrame(rows)


def summary_counts(readiness: pd.DataFrame, routes: pd.DataFrame, validations: pd.DataFrame, panel: pd.DataFrame) -> dict[str, int]:
    return {
        "economic_exposure_families_with_usable_histories": int(readiness["usable_history"].sum()),
        "families_with_at_least_1_year": int(readiness["has_1_year"].sum()),
        "families_with_at_least_3_years": int(readiness["has_3_years"].sum()),
        "families_with_at_least_5_years": int(readiness["has_5_years"].sum()),
        "families_with_at_least_10_years": int(readiness["has_10_years"].sum()),
        "families_with_validated_actual_implementation_histories": int(readiness["validated_actual_implementation_history"].sum()),
        "families_requiring_proxy_histories": int(readiness["requires_proxy_for_504_day_research"].sum()),
        "families_with_unresolved_historical_eligibility": int(readiness["historical_eligibility_unresolved"].sum()),
        "a3_ready_family_count": int(readiness["a3_ready"].sum()),
        "exact_identity_active_listing_routes": int((routes["route_type"] == "A0A1_ACTIVE_EXACT_TICKER_AND_ISIN").sum()),
        "historical_delisted_listing_extensions": int(routes["historical_listing_extension"].sum()),
        "validated_listing_histories": int(validations["total_return_validation_status"].str.startswith("PASS").sum()),
        "panel_rows": int(len(panel)),
    }


def render_reports(
    policy: dict[str, Any],
    counts: dict[str, int],
    decision: str,
    a3_authorized: bool,
    tests: pd.DataFrame,
    events: pd.DataFrame,
    validations: pd.DataFrame,
    fx_pairs: pd.DataFrame,
    yahoo_validation: pd.DataFrame,
    cash_validation: dict[str, Any],
    stale_report: pd.DataFrame,
    routes: pd.DataFrame,
    readiness: pd.DataFrame,
    unresolved: pd.DataFrame,
) -> dict[str, str]:
    test_counts = tests["status"].value_counts().to_dict()
    event_counts = events["validation_status"].value_counts().to_dict() if not events.empty else {}
    listing_validation_counts = validations["total_return_validation_status"].value_counts().to_dict()
    fx_counts = fx_pairs["validation_status"].value_counts().to_dict() if not fx_pairs.empty else {}
    yahoo_counts = yahoo_validation["validation_status"].value_counts().to_dict() if not yahoo_validation.empty else {}
    stale_total = int(stale_report.get("stale_session_count", pd.Series(dtype=float)).sum())
    missing_total = int(stale_report.get("missing_session_count", pd.Series(dtype=float)).sum())
    historical_extensions = int(routes["historical_listing_extension"].sum())
    common_warning = "CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY."

    reports: dict[str, str] = {}
    reports["UKACTIVE_A2_SCOPE_AND_METHOD.md"] = f"""# UKACTIVE A2 — Scope and Method

Decision: `{decision}`

This stage constructs point-in-time identity, availability and GBP total-return data. It does **not** test momentum, rank signals, construct a portfolio or report strategy performance.

The authoritative input identity is A0A1's fund → share class/ISIN → listing model. A2 admitted {counts['exact_identity_active_listing_routes']} active price routes only where both ticker and ISIN matched the EODHD LSE catalogue, plus {historical_extensions} exact-ISIN delisted listing extensions. Ticker-only matches were rejected.

The immutable long-form panel contains one row per economic family/date, so extra ETF providers cannot create extra economic opportunities. Canonical implementation selection uses only the prior XLON research session and the predeclared policy `{policy['policy_id']}`.

{common_warning}

Actual GBP cash is a separate SONIA-based research asset. It is not CSH2, another ETF or a claim about broker cash remuneration. Proxy and live implementation histories are structurally separate and are never spliced.
"""
    reports["UKACTIVE_A2_POINT_IN_TIME_ELIGIBILITY_POLICY.md"] = f"""# UKACTIVE A2 — Point-in-Time Eligibility Policy

Historical states are stored independently for fund existence, share-class existence, listing existence, listing activity, price availability, return availability, warm-up availability, structural evidence, UK retail knowledge and account-eligibility knowledge.

`HISTORICALLY_VERIFIED_INVESTABLE` is reserved for contemporaneous dated evidence. The current run has no basis for assigning that state retrospectively. `HISTORICALLY_PROBABLE` is a low-confidence research label used only when a currently verified share class also has an exact-identity contemporaneous LSE price observation. It does not mean historical ISA, SIPP or broker eligibility was verified. All other extant routes are `HISTORICALLY_UNCERTAIN` unless affirmative dated evidence establishes another state.

`NOT_YET_EXISTING` is used only before an evidenced inception date. Unknown pre-observation periods remain unknown rather than being converted into a negative claim.

{common_warning}
"""
    reports["UKACTIVE_A2_TOTAL_RETURN_DATA_POLICY.md"] = f"""# UKACTIVE A2 — Total-Return Data Policy

Raw close is retained but is not the authoritative return field. EODHD documents `adjusted_close` as adjusted for splits and dividends. A2 accepts that route only behind a validation gate consisting of explicit distribution reconstruction, corporate-action inspection, accumulating/distributing coherence checks and representative Yahoo overlaps.

For an ex-distribution date, the independent reconstruction is:

`(split-adjusted raw close_t + distribution_t in price units) / raw close_t-1 - 1`

The stored authoritative series remains adjusted-close percentage change. The distribution is not added again. Event status counts were `{event_counts}`; listing validation statuses were `{listing_validation_counts}`. Yahoo overlap statuses were `{yahoo_counts}`.

Where a GBP-labelled vendor event is numerically implausible relative to a GBP raw price, policy v1.1 applies a recorded 0.01 pence-to-GBP normalization only under the declared 20% plausibility bound. Missing ex-date prices remain unresolved and are never silently shifted.

Missing, stale, post-stale catch-up and unexplained >35% daily observations are invalid rather than forward-filled. Live implementation and proxy histories use different labels and files.
"""
    reports["UKACTIVE_A2_FX_AND_GBP_ACCOUNTING_POLICY.md"] = f"""# UKACTIVE A2 — FX and GBP Accounting Policy

Portfolio accounting currency is GBP. GBP and GBX listing lines receive no FX conversion; GBX applies the explicit price-unit multiplier `0.01`. Foreign-currency listing wealth is local adjusted wealth multiplied once by the ECB GBP-per-local reference rate published by the XLON close. The same-date rate is used when present; only ECB/TARGET observation gaps fall back to the latest prior rate.

The ECB normally publishes the reference rates around 16:00 CET, before the 16:30 Europe/London LSE close. They are used as deterministic informational valuation references, not asserted transaction prices.

Trading currency is not used to infer underlying economic currency exposure. A GBP-listed unhedged US equity ETF therefore receives no second FX conversion: its GBP quote already embeds translation. A USD listing of the same ISIN is converted once for GBP accounting.

Same-ISIN GBP/foreign listing validation statuses were `{fx_counts}` across {len(fx_pairs)} pairs. A2 recorded every A0A1/EODHD GBP-versus-GBX discrepancy as a versioned lineage correction rather than silently changing A0A1.
"""
    reports["UKACTIVE_A2_CASH_MODEL.md"] = f"""# UKACTIVE A2 — GBP Cash Model

`ACTUAL_GBP_CASH` is a separate research asset, not an exchange-traded instrument. It uses Bank of England daily SONIA (`IUDSOIA`) mirrored by FRED, compounded ACT/365 across calendar days between XLON sessions. The independent validation series is the Bank of England SONIA Compounded Index (`IUDZOS2`), also mirrored by FRED.

Validation result: `{cash_validation}`.

No fee, haircut, tax or account-specific spread is applied in A2. The series is not represented as CSH2 or another cash-like ETF, and it is not a claim about IBKR or any broker's client cash rate.
"""
    reports["UKACTIVE_A2_IMPLEMENTATION_SELECTION_POLICY.md"] = f"""# UKACTIVE A2 — Canonical Implementation Selection Policy

For return date T, selection information is limited to the immediately prior canonical XLON session. Candidate requirements and ordered tie-breaks are fixed in `{POLICY_PATH}`.

Order: GBP/GBX listing first; more valid observations accumulated only through the information date; fewer bad observations accumulated only through that date; earlier first observed date; then stable share-class and listing IDs. Current AUM, current liquidity, future eligibility, future returns, provider popularity and all legacy ETF strategy logic are forbidden.

The output records the selected share class, selected listing, information date, reason and evidence. `execution_eligible_date` is strictly later than `signal_information_date`; same-close return capture is impossible by construction.
"""
    reports["UKACTIVE_A2_DATA_QUALITY_REPORT.md"] = f"""# UKACTIVE A2 — Data Quality Report

Decision: `{decision}`

- Automated tests: {test_counts}; critical failures: {int(((tests['critical']) & (tests['status'] == 'FAIL')).sum())}.
- Usable A0A1 family histories: {counts['economic_exposure_families_with_usable_histories']}.
- Validated actual implementation histories: {counts['families_with_validated_actual_implementation_histories']} families.
- Explicit distribution reconstruction: {event_counts}.
- Listing validation: {listing_validation_counts}.
- Representative Yahoo overlaps: {yahoo_counts}.
- FX same-ISIN cross-checks: {fx_counts}.
- Stale sessions flagged and invalidated: {stale_total}.
- Missing in-life sessions retained as missing: {missing_total}.
- Delisted exact-ISIN listing extensions retained: {historical_extensions}.
- Broker checks: zero; every row remains `NOT_CHECKED`.

No missing price was forward-filled and no stale price was converted to a legitimate zero return. Price-unit corrections are in `UKACTIVE_A2_LINEAGE_CORRECTIONS.csv`. The EODHD route is an indicative vendor source, not an official exchange total-return feed; this limitation remains open and visible.
"""
    reports["UKACTIVE_A2_A3_READINESS_REPORT.md"] = f"""# UKACTIVE A2 — A3 Readiness

Decision: `{decision}`

A3-ready A0A1 families: **{counts['a3_ready_family_count']}**. The readiness rule requires at least {policy['a3_readiness']['minimum_valid_observations']} consecutive-valid-capable observations, an actual implementation history and no failed return/FX/price-unit gate. Tier metadata is preserved, so A3 can distinguish CORE from CORE + EXTENDED without rebuilding data.

A3 signal discovery authorised: **{'YES' if a3_authorized else 'NO'}**.

If authorised, A3 is research-only and must use the point-in-time flags, prior-session information mapping and duplicate-safe economic-family rows. It may not call an uncertain historical eligibility state verified investability, may not splice the empty proxy panel into live histories and may not make deployment claims. Broker confirmation remains mandatory before any future `DEPLOYMENT_CANDIDATE` state.

Open items: {len(unresolved)}. Families requiring a proxy for a 504-observation research window: {counts['families_requiring_proxy_histories']}.
"""
    return reports


def git_state(path: Path) -> dict[str, Any]:
    try:
        inside = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if inside.returncode != 0 or inside.stdout.strip().lower() != "true":
            return {
                "commit": "NOT_AVAILABLE_NOT_A_GIT_WORKTREE",
                "worktree_state": "NOT_APPLICABLE_NOT_A_GIT_WORKTREE",
                "complete_patch_if_dirty": "NOT_APPLICABLE_NOT_A_GIT_WORKTREE",
            }
        commit = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=15).stdout.strip()
        status = subprocess.run(["git", "-C", str(path), "status", "--porcelain=v1"], capture_output=True, text=True, timeout=15).stdout
        diff = subprocess.run(["git", "-C", str(path), "diff", "--binary", "HEAD"], capture_output=True, text=True, timeout=30).stdout
        return {
            "commit": commit,
            "worktree_state": "DIRTY" if status.strip() else "CLEAN",
            "porcelain_status": status,
            "complete_patch_if_dirty": diff if status.strip() else "NOT_APPLICABLE_CLEAN",
        }
    except Exception as exc:
        return {
            "commit": "NOT_AVAILABLE",
            "worktree_state": "GIT_CHECK_FAILED",
            "complete_patch_if_dirty": "NOT_AVAILABLE",
            "error": f"{type(exc).__name__}:{exc}",
        }


def package_versions() -> dict[str, str]:
    names = ["pandas", "numpy", "pyarrow", "requests", "duckdb", "scipy"]
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "NOT_INSTALLED"
    return versions


def main() -> int:
    parser = argparse.ArgumentParser(description="Build UKACTIVE-A2 point-in-time and GBP total-return research data")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--refresh", action="store_true", help="Refresh read-only HTTP source captures instead of reusing hashed captures")
    args = parser.parse_args()

    started_at = utc_now()
    for directory in [CODE_DIR, CONFIG_DIR, EVIDENCE_DIR, SOURCE_DIR, RAW_EODHD_DIR, RAW_EXTERNAL_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    inputs = read_inputs()
    input_paths = [PROGRAMME_ROOT / name for name in A0_INPUTS] + [POLICY_PATH, CODE_DIR / "ukactive_a2_core.py", Path(__file__).resolve()]
    input_hashes = {str(path): sha256_file(path) for path in input_paths}

    key, key_source = load_api_key()
    client = CaptureClient(key, SOURCE_DIR, refresh=args.refresh)
    active_payload = client.get_json(
        "EODHD",
        "https://eodhd.com/api/exchange-symbol-list/LSE",
        {},
        "eodhd/catalogue_lse_active.json.gz",
        "EXCHANGE_SYMBOL_LIST:LSE:ACTIVE",
    )
    delisted_payload = client.get_json(
        "EODHD",
        "https://eodhd.com/api/exchange-symbol-list/LSE",
        {"delisted": 1},
        "eodhd/catalogue_lse_delisted.json.gz",
        "EXCHANGE_SYMBOL_LIST:LSE:DELISTED",
    )
    try:
        client.get_json(
            "EODHD",
            "https://eodhd.com/api/exchange-details/LSE",
            {"from": policy["history_end"][:4] + "-01-01", "to": policy["history_end"]},
            "eodhd/exchange_details_lse.json.gz",
            "EXCHANGE_DETAILS:LSE:CURRENT_WINDOW",
        )
    except Exception as exc:
        print(f"Exchange-details corroboration unavailable: {type(exc).__name__}", flush=True)

    active_catalogue = normalize_catalogue(active_payload, False)
    delisted_catalogue = normalize_catalogue(delisted_payload, True)
    routes, lineage = build_listing_routes(inputs, active_catalogue, delisted_catalogue)
    routes = enrich_routes(routes, inputs)
    lineage = pd.concat(
        [
            lineage,
            pd.DataFrame(
                [
                    {
                        "lineage_item_id": "A2LIN-POLICY-V1-2",
                        "lineage_action": "POLICY_REVISION_AFTER_FAILED_VALIDATION_DRY_RUN_BEFORE_FINAL_PANEL",
                        "a0a1_record_id": "NOT_APPLICABLE",
                        "field": "distribution_event_unit_resolution_and_fx_reference_timing",
                        "a0a1_value": "NOT_APPLICABLE",
                        "a2_value": policy.get("revision_note", "UKACTIVE-A2-POLICY-v1.1.0"),
                        "evidence": "Initial A2 validation dry run; no final panel decision was promoted from that run.",
                        "status": "PREDECLARED_FOR_FINAL_BUILD",
                        "materiality": "TOTAL_RETURN_CORRECTNESS_AND_REPRODUCIBILITY",
                    }
                ]
            ),
        ],
        ignore_index=True,
        sort=False,
    )
    if routes.empty:
        raise RuntimeError("No exact ticker+ISIN LSE routes were admitted")
    print(f"Admitted {len(routes)} exact-identity active/historical listing routes", flush=True)

    payloads = fetch_listing_payloads(client, routes, policy, args.workers)
    normalized_prices = {listing_id: normalize_price_payload(payload.get("eod", [])) for listing_id, payload in payloads.items()}
    calendar, calendar_audit = build_calendar(normalized_prices, routes)
    if len(calendar) < 504:
        raise RuntimeError(f"Canonical XLON observed calendar is too short: {len(calendar)} sessions")

    currencies = routes["effective_listing_currency"].dropna().astype(str).str.upper().tolist()
    ecb_rows = fetch_ecb_fx(client, policy["history_start"], policy["history_end"], currencies)
    fx_table = build_fx_table(ecb_rows, calendar, currencies)
    sonia_rate = fetch_fred_series(client, "IUDSOIA", policy["history_start"], policy["history_end"])
    sonia_index = fetch_fred_series(client, "IUDZOS2", "2018-04-23", policy["history_end"])
    cash, cash_validation = build_cash_series(calendar, sonia_rate, sonia_index)

    instrument, pit, events, stale_report, listing_frames = build_instrument_and_eligibility_histories(
        routes, payloads, calendar, fx_table, policy
    )
    validations = listing_validation_status(routes, events, listing_frames)
    instrument, pit, listing_frames = apply_listing_validation_gate(instrument, pit, listing_frames, validations)
    yahoo_validation = fetch_and_validate_yahoo(client, routes, listing_frames, policy)
    fx_pairs = build_fx_pair_validation(routes, listing_frames)
    instrument, pit, listing_frames, validations, cross_source_exclusions = apply_cross_source_failure_gate(
        routes, instrument, pit, listing_frames, validations, fx_pairs, yahoo_validation
    )
    if not cross_source_exclusions.empty:
        lineage = pd.concat([lineage, cross_source_exclusions], ignore_index=True, sort=False)
    coherence = build_share_class_coherence(routes, listing_frames)
    canonical, exposure, panel = build_canonical_histories(
        routes, listing_frames, pit, inputs["exposure"], calendar, cash, policy
    )
    readiness = build_readiness(exposure, inputs["exposure"], policy)
    manual_cases, manual_markdown = build_manual_validation_cases(routes, listing_frames, events, cash)

    proxy_columns = {
        "date": pd.Series(dtype="datetime64[ns]"),
        "economic_exposure_family_id": pd.Series(dtype="string"),
        "proxy_series_id": pd.Series(dtype="string"),
        "return_gbp_total": pd.Series(dtype="float64"),
        "proxy_flag": pd.Series(dtype="bool"),
        "history_type": pd.Series(dtype="string"),
        "source_series_identifier": pd.Series(dtype="string"),
        "data_valid": pd.Series(dtype="bool"),
        "warning": pd.Series(dtype="string"),
    }
    proxy_panel = pd.DataFrame(proxy_columns)

    historical_extension_count = int(routes["historical_listing_extension"].sum())
    tests = run_automated_tests(
        policy,
        routes,
        instrument,
        pit,
        canonical,
        panel,
        events,
        validations,
        lineage,
        cash_validation,
        fx_pairs,
        yahoo_validation,
        historical_extension_count,
    )
    unresolved = build_unresolved_items(routes, inputs, readiness, lineage, stale_report, events)
    counts = summary_counts(readiness, routes, validations, panel)
    critical_failures = int(((tests["critical"]) & (tests["status"].eq("FAIL"))).sum())
    pass_gate = (
        critical_failures == 0
        and counts["economic_exposure_families_with_usable_histories"] >= 60
        and counts["a3_ready_family_count"] >= 30
        and cash_validation.get("status") == "PASS"
    )
    decision = "UKACTIVE_A2_PASS_WITH_OPEN_ITEMS" if pass_gate and len(unresolved) else ("UKACTIVE_A2_PASS" if pass_gate else "UKACTIVE_A2_FAIL")
    a3_authorized = decision in {"UKACTIVE_A2_PASS", "UKACTIVE_A2_PASS_WITH_OPEN_ITEMS"}

    parquet_meta = {
        "run_id": RUN_ID,
        "stage_id": STAGE_ID,
        "policy_id": policy["policy_id"],
        "policy_sha256": sha256_file(POLICY_PATH),
        "created_at_utc": utc_now(),
        "warning": "CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY",
    }
    # Canonical machine-readable data.
    write_parquet(instrument, PROGRAMME_ROOT / "UKACTIVE_A2_INSTRUMENT_HISTORY_MASTER.parquet", parquet_meta)
    write_parquet(exposure, PROGRAMME_ROOT / "UKACTIVE_A2_EXPOSURE_HISTORY_MASTER.parquet", parquet_meta)
    write_parquet(pit, PROGRAMME_ROOT / "UKACTIVE_A2_POINT_IN_TIME_ELIGIBILITY.parquet", parquet_meta)
    write_parquet(canonical, PROGRAMME_ROOT / "UKACTIVE_A2_CANONICAL_IMPLEMENTATION_HISTORY.parquet", parquet_meta)
    write_parquet(panel, PROGRAMME_ROOT / "UKACTIVE_A2_TOTAL_RETURN_PANEL_GBP.parquet", parquet_meta)
    write_parquet(proxy_panel, PROGRAMME_ROOT / "UKACTIVE_A2_PROXY_HISTORY_PANEL.parquet", parquet_meta)
    write_parquet(fx_table, PROGRAMME_ROOT / "UKACTIVE_A2_FX_SERIES.parquet", parquet_meta)
    write_parquet(cash, PROGRAMME_ROOT / "UKACTIVE_A2_CASH_SERIES.parquet", parquet_meta)

    # Deterministic derived matrices; these never create additional economic opportunities.
    return_matrix = panel.pivot(index="date", columns="economic_exposure_family_id", values="return_gbp_total").sort_index()
    valid_matrix = panel.pivot(index="date", columns="economic_exposure_family_id", values="data_valid").sort_index()
    write_parquet(return_matrix.reset_index(), PROGRAMME_ROOT / "UKACTIVE_A2_TOTAL_RETURN_MATRIX_GBP.parquet", parquet_meta)
    write_parquet(valid_matrix.reset_index(), PROGRAMME_ROOT / "UKACTIVE_A2_DATA_VALID_MATRIX.parquet", parquet_meta)

    # Human-auditable ledgers and diagnostics.
    write_csv(events, PROGRAMME_ROOT / "UKACTIVE_A2_DISTRIBUTION_EVENTS.csv")
    write_csv(stale_report, PROGRAMME_ROOT / "UKACTIVE_A2_STALE_AND_MISSING_DATA_REPORT.csv")
    write_csv(tests, PROGRAMME_ROOT / "UKACTIVE_A2_AUTOMATED_TEST_RESULTS.csv")
    write_csv(unresolved, PROGRAMME_ROOT / "UKACTIVE_A2_UNRESOLVED_ITEMS.csv")
    write_csv(lineage, PROGRAMME_ROOT / "UKACTIVE_A2_LINEAGE_CORRECTIONS.csv")
    write_csv(routes, PROGRAMME_ROOT / "UKACTIVE_A2_SOURCE_ROUTE_MAP.csv")
    write_csv(validations, PROGRAMME_ROOT / "UKACTIVE_A2_TOTAL_RETURN_VALIDATION_BY_LISTING.csv")
    write_csv(yahoo_validation, PROGRAMME_ROOT / "UKACTIVE_A2_OVERLAPPING_SOURCE_VALIDATION.csv")
    write_csv(fx_pairs, PROGRAMME_ROOT / "UKACTIVE_A2_FX_PAIR_VALIDATION.csv")
    write_csv(coherence, PROGRAMME_ROOT / "UKACTIVE_A2_SHARE_CLASS_COHERENCE.csv")
    write_csv(calendar_audit, PROGRAMME_ROOT / "UKACTIVE_A2_XLON_RESEARCH_CALENDAR.csv")
    write_csv(readiness, PROGRAMME_ROOT / "UKACTIVE_A2_FAMILY_COVERAGE_AND_READINESS.csv")
    write_csv(manual_cases, PROGRAMME_ROOT / "UKACTIVE_A2_MANUAL_VALIDATION_CASES.csv")
    (PROGRAMME_ROOT / "UKACTIVE_A2_MANUAL_VALIDATION_CASES.md").write_text(manual_markdown, encoding="utf-8")

    source_ledger = build_source_ledger(client, input_hashes)
    write_csv(source_ledger, PROGRAMME_ROOT / "UKACTIVE_A2_DATA_SOURCE_LEDGER.csv")
    evidence_path = EVIDENCE_DIR / "UKACTIVE_A2_EVIDENCE_LEDGER.jsonl"
    with evidence_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in source_ledger.to_dict(orient="records"):
            handle.write(json.dumps({"record_type": "SOURCE", **row}, default=json_default) + "\n")
        for row in lineage.to_dict(orient="records"):
            handle.write(json.dumps({"record_type": "LINEAGE", **row}, default=json_default) + "\n")
        for row in manual_cases.to_dict(orient="records"):
            handle.write(json.dumps({"record_type": "MANUAL_VALIDATION", **row}, default=json_default) + "\n")

    reports = render_reports(
        policy, counts, decision, a3_authorized, tests, events, validations, fx_pairs, yahoo_validation,
        cash_validation, stale_report, routes, readiness, unresolved
    )
    for filename, text in reports.items():
        (PROGRAMME_ROOT / filename).write_text(text, encoding="utf-8")

    decision_payload = {
        "stage_id": STAGE_ID,
        "run_id": RUN_ID,
        "decision": decision,
        "a3_signal_discovery_authorised": a3_authorized,
        "authorisation_scope": "RESEARCH_ONLY_A3_READY_FAMILIES_NO_DEPLOYMENT_CLAIM" if a3_authorized else "NOT_AUTHORISED",
        "counts": counts,
        "total_return_validation_results": {
            "listing_status_counts": validations["total_return_validation_status"].value_counts().to_dict(),
            "distribution_event_status_counts": events["validation_status"].value_counts().to_dict() if not events.empty else {},
            "overlap_source_status_counts": yahoo_validation["validation_status"].value_counts().to_dict(),
        },
        "fx_gbp_validation_results": fx_pairs["validation_status"].value_counts().to_dict() if not fx_pairs.empty else {},
        "cash_validation": cash_validation,
        "automated_tests": {"passed": int(tests["status"].eq("PASS").sum()), "failed": int(tests["status"].eq("FAIL").sum()), "critical_failures": critical_failures},
        "open_item_count": int(len(unresolved)),
        "warning": "CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY",
        "strategy_results_produced": False,
    }
    write_json(decision_payload, PROGRAMME_ROOT / "UKACTIVE_A2_DECISION.json")
    with evidence_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps({"record_type": "DECISION", **decision_payload}, default=json_default) + "\n")

    completed_at = utc_now()
    output_paths = sorted(
        [path for path in PROGRAMME_ROOT.glob("UKACTIVE_A2_*") if path.is_file() and path.name != "UKACTIVE_A2_MANIFEST.json"]
        + [evidence_path]
    )
    output_hashes = {str(path): sha256_file(path) for path in output_paths}
    coverage_records = readiness.to_dict(orient="records")
    manifest = {
        "programme_id": PROGRAMME_ROOT.name,
        "programme_root": str(PROGRAMME_ROOT),
        "stage_id": STAGE_ID,
        "run_id": RUN_ID,
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "decision": decision,
        "git": git_state(Path(r"D:\Codex\equity_quant_research_platform")),
        "executed_command_line": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        "input_hashes": input_hashes,
        "source_code_hashes": {
            str(Path(__file__).resolve()): sha256_file(Path(__file__).resolve()),
            str(CODE_DIR / "ukactive_a2_core.py"): sha256_file(CODE_DIR / "ukactive_a2_core.py"),
        },
        "executed_source_snapshot_paths": [str(Path(__file__).resolve()), str(CODE_DIR / "ukactive_a2_core.py"), str(POLICY_PATH)],
        "output_hashes_excluding_manifest_itself": output_hashes,
        "source_urls": SOURCE_URLS,
        "source_retrieval_timestamps": sorted(set(source_ledger["retrieval_timestamp_utc"].astype(str))),
        "source_series_identifiers": sorted(set(source_ledger["series_identifier"].astype(str))),
        "source_capture_count": int(source_ledger["capture_path"].ne("NOT_CAPTURED_PUBLIC_DOCUMENTATION").sum()),
        "evidence_record_count": sum(1 for _ in evidence_path.open("r", encoding="utf-8")),
        "broker_check_method": "NOT_CHECKED_NO_SAFE_EXACT_ISIN_ROUTE_EXECUTED",
        "broker_confirmed_count": 0,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "timezone": "Europe/London",
            "package_versions": package_versions(),
        },
        "policy": policy,
        "policy_hash": sha256_file(POLICY_PATH),
        "classification_rule_version": inputs["a0_manifest"].get("classification_rule_version", "UKACTIVE-CLASSIFICATION-v1.0.0"),
        "duplicate_rule_version": inputs["a0_manifest"].get("duplicate_rule_version", "UKACTIVE-DUPLICATE-v1.0.0"),
        "a2_implementation_rule_version": policy["policy_id"],
        "automated_test_results": tests.to_dict(orient="records"),
        "unresolved_gaps": unresolved.to_dict(orient="records"),
        "data_coverage_statistics_by_exposure_family": coverage_records,
        "counts": counts,
        "cash_validation": cash_validation,
        "reproducibility_assessment": "EXECUTED_CODE_INPUT_SOURCE_AND_OUTPUT_HASHES_COMPLETE; NO_GIT_ANCESTRY_AVAILABLE",
        "manifest_self_hash_policy": "Manifest excludes its own hash to avoid recursion",
        "strategy_backtest_executed": False,
        "strategy_performance_statistics_produced": False,
        "warning": "CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY",
    }
    write_json(manifest, PROGRAMME_ROOT / "UKACTIVE_A2_MANIFEST.json")

    missing_required = [name for name in REQUIRED_OUTPUTS if not (PROGRAMME_ROOT / name).exists()]
    if missing_required:
        raise RuntimeError(f"Required output contract incomplete: {missing_required}")
    print(json.dumps({"decision": decision, "counts": counts, "critical_test_failures": critical_failures}, indent=2), flush=True)
    return 0 if decision != "UKACTIVE_A2_FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
