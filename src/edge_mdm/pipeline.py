"""One bounded, deterministic MDM-to-feature-ready daily build path."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import duckdb

from .actions import CorporateActionError, RETURN_COLUMNS, build_return_components
from .assemble import (
    PANEL_COLUMNS,
    AssemblyError,
    JoinAudit,
    assemble_security_day_panel,
)
from .contracts import REQUIRED_SORT_KEYS
from .fingerprint import logical_rows_fingerprint, package_source_fingerprint
from .lineage import FIELD_LINEAGE_VERSION, PANEL_FIELD_LINEAGE
from .source import SourceValidationError, VerifiedMdmSnapshot, verify_mdm_snapshot
from .scope import ProductionScopeApproval, assert_repository_production_gate_open
from .temporal import TemporalIntegrityError
from .universe import UNIVERSE_COLUMNS, build_historical_universe, universe_counts
from .validation import AdmissionEvidence, ValidationReport, validate_daily_release


PIPELINE_VERSION = "edge-mdm-daily-pipeline-v1"
REQUEST_SCHEMA_VERSION = "edge.feature_ready_request.v1"
SUPPORTED_REQUEST_POLICY_BUNDLES = frozenset(
    {
        (
            "PTC-TEST-001",
            "CAL-TEST-001",
            "UNIV-TEST-001",
            "CA-TEST-001",
            "PIT-TEST-001",
            "edge.security_day_observable.v1",
            "edge.return_consistent_daily.v1",
        )
    }
)


class PipelineError(RuntimeError):
    """Typed fail-closed construction error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class DailySliceRequest:
    request_id: str
    universe_id: str
    exchange_ids: tuple[str, ...]
    security_types: tuple[str, ...]
    currencies: tuple[str, ...]
    start_session: str
    end_session: str
    population_time_contract_version: str
    calendar_policy_version: str
    universe_policy_version: str
    corporate_action_policy_version: str
    point_in_time_join_version: str
    observable_schema_version: str = "edge.security_day_observable.v1"
    return_view_schema_version: str = "edge.return_consistent_daily.v1"
    observation_clock: str = "POST_CLOSE_CUTOFF"
    primary_listings_only: bool = True
    requested_fields: tuple[str, ...] = PANEL_COLUMNS
    use_mode: str = "PRODUCTION_RESEARCH"

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "universe_id",
            "population_time_contract_version",
            "calendar_policy_version",
            "universe_policy_version",
            "corporate_action_policy_version",
            "point_in_time_join_version",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} is required")
        if not self.exchange_ids or not self.security_types or not self.currencies:
            raise ValueError("exchange_ids, security_types, and currencies are required")
        if date.fromisoformat(self.start_session) > date.fromisoformat(self.end_session):
            raise ValueError("start_session cannot be after end_session")
        if self.observation_clock != "POST_CLOSE_CUTOFF":
            raise ValueError("the first implementation supports POST_CLOSE_CUTOFF only")
        if self.use_mode not in {"PRODUCTION_RESEARCH", "TEST_ONLY_VALIDATION"}:
            raise ValueError("unsupported use_mode")
        if self.requested_fields != PANEL_COLUMNS:
            raise ValueError(
                "the first implementation exposes only the frozen observable panel schema"
            )
        policy_bundle = (
            self.population_time_contract_version,
            self.calendar_policy_version,
            self.universe_policy_version,
            self.corporate_action_policy_version,
            self.point_in_time_join_version,
            self.observable_schema_version,
            self.return_view_schema_version,
        )
        if policy_bundle not in SUPPORTED_REQUEST_POLICY_BUNDLES:
            raise ValueError(
                "unsupported policy bundle; every executable policy must have code-bound semantics"
            )

    @property
    def policy_versions(self) -> Mapping[str, str]:
        return {
            "population_time": self.population_time_contract_version,
            "calendar": self.calendar_policy_version,
            "universe": self.universe_policy_version,
            "corporate_action": self.corporate_action_policy_version,
            "point_in_time_join": self.point_in_time_join_version,
            "observable_schema": self.observable_schema_version,
            "return_view_schema": self.return_view_schema_version,
            "pipeline": PIPELINE_VERSION,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": REQUEST_SCHEMA_VERSION,
            "request_id": self.request_id,
            "universe_id": self.universe_id,
            "exchange_ids": list(self.exchange_ids),
            "security_types": list(self.security_types),
            "currencies": list(self.currencies),
            "start_session": self.start_session,
            "end_session": self.end_session,
            "observation_clock": self.observation_clock,
            "primary_listings_only": self.primary_listings_only,
            "requested_fields": list(self.requested_fields),
            "use_mode": self.use_mode,
            "policy_versions": dict(self.policy_versions),
        }

    @classmethod
    def from_policy_mapping(cls, value: Mapping[str, Any]) -> "DailySliceRequest":
        expected = {
            "schema_version",
            "classification",
            "request_id",
            "universe_id",
            "exchange_ids",
            "security_types",
            "currencies",
            "start_session",
            "end_session",
            "observation_clock",
            "primary_listings_only",
            "use_mode",
            "policy_versions",
        }
        if set(value) != expected:
            raise ValueError(
                f"daily-slice policy keys mismatch: missing={sorted(expected - set(value))}, "
                f"unexpected={sorted(set(value) - expected)}"
            )
        policy = value["policy_versions"]
        if not isinstance(policy, Mapping) or set(policy) != {
            "population_time",
            "calendar",
            "universe",
            "corporate_action",
            "point_in_time_join",
        }:
            raise ValueError("policy_versions has the wrong exact contract")
        use_mode = str(value["use_mode"])
        classification = str(value["classification"])
        if use_mode == "TEST_ONLY_VALIDATION" and classification != "TEST_ONLY_NON_PRODUCTION":
            raise ValueError("test requests must be explicitly TEST_ONLY_NON_PRODUCTION")
        if use_mode == "PRODUCTION_RESEARCH" and classification != "PRODUCTION_RESEARCH":
            raise ValueError("production requests must be explicitly classified")
        return cls(
            request_id=str(value["request_id"]),
            universe_id=str(value["universe_id"]),
            exchange_ids=_string_tuple(value["exchange_ids"], "exchange_ids"),
            security_types=_string_tuple(value["security_types"], "security_types"),
            currencies=_string_tuple(value["currencies"], "currencies"),
            start_session=str(value["start_session"]),
            end_session=str(value["end_session"]),
            population_time_contract_version=str(policy["population_time"]),
            calendar_policy_version=str(policy["calendar"]),
            universe_policy_version=str(policy["universe"]),
            corporate_action_policy_version=str(policy["corporate_action"]),
            point_in_time_join_version=str(policy["point_in_time_join"]),
            observation_clock=str(value["observation_clock"]),
            primary_listings_only=value["primary_listings_only"] is True,
            use_mode=use_mode,
        )


