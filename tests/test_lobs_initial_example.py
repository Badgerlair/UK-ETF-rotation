"""Fidelity and non-authority checks for the initial 2026-08-11 draft."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from edge_lobs.errors import LobsError
from edge_lobs.jsonio import load_json_object
from edge_lobs.validation import (
    validate_import_manifest_document,
    validate_observation_document,
)


EXAMPLE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "observations"
    / "leadership_rotation"
    / "examples"
    / "2026-08-11"
)


def _documents() -> tuple[dict, dict]:
    observation = load_json_object(EXAMPLE_ROOT / "observation_batch.json")
    manifest = load_json_object(EXAMPLE_ROOT / "import_manifest.template.json")
    return observation, manifest


def test_initial_example_is_only_a_non_authoritative_draft_template() -> None:
    observation, manifest = _documents()
    assert observation["validation_status"] == "AWAITING_RAW_SOURCES_AND_PROVENANCE"
    assert manifest["validation_status"] == "AWAITING_RAW_SOURCES_AND_PROVENANCE"
    assert observation["information_cutoff_timestamp"] is None
    assert observation["information_cutoff_timezone"] is None
    assert observation["recorded_at"] is None

    with pytest.raises(LobsError, match="DRAFT_NOT_IMPORT_ADMISSIBLE"):
        validate_observation_document(observation)
    with pytest.raises(LobsError, match="TEMPLATE_NOT_IMPORT_ADMISSIBLE"):
        validate_import_manifest_document(manifest, observation)

    observation_report = validate_observation_document(observation, allow_draft=True)
    manifest_report = validate_import_manifest_document(
        manifest, observation, allow_template=True
    )
    assert observation_report.state == "DRAFT_STRUCTURALLY_ACCEPTED_NON_AUTHORITATIVE"
    assert manifest_report.state == "TEMPLATE_STRUCTURALLY_ACCEPTED_NON_AUTHORITATIVE"
    assert "not validated, admissible, sealed, or imported" in observation["notes"]
    assert "does not claim validation, sealing, admissibility, or ingestion" in manifest["notes"]


def test_all_missing_raw_source_provenance_is_explicitly_null() -> None:
    observation, manifest = _documents()
    expected_types = {"PDF", "SCREENSHOT", "WEB_METADATA"}
    assert {source["source_type"] for source in manifest["sources"]} == expected_types
    assert {source["source_id"] for source in manifest["sources"]} == set(
        observation["source_ids"]
    )
    nullable_provenance = {
        "source_original_filename",
        "source_identity",
        "path",
        "source_capture_timestamp",
        "source_publication_timestamp",
        "source_publication_date",
        "timestamp_precision",
        "timezone",
        "historical_reconstruction",
        "contemporaneous_capture_attested",
        "expected_sha256",
        "parser_version",
    }
    for source in manifest["sources"]:
        assert all(source[key] is None for key in nullable_provenance)
        assert source["capture_mode"] == "PROSPECTIVE"


def test_supplied_market_instrument_and_group_observations_are_preserved() -> None:
    observation, _ = _documents()
    assert len(observation["market"]) == 19
    market_text = {record["source_text"] for record in observation["market"]}
    assert {
        "Trend: 4 of 4 UP",
        "10 EMA: up",
        "21 EMA: up",
        "50 SMA: up",
        "200 SMA: up",
        "Market is building as new leaders emerge.",
        "Bios and software, especially cyber, acting well.",
        "Semiconductors acting weak.",
        "Be ready for anything.",
        "Current View: Building up the right side",
        "Short term: Range building",
        "Intermediate Term: Consolidation",
        "Longer Term: Uptrend",
        "Bios have momentum",
        "Software has momentum",
        "Oil and gas perking up",
        "Miners perking up",
        "Semis took shots today",
        "Watch whether semis can become positive ex-breakers",
    } == market_text

    assert len(observation["instruments"]) == 7
    instrument_assertions = Counter(
        (record["instrument"], record["source_text"])
        for record in observation["instruments"]
    )
    assert instrument_assertions == Counter(
        {
            ("QQQ", "Building under this level"): 1,
            ("IWM", "Building a handle"): 1,
            ("IBIT", "Coiling but longer term downtrend still"): 2,
            ("SMH", "Down off the level"): 1,
            ("IGV", "Reconfirmation up"): 1,
            ("XBI", "Good bar moving up the right side of this base"): 1,
        }
    )

    assert len(observation["groups"]) == 11
    group_pairs = {
        (record["group_name"], record["source_text"])
        for record in observation["groups"]
    }
    assert {
        ("Bios", "Bios and software, especially cyber, acting well."),
        ("Software", "Bios and software, especially cyber, acting well."),
        ("Cyber", "Bios and software, especially cyber, acting well."),
        ("Semiconductors", "Semiconductors acting weak."),
        ("Bios", "Bios have momentum"),
        ("Software", "Software has momentum"),
        ("Oil and gas", "Oil and gas perking up"),
        ("Miners", "Miners perking up"),
        ("Semis", "Semis took shots today"),
        ("Semis", "Watch whether semis can become positive ex-breakers"),
        ("Semis", "Semis weak today"),
    } == group_pairs
    assert all(record["taxonomy_origin"] == "SOURCE_TAXONOMY" for record in observation["groups"])


def test_all_supplied_stock_watchlist_and_focus_assertions_are_preserved() -> None:
    observation, _ = _documents()
    expected_by_ticker = {
        "TSLA": ["Inside day"],
        "META": ["Downside reversal"],
        "MSFT": ["Fade off highs, could use a rest"],
        "AAPL": ["Gap down, decent close"],
        "AMZN": ["Building post gap"],
        "GOOG": ["Pulling in still to the 21"],
        "NVDA": ["Break lower", "Semis weak today", "Want this to build above the gap area"],
        "SPCX": ["Some follow through"],
        "SNDK": ["Inside", "Below MAs"],
        "MU": ["Stronger than SNDK", "Double inside at the 21", "Below the 50", "MU"],
        "BE": ["Leaking lower"],
        "AMD": ["Leaking lower below the 21"],
        "DELL": ["Fade at the pivot"],
        "CRWD": ["Reconfirmation"],
        "DDOG": ["Strong push into the gap"],
        "NET": ["Reversal"],
        "LLY": ["Strong follow through"],
        "TXG": ["Strong follow through", "Testing 2023 levels"],
        "BSP": ["Strong push", "New software name"],
        "FSLY": ["Strong push with DDOG"],
        "AEHR": ["Watching for a range re-breakout", "Not a great close but stronger than most semis", "AEHR"],
        "SYRE": ["Watching for a range breakout"],
        "ANET": ["Watching for a range breakout"],
        "ARWR": ["Watching for a range breakout"],
        "COMP": ["Watching for a flag breakout"],
        "FTNT": ["Watching for a range breakout"],
        "GM": ["Watching for a range breakout / push off the level"],
        "HRMY": ["Watching for a range breakout"],
        "KNSA": ["Watching for a range breakout", "KNSA"],
        "KYMR": ["Watching for a range breakout"],
        "OKTA": ["Watching for a range breakout", "Lagging other cybers"],
        "TENB": ["Watching for re-breakout"],
    }
    actual_by_ticker: dict[str, list[str]] = {}
    for record in observation["stocks"]:
        actual_by_ticker.setdefault(record["ticker"], []).append(record["source_text"])
        assert record["security_id"] is None
        assert record["identity_resolution_status"] == "UNRESOLVED"
    assert len(observation["stocks"]) == 44
    assert set(actual_by_ticker) == set(expected_by_ticker)
    for ticker, expected in expected_by_ticker.items():
        assert Counter(actual_by_ticker[ticker]) == Counter(expected)

    watchlist_tickers = {
        record["ticker"]
        for record in observation["stocks"]
        if record["source_role"] == "WATCHLIST"
    }
    assert watchlist_tickers == {
        "AEHR", "SYRE", "ANET", "ARWR", "COMP", "FTNT", "GM",
        "HRMY", "KNSA", "KYMR", "OKTA", "TENB",
    }
    focus = [
        record["ticker"]
        for record in observation["stocks"]
        if record["source_role"] == "FOCUS_LIST"
    ]
    assert focus == ["AEHR", "MU", "KNSA"]


def test_futures_values_preserve_display_precision_and_italy_local_time() -> None:
    observation, _ = _documents()
    actual = [
        (row["instrument"], row["value"], row["change_percent"])
        for row in observation["futures_snapshot"]
    ]
    assert actual == [
        ("US 30", "53,965.6", "-0.02%"),
        ("US 500", "7,763.8", "+0.14%"),
        ("US Tech 100", "29,726.4", "+0.35%"),
        ("Small Cap 2000", "3,025.6", "+0.27%"),
        ("S&P 500 VIX", "16.90", "-0.34%"),
    ]
    for row in observation["futures_snapshot"]:
        assert row["observation_timestamp"] == "2026-08-11T07:02:00+02:00"
        assert row["timezone"] == "Europe/Rome"
        assert row["timestamp_precision"] == "APPROXIMATE_MINUTE"
        assert row["source_type"] == "SCREENSHOT"
        assert row["change_absolute"] is None


def test_article_is_title_metadata_only_and_all_records_keep_source_origin() -> None:
    observation, _ = _documents()
    assert observation["macro_context"] == [
        {
            "observation_id": "EDGE-LOBS-OBS-20260811-MAC-001",
            "timestamp": None,
            "timezone": None,
            "derivation_type": "SOURCE_DERIVED",
            "observation_subtype": None,
            "source_text": "Asian stocks mixed as Korea gains, China slips; RBA decision in focus",
            "source_id": "EDGE-LOBS-SRC-20260811-INVESTING-ARTICLE",
            "source_location": None,
            "confidence_of_extraction": "UNKNOWN",
            "capture_mode": "PROSPECTIVE",
            "notes": "Article title metadata only; no body content or macro interpretation supplied.",
            "context_type": "ARTICLE_METADATA",
            "title": "Asian stocks mixed as Korea gains, China slips; RBA decision in focus",
            "description": None,
        }
    ]
    all_records = [
        record
        for name in (
            "market", "instruments", "groups", "stocks", "futures_snapshot", "macro_context"
        )
        for record in observation[name]
    ]
    assert len(all_records) == 87
    assert len({record["observation_id"] for record in all_records}) == 87
    assert all(record["derivation_type"] == "SOURCE_DERIVED" for record in all_records)
    assert all(record["capture_mode"] == "PROSPECTIVE" for record in all_records)
