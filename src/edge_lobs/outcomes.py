"""Independent, fail-closed forward-outcome boundary for ``edge_lobs``.

Stage 1 defines clocks, maturity and lineage checks only.  It intentionally
contains no real price/outcome calculation and cannot turn caller-authored JSON
into admitted Project EDGE evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Iterable, Mapping, Sequence

from .errors import LobsError
from .jsonio import canonical_json_bytes, write_canonical_json_new
from .mdm import (
    STRUCTURAL_VALIDATION_ONLY,
    TEST_ONLY_CLASSIFICATION,
    TestOnlyValidationReport,
    _batch_value,
    _reject_authority_claims,
    _require_sha256,
    _required_mapping,
    _required_sequence,
    _required_text,
    _scoped_tradable_sessions,
    parse_aware_timestamp,
    require_production_mdm_access,
)


OUTCOME_SCHEMA_VERSION = "edge.leadership_forward_outcomes.v1"
OUTCOME_ARTIFACT_MANIFEST_SCHEMA_VERSION = (
    "edge.leadership_forward_outcome_artifact_manifest.v1"
)
OUTCOME_LAYER = "FORWARD_OUTCOME"
ALLOWED_HORIZONS = frozenset({1, 3, 5, 10, 20, 40, 60})

_SOURCE_PAYLOAD_KEYS = frozenset(
    {
        "source_text",
        "source_role",
        "source_classification",
        "setup_state",
        "market",
        "instruments",
        "groups",
        "stocks",
        "futures_snapshot",
        "macro_context",
        "source_observations",
        "observation_records",
    }
)


@dataclass(frozen=True, slots=True)
class OutcomeWindow:
    """Mechanically derived trading-session window for one horizon."""

    exchange_id: str
    horizon_sessions: int
    information_cutoff_timestamp: str
    first_contributing_at: str
    start_session: str
    end_session: str
    maturity_timestamp: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "exchange_id": self.exchange_id,
            "horizon_sessions": self.horizon_sessions,
            "information_cutoff_timestamp": self.information_cutoff_timestamp,
            "first_contributing_at": self.first_contributing_at,
            "start_session": self.start_session,
            "end_session": self.end_session,
            "maturity_timestamp": self.maturity_timestamp,
        }


@dataclass(frozen=True, slots=True)
class TestOnlyOutcomeArtifact:
    """One immutable, explicitly non-authoritative outcome artifact."""

    artifact_id: str
    artifact_root: Path
    payload_path: Path
    manifest_path: Path
    payload_sha256: str
    manifest_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_root": str(self.artifact_root),
            "payload_path": str(self.payload_path),
            "manifest_path": str(self.manifest_path),
            "payload_sha256": self.payload_sha256,
            "manifest_sha256": self.manifest_sha256,
            "classification": TEST_ONLY_CLASSIFICATION,
            "production_use_permitted": False,
            "research_use_permitted": False,
            "admission_status": STRUCTURAL_VALIDATION_ONLY,
        }


def _utc_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def validate_outcome_horizon(value: Any) -> int:
    """Return an allowed integer trading-session horizon."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise LobsError("OUTCOME_HORIZON_INVALID", "horizon must be an integer")
    if value not in ALLOWED_HORIZONS:
        raise LobsError(
            "OUTCOME_HORIZON_NOT_ALLOWED",
            f"horizon must be one of {sorted(ALLOWED_HORIZONS)}",
        )
    return value


def _future_sessions_known_at_cutoff(
    session_rows: Iterable[Mapping[str, Any]],
    *,
    information_cutoff_timestamp: Any,
    exchange_id: str,
) -> tuple[datetime, list[dict[str, Any]]]:
    cutoff = parse_aware_timestamp(
        information_cutoff_timestamp, field="information_cutoff_timestamp"
    )
    sessions = _scoped_tradable_sessions(session_rows, exchange_id=exchange_id)
    eligible = [
        row
        for row in sessions
        if row["_available_at_utc"] <= cutoff and row["_open_at_utc"] > cutoff
    ]
    return cutoff, sorted(
        eligible, key=lambda row: (row["_open_at_utc"], row["session_date"])
    )


def derive_first_permissible_outcome_session(
    session_rows: Iterable[Mapping[str, Any]],
    *,
    information_cutoff_timestamp: Any,
    exchange_id: str,
) -> dict[str, Any]:
    """Select the first known tradable session opening strictly after cutoff."""

    _, eligible = _future_sessions_known_at_cutoff(
        session_rows,
        information_cutoff_timestamp=information_cutoff_timestamp,
        exchange_id=exchange_id,
    )
    if not eligible:
        raise LobsError(
            "FIRST_OUTCOME_SESSION_UNAVAILABLE",
            "no admitted tradable session opens strictly after the information cutoff",
        )
    return {key: value for key, value in eligible[0].items() if not key.startswith("_")}