@dataclass(frozen=True)
class DailySliceBuild:
    snapshot: VerifiedMdmSnapshot
    request: DailySliceRequest
    identity_rows: tuple[Mapping[str, Any], ...]
    session_rows: tuple[Mapping[str, Any], ...]
    observation_rows: tuple[Mapping[str, Any], ...]
    action_rows: tuple[Mapping[str, Any], ...]
    membership_rows: tuple[Mapping[str, Any], ...]
    universe_rows: tuple[Mapping[str, Any], ...]
    panel_rows: tuple[Mapping[str, Any], ...]
    return_rows: tuple[Mapping[str, Any], ...]
    join_audit: JoinAudit
    fingerprints: Mapping[str, str]
    replay_fingerprints: Mapping[str, str]
    lineage_manifest: Mapping[str, Any]
    validation_report: ValidationReport
    software_source_sha256: str
    production_scope_approval_id: str | None

    @property
    def production_release_permitted(self) -> bool:
        return (
            self.snapshot.production_use_permitted
            and self.request.use_mode == "PRODUCTION_RESEARCH"
            and self.validation_report.state == "ADMISSIBLE"
        )

    def summary(self) -> dict[str, Any]:
        return {
            "source_snapshot_id": self.snapshot.manifest.snapshot_id,
            "request_id": self.request.request_id,
            "source_kind": self.snapshot.manifest.source_kind,
            "validation_state": self.validation_report.state,
            "production_release_permitted": self.production_release_permitted,
            "population": universe_counts(self.universe_rows),
            "observable_panel_rows": len(self.panel_rows),
            "return_view_rows": len(self.return_rows),
            "join_audit": self.join_audit.as_dict(),
            "fingerprints": dict(self.fingerprints),
            "software_source_sha256": self.software_source_sha256,
            "production_scope_approval_id": self.production_scope_approval_id,
        }


def _read_table_rows(
    snapshot: VerifiedMdmSnapshot, logical_name: str
) -> list[dict[str, Any]]:
    table = snapshot.table(logical_name)
    table.assert_unchanged()
    columns = table.columns
    projection = ", ".join(
        f'CAST("{name}" AS VARCHAR) AS "{name}"' for name in columns
    )
    order = ", ".join(
        f'"{name}" ASC NULLS FIRST' for name in REQUIRED_SORT_KEYS[logical_name]
    )
    with duckdb.connect(database=":memory:") as connection:
        connection.execute("SET threads = 1")
        connection.execute("SET TimeZone = 'UTC'")
        cursor = connection.execute(
            f"SELECT {projection} FROM read_parquet(?) ORDER BY {order}",
            [str(table.path)],
        )
        return [dict(zip(columns, values, strict=True)) for values in cursor.fetchall()]


