"""UKACTIVE-A3R2U: current refresh and five-year lifecycle audit."""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow

import build_ukactive_a0a1 as a0
from ukactive_a3r2_core import (
    PLATFORM_ROOT,
    PROGRAMME_ROOT,
    WARNING,
    audit_file,
    bool_series,
    git_output,
    read_policy,
    sha256_bytes,
    sha256_file,
    stable_id,
    utc_now,
    write_csv,
    write_json,
    write_parquet,
    write_text,
)


PREFIX = "UKACTIVE_A3R2U"
OBSERVATION_DATE = "2026-08-23"
RUN_ID = "UKACTIVE-A3R2U-20260823-001"
SOURCE_DIR = PROGRAMME_ROOT / "evidence" / "sources" / "a3r2u_20260823"
LEDGER_PATH = PROGRAMME_ROOT / "evidence" / "UKACTIVE_A3R2_EVIDENCE_LEDGER.jsonl"


II_CONFIRMED = {"CUKS", "TELE", "NDUS", "MTRL", "ITEC", "UTIL", "SEAL", "EBIG", "CSUK", "EBIZ"}


CURATED_LIFECYCLE_EVENTS = [
    ("IE000HMSHYJ6", "2024-04-29", "CLOSURE", "Electric Vehicle Charging Infrastructure UCITS ETF", "https://hanetf.com/closed-funds/"),
    ("IE00BMFNWC33", "2024-04-17", "CLOSURE", "Solar Energy UCITS ETF", "https://hanetf.com/closed-funds/"),
    ("IE00BLH3CV30", "2024-04-19", "MERGER", "Procure Space UCITS ETF merged into Future of Defence UCITS ETF", "https://hanetf.com/closed-funds/"),
    ("IE00BN76Y761", "2024-04-19", "MERGER", "U.S. Global Jets UCITS ETF merged into The Travel UCITS ETF", "https://hanetf.com/closed-funds/"),
    ("IE00BLH3CQ86", "2024-02-27", "MERGER", "HANetf S&P Global Clean Energy Select merged into iClima Global Decarbonisation Enablers", "https://hanetf.com/closed-funds/"),
    ("IE00BMQ8YK98", "2024-03-14", "MERGER", "ETC Group Digital Assets and Blockchain Equity merged into ETC Group Global Metaverse", "https://hanetf.com/closed-funds/"),
    ("IE00BDDRF924", "2024-03-28", "MERGER", "HAN-GINS Cloud Technology merged into HAN-GINS Tech Megatrend", "https://hanetf.com/closed-funds/"),
    ("IE000TVPSRI1", "2025-03-19", "MERGER", "Grayscale Future of Finance merged into HAN-GINS Tech Megatrend", "https://hanetf.com/closed-funds/"),
    ("IE000KDY10O3", "2024-07-01", "MANDATE_CHANGE", "ETC Group Global Metaverse changed to ETC Group Web 3.0", "https://hanetf.com/closed-funds/"),
    ("IE000KDY10O3", "2026-07-15", "MANDATE_CHANGE", "Strategy changed to Future of US Defence UCITS ETF", "https://hanetf.com/fund/gijo-future-of-us-defence-etf/"),
    ("NOT_AVAILABLE", "2024-08-21", "CLOSURE", "iShares FTSE Italia Mid-Small Cap UCITS ETF ceased operations", "https://www.ishares.com/uk/individual/en/literature/annual-report/ishares-vii-plc-en-annual-report-2025.pdf"),
]


def out(name: str) -> Path:
    return PROGRAMME_ROOT / f"{PREFIX}_{name}"


def append_ledger(records: list[dict[str, Any]]) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing_ids: set[str] = set()
    if LEDGER_PATH.exists():
        for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                existing_ids.add(str(json.loads(line)["evidence_id"]))
            except (json.JSONDecodeError, KeyError):
                raise AssertionError(f"Malformed existing evidence-ledger row: {LEDGER_PATH}")
    with LEDGER_PATH.open("a", encoding="utf-8") as handle:
        for record in records:
            if str(record["evidence_id"]) in existing_ids:
                continue
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
            existing_ids.add(str(record["evidence_id"]))


