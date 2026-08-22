"""Fail-closed verification and read-only access for one MDM snapshot bundle."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import duckdb

from .contracts import (
    REQUIRED_COLUMN_TYPES,
    REQUIRED_SORT_KEYS,
    REQUIRED_TABLE_COLUMNS,
    REQUIRED_TABLES,
    ContractError,
    MdmSnapshotManifest,
    MdmTableManifest,
)
from .fingerprint import (
    logical_rows_fingerprint,
    schema_fingerprint,
    sha256_file,
)


class SourceValidationError(RuntimeError):
    """Typed failure at the authorised MDM source boundary."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        logical_table: str | None = None,
        path: Path | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.logical_table = logical_table
        self.path = path
        context = []
        if logical_table is not None:
            context.append(f"table={logical_table}")
        if path is not None:
            context.append(f"path={path}")
        suffix = f" ({', '.join(context)})" if context else ""
        super().__init__(f"{code}: {message}{suffix}")


_NULLABLE_COLUMNS: Mapping[str, frozenset[str]] = {
    "identity_lifecycle": frozenset({"effective_to"}),
    "exchange_sessions": frozenset(
        {"open_at", "close_at", "cutoff_at", "previous_session_date", "next_session_date"}
    ),
    "daily_observations": frozenset(),
    "corporate_actions": frozenset(
        {
            "split_ratio",
            "cash_amount",
            "currency",
            "terminal_consideration",
            "successor_listing_id",
        }
    ),
    "universe_membership": frozenset({"effective_to"}),
}


def _resolved_existing_path(path: str | Path, *, directory: bool) -> Path:
    candidate = Path(path)
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise SourceValidationError(
            "SOURCE_PATH_MISSING", "source path does not resolve", path=candidate
        ) from exc
    if directory and not resolved.is_dir():
        raise SourceValidationError(
            "AUTHORISED_ROOT_INVALID",
            "authorised MDM root must be a directory",
            path=resolved,
        )
    if not directory and not resolved.is_file():
        raise SourceValidationError(
            "SOURCE_PATH_INVALID", "source path must be a file", path=resolved
        )
    return resolved


def _require_contained(path: Path, root: Path, code: str) -> None:
    if not path.is_relative_to(root):
        raise SourceValidationError(
            code, "resolved path escapes its authorised root", path=path
        )


def _reject_duplicate_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SourceValidationError(
                "MANIFEST_DUPLICATE_KEY", f"duplicate JSON key {key!r}"
            )
        result[key] = value
    return result


def _read_manifest(path: Path) -> MdmSnapshotManifest:
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SourceValidationError(
            "MANIFEST_READ_FAILED", "manifest is not readable UTF-8", path=path
        ) from exc
    try:
        value = json.loads(raw, object_pairs_hook=_reject_duplicate_object_keys)
    except SourceValidationError:
        raise
    except json.JSONDecodeError as exc:
        raise SourceValidationError(
            "MANIFEST_JSON_INVALID", "manifest is not valid JSON", path=path
        ) from exc
    if not isinstance(value, Mapping):
        raise SourceValidationError(
            "MANIFEST_CONTRACT_INVALID", "manifest root must be an object", path=path
        )
    try:
        return MdmSnapshotManifest.from_mapping(value)
    except ContractError as exc:
        raise SourceValidationError(
            "MANIFEST_CONTRACT_INVALID", str(exc), path=path
        ) from exc


def _quoted_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _iter_cursor_rows(
    cursor: duckdb.DuckDBPyConnection, batch_size: int = 4096
) -> Iterator[Sequence[Any]]:
    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            return
        yield from rows


@dataclass(frozen=True, slots=True)
class VerifiedMdmTable:
    """A fully verified immutable table with a read-only Parquet scan method."""

    manifest: MdmTableManifest
    path: Path
    columns: tuple[str, ...]
    physical_types: tuple[str, ...]
    verified_sha256: str
    verified_schema_sha256: str
    verified_logical_sha256: str

    def assert_unchanged(self) -> None:
        """Fail if source bytes changed since boundary verification."""

        actual = sha256_file(self.path)
        if actual != self.verified_sha256:
            raise SourceValidationError(
                "SOURCE_CHANGED_AFTER_VERIFICATION",
                f"expected SHA-256 {self.verified_sha256}, found {actual}",
                logical_table=self.manifest.logical_name,
                path=self.path,
            )

    def scan(
        self, connection: duckdb.DuckDBPyConnection
    ) -> duckdb.DuckDBPyRelation:
        """Return a lazy read-only relation after rechecking source integrity."""

        self.assert_unchanged()
        return connection.read_parquet(str(self.path))


