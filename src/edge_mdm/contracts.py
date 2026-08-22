"""Strict immutable contracts for an authorised MDM daily snapshot.

This module deliberately defines one bounded source contract. It is not a
vendor-adapter framework and it performs no field inference.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
import re
from typing import Any, Mapping

from .fingerprint import (
    LOGICAL_ROWS_FINGERPRINT_VERSION,
    SCHEMA_FINGERPRINT_VERSION,
)


MDM_SOURCE_AUTHORITY = "MDM"
MANIFEST_SCHEMA_VERSION = "edge-mdm-snapshot-manifest-v1"
MDM_PRODUCTION_SNAPSHOT = "MDM_PRODUCTION_SNAPSHOT"
TEST_ONLY_NON_PRODUCTION = "TEST_ONLY_NON_PRODUCTION"
AUTHORISED_FOR_PROJECT_EDGE_RESEARCH = "AUTHORISED_FOR_PROJECT_EDGE_RESEARCH"
TEST_ONLY_NOT_AUTHORISED = "TEST_ONLY_NOT_AUTHORISED"

REQUIRED_TABLES = frozenset(
    {
        "identity_lifecycle",
        "exchange_sessions",
        "daily_observations",
        "corporate_actions",
        "universe_membership",
    }
)

REQUIRED_TABLE_COLUMNS: Mapping[str, frozenset[str]] = {
    "identity_lifecycle": frozenset(
        {
            "source_record_id",
            "mdm_vintage_id",
            "security_id",
            "issuer_id",
            "listing_id",
            "ticker",
            "exchange_id",
            "currency",
            "security_type",
            "share_class",
            "primary_listing",
            "lifecycle_state",
            "effective_from",
            "effective_to",
            "published_at",
            "available_at",
            "quality_state",
        }
    ),
    "exchange_sessions": frozenset(
        {
            "source_record_id",
            "mdm_vintage_id",
            "exchange_id",
            "calendar_id",
            "session_date",
            "timezone",
            "open_at",
            "close_at",
            "cutoff_at",
            "early_close",
            "session_state",
            "previous_session_date",
            "next_session_date",
            "available_at",
            "quality_state",
        }
    ),
    "daily_observations": frozenset(
        {
            "source_record_id",
            "mdm_vintage_id",
            "listing_id",
            "session_date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "currency",
            "price_basis",
            "observation_state",
            "available_at",
            "value_state",
            "quality_state",
        }
    ),
    "corporate_actions": frozenset(
        {
            "source_record_id",
            "mdm_vintage_id",
            "action_id",
            "listing_id",
            "action_type",
            "action_status",
            "announcement_at",
            "published_at",
            "available_at",
            "ex_date",
            "effective_at",
            "split_ratio",
            "cash_amount",
            "currency",
            "terminal_consideration",
            "successor_listing_id",
            "timestamp_precision",
            "quality_state",
        }
    ),
    "universe_membership": frozenset(
        {
            "source_record_id",
            "mdm_vintage_id",
            "universe_id",
            "listing_id",
            "membership_state",
            "effective_from",
            "effective_to",
            "published_at",
            "available_at",
            "quality_state",
        }
    ),
}

# Exact DuckDB physical types for the bounded first-release input contract.
# A source cannot redefine a scientific field merely by changing both a file
# and its self-declared schema hash.
REQUIRED_COLUMN_TYPES: Mapping[str, Mapping[str, str]] = {
    "identity_lifecycle": {
        "source_record_id": "VARCHAR",
        "mdm_vintage_id": "VARCHAR",
        "security_id": "VARCHAR",
        "issuer_id": "VARCHAR",
        "listing_id": "VARCHAR",
        "ticker": "VARCHAR",
        "exchange_id": "VARCHAR",
        "currency": "VARCHAR",
        "security_type": "VARCHAR",
        "share_class": "VARCHAR",
        "primary_listing": "BOOLEAN",
        "lifecycle_state": "VARCHAR",
        "effective_from": "TIMESTAMP WITH TIME ZONE",
        "effective_to": "TIMESTAMP WITH TIME ZONE",
        "published_at": "TIMESTAMP WITH TIME ZONE",
        "available_at": "TIMESTAMP WITH TIME ZONE",
        "quality_state": "VARCHAR",
    },
    "exchange_sessions": {
        "source_record_id": "VARCHAR",
        "mdm_vintage_id": "VARCHAR",
        "exchange_id": "VARCHAR",
        "calendar_id": "VARCHAR",
        "session_date": "DATE",
        "timezone": "VARCHAR",
        "open_at": "TIMESTAMP WITH TIME ZONE",
        "close_at": "TIMESTAMP WITH TIME ZONE",
        "cutoff_at": "TIMESTAMP WITH TIME ZONE",
        "early_close": "BOOLEAN",
        "session_state": "VARCHAR",
        "previous_session_date": "DATE",
        "next_session_date": "DATE",
        "available_at": "TIMESTAMP WITH TIME ZONE",
        "quality_state": "VARCHAR",
    },
    "daily_observations": {
        "source_record_id": "VARCHAR",
        "mdm_vintage_id": "VARCHAR",
        "listing_id": "VARCHAR",
        "session_date": "DATE",
        "open": "DECIMAL(18,6)",
        "high": "DECIMAL(18,6)",
        "low": "DECIMAL(18,6)",
        "close": "DECIMAL(18,6)",
        "volume": "BIGINT",
        "currency": "VARCHAR",
        "price_basis": "VARCHAR",
        "observation_state": "VARCHAR",
        "available_at": "TIMESTAMP WITH TIME ZONE",
        "value_state": "VARCHAR",
        "quality_state": "VARCHAR",
    },
    "corporate_actions": {
        "source_record_id": "VARCHAR",
        "mdm_vintage_id": "VARCHAR",
        "action_id": "VARCHAR",
        "listing_id": "VARCHAR",
        "action_type": "VARCHAR",
        "action_status": "VARCHAR",
        "announcement_at": "TIMESTAMP WITH TIME ZONE",
        "published_at": "TIMESTAMP WITH TIME ZONE",
        "available_at": "TIMESTAMP WITH TIME ZONE",
        "ex_date": "DATE",
        "effective_at": "TIMESTAMP WITH TIME ZONE",
        "split_ratio": "DECIMAL(18,8)",
        "cash_amount": "DECIMAL(18,6)",
        "currency": "VARCHAR",
        "terminal_consideration": "DECIMAL(18,6)",
        "successor_listing_id": "VARCHAR",
        "timestamp_precision": "VARCHAR",
        "quality_state": "VARCHAR",
    },
    "universe_membership": {
        "source_record_id": "VARCHAR",
        "mdm_vintage_id": "VARCHAR",
        "universe_id": "VARCHAR",
        "listing_id": "VARCHAR",
        "membership_state": "VARCHAR",
        "effective_from": "TIMESTAMP WITH TIME ZONE",
        "effective_to": "TIMESTAMP WITH TIME ZONE",
        "published_at": "TIMESTAMP WITH TIME ZONE",
        "available_at": "TIMESTAMP WITH TIME ZONE",
        "quality_state": "VARCHAR",
    },
}

REQUIRED_SORT_KEYS: Mapping[str, tuple[str, ...]] = {
    "identity_lifecycle": (
        "listing_id",
        "effective_from",
        "source_record_id",
    ),
    "exchange_sessions": (
        "exchange_id",
        "session_date",
        "source_record_id",
    ),
    "daily_observations": (
        "listing_id",
        "session_date",
        "source_record_id",
    ),
    "corporate_actions": (
        "listing_id",
        "effective_at",
        "action_id",
        "source_record_id",
    ),
    "universe_membership": (
        "universe_id",
        "listing_id",
        "effective_from",
        "source_record_id",
    ),
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MUTABLE_IDENTIFIER_RE = re.compile(
    r"(^|[^a-z0-9])(latest|current|head|rolling)([^a-z0-9]|$)",
    re.IGNORECASE,
)


class ContractError(ValueError):
    """Raised when an MDM manifest violates the frozen boundary contract."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def _strict_keys(
    value: Mapping[str, Any], expected: frozenset[str], context: str
) -> None:
    actual = frozenset(value)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        parts: list[str] = []
        if missing:
            parts.append(f"missing keys {missing!r}")
        if unexpected:
            parts.append(f"unexpected keys {unexpected!r}")
        raise ContractError(context, "; ".join(parts))


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(field, "must be a non-empty string")
    if value != value.strip():
        raise ContractError(field, "must not contain surrounding whitespace")
    return value