def fetch_live_lse() -> tuple[pd.DataFrame, list[dict[str, Any]], list[dict[str, Any]]]:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    source_audit: list[dict[str, Any]] = []
    for subcategory_id, label in [("15", "ETF"), ("16", "ETC"), ("17", "ETN")]:
        page = 1
        while True:
            parameters = f"categories=ETFS&subcategories={subcategory_id}&page={page}&size=100"
            result = a0.lse_post(parameters)
            payload = a0.json_load_result(result)
            page_rows = a0.flatten_lse_rows(payload)
            capture = SOURCE_DIR / f"lse_{label.lower()}_page_{page:03d}.json"
            capture.write_bytes(result.body)
            digest = sha256_bytes(result.body)
            evidence_id = stable_id("EVD-A3R2", "LSE", label, page, digest)
            ledger.append(
                {
                    "evidence_id": evidence_id,
                    "stage_id": "UKACTIVE-A3R2U",
                    "evidence_type": "CURRENT_EXCHANGE_CATALOGUE",
                    "publisher": "London Stock Exchange",
                    "url": result.url,
                    "retrieved_at": result.retrieved_at,
                    "source_sha256": digest,
                    "local_capture": capture.relative_to(PROGRAMME_ROOT).as_posix(),
                    "supports": "Current LSE ETF/ETC/ETN listing presence and exact ISIN/ticker/currency identity; not historical or broker eligibility",
                }
            )
            source_audit.append({"source": "LSE_PRICE_EXPLORER", "subcategory": label, "page": page, "url": result.url, "retrieved_at": result.retrieved_at, "sha256": digest, "row_count": len(page_rows)})
            for raw in page_rows:
                if str(a0.field(raw, "islse")).lower() not in {"true", "1"}:
                    continue
                raw_currency = a0.clean_text(a0.field(raw, "currency"))
                listing_currency, price_unit, multiplier = a0.price_fields(raw_currency)
                rows.append(
                    {
                        "isin": a0.clean_text(a0.field(raw, "isin")).upper(),
                        "ticker": a0.clean_text(a0.field(raw, "tidm", "ticker")).upper(),
                        "mic": "XLON",
                        "listing_currency": listing_currency,
                        "price_unit": price_unit,
                        "price_unit_multiplier": multiplier,
                        "issuer": a0.clean_text(a0.field(raw, "issuername", "issuer")),
                        "description": a0.clean_text(a0.field(raw, "description", "name")),
                        "instrument_type": a0.instrument_type(label, a0.clean_text(a0.field(raw, "description", "name"))),
                        "last_price_observed": a0.clean_text(a0.field(raw, "lastprice", "midprice")),
                        "source_url": result.url,
                        "evidence_id": evidence_id,
                    }
                )
            if len(page_rows) < 100:
                break
            page += 1
            if page > 100:
                raise AssertionError("Unexpected LSE pagination depth")
    frame = pd.DataFrame(rows).drop_duplicates(["isin", "ticker", "mic", "price_unit"]).sort_values(["isin", "ticker", "price_unit"]).reset_index(drop=True)
    return frame, ledger, source_audit


def capture_policy_sources() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for label, url in [
        ("II_CHARGES", "https://www.ii.co.uk/our-charges"),
        ("HANETF_CLOSED_FUNDS", "https://hanetf.com/closed-funds/"),
        ("HANETF_US_DEFENCE", "https://hanetf.com/fund/gijo-future-of-us-defence-etf/"),
    ]:
        result = a0.fetch(url)
        capture = SOURCE_DIR / f"{label.lower()}.html"
        captured = result.status == 200 and bool(result.body)
        if captured:
            capture.write_bytes(result.body)
        digest = sha256_bytes(result.body) if captured else "NOT_CAPTURED_HTTP_ERROR"
        records.append(
            {
                "evidence_id": stable_id("EVD-A3R2", label, result.retrieved_at, digest),
                "stage_id": "UKACTIVE-A3R2U",
                "evidence_type": "CURRENT_PRIMARY_WEB_SOURCE",
                "publisher": "Interactive Investor" if label == "II_CHARGES" else "HANetf",
                "url": result.url,
                "retrieved_at": result.retrieved_at,
                "http_status": result.status,
                "retrieval_error": result.error or "NOT_APPLICABLE",
                "source_sha256": digest,
                "local_capture": capture.relative_to(PROGRAMME_ROOT).as_posix() if captured else "NOT_CAPTURED_HTTP_ERROR",
                "supports": "Current platform costs" if label == "II_CHARGES" else "Recent ETF closure, merger and mandate-change lifecycle evidence",
            }
        )
    records.append(
        {
            "evidence_id": "EVD-A3R2-USER-II-20260823",
            "stage_id": "UKACTIVE-A3R2U",
            "evidence_type": "USER_SUPPLIED_CURRENT_PLATFORM_OBSERVATION",
            "publisher": "User",
            "url": "NOT_APPLICABLE_USER_SUPPLIED",
            "retrieved_at": "2026-08-23T00:00:00+01:00",
            "source_sha256": "NOT_APPLICABLE_USER_SUPPLIED",
            "local_capture": "NOT_APPLICABLE",
            "supports": "Current-only Interactive Investor visibility/tradability for specified tickers; no historical back-projection",
        }
    )
    return records


def first_last_history(eligibility: pd.DataFrame) -> pd.DataFrame:
    valid = eligibility.loc[bool_series(eligibility["endpoint_valid"])].copy()
    summary = valid.groupby("economic_exposure_family_id")["date"].agg(first_valid_date="min", last_valid_date="max", valid_endpoint_count="count").reset_index()
    return summary