@dataclass(frozen=True, slots=True)
class VerifiedMdmSnapshot:
    """Verified source handle; no unverified table path is exposed for use."""

    manifest: MdmSnapshotManifest
    manifest_path: Path
    manifest_sha256: str
    authorised_mdm_root: Path
    bundle_root: Path
    tables: tuple[VerifiedMdmTable, ...]

    @property
    def production_use_permitted(self) -> bool:
        return self.manifest.production_use_permitted

    def require_production_use(self) -> None:
        """Fail closed before any production build or admission decision."""

        if not self.production_use_permitted:
            raise SourceValidationError(
                "SOURCE_NOT_AUTHORISED_FOR_PRODUCTION",
                "test-only data cannot enter a production snapshot or admission",
                path=self.manifest_path,
            )

    def assert_unchanged(self) -> None:
        """Recheck the manifest and all table bytes before governed reuse."""

        actual_manifest_sha256 = sha256_file(self.manifest_path)
        if actual_manifest_sha256 != self.manifest_sha256:
            raise SourceValidationError(
                "MANIFEST_CHANGED_AFTER_VERIFICATION",
                f"expected SHA-256 {self.manifest_sha256}, "
                f"found {actual_manifest_sha256}",
                path=self.manifest_path,
            )
        for table in self.tables:
            table.assert_unchanged()

    def table(self, logical_name: str) -> VerifiedMdmTable:
        if logical_name not in REQUIRED_TABLES:
            raise KeyError(f"unsupported MDM table {logical_name!r}")
        for table in self.tables:
            if table.manifest.logical_name == logical_name:
                return table
        raise SourceValidationError(
            "REQUIRED_TABLE_MISSING",
            "verified snapshot is internally incomplete",
            logical_table=logical_name,
        )

    def scan(
        self,
        logical_name: str,
        connection: duckdb.DuckDBPyConnection,
    ) -> duckdb.DuckDBPyRelation:
        actual_manifest_sha256 = sha256_file(self.manifest_path)
        if actual_manifest_sha256 != self.manifest_sha256:
            raise SourceValidationError(
                "MANIFEST_CHANGED_AFTER_VERIFICATION",
                f"expected SHA-256 {self.manifest_sha256}, "
                f"found {actual_manifest_sha256}",
                path=self.manifest_path,
            )
        return self.table(logical_name).scan(connection)