def _filter_scope(
    rows: Mapping[str, list[dict[str, Any]]], request: DailySliceRequest
) -> dict[str, list[dict[str, Any]]]:
    exchange_ids = set(request.exchange_ids)
    sessions = [
        row
        for row in rows["exchange_sessions"]
        if row["exchange_id"] in exchange_ids
        and request.start_session <= row["session_date"] <= request.end_session
    ]
    if not sessions:
        raise PipelineError("REQUEST_SCOPE_EMPTY", "no exchange sessions match the request")
    all_identity_listing_ids = {
        str(row["listing_id"]) for row in rows["identity_lifecycle"]
    }
    identities = [
        row for row in rows["identity_lifecycle"] if row["exchange_id"] in exchange_ids
    ]
    listing_ids = {row["listing_id"] for row in identities}
    requested_memberships = [
        row
        for row in rows["universe_membership"]
        if row["universe_id"] == request.universe_id
    ]
    unresolved_requested_listing_ids = {
        str(row["listing_id"])
        for row in requested_memberships
        if str(row["listing_id"]) not in all_identity_listing_ids
    }
    memberships = [
        row
        for row in requested_memberships
        if row["listing_id"] in listing_ids
        or row["listing_id"] in unresolved_requested_listing_ids
    ]
    observations = [
        row
        for row in rows["daily_observations"]
        if (
            row["listing_id"] in listing_ids
            or row["listing_id"] in unresolved_requested_listing_ids
        )
        and request.start_session <= row["session_date"] <= request.end_session
    ]
    # Retain the complete revision history for relevant listings.  Filtering
    # individual revisions by their own ex-date can resurrect a superseded
    # in-range action when a later correction moves it out of range.
    actions = [
        row
        for row in rows["corporate_actions"]
        if row["listing_id"] in listing_ids
        or row["listing_id"] in unresolved_requested_listing_ids
    ]
    return {
        "identity_lifecycle": identities,
        "exchange_sessions": sessions,
        "daily_observations": observations,
        "corporate_actions": actions,
        "universe_membership": memberships,
    }


def _fingerprint(
    columns: Sequence[str], rows: Iterable[Mapping[str, Any]]
) -> str:
    material = list(rows)
    values = (tuple(row.get(column) for column in columns) for row in material)
    return logical_rows_fingerprint(tuple(columns), values).sha256


def _transform(
    scoped: Mapping[str, list[dict[str, Any]]], request: DailySliceRequest
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    JoinAudit,
    dict[str, str],
]:
    universe = build_historical_universe(
        scoped["identity_lifecycle"],
        scoped["exchange_sessions"],
        scoped["universe_membership"],
        universe_id=request.universe_id,
        allowed_security_types=request.security_types,
        allowed_currencies=request.currencies,
        primary_listings_only=request.primary_listings_only,
    )
    panel, join_audit = assemble_security_day_panel(
        universe,
        scoped["daily_observations"],
        scoped["corporate_actions"],
    )
    returns = build_return_components(panel, scoped["corporate_actions"])
    if not universe or not panel or not returns:
        raise PipelineError(
            "FEATURE_READY_OUTPUT_EMPTY", "the governed request produced no complete panel"
        )
    fingerprints = {
        "universe": _fingerprint(UNIVERSE_COLUMNS, universe),
        "observable_panel": _fingerprint(PANEL_COLUMNS, panel),
        "return_consistent_view": _fingerprint(RETURN_COLUMNS, returns),
    }
    return universe, panel, returns, join_audit, fingerprints


