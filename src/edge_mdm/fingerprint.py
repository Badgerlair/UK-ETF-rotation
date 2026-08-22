"""Deterministic fingerprints for scientific source and logical data."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
import math
from pathlib import Path, PurePath
from typing import Any, BinaryIO


SCHEMA_FINGERPRINT_VERSION = "edge-schema-v1"
LOGICAL_ROWS_FINGERPRINT_VERSION = "edge-logical-rows-v1-text"
SOFTWARE_FINGERPRINT_VERSION = "edge-python-source-v1"
_READ_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class LogicalRowsFingerprint:
    version: str
    row_count: int
    sha256: str


def _normalise(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("NaN and infinity cannot be fingerprinted")
        return {"$float_hex": value.hex()}
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite Decimal cannot be fingerprinted")
        return {"$decimal": format(value, "f")}
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("naive datetime cannot be fingerprinted")
        rendered = value.astimezone(timezone.utc).isoformat(timespec="microseconds")
        return {"$datetime_utc": rendered.replace("+00:00", "Z")}
    if isinstance(value, date):
        return {"$date": value.isoformat()}
    if isinstance(value, time):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("naive time cannot be fingerprinted")
        return {"$time": value.isoformat(timespec="microseconds")}
    if isinstance(value, Enum):
        return _normalise(value.value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"$bytes_hex": bytes(value).hex()}
    if isinstance(value, PurePath):
        return {"$path": value.as_posix()}
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _normalise(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical JSON mapping keys must be strings")
            result[key] = _normalise(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_normalise(item) for item in value]
    raise TypeError(f"unsupported canonical JSON type: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """Return a single canonical UTF-8 JSON representation.

    Object keys are sorted, insignificant whitespace is removed, and values
    with scientific encoding ambiguity receive explicit tagged encodings.
    """

    return json.dumps(
        _normalise(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hash_stream(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    while chunk := stream.read(_READ_CHUNK_BYTES):
        digest.update(chunk)
    return digest.hexdigest()


def sha256_file(path: str | Path) -> str:
    resolved = Path(path)
    with resolved.open("rb") as stream:
        return _hash_stream(stream)


def package_source_fingerprint(package_root: str | Path | None = None) -> str:
    """Fingerprint the exact Python implementation used for a build."""

    root = (
        Path(package_root).resolve()
        if package_root is not None
        else Path(__file__).resolve().parent
    )
    files = sorted(path for path in root.rglob("*.py") if path.is_file())
    if not files:
        raise ValueError(f"no Python sources beneath {root}")
    digest = hashlib.sha256()
    digest.update(canonical_json_bytes({"version": SOFTWARE_FINGERPRINT_VERSION}))
    digest.update(b"\n")
    for path in files:
        relative = path.relative_to(root).as_posix()
        digest.update(canonical_json_bytes({"path": relative, "bytes": path.stat().st_size}))
        digest.update(b"\n")
        with path.open("rb") as stream:
            while chunk := stream.read(_READ_CHUNK_BYTES):
                digest.update(chunk)
        digest.update(b"\n")
    return digest.hexdigest()


def schema_fingerprint(
    columns_and_types: Iterable[tuple[str, str]],
) -> str:
    """Fingerprint an ordered physical schema.

    Column order is intentionally significant because it affects the logical
    row encoding and downstream artifact contract.
    """

    schema = [
        {"name": str(name), "type": str(data_type)}
        for name, data_type in columns_and_types
    ]
    payload = {
        "version": SCHEMA_FINGERPRINT_VERSION,
        "columns": schema,
    }
    return sha256_bytes(canonical_json_bytes(payload))


def logical_rows_fingerprint(
    column_names: Sequence[str], rows: Iterable[Sequence[Any]]
) -> LogicalRowsFingerprint:
    """Fingerprint rows in the exact order supplied by the caller.

    Callers must first impose the table contract's deterministic sort order.
    Including the ordered column names prevents two different schemas with
    coincidentally equal row values from sharing a logical fingerprint.
    """

    names = tuple(column_names)
    if not names or any(not isinstance(name, str) or not name for name in names):
        raise ValueError("column_names must contain non-empty strings")
    if len(names) != len(set(names)):
        raise ValueError("column_names must be unique")

    digest = hashlib.sha256()
    digest.update(
        canonical_json_bytes(
            {
                "version": LOGICAL_ROWS_FINGERPRINT_VERSION,
                "columns": names,
            }
        )
    )
    digest.update(b"\n")
    row_count = 0
    for row_count, row in enumerate(rows, start=1):
        values = tuple(row)
        if len(values) != len(names):
            raise ValueError(
                f"row {row_count} has {len(values)} values; expected {len(names)}"
            )
        digest.update(canonical_json_bytes(values))
        digest.update(b"\n")
    return LogicalRowsFingerprint(
        version=LOGICAL_ROWS_FINGERPRINT_VERSION,
        row_count=row_count,
        sha256=digest.hexdigest(),
    )
