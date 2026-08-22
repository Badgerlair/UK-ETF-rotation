"""Strict and deterministic JSON I/O for immutable ledger artifacts."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from edge_mdm.fingerprint import canonical_json_bytes as _canonical_json_bytes

from .errors import LobsError


class _DuplicateKeyError(ValueError):
    pass


class _NonFiniteNumberError(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(key)
        result[key] = value
    return result


def _reject_constant(token: str) -> Any:
    raise _NonFiniteNumberError(token)


def _finite_float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise _NonFiniteNumberError(token)
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Return Project EDGE canonical UTF-8 JSON bytes without a newline."""

    try:
        return _canonical_json_bytes(value)
    except (TypeError, ValueError) as exc:
        raise LobsError("NON_CANONICAL_JSON", str(exc)) from exc


def load_json_object(path: str | Path) -> dict[str, Any]:
    """Strict-load one UTF-8 JSON object.

    Duplicate object keys and all non-finite numeric representations are hard
    failures.  A top-level array or scalar is not an admissible document.
    """

    source = Path(path)
    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise LobsError("JSON_READ_FAILED", str(exc), path=str(source)) from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LobsError(
            "JSON_NOT_UTF8", "document must be valid UTF-8", path=str(source)
        ) from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
        )
    except _DuplicateKeyError as exc:
        raise LobsError(
            "DUPLICATE_JSON_KEY",
            f"duplicate object key {exc.args[0]!r}",
            path=str(source),
        ) from exc
    except _NonFiniteNumberError as exc:
        raise LobsError(
            "NONFINITE_JSON_NUMBER",
            f"non-finite JSON number {exc.args[0]!r} is prohibited",
            path=str(source),
        ) from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise LobsError("INVALID_JSON", str(exc), path=str(source)) from exc
    if not isinstance(value, dict):
        raise LobsError(
            "JSON_OBJECT_REQUIRED",
            "top-level JSON value must be an object",
            path=str(source),
        )
    return value


def write_canonical_json_new(path: str | Path, value: Any) -> None:
    """Create one canonical JSON file exclusively and durably.

    The helper never overwrites an existing path.  Callers are responsible for
    creating and validating the containing staging directory.
    """

    target = Path(path)
    encoded = canonical_json_bytes(value) + b"\n"
    try:
        with target.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise LobsError(
            "IMMUTABLE_PATH_EXISTS",
            "exclusive canonical JSON write refused to overwrite an existing path",
            path=str(target),
        ) from exc
    except OSError as exc:
        raise LobsError("JSON_WRITE_FAILED", str(exc), path=str(target)) from exc