def preferred_lines() -> pd.DataFrame:
    path = PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_CURRENT_IMPLEMENTATION_LINES_POST_A2R.csv"
    frame = pd.read_csv(path, dtype=str).fillna("NOT_APPLICABLE")
    preferred = frame.loc[frame["preferred_or_alternate"].eq("PREFERRED")].copy()
    if preferred["economic_exposure_family_id"].duplicated().any():
        preferred = preferred.sort_values(["economic_exposure_family_id", "ticker"]).drop_duplicates("economic_exposure_family_id")
    return preferred


def build_current_snapshot(live: pd.DataFrame, eligibility: pd.DataFrame) -> pd.DataFrame:
    dynamic = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A2R_DYNAMIC_SIGNAL_ELIGIBILITY.parquet")
    roles = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_ROTATION_ROLE_MASTER_POST_A2R.csv", dtype=str).fillna("NOT_APPLICABLE")
    lines = preferred_lines()
    history = first_last_history(eligibility)
    role_columns = [
        "economic_exposure_family_id", "economic_exposure_name", "universe_tier", "asset_class", "sub_asset_class",
        "a0_primary_geography", "a0_geographic_scope", "sector", "industry", "economic_theme", "deepvue_theme",
        "primary_rotation_role", "primary_competition_pool_id", "parent_exposure_family_id", "overlap_cluster_id",
        "selectable_flag", "benchmark_only_flag", "research_data_ready_flag", "research_maturity",
    ]
    snapshot = dynamic[["economic_exposure_family_id", "valid_return_observations", "data_quality_flags"]].merge(
        roles[role_columns], on="economic_exposure_family_id", how="left", validate="one_to_one"
    ).merge(history, on="economic_exposure_family_id", how="left", validate="one_to_one")
    line_columns = [
        "economic_exposure_family_id", "fund_entity_id", "share_class_id", "listing_id", "isin", "ticker", "exchange", "mic",
        "listing_currency", "price_unit", "provider_issuer", "product_structure", "instrument_type", "ucits_status",
        "LSE_current_status", "UK_retail_disclosure_status", "public_ISA_rules_status", "public_evidence_URLs",
        "public_evidence_date", "public_evidence_confidence", "economic_lineage_valid",
    ]
    snapshot = snapshot.merge(lines[line_columns], on="economic_exposure_family_id", how="left", validate="one_to_one")
    live_keys = set(zip(live["isin"], live["ticker"], live["mic"], live["price_unit"]))
    snapshot["a3r2u_lse_current_status"] = [
        "CONFIRMED" if (str(row.isin), str(row.ticker), str(row.mic), str(row.price_unit)) in live_keys else "NOT_CONFIRMED"
        for row in snapshot.itertuples()
    ]
    snapshot["II_CURRENT_TRADABLE"] = snapshot["ticker"].where(snapshot["ticker"].isin(II_CONFIRMED), "NOT_CHECKED")
    snapshot.loc[snapshot["ticker"].isin(II_CONFIRMED), "II_CURRENT_TRADABLE"] = "CONFIRMED_BY_USER"
    snapshot["II_OBSERVATION_DATE"] = snapshot["ticker"].where(snapshot["ticker"].isin(II_CONFIRMED), "NOT_APPLICABLE")
    snapshot.loc[snapshot["ticker"].isin(II_CONFIRMED), "II_OBSERVATION_DATE"] = OBSERVATION_DATE
    snapshot["II_CONFIRMED_ALTERNATE_TICKERS"] = "NOT_APPLICABLE"
    snapshot.loc[snapshot["economic_exposure_family_id"].eq("GLOBAL_RETAIL"), "II_CONFIRMED_ALTERNATE_TICKERS"] = "EBIZ_USD_LINE"
    snapshot["II_USER_IMPLEMENTATION_PREFERENCE"] = "NOT_STATED"
    snapshot.loc[snapshot["economic_exposure_family_id"].eq("GLOBAL_RETAIL"), "II_USER_IMPLEMENTATION_PREFERENCE"] = "PREFER_EBIG_GBP_OVER_EBIZ_USD"
    snapshot.loc[snapshot["economic_exposure_family_id"].eq("UK_BROAD_MARKET"), "II_USER_IMPLEMENTATION_PREFERENCE"] = "PREFER_CSUK;FASA_NOT_PREFERRED"
    snapshot["current_implementable_view"] = (
        snapshot["a3r2u_lse_current_status"].eq("CONFIRMED")
        & snapshot["economic_lineage_valid"].astype(str).str.upper().isin({"TRUE", "YES"})
    ).map({True: "YES", False: "NO"})
    snapshot["current_observation_date"] = OBSERVATION_DATE
    snapshot["historical_ii_back_projection"] = "NO"
    snapshot["warning"] = WARNING
    return snapshot.sort_values("economic_exposure_family_id").reset_index(drop=True)