def derive_outcome_window(
    session_rows: Iterable[Mapping[str, Any]],
    *,
    information_cutoff_timestamp: Any,
    exchange_id: str,
    horizon_sessions: int,
) -> OutcomeWindow:
    """Derive start, end and maturity without inspecting any future outcome."""

    horizon = validate_outcome_horizon(horizon_sessions)
    cutoff, eligible = _future_sessions_known_at_cutoff(
        session_rows,
        information_cutoff_timestamp=information_cutoff_timestamp,
        exchange_id=exchange_id,
    )
    if len(eligible) < horizon:
        raise LobsError(
            "OUTCOME_HORIZON_SESSION_UNAVAILABLE",
            f"{horizon} known future trading sessions are required; found {len(eligible)}",
        )
    first = eligible[0]
    final = eligible[horizon - 1]
    return OutcomeWindow(
        exchange_id=exchange_id,
        horizon_sessions=horizon,
        information_cutoff_timestamp=_utc_text(cutoff),
        first_contributing_at=_utc_text(first["_open_at_utc"]),
        start_session=str(first["session_date"]),
        end_session=str(final["session_date"]),
        maturity_timestamp=_utc_text(final["_cutoff_at_utc"]),
    )


def assert_outcome_mature(
    window: OutcomeWindow, *, calculation_timestamp: Any
) -> datetime:
    """Fail unless the final governed session cutoff has elapsed."""

    calculated = parse_aware_timestamp(
        calculation_timestamp, field="calculation_timestamp"
    )
    maturity = parse_aware_timestamp(
        window.maturity_timestamp, field="maturity_timestamp"
    )
    if calculated < maturity:
        raise LobsError(
            "OUTCOME_HORIZON_NOT_MATURE",
            "the final required session cutoff has not elapsed",
        )
    return calculated