def _immutable_identifier(value: Any, field: str) -> str:
    result = _required_string(value, field)
    if "latest" in result.casefold() or _MUTABLE_IDENTIFIER_RE.search(result):
        raise ContractError(field, "must be immutable, not a mutable alias")
    return result


def _sha256(value: Any, field: str) -> str:
    result = _required_string(value, field)
    if not _SHA256_RE.fullmatch(result):
        raise ContractError(field, "must be a lowercase 64-character SHA-256")
    return result


def _non_negative_integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContractError(field, "must be a non-negative integer")
    return value


def _required_boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError(field, "must be a boolean")
    return value


def _utc_datetime(value: Any, field: str) -> datetime:
    if isinstance(value, str):
        candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            result = datetime.fromisoformat(candidate)
        except ValueError as exc:
            raise ContractError(field, "must be an ISO-8601 timestamp") from exc
    elif isinstance(value, datetime):
        result = value
    else:
        raise ContractError(field, "must be an ISO-8601 timestamp")

    if result.tzinfo is None or result.utcoffset() is None:
        raise ContractError(field, "must be timezone-aware")
    if result.utcoffset() != timezone.utc.utcoffset(result):
        raise ContractError(field, "must be expressed in UTC")
    return result.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class MdmTableManifest:
    """Immutable description of one retained MDM Parquet table."""

    logical_name: str
    relative_path: PurePosixPath
    format: str
    schema_version: str
    schema_fingerprint_version: str
    schema_sha256: str
    row_count: int
    sha256: str
    logical_fingerprint_version: str
    logical_sha256: str
    logical_sort_keys: tuple[str, ...]
    complete: bool

    def __post_init__(self) -> None:
        if self.logical_name not in REQUIRED_TABLES:
            raise ContractError(
                "logical_name", f"unsupported table {self.logical_name!r}"
            )
        if not isinstance(self.relative_path, PurePosixPath):
            raise ContractError("relative_path", "must be a PurePosixPath")
        if self.relative_path.is_absolute() or ".." in self.relative_path.parts:
            raise ContractError("relative_path", "must stay inside the snapshot bundle")
        if "\\" in self.relative_path.as_posix():
            raise ContractError("relative_path", "must use POSIX separators")
        if self.relative_path.suffix.casefold() != ".parquet":
            raise ContractError("relative_path", "must identify a Parquet file")
        if self.format != "parquet":
            raise ContractError("format", "only parquet is supported")
        _immutable_identifier(self.schema_version, "schema_version")
        if self.schema_fingerprint_version != SCHEMA_FINGERPRINT_VERSION:
            raise ContractError(
                "schema_fingerprint_version",
                f"must equal {SCHEMA_FINGERPRINT_VERSION!r}",
            )
        _sha256(self.schema_sha256, "schema_sha256")
        _non_negative_integer(self.row_count, "row_count")
        _sha256(self.sha256, "sha256")
        if self.logical_fingerprint_version != LOGICAL_ROWS_FINGERPRINT_VERSION:
            raise ContractError(
                "logical_fingerprint_version",
                f"must equal {LOGICAL_ROWS_FINGERPRINT_VERSION!r}",
            )
        _sha256(self.logical_sha256, "logical_sha256")
        if not isinstance(self.logical_sort_keys, tuple):
            raise ContractError("logical_sort_keys", "must be an immutable tuple")
        if self.logical_sort_keys != REQUIRED_SORT_KEYS[self.logical_name]:
            raise ContractError(
                "logical_sort_keys",
                f"must equal {REQUIRED_SORT_KEYS[self.logical_name]!r}",
            )
        if self.complete is not True:
            raise ContractError("complete", "partial tables are prohibited")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "MdmTableManifest":
        if not isinstance(value, Mapping):
            raise ContractError("tables[]", "must be an object")
        expected = frozenset(
            {
                "logical_name",
                "relative_path",
                "format",
                "schema_version",
                "schema_fingerprint_version",
                "schema_sha256",
                "row_count",
                "sha256",
                "logical_fingerprint_version",
                "logical_sha256",
                "logical_sort_keys",
                "complete",
            }
        )
        _strict_keys(value, expected, "tables[]")
        logical_name = _required_string(value["logical_name"], "logical_name")
        raw_path = _required_string(value["relative_path"], "relative_path")
        if "\\" in raw_path:
            raise ContractError("relative_path", "must use POSIX separators")
        raw_sort_keys = value["logical_sort_keys"]
        if not isinstance(raw_sort_keys, list) or not all(
            isinstance(item, str) and item for item in raw_sort_keys
        ):
            raise ContractError("logical_sort_keys", "must be an array of names")
        return cls(
            logical_name=logical_name,
            relative_path=PurePosixPath(raw_path),
            format=_required_string(value["format"], "format"),
            schema_version=_immutable_identifier(
                value["schema_version"], "schema_version"
            ),
            schema_fingerprint_version=_required_string(
                value["schema_fingerprint_version"],
                "schema_fingerprint_version",
            ),
            schema_sha256=_sha256(value["schema_sha256"], "schema_sha256"),
            row_count=_non_negative_integer(value["row_count"], "row_count"),
            sha256=_sha256(value["sha256"], "sha256"),
            logical_fingerprint_version=_required_string(
                value["logical_fingerprint_version"],
                "logical_fingerprint_version",
            ),
            logical_sha256=_sha256(
                value["logical_sha256"], "logical_sha256"
            ),
            logical_sort_keys=tuple(raw_sort_keys),
            complete=_required_boolean(value["complete"], "complete"),
        )