def _verify_table(
    descriptor: MdmTableManifest,
    *,
    bundle_root: Path,
    authorised_root: Path,
    connection: duckdb.DuckDBPyConnection,
    snapshot_id: str,
    snapshot_cutoff_utc: Any,
) -> VerifiedMdmTable:
    candidate = bundle_root.joinpath(*descriptor.relative_path.parts)
    try:
        path = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise SourceValidationError(
            "TABLE_FILE_MISSING",
            "declared table file does not resolve",
            logical_table=descriptor.logical_name,
            path=candidate,
        ) from exc
    _require_contained(path, bundle_root, "TABLE_PATH_UNTRUSTED")
    _require_contained(path, authorised_root, "TABLE_PATH_UNAUTHORISED")
    if not path.is_file() or path.suffix.casefold() != ".parquet":
        raise SourceValidationError(
            "TABLE_FILE_INVALID",
            "declared table must be a Parquet file",
            logical_table=descriptor.logical_name,
            path=path,
        )

    actual_file_sha256 = sha256_file(path)
    if actual_file_sha256 != descriptor.sha256:
        raise SourceValidationError(
            "TABLE_HASH_MISMATCH",
            f"expected {descriptor.sha256}, found {actual_file_sha256}",
            logical_table=descriptor.logical_name,
            path=path,
        )

    try:
        relation = connection.read_parquet(str(path))
        columns = tuple(str(name) for name in relation.columns)
        physical_types = tuple(str(kind) for kind in relation.types)
    except duckdb.Error as exc:
        raise SourceValidationError(
            "TABLE_PARQUET_INVALID",
            "DuckDB could not read the declared Parquet file",
            logical_table=descriptor.logical_name,
            path=path,
        ) from exc

    if len(columns) != len(set(columns)):
        raise SourceValidationError(
            "TABLE_DUPLICATE_COLUMN",
            "physical schema contains duplicate column names",
            logical_table=descriptor.logical_name,
            path=path,
        )
    required_columns = REQUIRED_TABLE_COLUMNS[descriptor.logical_name]
    missing_columns = sorted(required_columns - set(columns))
    unexpected_columns = sorted(set(columns) - required_columns)
    expected_column_order = tuple(REQUIRED_COLUMN_TYPES[descriptor.logical_name])
    if missing_columns or unexpected_columns or columns != expected_column_order:
        raise SourceValidationError(
            "TABLE_SCHEMA_COLUMNS_MISMATCH",
            f"missing={missing_columns!r}, unexpected={unexpected_columns!r}, "
            f"order_matches={columns == expected_column_order}",
            logical_table=descriptor.logical_name,
            path=path,
        )

    actual_types_by_column = dict(zip(columns, physical_types, strict=True))
    type_mismatches = {
        column: {
            "expected": expected_type,
            "actual": actual_types_by_column[column],
        }
        for column, expected_type in REQUIRED_COLUMN_TYPES[
            descriptor.logical_name
        ].items()
        if actual_types_by_column[column] != expected_type
    }
    if type_mismatches:
        raise SourceValidationError(
            "TABLE_COLUMN_TYPE_MISMATCH",
            f"required physical types differ: {type_mismatches!r}",
            logical_table=descriptor.logical_name,
            path=path,
        )

    actual_schema_sha256 = schema_fingerprint(zip(columns, physical_types, strict=True))
    if actual_schema_sha256 != descriptor.schema_sha256:
        raise SourceValidationError(
            "TABLE_SCHEMA_MISMATCH",
            f"expected {descriptor.schema_sha256}, found {actual_schema_sha256}",
            logical_table=descriptor.logical_name,
            path=path,
        )

    count_cursor = connection.execute(
        "SELECT count(*) FROM read_parquet(?)", [str(path)]
    )
    actual_row_count = int(count_cursor.fetchone()[0])
    if actual_row_count != descriptor.row_count:
        raise SourceValidationError(
            "TABLE_ROW_COUNT_MISMATCH",
            f"expected {descriptor.row_count}, found {actual_row_count}",
            logical_table=descriptor.logical_name,
            path=path,
        )

    non_nullable = sorted(required_columns - _NULLABLE_COLUMNS[descriptor.logical_name])
    non_nullable_predicate = " OR ".join(
        f"{_quoted_identifier(name)} IS NULL" for name in non_nullable
    )
    missing_required_count = int(
        connection.execute(
            f"SELECT count(*) FROM read_parquet(?) WHERE {non_nullable_predicate}",
            [str(path)],
        ).fetchone()[0]
    )
    if missing_required_count:
        raise SourceValidationError(
            "TABLE_REQUIRED_VALUE_NULL",
            f"{missing_required_count} rows contain null Mandatory values",
            logical_table=descriptor.logical_name,
            path=path,
        )

    wrong_vintage_count = int(
        connection.execute(
            "SELECT count(*) FROM read_parquet(?) WHERE mdm_vintage_id <> ?",
            [str(path), snapshot_id],
        ).fetchone()[0]
    )
    if wrong_vintage_count:
        raise SourceValidationError(
            "TABLE_VINTAGE_MISMATCH",
            f"{wrong_vintage_count} rows do not bind to snapshot {snapshot_id!r}",
            logical_table=descriptor.logical_name,
            path=path,
        )

    after_cutoff_count = int(
        connection.execute(
            "SELECT count(*) FROM read_parquet(?) WHERE available_at > ?",
            [str(path), snapshot_cutoff_utc],
        ).fetchone()[0]
    )
    if after_cutoff_count:
        raise SourceValidationError(
            "TABLE_AVAILABILITY_AFTER_SNAPSHOT_CUTOFF",
            f"{after_cutoff_count} rows exceed the snapshot cutoff",
            logical_table=descriptor.logical_name,
            path=path,
        )

    sort_keys = REQUIRED_SORT_KEYS[descriptor.logical_name]
    null_predicate = " OR ".join(
        f"{_quoted_identifier(name)} IS NULL" for name in sort_keys
    )
    null_cursor = connection.execute(
        f"SELECT count(*) FROM read_parquet(?) WHERE {null_predicate}",
        [str(path)],
    )
    null_key_count = int(null_cursor.fetchone()[0])
    if null_key_count:
        raise SourceValidationError(
            "TABLE_NULL_SORT_KEY",
            f"{null_key_count} rows contain null deterministic sort keys",
            logical_table=descriptor.logical_name,
            path=path,
        )

    group_keys = ", ".join(_quoted_identifier(name) for name in sort_keys)
    duplicate_cursor = connection.execute(
        "SELECT count(*) FROM ("
        f"SELECT 1 FROM read_parquet(?) GROUP BY {group_keys} "
        "HAVING count(*) > 1"
        ") duplicate_groups",
        [str(path)],
    )
    duplicate_key_groups = int(duplicate_cursor.fetchone()[0])
    if duplicate_key_groups:
        raise SourceValidationError(
            "TABLE_DUPLICATE_SORT_KEY",
            f"{duplicate_key_groups} duplicate deterministic key groups",
            logical_table=descriptor.logical_name,
            path=path,
        )

    order_clause = ", ".join(
        f"{_quoted_identifier(name)} ASC NULLS FIRST" for name in sort_keys
    )
    # Fetch canonical DuckDB text instead of driver timestamp objects. This
    # avoids an undeclared timezone-package dependency; the physical schema
    # hash separately prevents cross-type collisions.
    logical_projection = ", ".join(
        f"CAST({_quoted_identifier(name)} AS VARCHAR) AS {_quoted_identifier(name)}"
        for name in columns
    )
    row_cursor = connection.execute(
        f"SELECT {logical_projection} FROM read_parquet(?) ORDER BY {order_clause}",
        [str(path)],
    )
    logical = logical_rows_fingerprint(columns, _iter_cursor_rows(row_cursor))
    if logical.row_count != descriptor.row_count:
        raise SourceValidationError(
            "TABLE_LOGICAL_ROW_COUNT_MISMATCH",
            f"fingerprinted {logical.row_count}, expected {descriptor.row_count}",
            logical_table=descriptor.logical_name,
            path=path,
        )
    if logical.sha256 != descriptor.logical_sha256:
        raise SourceValidationError(
            "TABLE_LOGICAL_HASH_MISMATCH",
            f"expected {descriptor.logical_sha256}, found {logical.sha256}",
            logical_table=descriptor.logical_name,
            path=path,
        )

    return VerifiedMdmTable(
        manifest=descriptor,
        path=path,
        columns=columns,
        physical_types=physical_types,
        verified_sha256=actual_file_sha256,
        verified_schema_sha256=actual_schema_sha256,
        verified_logical_sha256=logical.sha256,
    )


