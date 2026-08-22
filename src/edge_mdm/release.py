"""Immutable artifact materialisation and fail-closed release access."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import shutil
import tempfile
from typing import Any, Iterable, Mapping, Sequence

import duckdb

from .actions import RETURN_COLUMNS
from .assemble import PANEL_COLUMNS
from .fingerprint import (
    canonical_json_bytes,
    logical_rows_fingerprint,
    package_source_fingerprint,
    sha256_bytes,
    sha256_file,
)
from .lineage import FIELD_LINEAGE_VERSION, PANEL_FIELD_LINEAGE
from .pipeline import (
    DailySliceBuild,
    DailySliceRequest,
    PIPELINE_VERSION,
    REQUEST_SCHEMA_VERSION,
    build_daily_slice,
)
from .scope import (
    ProductionScopeApproval,
    assert_repository_production_gate_open,
)
from .source import SourceValidationError, VerifiedMdmSnapshot, verify_mdm_snapshot
from .universe import UNIVERSE_COLUMNS
from .validation import (
    HARD_FAILURE_CODES,
    AdmissionEvidence,
    validate_daily_release,
)


ARTIFACT_MANIFEST_VERSION = "edge.feature_ready_artifact.v1"
RELEASE_REGISTER_VERSION = "edge.release_register.v1"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_DATASET_CONTRACTS: Mapping[str, tuple[str, tuple[str, ...], tuple[str, ...]]] = {
    "historical_universe": (
        "historical_universe.parquet",
        UNIVERSE_COLUMNS,
        ("session_date", "exchange_id", "security_id"),
    ),
    "observable_panel": (
        "observable_panel.parquet",
        PANEL_COLUMNS,
        ("session_date", "security_id"),
    ),
    "return_consistent_view": (
        "return_consistent_view.parquet",
        RETURN_COLUMNS,
        ("session_date", "security_id"),
    ),
}

_SUPPORTING_FILES = frozenset(
    {"request.json", "lineage.json", "validation_report.json", "join_audit.json"}
)
_REQUIRED_PAYLOAD_FILES = frozenset(
    {contract[0] for contract in _DATASET_CONTRACTS.values()}
) | _SUPPORTING_FILES

_ARTIFACT_MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "artifact_id",
        "artifact_state",
        "production_use_permitted",
        "source_kind",
        "source_snapshot_id",
        "source_manifest_sha256",
        "request_id",
        "builder_id",
        "pipeline_version",
        "software_source_sha256",
        "production_scope_approval_id",
        "environment",
        "logical_fingerprints",
        "replay_fingerprints",
        "materialized_datasets",
        "validation_state",
        "population",
        "files",
        "limitations",
    }
)


class ReleaseError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class MaterialisedArtifact:
    artifact_id: str
    root: Path
    manifest_path: Path
    manifest_sha256: str
    manifest: Mapping[str, Any]

    @property
    def production_use_permitted(self) -> bool:
        return bool(self.manifest.get("production_use_permitted"))


_PANEL_TYPES: Mapping[str, str] = {
    **{name: "VARCHAR" for name in PANEL_COLUMNS},
    "session_date": "DATE",
    "previous_session_date": "DATE",
    "next_session_date": "DATE",
    "open_at": "TIMESTAMP WITH TIME ZONE",
    "close_at": "TIMESTAMP WITH TIME ZONE",
    "cutoff_at": "TIMESTAMP WITH TIME ZONE",
    "primary_listing": "BOOLEAN",
    "candidate": "BOOLEAN",
    "eligible": "BOOLEAN",
    "open": "DECIMAL(18,6)",
    "high": "DECIMAL(18,6)",
    "low": "DECIMAL(18,6)",
    "close": "DECIMAL(18,6)",
    "volume": "BIGINT",
}

_RETURN_DECIMALS = frozenset(
    {
        "previous_close",
        "raw_close",
        "raw_return_1d",
        "split_multiplier",
        "split_consistent_volume",
        "price_return_1d",
        "distribution_return_1d",
        "terminal_return",
        "total_return_1d",
    }
)


def _ensure_inside(path: Path, repository_root: Path, code: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(repository_root):
        raise ReleaseError(code, f"path leaves repository: {resolved}")
    return resolved


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _write_parquet(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[str],
    types: Mapping[str, str],
) -> None:
    definitions = ", ".join(f'"{name}" {types[name]}' for name in columns)
    placeholders = ", ".join("?" for _ in columns)
    with duckdb.connect(database=":memory:") as connection:
        connection.execute("SET threads = 1")
        connection.execute("SET TimeZone = 'UTC'")
        connection.execute(f"CREATE TABLE output ({definitions})")
        if rows:
            connection.executemany(
                f"INSERT INTO output VALUES ({placeholders})",
                [tuple(row.get(column) for column in columns) for row in rows],
            )
        connection.execute(
            "COPY output TO ? (FORMAT PARQUET, COMPRESSION ZSTD)", [str(path)]
        )


def _universe_types(columns: Iterable[str]) -> dict[str, str]:
    result = {name: "VARCHAR" for name in columns}
    for name in ("session_date", "previous_session_date", "next_session_date"):
        if name in result:
            result[name] = "DATE"
    for name in ("open_at", "close_at", "cutoff_at"):
        if name in result:
            result[name] = "TIMESTAMP WITH TIME ZONE"
    for name in ("primary_listing", "candidate", "eligible"):
        if name in result:
            result[name] = "BOOLEAN"
    return result


def _return_types(columns: Iterable[str]) -> dict[str, str]:
    result = {name: "VARCHAR" for name in columns}
    if "session_date" in result:
        result["session_date"] = "DATE"
    for name in _RETURN_DECIMALS:
        if name in result:
            result[name] = "DECIMAL(38,12)"
    return result


def _dataset_types(dataset_name: str) -> Mapping[str, str]:
    if dataset_name == "historical_universe":
        return _universe_types(UNIVERSE_COLUMNS)
    if dataset_name == "observable_panel":
        return _PANEL_TYPES
    if dataset_name == "return_consistent_view":
        return _return_types(RETURN_COLUMNS)
    raise ReleaseError("ARTIFACT_DATASET_UNKNOWN", dataset_name)


def _parquet_profile(
    path: Path,
    *,
    columns: tuple[str, ...],
    types: Mapping[str, str],
    sort_keys: tuple[str, ...],
) -> dict[str, Any]:
    try:
        with duckdb.connect(database=":memory:") as connection:
            connection.execute("SET threads = 1")
            connection.execute("SET TimeZone = 'UTC'")
            relation = connection.read_parquet(str(path))
            actual_columns = tuple(str(name) for name in relation.columns)
            actual_types = tuple(str(kind) for kind in relation.types)
            expected_types = tuple(types[name] for name in columns)
            if actual_columns != columns or actual_types != expected_types:
                raise ReleaseError(
                    "ARTIFACT_PARQUET_SCHEMA_MISMATCH",
                    f"{path.name}: columns={actual_columns!r}, types={actual_types!r}",
                )
            projection = ", ".join(
                f'CAST("{name}" AS VARCHAR) AS "{name}"' for name in columns
            )
            order = ", ".join(
                f'"{name}" ASC NULLS FIRST' for name in sort_keys
            )
            cursor = connection.execute(
                f"SELECT {projection} FROM read_parquet(?) ORDER BY {order}",
                [str(path)],
            )
            logical = logical_rows_fingerprint(columns, cursor.fetchall())
    except ReleaseError:
        raise
    except (duckdb.Error, OSError, ValueError) as exc:
        raise ReleaseError("ARTIFACT_PARQUET_INVALID", path.name) from exc
    return {
        "columns": list(columns),
        "physical_types": list(expected_types),
        "sort_keys": list(sort_keys),
        "row_count": logical.row_count,
        "logical_sha256": logical.sha256,
    }


def _materialized_profiles_for_build(
    build: DailySliceBuild, directory: Path
) -> dict[str, dict[str, Any]]:
    """Materialise a build into a governed temporary directory for comparison."""

    paths = {
        "historical_universe": directory / "historical_universe.parquet",
        "observable_panel": directory / "observable_panel.parquet",
        "return_consistent_view": directory / "return_consistent_view.parquet",
    }
    _write_parquet(
        paths["historical_universe"],
        build.universe_rows,
        UNIVERSE_COLUMNS,
        _universe_types(UNIVERSE_COLUMNS),
    )
    _write_parquet(
        paths["observable_panel"],
        build.panel_rows,
        PANEL_COLUMNS,
        _PANEL_TYPES,
    )
    _write_parquet(
        paths["return_consistent_view"],
        build.return_rows,
        RETURN_COLUMNS,
        _return_types(RETURN_COLUMNS),
    )
    return {
        dataset_name: _parquet_profile(
            paths[dataset_name],
            columns=contract[1],
            types=_dataset_types(dataset_name),
            sort_keys=contract[2],
        )
        for dataset_name, contract in _DATASET_CONTRACTS.items()
    }


def _revalidate_build(build: DailySliceBuild) -> None:
    """Revalidate current build contents immediately before materialisation."""

    build.snapshot.assert_unchanged()
    current_source_hash = package_source_fingerprint()
    if build.software_source_sha256 != current_source_hash:
        raise ReleaseError(
            "SOFTWARE_CHANGED_SINCE_VALIDATION",
            "the implementation differs from the implementation that validated the build",
        )
    evidence = AdmissionEvidence(
        snapshot=build.snapshot,
        requested_fields=tuple(
            {"field_id": field, "alias": field}
            for field in build.request.requested_fields
        ),
        field_roles={
            field: str(PANEL_FIELD_LINEAGE[field]["role"])
            for field in PANEL_COLUMNS
        },
        lineage_manifest=build.lineage_manifest,
        first_fingerprints=build.fingerprints,
        replay_fingerprints=build.replay_fingerprints,
    )
    report = validate_daily_release(
        evidence=evidence,
        identity_rows=list(build.identity_rows),
        session_rows=list(build.session_rows),
        observation_rows=list(build.observation_rows),
        action_rows=list(build.action_rows),
        membership_rows=list(build.membership_rows),
        universe_rows=list(build.universe_rows),
        panel_rows=list(build.panel_rows),
        return_rows=list(build.return_rows),
    )
    if not report.passed or report.as_dict() != build.validation_report.as_dict():
        raise ReleaseError(
            "BUILD_CHANGED_AFTER_VALIDATION",
            "current rows, lineage, fingerprints, or validation decision differ",
        )


def _artifact_identity_from_values(
    *,
    source_snapshot_id: str,
    source_manifest_sha256: str,
    request: Mapping[str, Any],
    fingerprints: Mapping[str, str],
    software_source_sha256: str,
    production_scope_approval_id: str | None,
) -> str:
    payload = {
        "source_snapshot_id": source_snapshot_id,
        "source_manifest_sha256": source_manifest_sha256,
        "request": dict(request),
        "fingerprints": dict(fingerprints),
        "pipeline_version": PIPELINE_VERSION,
        "software_source_sha256": software_source_sha256,
        "production_scope_approval_id": production_scope_approval_id,
    }
    return "EDGE-" + sha256_bytes(canonical_json_bytes(payload))[:24].upper()


def _artifact_identity(build: DailySliceBuild) -> str:
    return _artifact_identity_from_values(
        source_snapshot_id=build.snapshot.manifest.snapshot_id,
        source_manifest_sha256=build.snapshot.manifest_sha256,
        request=build.request.as_dict(),
        fingerprints=build.fingerprints,
        software_source_sha256=build.software_source_sha256,
        production_scope_approval_id=build.production_scope_approval_id,
    )


def materialise_candidate(
    build: DailySliceBuild,
    *,
    repository_root: str | Path,
    output_root: str | Path,
    builder_id: str,
) -> MaterialisedArtifact:
    """Write a validated immutable candidate; never publish it implicitly."""

    if not builder_id.strip():
        raise ReleaseError("BUILDER_ID_REQUIRED", "builder identity is required")
    _revalidate_build(build)
    repo = Path(repository_root).resolve(strict=True)
    output = _ensure_inside(Path(output_root), repo, "OUTPUT_OUTSIDE_REPOSITORY")
    output.mkdir(parents=True, exist_ok=True)
    artifact_id = _artifact_identity(build)
    final_root = _ensure_inside(output / artifact_id, repo, "ARTIFACT_OUTSIDE_REPOSITORY")
    if final_root.exists():
        raise ReleaseError(
            "IMMUTABLE_ARTIFACT_EXISTS", f"artifact already exists: {artifact_id}"
        )
    temporary = Path(tempfile.mkdtemp(prefix=".edge-build-", dir=output)).resolve()
    _ensure_inside(temporary, output, "TEMPORARY_PATH_OUTSIDE_OUTPUT")
    try:
        artifact_paths = {
            "historical_universe": temporary / "historical_universe.parquet",
            "observable_panel": temporary / "observable_panel.parquet",
            "return_consistent_view": temporary / "return_consistent_view.parquet",
        }
        _write_parquet(
            artifact_paths["historical_universe"],
            build.universe_rows,
            UNIVERSE_COLUMNS,
            _universe_types(UNIVERSE_COLUMNS),
        )
        _write_parquet(
            artifact_paths["observable_panel"],
            build.panel_rows,
            PANEL_COLUMNS,
            _PANEL_TYPES,
        )
        _write_parquet(
            artifact_paths["return_consistent_view"],
            build.return_rows,
            RETURN_COLUMNS,
            _return_types(RETURN_COLUMNS),
        )

        materialized_datasets = {
            dataset_name: _parquet_profile(
                artifact_paths[dataset_name],
                columns=contract[1],
                types=_dataset_types(dataset_name),
                sort_keys=contract[2],
            )
            for dataset_name, contract in _DATASET_CONTRACTS.items()
        }

        supporting = {
            "request": temporary / "request.json",
            "lineage": temporary / "lineage.json",
            "validation": temporary / "validation_report.json",
            "join_audit": temporary / "join_audit.json",
        }
        _write_json(supporting["request"], build.request.as_dict())
        _write_json(supporting["lineage"], build.lineage_manifest)
        _write_json(supporting["validation"], build.validation_report.as_dict())
        _write_json(supporting["join_audit"], build.join_audit.as_dict())

        files = {
            path.name: {
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in sorted(
                [*artifact_paths.values(), *supporting.values()], key=lambda item: item.name
            )
        }
        production_permitted = build.production_release_permitted
        manifest = {
            "schema_version": ARTIFACT_MANIFEST_VERSION,
            "artifact_id": artifact_id,
            "artifact_state": (
                "READY_FOR_INDEPENDENT_REVIEW"
                if production_permitted
                else "TEST_EVIDENCE_NON_PRODUCTION"
            ),
            "production_use_permitted": production_permitted,
            "source_kind": build.snapshot.manifest.source_kind,
            "source_snapshot_id": build.snapshot.manifest.snapshot_id,
            "source_manifest_sha256": build.snapshot.manifest_sha256,
            "request_id": build.request.request_id,
            "builder_id": builder_id,
            "pipeline_version": PIPELINE_VERSION,
            "software_source_sha256": build.software_source_sha256,
            "production_scope_approval_id": build.production_scope_approval_id,
            "environment": {
                "python": platform.python_version(),
                "duckdb": duckdb.__version__,
                "platform": platform.platform(),
            },
            "logical_fingerprints": dict(build.fingerprints),
            "replay_fingerprints": dict(build.replay_fingerprints),
            "materialized_datasets": materialized_datasets,
            "validation_state": build.validation_report.state,
            "population": universe_counts_for_manifest(build),
            "files": files,
            "limitations": (
                ["SYNTHETIC_TEST_DATA_MUST_NOT_ENTER_RESEARCH"]
                if not production_permitted
                else []
            ),
        }
        manifest_path = temporary / "artifact_manifest.json"
        _write_json(manifest_path, manifest)
        manifest_sha256 = sha256_file(manifest_path)
        os.replace(temporary, final_root)
        return MaterialisedArtifact(
            artifact_id=artifact_id,
            root=final_root,
            manifest_path=final_root / manifest_path.name,
            manifest_sha256=manifest_sha256,
            manifest=manifest,
        )
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise


def universe_counts_for_manifest(build: DailySliceBuild) -> dict[str, int]:
    return {
        "universe_rows": len(build.universe_rows),
        "candidate_rows": sum(bool(row["candidate"]) for row in build.universe_rows),
        "eligible_rows": sum(bool(row["eligible"]) for row in build.universe_rows),
        "observable_panel_rows": len(build.panel_rows),
        "return_view_rows": len(build.return_rows),
    }


def record_failed_build_attempt(
    *,
    repository_root: str | Path,
    output_root: str | Path,
    stage: str,
    error: Exception,
    context: Mapping[str, Any],
) -> Path:
    """Retain a typed immutable failure record without retaining unsafe output."""

    repo = Path(repository_root).resolve(strict=True)
    output = _ensure_inside(Path(output_root), repo, "OUTPUT_OUTSIDE_REPOSITORY")
    failures = _ensure_inside(
        output / "failed_attempts", repo, "FAILURE_EVIDENCE_OUTSIDE_REPOSITORY"
    )
    failures.mkdir(parents=True, exist_ok=True)
    recorded_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    body = {
        "schema_version": "edge.failed_build_attempt.v1",
        "recorded_at_utc": recorded_at,
        "stage": stage,
        "error_type": type(error).__name__,
        "error_code": getattr(error, "code", "UNCLASSIFIED_FAILURE"),
        "message": str(error),
        "software_source_sha256": package_source_fingerprint(),
        "context": dict(context),
    }
    digest = sha256_bytes(canonical_json_bytes(body))
    target = failures / f"EDGE-FAILED-{digest[:24].upper()}.json"
    try:
        with target.open("xb") as stream:
            stream.write(canonical_json_bytes({**body, "record_sha256": digest}) + b"\n")
    except FileExistsError as exc:
        raise ReleaseError("FAILURE_EVIDENCE_ID_COLLISION", str(target)) from exc
    return target


def _load_register(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    previous = "0" * 64
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReleaseError(
                "RELEASE_REGISTER_INVALID", f"invalid JSON at line {line_number}"
            ) from exc
        claimed = record.pop("record_sha256", None)
        if record.get("previous_record_sha256") != previous:
            raise ReleaseError("RELEASE_REGISTER_CHAIN_BROKEN", f"line {line_number}")
        actual = sha256_bytes(canonical_json_bytes(record))
        if claimed != actual:
            raise ReleaseError("RELEASE_REGISTER_HASH_MISMATCH", f"line {line_number}")
        record["record_sha256"] = claimed
        records.append(record)
        previous = claimed
    return records


def _reject_duplicate_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReleaseError("ARTIFACT_JSON_DUPLICATE_KEY", key)
        result[key] = value
    return result


def _read_json_object(path: Path, code: str) -> Mapping[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_object_keys,
        )
    except ReleaseError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseError(code, path.name) from exc
    if not isinstance(value, Mapping):
        raise ReleaseError(code, path.name)
    return value


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], code: str) -> None:
    if set(value) != expected:
        raise ReleaseError(
            code,
            f"missing={sorted(expected - set(value))!r}, "
            f"unexpected={sorted(set(value) - expected)!r}",
        )


def _require_sha256(value: Any, code: str) -> str:
    rendered = str(value)
    if not _SHA256_RE.fullmatch(rendered):
        raise ReleaseError(code, rendered)
    return rendered


def _read_artifact_manifest(
    artifact: MaterialisedArtifact, repository_root: Path
) -> Mapping[str, Any]:
    repo = repository_root.resolve(strict=True)
    try:
        root = artifact.root.resolve(strict=True)
        manifest_path = artifact.manifest_path.resolve(strict=True)
    except OSError as exc:
        raise ReleaseError("ARTIFACT_PATH_INVALID", artifact.artifact_id) from exc
    if not root.is_relative_to(repo):
        raise ReleaseError("ARTIFACT_OUTSIDE_REPOSITORY", str(root))
    if root.name != artifact.artifact_id:
        raise ReleaseError("ARTIFACT_ROOT_ID_MISMATCH", artifact.artifact_id)
    if manifest_path != root / "artifact_manifest.json":
        raise ReleaseError("ARTIFACT_MANIFEST_PATH_INVALID", str(manifest_path))
    manifest = _read_json_object(manifest_path, "ARTIFACT_MANIFEST_INVALID")
    _exact_keys(
        manifest, _ARTIFACT_MANIFEST_KEYS, "ARTIFACT_MANIFEST_SCHEMA_INVALID"
    )
    if manifest.get("schema_version") != ARTIFACT_MANIFEST_VERSION:
        raise ReleaseError("ARTIFACT_MANIFEST_VERSION_INVALID", artifact.artifact_id)
    if manifest.get("artifact_id") != artifact.artifact_id:
        raise ReleaseError("ARTIFACT_ID_MISMATCH", artifact.artifact_id)
    if not re.fullmatch(r"EDGE-[0-9A-F]{24}", artifact.artifact_id):
        raise ReleaseError("ARTIFACT_ID_INVALID", artifact.artifact_id)
    actual_hash = sha256_file(manifest_path)
    if actual_hash != artifact.manifest_sha256:
        raise ReleaseError("ARTIFACT_MANIFEST_CHANGED", artifact.artifact_id)
    _require_sha256(manifest.get("source_manifest_sha256"), "SOURCE_HASH_INVALID")
    _require_sha256(manifest.get("software_source_sha256"), "SOFTWARE_HASH_INVALID")
    return manifest


def _verify_artifact_files(
    artifact: MaterialisedArtifact, manifest: Mapping[str, Any]
) -> None:
    files = manifest.get("files")
    if not isinstance(files, Mapping):
        raise ReleaseError("ARTIFACT_FILE_MANIFEST_MISSING", artifact.artifact_id)
    if set(files) != _REQUIRED_PAYLOAD_FILES:
        raise ReleaseError(
            "ARTIFACT_FILE_SET_INVALID",
            f"missing={sorted(_REQUIRED_PAYLOAD_FILES - set(files))!r}, "
            f"unexpected={sorted(set(files) - _REQUIRED_PAYLOAD_FILES)!r}",
        )
    actual_names = {
        path.name for path in artifact.root.iterdir() if path.is_file()
    }
    expected_names = set(_REQUIRED_PAYLOAD_FILES) | {"artifact_manifest.json"}
    if actual_names != expected_names:
        raise ReleaseError("ARTIFACT_DIRECTORY_SET_INVALID", artifact.artifact_id)
    for filename, descriptor in files.items():
        if not isinstance(filename, str) or not isinstance(descriptor, Mapping):
            raise ReleaseError("ARTIFACT_FILE_MANIFEST_INVALID", artifact.artifact_id)
        _exact_keys(
            descriptor,
            frozenset({"sha256", "bytes"}),
            "ARTIFACT_FILE_DESCRIPTOR_INVALID",
        )
        path = (artifact.root / filename).resolve()
        if not path.is_relative_to(artifact.root.resolve()) or not path.is_file():
            raise ReleaseError("ARTIFACT_FILE_MISSING", filename)
        expected_hash = _require_sha256(
            descriptor.get("sha256"), "ARTIFACT_FILE_HASH_INVALID"
        )
        expected_bytes = descriptor.get("bytes")
        if (
            isinstance(expected_bytes, bool)
            or not isinstance(expected_bytes, int)
            or expected_bytes <= 0
            or path.stat().st_size != expected_bytes
        ):
            raise ReleaseError("ARTIFACT_FILE_SIZE_MISMATCH", filename)
        if sha256_file(path) != expected_hash:
            raise ReleaseError("ARTIFACT_FILE_CHANGED", filename)


def _parse_request(value: Mapping[str, Any]) -> DailySliceRequest:
    expected = frozenset(
        {
            "schema_version",
            "request_id",
            "universe_id",
            "exchange_ids",
            "security_types",
            "currencies",
            "start_session",
            "end_session",
            "observation_clock",
            "primary_listings_only",
            "requested_fields",
            "use_mode",
            "policy_versions",
        }
    )
    _exact_keys(value, expected, "ARTIFACT_REQUEST_SCHEMA_INVALID")
    if value.get("schema_version") != REQUEST_SCHEMA_VERSION:
        raise ReleaseError("ARTIFACT_REQUEST_VERSION_INVALID", "request.json")
    policies = value.get("policy_versions")
    policy_keys = frozenset(
        {
            "population_time",
            "calendar",
            "universe",
            "corporate_action",
            "point_in_time_join",
            "observable_schema",
            "return_view_schema",
            "pipeline",
        }
    )
    if not isinstance(policies, Mapping):
        raise ReleaseError("ARTIFACT_REQUEST_POLICY_INVALID", "request.json")
    _exact_keys(policies, policy_keys, "ARTIFACT_REQUEST_POLICY_INVALID")
    for array_name in ("exchange_ids", "security_types", "currencies"):
        values = value.get(array_name)
        if (
            not isinstance(values, list)
            or not values
            or not all(isinstance(item, str) and item for item in values)
            or len(values) != len(set(values))
        ):
            raise ReleaseError("ARTIFACT_REQUEST_SCOPE_INVALID", array_name)
    if value.get("requested_fields") != list(PANEL_COLUMNS):
        raise ReleaseError("ARTIFACT_REQUEST_FIELDS_INVALID", "request.json")
    if not isinstance(value.get("primary_listings_only"), bool):
        raise ReleaseError("ARTIFACT_REQUEST_LISTING_POLICY_INVALID", "request.json")
    try:
        request = DailySliceRequest(
            request_id=str(value["request_id"]),
            universe_id=str(value["universe_id"]),
            exchange_ids=tuple(value["exchange_ids"]),
            security_types=tuple(value["security_types"]),
            currencies=tuple(value["currencies"]),
            start_session=str(value["start_session"]),
            end_session=str(value["end_session"]),
            population_time_contract_version=str(policies["population_time"]),
            calendar_policy_version=str(policies["calendar"]),
            universe_policy_version=str(policies["universe"]),
            corporate_action_policy_version=str(policies["corporate_action"]),
            point_in_time_join_version=str(policies["point_in_time_join"]),
            observable_schema_version=str(policies["observable_schema"]),
            return_view_schema_version=str(policies["return_view_schema"]),
            observation_clock=str(value["observation_clock"]),
            primary_listings_only=value["primary_listings_only"],
            requested_fields=tuple(value["requested_fields"]),
            use_mode=str(value["use_mode"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ReleaseError("ARTIFACT_REQUEST_INVALID", str(exc)) from exc
    if request.as_dict() != dict(value):
        raise ReleaseError("ARTIFACT_REQUEST_NONCANONICAL", "request.json")
    return request


def _validate_supporting_evidence(
    artifact: MaterialisedArtifact,
    manifest: Mapping[str, Any],
) -> DailySliceRequest:
    request_value = _read_json_object(
        artifact.root / "request.json", "ARTIFACT_REQUEST_INVALID"
    )
    request = _parse_request(request_value)
    if manifest.get("request_id") != request.request_id:
        raise ReleaseError("ARTIFACT_REQUEST_ID_MISMATCH", request.request_id)

    lineage = _read_json_object(
        artifact.root / "lineage.json", "ARTIFACT_LINEAGE_INVALID"
    )
    lineage_keys = frozenset(
        {
            "schema_version",
            "source_snapshot_id",
            "source_manifest_sha256",
            "request_id",
            "policy_versions",
            "source_table_logical_sha256",
            "scoped_source_logical_sha256",
            "universe_logical_sha256",
            "panel_logical_sha256",
            "return_view_logical_sha256",
            "software_source_sha256",
            "production_scope_approval_id",
            "capability_audit_id",
            "field_lineage_version",
            "observable_panel_field_lineage",
        }
    )
    _exact_keys(lineage, lineage_keys, "ARTIFACT_LINEAGE_SCHEMA_INVALID")
    expected_lineage_values = {
        "schema_version": "edge.lineage_manifest.v1",
        "source_snapshot_id": manifest.get("source_snapshot_id"),
        "source_manifest_sha256": manifest.get("source_manifest_sha256"),
        "request_id": request.request_id,
        "policy_versions": dict(request.policy_versions),
        "universe_logical_sha256": manifest.get("logical_fingerprints", {}).get(
            "universe"
        ),
        "panel_logical_sha256": manifest.get("logical_fingerprints", {}).get(
            "observable_panel"
        ),
        "return_view_logical_sha256": manifest.get("logical_fingerprints", {}).get(
            "return_consistent_view"
        ),
        "software_source_sha256": manifest.get("software_source_sha256"),
        "production_scope_approval_id": manifest.get(
            "production_scope_approval_id"
        ),
        "field_lineage_version": FIELD_LINEAGE_VERSION,
        "observable_panel_field_lineage": {
            field: dict(PANEL_FIELD_LINEAGE[field]) for field in PANEL_COLUMNS
        },
    }
    for key, expected in expected_lineage_values.items():
        if lineage.get(key) != expected:
            raise ReleaseError("ARTIFACT_LINEAGE_MISMATCH", key)
    for key in ("source_table_logical_sha256", "scoped_source_logical_sha256"):
        values = lineage.get(key)
        if not isinstance(values, Mapping) or len(values) != 5:
            raise ReleaseError("ARTIFACT_LINEAGE_HASHES_INVALID", key)
        for digest in values.values():
            _require_sha256(digest, "ARTIFACT_LINEAGE_HASH_INVALID")

    validation = _read_json_object(
        artifact.root / "validation_report.json", "ARTIFACT_VALIDATION_INVALID"
    )
    _exact_keys(
        validation,
        frozenset({"schema_version", "state", "hard_blocker_count", "checks"}),
        "ARTIFACT_VALIDATION_SCHEMA_INVALID",
    )
    checks = validation.get("checks")
    if not isinstance(checks, list) or len(checks) != len(HARD_FAILURE_CODES):
        raise ReleaseError("ARTIFACT_VALIDATION_CHECKS_INVALID", "validation_report.json")
    check_codes: set[str] = set()
    for check in checks:
        if not isinstance(check, Mapping):
            raise ReleaseError("ARTIFACT_VALIDATION_CHECK_INVALID", "not an object")
        _exact_keys(
            check,
            frozenset(
                {
                    "code",
                    "status",
                    "severity",
                    "count",
                    "detail",
                    "error_codes",
                    "sample_errors",
                }
            ),
            "ARTIFACT_VALIDATION_CHECK_SCHEMA_INVALID",
        )
        code = str(check.get("code"))
        check_codes.add(code)
        if not (
            check.get("status") == "PASS"
            and check.get("severity") == "MANDATORY"
            and check.get("count") == 0
            and check.get("error_codes") == []
            and check.get("sample_errors") == []
            and isinstance(check.get("detail"), str)
            and check.get("detail")
        ):
            raise ReleaseError("ARTIFACT_VALIDATION_CHECK_NOT_PASS", code)
    if check_codes != set(HARD_FAILURE_CODES):
        raise ReleaseError("ARTIFACT_VALIDATION_CHECK_SET_INVALID", str(check_codes))
    expected_state = (
        "ADMISSIBLE"
        if request.use_mode == "PRODUCTION_RESEARCH"
        else "TEST_ADMISSIBLE_NON_PRODUCTION"
    )
    if not (
        validation.get("schema_version") == "edge.validation_report.v1"
        and validation.get("state") == expected_state
        and validation.get("hard_blocker_count") == 0
        and manifest.get("validation_state") == expected_state
    ):
        raise ReleaseError("ARTIFACT_VALIDATION_STATE_INVALID", expected_state)

    join_audit = _read_json_object(
        artifact.root / "join_audit.json", "ARTIFACT_JOIN_AUDIT_INVALID"
    )
    audit_keys = frozenset(
        {
            "left_rows",
            "matched_rows",
            "unmatched_rows",
            "multiple_match_rows",
            "rejected_not_available",
            "terminal_missing_bar_rows",
        }
    )
    _exact_keys(join_audit, audit_keys, "ARTIFACT_JOIN_AUDIT_SCHEMA_INVALID")
    if any(
        isinstance(join_audit[key], bool)
        or not isinstance(join_audit[key], int)
        or join_audit[key] < 0
        for key in audit_keys
    ):
        raise ReleaseError("ARTIFACT_JOIN_AUDIT_VALUE_INVALID", "join_audit.json")
    if not (
        join_audit["left_rows"]
        == join_audit["matched_rows"] + join_audit["unmatched_rows"]
        and join_audit["terminal_missing_bar_rows"] <= join_audit["unmatched_rows"]
        and join_audit["multiple_match_rows"] == 0
    ):
        raise ReleaseError("ARTIFACT_JOIN_AUDIT_INCONSISTENT", "join_audit.json")
    return request


def _verify_materialized_datasets(
    artifact: MaterialisedArtifact, manifest: Mapping[str, Any]
) -> None:
    declared = manifest.get("materialized_datasets")
    if not isinstance(declared, Mapping) or set(declared) != set(_DATASET_CONTRACTS):
        raise ReleaseError("ARTIFACT_DATASET_MANIFEST_INVALID", artifact.artifact_id)
    population = manifest.get("population")
    population_keys = frozenset(
        {
            "universe_rows",
            "candidate_rows",
            "eligible_rows",
            "observable_panel_rows",
            "return_view_rows",
        }
    )
    if not isinstance(population, Mapping):
        raise ReleaseError("ARTIFACT_POPULATION_INVALID", artifact.artifact_id)
    _exact_keys(population, population_keys, "ARTIFACT_POPULATION_INVALID")
    if any(
        isinstance(population[key], bool)
        or not isinstance(population[key], int)
        or population[key] < 0
        for key in population_keys
    ):
        raise ReleaseError("ARTIFACT_POPULATION_INVALID", artifact.artifact_id)
    row_count_keys = {
        "historical_universe": "universe_rows",
        "observable_panel": "observable_panel_rows",
        "return_consistent_view": "return_view_rows",
    }
    for dataset_name, (filename, columns, sort_keys) in _DATASET_CONTRACTS.items():
        descriptor = declared[dataset_name]
        if not isinstance(descriptor, Mapping):
            raise ReleaseError("ARTIFACT_DATASET_DESCRIPTOR_INVALID", dataset_name)
        _exact_keys(
            descriptor,
            frozenset(
                {
                    "columns",
                    "physical_types",
                    "sort_keys",
                    "row_count",
                    "logical_sha256",
                }
            ),
            "ARTIFACT_DATASET_DESCRIPTOR_INVALID",
        )
        actual = _parquet_profile(
            artifact.root / filename,
            columns=columns,
            types=_dataset_types(dataset_name),
            sort_keys=sort_keys,
        )
        if dict(descriptor) != actual:
            raise ReleaseError("ARTIFACT_DATASET_PROFILE_MISMATCH", dataset_name)
        if actual["row_count"] != population[row_count_keys[dataset_name]]:
            raise ReleaseError("ARTIFACT_DATASET_ROW_COUNT_MISMATCH", dataset_name)
    if population["observable_panel_rows"] != population["return_view_rows"]:
        raise ReleaseError("ARTIFACT_VIEW_ROW_COUNT_MISMATCH", artifact.artifact_id)
    with duckdb.connect(database=":memory:") as connection:
        counts = connection.execute(
            "SELECT count(*) FILTER (WHERE candidate), "
            "count(*) FILTER (WHERE eligible) FROM read_parquet(?)",
            [str(artifact.root / "historical_universe.parquet")],
        ).fetchone()
    if (int(counts[0]), int(counts[1])) != (
        population["candidate_rows"],
        population["eligible_rows"],
    ):
        raise ReleaseError("ARTIFACT_POPULATION_COUNT_MISMATCH", artifact.artifact_id)


def verify_materialised_candidate(
    artifact: MaterialisedArtifact, *, repository_root: str | Path
) -> tuple[Mapping[str, Any], DailySliceRequest]:
    """Verify every candidate byte and governed support record from disk."""

    repo = Path(repository_root).resolve(strict=True)
    manifest = _read_artifact_manifest(artifact, repo)
    _verify_artifact_files(artifact, manifest)
    request = _validate_supporting_evidence(artifact, manifest)

    environment = manifest.get("environment")
    if not isinstance(environment, Mapping):
        raise ReleaseError("ARTIFACT_ENVIRONMENT_INVALID", artifact.artifact_id)
    _exact_keys(
        environment,
        frozenset({"python", "duckdb", "platform"}),
        "ARTIFACT_ENVIRONMENT_INVALID",
    )
    if not all(isinstance(value, str) and value for value in environment.values()):
        raise ReleaseError("ARTIFACT_ENVIRONMENT_INVALID", artifact.artifact_id)
    if environment.get("duckdb") != duckdb.__version__:
        raise ReleaseError("ARTIFACT_DUCKDB_VERSION_MISMATCH", artifact.artifact_id)

    fingerprint_keys = frozenset(
        {"universe", "observable_panel", "return_consistent_view"}
    )
    logical = manifest.get("logical_fingerprints")
    replay = manifest.get("replay_fingerprints")
    if not isinstance(logical, Mapping) or not isinstance(replay, Mapping):
        raise ReleaseError("ARTIFACT_LOGICAL_FINGERPRINTS_INVALID", artifact.artifact_id)
    _exact_keys(logical, fingerprint_keys, "ARTIFACT_LOGICAL_FINGERPRINTS_INVALID")
    _exact_keys(replay, fingerprint_keys, "ARTIFACT_REPLAY_FINGERPRINTS_INVALID")
    for digest in [*logical.values(), *replay.values()]:
        _require_sha256(digest, "ARTIFACT_LOGICAL_FINGERPRINT_INVALID")
    if logical != replay:
        raise ReleaseError("ARTIFACT_REPLAY_MISMATCH", artifact.artifact_id)
    if manifest.get("pipeline_version") != PIPELINE_VERSION:
        raise ReleaseError("ARTIFACT_PIPELINE_VERSION_MISMATCH", artifact.artifact_id)
    if manifest.get("software_source_sha256") != package_source_fingerprint():
        raise ReleaseError("ARTIFACT_SOFTWARE_VERSION_MISMATCH", artifact.artifact_id)
    expected_id = _artifact_identity_from_values(
        source_snapshot_id=str(manifest.get("source_snapshot_id")),
        source_manifest_sha256=str(manifest.get("source_manifest_sha256")),
        request=request.as_dict(),
        fingerprints=logical,
        software_source_sha256=str(manifest.get("software_source_sha256")),
        production_scope_approval_id=manifest.get("production_scope_approval_id"),
    )
    if expected_id != artifact.artifact_id:
        raise ReleaseError("ARTIFACT_ID_RECOMPUTATION_FAILED", artifact.artifact_id)
    if not isinstance(manifest.get("builder_id"), str) or not manifest["builder_id"].strip():
        raise ReleaseError("ARTIFACT_BUILDER_INVALID", artifact.artifact_id)
    if not isinstance(manifest.get("limitations"), list) or not all(
        isinstance(value, str) and value for value in manifest["limitations"]
    ):
        raise ReleaseError("ARTIFACT_LIMITATIONS_INVALID", artifact.artifact_id)
    production_claim = request.use_mode == "PRODUCTION_RESEARCH"
    if production_claim:
        coherent = (
            manifest.get("production_use_permitted") is True
            and manifest.get("source_kind") == "MDM_PRODUCTION_SNAPSHOT"
            and manifest.get("artifact_state") == "READY_FOR_INDEPENDENT_REVIEW"
            and manifest.get("validation_state") == "ADMISSIBLE"
            and isinstance(manifest.get("production_scope_approval_id"), str)
            and bool(str(manifest.get("production_scope_approval_id")).strip())
            and manifest.get("limitations") == []
        )
    else:
        coherent = (
            manifest.get("production_use_permitted") is False
            and manifest.get("source_kind") == "TEST_ONLY_NON_PRODUCTION"
            and manifest.get("artifact_state") == "TEST_EVIDENCE_NON_PRODUCTION"
            and manifest.get("validation_state")
            == "TEST_ADMISSIBLE_NON_PRODUCTION"
            and manifest.get("production_scope_approval_id") is None
            and "SYNTHETIC_TEST_DATA_MUST_NOT_ENTER_RESEARCH"
            in manifest.get("limitations", [])
        )
    if not coherent:
        raise ReleaseError("ARTIFACT_CLASSIFICATION_INCOHERENT", artifact.artifact_id)
    _verify_materialized_datasets(artifact, manifest)
    return manifest, request


def _verify_candidate_matches_build(
    artifact: MaterialisedArtifact,
    disk_manifest: Mapping[str, Any],
    rebuilt: DailySliceBuild,
    *,
    repository_root: str | Path,
) -> None:
    """Bind the actual candidate Parquet/support files to an independent build."""

    repo = Path(repository_root).resolve(strict=True)
    temporary_parent = _ensure_inside(
        artifact.root.parent, repo, "REBUILD_TEMPORARY_PARENT_OUTSIDE_REPOSITORY"
    )
    temporary = Path(
        tempfile.mkdtemp(prefix=".edge-independent-rebuild-", dir=temporary_parent)
    ).resolve()
    _ensure_inside(
        temporary, temporary_parent, "REBUILD_TEMPORARY_PATH_OUTSIDE_REPOSITORY"
    )
    try:
        rebuilt_materialized = _materialized_profiles_for_build(rebuilt, temporary)
    finally:
        if temporary.exists():
            cleanup_target = _ensure_inside(
                temporary,
                temporary_parent,
                "REBUILD_CLEANUP_PATH_OUTSIDE_REPOSITORY",
            )
            shutil.rmtree(cleanup_target)

    disk_lineage = _read_json_object(
        artifact.root / "lineage.json", "ARTIFACT_LINEAGE_INVALID"
    )
    disk_validation = _read_json_object(
        artifact.root / "validation_report.json", "ARTIFACT_VALIDATION_INVALID"
    )
    disk_join_audit = _read_json_object(
        artifact.root / "join_audit.json", "ARTIFACT_JOIN_AUDIT_INVALID"
    )
    if not (
        _artifact_identity(rebuilt) == artifact.artifact_id
        and rebuilt.fingerprints == disk_manifest.get("logical_fingerprints")
        and rebuilt.replay_fingerprints == disk_manifest.get("replay_fingerprints")
        and rebuilt.lineage_manifest == disk_lineage
        and rebuilt.validation_report.as_dict() == disk_validation
        and rebuilt.join_audit.as_dict() == disk_join_audit
        and universe_counts_for_manifest(rebuilt) == disk_manifest.get("population")
        and rebuilt_materialized == disk_manifest.get("materialized_datasets")
    ):
        raise ReleaseError("INDEPENDENT_REBUILD_MISMATCH", artifact.artifact_id)


def _fresh_production_snapshot(
    source_snapshot: VerifiedMdmSnapshot,
    production_scope: ProductionScopeApproval,
) -> VerifiedMdmSnapshot:
    """Rebuild a trusted source handle from the exact approved MDM root."""

    try:
        fresh = verify_mdm_snapshot(
            source_snapshot.manifest_path,
            production_scope.authorised_mdm_root,
        )
    except SourceValidationError as exc:
        raise ReleaseError("PRODUCTION_SOURCE_REVERIFICATION_FAILED", str(exc)) from exc
    fresh.require_production_use()
    return fresh


def approve_production_release(
    artifact: MaterialisedArtifact,
    *,
    repository_root: str | Path,
    register_path: str | Path,
    reviewer_id: str,
    review_evidence_id: str,
    source_snapshot: VerifiedMdmSnapshot | None = None,
    production_scope: ProductionScopeApproval | None = None,
) -> Mapping[str, Any]:
    """Append a production release only after distinct independent review."""

    disk_manifest, request = verify_materialised_candidate(
        artifact, repository_root=repository_root
    )
    if not (
        disk_manifest.get("production_use_permitted") is True
        and disk_manifest.get("source_kind") == "MDM_PRODUCTION_SNAPSHOT"
        and disk_manifest.get("validation_state") == "ADMISSIBLE"
        and disk_manifest.get("artifact_state") == "READY_FOR_INDEPENDENT_REVIEW"
        and request.use_mode == "PRODUCTION_RESEARCH"
        and not disk_manifest.get("limitations")
    ):
        raise ReleaseError(
            "NON_PRODUCTION_ARTIFACT", "test-only or inadmissible artifacts cannot release"
        )
    if source_snapshot is None or production_scope is None:
        raise ReleaseError(
            "VERIFIED_PRODUCTION_EVIDENCE_REQUIRED",
            "release requires the verified source handle and exact approved scope",
        )
    try:
        assert_repository_production_gate_open(
            production_scope, repository_root=repository_root
        )
    except ValueError as exc:
        raise ReleaseError("PRODUCTION_GATE_BLOCKED", str(exc)) from exc
    source_snapshot = _fresh_production_snapshot(source_snapshot, production_scope)
    if not (
        source_snapshot.manifest.snapshot_id
        == disk_manifest.get("source_snapshot_id")
        and source_snapshot.manifest_sha256
        == disk_manifest.get("source_manifest_sha256")
    ):
        raise ReleaseError("ARTIFACT_SOURCE_BINDING_MISMATCH", artifact.artifact_id)
    try:
        production_scope.assert_authorised(source_snapshot, request)
    except ValueError as exc:
        raise ReleaseError("PRODUCTION_SCOPE_REJECTED", str(exc)) from exc
    if production_scope.approval_id != disk_manifest.get(
        "production_scope_approval_id"
    ):
        raise ReleaseError("PRODUCTION_SCOPE_ID_MISMATCH", artifact.artifact_id)

    # Reconstruct independently from the still-verified MDM snapshot.  This
    # prevents a caller-created manifest or post-validation row mutation from
    # becoming a release merely by making its assertions self-consistent.
    rebuilt = build_daily_slice(
        source_snapshot, request, production_scope=production_scope
    )
    _verify_candidate_matches_build(
        artifact,
        disk_manifest,
        rebuilt,
        repository_root=repository_root,
    )
    builder_id = str(disk_manifest.get("builder_id", ""))
    if not reviewer_id.strip() or reviewer_id == builder_id:
        raise ReleaseError(
            "INDEPENDENT_REVIEW_REQUIRED", "reviewer must differ from builder"
        )
    if not review_evidence_id.strip():
        raise ReleaseError("REVIEW_EVIDENCE_REQUIRED", "review evidence is required")
    repo = Path(repository_root).resolve(strict=True)
    register = _ensure_inside(
        Path(register_path), repo, "REGISTER_OUTSIDE_REPOSITORY"
    )
    register.parent.mkdir(parents=True, exist_ok=True)
    records = _load_register(register)
    if any(
        row.get("artifact_id") == artifact.artifact_id
        and row.get("release_state") == "RELEASED"
        for row in records
    ):
        raise ReleaseError("ARTIFACT_ALREADY_RELEASED", artifact.artifact_id)
    source_snapshot_id = str(disk_manifest["source_snapshot_id"])
    source_manifest_sha256 = str(disk_manifest["source_manifest_sha256"])
    prior_source_hashes = {
        str(row.get("source_manifest_sha256"))
        for row in records
        if row.get("source_snapshot_id") == source_snapshot_id
        and row.get("source_manifest_sha256")
    }
    if prior_source_hashes and prior_source_hashes != {source_manifest_sha256}:
        raise ReleaseError(
            "SOURCE_SNAPSHOT_ID_REUSED_WITH_DIFFERENT_CONTENT", source_snapshot_id
        )
    body = {
        "schema_version": RELEASE_REGISTER_VERSION,
        "previous_record_sha256": (
            records[-1]["record_sha256"] if records else "0" * 64
        ),
        "artifact_id": artifact.artifact_id,
        "artifact_manifest_sha256": artifact.manifest_sha256,
        "source_snapshot_id": source_snapshot_id,
        "source_manifest_sha256": source_manifest_sha256,
        "release_state": "RELEASED",
        "builder_id": builder_id,
        "reviewer_id": reviewer_id,
        "review_evidence_id": review_evidence_id,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    record = {**body, "record_sha256": sha256_bytes(canonical_json_bytes(body))}
    encoded = canonical_json_bytes(record) + b"\n"
    descriptor = os.open(register, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return record


def change_production_release_state(
    *,
    repository_root: str | Path,
    register_path: str | Path,
    artifact_id: str,
    new_state: str,
    authority_id: str,
    reason: str,
    successor_artifact_id: str | None = None,
) -> Mapping[str, Any]:
    """Append a revocation or supersession without rewriting history."""

    if new_state not in {"REVOKED", "SUPERSEDED"}:
        raise ReleaseError("INVALID_RELEASE_STATE", new_state)
    if not authority_id.strip() or not reason.strip():
        raise ReleaseError(
            "RELEASE_STATE_EVIDENCE_REQUIRED", "authority and reason are required"
        )
    if new_state == "SUPERSEDED" and not successor_artifact_id:
        raise ReleaseError("SUCCESSOR_REQUIRED", artifact_id)
    repo = Path(repository_root).resolve(strict=True)
    register = _ensure_inside(
        Path(register_path), repo, "REGISTER_OUTSIDE_REPOSITORY"
    )
    records = _load_register(register)
    prior = [row for row in records if row.get("artifact_id") == artifact_id]
    if not prior or prior[-1].get("release_state") != "RELEASED":
        raise ReleaseError("ARTIFACT_NOT_CURRENTLY_RELEASED", artifact_id)
    body = {
        "schema_version": RELEASE_REGISTER_VERSION,
        "previous_record_sha256": records[-1]["record_sha256"],
        "artifact_id": artifact_id,
        "artifact_manifest_sha256": prior[-1]["artifact_manifest_sha256"],
        "source_snapshot_id": prior[-1]["source_snapshot_id"],
        "source_manifest_sha256": prior[-1]["source_manifest_sha256"],
        "release_state": new_state,
        "authority_id": authority_id,
        "reason": reason,
        "successor_artifact_id": successor_artifact_id,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    record = {**body, "record_sha256": sha256_bytes(canonical_json_bytes(body))}
    descriptor = os.open(register, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, canonical_json_bytes(record) + b"\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return record


def verify_production_access(
    artifact: MaterialisedArtifact,
    *,
    repository_root: str | Path,
    register_path: str | Path,
    source_snapshot: VerifiedMdmSnapshot | None = None,
    production_scope: ProductionScopeApproval | None = None,
) -> None:
    """Fail unless artifact bytes and the current production register agree."""

    disk_manifest, request = verify_materialised_candidate(
        artifact, repository_root=repository_root
    )
    if not (
        disk_manifest.get("production_use_permitted") is True
        and disk_manifest.get("source_kind") == "MDM_PRODUCTION_SNAPSHOT"
        and disk_manifest.get("validation_state") == "ADMISSIBLE"
        and request.use_mode == "PRODUCTION_RESEARCH"
        and not disk_manifest.get("limitations")
    ):
        raise ReleaseError("NON_PRODUCTION_ARTIFACT", artifact.artifact_id)
    if source_snapshot is None or production_scope is None:
        raise ReleaseError(
            "VERIFIED_PRODUCTION_EVIDENCE_REQUIRED", artifact.artifact_id
        )
    try:
        assert_repository_production_gate_open(
            production_scope, repository_root=repository_root
        )
    except ValueError as exc:
        raise ReleaseError("PRODUCTION_GATE_BLOCKED", str(exc)) from exc
    source_snapshot = _fresh_production_snapshot(source_snapshot, production_scope)
    if not (
        source_snapshot.manifest.snapshot_id
        == disk_manifest.get("source_snapshot_id")
        and source_snapshot.manifest_sha256
        == disk_manifest.get("source_manifest_sha256")
        and production_scope.approval_id
        == disk_manifest.get("production_scope_approval_id")
    ):
        raise ReleaseError("ARTIFACT_SOURCE_BINDING_MISMATCH", artifact.artifact_id)
    try:
        production_scope.assert_authorised(source_snapshot, request)
    except ValueError as exc:
        raise ReleaseError("PRODUCTION_SCOPE_REJECTED", str(exc)) from exc
    rebuilt = build_daily_slice(
        source_snapshot, request, production_scope=production_scope
    )
    _verify_candidate_matches_build(
        artifact,
        disk_manifest,
        rebuilt,
        repository_root=repository_root,
    )
    repo = Path(repository_root).resolve(strict=True)
    register = _ensure_inside(Path(register_path), repo, "REGISTER_OUTSIDE_REPOSITORY")
    records = _load_register(register)
    matching = [row for row in records if row.get("artifact_id") == artifact.artifact_id]
    if not matching or matching[-1].get("release_state") != "RELEASED":
        raise ReleaseError("ARTIFACT_NOT_RELEASED", artifact.artifact_id)
    if matching[-1].get("artifact_manifest_sha256") != sha256_file(
        artifact.manifest_path
    ):
        raise ReleaseError("ARTIFACT_MANIFEST_CHANGED", artifact.artifact_id)
    if not (
        matching[-1].get("source_snapshot_id")
        == source_snapshot.manifest.snapshot_id
        and matching[-1].get("source_manifest_sha256")
        == source_snapshot.manifest_sha256
    ):
        raise ReleaseError("RELEASE_SOURCE_BINDING_MISMATCH", artifact.artifact_id)