@dataclass(frozen=True, slots=True)
class MdmSnapshotManifest:
    """Strict manifest for one complete, immutable, authorised MDM snapshot."""

    manifest_schema_version: str
    source_authority: str
    source_kind: str
    authorisation_status: str
    authorisation_scope_id: str
    snapshot_id: str
    source_version: str
    consistency_token: str
    created_at_utc: datetime
    snapshot_cutoff_utc: datetime
    replayable: bool
    complete: bool
    tables: tuple[MdmTableManifest, ...]

    def __post_init__(self) -> None:
        if self.manifest_schema_version != MANIFEST_SCHEMA_VERSION:
            raise ContractError(
                "manifest_schema_version",
                f"must equal {MANIFEST_SCHEMA_VERSION!r}",
            )
        if self.source_authority != MDM_SOURCE_AUTHORITY:
            raise ContractError(
                "source_authority", f"must equal {MDM_SOURCE_AUTHORITY!r}"
            )
        if self.source_kind not in {
            MDM_PRODUCTION_SNAPSHOT,
            TEST_ONLY_NON_PRODUCTION,
        }:
            raise ContractError(
                "source_kind",
                "must explicitly identify production MDM or test-only data",
            )
        _immutable_identifier(
            self.authorisation_scope_id, "authorisation_scope_id"
        )
        if self.source_kind == MDM_PRODUCTION_SNAPSHOT:
            if self.authorisation_status != AUTHORISED_FOR_PROJECT_EDGE_RESEARCH:
                raise ContractError(
                    "authorisation_status",
                    "a production MDM snapshot must be explicitly authorised",
                )
        elif self.authorisation_status != TEST_ONLY_NOT_AUTHORISED:
            raise ContractError(
                "authorisation_status",
                "a test-only snapshot must be explicitly not authorised",
            )
        _immutable_identifier(self.snapshot_id, "snapshot_id")
        _immutable_identifier(self.source_version, "source_version")
        _immutable_identifier(self.consistency_token, "consistency_token")
        _utc_datetime(self.created_at_utc, "created_at_utc")
        _utc_datetime(self.snapshot_cutoff_utc, "snapshot_cutoff_utc")
        if self.snapshot_cutoff_utc > self.created_at_utc:
            raise ContractError(
                "snapshot_cutoff_utc", "cannot be later than snapshot creation"
            )
        if self.replayable is not True:
            raise ContractError("replayable", "exact replay is mandatory")
        if self.complete is not True:
            raise ContractError("complete", "partial snapshots are prohibited")
        if not isinstance(self.tables, tuple) or not all(
            isinstance(table, MdmTableManifest) for table in self.tables
        ):
            raise ContractError(
                "tables", "must be an immutable tuple of MdmTableManifest values"
            )
        names = [table.logical_name for table in self.tables]
        if len(names) != len(set(names)):
            raise ContractError("tables", "logical table names must be unique")
        actual = frozenset(names)
        if actual != REQUIRED_TABLES:
            missing = sorted(REQUIRED_TABLES - actual)
            unexpected = sorted(actual - REQUIRED_TABLES)
            raise ContractError(
                "tables",
                f"required table set mismatch; missing={missing!r}, "
                f"unexpected={unexpected!r}",
            )

    @property
    def production_use_permitted(self) -> bool:
        """True only for an explicitly authorised production MDM snapshot."""

        return (
            self.source_authority == MDM_SOURCE_AUTHORITY
            and self.source_kind == MDM_PRODUCTION_SNAPSHOT
            and self.authorisation_status
            == AUTHORISED_FOR_PROJECT_EDGE_RESEARCH
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "MdmSnapshotManifest":
        if not isinstance(value, Mapping):
            raise ContractError("manifest", "must be an object")
        expected = frozenset(
            {
                "manifest_schema_version",
                "source_authority",
                "source_kind",
                "authorisation_status",
                "authorisation_scope_id",
                "snapshot_id",
                "source_version",
                "consistency_token",
                "created_at_utc",
                "snapshot_cutoff_utc",
                "replayable",
                "complete",
                "tables",
            }
        )
        _strict_keys(value, expected, "manifest")
        raw_tables = value["tables"]
        if not isinstance(raw_tables, list):
            raise ContractError("tables", "must be an array")
        tables = tuple(MdmTableManifest.from_mapping(item) for item in raw_tables)
        return cls(
            manifest_schema_version=_required_string(
                value["manifest_schema_version"], "manifest_schema_version"
            ),
            source_authority=_required_string(
                value["source_authority"], "source_authority"
            ),
            source_kind=_required_string(value["source_kind"], "source_kind"),
            authorisation_status=_required_string(
                value["authorisation_status"], "authorisation_status"
            ),
            authorisation_scope_id=_immutable_identifier(
                value["authorisation_scope_id"], "authorisation_scope_id"
            ),
            snapshot_id=_immutable_identifier(value["snapshot_id"], "snapshot_id"),
            source_version=_immutable_identifier(
                value["source_version"], "source_version"
            ),
            consistency_token=_immutable_identifier(
                value["consistency_token"], "consistency_token"
            ),
            created_at_utc=_utc_datetime(
                value["created_at_utc"], "created_at_utc"
            ),
            snapshot_cutoff_utc=_utc_datetime(
                value["snapshot_cutoff_utc"], "snapshot_cutoff_utc"
            ),
            replayable=_required_boolean(value["replayable"], "replayable"),
            complete=_required_boolean(value["complete"], "complete"),
            tables=tables,
        )
