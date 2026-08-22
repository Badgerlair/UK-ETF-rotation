"""Deterministic synthetic MDM fixtures for Project EDGE Milestone 3.

The fixture deliberately contains no empirical market evidence.  It is a small,
fixed safety fixture for point-in-time, identity, corporate-action, universe,
admissibility, and deterministic-replay tests.

Only the Python standard library and DuckDB are used.  The factory writes CSV
source tables plus a manifest into a caller-supplied pytest ``tmp_path``.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import duckdb


FIXTURE_ID = "EDGE_M3_PIT_001"
FIXTURE_CLASSIFICATION = "TEST_ONLY_NON_PRODUCTION"
SOURCE_AUTHORITY = "MDM"
AUTHORISATION_STATUS = "AUTHORISED"
MDM_SNAPSHOT_ID = "MDM-FIXTURE-001"
EDGE_SNAPSHOT_ID = "EDGE-FIXTURE-001"

SUPPORTED_MUTATIONS = frozenset(
    {
        "wrong_source",
        "row_count",
        "hash",
        "future_bar",
        "non_session_bar",
        "ambiguous_identity",
        "missing_terminal",
        "duplicate_sector",
        "outcome_column",
        "reversed_order",
    }
)


@dataclass(frozen=True)
class FixtureBundle:
    """Paths and parsed metadata for one generated fixture."""

    root: Path
    manifest_path: Path
    table_paths: Mapping[str, Path]
    manifest: Mapping[str, Any]

    def table_path(self, table_name: str) -> Path:
        """Return a table path or raise a useful key error."""

        return self.table_paths[table_name]


def _column(
    name: str,
    logical_type: str,
    *,
    nullable: bool = False,
    semantic_role: str = "OBSERVABLE",
) -> dict[str, Any]:
    return {
        "name": name,
        "logical_type": logical_type,
        "nullable": nullable,
        "semantic_role": semantic_role,
    }


BASE_SCHEMAS: dict[str, tuple[dict[str, Any], ...]] = {
    "identity_lifecycle": (
        _column("record_id", "string"),
        _column("record_kind", "string"),
        _column("security_id", "string"),
        _column("issuer_id", "string"),
        _column("listing_id", "string"),
        _column("exchange_id", "string"),
        _column("currency", "string"),
        _column("security_type", "string"),
        _column("share_class", "string"),
        _column("ticker", "string", nullable=True),
        _column("effective_from", "timestamp_utc"),
        _column("effective_to", "timestamp_utc", nullable=True),
        _column("lifecycle_state", "string", nullable=True),
        _column("available_at", "timestamp_utc"),
        _column("revision_of", "string", nullable=True),
        _column("mdm_vintage_id", "string"),
    ),
    "exchange_sessions": (
        _column("calendar_id", "string"),
        _column("calendar_version", "string"),
        _column("exchange_id", "string"),
        _column("session_date", "date"),
        _column("timezone", "string"),
        _column("utc_offset_minutes", "int64"),
        _column("session_state", "string"),
        _column("is_trading_session", "boolean"),
        _column("open_at", "timestamp_utc", nullable=True),
        _column("close_at", "timestamp_utc", nullable=True),
        _column("cutoff_at", "timestamp_utc", nullable=True),
        _column("early_close", "boolean"),
        _column("previous_session_date", "date", nullable=True),
        _column("next_session_date", "date", nullable=True),
        _column("available_at", "timestamp_utc"),
        _column("mdm_vintage_id", "string"),
    ),
    "daily_observations": (
        _column("security_id", "string"),
        _column("listing_id", "string"),
        _column("exchange_id", "string"),
        _column("session_date", "date"),
        _column("open", "decimal(18,6)"),
        _column("high", "decimal(18,6)"),
        _column("low", "decimal(18,6)"),
        _column("close", "decimal(18,6)"),
        _column("volume", "int64"),
        _column("currency", "string"),
        _column("trade_state", "string"),
        _column("available_at", "timestamp_utc"),
        _column("mdm_vintage_id", "string"),
    ),
    "corporate_actions": (
        _column("action_id", "string"),
        _column("security_id", "string"),
        _column("listing_id", "string"),
        _column("action_type", "string"),
        _column("published_at", "timestamp_utc"),
        _column("available_at", "timestamp_utc"),
        _column("effective_at", "timestamp_utc"),
        _column("currency", "string", nullable=True),
        _column("new_shares_per_old_share", "decimal(18,6)", nullable=True),
        _column("post_price_equivalence_multiplier", "decimal(18,6)", nullable=True),
        _column("cash_per_share", "decimal(18,6)", nullable=True),
        _column("terminal_cash_per_share", "decimal(18,6)", nullable=True),
        _column("action_status", "string"),
        _column("action_version", "int64"),
        _column("mdm_vintage_id", "string"),
    ),
    "universe_membership": (
        _column("security_id", "string"),
        _column("listing_id", "string"),
        _column("exchange_id", "string"),
        _column("session_date", "date"),
        _column("lifecycle_state", "string"),
        _column("candidate", "boolean"),
        _column("eligible", "boolean"),
        _column("reason_code", "string", nullable=True),
        _column("universe_policy_version", "string"),
        _column("research_cutoff", "timestamp_utc"),
        _column("mdm_vintage_id", "string"),
    ),
    "sector_history": (
        _column("record_id", "string"),
        _column("security_id", "string"),
        _column("classification_system", "string"),
        _column("sector", "string"),
        _column("published_at", "timestamp_utc"),
        _column("available_at", "timestamp_utc"),
        _column("effective_from", "timestamp_utc"),
        _column("effective_to", "timestamp_utc", nullable=True),
        _column("mdm_vintage_id", "string"),
    ),
    "index_membership": (
        _column("record_id", "string"),
        _column("security_id", "string"),
        _column("index_id", "string"),
        _column("published_at", "timestamp_utc"),
        _column("available_at", "timestamp_utc"),
        _column("effective_from", "timestamp_utc"),
        _column("effective_to", "timestamp_utc", nullable=True),
        _column("is_member", "boolean"),
        _column("mdm_vintage_id", "string"),
    ),
    "fundamentals": (
        _column("record_id", "string"),
        _column("security_id", "string"),
        _column("metric", "string"),
        _column("fiscal_period_end", "date"),
        _column("value", "decimal(18,6)"),
        _column("unit", "string"),
        _column("published_at", "timestamp_utc"),
        _column("available_at", "timestamp_utc"),
        _column("revision_number", "int64"),
        _column("revision_of", "string", nullable=True),
        _column("mdm_vintage_id", "string"),
    ),
}


def _identity_rows() -> list[dict[str, str]]:
    common = {
        "currency": "USD",
        "security_type": "COMMON_STOCK",
        "share_class": "A",
        "mdm_vintage_id": MDM_SNAPSHOT_ID,
    }
    return [
        {
            **common,
            "record_id": "ID-S1",
            "record_kind": "IDENTITY",
            "security_id": "S1",
            "issuer_id": "I1",
            "listing_id": "L1",
            "exchange_id": "XEQ",
            "ticker": "",
            "effective_from": "2024-01-01T14:30:00Z",
            "effective_to": "",
            "lifecycle_state": "",
            "available_at": "2024-01-01T00:00:00Z",
            "revision_of": "",
        },
        {
            **common,
            "record_id": "ID-S2",
            "record_kind": "IDENTITY",
            "security_id": "S2",
            "issuer_id": "I2",
            "listing_id": "L2",
            "exchange_id": "XEQ",
            "ticker": "",
            "effective_from": "2024-03-14T13:30:00Z",
            "effective_to": "",
            "lifecycle_state": "",
            "available_at": "2024-03-14T13:30:00Z",
            "revision_of": "",
        },
        {
            **common,
            "record_id": "ID-S3",
            "record_kind": "IDENTITY",
            "security_id": "S3",
            "issuer_id": "I3",
            "listing_id": "L3",
            "exchange_id": "XEQ",
            "ticker": "",
            "effective_from": "2024-01-01T14:30:00Z",
            "effective_to": "",
            "lifecycle_state": "",
            "available_at": "2024-01-01T00:00:00Z",
            "revision_of": "",
        },
        {
            **common,
            "record_id": "SYM-S1-ARC-V1",
            "record_kind": "SYMBOL",
            "security_id": "S1",
            "issuer_id": "I1",
            "listing_id": "L1",
            "exchange_id": "XEQ",
            "ticker": "ARC",
            "effective_from": "2024-01-01T14:30:00Z",
            "effective_to": "",
            "lifecycle_state": "",
            "available_at": "2024-01-01T00:00:00Z",
            "revision_of": "",
        },
        {
            **common,
            "record_id": "SYM-S1-ARC-V2",
            "record_kind": "SYMBOL",
            "security_id": "S1",
            "issuer_id": "I1",
            "listing_id": "L1",
            "exchange_id": "XEQ",
            "ticker": "ARC",
            "effective_from": "2024-01-01T14:30:00Z",
            "effective_to": "2024-03-12T13:30:00Z",
            "lifecycle_state": "",
            "available_at": "2024-03-11T12:00:00Z",
            "revision_of": "SYM-S1-ARC-V1",
        },
        {
            **common,
            "record_id": "SYM-S1-NOVA",
            "record_kind": "SYMBOL",
            "security_id": "S1",
            "issuer_id": "I1",
            "listing_id": "L1",
            "exchange_id": "XEQ",
            "ticker": "NOVA",
            "effective_from": "2024-03-12T13:30:00Z",
            "effective_to": "",
            "lifecycle_state": "",
            "available_at": "2024-03-11T12:00:00Z",
            "revision_of": "",
        },
        {
            **common,
            "record_id": "SYM-S2-ARC",
            "record_kind": "SYMBOL",
            "security_id": "S2",
            "issuer_id": "I2",
            "listing_id": "L2",
            "exchange_id": "XEQ",
            "ticker": "ARC",
            "effective_from": "2024-03-14T13:30:00Z",
            "effective_to": "",
            "lifecycle_state": "",
            "available_at": "2024-03-14T13:30:00Z",
            "revision_of": "",
        },
        {
            **common,
            "record_id": "SYM-S3-FALL",
            "record_kind": "SYMBOL",
            "security_id": "S3",
            "issuer_id": "I3",
            "listing_id": "L3",
            "exchange_id": "XEQ",
            "ticker": "FALL",
            "effective_from": "2024-01-01T14:30:00Z",
            "effective_to": "2024-03-15T13:30:00Z",
            "lifecycle_state": "",
            "available_at": "2024-01-01T00:00:00Z",
            "revision_of": "",
        },
        {
            **common,
            "record_id": "LIFE-S1-ACTIVE",
            "record_kind": "LIFECYCLE",
            "security_id": "S1",
            "issuer_id": "I1",
            "listing_id": "L1",
            "exchange_id": "XEQ",
            "ticker": "",
            "effective_from": "2024-01-01T14:30:00Z",
            "effective_to": "",
            "lifecycle_state": "ACTIVE",
            "available_at": "2024-01-01T00:00:00Z",
            "revision_of": "",
        },
        {
            **common,
            "record_id": "LIFE-S2-ACTIVE",
            "record_kind": "LIFECYCLE",
            "security_id": "S2",
            "issuer_id": "I2",
            "listing_id": "L2",
            "exchange_id": "XEQ",
            "ticker": "",
            "effective_from": "2024-03-14T13:30:00Z",
            "effective_to": "",
            "lifecycle_state": "ACTIVE",
            "available_at": "2024-03-14T13:30:00Z",
            "revision_of": "",
        },
        {
            **common,
            "record_id": "LIFE-S3-ACTIVE-V1",
            "record_kind": "LIFECYCLE",
            "security_id": "S3",
            "issuer_id": "I3",
            "listing_id": "L3",
            "exchange_id": "XEQ",
            "ticker": "",
            "effective_from": "2024-01-01T14:30:00Z",
            "effective_to": "",
            "lifecycle_state": "ACTIVE",
            "available_at": "2024-01-01T00:00:00Z",
            "revision_of": "",
        },
        {
            **common,
            "record_id": "LIFE-S3-ACTIVE-V2",
            "record_kind": "LIFECYCLE",
            "security_id": "S3",
            "issuer_id": "I3",
            "listing_id": "L3",
            "exchange_id": "XEQ",
            "ticker": "",
            "effective_from": "2024-01-01T14:30:00Z",
            "effective_to": "2024-03-15T13:30:00Z",
            "lifecycle_state": "ACTIVE",
            "available_at": "2024-03-14T18:01:00Z",
            "revision_of": "LIFE-S3-ACTIVE-V1",
        },
        {
            **common,
            "record_id": "LIFE-S3-DELISTED",
            "record_kind": "LIFECYCLE",
            "security_id": "S3",
            "issuer_id": "I3",
            "listing_id": "L3",
            "exchange_id": "XEQ",
            "ticker": "",
            "effective_from": "2024-03-15T13:30:00Z",
            "effective_to": "",
            "lifecycle_state": "DELISTED",
            "available_at": "2024-03-14T18:01:00Z",
            "revision_of": "",
        },
    ]


def _calendar_rows() -> list[dict[str, str]]:
    rows = [
        ("2024-03-07", -300, "REGULAR_BOUNDARY", True, "14:30", "21:00", "21:05", "", "2024-03-08", False),
        ("2024-03-08", -300, "REGULAR", True, "14:30", "21:00", "21:05", "2024-03-07", "2024-03-11", False),
        ("2024-03-11", -240, "REGULAR", True, "13:30", "20:00", "20:05", "2024-03-08", "2024-03-12", False),
        ("2024-03-12", -240, "REGULAR", True, "13:30", "20:00", "20:05", "2024-03-11", "2024-03-14", False),
        ("2024-03-13", -240, "HOLIDAY", False, "", "", "", "2024-03-12", "2024-03-14", False),
        ("2024-03-14", -240, "EARLY_CLOSE", True, "13:30", "17:00", "17:05", "2024-03-12", "2024-03-15", True),
        ("2024-03-15", -240, "REGULAR", True, "13:30", "20:00", "20:05", "2024-03-14", "2024-03-18", False),
        ("2024-03-18", -240, "REGULAR", True, "13:30", "20:00", "20:05", "2024-03-15", "2024-03-19", False),
        ("2024-03-19", -240, "REGULAR_BOUNDARY", True, "13:30", "20:00", "20:05", "2024-03-18", "", False),
    ]
    result: list[dict[str, str]] = []
    for date, offset, state, trading, opened, closed, cutoff, previous, following, early in rows:
        timestamp = lambda value: f"{date}T{value}:00Z" if value else ""
        result.append(
            {
                "calendar_id": "XEQ",
                "calendar_version": "XEQ-CAL-001",
                "exchange_id": "XEQ",
                "session_date": date,
                "timezone": "America/New_York",
                "utc_offset_minutes": str(offset),
                "session_state": state,
                "is_trading_session": str(trading).lower(),
                "open_at": timestamp(opened),
                "close_at": timestamp(closed),
                "cutoff_at": timestamp(cutoff),
                "early_close": str(early).lower(),
                "previous_session_date": previous,
                "next_session_date": following,
                "available_at": "2024-01-01T00:00:00Z",
                "mdm_vintage_id": MDM_SNAPSHOT_ID,
            }
        )
    return result


def _daily_rows() -> list[dict[str, str]]:
    values = [
        ("2024-03-08", "S1", "L1", "98", "101", "97", "100", "1000", "2024-03-08T21:05:00Z"),
        ("2024-03-11", "S1", "L1", "100", "102", "99", "100", "1100", "2024-03-11T20:05:00Z"),
        ("2024-03-12", "S1", "L1", "50", "52", "49", "51", "2200", "2024-03-12T20:05:00Z"),
        ("2024-03-14", "S1", "L1", "51", "53", "50", "52", "2100", "2024-03-14T17:05:00Z"),
        ("2024-03-15", "S1", "L1", "51", "52", "50", "51", "2000", "2024-03-15T20:05:00Z"),
        ("2024-03-18", "S1", "L1", "51", "54", "51", "53", "2300", "2024-03-18T20:05:00Z"),
        ("2024-03-14", "S2", "L2", "20", "21", "19", "20", "500", "2024-03-14T17:05:00Z"),
        ("2024-03-15", "S2", "L2", "20", "22", "20", "21", "550", "2024-03-15T20:05:00Z"),
        ("2024-03-18", "S2", "L2", "21", "23", "21", "22", "600", "2024-03-18T20:05:00Z"),
        ("2024-03-08", "S3", "L3", "12", "12", "11", "12", "300", "2024-03-08T21:05:00Z"),
        ("2024-03-11", "S3", "L3", "12", "12", "10", "11", "350", "2024-03-11T20:05:00Z"),
        ("2024-03-12", "S3", "L3", "11", "12", "10", "11", "320", "2024-03-12T20:05:00Z"),
        ("2024-03-14", "S3", "L3", "11", "11", "9", "10", "400", "2024-03-14T17:05:00Z"),
    ]
    return [
        {
            "session_date": date,
            "security_id": security,
            "listing_id": listing,
            "exchange_id": "XEQ",
            "open": opened,
            "high": high,
            "low": low,
            "close": closed,
            "volume": volume,
            "currency": "USD",
            "trade_state": "TRADED",
            "available_at": available,
            "mdm_vintage_id": MDM_SNAPSHOT_ID,
        }
        for date, security, listing, opened, high, low, closed, volume, available in values
    ]


def _corporate_action_rows() -> list[dict[str, str]]:
    return [
        {
            "action_id": "A-SPLIT",
            "security_id": "S1",
            "listing_id": "L1",
            "action_type": "SPLIT",
            "published_at": "2024-03-08T14:59:00Z",
            "available_at": "2024-03-08T15:00:00Z",
            "effective_at": "2024-03-12T13:30:00Z",
            "currency": "",
            "new_shares_per_old_share": "2",
            "post_price_equivalence_multiplier": "2",
            "cash_per_share": "",
            "terminal_cash_per_share": "",
            "action_status": "CONFIRMED",
            "action_version": "1",
            "mdm_vintage_id": MDM_SNAPSHOT_ID,
        },
        {
            "action_id": "A-DIV",
            "security_id": "S1",
            "listing_id": "L1",
            "action_type": "CASH_DISTRIBUTION",
            "published_at": "2024-03-12T15:00:00Z",
            "available_at": "2024-03-12T15:01:00Z",
            "effective_at": "2024-03-15T13:30:00Z",
            "currency": "USD",
            "new_shares_per_old_share": "",
            "post_price_equivalence_multiplier": "",
            "cash_per_share": "1",
            "terminal_cash_per_share": "",
            "action_status": "CONFIRMED",
            "action_version": "1",
            "mdm_vintage_id": MDM_SNAPSHOT_ID,
        },
        {
            "action_id": "A-DEL",
            "security_id": "S3",
            "listing_id": "L3",
            "action_type": "TERMINAL_DELISTING",
            "published_at": "2024-03-14T18:00:00Z",
            "available_at": "2024-03-14T18:01:00Z",
            "effective_at": "2024-03-15T13:30:00Z",
            "currency": "USD",
            "new_shares_per_old_share": "",
            "post_price_equivalence_multiplier": "",
            "cash_per_share": "",
            "terminal_cash_per_share": "2",
            "action_status": "CONFIRMED",
            "action_version": "1",
            "mdm_vintage_id": MDM_SNAPSHOT_ID,
        },
    ]


def _universe_rows() -> list[dict[str, str]]:
    cutoffs = {
        "2024-03-08": "2024-03-08T21:05:00Z",
        "2024-03-11": "2024-03-11T20:05:00Z",
        "2024-03-12": "2024-03-12T20:05:00Z",
        "2024-03-14": "2024-03-14T17:05:00Z",
        "2024-03-15": "2024-03-15T20:05:00Z",
        "2024-03-18": "2024-03-18T20:05:00Z",
    }
    states = {
        "S1": {
            date: ("ACTIVE", True, True, "") for date in cutoffs
        },
        "S2": {
            "2024-03-08": ("PRE_LISTING", False, False, "PRE_LISTING"),
            "2024-03-11": ("PRE_LISTING", False, False, "PRE_LISTING"),
            "2024-03-12": ("PRE_LISTING", False, False, "PRE_LISTING"),
            "2024-03-14": ("ACTIVE", True, True, ""),
            "2024-03-15": ("ACTIVE", True, True, ""),
            "2024-03-18": ("ACTIVE", True, True, ""),
        },
        "S3": {
            "2024-03-08": ("ACTIVE", True, True, ""),
            "2024-03-11": ("ACTIVE", True, True, ""),
            "2024-03-12": ("ACTIVE", True, True, ""),
            "2024-03-14": ("ACTIVE", True, True, ""),
            "2024-03-15": ("DELISTED", True, False, "TERMINAL_SETTLEMENT_ONLY"),
            "2024-03-18": ("DELISTED", False, False, "POST_DELISTING"),
        },
    }
    listing_ids = {"S1": "L1", "S2": "L2", "S3": "L3"}
    result: list[dict[str, str]] = []
    for security_id in ("S1", "S2", "S3"):
        for session_date in cutoffs:
            lifecycle, candidate, eligible, reason = states[security_id][session_date]
            result.append(
                {
                    "security_id": security_id,
                    "listing_id": listing_ids[security_id],
                    "exchange_id": "XEQ",
                    "session_date": session_date,
                    "lifecycle_state": lifecycle,
                    "candidate": str(candidate).lower(),
                    "eligible": str(eligible).lower(),
                    "reason_code": reason,
                    "universe_policy_version": "UP-001",
                    "research_cutoff": cutoffs[session_date],
                    "mdm_vintage_id": MDM_SNAPSHOT_ID,
                }
            )
    return result


def _sector_rows() -> list[dict[str, str]]:
    return [
        {
            "record_id": "C1",
            "security_id": "S1",
            "classification_system": "EDGE-SYNTHETIC-SECTOR",
            "sector": "TECH",
            "published_at": "2024-01-01T00:00:00Z",
            "available_at": "2024-01-01T00:00:00Z",
            "effective_from": "2024-01-01T00:00:00Z",
            "effective_to": "2024-03-14T13:30:00Z",
            "mdm_vintage_id": MDM_SNAPSHOT_ID,
        },
        {
            "record_id": "C2",
            "security_id": "S1",
            "classification_system": "EDGE-SYNTHETIC-SECTOR",
            "sector": "HEALTH",
            "published_at": "2024-03-12T21:00:00Z",
            "available_at": "2024-03-12T21:01:00Z",
            "effective_from": "2024-03-14T13:30:00Z",
            "effective_to": "",
            "mdm_vintage_id": MDM_SNAPSHOT_ID,
        },
    ]


def _index_rows() -> list[dict[str, str]]:
    return [
        {
            "record_id": "M1",
            "security_id": "S1",
            "index_id": "IDX100",
            "published_at": "2024-03-11T20:59:00Z",
            "available_at": "2024-03-11T21:00:00Z",
            "effective_from": "2024-03-15T13:30:00Z",
            "effective_to": "",
            "is_member": "true",
            "mdm_vintage_id": MDM_SNAPSHOT_ID,
        }
    ]


def _fundamental_rows() -> list[dict[str, str]]:
    return [
        {
            "record_id": "F1-V1",
            "security_id": "S1",
            "metric": "EPS",
            "fiscal_period_end": "2023-12-31",
            "value": "1.00",
            "unit": "USD_PER_SHARE",
            "published_at": "2024-03-11T21:00:00Z",
            "available_at": "2024-03-12T13:00:00Z",
            "revision_number": "1",
            "revision_of": "",
            "mdm_vintage_id": MDM_SNAPSHOT_ID,
        },
        {
            "record_id": "F1-V2",
            "security_id": "S1",
            "metric": "EPS",
            "fiscal_period_end": "2023-12-31",
            "value": "0.80",
            "unit": "USD_PER_SHARE",
            "published_at": "2024-03-18T12:00:00Z",
            "available_at": "2024-03-18T12:05:00Z",
            "revision_number": "2",
            "revision_of": "F1-V1",
            "mdm_vintage_id": MDM_SNAPSHOT_ID,
        },
    ]


def _base_tables() -> dict[str, list[dict[str, str]]]:
    return {
        "identity_lifecycle": _identity_rows(),
        "exchange_sessions": _calendar_rows(),
        "daily_observations": _daily_rows(),
        "corporate_actions": _corporate_action_rows(),
        "universe_membership": _universe_rows(),
        "sector_history": _sector_rows(),
        "index_membership": _index_rows(),
        "fundamentals": _fundamental_rows(),
    }


def _normalise_mutations(mutations: str | Iterable[str] | None) -> tuple[str, ...]:
    if mutations is None:
        result: tuple[str, ...] = ()
    elif isinstance(mutations, str):
        result = (mutations,)
    else:
        result = tuple(sorted(set(mutations)))
    unknown = set(result) - SUPPORTED_MUTATIONS
    if unknown:
        raise ValueError(f"Unsupported fixture mutation(s): {sorted(unknown)}")
    return result


def _apply_data_mutations(
    tables: dict[str, list[dict[str, str]]],
    schemas: dict[str, list[dict[str, Any]]],
    mutations: Sequence[str],
) -> None:
    if "future_bar" in mutations:
        tables["daily_observations"].append(
            {
                "security_id": "S1",
                "listing_id": "L1",
                "exchange_id": "XEQ",
                "session_date": "2024-03-19",
                "open": "53",
                "high": "55",
                "low": "52",
                "close": "54",
                "volume": "2400",
                "currency": "USD",
                "trade_state": "TRADED",
                "available_at": "2024-03-19T20:05:00Z",
                "mdm_vintage_id": MDM_SNAPSHOT_ID,
            }
        )

    if "non_session_bar" in mutations:
        tables["daily_observations"].append(
            {
                "security_id": "S1",
                "listing_id": "L1",
                "exchange_id": "XEQ",
                "session_date": "2024-03-13",
                "open": "51",
                "high": "52",
                "low": "50",
                "close": "51",
                "volume": "1000",
                "currency": "USD",
                "trade_state": "TRADED",
                "available_at": "2024-03-13T20:05:00Z",
                "mdm_vintage_id": MDM_SNAPSHOT_ID,
            }
        )

    if "ambiguous_identity" in mutations:
        common = {
            "security_id": "S4",
            "issuer_id": "I4",
            "listing_id": "L4",
            "exchange_id": "XEQ",
            "currency": "USD",
            "security_type": "COMMON_STOCK",
            "share_class": "A",
            "effective_to": "",
            "available_at": "2024-03-14T13:30:00Z",
            "revision_of": "",
            "mdm_vintage_id": MDM_SNAPSHOT_ID,
        }
        tables["identity_lifecycle"].extend(
            [
                {
                    **common,
                    "record_id": "ID-S4",
                    "record_kind": "IDENTITY",
                    "ticker": "",
                    "effective_from": "2024-03-14T13:30:00Z",
                    "lifecycle_state": "",
                },
                {
                    **common,
                    "record_id": "SYM-S4-ARC",
                    "record_kind": "SYMBOL",
                    "ticker": "ARC",
                    "effective_from": "2024-03-14T13:30:00Z",
                    "lifecycle_state": "",
                },
                {
                    **common,
                    "record_id": "LIFE-S4-ACTIVE",
                    "record_kind": "LIFECYCLE",
                    "ticker": "",
                    "effective_from": "2024-03-14T13:30:00Z",
                    "lifecycle_state": "ACTIVE",
                },
            ]
        )

    if "missing_terminal" in mutations:
        tables["corporate_actions"] = [
            row for row in tables["corporate_actions"] if row["action_id"] != "A-DEL"
        ]

    if "duplicate_sector" in mutations:
        duplicate = dict(next(row for row in tables["sector_history"] if row["record_id"] == "C2"))
        duplicate["record_id"] = "C2-B"
        duplicate["sector"] = "FIN"
        tables["sector_history"].append(duplicate)

    if "outcome_column" in mutations:
        schemas["daily_observations"].append(
            _column(
                "forward_total_return_1_session",
                "decimal(18,6)",
                nullable=True,
                semantic_role="OUTCOME",
            )
        )
        for row in tables["daily_observations"]:
            row["forward_total_return_1_session"] = "0.100000" if (
                row["security_id"] == "S1" and row["session_date"] == "2024-03-08"
            ) else ""

    if "reversed_order" in mutations:
        for rows in tables.values():
            rows.reverse()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _schema_fingerprint(table_name: str, schema: Sequence[Mapping[str, Any]]) -> str:
    return _sha256_bytes(_canonical_json({"table": table_name, "columns": list(schema)}))


def _canonical_rows_fingerprint(
    rows: Sequence[Mapping[str, str]], columns: Sequence[str]
) -> str:
    canonical_rows = sorted(tuple(row.get(column, "") for column in columns) for row in rows)
    return _sha256_bytes(_canonical_json({"columns": list(columns), "rows": canonical_rows}))


def _write_csv(
    path: Path,
    columns: Sequence[str],
    rows: Sequence[Mapping[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(
            target,
            fieldnames=list(columns),
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


DUCKDB_TYPE_MAP = {
    "string": "VARCHAR",
    "date": "DATE",
    "timestamp_utc": "TIMESTAMPTZ",
    "decimal(18,6)": "DECIMAL(18,6)",
    "int64": "BIGINT",
    "boolean": "BOOLEAN",
}


def _duckdb_validate_csv(
    path: Path, schema: Sequence[Mapping[str, Any]]
) -> tuple[int, tuple[str, ...]]:
    """Validate that DuckDB reads every value under the declared logical schema."""

    declared_types = {
        str(column["name"]): DUCKDB_TYPE_MAP[str(column["logical_type"])]
        for column in schema
    }
    with path.open("r", encoding="utf-8", newline="") as source:
        header = tuple(next(csv.reader(source)))

    connection = duckdb.connect(database=":memory:")
    try:
        relation = connection.read_csv(
            str(path),
            header=True,
            columns=declared_types,
        )
        row_count = int(relation.aggregate("count(*) AS row_count").fetchone()[0])
    finally:
        connection.close()
    return row_count, header


def _scientific_expectations() -> dict[str, Any]:
    feature_ready_keys = [
        ["2024-03-08", "S1"],
        ["2024-03-08", "S3"],
        ["2024-03-11", "S1"],
        ["2024-03-11", "S3"],
        ["2024-03-12", "S1"],
        ["2024-03-12", "S3"],
        ["2024-03-14", "S1"],
        ["2024-03-14", "S2"],
        ["2024-03-14", "S3"],
        ["2024-03-15", "S1"],
        ["2024-03-15", "S2"],
        ["2024-03-15", "S3"],
        ["2024-03-18", "S1"],
        ["2024-03-18", "S2"],
    ]
    return {
        "requested_sessions": [
            "2024-03-08",
            "2024-03-11",
            "2024-03-12",
            "2024-03-14",
            "2024-03-15",
            "2024-03-18",
        ],
        "universe_counts": {
            "assessment_rows": 18,
            "candidate_security_days": 14,
            "eligible_security_days": 13,
            "candidate_but_ineligible": 1,
            "non_candidate_assessments": 4,
            "feature_ready_rows": 14,
            "raw_bar_rows": 13,
            "terminal_rows_without_bar": 1,
            "distinct_securities": 3,
            "distinct_sessions": 6,
        },
        "feature_ready_keys": feature_ready_keys,
        "identity_resolution": {
            "ARC_at_2024_03_11_cutoff": "S1",
            "S1_ticker_at_2024_03_11_cutoff": "ARC",
            "S1_ticker_at_2024_03_12_cutoff": "NOVA",
            "ARC_at_2024_03_15_cutoff": "S2",
        },
        "point_in_time": {
            "S1_sector_at_2024_03_12_cutoff": "TECH",
            "S1_sector_at_2024_03_14_cutoff": "HEALTH",
            "S1_IDX100_at_2024_03_14_cutoff": False,
            "S1_IDX100_at_2024_03_15_cutoff": True,
            "S1_EPS_at_2024_03_11_cutoff": None,
            "S1_EPS_at_2024_03_12_cutoff": "1.00",
            "S1_EPS_at_2024_03_14_cutoff": "1.00",
            "S1_EPS_at_2024_03_18_cutoff": "0.80",
        },
        "return_expectations": {
            "split_raw_close_return": "-0.490000000000",
            "split_consistent_price_return": "0.020000000000",
            "split_consistent_volume": "1100",
            "distribution_price_return": "-0.019230769231",
            "distribution_return": "0.019230769231",
            "distribution_total_return": "0.000000000000",
            "terminal_total_return": "-0.800000000000",
            "comparison_tolerance": "0.000000000001",
        },
    }


def build_edge_m3_pit_001(
    tmp_path: str | Path,
    *,
    mutations: str | Iterable[str] | None = None,
) -> FixtureBundle:
    """Build the deterministic EDGE_M3_PIT_001 fixture beneath ``tmp_path``.

    A clean fixture uses ``mutations=None``.  Each named mutation is a controlled
    fault intended for one fail-closed test.  Existing destinations are never
    overwritten.
    """

    selected_mutations = _normalise_mutations(mutations)
    suffix = "" if not selected_mutations else "__" + "__".join(selected_mutations)
    root = Path(tmp_path).resolve() / f"{FIXTURE_ID}{suffix}"
    root.mkdir(parents=True, exist_ok=False)

    tables = _base_tables()
    schemas = {
        name: [dict(column) for column in schema]
        for name, schema in BASE_SCHEMAS.items()
    }
    _apply_data_mutations(tables, schemas, selected_mutations)

    table_paths: dict[str, Path] = {}
    table_manifest: dict[str, Any] = {}
    for table_name in sorted(tables):
        schema = schemas[table_name]
        columns = [str(column["name"]) for column in schema]
        path = root / f"{table_name}.csv"
        _write_csv(path, columns, tables[table_name])
        duckdb_row_count, parsed_header = _duckdb_validate_csv(path, schema)
        if parsed_header != tuple(columns):
            raise AssertionError(
                f"Written header for {table_name} differs from its declared schema"
            )
        table_paths[table_name] = path
        table_manifest[table_name] = {
            "classification": FIXTURE_CLASSIFICATION,
            "relative_path": path.name,
            "row_count": duckdb_row_count,
            "columns": columns,
            "required_columns": columns,
            "schema": schema,
            "schema_fingerprint_sha256": _schema_fingerprint(table_name, schema),
            "content_sha256": _sha256_file(path),
            "canonical_rows_sha256": _canonical_rows_fingerprint(
                tables[table_name], columns
            ),
        }

    manifest: dict[str, Any] = {
        "fixture_id": FIXTURE_ID,
        "fixture_version": "1.0.0",
        "classification": FIXTURE_CLASSIFICATION,
        "production_use_permitted": False,
        "contains_empirical_market_data": False,
        "source_authority": "NOT_MDM" if "wrong_source" in selected_mutations else SOURCE_AUTHORITY,
        "authorisation_status": AUTHORISATION_STATUS,
        "authorisation_scope": "TEST_ONLY_SYNTHETIC_FIXTURE",
        "mdm_snapshot_id": MDM_SNAPSHOT_ID,
        "edge_snapshot_id": EDGE_SNAPSHOT_ID,
        "mutations": list(selected_mutations),
        "scope": {
            "exchange_id": "XEQ",
            "timezone": "America/New_York",
            "start_session": "2024-03-08",
            "end_session": "2024-03-18",
            "observation_clock": "DAILY_CLOSE_PLUS_FIVE_MINUTES",
            "effective_interval_semantics": "HALF_OPEN",
            "output_order": ["session_date", "security_id"],
        },
        "policy_versions": {
            "universe": "UP-001",
            "point_in_time_join": "PIT-001",
            "corporate_action": "CA-001",
            "feature_ready_schema": "FR-001",
        },
        "scientific_use": {
            "admissible_clean_scope": "DAILY_PRICE_PATH_TESTING",
            "optional_capabilities": [
                "SECTOR_SENTINEL_NOT_ACTIVATED",
                "INDEX_SENTINEL_NOT_ACTIVATED",
                "FUNDAMENTAL_SENTINEL_NOT_ACTIVATED",
            ],
        },
        "scientific_expectations": _scientific_expectations(),
        "tables": table_manifest,
    }

    if "row_count" in selected_mutations:
        manifest["tables"]["daily_observations"]["row_count"] += 1
    if "hash" in selected_mutations:
        manifest["tables"]["daily_observations"]["content_sha256"] = "0" * 64

    manifest_path = root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=True, allow_nan=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return FixtureBundle(
        root=root,
        manifest_path=manifest_path,
        table_paths=table_paths,
        manifest=manifest,
    )


def build_fixture(
    tmp_path: str | Path,
    *,
    mutations: str | Iterable[str] | None = None,
) -> FixtureBundle:
    """Short alias for :func:`build_edge_m3_pit_001`."""

    return build_edge_m3_pit_001(tmp_path, mutations=mutations)


def load_manifest(path_or_directory: str | Path) -> dict[str, Any]:
    """Load a generated fixture manifest."""

    path = Path(path_or_directory)
    manifest_path = path if path.name == "manifest.json" else path / "manifest.json"
    with manifest_path.open("r", encoding="utf-8") as source:
        return json.load(source)


def verify_fixture(path_or_directory: str | Path) -> tuple[str, ...]:
    """Return deterministic structural/integrity error codes for a fixture.

    Scientific sentinel mutations such as ``future_bar`` remain structurally
    valid and are intentionally left for the corresponding scientific validator.
    """

    path = Path(path_or_directory)
    root = path.parent if path.name == "manifest.json" else path
    manifest = load_manifest(path)
    errors: list[str] = []

    if manifest.get("classification") != FIXTURE_CLASSIFICATION:
        errors.append("FIXTURE_CLASSIFICATION_MISSING")
    if manifest.get("production_use_permitted") is not False:
        errors.append("PRODUCTION_USE_FLAG_INVALID")
    if manifest.get("source_authority") != SOURCE_AUTHORITY:
        errors.append("SOURCE_AUTHORITY_INVALID")
    if manifest.get("authorisation_status") != AUTHORISATION_STATUS:
        errors.append("AUTHORISATION_STATUS_INVALID")

    for table_name in sorted(manifest.get("tables", {})):
        entry = manifest["tables"][table_name]
        table_path = root / entry["relative_path"]
        prefix = table_name.upper()
        if not table_path.is_file():
            errors.append(f"{prefix}_FILE_MISSING")
            continue

        schema = entry["schema"]
        expected_columns = tuple(entry["columns"])
        try:
            actual_count, actual_header = _duckdb_validate_csv(table_path, schema)
        except Exception:
            errors.append(f"{prefix}_DUCKDB_SCHEMA_INVALID")
            continue

        if actual_header != expected_columns:
            errors.append(f"{prefix}_COLUMN_ORDER_MISMATCH")
        if not set(entry["required_columns"]).issubset(actual_header):
            errors.append(f"{prefix}_REQUIRED_COLUMNS_MISSING")
        if actual_count != entry["row_count"]:
            errors.append(f"{prefix}_ROW_COUNT_MISMATCH")
        if _schema_fingerprint(table_name, schema) != entry["schema_fingerprint_sha256"]:
            errors.append(f"{prefix}_SCHEMA_FINGERPRINT_MISMATCH")
        if _sha256_file(table_path) != entry["content_sha256"]:
            errors.append(f"{prefix}_CONTENT_HASH_MISMATCH")

        with table_path.open("r", encoding="utf-8", newline="") as source:
            rows = list(csv.DictReader(source))
        if _canonical_rows_fingerprint(rows, actual_header) != entry["canonical_rows_sha256"]:
            errors.append(f"{prefix}_CANONICAL_ROWS_HASH_MISMATCH")

    return tuple(errors)


__all__ = [
    "AUTHORISATION_STATUS",
    "EDGE_SNAPSHOT_ID",
    "FIXTURE_CLASSIFICATION",
    "FIXTURE_ID",
    "FixtureBundle",
    "MDM_SNAPSHOT_ID",
    "SOURCE_AUTHORITY",
    "SUPPORTED_MUTATIONS",
    "build_edge_m3_pit_001",
    "build_fixture",
    "load_manifest",
    "verify_fixture",
]


# ---------------------------------------------------------------------------
# Strict Parquet fixture for the real source-boundary integration tests.
# ---------------------------------------------------------------------------

CANONICAL_PARQUET_MUTATIONS = frozenset(
    {
        "wrong_hash",
        "wrong_row_count",
        "wrong_physical_type",
        "mutable_snapshot_id",
        "path_escape",
        "future_bar",
        "non_session_bar",
        "duplicate_bar",
        "ambiguous_identity",
        "unknown_lifecycle",
        "listing_security_drift",
        "listing_currency_drift",
        "orphan_membership",
        "missing_terminal",
        "late_action",
        "future_action_revision",
        "action_listing_drift",
        "action_revision_out_of_range",
        "action_currency_mismatch",
        "null_cash_amount",
        "unsupported_complex_action",
        "terminal_bar_conflict",
        "compound_terminal_action",
        "late_cutoff",
        "bar_revision",
        "bar_future_revision",
        "halted_no_bar",
        "mixed_vintage",
        "outcome_column",
        "reversed_input",
    }
)


def _canonical_source_rows() -> dict[str, list[dict[str, Any]]]:
    vintage = "MDM-FIXTURE-001"
    identities = [
        {
            "source_record_id": "ID-S1-ARC",
            "mdm_vintage_id": vintage,
            "security_id": "S1",
            "issuer_id": "I1",
            "listing_id": "L1",
            "ticker": "ARC",
            "exchange_id": "XEQ",
            "currency": "USD",
            "security_type": "COMMON_STOCK",
            "share_class": "A",
            "primary_listing": True,
            "lifecycle_state": "ACTIVE",
            "effective_from": "2024-01-01T14:30:00Z",
            "effective_to": "2024-03-12T13:30:00Z",
            "published_at": "2024-01-01T00:00:00Z",
            "available_at": "2024-01-01T00:00:00Z",
            "quality_state": "PASSED",
        },
        {
            "source_record_id": "ID-S1-NOVA",
            "mdm_vintage_id": vintage,
            "security_id": "S1",
            "issuer_id": "I1",
            "listing_id": "L1",
            "ticker": "NOVA",
            "exchange_id": "XEQ",
            "currency": "USD",
            "security_type": "COMMON_STOCK",
            "share_class": "A",
            "primary_listing": True,
            "lifecycle_state": "ACTIVE",
            "effective_from": "2024-03-12T13:30:00Z",
            "effective_to": None,
            "published_at": "2024-03-11T11:59:00Z",
            "available_at": "2024-03-11T12:00:00Z",
            "quality_state": "PASSED",
        },
        {
            "source_record_id": "ID-S2-ARC",
            "mdm_vintage_id": vintage,
            "security_id": "S2",
            "issuer_id": "I2",
            "listing_id": "L2",
            "ticker": "ARC",
            "exchange_id": "XEQ",
            "currency": "USD",
            "security_type": "COMMON_STOCK",
            "share_class": "A",
            "primary_listing": True,
            "lifecycle_state": "ACTIVE",
            "effective_from": "2024-03-14T13:30:00Z",
            "effective_to": None,
            "published_at": "2024-03-14T13:29:00Z",
            "available_at": "2024-03-14T13:30:00Z",
            "quality_state": "PASSED",
        },
        {
            "source_record_id": "ID-S3-FALL",
            "mdm_vintage_id": vintage,
            "security_id": "S3",
            "issuer_id": "I3",
            "listing_id": "L3",
            "ticker": "FALL",
            "exchange_id": "XEQ",
            "currency": "USD",
            "security_type": "COMMON_STOCK",
            "share_class": "A",
            "primary_listing": True,
            "lifecycle_state": "ACTIVE",
            "effective_from": "2024-01-01T14:30:00Z",
            "effective_to": "2024-03-15T13:30:00Z",
            "published_at": "2024-01-01T00:00:00Z",
            "available_at": "2024-01-01T00:00:00Z",
            "quality_state": "PASSED",
        },
        {
            "source_record_id": "ID-S3-DELISTED",
            "mdm_vintage_id": vintage,
            "security_id": "S3",
            "issuer_id": "I3",
            "listing_id": "L3",
            "ticker": "FALL",
            "exchange_id": "XEQ",
            "currency": "USD",
            "security_type": "COMMON_STOCK",
            "share_class": "A",
            "primary_listing": True,
            "lifecycle_state": "DELISTED",
            "effective_from": "2024-03-15T13:30:00Z",
            "effective_to": None,
            "published_at": "2024-03-14T18:00:00Z",
            "available_at": "2024-03-14T18:01:00Z",
            "quality_state": "PASSED",
        },
    ]

    calendar_values = [
        ("2024-03-08", "REGULAR", "2024-03-08T14:30:00Z", "2024-03-08T21:00:00Z", "2024-03-08T21:05:00Z", False, "2024-03-07", "2024-03-11"),
        ("2024-03-11", "REGULAR", "2024-03-11T13:30:00Z", "2024-03-11T20:00:00Z", "2024-03-11T20:05:00Z", False, "2024-03-08", "2024-03-12"),
        ("2024-03-12", "REGULAR", "2024-03-12T13:30:00Z", "2024-03-12T20:00:00Z", "2024-03-12T20:05:00Z", False, "2024-03-11", "2024-03-14"),
        ("2024-03-13", "HOLIDAY", None, None, None, False, "2024-03-12", "2024-03-14"),
        ("2024-03-14", "EARLY_CLOSE", "2024-03-14T13:30:00Z", "2024-03-14T17:00:00Z", "2024-03-14T17:05:00Z", True, "2024-03-12", "2024-03-15"),
        ("2024-03-15", "REGULAR", "2024-03-15T13:30:00Z", "2024-03-15T20:00:00Z", "2024-03-15T20:05:00Z", False, "2024-03-14", "2024-03-18"),
        ("2024-03-18", "REGULAR", "2024-03-18T13:30:00Z", "2024-03-18T20:00:00Z", "2024-03-18T20:05:00Z", False, "2024-03-15", "2024-03-19"),
    ]
    sessions = [
        {
            "source_record_id": f"CAL-XEQ-{session_date}",
            "mdm_vintage_id": vintage,
            "exchange_id": "XEQ",
            "calendar_id": "XEQ-CAL-001",
            "session_date": session_date,
            "timezone": "America/New_York",
            "open_at": open_at,
            "close_at": close_at,
            "cutoff_at": cutoff_at,
            "early_close": early,
            "session_state": state,
            "previous_session_date": previous,
            "next_session_date": following,
            "available_at": "2024-01-01T00:00:00Z",
            "quality_state": "PASSED",
        }
        for session_date, state, open_at, close_at, cutoff_at, early, previous, following in calendar_values
    ]

    daily_values = [
        ("2024-03-08", "L1", "98", "101", "97", "100", 1000, "2024-03-08T21:05:00Z"),
        ("2024-03-11", "L1", "100", "102", "99", "100", 1100, "2024-03-11T20:05:00Z"),
        ("2024-03-12", "L1", "50", "52", "49", "51", 2200, "2024-03-12T20:05:00Z"),
        ("2024-03-14", "L1", "51", "53", "50", "52", 2100, "2024-03-14T17:05:00Z"),
        ("2024-03-15", "L1", "51", "52", "50", "51", 2000, "2024-03-15T20:05:00Z"),
        ("2024-03-18", "L1", "51", "54", "51", "53", 2300, "2024-03-18T20:05:00Z"),
        ("2024-03-14", "L2", "20", "21", "19", "20", 500, "2024-03-14T17:05:00Z"),
        ("2024-03-15", "L2", "20", "22", "20", "21", 550, "2024-03-15T20:05:00Z"),
        ("2024-03-18", "L2", "21", "23", "21", "22", 600, "2024-03-18T20:05:00Z"),
        ("2024-03-08", "L3", "12", "12", "11", "12", 300, "2024-03-08T21:05:00Z"),
        ("2024-03-11", "L3", "12", "12", "10", "11", 350, "2024-03-11T20:05:00Z"),
        ("2024-03-12", "L3", "11", "12", "10", "11", 320, "2024-03-12T20:05:00Z"),
        ("2024-03-14", "L3", "11", "11", "9", "10", 400, "2024-03-14T17:05:00Z"),
    ]
    observations = [
        {
            "source_record_id": f"OBS-{listing_id}-{session_date}",
            "mdm_vintage_id": vintage,
            "listing_id": listing_id,
            "session_date": session_date,
            "open": opened,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "currency": "USD",
            "price_basis": "RAW_UNADJUSTED",
            "observation_state": "TRADED",
            "available_at": available_at,
            "value_state": "PRESENT",
            "quality_state": "PASSED",
        }
        for session_date, listing_id, opened, high, low, close, volume, available_at in daily_values
    ]

    actions = [
        {
            "source_record_id": "ACT-SPLIT-001",
            "mdm_vintage_id": vintage,
            "action_id": "A-SPLIT",
            "listing_id": "L1",
            "action_type": "SPLIT",
            "action_status": "CONFIRMED",
            "announcement_at": "2024-03-08T14:58:00Z",
            "published_at": "2024-03-08T14:59:00Z",
            "available_at": "2024-03-08T15:00:00Z",
            "ex_date": "2024-03-12",
            "effective_at": "2024-03-12T13:30:00Z",
            "split_ratio": "2",
            "cash_amount": None,
            "currency": None,
            "terminal_consideration": None,
            "successor_listing_id": None,
            "timestamp_precision": "EXACT",
            "quality_state": "PASSED",
        },
        {
            "source_record_id": "ACT-DIV-001",
            "mdm_vintage_id": vintage,
            "action_id": "A-DIV",
            "listing_id": "L1",
            "action_type": "CASH_DISTRIBUTION",
            "action_status": "CONFIRMED",
            "announcement_at": "2024-03-12T14:59:00Z",
            "published_at": "2024-03-12T15:00:00Z",
            "available_at": "2024-03-12T15:01:00Z",
            "ex_date": "2024-03-15",
            "effective_at": "2024-03-15T13:30:00Z",
            "split_ratio": None,
            "cash_amount": "1",
            "currency": "USD",
            "terminal_consideration": None,
            "successor_listing_id": None,
            "timestamp_precision": "EXACT",
            "quality_state": "PASSED",
        },
        {
            "source_record_id": "ACT-DEL-001",
            "mdm_vintage_id": vintage,
            "action_id": "A-DEL",
            "listing_id": "L3",
            "action_type": "TERMINAL_DELISTING",
            "action_status": "CONFIRMED",
            "announcement_at": "2024-03-14T17:59:00Z",
            "published_at": "2024-03-14T18:00:00Z",
            "available_at": "2024-03-14T18:01:00Z",
            "ex_date": "2024-03-15",
            "effective_at": "2024-03-15T13:30:00Z",
            "split_ratio": None,
            "cash_amount": None,
            "currency": "USD",
            "terminal_consideration": "2",
            "successor_listing_id": None,
            "timestamp_precision": "EXACT",
            "quality_state": "PASSED",
        },
    ]

    memberships = [
        {
            "source_record_id": f"UNIV-{listing_id}",
            "mdm_vintage_id": vintage,
            "universe_id": "EDGE-PRIMARY-EQUITY",
            "listing_id": listing_id,
            "membership_state": "INCLUDED",
            "effective_from": effective_from,
            "effective_to": None,
            "published_at": published_at,
            "available_at": available_at,
            "quality_state": "PASSED",
        }
        for listing_id, effective_from, published_at, available_at in (
            ("L1", "2024-01-01T14:30:00Z", "2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z"),
            ("L2", "2024-03-14T13:30:00Z", "2024-03-14T13:29:00Z", "2024-03-14T13:30:00Z"),
            ("L3", "2024-01-01T14:30:00Z", "2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z"),
        )
    ]
    return {
        "identity_lifecycle": identities,
        "exchange_sessions": sessions,
        "daily_observations": observations,
        "corporate_actions": actions,
        "universe_membership": memberships,
    }


def _write_parquet_table(
    connection: duckdb.DuckDBPyConnection,
    path: Path,
    rows: list[dict[str, Any]],
    columns_and_types: Mapping[str, str],
) -> None:
    column_sql = ", ".join(
        f'"{name}" {data_type}' for name, data_type in columns_and_types.items()
    )
    connection.execute(f"CREATE OR REPLACE TABLE fixture_table ({column_sql})")
    columns = tuple(columns_and_types)
    placeholders = ", ".join("?" for _ in columns)
    if rows:
        connection.executemany(
            f"INSERT INTO fixture_table VALUES ({placeholders})",
            [tuple(row.get(column) for column in columns) for row in rows],
        )
    connection.execute(
        "COPY fixture_table TO ? (FORMAT PARQUET, COMPRESSION ZSTD)", [str(path)]
    )


def build_canonical_parquet_fixture(
    tmp_path: str | Path,
    *,
    mutations: str | Iterable[str] | None = None,
) -> FixtureBundle:
    """Build a strict test-only Parquet snapshot accepted only with opt-in.

    This is the positive integration fixture for the production-shaped MDM
    boundary. It remains permanently classified as non-production.
    """

    from edge_mdm.contracts import (
        LOGICAL_ROWS_FINGERPRINT_VERSION,
        MANIFEST_SCHEMA_VERSION,
        REQUIRED_COLUMN_TYPES,
        REQUIRED_SORT_KEYS,
        SCHEMA_FINGERPRINT_VERSION,
        TEST_ONLY_NON_PRODUCTION,
        TEST_ONLY_NOT_AUTHORISED,
    )
    from edge_mdm.fingerprint import (
        logical_rows_fingerprint,
        schema_fingerprint,
        sha256_file,
    )

    selected = _normalise_canonical_mutations(mutations)
    suffix = "" if not selected else "__" + "__".join(selected)
    root = Path(tmp_path).resolve() / f"EDGE_M3_CANONICAL_PARQUET{suffix}"
    root.mkdir(parents=True, exist_ok=False)
    tables = _canonical_source_rows()

    if "future_bar" in selected:
        tables["daily_observations"][0]["available_at"] = "2024-03-11T20:05:01Z"
    if "non_session_bar" in selected:
        row = dict(tables["daily_observations"][0])
        row.update(
            source_record_id="OBS-L1-2024-03-13",
            session_date="2024-03-13",
            available_at="2024-03-13T20:05:00Z",
        )
        tables["daily_observations"].append(row)
    if "duplicate_bar" in selected:
        row = dict(tables["daily_observations"][0])
        row["source_record_id"] = "OBS-L1-2024-03-08-DUP"
        tables["daily_observations"].append(row)
    if "ambiguous_identity" in selected:
        row = dict(tables["identity_lifecycle"][2])
        row.update(
            source_record_id="ID-S4-ARC",
            security_id="S4",
            issuer_id="I4",
            listing_id="L4",
        )
        tables["identity_lifecycle"].append(row)
    if "unknown_lifecycle" in selected:
        tables["identity_lifecycle"][2]["lifecycle_state"] = "ACTVE"
    if "listing_security_drift" in selected:
        active = next(
            row
            for row in tables["identity_lifecycle"]
            if row["source_record_id"] == "ID-S1-NOVA"
        )
        active["effective_to"] = "2024-03-15T13:30:00Z"
        successor = dict(active)
        successor.update(
            source_record_id="ID-L1-SECURITY-DRIFT",
            security_id="S9",
            issuer_id="I9",
            effective_from="2024-03-15T13:30:00Z",
            effective_to=None,
            published_at="2024-03-14T18:00:00Z",
            available_at="2024-03-14T18:01:00Z",
        )
        tables["identity_lifecycle"].append(successor)
    if "listing_currency_drift" in selected:
        active = next(
            row
            for row in tables["identity_lifecycle"]
            if row["source_record_id"] == "ID-S1-NOVA"
        )
        active["effective_to"] = "2024-03-15T13:30:00Z"
        redenominated = dict(active)
        redenominated.update(
            source_record_id="ID-L1-CURRENCY-DRIFT",
            currency="EUR",
            effective_from="2024-03-15T13:30:00Z",
            effective_to=None,
            published_at="2024-03-14T18:00:00Z",
            available_at="2024-03-14T18:01:00Z",
        )
        tables["identity_lifecycle"].append(redenominated)
        for observation in tables["daily_observations"]:
            if (
                observation["listing_id"] == "L1"
                and observation["session_date"] >= "2024-03-15"
            ):
                observation["currency"] = "EUR"
        next(
            row
            for row in tables["corporate_actions"]
            if row["action_id"] == "A-DIV"
        )["currency"] = "EUR"
    if "orphan_membership" in selected:
        row = dict(tables["universe_membership"][0])
        row.update(
            source_record_id="UNIV-L999",
            listing_id="L999",
        )
        tables["universe_membership"].append(row)
    if "missing_terminal" in selected:
        tables["corporate_actions"] = [
            row
            for row in tables["corporate_actions"]
            if row["action_type"] != "TERMINAL_DELISTING"
        ]
    if "late_action" in selected:
        tables["corporate_actions"][0]["available_at"] = "2024-03-12T20:05:01Z"
    if "future_action_revision" in selected:
        original = next(
            row
            for row in tables["corporate_actions"]
            if row["action_id"] == "A-DIV"
        )
        revision = dict(original)
        revision.update(
            source_record_id="ACT-DIV-002-FUTURE",
            announcement_at="2024-03-16T11:58:00Z",
            published_at="2024-03-16T11:59:00Z",
            available_at="2024-03-16T12:00:00Z",
            cash_amount="2",
        )
        tables["corporate_actions"].append(revision)
    if "action_listing_drift" in selected:
        original = next(
            row
            for row in tables["corporate_actions"]
            if row["action_id"] == "A-DIV"
        )
        revision = dict(original)
        revision.update(
            source_record_id="ACT-DIV-002-LISTING-DRIFT",
            listing_id="L2",
            announcement_at="2024-03-12T15:02:00Z",
            published_at="2024-03-12T15:03:00Z",
            available_at="2024-03-12T15:04:00Z",
        )
        tables["corporate_actions"].append(revision)
    if "action_revision_out_of_range" in selected:
        revision = dict(tables["corporate_actions"][0])
        revision.update(
            source_record_id="ACT-SPLIT-002",
            action_status="CANCELLED",
            announcement_at="2024-03-10T12:00:00Z",
            published_at="2024-03-11T12:00:00Z",
            available_at="2024-03-11T12:01:00Z",
            ex_date="2024-04-01",
            effective_at="2024-04-01T13:30:00Z",
        )
        tables["corporate_actions"].append(revision)
    if "action_currency_mismatch" in selected:
        next(
            row
            for row in tables["corporate_actions"]
            if row["action_type"] == "CASH_DISTRIBUTION"
        )["currency"] = "EUR"
    if "null_cash_amount" in selected:
        next(
            row
            for row in tables["corporate_actions"]
            if row["action_type"] == "CASH_DISTRIBUTION"
        )["cash_amount"] = None
    if "unsupported_complex_action" in selected:
        action = next(
            row
            for row in tables["corporate_actions"]
            if row["action_type"] == "CASH_DISTRIBUTION"
        )
        action["action_type"] = "MERGER"
    if "terminal_bar_conflict" in selected:
        row = dict(tables["daily_observations"][-1])
        row.update(
            source_record_id="OBS-L3-2024-03-15-CONFLICT",
            session_date="2024-03-15",
            open="2",
            high="2",
            low="2",
            close="2",
            volume=100,
            available_at="2024-03-15T20:05:00Z",
        )
        tables["daily_observations"].append(row)
    if "compound_terminal_action" in selected:
        action = dict(tables["corporate_actions"][0])
        action.update(
            source_record_id="ACT-L3-SPLIT-TERMINAL-DATE",
            action_id="A-L3-SPLIT-TERMINAL-DATE",
            listing_id="L3",
            announcement_at="2024-03-14T16:00:00Z",
            published_at="2024-03-14T16:01:00Z",
            available_at="2024-03-14T16:02:00Z",
            ex_date="2024-03-15",
            effective_at="2024-03-15T13:30:00Z",
        )
        tables["corporate_actions"].append(action)
    if "late_cutoff" in selected:
        next(
            row
            for row in tables["exchange_sessions"]
            if row["session_date"] == "2024-03-11"
        )["cutoff_at"] = "2024-03-11T20:06:00Z"
    if "bar_revision" in selected:
        original = next(
            row
            for row in tables["daily_observations"]
            if row["listing_id"] == "L1" and row["session_date"] == "2024-03-11"
        )
        original["available_at"] = "2024-03-11T20:03:00Z"
        revision = dict(original)
        revision.update(
            source_record_id="OBS-L1-2024-03-11-REV2",
            close="101",
            high="103",
            available_at="2024-03-11T20:04:00Z",
        )
        tables["daily_observations"].append(revision)
    if "bar_future_revision" in selected:
        original = next(
            row
            for row in tables["daily_observations"]
            if row["listing_id"] == "L1" and row["session_date"] == "2024-03-11"
        )
        revision = dict(original)
        revision.update(
            source_record_id="OBS-L1-2024-03-11-FUTURE-REV",
            close="101",
            high="103",
            available_at="2024-03-11T20:06:00Z",
        )
        tables["daily_observations"].append(revision)
    if "halted_no_bar" in selected:
        active = next(
            row
            for row in tables["identity_lifecycle"]
            if row["source_record_id"] == "ID-S1-NOVA"
        )
        active["effective_to"] = "2024-03-14T13:30:00Z"
        halted = dict(active)
        halted.update(
            source_record_id="ID-S1-NOVA-HALTED",
            lifecycle_state="HALTED",
            effective_from="2024-03-14T13:30:00Z",
            effective_to="2024-03-15T13:30:00Z",
            published_at="2024-03-13T12:00:00Z",
            available_at="2024-03-13T12:01:00Z",
        )
        resumed = dict(active)
        resumed.update(
            source_record_id="ID-S1-NOVA-RESUMED",
            effective_from="2024-03-15T13:30:00Z",
            effective_to=None,
            published_at="2024-03-14T18:00:00Z",
            available_at="2024-03-14T18:01:00Z",
        )
        tables["identity_lifecycle"].extend([halted, resumed])
        tables["daily_observations"] = [
            row
            for row in tables["daily_observations"]
            if not (
                row["listing_id"] == "L1"
                and row["session_date"] == "2024-03-14"
            )
        ]
    if "mixed_vintage" in selected:
        tables["daily_observations"][0]["mdm_vintage_id"] = "MDM-FIXTURE-OTHER"
    if "reversed_input" in selected:
        for rows in tables.values():
            rows.reverse()

    table_paths: dict[str, Path] = {}
    table_manifests: list[dict[str, Any]] = []
    with duckdb.connect(database=":memory:") as connection:
        connection.execute("SET threads = 1")
        connection.execute("SET TimeZone = 'UTC'")
        for logical_name in sorted(tables):
            path = root / f"{logical_name}.parquet"
            schema = dict(REQUIRED_COLUMN_TYPES[logical_name])
            if "wrong_physical_type" in selected and logical_name == "daily_observations":
                schema["volume"] = "VARCHAR"
            if "outcome_column" in selected and logical_name == "daily_observations":
                schema["future_return_target"] = "DECIMAL(18,6)"
                for row in tables[logical_name]:
                    row["future_return_target"] = "0.1"
            _write_parquet_table(connection, path, tables[logical_name], schema)
            relation = connection.read_parquet(str(path))
            columns = tuple(str(name) for name in relation.columns)
            physical_types = tuple(str(kind) for kind in relation.types)
            order_clause = ", ".join(
                f'"{name}" ASC NULLS FIRST'
                for name in REQUIRED_SORT_KEYS[logical_name]
            )
            logical_projection = ", ".join(
                f'CAST("{name}" AS VARCHAR) AS "{name}"' for name in columns
            )
            cursor = connection.execute(
                f"SELECT {logical_projection} FROM read_parquet(?) ORDER BY {order_clause}",
                [str(path)],
            )
            logical = logical_rows_fingerprint(columns, cursor.fetchall())
            table_paths[logical_name] = path
            table_manifests.append(
                {
                    "logical_name": logical_name,
                    "relative_path": path.name,
                    "format": "parquet",
                    "schema_version": f"edge-{logical_name.replace('_', '-')}-v1",
                    "schema_fingerprint_version": SCHEMA_FINGERPRINT_VERSION,
                    "schema_sha256": schema_fingerprint(
                        zip(columns, physical_types, strict=True)
                    ),
                    "row_count": logical.row_count,
                    "sha256": sha256_file(path),
                    "logical_fingerprint_version": LOGICAL_ROWS_FINGERPRINT_VERSION,
                    "logical_sha256": logical.sha256,
                    "logical_sort_keys": list(REQUIRED_SORT_KEYS[logical_name]),
                    "complete": True,
                }
            )

    if "wrong_hash" in selected:
        next(
            table for table in table_manifests if table["logical_name"] == "daily_observations"
        )["sha256"] = "0" * 64
    if "wrong_row_count" in selected:
        next(
            table for table in table_manifests if table["logical_name"] == "daily_observations"
        )["row_count"] += 1

    manifest: dict[str, Any] = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "source_authority": "MDM",
        "source_kind": TEST_ONLY_NON_PRODUCTION,
        "authorisation_status": TEST_ONLY_NOT_AUTHORISED,
        "authorisation_scope_id": "EDGE-M3-SYNTHETIC-SAFETY-001",
        "snapshot_id": "MDM-FIXTURE-001",
        "source_version": "mdm-fixture-v1",
        "consistency_token": "mdm-fixture-consistency-001",
        "created_at_utc": "2024-03-21T00:00:00Z",
        "snapshot_cutoff_utc": "2024-03-20T23:59:59Z",
        "replayable": True,
        "complete": True,
        "tables": table_manifests,
    }
    if "mutable_snapshot_id" in selected:
        manifest["snapshot_id"] = "latest"
    if "path_escape" in selected:
        next(
            table
            for table in manifest["tables"]
            if table["logical_name"] == "daily_observations"
        )["relative_path"] = "../daily_observations.parquet"
    manifest_path = root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=True, allow_nan=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return FixtureBundle(root, manifest_path, table_paths, manifest)


def _normalise_canonical_mutations(
    mutations: str | Iterable[str] | None,
) -> tuple[str, ...]:
    if mutations is None:
        return ()
    values = (mutations,) if isinstance(mutations, str) else tuple(mutations)
    unknown = set(values) - CANONICAL_PARQUET_MUTATIONS
    if unknown:
        raise ValueError(f"Unsupported canonical mutation(s): {sorted(unknown)}")
    return tuple(sorted(set(values)))


__all__ += [
    "CANONICAL_PARQUET_MUTATIONS",
    "build_canonical_parquet_fixture",
]