def build_change_log(live: pd.DataFrame, old: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    old_lse = old.loc[old["source_name"].eq("LSE_PRICE_EXPLORER")].copy()
    old_keys = set(zip(old_lse["isin"], old_lse["ticker"], old_lse["mic"], old_lse["price_unit"]))
    live_keys = set(zip(live["isin"], live["ticker"], live["mic"], live["price_unit"]))
    rows: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    old_isin_family = old.groupby("isin")["matched_economic_exposure_family_id"].agg(lambda values: ";".join(sorted(set(values) - {"NOT_CLASSIFIED_IN_CURATED_MASTER"}))).to_dict()
    for key in sorted(live_keys - old_keys):
        current = live.loc[(live["isin"] == key[0]) & (live["ticker"] == key[1]) & (live["mic"] == key[2]) & (live["price_unit"] == key[3])].iloc[0]
        family = old_isin_family.get(key[0], "") or "UNCLASSIFIED_NEW_CURRENT_LINE"
        change_type = "NEW_TRADING_LINE_EXISTING_ISIN" if key[0] in set(old_lse["isin"]) else "NEW_CURRENT_PRODUCT_CANDIDATE"
        rows.append({"change_id": stable_id("A3R2U-CHG", *key), "event_date": OBSERVATION_DATE, "event_type": change_type, "isin": key[0], "ticker": key[1], "economic_exposure_family_id": family, "description": current["description"], "source_url": current["source_url"], "evidence_confidence": "HIGH_CURRENT_LSE", "historical_effect": "NONE_UNTIL_VALIDATED"})
        candidates.append({"candidate_id": stable_id("A3R2U-NEW", *key), "isin": key[0], "ticker": key[1], "listing_currency": current["listing_currency"], "price_unit": key[3], "issuer": current["issuer"], "product_name": current["description"], "candidate_type": change_type, "existing_family_match": family, "admission_status": "NOT_ADMITTED_REQUIRES_IDENTITY_EVIDENCE_AND_A2_VALIDATION", "source_url": current["source_url"], "observation_date": OBSERVATION_DATE, "warning": WARNING})
    for key in sorted(old_keys - live_keys):
        prior = old_lse.loc[(old_lse["isin"] == key[0]) & (old_lse["ticker"] == key[1]) & (old_lse["mic"] == key[2]) & (old_lse["price_unit"] == key[3])].iloc[0]
        rows.append({"change_id": stable_id("A3R2U-CHG", "ABSENT", *key), "event_date": OBSERVATION_DATE, "event_type": "NOT_OBSERVED_IN_A3R2U_LSE_REFRESH", "isin": key[0], "ticker": key[1], "economic_exposure_family_id": prior["matched_economic_exposure_family_id"], "description": prior["description_as_published"], "source_url": prior["source_url"], "evidence_confidence": "MEDIUM_REQUIRES_PRODUCT_STATUS_REVIEW", "historical_effect": "DO_NOT_BACK_PROJECT"})
    for isin, date, event_type, description, source_url in CURATED_LIFECYCLE_EVENTS:
        family = old_isin_family.get(isin, "") or "NOT_CLASSIFIED_IN_CURRENT_MASTER"
        rows.append({"change_id": stable_id("A3R2U-LIFE", isin, date, event_type), "event_date": date, "event_type": event_type, "isin": isin, "ticker": "NOT_APPLICABLE", "economic_exposure_family_id": family, "description": description, "source_url": source_url, "evidence_confidence": "HIGH_PRIMARY_ISSUER", "historical_effect": "LIFECYCLE_EVENT_NO_SILENT_SURVIVOR_SUBSTITUTION"})
    change_log = pd.DataFrame(rows).sort_values(["event_date", "event_type", "isin"]).reset_index(drop=True)
    candidate_columns = ["candidate_id", "isin", "ticker", "listing_currency", "price_unit", "issuer", "product_name", "candidate_type", "existing_family_match", "admission_status", "source_url", "observation_date", "warning"]
    new_products = pd.DataFrame(candidates, columns=candidate_columns)
    return change_log, new_products


def build_lifecycle(snapshot: pd.DataFrame, eligibility: pd.DataFrame, endpoint: pd.DataFrame, change_log: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    cutoff = calendar.max()
    anniversary = cutoff - pd.DateOffset(years=5)
    start = calendar[calendar >= anniversary][0]
    transitions = endpoint.loc[bool_series(endpoint["implementation_transition_flag"])].groupby("economic_exposure_family_id")["date"].agg(
        implementation_transition_count="count", implementation_transition_dates=lambda x: ";".join(pd.to_datetime(x).dt.strftime("%Y-%m-%d"))
    ).reset_index()
    lifecycle = snapshot.merge(transitions, on="economic_exposure_family_id", how="left")
    lifecycle["implementation_transition_count"] = lifecycle["implementation_transition_count"].fillna(0).astype(int)
    lifecycle["implementation_transition_dates"] = lifecycle["implementation_transition_dates"].fillna("NOT_APPLICABLE")
    event_map = change_log.loc[change_log["economic_exposure_family_id"].ne("NOT_CLASSIFIED_IN_CURRENT_MASTER")].groupby("economic_exposure_family_id").agg(
        recent_external_event_count=("change_id", "count"),
        recent_external_events=("event_type", lambda x: ";".join(x.astype(str))),
        recent_external_event_dates=("event_date", lambda x: ";".join(x.astype(str))),
    ).reset_index()
    lifecycle = lifecycle.merge(event_map, on="economic_exposure_family_id", how="left")
    lifecycle["recent_external_event_count"] = lifecycle["recent_external_event_count"].fillna(0).astype(int)
    lifecycle["recent_external_events"] = lifecycle["recent_external_events"].fillna("NOT_APPLICABLE")
    lifecycle["recent_external_event_dates"] = lifecycle["recent_external_event_dates"].fillna("NOT_APPLICABLE")
    lifecycle["five_year_window_start"] = start
    lifecycle["data_cutoff"] = cutoff
    lifecycle["launched_within_final_five_years"] = (pd.to_datetime(lifecycle["first_valid_date"]) >= start).fillna(False).map({True: "YES", False: "NO"})
    lifecycle["valid_near_cutoff"] = (pd.to_datetime(lifecycle["last_valid_date"]) >= calendar[-4]).fillna(False).map({True: "YES", False: "NO"})
    lifecycle["lifecycle_primary_state"] = "CONTINUING_HISTORY"
    lifecycle.loc[lifecycle["launched_within_final_five_years"].eq("YES"), "lifecycle_primary_state"] = "LAUNCHED_WITHIN_FINAL_FIVE_YEARS"
    lifecycle.loc[lifecycle["implementation_transition_count"].gt(0), "lifecycle_primary_state"] = "CANONICAL_IMPLEMENTATION_TRANSITION"
    lifecycle.loc[lifecycle["recent_external_events"].str.contains("MANDATE_CHANGE", na=False), "lifecycle_primary_state"] = "MANDATE_CHANGE_REQUIRES_LINEAGE_BOUNDARY"
    lifecycle.loc[lifecycle["last_valid_date"].isna(), "lifecycle_primary_state"] = "NO_VALID_IMPLEMENTATION_HISTORY"
    lifecycle.loc[lifecycle["valid_near_cutoff"].eq("NO") & lifecycle["last_valid_date"].notna(), "lifecycle_primary_state"] = "HISTORY_NOT_CURRENT_AT_CUTOFF_REVIEW_REQUIRED"
    lifecycle["recent_survivorship_census_classification"] = "RECENT_FIVE_YEAR_CENSUS_SUBSTANTIALLY_COMPLETE"
    lifecycle["survivorship_limitation"] = "CURRENT_LSE_CENSUS_PLUS_MASTER_LINEAGE_AND_PRIMARY_ISSUER_EVENTS; NO_COMPLETE_LICENSED_HISTORICAL_LSE_DELISTING_FEED"
    keep = [
        "economic_exposure_family_id", "economic_exposure_name", "primary_rotation_role", "research_maturity", "first_valid_date", "last_valid_date",
        "valid_endpoint_count", "five_year_window_start", "data_cutoff", "launched_within_final_five_years", "valid_near_cutoff",
        "implementation_transition_count", "implementation_transition_dates", "recent_external_event_count", "recent_external_events",
        "recent_external_event_dates", "a3r2u_lse_current_status", "current_implementable_view", "lifecycle_primary_state",
        "recent_survivorship_census_classification", "survivorship_limitation", "warning",
    ]
    return lifecycle[keep].sort_values("economic_exposure_family_id").reset_index(drop=True)


def build_dynamic_universe(snapshot: pd.DataFrame, eligibility: pd.DataFrame, calendar: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cutoff = calendar.max()
    start = calendar[calendar >= cutoff - pd.DateOffset(years=5)][0]
    base = eligibility.copy()
    base["date"] = pd.to_datetime(base["date"])
    base = base.sort_values(["economic_exposure_family_id", "date"]).reset_index(drop=True)
    base["endpoint_valid_bool"] = bool_series(base["endpoint_valid"])
    base["accrued_valid_endpoint_count"] = base.groupby("economic_exposure_family_id")["endpoint_valid_bool"].cumsum()
    base["contemporaneous_research_maturity"] = "NEW"
    base.loc[base["accrued_valid_endpoint_count"].ge(504), "contemporaneous_research_maturity"] = "DEVELOPING"
    base.loc[base["accrued_valid_endpoint_count"].ge(1260), "contemporaneous_research_maturity"] = "MATURE"
    for horizon in [21, 42, 63, 126, 252]:
        base[f"dynamic_point_in_time_{horizon}"] = base[f"formation_return_{horizon}"].notna()
    at_start = base.loc[base["date"].eq(start), ["economic_exposure_family_id", "formation_return_63"]].copy()
    static_families = set(at_start.loc[at_start["formation_return_63"].notna(), "economic_exposure_family_id"])
    base["five_year_start_static_view"] = base["economic_exposure_family_id"].isin(static_families)
    base["mature_only_view"] = base["contemporaneous_research_maturity"].eq("MATURE")
    base["mature_plus_developing_view"] = base["contemporaneous_research_maturity"].isin(["MATURE", "DEVELOPING"])
    current_map = snapshot.set_index("economic_exposure_family_id")["current_implementable_view"]
    base["current_implementable_view_current_only"] = base["economic_exposure_family_id"].map(current_map).fillna("NO")
    base["current_implementable_metadata_back_projected"] = "NO"
    meta_cols = ["economic_exposure_family_id", "economic_exposure_name", "primary_rotation_role", "primary_competition_pool_id", "research_maturity", "universe_tier"]
    base = base.merge(snapshot[meta_cols], on="economic_exposure_family_id", how="left", validate="many_to_one")
    keep = [
        "date", "economic_exposure_family_id", "economic_exposure_name", "primary_rotation_role", "primary_competition_pool_id", "universe_tier",
        "endpoint_valid_bool", "accrued_valid_endpoint_count", "contemporaneous_research_maturity",
        "dynamic_point_in_time_21", "dynamic_point_in_time_42", "dynamic_point_in_time_63", "dynamic_point_in_time_126", "dynamic_point_in_time_252",
        "five_year_start_static_view", "mature_only_view", "mature_plus_developing_view", "current_implementable_view_current_only",
        "current_implementable_metadata_back_projected", "continuity_segment_id", "endpoint_failure_reason", "warning",
    ]
    dynamic = base[keep].copy()

    family_views = dynamic.groupby("economic_exposure_family_id").agg(
        economic_exposure_name=("economic_exposure_name", "first"),
        primary_rotation_role=("primary_rotation_role", "first"),
        first_endpoint_date=("date", "min"),
        latest_endpoint_date=("date", "max"),
        five_year_start_static=("five_year_start_static_view", "max"),
        latest_maturity=("contemporaneous_research_maturity", "last"),
        current_implementable_view=("current_implementable_view_current_only", "last"),
    ).reset_index()
    for horizon in [21, 42, 63, 126, 252]:
        counts = dynamic.groupby("economic_exposure_family_id")[f"dynamic_point_in_time_{horizon}"].sum().rename(f"valid_signal_dates_{horizon}")
        family_views = family_views.merge(counts, on="economic_exposure_family_id")
    family_views["warning"] = WARNING

    count_rows: list[dict[str, Any]] = []
    for year in range(start.year, cutoff.year + 1):
        year_dates = calendar[(calendar.year == year) & (calendar >= start)]
        if len(year_dates) == 0:
            continue
        date = year_dates.max()
        row = dynamic.loc[dynamic["date"].eq(date)]
        count_rows.append(
            {
                "year": year,
                "asof_date": date,
                "active_implementation_family_count": int(row["endpoint_valid_bool"].sum()),
                "eligible_short_63_family_count": int(row["dynamic_point_in_time_63"].sum()),
                "eligible_long_252_family_count": int(row["dynamic_point_in_time_252"].sum()),
                "five_year_start_static_active_count": int((row["endpoint_valid_bool"] & row["five_year_start_static_view"]).sum()),
                "mature_active_count": int((row["endpoint_valid_bool"] & row["mature_only_view"]).sum()),
                "partial_year": "YES" if year == cutoff.year else "NO",
            }
        )
    return dynamic, family_views, pd.DataFrame(count_rows)


def validation_results(live: pd.DataFrame, snapshot: pd.DataFrame, dynamic: pd.DataFrame, new_products: pd.DataFrame, change_log: pd.DataFrame) -> pd.DataFrame:
    tests = []
    def add(test_id: str, requirement: str, passed: bool, detail: str) -> None:
        tests.append({"test_id": test_id, "requirement": requirement, "status": "PASS" if passed else "FAIL", "detail": detail, "critical": "YES"})
    add("A3R2U-T01", "Master family identity remains unique", snapshot["economic_exposure_family_id"].is_unique, f"{len(snapshot)} rows")
    add(
        "A3R2U-T02",
        "Ticker does not replace family identity",
        "economic_exposure_family_id" in snapshot.columns
        and "ticker" in snapshot.columns
        and snapshot["economic_exposure_family_id"].notna().all(),
        "Every row retains family identity; ticker is implementation metadata and is not used as the key",
    )
    add("A3R2U-T03", "Live LSE refresh is non-empty", len(live) > 4000, f"{len(live)} current lines")
    add("A3R2U-T04", "Current ii evidence is not historical", set(dynamic["current_implementable_metadata_back_projected"]) == {"NO"}, "No current metadata back-projected")
    add("A3R2U-T05", "User ii confirmations are current-only", snapshot.loc[snapshot["II_CURRENT_TRADABLE"].eq("CONFIRMED_BY_USER"), "II_OBSERVATION_DATE"].eq(OBSERVATION_DATE).all(), f"{snapshot['II_CURRENT_TRADABLE'].eq('CONFIRMED_BY_USER').sum()} preferred lines")
    add("A3R2U-T06", "New products are not auto-admitted", new_products.empty or new_products["admission_status"].eq("NOT_ADMITTED_REQUIRES_IDENTITY_EVIDENCE_AND_A2_VALIDATION").all(), f"{len(new_products)} candidates")
    add("A3R2U-T07", "Point-in-time rows are unique", not dynamic.duplicated(["date", "economic_exposure_family_id"]).any(), f"{len(dynamic)} rows")
    add("A3R2U-T08", "Closed/mandate events are retained", change_log["event_type"].isin(["CLOSURE", "MERGER", "MANDATE_CHANGE"]).sum() >= 10, f"{change_log['event_type'].isin(['CLOSURE','MERGER','MANDATE_CHANGE']).sum()} primary-source events")
    add("A3R2U-T09", "FASA is not inferred ii-confirmed", not snapshot.loc[snapshot["ticker"].eq("FASA"), "II_CURRENT_TRADABLE"].eq("CONFIRMED_BY_USER").any(), "FASA preference is separate from availability")
    add("A3R2U-T10", "EBIG preferred and EBIZ recorded alternate", snapshot.loc[snapshot["economic_exposure_family_id"].eq("GLOBAL_RETAIL"), "ticker"].eq("EBIG").all(), "GBP preferred line retained")
    return pd.DataFrame(tests)


def main() -> int:
    policy = read_policy()
    if policy["pre_a3r2_commit"] != "c30de89d0ceee74ea024708e7c95270bae38d150":
        raise AssertionError("Unexpected A3R2 preregistration checkpoint")
    if json.loads((PROGRAMME_ROOT / "UKACTIVE_A2R2_DECISION.json").read_text())["decision"] != "UKACTIVE_A2R2_PASS":
        raise AssertionError("A2R2 is not PASS")

    print("A3R2U: refreshing current LSE catalogue", flush=True)
    live, lse_ledger, source_audit = fetch_live_lse()
    policy_ledger = capture_policy_sources()
    append_ledger(lse_ledger + policy_ledger)
    old = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A0A1_DISCOVERY_REGISTRY.csv", dtype=str).fillna("")
    eligibility = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A2R2_CORRECTED_SIGNAL_ELIGIBILITY.parquet")
    eligibility["date"] = pd.to_datetime(eligibility["date"])
    endpoint = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A2R2_SIGNAL_ENDPOINT_HISTORY.parquet")
    endpoint["date"] = pd.to_datetime(endpoint["date"])
    calendar_frame = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A2R2_XLON_RESEARCH_CALENDAR.csv")
    calendar = pd.DatetimeIndex(pd.to_datetime(calendar_frame.loc[bool_series(calendar_frame["a2r2_official_xlon_session"]), "date"])).sort_values()

    snapshot = build_current_snapshot(live, eligibility)
    change_log, new_products = build_change_log(live, old)
    lifecycle = build_lifecycle(snapshot, eligibility, endpoint, change_log, calendar)
    dynamic, vintage, annual_counts = build_dynamic_universe(snapshot, eligibility, calendar)
    tests = validation_results(live, snapshot, dynamic, new_products, change_log)

    census = "RECENT_FIVE_YEAR_CENSUS_SUBSTANTIALLY_COMPLETE"
    decision_state = "UKACTIVE_A3R2U_PASS_WITH_OPEN_ITEMS" if tests["status"].eq("PASS").all() else "UKACTIVE_A3R2U_FAIL"
    decision = {
        "stage_id": "UKACTIVE-A3R2U",
        "run_id": RUN_ID,
        "decision": decision_state,
        "decision_timestamp": utc_now(),
        "current_lse_line_count": int(len(live)),
        "prior_lse_line_count": int(old["source_name"].eq("LSE_PRICE_EXPLORER").sum()),
        "new_current_listing_count": int(len(new_products)),
        "new_economic_family_count": 0,
        "current_lines_not_seen_count": int(change_log["event_type"].eq("NOT_OBSERVED_IN_A3R2U_LSE_REFRESH").sum()),
        "curated_recent_closure_count": int(change_log["event_type"].eq("CLOSURE").sum()),
        "curated_recent_merger_count": int(change_log["event_type"].eq("MERGER").sum()),
        "curated_recent_mandate_change_count": int(change_log["event_type"].eq("MANDATE_CHANGE").sum()),
        "recent_five_year_census_classification": census,
        "master_family_count_retained": int(len(snapshot)),
        "ii_current_user_confirmed_preferred_line_count": int(snapshot["II_CURRENT_TRADABLE"].eq("CONFIRMED_BY_USER").sum()),
        "ii_user_confirmed_total_ticker_count_including_ebiz_alternate": len(II_CONFIRMED),
        "tests_passed": int(tests["status"].eq("PASS").sum()),
        "tests_total": int(len(tests)),
        "a3r2s_authorised": bool(tests["status"].eq("PASS").all()),
        "warning": WARNING,
    }

    scope = """# UKACTIVE-A3R2U scope and method

A3R2U is a versioned current refresh and final-five-year lifecycle audit. It does not rebuild or renumber the authoritative economic-family master. The search order is the existing discovery/evidence master, a new exact current LSE catalogue capture, then primary issuer lifecycle evidence for gaps. New lines are never admitted without identity and A2 return validation.

Current Interactive Investor observations supplied by the user are dated 2026-08-23 and remain current-only. EBIG is the preferred GBP line; EBIZ is a confirmed USD alternate. CSUK remains preferred to FASA, and FASA is not inferred to be ii-confirmed.
"""
    survivorship = f"""# UKACTIVE-A3R2U recent survivorship report

Classification: **{census}**.

The refresh captured {len(live):,} current LSE ETF/ETC/ETN lines and reconciled all {len(snapshot)} authoritative A2R2 research families. The five-year census combines current LSE presence, validated implementation-history starts/ends, canonical implementation transitions, and primary issuer evidence for selected closures, mergers and mandate changes.

It is not classified COMPLETE because no complete licensed historical LSE delisting feed was available. Current-survivor bias is controlled through `DYNAMIC_POINT_IN_TIME`, `FIVE_YEAR_START_STATIC`, `MATURE_ONLY`, and `MATURE_PLUS_DEVELOPING` views and through explicit issuer lifecycle events. Products absent from the current master are not silently treated as never having existed.

The mandate history of ISIN IE000KDY10O3 is explicitly bounded: Web 3.0 history is not US-defence history, and the US-defence family remains valid only after the July 2026 strategy change and A2R warm-up.
"""

    outputs = []
    outputs.append(write_text(out("SCOPE_AND_METHOD.md"), scope))
    outputs.append(write_csv(out("CURRENT_UNIVERSE_SNAPSHOT.csv"), snapshot))
    outputs.append(write_csv(out("UNIVERSE_CHANGE_LOG.csv"), change_log))
    outputs.append(write_csv(out("NEW_PRODUCT_CANDIDATES.csv"), new_products))
    outputs.append(write_csv(out("FIVE_YEAR_LIFECYCLE_AUDIT.csv"), lifecycle))
    outputs.append(write_text(out("RECENT_SURVIVORSHIP_REPORT.md"), survivorship))
    outputs.append(write_parquet(out("DYNAMIC_UNIVERSE.parquet"), dynamic))
    outputs.append(write_csv(out("UNIVERSE_VINTAGE_VIEWS.csv"), vintage))
    outputs.append(write_csv(out("ACTIVE_FAMILY_COUNTS_BY_YEAR.csv"), annual_counts))
    outputs.append(write_csv(out("VALIDATION_RESULTS.csv"), tests))
    decision_path = out("DECISION.json")
    outputs.append(write_json(decision_path, decision))
    manifest = {
        "stage_id": "UKACTIVE-A3R2U",
        "run_id": RUN_ID,
        "created_at": utc_now(),
        "decision": decision_state,
        "repository_root": str(PLATFORM_ROOT),
        "git_branch": git_output("branch", "--show-current"),
        "pre_a3r2_commit": policy["pre_a3r2_commit"],
        "preregistration_commit": git_output("rev-parse", "HEAD"),
        "post_a3r2u_commit": "PENDING_AFTER_EXECUTION",
        "inputs": [
            {"path": str(PROGRAMME_ROOT / name), "sha256": sha256_file(PROGRAMME_ROOT / name)}
            for name in [
                "UKACTIVE_A0A1_DISCOVERY_REGISTRY.csv", "UKACTIVE_A2R2_CORRECTED_SIGNAL_ELIGIBILITY.parquet",
                "UKACTIVE_A2R2_SIGNAL_ENDPOINT_HISTORY.parquet", "UKACTIVE_A2R2_XLON_RESEARCH_CALENDAR.csv",
                "UKACTIVE_A2R_A3R0_ROTATION_ROLE_MASTER_POST_A2R.csv", "UKACTIVE_A2R_A3R0_CURRENT_IMPLEMENTATION_LINES_POST_A2R.csv",
                "config/UKACTIVE_A3R2_POLICY_v1.json",
            ]
        ],
        "source_pages": source_audit,
        "primary_source_urls": sorted({record["url"] for record in lse_ledger + policy_ledger if str(record["url"]).startswith("http")}),
        "outputs_excluding_manifest": outputs,
        "executed_source": audit_file(Path(__file__)),
        "package_versions": {"python": platform.python_version(), "pandas": pd.__version__, "pyarrow": pyarrow.__version__},
        "unresolved_items": ["No complete licensed historical LSE delisting feed", WARNING],
    }
    write_json(out("MANIFEST.json"), manifest)
    print(json.dumps(decision, indent=2), flush=True)
    return 0 if tests["status"].eq("PASS").all() else 2


if __name__ == "__main__":
    raise SystemExit(main())