def _reject_embedded_source_payload(value: Any, *, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            child = f"{path}.{key}"
            if str(key).casefold() in _SOURCE_PAYLOAD_KEYS:
                raise LobsError(
                    "SOURCE_PAYLOAD_FORBIDDEN_IN_OUTCOME",
                    f"outcome documents may reference but not embed source observations: {child}",
                )
            _reject_embedded_source_payload(item, path=child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_embedded_source_payload(item, path=f"{path}[{index}]")


def _require_row_sequence(value: Any) -> Sequence[Any]:
    rows = _required_sequence(value, field="rows")
    if not rows:
        raise LobsError("OUTCOME_ROWS_REQUIRED", "rows must not be empty")
    return rows


def validate_test_only_outcomes(
    document: Mapping[str, Any],
    *,
    batch_manifest: Mapping[str, Any],
    session_rows: Iterable[Mapping[str, Any]],
) -> TestOnlyValidationReport:
    """Validate outcome clocks/lineage while permanently retaining test status."""

    value = _required_mapping(document, field="outcomes")
    _reject_authority_claims(value)
    _reject_embedded_source_payload(value)
    if value.get("schema_version") != OUTCOME_SCHEMA_VERSION:
        raise LobsError("OUTCOME_SCHEMA_VERSION_INVALID", "unsupported outcome schema")
    if value.get("classification") != TEST_ONLY_CLASSIFICATION:
        raise LobsError(
            "TEST_ONLY_CLASSIFICATION_REQUIRED",
            "caller-authored outcomes must be explicitly test-only",
        )
    if value.get("production_use_permitted") is not False:
        raise LobsError(
            "TEST_ONLY_SELF_AUTHORISATION_FORBIDDEN",
            "production_use_permitted must be false",
        )
    if value.get("research_use_permitted") is not False:
        raise LobsError(
            "TEST_ONLY_SELF_AUTHORISATION_FORBIDDEN",
            "research_use_permitted must be false",
        )
    if value.get("admission_status") != STRUCTURAL_VALIDATION_ONLY:
        raise LobsError(
            "TEST_ONLY_SELF_AUTHORISATION_FORBIDDEN",
            f"admission_status must equal {STRUCTURAL_VALIDATION_ONLY}",
        )

    batch_id = _required_text(value.get("observation_batch_id"), field="observation_batch_id")
    if batch_id != str(_batch_value(batch_manifest, "observation_batch_id")):
        raise LobsError("OUTCOME_BATCH_MISMATCH", "observation batch identity differs")
    cutoff = parse_aware_timestamp(
        value.get("information_cutoff_timestamp"),
        field="information_cutoff_timestamp",
    )
    batch_cutoff = parse_aware_timestamp(
        _batch_value(batch_manifest, "information_cutoff_timestamp"),
        field="batch_manifest.information_cutoff_timestamp",
    )
    if cutoff != batch_cutoff:
        raise LobsError("OUTCOME_CUTOFF_MISMATCH", "batch and outcome cutoffs differ")

    exchange_id = _required_text(value.get("exchange_id"), field="exchange_id")
    calculated = parse_aware_timestamp(
        value.get("calculation_timestamp"), field="calculation_timestamp"
    )
    source_snapshot_id = _required_text(value.get("source_snapshot_id"), field="source_snapshot_id")
    _require_sha256(value.get("source_manifest_sha256"), field="source_manifest_sha256")
    _require_sha256(value.get("source_artifact_manifest_sha256"), field="source_artifact_manifest_sha256")
    _require_sha256(value.get("software_source_sha256"), field="software_source_sha256")

    rows = _require_row_sequence(value.get("rows"))
    seen_ids: set[str] = set()
    for index, raw in enumerate(rows):
        row = _required_mapping(raw, field=f"rows[{index}]")
        outcome_id = _required_text(row.get("outcome_id"), field=f"rows[{index}].outcome_id")
        if outcome_id in seen_ids:
            raise LobsError("DUPLICATE_OUTCOME_ID", f"duplicate outcome_id {outcome_id!r}")
        seen_ids.add(outcome_id)
        if row.get("layer") != OUTCOME_LAYER:
            raise LobsError(
                "OUTCOME_LAYER_INVALID", f"rows[{index}].layer must equal {OUTCOME_LAYER}"
            )
        _required_text(
            row.get("outcome_definition_id"),
            field=f"rows[{index}].outcome_definition_id",
        )
        _required_text(
            row.get("outcome_definition_version"),
            field=f"rows[{index}].outcome_definition_version",
        )
        if str(row.get("source_snapshot_id", "")) != source_snapshot_id:
            raise LobsError("OUTCOME_LINEAGE_MISMATCH", f"rows[{index}] snapshot differs")

        horizon = validate_outcome_horizon(row.get("horizon_sessions"))
        window = derive_outcome_window(
            session_rows,
            information_cutoff_timestamp=cutoff,
            exchange_id=exchange_id,
            horizon_sessions=horizon,
        )
        expected = window.as_dict()
        for field in (
            "first_contributing_at",
            "start_session",
            "end_session",
            "maturity_timestamp",
        ):
            actual = _required_text(row.get(field), field=f"rows[{index}].{field}")
            if field.endswith("_at") or field == "maturity_timestamp":
                if parse_aware_timestamp(actual, field=f"rows[{index}].{field}") != parse_aware_timestamp(
                    expected[field], field=f"derived.{field}"
                ):
                    raise LobsError(
                        "OUTCOME_CLOCK_MISMATCH",
                        f"rows[{index}].{field} differs from the mechanical session clock",
                    )
            elif actual != expected[field]:
                raise LobsError(
                    "OUTCOME_CLOCK_MISMATCH",
                    f"rows[{index}].{field} differs from the mechanical session clock",
                )

        assert_outcome_mature(window, calculation_timestamp=calculated)
        max_available = parse_aware_timestamp(
            row.get("max_available_at"), field=f"rows[{index}].max_available_at"
        )
        if max_available > calculated:
            raise LobsError(
                "OUTCOME_INPUT_AFTER_CALCULATION",
                f"rows[{index}] uses a record unavailable at calculation time",
            )
        if parse_aware_timestamp(
            row.get("first_contributing_at"), field=f"rows[{index}].first_contributing_at"
        ) <= cutoff:
            raise LobsError(
                "OUTCOME_BEGINS_BEFORE_CUTOFF",
                f"rows[{index}] begins before or at the information cutoff",
            )

    return TestOnlyValidationReport(
        document_type="FORWARD_OUTCOMES",
        state="TEST_ONLY_STRUCTURALLY_VALID",
        checks=(
            "CALLER_CANNOT_SELF_AUTHORISE",
            "SOURCE_PAYLOAD_NOT_EMBEDDED",
            "MECHANICAL_OUTCOME_START_DERIVED",
            "ALLOWED_HORIZON",
            "HORIZON_MATURE",
            "CALCULATION_AVAILABILITY_BOUNDED",
        ),
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_contained(path: Path, root: Path, *, code: str) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise LobsError(code, "path escapes the authorised outcome root", path=str(path)) from exc


def _resolve_test_only_outcome_root(
    repository_root: str | Path,
    output_root: str | Path | None,
) -> tuple[Path, Path]:
    try:
        repository = Path(repository_root).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise LobsError("REPOSITORY_ROOT_INVALID", "repository root does not resolve") from exc
    if not repository.is_dir():
        raise LobsError(
            "REPOSITORY_ROOT_INVALID",
            "repository root must be a directory",
            path=str(repository),
        )

    authorised = (
        repository / "research" / "leadership_rotation" / "outcomes"
    ).resolve(strict=False)
    if output_root is None:
        selected = authorised / "test_only"
    else:
        supplied = Path(output_root)
        selected = supplied if supplied.is_absolute() else repository / supplied
    selected = selected.resolve(strict=False)
    _require_contained(authorised, repository, code="OUTCOME_ROOT_OUTSIDE_REPOSITORY")
    _require_contained(selected, authorised, code="OUTCOME_ROOT_NOT_SEPARATE")
    try:
        selected.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise LobsError(
            "OUTCOME_ROOT_CREATE_FAILED", str(exc), path=str(selected)
        ) from exc
    selected = selected.resolve(strict=True)
    _require_contained(selected, authorised, code="OUTCOME_ROOT_NOT_SEPARATE")
    return repository, selected


def _open_exclusive_claim(path: Path) -> int:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.write(descriptor, b"TEST_ONLY_OUTCOME_MATERIALISATION\n")
        os.fsync(descriptor)
        return descriptor
    except FileExistsError as exc:
        raise LobsError(
            "OUTCOME_ARTIFACT_WRITE_IN_PROGRESS",
            "an exclusive materialisation claim already exists",
            path=str(path),
        ) from exc
    except OSError as exc:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise LobsError("OUTCOME_CLAIM_FAILED", str(exc), path=str(path)) from exc


def _verify_staged_outcome_artifact(
    *,
    staging: Path,
    payload_sha256: str,
    manifest_sha256: str,
) -> None:
    payload_path = staging / "outcomes.json"
    manifest_path = staging / "artifact_manifest.json"
    try:
        actual_payload = _sha256_bytes(payload_path.read_bytes())
        actual_manifest = _sha256_bytes(manifest_path.read_bytes())
    except OSError as exc:
        raise LobsError(
            "OUTCOME_ARTIFACT_VERIFY_FAILED", str(exc), path=str(staging)
        ) from exc
    if actual_payload != payload_sha256:
        raise LobsError(
            "OUTCOME_PAYLOAD_CHANGED_DURING_WRITE",
            "staged canonical outcome payload hash changed",
            path=str(payload_path),
        )
    if actual_manifest != manifest_sha256:
        raise LobsError(
            "OUTCOME_MANIFEST_CHANGED_DURING_WRITE",
            "staged outcome manifest hash changed",
            path=str(manifest_path),
        )


def materialise_test_only_outcomes(
    document: Mapping[str, Any],
    *,
    batch_manifest: Mapping[str, Any],
    session_rows: Iterable[Mapping[str, Any]],
    repository_root: str | Path,
    output_root: str | Path | None = None,
) -> TestOnlyOutcomeArtifact:
    """Atomically store one immutable, structurally validated test artifact.

    The directory identity is the full SHA-256 of the exact canonical payload
    bytes.  This path cannot release, admit, or make the values research-usable;
    its classification and false authority flags are repeated in the manifest.
    A custom output root, when supplied, must remain under the repository's
    dedicated ``research/leadership_rotation/outcomes`` tree.
    """

    rows = list(session_rows)
    validate_test_only_outcomes(
        document,
        batch_manifest=batch_manifest,
        session_rows=rows,
    )
    value = dict(document)
    payload_bytes = canonical_json_bytes(value) + b"\n"
    payload_sha256 = _sha256_bytes(payload_bytes)
    artifact_id = "EDGE-LOUT-" + payload_sha256.upper()
    _, destination_root = _resolve_test_only_outcome_root(
        repository_root, output_root
    )
    final_root = destination_root / artifact_id
    _require_contained(
        final_root, destination_root, code="OUTCOME_ARTIFACT_OUTSIDE_ROOT"
    )
    if final_root.exists():
        raise LobsError(
            "IMMUTABLE_OUTCOME_ARTIFACT_EXISTS",
            "content-derived outcome artifact already exists; overwrite refused",
            path=str(final_root),
        )

    claim_path = destination_root / f".{artifact_id}.claim"
    claim_descriptor = _open_exclusive_claim(claim_path)
    staging: Path | None = None
    committed = False
    try:
        if final_root.exists():
            raise LobsError(
                "IMMUTABLE_OUTCOME_ARTIFACT_EXISTS",
                "content-derived outcome artifact already exists; overwrite refused",
                path=str(final_root),
            )
        staging = Path(
            tempfile.mkdtemp(
                prefix=f".{artifact_id}.staging-", dir=str(destination_root)
            )
        ).resolve(strict=True)
        _require_contained(
            staging, destination_root, code="OUTCOME_STAGING_OUTSIDE_ROOT"
        )
        payload_path = staging / "outcomes.json"
        write_canonical_json_new(payload_path, value)
        if _sha256_bytes(payload_path.read_bytes()) != payload_sha256:
            raise LobsError(
                "OUTCOME_PAYLOAD_WRITE_MISMATCH",
                "canonical payload bytes do not match the content-derived identity",
                path=str(payload_path),
            )

        manifest = {
            "schema_version": OUTCOME_ARTIFACT_MANIFEST_SCHEMA_VERSION,
            "artifact_id": artifact_id,
            "artifact_type": "TEST_ONLY_FORWARD_OUTCOMES",
            "classification": TEST_ONLY_CLASSIFICATION,
            "production_use_permitted": False,
            "research_use_permitted": False,
            "admission_status": STRUCTURAL_VALIDATION_ONLY,
            "observation_batch_id": _required_text(
                value.get("observation_batch_id"), field="observation_batch_id"
            ),
            "information_cutoff_timestamp": _required_text(
                value.get("information_cutoff_timestamp"),
                field="information_cutoff_timestamp",
            ),
            "payload_content_sha256": payload_sha256,
            "files": [
                {
                    "path": "outcomes.json",
                    "bytes": len(payload_bytes),
                    "sha256": payload_sha256,
                }
            ],
        }
        manifest_path = staging / "artifact_manifest.json"
        write_canonical_json_new(manifest_path, manifest)
        manifest_sha256 = _sha256_bytes(manifest_path.read_bytes())
        _verify_staged_outcome_artifact(
            staging=staging,
            payload_sha256=payload_sha256,
            manifest_sha256=manifest_sha256,
        )
        try:
            staging.rename(final_root)
        except FileExistsError as exc:
            raise LobsError(
                "IMMUTABLE_OUTCOME_ARTIFACT_EXISTS",
                "content-derived outcome artifact already exists; overwrite refused",
                path=str(final_root),
            ) from exc
        except OSError as exc:
            raise LobsError(
                "OUTCOME_ARTIFACT_COMMIT_FAILED", str(exc), path=str(final_root)
            ) from exc
        committed = True
        staging = None

        payload_path = final_root / "outcomes.json"
        manifest_path = final_root / "artifact_manifest.json"
        _verify_staged_outcome_artifact(
            staging=final_root,
            payload_sha256=payload_sha256,
            manifest_sha256=manifest_sha256,
        )
        return TestOnlyOutcomeArtifact(
            artifact_id=artifact_id,
            artifact_root=final_root,
            payload_path=payload_path,
            manifest_path=manifest_path,
            payload_sha256=payload_sha256,
            manifest_sha256=manifest_sha256,
        )
    finally:
        try:
            os.close(claim_descriptor)
        except OSError:
            pass
        try:
            claim_path.unlink(missing_ok=True)
        except OSError:
            pass
        if not committed and staging is not None and staging.exists():
            _require_contained(
                staging, destination_root, code="OUTCOME_STAGING_OUTSIDE_ROOT"
            )
            shutil.rmtree(staging)


def materialise_production_outcomes(
    *,
    artifact: Any,
    repository_root: str,
    register_path: str,
    source_snapshot: Any,
    production_scope: Any,
) -> None:
    """Guard the intentionally unimplemented real outcome path."""

    require_production_mdm_access(
        artifact=artifact,
        repository_root=repository_root,
        register_path=register_path,
        source_snapshot=source_snapshot,
        production_scope=production_scope,
    )
    raise LobsError(
        "OUTCOME_CALCULATION_NOT_IMPLEMENTED",
        "Stage 1 contains no real forward-outcome calculation",
    )


__all__ = [
    "ALLOWED_HORIZONS",
    "OUTCOME_ARTIFACT_MANIFEST_SCHEMA_VERSION",
    "OUTCOME_LAYER",
    "OUTCOME_SCHEMA_VERSION",
    "OutcomeWindow",
    "TestOnlyOutcomeArtifact",
    "assert_outcome_mature",
    "derive_first_permissible_outcome_session",
    "derive_outcome_window",
    "materialise_production_outcomes",
    "materialise_test_only_outcomes",
    "validate_outcome_horizon",
    "validate_test_only_outcomes",
]
