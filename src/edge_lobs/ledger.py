"""Immutable transactional storage for Leadership Observation Ledger batches.

The ledger is deliberately narrower than a database.  One successful import
creates one write-once batch directory and one hash-chained register event.
Indexes are derived conveniences and never confer authority.  All authoritative
reads revalidate the register, batch manifest, payload inventory, raw bytes, and
structured observation.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from typing import Any, Iterator, Mapping, Sequence

from edge_mdm.fingerprint import package_source_fingerprint, sha256_bytes, sha256_file

from .errors import LobsError
from .jsonio import canonical_json_bytes, load_json_object, write_canonical_json_new
from .validation import (
    validate_import_manifest_document,
    validate_observation_document,
)


OBSERVATION_ROOT_PARTS = ("observations", "leadership_rotation")
LEDGER_SCHEMA_VERSION = "edge.leadership_ledger.v1"
SOURCE_MANIFEST_SCHEMA_VERSION = "edge.leadership_source_manifest.v1"
BATCH_MANIFEST_SCHEMA_VERSION = "edge.leadership_batch_manifest.v1"
VALIDATION_REPORT_SCHEMA_VERSION = "edge.leadership_import_validation.v1"
REGISTER_SCHEMA_VERSION = "edge.leadership_ledger_event.v1"
INDEX_SCHEMA_VERSION = "edge.leadership_ledger_index.v1"

_BATCH_ID_RE = re.compile(r"^EDGE-LOBS-[0-9]{8}-[A-Za-z0-9][A-Za-z0-9._-]*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_OBSERVATION_ARRAYS = (
    "market",
    "instruments",
    "groups",
    "stocks",
    "futures_snapshot",
    "macro_context",
)
_COPY_CHUNK_BYTES = 1024 * 1024

_REGISTER_KEYS = frozenset(
    {
        "schema_version",
        "event_type",
        "previous_record_sha256",
        "observation_batch_id",
        "batch_manifest_sha256",
        "observation_ids",
        "source_ids",
        "source_identities",
        "source_hashes",
        "recorded_at_utc",
        "actor",
        "record_sha256",
    }
)
_BATCH_MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "observation_batch_id",
        "observation_date",
        "information_cutoff_timestamp",
        "information_cutoff_timezone",
        "capture_mode",
        "sealed_at_utc",
        "observation_sha256",
        "source_manifest_sha256",
        "validation_report_sha256",
        "software_source_sha256",
        "observation_ids",
        "source_ids",
        "source_identities",
        "source_hashes",
        "file_inventory",
        "authority_state",
        "limitations",
    }
)
_SOURCE_MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "observation_batch_id",
        "capture_mode",
        "ingested_at_utc",
        "sources",
    }
)
_SOURCE_ENTRY_KEYS = frozenset(
    {
        "source_id",
        "observation_batch_id",
        "source_type",
        "source_name",
        "source_title",
        "source_original_filename",
        "source_identity",
        "source_capture_timestamp",
        "source_publication_timestamp",
        "source_publication_date",
        "timestamp_precision",
        "timezone",
        "capture_mode",
        "historical_reconstruction",
        "contemporaneous_capture_attested",
        "expected_sha256",
        "parser_version",
        "notes",
        "ingested_timestamp",
        "original_hash",
        "byte_length",
        "storage_location",
    }
)
_FILE_DESCRIPTOR_KEYS = frozenset({"path", "bytes", "sha256"})


@dataclass(frozen=True, slots=True)
class LedgerPaths:
    """Resolved repository-owned paths used by the ledger."""

    repository_root: Path
    observation_root: Path
    inbox_root: Path
    ledger_root: Path
    batches_root: Path
    registry_root: Path
    register_path: Path
    indexes_root: Path
    index_path: Path
    lock_path: Path

    @classmethod
    def from_repository(cls, repository_root: str | Path) -> "LedgerPaths":
        candidate = Path(repository_root)
        try:
            root = candidate.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise LobsError(
                "REPOSITORY_ROOT_INVALID",
                "repository root does not resolve",
                path=str(candidate),
            ) from exc
        if not root.is_dir():
            raise LobsError(
                "REPOSITORY_ROOT_INVALID",
                "repository root must be a directory",
                path=str(root),
            )
        observation_root = root.joinpath(*OBSERVATION_ROOT_PARTS)
        ledger_root = observation_root / "ledger"
        registry_root = ledger_root / "registry"
        indexes_root = ledger_root / "indexes"
        result = cls(
            repository_root=root,
            observation_root=observation_root,
            inbox_root=observation_root / "inbox",
            ledger_root=ledger_root,
            batches_root=ledger_root / "batches",
            registry_root=registry_root,
            register_path=registry_root / "ledger_events.jsonl",
            indexes_root=indexes_root,
            index_path=indexes_root / "ledger_index.json",
            lock_path=registry_root / ".ledger.lock",
        )
        for path in (
            result.observation_root,
            result.inbox_root,
            result.ledger_root,
            result.batches_root,
            result.registry_root,
            result.register_path,
            result.indexes_root,
            result.index_path,
            result.lock_path,
        ):
            _require_contained(path, root, "LEDGER_PATH_OUTSIDE_REPOSITORY")
        return result


@dataclass(frozen=True, slots=True)
class SealedBatch:
    """Result of a completed and independently reverified import."""

    observation_batch_id: str
    root: Path
    batch_manifest_path: Path
    batch_manifest_sha256: str
    register_record_sha256: str
    index_path: Path

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_batch_id": self.observation_batch_id,
            "root": str(self.root),
            "batch_manifest_path": str(self.batch_manifest_path),
            "batch_manifest_sha256": self.batch_manifest_sha256,
            "register_record_sha256": self.register_record_sha256,
            "index_path": str(self.index_path),
        }


@dataclass(frozen=True, slots=True)
class _RawInput:
    entry: Mapping[str, Any]
    path: Path
    sha256: str
    byte_length: int


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _require_contained(path: Path, parent: Path, code: str) -> Path:
    try:
        resolved = path.resolve(strict=False)
        resolved_parent = parent.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise LobsError(code, "path cannot be resolved", path=str(path)) from exc
    if resolved != resolved_parent and not resolved.is_relative_to(resolved_parent):
        raise LobsError(code, "resolved path escapes its authorised root", path=str(resolved))
    return resolved


def _resolve_existing_file(
    value: str | Path,
    *,
    relative_to: Path,
    contained_by: Path,
    code: str,
) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = relative_to / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise LobsError(code, "required file does not resolve", path=str(candidate)) from exc
    _require_contained(resolved, contained_by, code)
    if not resolved.is_file():
        raise LobsError(code, "required path must be a file", path=str(resolved))
    return resolved


def _ensure_directory(path: Path, *, contained_by: Path, code: str) -> Path:
    _require_contained(path, contained_by, code)
    try:
        path.mkdir(parents=True, exist_ok=True)
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise LobsError(code, str(exc), path=str(path)) from exc
    _require_contained(resolved, contained_by, code)
    if not resolved.is_dir():
        raise LobsError(code, "authoritative path must be a directory", path=str(resolved))
    return resolved


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], code: str) -> None:
    actual = set(value)
    if actual != expected:
        raise LobsError(
            code,
            f"missing={sorted(expected - actual)!r}, unexpected={sorted(actual - expected)!r}",
        )


def _require_sha256(value: Any, *, code: str) -> str:
    rendered = str(value)
    if not _SHA256_RE.fullmatch(rendered):
        raise LobsError(code, f"invalid SHA-256 {rendered!r}")
    return rendered


def _require_unique_strings(value: Any, *, field: str, code: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() or item != item.strip()
        for item in value
    ):
        raise LobsError(code, f"{field} must be an array of non-empty strings")
    result = tuple(value)
    if len(result) != len(set(result)):
        raise LobsError(code, f"{field} contains duplicates")
    if result != tuple(sorted(result)):
        raise LobsError(code, f"{field} must use canonical sorted order")
    return result


def _report_dict(value: Any, *, label: str) -> dict[str, Any]:
    if hasattr(value, "as_dict"):
        result = value.as_dict()
    elif isinstance(value, Mapping):
        result = dict(value)
    else:
        raise LobsError(
            "VALIDATION_REPORT_INVALID",
            f"{label} validator returned {type(value).__name__}, expected a report",
        )
    if not isinstance(result, dict):
        raise LobsError("VALIDATION_REPORT_INVALID", f"{label} report is not an object")
    canonical_json_bytes(result)
    return result


def _observation_ids(observation: Mapping[str, Any]) -> tuple[str, ...]:
    result: list[str] = []
    for field in _OBSERVATION_ARRAYS:
        rows = observation.get(field)
        if not isinstance(rows, list):
            raise LobsError(
                "OBSERVATION_ARRAY_INVALID", f"{field} must be an array"
            )
        for row in rows:
            if not isinstance(row, Mapping):
                raise LobsError(
                    "OBSERVATION_RECORD_INVALID", f"{field} entries must be objects"
                )
            observation_id = row.get("observation_id")
            if not isinstance(observation_id, str) or not observation_id.strip():
                raise LobsError(
                    "OBSERVATION_ID_REQUIRED", f"{field} record lacks observation_id"
                )
            result.append(observation_id)
    if len(result) != len(set(result)):
        raise LobsError(
            "DUPLICATE_OBSERVATION_ID", "observation IDs must be unique within a batch"
        )
    return tuple(sorted(result))


def _actor(observation: Mapping[str, Any]) -> str:
    extractor = observation.get("extractor")
    if not isinstance(extractor, Mapping):
        raise LobsError("EXTRACTOR_INVALID", "observation extractor must be an object")
    actor_id = extractor.get("actor_id")
    actor_type = extractor.get("actor_type")
    if isinstance(actor_id, str) and actor_id.strip():
        return actor_id
    if isinstance(actor_type, str) and actor_type.strip():
        return actor_type
    raise LobsError("IMPORT_ACTOR_REQUIRED", "extractor actor identity is required")


def _strict_json_line(line: bytes, *, line_number: int, path: Path) -> dict[str, Any]:
    try:
        text = line.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LobsError(
            "LEDGER_REGISTER_NOT_UTF8",
            f"invalid UTF-8 at line {line_number}",
            path=str(path),
        ) from exc

    class _Duplicate(ValueError):
        pass

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise _Duplicate(key)
            result[key] = item
        return result

    def reject_constant(token: str) -> Any:
        raise ValueError(f"non-finite number {token}")

    try:
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except _Duplicate as exc:
        raise LobsError(
            "LEDGER_REGISTER_DUPLICATE_KEY",
            f"duplicate key {exc.args[0]!r} at line {line_number}",
            path=str(path),
        ) from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise LobsError(
            "LEDGER_REGISTER_INVALID_JSON",
            f"invalid JSON at line {line_number}: {exc}",
            path=str(path),
        ) from exc
    if not isinstance(value, dict):
        raise LobsError(
            "LEDGER_REGISTER_OBJECT_REQUIRED",
            f"line {line_number} is not an object",
            path=str(path),
        )
    if canonical_json_bytes(value) != line:
        raise LobsError(
            "LEDGER_REGISTER_NONCANONICAL",
            f"line {line_number} is not canonical JSON",
            path=str(path),
        )
    return value


def _load_register(paths: LedgerPaths) -> tuple[dict[str, Any], ...]:
    register = paths.register_path
    if not register.exists():
        return ()
    resolved = _require_contained(
        register, paths.repository_root, "LEDGER_REGISTER_OUTSIDE_REPOSITORY"
    )
    if not resolved.is_file():
        raise LobsError(
            "LEDGER_REGISTER_INVALID", "register must be a file", path=str(resolved)
        )
    try:
        raw = resolved.read_bytes()
    except OSError as exc:
        raise LobsError("LEDGER_REGISTER_READ_FAILED", str(exc), path=str(resolved)) from exc
    if not raw:
        raise LobsError(
            "LEDGER_REGISTER_EMPTY", "an existing register cannot be empty", path=str(resolved)
        )
    if not raw.endswith(b"\n"):
        raise LobsError(
            "LEDGER_REGISTER_TRUNCATED",
            "register must end with a complete newline-terminated event",
            path=str(resolved),
        )
    records: list[dict[str, Any]] = []
    previous = "0" * 64
    seen_batches: set[str] = set()
    for line_number, line in enumerate(raw.splitlines(), 1):
        if not line:
            raise LobsError(
                "LEDGER_REGISTER_BLANK_LINE",
                f"blank line {line_number} is prohibited",
                path=str(resolved),
            )
        record = _strict_json_line(line, line_number=line_number, path=resolved)
        _exact_keys(record, _REGISTER_KEYS, "LEDGER_REGISTER_SCHEMA_INVALID")
        if record.get("schema_version") != REGISTER_SCHEMA_VERSION:
            raise LobsError(
                "LEDGER_REGISTER_VERSION_INVALID", f"line {line_number}"
            )
        if record.get("event_type") != "SEALED":
            raise LobsError("LEDGER_REGISTER_EVENT_INVALID", f"line {line_number}")
        if record.get("previous_record_sha256") != previous:
            raise LobsError("LEDGER_REGISTER_CHAIN_BROKEN", f"line {line_number}")
        claimed = _require_sha256(
            record.get("record_sha256"), code="LEDGER_REGISTER_HASH_INVALID"
        )
        body = {key: item for key, item in record.items() if key != "record_sha256"}
        actual = sha256_bytes(canonical_json_bytes(body))
        if actual != claimed:
            raise LobsError("LEDGER_REGISTER_HASH_MISMATCH", f"line {line_number}")
        _require_sha256(
            record.get("batch_manifest_sha256"), code="BATCH_MANIFEST_HASH_INVALID"
        )
        for field in (
            "observation_ids",
            "source_ids",
            "source_identities",
            "source_hashes",
        ):
            _require_unique_strings(
                record.get(field), field=field, code="LEDGER_REGISTER_SCHEMA_INVALID"
            )
        for digest in record["source_hashes"]:
            _require_sha256(digest, code="SOURCE_HASH_INVALID")
        batch_id = str(record.get("observation_batch_id", ""))
        if not _BATCH_ID_RE.fullmatch(batch_id):
            raise LobsError("OBSERVATION_BATCH_ID_INVALID", batch_id)
        if batch_id in seen_batches:
            raise LobsError("DUPLICATE_REGISTER_BATCH_ID", batch_id)
        if not isinstance(record.get("actor"), str) or not record["actor"].strip():
            raise LobsError("LEDGER_REGISTER_ACTOR_INVALID", f"line {line_number}")
        seen_batches.add(batch_id)
        records.append(record)
        previous = claimed
    return tuple(records)


def _file_descriptor(path: Path, *, relative_to: Path) -> dict[str, Any]:
    relative = path.relative_to(relative_to).as_posix()
    return {"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def _safe_bundle_file(bundle_root: Path, relative_text: Any) -> Path:
    if not isinstance(relative_text, str) or not relative_text:
        raise LobsError("BATCH_FILE_PATH_INVALID", repr(relative_text))
    relative = PurePosixPath(relative_text)
    if relative.is_absolute() or ".." in relative.parts or "\\" in relative_text:
        raise LobsError("BATCH_FILE_PATH_INVALID", relative_text)
    path = bundle_root.joinpath(*relative.parts)
    resolved = _require_contained(path, bundle_root, "BATCH_FILE_OUTSIDE_BUNDLE")
    if not resolved.is_file():
        raise LobsError("BATCH_FILE_MISSING", relative_text, path=str(resolved))
    return resolved


def _verify_batch(
    batch_root: Path, event: Mapping[str, Any], *, expected_batch_id: str
) -> dict[str, Any]:
    manifest_path = batch_root / "batch_manifest.json"
    if not manifest_path.is_file():
        raise LobsError(
            "BATCH_MANIFEST_MISSING", "sealed batch lacks batch_manifest.json", path=str(batch_root)
        )
    actual_manifest_hash = sha256_file(manifest_path)
    if actual_manifest_hash != event.get("batch_manifest_sha256"):
        raise LobsError("BATCH_MANIFEST_HASH_MISMATCH", expected_batch_id)
    manifest = load_json_object(manifest_path)
    _exact_keys(manifest, _BATCH_MANIFEST_KEYS, "BATCH_MANIFEST_SCHEMA_INVALID")
    if manifest.get("schema_version") != BATCH_MANIFEST_SCHEMA_VERSION:
        raise LobsError("BATCH_MANIFEST_VERSION_INVALID", expected_batch_id)
    if manifest.get("observation_batch_id") != expected_batch_id:
        raise LobsError("BATCH_DIRECTORY_ID_MISMATCH", expected_batch_id)
    if manifest.get("authority_state") != "SEALED_CAPTURE_RECORD":
        raise LobsError("BATCH_AUTHORITY_STATE_INVALID", expected_batch_id)
    if not isinstance(manifest.get("limitations"), list) or not all(
        isinstance(item, str) and item for item in manifest["limitations"]
    ):
        raise LobsError("BATCH_LIMITATIONS_INVALID", expected_batch_id)
    _require_sha256(
        manifest.get("software_source_sha256"), code="SOFTWARE_SOURCE_HASH_INVALID"
    )
    inventory = manifest.get("file_inventory")
    if not isinstance(inventory, list) or not inventory:
        raise LobsError("BATCH_FILE_INVENTORY_INVALID", expected_batch_id)
    descriptors: dict[str, Mapping[str, Any]] = {}
    for descriptor in inventory:
        if not isinstance(descriptor, Mapping):
            raise LobsError("BATCH_FILE_DESCRIPTOR_INVALID", expected_batch_id)
        _exact_keys(descriptor, _FILE_DESCRIPTOR_KEYS, "BATCH_FILE_DESCRIPTOR_INVALID")
        relative = descriptor.get("path")
        if not isinstance(relative, str) or relative in descriptors:
            raise LobsError("BATCH_FILE_DESCRIPTOR_INVALID", repr(relative))
        path = _safe_bundle_file(batch_root, relative)
        expected_bytes = descriptor.get("bytes")
        if isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int) or expected_bytes <= 0:
            raise LobsError("BATCH_FILE_SIZE_INVALID", relative)
        if path.stat().st_size != expected_bytes:
            raise LobsError("BATCH_FILE_SIZE_MISMATCH", relative)
        expected_hash = _require_sha256(
            descriptor.get("sha256"), code="BATCH_FILE_HASH_INVALID"
        )
        if sha256_file(path) != expected_hash:
            raise LobsError("BATCH_FILE_HASH_MISMATCH", relative)
        descriptors[relative] = descriptor
    actual_files = {
        path.relative_to(batch_root).as_posix()
        for path in batch_root.rglob("*")
        if path.is_file()
    }
    expected_files = set(descriptors) | {"batch_manifest.json"}
    if actual_files != expected_files:
        raise LobsError(
            "BATCH_DIRECTORY_SET_INVALID",
            f"missing={sorted(expected_files - actual_files)!r}, "
            f"unexpected={sorted(actual_files - expected_files)!r}",
        )
    for required in (
        "observation_batch.json",
        "source_manifest.json",
        "validation_report.json",
    ):
        if required not in descriptors:
            raise LobsError("BATCH_REQUIRED_FILE_MISSING", required)
    bindings = {
        "observation_batch.json": "observation_sha256",
        "source_manifest.json": "source_manifest_sha256",
        "validation_report.json": "validation_report_sha256",
    }
    for filename, field in bindings.items():
        digest = _require_sha256(manifest.get(field), code="BATCH_BINDING_HASH_INVALID")
        if digest != descriptors[filename]["sha256"]:
            raise LobsError("BATCH_BINDING_HASH_MISMATCH", field)

    observation_path = batch_root / "observation_batch.json"
    observation = load_json_object(observation_path)
    validate_observation_document(observation, allow_draft=False)
    if observation.get("observation_batch_id") != expected_batch_id:
        raise LobsError("OBSERVATION_BATCH_ID_MISMATCH", expected_batch_id)
    if observation.get("capture_mode") != manifest.get("capture_mode"):
        raise LobsError("CAPTURE_MODE_MISMATCH", expected_batch_id)
    for field in (
        "observation_date",
        "information_cutoff_timestamp",
        "information_cutoff_timezone",
    ):
        if observation.get(field) != manifest.get(field):
            raise LobsError(
                "BATCH_OBSERVATION_BINDING_MISMATCH",
                f"{field} differs between the sealed observation and batch manifest",
            )
    observation_ids = _observation_ids(observation)
    if observation_ids != tuple(manifest.get("observation_ids", [])):
        raise LobsError("BATCH_OBSERVATION_IDS_MISMATCH", expected_batch_id)

    source_manifest = load_json_object(batch_root / "source_manifest.json")
    _exact_keys(
        source_manifest, _SOURCE_MANIFEST_KEYS, "SOURCE_MANIFEST_SCHEMA_INVALID"
    )
    if source_manifest.get("schema_version") != SOURCE_MANIFEST_SCHEMA_VERSION:
        raise LobsError("SOURCE_MANIFEST_VERSION_INVALID", expected_batch_id)
    if source_manifest.get("observation_batch_id") != expected_batch_id:
        raise LobsError("SOURCE_MANIFEST_BATCH_ID_MISMATCH", expected_batch_id)
    if source_manifest.get("capture_mode") != manifest.get("capture_mode"):
        raise LobsError("SOURCE_MANIFEST_CAPTURE_MODE_MISMATCH", expected_batch_id)
    source_rows = source_manifest.get("sources")
    if not isinstance(source_rows, list) or not source_rows:
        raise LobsError("SOURCE_MANIFEST_SOURCES_INVALID", expected_batch_id)
    source_ids: list[str] = []
    source_identities: list[str] = []
    source_hashes: list[str] = []
    for source in source_rows:
        if not isinstance(source, Mapping):
            raise LobsError("SOURCE_MANIFEST_ENTRY_INVALID", expected_batch_id)
        _exact_keys(source, _SOURCE_ENTRY_KEYS, "SOURCE_MANIFEST_ENTRY_INVALID")
        if source.get("observation_batch_id") != expected_batch_id:
            raise LobsError("SOURCE_BATCH_ID_MISMATCH", str(source.get("source_id")))
        if source.get("capture_mode") != manifest.get("capture_mode"):
            raise LobsError("SOURCE_CAPTURE_MODE_MISMATCH", str(source.get("source_id")))
        source_id = str(source.get("source_id", ""))
        identity = str(source.get("source_identity", ""))
        if not source_id or not identity:
            raise LobsError("SOURCE_IDENTITY_REQUIRED", source_id)
        digest = _require_sha256(source.get("original_hash"), code="SOURCE_HASH_INVALID")
        byte_length = source.get("byte_length")
        if isinstance(byte_length, bool) or not isinstance(byte_length, int) or byte_length <= 0:
            raise LobsError("EMPTY_RAW_SOURCE", source_id)
        raw_path = _safe_bundle_file(batch_root, source.get("storage_location"))
        if raw_path.stat().st_size != byte_length:
            raise LobsError("RAW_SOURCE_SIZE_MISMATCH", source_id)
        if sha256_file(raw_path) != digest:
            raise LobsError("RAW_SOURCE_HASH_MISMATCH", source_id)
        source_ids.append(source_id)
        source_identities.append(identity)
        source_hashes.append(digest)
    if any(len(values) != len(set(values)) for values in (source_ids, source_identities, source_hashes)):
        raise LobsError("DUPLICATE_SOURCE_IN_BATCH", expected_batch_id)
    canonical_sources = (
        tuple(sorted(source_ids)),
        tuple(sorted(source_identities)),
        tuple(sorted(source_hashes)),
    )
    manifest_sources = (
        tuple(manifest.get("source_ids", [])),
        tuple(manifest.get("source_identities", [])),
        tuple(manifest.get("source_hashes", [])),
    )
    if canonical_sources != manifest_sources:
        raise LobsError("BATCH_SOURCE_BINDING_MISMATCH", expected_batch_id)
    observation_source_ids = observation.get("source_ids")
    if not isinstance(observation_source_ids, list) or set(observation_source_ids) != set(source_ids):
        raise LobsError("SOURCE_ID_SET_MISMATCH", expected_batch_id)
    event_bindings = (
        tuple(event.get("observation_ids", [])),
        tuple(event.get("source_ids", [])),
        tuple(event.get("source_identities", [])),
        tuple(event.get("source_hashes", [])),
    )
    manifest_bindings = (
        observation_ids,
        *manifest_sources,
    )
    if event_bindings != manifest_bindings:
        raise LobsError("REGISTER_BATCH_BINDING_MISMATCH", expected_batch_id)
    load_json_object(batch_root / "validation_report.json")
    return {
        "observation_batch_id": expected_batch_id,
        "observation_date": observation.get("observation_date"),
        "information_cutoff_timestamp": observation.get("information_cutoff_timestamp"),
        "capture_mode": observation.get("capture_mode"),
        "batch_manifest_sha256": actual_manifest_hash,
        "observation_ids": list(observation_ids),
        "source_ids": list(manifest_sources[0]),
        "source_identities": list(manifest_sources[1]),
        "source_hashes": list(manifest_sources[2]),
    }


def _batch_directories(paths: LedgerPaths) -> dict[str, Path]:
    if not paths.batches_root.exists():
        return {}
    resolved = _require_contained(
        paths.batches_root, paths.repository_root, "BATCHES_ROOT_OUTSIDE_REPOSITORY"
    )
    if not resolved.is_dir():
        raise LobsError("BATCHES_ROOT_INVALID", "batches root must be a directory")
    result: dict[str, Path] = {}
    for child in resolved.iterdir():
        if not child.is_dir():
            raise LobsError(
                "LEDGER_BATCH_DIRECTORY_INVALID",
                "only batch directories may exist beneath batches",
                path=str(child),
            )
        result[child.name] = child
    return result


def _assert_globally_unique(
    batches: Sequence[Mapping[str, Any]], field: str, code: str
) -> None:
    owners: dict[str, str] = {}
    for batch in batches:
        batch_id = str(batch["observation_batch_id"])
        for value in batch[field]:
            prior = owners.get(str(value))
            if prior is not None:
                raise LobsError(code, f"{value!r} is shared by {prior} and {batch_id}")
            owners[str(value)] = batch_id


def _verify_ledger_unlocked(paths: LedgerPaths) -> dict[str, Any]:
    events = _load_register(paths)
    directories = _batch_directories(paths)
    registered_ids = {str(event["observation_batch_id"]) for event in events}
    directory_ids = set(directories)
    unregistered = sorted(directory_ids - registered_ids)
    if unregistered:
        raise LobsError(
            "UNREGISTERED_BATCH_PRESENT",
            f"batch directories lack seal events: {unregistered!r}",
        )
    missing = sorted(registered_ids - directory_ids)
    if missing:
        raise LobsError(
            "REGISTERED_BATCH_MISSING",
            f"seal events reference missing batch directories: {missing!r}",
        )
    verified: list[dict[str, Any]] = []
    for event in events:
        batch_id = str(event["observation_batch_id"])
        verified.append(
            _verify_batch(directories[batch_id], event, expected_batch_id=batch_id)
        )
    _assert_globally_unique(verified, "observation_ids", "DUPLICATE_LEDGER_OBSERVATION_ID")
    _assert_globally_unique(verified, "source_ids", "DUPLICATE_LEDGER_SOURCE_ID")
    _assert_globally_unique(
        verified, "source_identities", "DUPLICATE_LEDGER_SOURCE_IDENTITY"
    )
    _assert_globally_unique(verified, "source_hashes", "DUPLICATE_LEDGER_SOURCE_HASH")
    register_sha256 = sha256_file(paths.register_path) if paths.register_path.is_file() else sha256_bytes(b"")
    return {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "state": "VERIFIED",
        "batch_count": len(verified),
        "register_sha256": register_sha256,
        "batches": verified,
    }


def _ensure_ledger_roots(paths: LedgerPaths) -> None:
    _ensure_directory(
        paths.ledger_root,
        contained_by=paths.repository_root,
        code="LEDGER_ROOT_INVALID",
    )
    for directory in (paths.batches_root, paths.registry_root, paths.indexes_root):
        _ensure_directory(
            directory,
            contained_by=paths.ledger_root,
            code="LEDGER_DIRECTORY_INVALID",
        )


@contextmanager
def _exclusive_lock(paths: LedgerPaths) -> Iterator[None]:
    _ensure_ledger_roots(paths)
    descriptor: int | None = None
    try:
        descriptor = os.open(
            paths.lock_path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
        payload = canonical_json_bytes({"pid": os.getpid(), "acquired_at_utc": _utc_now()}) + b"\n"
        os.write(descriptor, payload)
        os.fsync(descriptor)
    except FileExistsError as exc:
        raise LobsError(
            "LEDGER_LOCKED",
            "exclusive ledger lock already exists; stale locks require explicit review",
            path=str(paths.lock_path),
        ) from exc
    except OSError as exc:
        if descriptor is not None:
            os.close(descriptor)
        raise LobsError("LEDGER_LOCK_FAILED", str(exc), path=str(paths.lock_path)) from exc
    try:
        assert descriptor is not None
        yield
    finally:
        os.close(descriptor)
        try:
            paths.lock_path.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise LobsError(
                "LEDGER_LOCK_RELEASE_FAILED", str(exc), path=str(paths.lock_path)
            ) from exc


def _resolve_raw_inputs(
    manifest: Mapping[str, Any], *, manifest_parent: Path, inbox_root: Path
) -> tuple[_RawInput, ...]:
    raw_sources = manifest.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise LobsError("RAW_SOURCES_REQUIRED", "import manifest sources cannot be empty")
    material: list[_RawInput] = []
    source_ids: set[str] = set()
    identities: set[str] = set()
    hashes: set[str] = set()
    for entry in raw_sources:
        if not isinstance(entry, Mapping):
            raise LobsError("IMPORT_SOURCE_INVALID", "source entries must be objects")
        source_id = str(entry.get("source_id", ""))
        identity = str(entry.get("source_identity", ""))
        if not source_id or not identity:
            raise LobsError("SOURCE_IDENTITY_REQUIRED", source_id)
        source_path = _resolve_existing_file(
            str(entry.get("path", "")),
            relative_to=manifest_parent,
            contained_by=inbox_root,
            code="SOURCE_PATH_OUTSIDE_INBOX",
        )
        size = source_path.stat().st_size
        if size <= 0:
            raise LobsError("EMPTY_RAW_SOURCE", source_id, path=str(source_path))
        digest = sha256_file(source_path)
        expected = entry.get("expected_sha256")
        if expected is not None and str(expected) != digest:
            raise LobsError(
                "SOURCE_EXPECTED_HASH_MISMATCH",
                f"expected {expected}, found {digest}",
                path=str(source_path),
            )
        if source_id in source_ids:
            raise LobsError("DUPLICATE_SOURCE_ID", source_id)
        if identity in identities:
            raise LobsError("DUPLICATE_SOURCE_IDENTITY", identity)
        if digest in hashes:
            raise LobsError(
                "DUPLICATE_RAW_SOURCE_CONTENT",
                f"identical bytes supplied more than once ({digest})",
            )
        source_ids.add(source_id)
        identities.add(identity)
        hashes.add(digest)
        material.append(_RawInput(dict(entry), source_path, digest, size))
    return tuple(sorted(material, key=lambda item: str(item.entry["source_id"])))


def _copy_file_new(source: Path, target: Path) -> None:
    try:
        with source.open("rb") as input_stream, target.open("xb") as output_stream:
            while chunk := input_stream.read(_COPY_CHUNK_BYTES):
                output_stream.write(chunk)
            output_stream.flush()
            os.fsync(output_stream.fileno())
    except FileExistsError as exc:
        raise LobsError(
            "IMMUTABLE_RAW_PATH_EXISTS", "raw staging path already exists", path=str(target)
        ) from exc
    except OSError as exc:
        raise LobsError("RAW_SOURCE_COPY_FAILED", str(exc), path=str(target)) from exc


def _source_manifest(
    raw_inputs: Sequence[_RawInput],
    *,
    observation_batch_id: str,
    capture_mode: str,
    ingested_at: str,
) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    for raw in raw_inputs:
        entry = dict(raw.entry)
        entry.pop("path", None)
        entry.update(
            {
                "observation_batch_id": observation_batch_id,
                "ingested_timestamp": ingested_at,
                "original_hash": raw.sha256,
                "byte_length": raw.byte_length,
                "storage_location": f"raw/{raw.sha256}",
            }
        )
        if set(entry) != _SOURCE_ENTRY_KEYS:
            missing = sorted(_SOURCE_ENTRY_KEYS - set(entry))
            unexpected = sorted(set(entry) - _SOURCE_ENTRY_KEYS)
            raise LobsError(
                "COMPUTED_SOURCE_MANIFEST_INVALID",
                f"missing={missing!r}, unexpected={unexpected!r}",
            )
        sources.append(entry)
    return {
        "schema_version": SOURCE_MANIFEST_SCHEMA_VERSION,
        "observation_batch_id": observation_batch_id,
        "capture_mode": capture_mode,
        "ingested_at_utc": ingested_at,
        "sources": sources,
    }


def _write_staged_bundle(
    staging: Path,
    *,
    observation: Mapping[str, Any],
    source_manifest: Mapping[str, Any],
    validation_report: Mapping[str, Any],
    raw_inputs: Sequence[_RawInput],
    sealed_at: str,
) -> tuple[dict[str, Any], str]:
    raw_root = staging / "raw"
    raw_root.mkdir(exist_ok=False)
    for raw in raw_inputs:
        _copy_file_new(raw.path, raw_root / raw.sha256)
    write_canonical_json_new(staging / "observation_batch.json", observation)
    write_canonical_json_new(staging / "source_manifest.json", source_manifest)
    write_canonical_json_new(staging / "validation_report.json", validation_report)
    payloads = sorted(
        (path for path in staging.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(staging).as_posix(),
    )
    inventory = [_file_descriptor(path, relative_to=staging) for path in payloads]
    observation_ids = list(_observation_ids(observation))
    source_ids = sorted(str(raw.entry["source_id"]) for raw in raw_inputs)
    source_identities = sorted(str(raw.entry["source_identity"]) for raw in raw_inputs)
    source_hashes = sorted(raw.sha256 for raw in raw_inputs)
    by_path = {descriptor["path"]: descriptor for descriptor in inventory}
    batch_manifest = {
        "schema_version": BATCH_MANIFEST_SCHEMA_VERSION,
        "observation_batch_id": str(observation["observation_batch_id"]),
        "observation_date": str(observation["observation_date"]),
        "information_cutoff_timestamp": str(
            observation["information_cutoff_timestamp"]
        ),
        "information_cutoff_timezone": str(
            observation["information_cutoff_timezone"]
        ),
        "capture_mode": str(observation["capture_mode"]),
        "sealed_at_utc": sealed_at,
        "observation_sha256": by_path["observation_batch.json"]["sha256"],
        "source_manifest_sha256": by_path["source_manifest.json"]["sha256"],
        "validation_report_sha256": by_path["validation_report.json"]["sha256"],
        "software_source_sha256": package_source_fingerprint(Path(__file__).resolve().parent),
        "observation_ids": observation_ids,
        "source_ids": source_ids,
        "source_identities": source_identities,
        "source_hashes": source_hashes,
        "file_inventory": inventory,
        "authority_state": "SEALED_CAPTURE_RECORD",
        "limitations": [
            "SOURCE_OBSERVATION_NOT_GROUND_TRUTH",
            "NO_MDM_ENRICHMENT_OR_FORWARD_OUTCOME_INCLUDED",
        ],
    }
    write_canonical_json_new(staging / "batch_manifest.json", batch_manifest)
    return batch_manifest, sha256_file(staging / "batch_manifest.json")


def _append_register(paths: LedgerPaths, body: Mapping[str, Any]) -> dict[str, Any]:
    record_digest = sha256_bytes(canonical_json_bytes(body))
    record = {**body, "record_sha256": record_digest}
    encoded = canonical_json_bytes(record) + b"\n"
    try:
        descriptor = os.open(
            paths.register_path,
            os.O_APPEND | os.O_CREAT | os.O_WRONLY,
            0o600,
        )
        try:
            offset = 0
            while offset < len(encoded):
                written = os.write(descriptor, encoded[offset:])
                if written <= 0:
                    raise OSError("register append made no progress")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise LobsError(
            "REGISTER_APPEND_FAILED_UNREGISTERED_BUNDLE",
            str(exc),
            path=str(paths.register_path),
        ) from exc
    return record


def _write_index_unlocked(paths: LedgerPaths, verified: Mapping[str, Any]) -> dict[str, Any]:
    index = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "register_sha256": verified["register_sha256"],
        "batch_count": verified["batch_count"],
        "batches": verified["batches"],
    }
    _ensure_directory(
        paths.indexes_root,
        contained_by=paths.ledger_root,
        code="LEDGER_INDEX_ROOT_INVALID",
    )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".ledger-index-", suffix=".json", dir=paths.indexes_root
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(canonical_json_bytes(index) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, paths.index_path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise LobsError("LEDGER_INDEX_WRITE_FAILED", str(exc), path=str(paths.index_path)) from exc
    return index


def _reject_existing_values(
    verified: Mapping[str, Any],
    *,
    observation_batch_id: str,
    observation_ids: Sequence[str],
    raw_inputs: Sequence[_RawInput],
) -> None:
    existing_batches = {str(row["observation_batch_id"]) for row in verified["batches"]}
    if observation_batch_id in existing_batches:
        raise LobsError("IMMUTABLE_BATCH_ID_COLLISION", observation_batch_id)
    checks = (
        (
            set(observation_ids),
            {value for row in verified["batches"] for value in row["observation_ids"]},
            "DUPLICATE_OBSERVATION_ID",
        ),
        (
            {str(raw.entry["source_id"]) for raw in raw_inputs},
            {value for row in verified["batches"] for value in row["source_ids"]},
            "DUPLICATE_SOURCE_ID",
        ),
        (
            {str(raw.entry["source_identity"]) for raw in raw_inputs},
            {value for row in verified["batches"] for value in row["source_identities"]},
            "DUPLICATE_SOURCE_IDENTITY",
        ),
        (
            {raw.sha256 for raw in raw_inputs},
            {value for row in verified["batches"] for value in row["source_hashes"]},
            "DUPLICATE_RAW_SOURCE_CONTENT",
        ),
    )
    for incoming, existing, code in checks:
        duplicate = sorted(incoming & existing)
        if duplicate:
            raise LobsError(code, f"already sealed values: {duplicate!r}")


def import_observation_batch(
    import_manifest_path: str | Path, repository_root: str | Path
) -> SealedBatch:
    """Validate and atomically seal one complete observation batch.

    Templates and drafts are not importable.  All schema and file validation is
    completed before a visible batch directory is created.  If the process fails
    after the directory rename but before the register append, the bundle is
    deliberately retained as an excluded orphan for explicit recovery review.
    """

    paths = LedgerPaths.from_repository(repository_root)
    if not paths.inbox_root.exists() or not paths.inbox_root.is_dir():
        raise LobsError(
            "INBOX_ROOT_MISSING",
            "leadership observation inbox does not exist",
            path=str(paths.inbox_root),
        )
    import_path = _resolve_existing_file(
        import_manifest_path,
        relative_to=paths.repository_root,
        contained_by=paths.inbox_root,
        code="IMPORT_MANIFEST_OUTSIDE_INBOX",
    )
    manifest = load_json_object(import_path)
    observation_path = _resolve_existing_file(
        str(manifest.get("observation_path", "")),
        relative_to=import_path.parent,
        contained_by=paths.inbox_root,
        code="OBSERVATION_PATH_OUTSIDE_INBOX",
    )
    observation = load_json_object(observation_path)
    observation_report = validate_observation_document(observation, allow_draft=False)
    manifest_report = validate_import_manifest_document(
        manifest, observation, allow_template=False
    )
    observation_validation = _report_dict(observation_report, label="observation")
    manifest_validation = _report_dict(manifest_report, label="import manifest")
    batch_id = str(observation.get("observation_batch_id", ""))
    if not _BATCH_ID_RE.fullmatch(batch_id):
        raise LobsError("OBSERVATION_BATCH_ID_INVALID", batch_id)
    if manifest.get("observation_batch_id") != batch_id:
        raise LobsError("OBSERVATION_BATCH_ID_MISMATCH", batch_id)
    if manifest.get("capture_mode") != observation.get("capture_mode"):
        raise LobsError("CAPTURE_MODE_MISMATCH", batch_id)
    observation_ids = _observation_ids(observation)
    raw_inputs = _resolve_raw_inputs(
        manifest, manifest_parent=import_path.parent, inbox_root=paths.inbox_root
    )
    manifest_source_ids = {str(raw.entry["source_id"]) for raw in raw_inputs}
    observation_source_ids = observation.get("source_ids")
    if not isinstance(observation_source_ids, list) or set(observation_source_ids) != manifest_source_ids:
        raise LobsError(
            "SOURCE_ID_SET_MISMATCH",
            "observation source_ids and import-manifest sources must match exactly",
        )
    actor = _actor(observation)
    validation_report = {
        "schema_version": VALIDATION_REPORT_SCHEMA_VERSION,
        "state": "VALIDATED_FOR_SEAL",
        "authority_source": "COMPUTED",
        "observation_validation": observation_validation,
        "import_manifest_validation": manifest_validation,
    }

    staging: Path | None = None
    committed = False
    with _exclusive_lock(paths):
        verified = _verify_ledger_unlocked(paths)
        _reject_existing_values(
            verified,
            observation_batch_id=batch_id,
            observation_ids=observation_ids,
            raw_inputs=raw_inputs,
        )
        final_root = _require_contained(
            paths.batches_root / batch_id,
            paths.batches_root,
            "BATCH_PATH_OUTSIDE_LEDGER",
        )
        if final_root.exists():
            raise LobsError("IMMUTABLE_BATCH_ID_COLLISION", batch_id)
        staging = Path(
            tempfile.mkdtemp(prefix=".edge-lobs-stage-", dir=paths.ledger_root)
        ).resolve()
        _require_contained(staging, paths.ledger_root, "STAGING_PATH_OUTSIDE_LEDGER")
        try:
            sealed_at = _utc_now()
            source_manifest = _source_manifest(
                raw_inputs,
                observation_batch_id=batch_id,
                capture_mode=str(observation["capture_mode"]),
                ingested_at=sealed_at,
            )
            batch_manifest, batch_manifest_hash = _write_staged_bundle(
                staging,
                observation=observation,
                source_manifest=source_manifest,
                validation_report=validation_report,
                raw_inputs=raw_inputs,
                sealed_at=sealed_at,
            )
            for raw in raw_inputs:
                if raw.path.stat().st_size != raw.byte_length or sha256_file(raw.path) != raw.sha256:
                    raise LobsError(
                        "SOURCE_CHANGED_DURING_IMPORT",
                        str(raw.entry["source_id"]),
                        path=str(raw.path),
                    )
                staged_raw = staging / "raw" / raw.sha256
                if staged_raw.stat().st_size != raw.byte_length or sha256_file(staged_raw) != raw.sha256:
                    raise LobsError(
                        "STAGED_SOURCE_HASH_MISMATCH", str(raw.entry["source_id"])
                    )
            if final_root.exists():
                raise LobsError("IMMUTABLE_BATCH_ID_COLLISION", batch_id)
            os.replace(staging, final_root)
            committed = True
            staging = None
            register_records = _load_register(paths)
            previous_hash = register_records[-1]["record_sha256"] if register_records else "0" * 64
            event_body = {
                "schema_version": REGISTER_SCHEMA_VERSION,
                "event_type": "SEALED",
                "previous_record_sha256": previous_hash,
                "observation_batch_id": batch_id,
                "batch_manifest_sha256": batch_manifest_hash,
                "observation_ids": list(batch_manifest["observation_ids"]),
                "source_ids": list(batch_manifest["source_ids"]),
                "source_identities": list(batch_manifest["source_identities"]),
                "source_hashes": list(batch_manifest["source_hashes"]),
                "recorded_at_utc": sealed_at,
                "actor": actor,
            }
            record = _append_register(paths, event_body)
            committed_state = _verify_ledger_unlocked(paths)
            _write_index_unlocked(paths, committed_state)
            final_state = _verify_ledger_unlocked(paths)
            if final_state != committed_state:
                raise LobsError(
                    "POST_COMMIT_VERIFICATION_CHANGED",
                    "authoritative ledger changed during index materialisation",
                )
            return SealedBatch(
                observation_batch_id=batch_id,
                root=final_root,
                batch_manifest_path=final_root / "batch_manifest.json",
                batch_manifest_sha256=batch_manifest_hash,
                register_record_sha256=str(record["record_sha256"]),
                index_path=paths.index_path,
            )
        finally:
            if not committed and staging is not None and staging.exists():
                _require_contained(
                    staging, paths.ledger_root, "STAGING_CLEANUP_OUTSIDE_LEDGER"
                )
                shutil.rmtree(staging)


def verify_ledger(repository_root: str | Path) -> dict[str, Any]:
    """Verify the complete authoritative ledger and exclude every orphan."""

    paths = LedgerPaths.from_repository(repository_root)
    if not paths.ledger_root.exists():
        return {
            "schema_version": LEDGER_SCHEMA_VERSION,
            "state": "VERIFIED",
            "batch_count": 0,
            "register_sha256": sha256_bytes(b""),
            "batches": [],
        }
    with _exclusive_lock(paths):
        return _verify_ledger_unlocked(paths)


def rebuild_index(repository_root: str | Path) -> dict[str, Any]:
    """Rebuild the non-authoritative index from verified seals and bundles."""

    paths = LedgerPaths.from_repository(repository_root)
    with _exclusive_lock(paths):
        verified = _verify_ledger_unlocked(paths)
        return _write_index_unlocked(paths, verified)


# Concise alias used by the command layer.
import_batch = import_observation_batch


__all__ = [
    "LedgerPaths",
    "SealedBatch",
    "import_batch",
    "import_observation_batch",
    "rebuild_index",
    "verify_ledger",
]
