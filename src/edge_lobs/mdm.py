"""Fail-closed MDM boundary for the Leadership Observation Ledger.

This module deliberately does not calculate market features.  It exposes the
small set of checks needed to prove that a future enrichment implementation is
using a released Project EDGE MDM artifact, and it provides structural,
explicitly test-only validators for synthetic boundary tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from .errors import LobsError


MDM_STATUS_SCHEMA_VERSION = "edge.leadership_mdm_status.v1"
ENRICHMENT_SCHEMA_VERSION = "edge.leadership_mdm_enrichment.v1"
TEST_ONLY_CLASSIFICATION = "TEST_ONLY_NON_PRODUCTION"
STRUCTURAL_VALIDATION_ONLY = "STRUCTURAL_VALIDATION_ONLY"
TRADABLE_SESSION_STATES = frozenset({"REGULAR", "EARLY_CLOSE"})

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_AUTHORITY_TRUE_KEYS = frozenset(
    {
        "admitted",
        "admissible",
        "production_use_permitted",
        "research_use_permitted",
        "released",
    }
)
_CURRENT_MEMBERSHIP_VALUES = frozenset(
    {"CURRENT", "CURRENT_ONLY", "LATEST", "PRESENT_DAY", "TODAY"}
)
_CURRENT_MEMBERSHIP_KEYS = frozenset(
    {"current_membership", "current_constituent", "is_current"}
)
_MEMBERSHIP_MODE_KEYS = frozenset(
    {"membership_basis", "membership_mode", "resolution_mode"}
)
_ENRICHMENT_OUTCOME_KEYS = frozenset(
    {
        "forward_return",
        "future_return",
        "future_value",
        "mfe",
        "mae",
        "outcome",
        "outcome_label",
        "subsequent_success",
        "target",
        "threshold_hit",
    }
)
_OUTCOME_FEATURE_ID_TOKENS = frozenset(
    {"FORWARD", "FUTURE", "MFE", "MAE", "OUTCOME", "TARGET", "SUBSEQUENT"}
)


@dataclass(frozen=True, slots=True)
class MdmStatus:
    """Repository-derived status; never a caller-authored authority claim."""

    capability_gate: str
    population_time_contract: str
    production_scope_status: str
    production_release_authority: str
    production_use_permitted: bool
    blockers: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return self.production_use_permitted and not self.blockers

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": MDM_STATUS_SCHEMA_VERSION,
            "production_implementation_ready": self.ready,
            "production_use_permitted": self.production_use_permitted,
            "mdm_capability_gate": self.capability_gate,
            "population_time_contract": self.population_time_contract,
            "production_scope_status": self.production_scope_status,
            "production_release_authority": self.production_release_authority,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True, slots=True)
class TestOnlyValidationReport:
    """A structural report that is incapable of granting research authority."""

    document_type: str
    state: str
    checks: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.state == "TEST_ONLY_STRUCTURALLY_VALID"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "edge.lobs_test_only_validation_report.v1",
            "document_type": self.document_type,
            "state": self.state,
            "classification": TEST_ONLY_CLASSIFICATION,
            "production_use_permitted": False,
            "research_use_permitted": False,
            "admission_status": STRUCTURAL_VALIDATION_ONLY,
            "checks": list(self.checks),
        }


@dataclass(frozen=True, slots=True)
class FeatureInputSummary:
    information_cutoff_timestamp: str
    exchange_id: str
    last_completed_session: str
    bar_count: int
    membership_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "classification": TEST_ONLY_CLASSIFICATION,
            "production_use_permitted": False,
            "research_use_permitted": False,
            "admission_status": STRUCTURAL_VALIDATION_ONLY,
            "information_cutoff_timestamp": self.information_cutoff_timestamp,
            "exchange_id": self.exchange_id,
            "last_completed_session": self.last_completed_session,
            "bar_count": self.bar_count,
            "membership_count": self.membership_count,
        }


def parse_aware_timestamp(value: Any, *, field: str) -> datetime:
    """Parse an ISO-8601 timestamp and normalise it to UTC."""

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip() == value and value:
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise LobsError("TIMESTAMP_INVALID", f"{field} must be ISO-8601") from exc
    else:
        raise LobsError("TIMESTAMP_INVALID", f"{field} must be an ISO-8601 string")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise LobsError("TIMESTAMP_TIMEZONE_REQUIRED", f"{field} must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _timestamp_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _required_text(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise LobsError("FIELD_INVALID", f"{field} must be a non-empty trimmed string")
    return value


def _required_mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LobsError("FIELD_INVALID", f"{field} must be an object")
    return value


def _required_sequence(value: Any, *, field: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise LobsError("FIELD_INVALID", f"{field} must be an array")
    return value


def _require_sha256(value: Any, *, field: str) -> str:
    text = _required_text(value, field=field)
    if _SHA256_RE.fullmatch(text) is None:
        raise LobsError("SHA256_INVALID", f"{field} must be a lowercase SHA-256")
    return text


def _load_config(path: Path) -> Mapping[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise LobsError("MDM_STATUS_CONFIG_INVALID", f"duplicate key {key!r}", path=path)
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise LobsError("MDM_STATUS_CONFIG_INVALID", f"non-finite value {value!r}", path=path)

    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(
            raw,
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except LobsError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LobsError("MDM_STATUS_CONFIG_INVALID", "configuration is unreadable", path=path) from exc
    return _required_mapping(value, field=str(path))


def read_mdm_status(repository_root: str | Path) -> MdmStatus:
    """Read the four canonical repository gates without accepting overrides."""

    try:
        root = Path(repository_root).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise LobsError("REPOSITORY_ROOT_INVALID", "repository root does not resolve") from exc
    if not root.is_dir():
        raise LobsError("REPOSITORY_ROOT_INVALID", "repository root must be a directory", path=root)
    config = root / "config"
    capability = _load_config(config / "mdm_capability_audit.v1.json")
    population = _load_config(config / "population_time_contract.v1.json")
    scope = _load_config(config / "production_scope_status.v1.json")
    authority = _load_config(config / "production_release_authority.v1.json")

    blockers: list[str] = []
    if capability.get("schema_version") != "edge.mdm_capability_audit.v1":
        blockers.append("MDM_CAPABILITY_AUDIT_SCHEMA_INVALID")
    if capability.get("production_gate") != "READY":
        blockers.append("MDM_CAPABILITY_GATE_BLOCKED")
    if population.get("schema_version") != "edge.population_time_contract.v1":
        blockers.append("POPULATION_TIME_CONTRACT_SCHEMA_INVALID")
    if not (
        population.get("status") == "RATIFIED"
        and population.get("production_use_permitted") is True
    ):
        blockers.append("POPULATION_TIME_CONTRACT_UNRATIFIED")
    if scope.get("schema_version") != "edge.production_scope_status.v1":
        blockers.append("PRODUCTION_SCOPE_STATUS_SCHEMA_INVALID")
    if scope.get("status") != "APPROVED_SCOPES_AVAILABLE":
        blockers.append("NO_APPROVED_PRODUCTION_SCOPE")
    if authority.get("schema_version") != "edge.production_release_authority.v1":
        blockers.append("PRODUCTION_RELEASE_AUTHORITY_SCHEMA_INVALID")
    if not (
        authority.get("status") == "READY"
        and authority.get("production_use_permitted") is True
    ):
        blockers.append("PRODUCTION_RELEASE_AUTHORITY_NOT_READY")

    production_permitted = not blockers
    return MdmStatus(
        capability_gate=str(capability.get("production_gate", "UNKNOWN")),
        population_time_contract=str(population.get("status", "UNKNOWN")),
        production_scope_status=str(scope.get("status", "UNKNOWN")),
        production_release_authority=str(authority.get("status", "UNKNOWN")),
        production_use_permitted=production_permitted,
        blockers=tuple(blockers),
    )


def require_production_mdm_access(
    *,
    artifact: Any,
    repository_root: str | Path,
    register_path: str | Path,
    source_snapshot: Any,
    production_scope: Any,
) -> MdmStatus:
    """Require the existing MDM production consumer boundary.

    No caller-authored row or self-declared source flag can enter this function
    as market data.  The current canonical configuration fails before the
    release verifier because every production gate is closed.
    """

    status = read_mdm_status(repository_root)
    if not status.ready:
        raise LobsError(
            "MDM_ENRICHMENT_PRODUCTION_BLOCKED",
            "canonical Project EDGE MDM gates are closed: " + ", ".join(status.blockers),
        )
    if any(
        value is None
        for value in (artifact, register_path, source_snapshot, production_scope)
    ):
        raise LobsError(
            "MDM_PRODUCTION_EVIDENCE_REQUIRED",
            "artifact, source snapshot, and approved production scope are required",
        )
    try:
        from edge_mdm import verify_production_access

        verify_production_access(
            artifact,
            repository_root=repository_root,
            register_path=register_path,
            source_snapshot=source_snapshot,
            production_scope=production_scope,
        )
    except LobsError:
        raise
    except Exception as exc:
        raise LobsError("MDM_PRODUCTION_ACCESS_REJECTED", str(exc)) from exc
    return status


def materialise_production_enrichment(
    *,
    artifact: Any,
    repository_root: str | Path,
    register_path: str | Path,
    source_snapshot: Any,
    production_scope: Any,
) -> None:
    """Guard the intentionally unimplemented real enrichment path."""

    require_production_mdm_access(
        artifact=artifact,
        repository_root=repository_root,
        register_path=register_path,
        source_snapshot=source_snapshot,
        production_scope=production_scope,
    )
    raise LobsError(
        "MDM_ENRICHMENT_CALCULATION_NOT_IMPLEMENTED",
        "Stage 1 contains no real market feature calculation",
    )


def _session_date(row: Mapping[str, Any], *, index: int) -> str:
    text = _required_text(row.get("session_date"), field=f"sessions[{index}].session_date")
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise LobsError("SESSION_DATE_INVALID", f"invalid session date {text!r}") from exc
    return text


def _scoped_tradable_sessions(
    session_rows: Iterable[Mapping[str, Any]], *, exchange_id: str
) -> list[dict[str, Any]]:
    wanted = _required_text(exchange_id, field="exchange_id")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(session_rows):
        row = _required_mapping(raw, field=f"sessions[{index}]")
        if str(row.get("exchange_id", "")) != wanted:
            continue
        if str(row.get("session_state", "")).upper() not in TRADABLE_SESSION_STATES:
            continue
        session_date = _session_date(row, index=index)
        if session_date in seen:
            raise LobsError(
                "AMBIGUOUS_SESSION",
                f"multiple tradable session rows for {wanted}:{session_date}",
            )
        seen.add(session_date)
        available = parse_aware_timestamp(
            row.get("available_at"), field=f"sessions[{index}].available_at"
        )
        opened = parse_aware_timestamp(row.get("open_at"), field=f"sessions[{index}].open_at")
        closed = parse_aware_timestamp(row.get("close_at"), field=f"sessions[{index}].close_at")
        cutoff = parse_aware_timestamp(row.get("cutoff_at"), field=f"sessions[{index}].cutoff_at")
        if not opened < closed <= cutoff:
            raise LobsError("SESSION_CLOCK_INVALID", f"invalid clock order for {wanted}:{session_date}")
        result.append(
            {
                **dict(row),
                "session_date": session_date,
                "_available_at_utc": available,
                "_open_at_utc": opened,
                "_close_at_utc": closed,
                "_cutoff_at_utc": cutoff,
            }
        )
    return sorted(result, key=lambda row: (row["_open_at_utc"], row["session_date"]))


def derive_last_completed_session(
    session_rows: Iterable[Mapping[str, Any]],
    *,
    information_cutoff_timestamp: Any,
    exchange_id: str,
) -> dict[str, Any]:
    """Derive, never trust, the last known tradable completed session."""

    information_cutoff = parse_aware_timestamp(
        information_cutoff_timestamp, field="information_cutoff_timestamp"
    )
    sessions = _scoped_tradable_sessions(session_rows, exchange_id=exchange_id)
    eligible = [
        row
        for row in sessions
        if row["_available_at_utc"] <= information_cutoff
        and row["_cutoff_at_utc"] <= information_cutoff
    ]
    if not eligible:
        raise LobsError(
            "LAST_COMPLETED_SESSION_UNAVAILABLE",
            "no tradable session was both known and complete by the information cutoff",
        )
    selected = max(eligible, key=lambda row: (row["_cutoff_at_utc"], row["session_date"]))
    return {key: value for key, value in selected.items() if not key.startswith("_")}


def _reject_current_membership_claim(row: Mapping[str, Any], *, index: int) -> None:
    normalised = {str(key).casefold(): value for key, value in row.items()}
    for key in _CURRENT_MEMBERSHIP_KEYS:
        raw = normalised.get(key)
        if raw is True or str(raw).strip().upper() in {"TRUE", "YES", "1"}:
            raise LobsError(
                "CURRENT_MEMBERSHIP_FORBIDDEN",
                f"memberships[{index}].{key} cannot identify a contributing PIT record",
            )
    for key in _MEMBERSHIP_MODE_KEYS:
        value = str(normalised.get(key, "")).strip().upper()
        if value in _CURRENT_MEMBERSHIP_VALUES:
            raise LobsError(
                "CURRENT_MEMBERSHIP_FORBIDDEN",
                f"memberships[{index}].{key} uses present-day membership",
            )


def validate_test_only_feature_inputs(
    bar_rows: Iterable[Mapping[str, Any]],
    session_rows: Iterable[Mapping[str, Any]],
    *,
    information_cutoff_timestamp: Any,
    exchange_id: str,
    membership_rows: Iterable[Mapping[str, Any]] = (),
    requested_last_completed_session: str | None = None,
) -> FeatureInputSummary:
    """Validate synthetic contributing inputs without granting MDM authority."""

    cutoff = parse_aware_timestamp(
        information_cutoff_timestamp, field="information_cutoff_timestamp"
    )
    sessions = list(session_rows)
    completed = derive_last_completed_session(
        sessions,
        information_cutoff_timestamp=cutoff,
        exchange_id=exchange_id,
    )
    completed_date = str(completed["session_date"])
    if (
        requested_last_completed_session is not None
        and requested_last_completed_session != completed_date
    ):
        raise LobsError(
            "LAST_COMPLETED_SESSION_MISMATCH",
            "request value differs from the session derived from the admitted clock",
        )

    by_date = {
        row["session_date"]: row
        for row in _scoped_tradable_sessions(sessions, exchange_id=exchange_id)
    }
    bars = list(bar_rows)
    for index, raw in enumerate(bars):
        row = _required_mapping(raw, field=f"bars[{index}]")
        session_date = _session_date(row, index=index)
        available = parse_aware_timestamp(
            row.get("available_at"), field=f"bars[{index}].available_at"
        )
        if available > cutoff:
            raise LobsError(
                "MDM_INPUT_AFTER_INFORMATION_CUTOFF",
                f"bars[{index}] was not available by the information cutoff",
            )
        session = by_date.get(session_date)
        if session is None:
            raise LobsError("BAR_SESSION_UNRESOLVED", f"no tradable session for {session_date}")
        if session["_available_at_utc"] > cutoff or session["_cutoff_at_utc"] > cutoff:
            raise LobsError(
                "MDM_BAR_SESSION_NOT_COMPLETED",
                f"bar session {session_date} had not completed by the information cutoff",
            )

    memberships = list(membership_rows)
    effective_at = parse_aware_timestamp(
        completed.get("open_at"), field="last_completed_session.open_at"
    )
    for index, raw in enumerate(memberships):
        row = _required_mapping(raw, field=f"memberships[{index}]")
        _reject_current_membership_claim(row, index=index)
        available = parse_aware_timestamp(
            row.get("available_at"), field=f"memberships[{index}].available_at"
        )
        start = parse_aware_timestamp(
            row.get("effective_from"), field=f"memberships[{index}].effective_from"
        )
        end_raw = row.get("effective_to")
        end = (
            None
            if end_raw is None or str(end_raw).strip() == ""
            else parse_aware_timestamp(end_raw, field=f"memberships[{index}].effective_to")
        )
        if available > cutoff:
            raise LobsError(
                "MDM_INPUT_AFTER_INFORMATION_CUTOFF",
                f"memberships[{index}] was not available by the information cutoff",
            )
        if not (start <= effective_at and (end is None or effective_at < end)):
            raise LobsError(
                "INEFFECTIVE_MEMBERSHIP_FORBIDDEN",
                f"memberships[{index}] was not effective for the completed-session assessment",
            )

    return FeatureInputSummary(
        information_cutoff_timestamp=_timestamp_text(cutoff),
        exchange_id=exchange_id,
        last_completed_session=completed_date,
        bar_count=len(bars),
        membership_count=len(memberships),
    )


def reject_mdm_taxonomy_source_leakage(value: Any, *, path: str = "$") -> None:
    """Reject MDM taxonomy labels from a source/user observation document."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            child = f"{path}.{key}"
            if (
                str(key).casefold() == "taxonomy_origin"
                and str(item).strip().upper() == "MDM_TAXONOMY"
            ):
                raise LobsError(
                    "MDM_TAXONOMY_SOURCE_LEAKAGE",
                    f"MDM_TAXONOMY is forbidden in a source bundle at {child}",
                )
            reject_mdm_taxonomy_source_leakage(item, path=child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reject_mdm_taxonomy_source_leakage(item, path=f"{path}[{index}]")


def _reject_authority_claims(value: Any, *, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            child = f"{path}.{key}"
            truth_claim = item is True or str(item).strip().upper() in {
                "TRUE",
                "YES",
                "ADMITTED",
                "RELEASED",
                "PERMITTED",
            }
            if str(key).casefold() in _AUTHORITY_TRUE_KEYS and truth_claim:
                raise LobsError(
                    "TEST_ONLY_SELF_AUTHORISATION_FORBIDDEN",
                    f"caller-authored authority claim at {child}",
                )
            _reject_authority_claims(item, path=child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_authority_claims(item, path=f"{path}[{index}]")


def _reject_enrichment_outcome_fields(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            child = f"{path}.{key}"
            if str(key).casefold() in _ENRICHMENT_OUTCOME_KEYS:
                raise LobsError(
                    "OUTCOME_FIELD_FORBIDDEN_IN_ENRICHMENT",
                    f"{child} is outcome-bearing",
                )
            _reject_enrichment_outcome_fields(item, path=child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_enrichment_outcome_fields(item, path=f"{path}[{index}]")


def _reject_outcome_feature_id(value: Any, *, field: str) -> None:
    feature_id = _required_text(value, field=field)
    tokens = frozenset(token for token in re.split(r"[^A-Z0-9]+", feature_id.upper()) if token)
    if tokens & _OUTCOME_FEATURE_ID_TOKENS or "THRESHOLD_HIT" in feature_id.upper():
        raise LobsError(
            "OUTCOME_FEATURE_ID_FORBIDDEN",
            f"{field} names a future outcome/target rather than a cutoff feature",
        )


def _batch_value(batch_manifest: Mapping[str, Any], field: str) -> Any:
    if field in batch_manifest:
        return batch_manifest[field]
    batch = batch_manifest.get("batch")
    if isinstance(batch, Mapping) and field in batch:
        return batch[field]
    raise LobsError("BATCH_MANIFEST_FIELD_MISSING", f"batch manifest lacks {field}")


def validate_test_only_enrichment(
    document: Mapping[str, Any],
    *,
    batch_manifest: Mapping[str, Any],
    session_rows: Iterable[Mapping[str, Any]],
) -> TestOnlyValidationReport:
    """Structurally validate synthetic enrichment without authenticating it."""

    value = _required_mapping(document, field="enrichment")
    _reject_authority_claims(value)
    if value.get("schema_version") != ENRICHMENT_SCHEMA_VERSION:
        raise LobsError("ENRICHMENT_SCHEMA_VERSION_INVALID", "unsupported enrichment schema")
    if value.get("classification") != TEST_ONLY_CLASSIFICATION:
        raise LobsError(
            "TEST_ONLY_CLASSIFICATION_REQUIRED",
            "caller-authored enrichment must be explicitly test-only",
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
        raise LobsError("ENRICHMENT_BATCH_MISMATCH", "observation batch identity differs")
    cutoff_text = _required_text(
        value.get("information_cutoff_timestamp"), field="information_cutoff_timestamp"
    )
    cutoff = parse_aware_timestamp(cutoff_text, field="information_cutoff_timestamp")
    manifest_cutoff = parse_aware_timestamp(
        _batch_value(batch_manifest, "information_cutoff_timestamp"),
        field="batch_manifest.information_cutoff_timestamp",
    )
    if cutoff != manifest_cutoff:
        raise LobsError("ENRICHMENT_CUTOFF_MISMATCH", "batch and enrichment cutoffs differ")
    exchange_id = _required_text(value.get("exchange_id"), field="exchange_id")
    completed = derive_last_completed_session(
        session_rows,
        information_cutoff_timestamp=cutoff,
        exchange_id=exchange_id,
    )
    requested_completed = _required_text(
        value.get("last_eligible_completed_session"),
        field="last_eligible_completed_session",
    )
    if requested_completed != completed["session_date"]:
        raise LobsError(
            "LAST_COMPLETED_SESSION_MISMATCH",
            "enrichment session was not derived from the admitted session clock",
        )

    _require_sha256(value.get("source_artifact_manifest_sha256"), field="source_artifact_manifest_sha256")
    _require_sha256(value.get("source_manifest_sha256"), field="source_manifest_sha256")
    _require_sha256(value.get("software_source_sha256"), field="software_source_sha256")
    source_snapshot_id = _required_text(value.get("source_snapshot_id"), field="source_snapshot_id")
    rows = _required_sequence(value.get("rows"), field="rows")
    for index, raw in enumerate(rows):
        row = _required_mapping(raw, field=f"rows[{index}]")
        _reject_enrichment_outcome_fields(row, path=f"rows[{index}]")
        _reject_outcome_feature_id(
            row.get("feature_id"), field=f"rows[{index}].feature_id"
        )
        if str(row.get("derivation_type", "")) != "MDM_DERIVED":
            raise LobsError(
                "ENRICHMENT_DERIVATION_INVALID",
                f"rows[{index}] must declare the intended MDM_DERIVED layer",
            )
        if str(row.get("source_snapshot_id", "")) != source_snapshot_id:
            raise LobsError("ENRICHMENT_LINEAGE_MISMATCH", f"rows[{index}] snapshot differs")
        max_available = parse_aware_timestamp(
            row.get("max_available_at"), field=f"rows[{index}].max_available_at"
        )
        if max_available > cutoff:
            raise LobsError(
                "MDM_INPUT_AFTER_INFORMATION_CUTOFF",
                f"rows[{index}] includes information unavailable at cutoff",
            )
        max_session = _required_text(
            row.get("max_contributing_session"),
            field=f"rows[{index}].max_contributing_session",
        )
        try:
            max_session_date = date.fromisoformat(max_session)
            completed_session_date = date.fromisoformat(requested_completed)
        except ValueError as exc:
            raise LobsError("SESSION_DATE_INVALID", f"rows[{index}] session is invalid") from exc
        if max_session_date > completed_session_date:
            raise LobsError(
                "MDM_BAR_SESSION_NOT_COMPLETED",
                f"rows[{index}] includes a later session",
            )
    return TestOnlyValidationReport(
        document_type="MDM_ENRICHMENT",
        state="TEST_ONLY_STRUCTURALLY_VALID",
        checks=(
            "CALLER_CANNOT_SELF_AUTHORISE",
            "BATCH_AND_CUTOFF_BOUND",
            "LAST_COMPLETED_SESSION_DERIVED",
            "CONTRIBUTING_AVAILABILITY_BOUNDED",
            "OUTCOME_LAYER_EXCLUDED",
        ),
    )


__all__ = [
    "ENRICHMENT_SCHEMA_VERSION",
    "FeatureInputSummary",
    "MDM_STATUS_SCHEMA_VERSION",
    "MdmStatus",
    "STRUCTURAL_VALIDATION_ONLY",
    "TEST_ONLY_CLASSIFICATION",
    "TRADABLE_SESSION_STATES",
    "TestOnlyValidationReport",
    "derive_last_completed_session",
    "materialise_production_enrichment",
    "parse_aware_timestamp",
    "read_mdm_status",
    "reject_mdm_taxonomy_source_leakage",
    "require_production_mdm_access",
    "validate_test_only_enrichment",
    "validate_test_only_feature_inputs",
]