def build_daily_slice(
    snapshot: VerifiedMdmSnapshot,
    request: DailySliceRequest,
    *,
    production_scope: ProductionScopeApproval | None = None,
) -> DailySliceBuild:
    """Build and validate one candidate slice from a verified snapshot.

    This function never publishes a release. A production request additionally
    requires a production-authorised MDM handle before construction begins.
    """

    if request.use_mode == "PRODUCTION_RESEARCH":
        try:
            assert_repository_production_gate_open(production_scope)
        except ValueError as exc:
            raise PipelineError("PRODUCTION_GATE_BLOCKED", str(exc)) from exc
        snapshot.require_production_use()
        if production_scope is None:
            raise PipelineError(
                "INDEPENDENT_SCOPE_APPROVAL_REQUIRED",
                "a self-declared source manifest cannot authorise production research",
            )
        try:
            # A VerifiedMdmSnapshot is a data carrier, not an authority token.
            # Reconstruct the handle from the approved root so a caller cannot
            # inject alternate table paths or self-asserted verification hashes.
            snapshot = verify_mdm_snapshot(
                snapshot.manifest_path,
                production_scope.authorised_mdm_root,
            )
        except SourceValidationError as exc:
            raise PipelineError(
                "PRODUCTION_SOURCE_REVERIFICATION_FAILED", str(exc)
            ) from exc
        snapshot.require_production_use()
        try:
            production_scope.assert_authorised(snapshot, request)
        except ValueError as exc:
            raise PipelineError("PRODUCTION_SCOPE_REJECTED", str(exc)) from exc
    else:
        snapshot.assert_unchanged()

    source_rows = {
        logical_name: _read_table_rows(snapshot, logical_name)
        for logical_name in sorted(REQUIRED_SORT_KEYS)
    }
    scoped = _filter_scope(source_rows, request)
    try:
        universe, panel, returns, join_audit, fingerprints = _transform(scoped, request)
    except (AssemblyError, CorporateActionError, TemporalIntegrityError, ValueError) as exc:
        raise PipelineError("SCIENTIFIC_TRANSFORM_FAILED", str(exc)) from exc

    reversed_scoped = {
        name: list(reversed(rows)) for name, rows in scoped.items()
    }
    try:
        _, _, _, _, replay_fingerprints = _transform(reversed_scoped, request)
    except (AssemblyError, CorporateActionError, TemporalIntegrityError, ValueError) as exc:
        raise PipelineError("DETERMINISTIC_REPLAY_FAILED", str(exc)) from exc

    lineage_manifest = {
        "schema_version": "edge.lineage_manifest.v1",
        "source_snapshot_id": snapshot.manifest.snapshot_id,
        "source_manifest_sha256": snapshot.manifest_sha256,
        "request_id": request.request_id,
        "policy_versions": dict(request.policy_versions),
        "source_table_logical_sha256": {
            table.manifest.logical_name: table.verified_logical_sha256
            for table in snapshot.tables
        },
        "scoped_source_logical_sha256": {
            logical_name: _fingerprint(
                tuple(snapshot.table(logical_name).columns), scoped[logical_name]
            )
            for logical_name in sorted(scoped)
        },
        "universe_logical_sha256": fingerprints["universe"],
        "panel_logical_sha256": fingerprints["observable_panel"],
        "return_view_logical_sha256": fingerprints["return_consistent_view"],
        "software_source_sha256": package_source_fingerprint(),
        "production_scope_approval_id": (
            production_scope.approval_id if production_scope is not None else None
        ),
        "capability_audit_id": (
            production_scope.capability_audit_id
            if production_scope is not None
            else "TEST_ONLY_NOT_APPLICABLE"
        ),
        "field_lineage_version": FIELD_LINEAGE_VERSION,
        "observable_panel_field_lineage": {
            field: dict(PANEL_FIELD_LINEAGE[field]) for field in PANEL_COLUMNS
        },
    }
    field_roles = {
        field: str(PANEL_FIELD_LINEAGE[field]["role"]) for field in PANEL_COLUMNS
    }
    evidence = AdmissionEvidence(
        snapshot=snapshot,
        requested_fields=tuple(
            {"field_id": field, "alias": field} for field in request.requested_fields
        ),
        field_roles=field_roles,
        lineage_manifest=lineage_manifest,
        first_fingerprints=fingerprints,
        replay_fingerprints=replay_fingerprints,
    )
    report = validate_daily_release(
        evidence=evidence,
        identity_rows=scoped["identity_lifecycle"],
        session_rows=scoped["exchange_sessions"],
        observation_rows=scoped["daily_observations"],
        action_rows=scoped["corporate_actions"],
        membership_rows=scoped["universe_membership"],
        universe_rows=universe,
        panel_rows=panel,
        return_rows=returns,
    )
    return DailySliceBuild(
        snapshot=snapshot,
        request=request,
        identity_rows=tuple(scoped["identity_lifecycle"]),
        session_rows=tuple(scoped["exchange_sessions"]),
        observation_rows=tuple(scoped["daily_observations"]),
        action_rows=tuple(scoped["corporate_actions"]),
        membership_rows=tuple(scoped["universe_membership"]),
        universe_rows=tuple(universe),
        panel_rows=tuple(panel),
        return_rows=tuple(returns),
        join_audit=join_audit,
        fingerprints=fingerprints,
        replay_fingerprints=replay_fingerprints,
        lineage_manifest=lineage_manifest,
        validation_report=report,
        software_source_sha256=str(lineage_manifest["software_source_sha256"]),
        production_scope_approval_id=(
            production_scope.approval_id if production_scope is not None else None
        ),
    )


def load_daily_slice_request(path: str | Path) -> DailySliceRequest:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"daily-slice policy is unreadable: {source}") from exc
    if not isinstance(value, Mapping):
        raise ValueError("daily-slice policy root must be an object")
    return DailySliceRequest.from_policy_mapping(value)


def _string_tuple(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{field} must be a non-empty string array")
    return tuple(value)