def verify_mdm_snapshot(
    manifest_path: str | Path,
    authorised_mdm_root: str | Path,
    *,
    allow_test_only: bool = False,
) -> VerifiedMdmSnapshot:
    """Validate and open exactly one immutable MDM snapshot bundle.

    Both the manifest and every resolved table must remain inside the explicit
    authorised MDM root. All five Mandatory source tables, physical hashes,
    schemas, row counts, deterministic keys, and logical hashes must verify.
    """

    root = _resolved_existing_path(authorised_mdm_root, directory=True)
    manifest_file = _resolved_existing_path(manifest_path, directory=False)
    _require_contained(manifest_file, root, "MANIFEST_PATH_UNAUTHORISED")
    bundle_root = manifest_file.parent
    _require_contained(bundle_root, root, "BUNDLE_PATH_UNAUTHORISED")

    if not isinstance(allow_test_only, bool):
        raise TypeError("allow_test_only must be a boolean")
    manifest = _read_manifest(manifest_file)
    if not manifest.production_use_permitted and not allow_test_only:
        raise SourceValidationError(
            "SOURCE_NOT_AUTHORISED_FOR_PRODUCTION",
            "test-only data requires an explicit non-production verification path",
            path=manifest_file,
        )
    manifest_sha256 = sha256_file(manifest_file)

    verified_tables: list[VerifiedMdmTable] = []
    try:
        with duckdb.connect(database=":memory:") as connection:
            connection.execute("SET threads = 1")
            connection.execute("SET TimeZone = 'UTC'")
            by_name = {table.logical_name: table for table in manifest.tables}
            for logical_name in sorted(REQUIRED_TABLES):
                verified_tables.append(
                    _verify_table(
                        by_name[logical_name],
                        bundle_root=bundle_root,
                        authorised_root=root,
                        connection=connection,
                        snapshot_id=manifest.snapshot_id,
                        snapshot_cutoff_utc=manifest.snapshot_cutoff_utc,
                    )
                )
    except SourceValidationError:
        raise
    except duckdb.Error as exc:
        raise SourceValidationError(
            "DUCKDB_SOURCE_VALIDATION_FAILED",
            "DuckDB failed while validating the source bundle",
            path=manifest_file,
        ) from exc

    return VerifiedMdmSnapshot(
        manifest=manifest,
        manifest_path=manifest_file,
        manifest_sha256=manifest_sha256,
        authorised_mdm_root=root,
        bundle_root=bundle_root,
        tables=tuple(verified_tables),
    )
