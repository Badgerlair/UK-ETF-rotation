"""Fail-closed validation for leadership observation and import documents."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import math
from pathlib import PurePosixPath
import re
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .contracts import (
    ALLOWED_SOURCE_DERIVATIONS,
    AWAITING_PROVENANCE,
    CAPTURE_MODES,
    EXTRACTOR_ACTOR_TYPES,
    EXTRACTOR_KEYS,
    EXTRACTION_CONFIDENCES,
    FORBIDDEN_OUTCOME_KEYS,
    FORBIDDEN_SOURCE_DERIVATIONS,
    GENERIC_ID_RE,
    GROUP_CLASSIFICATIONS,
    GROUP_TYPES,
    HUMAN_OBSERVATION_SUBTYPE,
    IDENTITY_RESOLUTION_STATUSES,
    IMPORT_MANIFEST_KEYS,
    IMPORT_MANIFEST_SCHEMA_VERSION,
    INSTRUMENT_KINDS,
    INSTRUMENT_OBSERVATION_TYPES,
    INSTRUMENT_STATES,
    MACRO_CONTEXT_TYPES,
    MARKET_FIELDS,
    MARKET_STATES,
    OBSERVATION_ARRAY_NAMES,
    OBSERVATION_BATCH_ID_RE,
    OBSERVATION_DOCUMENT_KEYS,
    OBSERVATION_ID_RE,
    OBSERVATION_SCHEMA_VERSION,
    READY_FOR_IMPORT,
    RECORD_KEYS,
    SHA256_RE,
    SOURCE_ENTRY_KEYS,
    SOURCE_TYPES,
    STOCK_SETUP_STATES,
    STOCK_SOURCE_ROLES,
    TAXONOMY_ORIGINS,
    TICKER_RE,
    TIMESTAMP_PRECISIONS,
    USER_DERIVED_SOURCE_TYPES,
    VALIDATION_REPORT_SCHEMA_VERSION,
    VALIDATION_STATUSES,
)
from .errors import LobsError


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """A successful structural decision, never an admission seal."""

    document_type: str
    state: str
    checks: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return True

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": VALIDATION_REPORT_SCHEMA_VERSION,
            "document_type": self.document_type,
            "state": self.state,
            "passed": True,
            "hard_blocker_count": 0,
            "checks": [
                {"code": code, "status": "PASS", "severity": "MANDATORY"}
                for code in self.checks
            ],
        }


def _fail(code: str, message: str, path: str) -> None:
    raise LobsError(code, message, path=path)


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("OBJECT_REQUIRED", "must be an object", path)
    if any(not isinstance(key, str) for key in value):
        _fail("JSON_KEY_INVALID", "all object keys must be strings", path)
    return value


def _strict_keys(value: Mapping[str, Any], expected: frozenset[str], path: str) -> None:
    actual = frozenset(value)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        _fail(
            "SCHEMA_KEYS_MISMATCH",
            f"exact keys required; missing={missing!r}; unexpected={unexpected!r}",
            path,
        )


def _required_string(value: Any, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        _fail("STRING_REQUIRED", "must be a string", path)
    if value != value.strip():
        _fail("SURROUNDING_WHITESPACE", "must not have surrounding whitespace", path)
    if not allow_empty and not value:
        _fail("REQUIRED_VALUE_MISSING", "must be a non-empty string", path)
    return value


def _optional_string(value: Any, path: str, *, allow_empty: bool = False) -> str | None:
    if value is None:
        return None
    return _required_string(value, path, allow_empty=allow_empty)


def _required_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        _fail("BOOLEAN_REQUIRED", "must be a boolean", path)
    return value


def _optional_bool(value: Any, path: str) -> bool | None:
    if value is None:
        return None
    return _required_bool(value, path)


def _enum(value: Any, allowed: frozenset[str], path: str) -> str:
    result = _required_string(value, path)
    if result not in allowed:
        _fail("VALUE_NOT_ALLOWED", f"must be one of {sorted(allowed)!r}", path)
    return result


def _optional_enum(value: Any, allowed: frozenset[str], path: str) -> str | None:
    if value is None:
        return None
    return _enum(value, allowed, path)


_MUTABLE_ID_RE = re.compile(
    r"(^|[^a-z0-9])(latest|current|head|rolling)([^a-z0-9]|$)", re.IGNORECASE
)


def _identifier(value: Any, path: str, *, pattern: re.Pattern[str] | None = None) -> str:
    result = _required_string(value, path)
    if _MUTABLE_ID_RE.search(result) or "latest" in result.casefold():
        _fail("MUTABLE_IDENTIFIER_FORBIDDEN", "must not be a mutable alias", path)
    required_pattern = GENERIC_ID_RE if pattern is None else pattern
    if required_pattern.fullmatch(result) is None:
        _fail("INVALID_IDENTIFIER", "does not match the immutable identifier contract", path)
    return result


def _optional_identifier(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _identifier(value, path)


def _date(value: Any, path: str) -> date:
    rendered = _required_string(value, path)
    try:
        parsed = date.fromisoformat(rendered)
    except ValueError as exc:
        raise LobsError("INVALID_DATE", "must be an ISO-8601 date", path=path) from exc
    if parsed.isoformat() != rendered:
        _fail("INVALID_DATE", "must use canonical YYYY-MM-DD form", path)
    return parsed


def _optional_date(value: Any, path: str) -> date | None:
    if value is None:
        return None
    return _date(value, path)


def _zone(value: Any, path: str) -> tuple[str, ZoneInfo]:
    name = _required_string(value, path)
    try:
        return name, ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise LobsError(
            "INVALID_IANA_TIMEZONE", "must be an installed IANA timezone", path=path
        ) from exc


def _timestamp_with_zone(
    timestamp_value: Any,
    timezone_value: Any,
    timestamp_path: str,
    timezone_path: str,
    *,
    required: bool,
) -> datetime | None:
    if timestamp_value is None:
        if timezone_value is not None:
            _zone(timezone_value, timezone_path)
        if not required:
            return None
        _fail(
            "TIMESTAMP_TIMEZONE_PAIR_REQUIRED",
            "timestamp and IANA timezone are required",
            timestamp_path,
        )
    if timezone_value is None:
        _fail(
            "TIMESTAMP_TIMEZONE_PAIR_REQUIRED",
            "a present timestamp requires an IANA timezone",
            timezone_path,
        )
    rendered = _required_string(timestamp_value, timestamp_path)
    zone_name, zone = _zone(timezone_value, timezone_path)
    candidate = rendered[:-1] + "+00:00" if rendered.endswith("Z") else rendered
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise LobsError(
            "INVALID_TIMESTAMP", "must be an ISO-8601 timestamp", path=timestamp_path
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail("NAIVE_TIMESTAMP", "must include an explicit UTC offset", timestamp_path)
    expected_offset = parsed.astimezone(zone).utcoffset()
    if parsed.utcoffset() != expected_offset:
        _fail(
            "TIMEZONE_OFFSET_MISMATCH",
            f"timestamp offset does not match {zone_name!r} at that instant",
            timestamp_path,
        )
    return parsed


def _walk_firewall(value: Any, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        _fail("NONFINITE_JSON_NUMBER", "NaN and infinity are prohibited", path)
    if isinstance(value, Decimal) and not value.is_finite():
        _fail("NONFINITE_JSON_NUMBER", "non-finite Decimal is prohibited", path)
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                _fail("JSON_KEY_INVALID", "all object keys must be strings", path)
            normalised = re.sub(r"[^a-z0-9]+", "_", key.casefold()).strip("_")
            if (
                normalised in FORBIDDEN_OUTCOME_KEYS
                or normalised.startswith(("forward_", "future_", "subsequent_", "outcome_", "target_"))
                or normalised.endswith(("_outcome", "_target"))
            ):
                _fail(
                    "OUTCOME_FIELD_FORBIDDEN",
                    "forward/outcome-derived fields are prohibited from source input",
                    f"{path}.{key}",
                )
            _walk_firewall(item, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _walk_firewall(item, f"{path}[{index}]")


def _string_array(value: Any, path: str, *, require_nonempty: bool) -> tuple[str, ...]:
    if not isinstance(value, list):
        _fail("ARRAY_REQUIRED", "must be an array", path)
    result = tuple(_identifier(item, f"{path}[{index}]") for index, item in enumerate(value))
    if require_nonempty and not result:
        _fail("REQUIRED_VALUE_MISSING", "must contain at least one source ID", path)
    if len(result) != len(set(result)):
        _fail("DUPLICATE_SOURCE_ID", "source IDs must be unique", path)
    return result


def _validate_extractor(value: Any) -> None:
    extractor = _mapping(value, "$.extractor")
    _strict_keys(extractor, EXTRACTOR_KEYS, "$.extractor")
    _enum(extractor["actor_type"], EXTRACTOR_ACTOR_TYPES, "$.extractor.actor_type")
    _identifier(extractor["actor_id"], "$.extractor.actor_id")
    _required_string(extractor["method"], "$.extractor.method")
    _required_string(extractor["version"], "$.extractor.version")


def _identity_pair(record: Mapping[str, Any], path: str) -> None:
    status = _enum(
        record["identity_resolution_status"],
        IDENTITY_RESOLUTION_STATUSES,
        f"{path}.identity_resolution_status",
    )
    security_id = _optional_identifier(record["security_id"], f"{path}.security_id")
    if status == "UNRESOLVED" and security_id is not None:
        _fail(
            "IDENTITY_STATE_MISMATCH",
            "UNRESOLVED identity must have null security_id",
            f"{path}.security_id",
        )
    if status == "RESOLVED_POINT_IN_TIME" and security_id is None:
        _fail(
            "IDENTITY_STATE_MISMATCH",
            "RESOLVED_POINT_IN_TIME requires security_id",
            f"{path}.security_id",
        )


def _validate_common_record(
    record: Mapping[str, Any],
    *,
    path: str,
    record_type: str,
    draft: bool,
    batch_capture_mode: str,
    batch_source_ids: frozenset[str],
    cutoff: datetime | None,
    seen_observation_ids: set[str],
) -> tuple[str, datetime | None]:
    _strict_keys(record, RECORD_KEYS[record_type], path)
    observation_id = _identifier(
        record["observation_id"], f"{path}.observation_id", pattern=OBSERVATION_ID_RE
    )
    if observation_id in seen_observation_ids:
        _fail(
            "DUPLICATE_OBSERVATION_ID",
            "observation_id must be globally unique within the batch",
            f"{path}.observation_id",
        )
    seen_observation_ids.add(observation_id)

    mode = _enum(record["capture_mode"], CAPTURE_MODES, f"{path}.capture_mode")
    if mode != batch_capture_mode:
        _fail(
            "CAPTURE_MODE_MISMATCH",
            "record capture_mode must equal batch capture_mode",
            f"{path}.capture_mode",
        )

    derivation = _required_string(record["derivation_type"], f"{path}.derivation_type")
    if derivation in FORBIDDEN_SOURCE_DERIVATIONS or derivation not in ALLOWED_SOURCE_DERIVATIONS:
        _fail(
            "DERIVATION_LAYER_FORBIDDEN",
            "source bundles permit only SOURCE_DERIVED or qualifying USER_DERIVED records",
            f"{path}.derivation_type",
        )
    subtype = _optional_string(record["observation_subtype"], f"{path}.observation_subtype")
    if derivation == "USER_DERIVED" and subtype != HUMAN_OBSERVATION_SUBTYPE:
        _fail(
            "USER_DERIVED_SUBTYPE_REQUIRED",
            f"USER_DERIVED requires {HUMAN_OBSERVATION_SUBTYPE!r}",
            f"{path}.observation_subtype",
        )
    if derivation == "SOURCE_DERIVED" and subtype is not None:
        _fail(
            "SOURCE_DERIVED_SUBTYPE_FORBIDDEN",
            "SOURCE_DERIVED extraction must not be relabelled as a user observation",
            f"{path}.observation_subtype",
        )

    _required_string(record["source_text"], f"{path}.source_text")
    _enum(
        record["confidence_of_extraction"],
        EXTRACTION_CONFIDENCES,
        f"{path}.confidence_of_extraction",
    )
    _required_string(record["notes"], f"{path}.notes", allow_empty=True)

    source_id = _optional_identifier(record["source_id"], f"{path}.source_id")
    source_location = _optional_string(record["source_location"], f"{path}.source_location")
    if not draft and (source_id is None or source_location is None):
        _fail(
            "SOURCE_LINEAGE_INCOMPLETE",
            "non-draft records require source_id and source_location",
            path,
        )
    if source_id is not None and source_id not in batch_source_ids:
        _fail(
            "SOURCE_ID_NOT_DECLARED",
            "record source_id is absent from batch source_ids",
            f"{path}.source_id",
        )

    timestamp = _timestamp_with_zone(
        record["timestamp"],
        record["timezone"],
        f"{path}.timestamp",
        f"{path}.timezone",
        required=not draft,
    )
    if cutoff is not None and timestamp is not None and timestamp > cutoff:
        _fail(
            "OBSERVATION_AFTER_INFORMATION_CUTOFF",
            "structured observation timestamp is later than the batch cutoff",
            f"{path}.timestamp",
        )
    return derivation, timestamp


def _validate_specific_record(
    record_type: str,
    record: Mapping[str, Any],
    path: str,
    *,
    draft: bool,
    cutoff: datetime | None,
) -> None:
    if record_type == "market":
        _enum(record["field"], MARKET_FIELDS, f"{path}.field")
        _optional_string(record["metric"], f"{path}.metric")
        _optional_enum(record["state"], MARKET_STATES, f"{path}.state")
    elif record_type == "instruments":
        _required_string(record["instrument"], f"{path}.instrument")
        _enum(record["instrument_kind"], INSTRUMENT_KINDS, f"{path}.instrument_kind")
        _identity_pair(record, path)
        _enum(
            record["observation_type"],
            INSTRUMENT_OBSERVATION_TYPES,
            f"{path}.observation_type",
        )
        _optional_enum(record["state"], INSTRUMENT_STATES, f"{path}.state")
    elif record_type == "groups":
        _identifier(record["group_id"], f"{path}.group_id")
        _required_string(record["group_name"], f"{path}.group_name")
        _enum(record["group_type"], GROUP_TYPES, f"{path}.group_type")
        taxonomy_origin = _enum(
            record["taxonomy_origin"], TAXONOMY_ORIGINS, f"{path}.taxonomy_origin"
        )
        derivation = str(record["derivation_type"])
        expected_taxonomy = (
            "SOURCE_TAXONOMY" if derivation == "SOURCE_DERIVED" else "USER_TAXONOMY"
        )
        if taxonomy_origin != expected_taxonomy:
            _fail(
                "TAXONOMY_ORIGIN_MISMATCH",
                f"{derivation} group requires {expected_taxonomy}",
                f"{path}.taxonomy_origin",
            )
        classification = _optional_enum(
            record["source_classification"],
            GROUP_CLASSIFICATIONS,
            f"{path}.source_classification",
        )
        basis = _optional_string(record["classification_basis"], f"{path}.classification_basis")
        if classification is not None and basis is None:
            _fail(
                "CLASSIFICATION_BASIS_REQUIRED",
                "a source classification requires an explicit basis",
                f"{path}.classification_basis",
            )
    elif record_type == "stocks":
        ticker = _required_string(record["ticker"], f"{path}.ticker")
        if TICKER_RE.fullmatch(ticker) is None:
            _fail("INVALID_TICKER", "must preserve a canonical source ticker", f"{path}.ticker")
        _identity_pair(record, path)
        _optional_string(record["company_name"], f"{path}.company_name")
        _optional_identifier(record["group_id"], f"{path}.group_id")
        _enum(record["source_role"], STOCK_SOURCE_ROLES, f"{path}.source_role")
        _optional_string(record["setup_family"], f"{path}.setup_family")
        _optional_enum(record["setup_state"], STOCK_SETUP_STATES, f"{path}.setup_state")
        for key in (
            "relative_strength_description",
            "moving_average_description",
            "price_action_description",
            "volume_description",
        ):
            _optional_string(record[key], f"{path}.{key}")
    elif record_type == "futures_snapshot":
        _required_string(record["instrument"], f"{path}.instrument")
        _required_string(record["value"], f"{path}.value")
        _optional_string(record["change_absolute"], f"{path}.change_absolute")
        _optional_string(record["change_percent"], f"{path}.change_percent")
        observed_at = _timestamp_with_zone(
            record["observation_timestamp"],
            record["timezone"],
            f"{path}.observation_timestamp",
            f"{path}.timezone",
            required=not draft,
        )
        if cutoff is not None and observed_at is not None and observed_at > cutoff:
            _fail(
                "OBSERVATION_AFTER_INFORMATION_CUTOFF",
                "snapshot observation timestamp is later than the batch cutoff",
                f"{path}.observation_timestamp",
            )
        precision = _optional_enum(
            record["timestamp_precision"],
            TIMESTAMP_PRECISIONS,
            f"{path}.timestamp_precision",
        )
        if not draft and precision is None:
            _fail(
                "PROVENANCE_REQUIRED",
                "timestamp_precision is required",
                f"{path}.timestamp_precision",
            )
        _enum(record["source_type"], SOURCE_TYPES, f"{path}.source_type")
    elif record_type == "macro_context":
        _enum(record["context_type"], MACRO_CONTEXT_TYPES, f"{path}.context_type")
        _required_string(record["title"], f"{path}.title")
        _optional_string(record["description"], f"{path}.description")
    else:  # pragma: no cover - protected by the frozen array list
        _fail("UNKNOWN_RECORD_TYPE", f"unsupported record type {record_type!r}", path)


def validate_observation_document(
    value: Any, allow_draft: bool = False
) -> ValidationReport:
    """Validate one exact observation document or raise :class:`LobsError`.

    ``allow_draft`` permits null provenance only for the explicitly labelled
    non-authoritative awaiting-provenance state.  It never makes that state
    import-admissible.
    """

    _walk_firewall(value)
    document = _mapping(value, "$")
    _strict_keys(document, OBSERVATION_DOCUMENT_KEYS, "$")
    if document["schema_version"] != OBSERVATION_SCHEMA_VERSION:
        _fail(
            "SCHEMA_VERSION_UNSUPPORTED",
            f"must equal {OBSERVATION_SCHEMA_VERSION!r}",
            "$.schema_version",
        )
    batch_id = _identifier(
        document["observation_batch_id"],
        "$.observation_batch_id",
        pattern=OBSERVATION_BATCH_ID_RE,
    )
    observation_date = _date(document["observation_date"], "$.observation_date")
    matched = OBSERVATION_BATCH_ID_RE.fullmatch(batch_id)
    assert matched is not None
    if matched.group("date") != observation_date.strftime("%Y%m%d"):
        _fail(
            "BATCH_DATE_MISMATCH",
            "observation_date must match the date encoded in observation_batch_id",
            "$.observation_date",
        )

    status = _enum(document["validation_status"], VALIDATION_STATUSES, "$.validation_status")
    draft = status == AWAITING_PROVENANCE
    if draft and not allow_draft:
        _fail(
            "DRAFT_NOT_IMPORT_ADMISSIBLE",
            "awaiting-source/provenance drafts require explicit allow_draft=True",
            "$.validation_status",
        )
    if not draft and status != READY_FOR_IMPORT:
        _fail("VALIDATION_STATUS_INVALID", "non-draft must be READY_FOR_IMPORT", "$.validation_status")

    capture_mode = _enum(document["capture_mode"], CAPTURE_MODES, "$.capture_mode")
    cutoff = _timestamp_with_zone(
        document["information_cutoff_timestamp"],
        document["information_cutoff_timezone"],
        "$.information_cutoff_timestamp",
        "$.information_cutoff_timezone",
        required=not draft,
    )
    recorded_at = _timestamp_with_zone(
        document["recorded_at"],
        document["information_cutoff_timezone"],
        "$.recorded_at",
        "$.information_cutoff_timezone",
        required=not draft,
    )
    if (
        capture_mode == "PROSPECTIVE"
        and cutoff is not None
        and recorded_at is not None
        and recorded_at > cutoff
    ):
        _fail(
            "RECORDED_AFTER_INFORMATION_CUTOFF",
            "prospective recorded_at must be no later than information cutoff",
            "$.recorded_at",
        )

    source_ids = _string_array(
        document["source_ids"], "$.source_ids", require_nonempty=not draft
    )
    source_id_set = frozenset(source_ids)
    _validate_extractor(document["extractor"])
    _optional_identifier(document["supersedes_batch_id"], "$.supersedes_batch_id")
    _required_string(document["notes"], "$.notes", allow_empty=True)

    seen_observation_ids: set[str] = set()
    for record_type in OBSERVATION_ARRAY_NAMES:
        records = document[record_type]
        if not isinstance(records, list):
            _fail("ARRAY_REQUIRED", "must be an array", f"$.{record_type}")
        for index, raw_record in enumerate(records):
            path = f"$.{record_type}[{index}]"
            record = _mapping(raw_record, path)
            _validate_common_record(
                record,
                path=path,
                record_type=record_type,
                draft=draft,
                batch_capture_mode=capture_mode,
                batch_source_ids=source_id_set,
                cutoff=cutoff,
                seen_observation_ids=seen_observation_ids,
            )
            _validate_specific_record(
                record_type, record, path, draft=draft, cutoff=cutoff
            )

    state = (
        "DRAFT_STRUCTURALLY_ACCEPTED_NON_AUTHORITATIVE"
        if draft
        else "STRUCTURALLY_VALID_IMPORT_CANDIDATE"
    )
    return ValidationReport(
        document_type="OBSERVATION_BATCH",
        state=state,
        checks=(
            "STRICT_SCHEMA",
            "TIMESTAMP_AND_TIMEZONE",
            "CAPTURE_MODE",
            "SOURCE_LINEAGE",
            "DERIVATION_LAYER",
            "OUTCOME_FIREWALL",
        ),
    )


def _relative_path(value: Any, path: str, *, required: bool) -> PurePosixPath | None:
    if value is None:
        if required:
            _fail("PROVENANCE_REQUIRED", "relative path is required", path)
        return None
    rendered = _required_string(value, path)
    if "\\" in rendered:
        _fail("INVALID_RELATIVE_PATH", "must use POSIX separators", path)
    result = PurePosixPath(rendered)
    if result.is_absolute() or not result.parts or ".." in result.parts or result == PurePosixPath("."):
        _fail("PATH_ESCAPE_FORBIDDEN", "path must stay within the configured inbox", path)
    return result


def _template_string(value: Any, path: str, *, template: bool) -> str | None:
    result = _optional_string(value, path)
    if result is None and not template:
        _fail("PROVENANCE_REQUIRED", "non-template manifest requires this value", path)
    return result


def _template_identifier(value: Any, path: str, *, template: bool) -> str | None:
    if value is None:
        if not template:
            _fail("PROVENANCE_REQUIRED", "non-template manifest requires this value", path)
        return None
    return _identifier(value, path)


def _source_timestamp(
    source: Mapping[str, Any], path: str, *, template: bool
) -> datetime | None:
    return _timestamp_with_zone(
        source["source_capture_timestamp"],
        source["timezone"],
        f"{path}.source_capture_timestamp",
        f"{path}.timezone",
        required=not template,
    )


def validate_import_manifest_document(
    value: Any,
    observation: Any,
    allow_template: bool = False,
) -> ValidationReport:
    """Validate an exact import manifest against its observation document."""

    _walk_firewall(value)
    manifest = _mapping(value, "$")
    _strict_keys(manifest, IMPORT_MANIFEST_KEYS, "$")
    if manifest["schema_version"] != IMPORT_MANIFEST_SCHEMA_VERSION:
        _fail(
            "SCHEMA_VERSION_UNSUPPORTED",
            f"must equal {IMPORT_MANIFEST_SCHEMA_VERSION!r}",
            "$.schema_version",
        )

    # Validate a draft structurally here so this manifest boundary can issue
    # the more specific TEMPLATE_NOT_IMPORT_ADMISSIBLE decision below.  The
    # returned observation report cannot itself authorise an import.
    validate_observation_document(observation, allow_draft=True)
    observation_document = _mapping(observation, "$observation")
    batch_id = _identifier(
        manifest["observation_batch_id"],
        "$.observation_batch_id",
        pattern=OBSERVATION_BATCH_ID_RE,
    )
    if batch_id != observation_document["observation_batch_id"]:
        _fail(
            "BATCH_ID_MISMATCH",
            "manifest and observation batch IDs must be identical",
            "$.observation_batch_id",
        )
    capture_mode = _enum(manifest["capture_mode"], CAPTURE_MODES, "$.capture_mode")
    if capture_mode != observation_document["capture_mode"]:
        _fail(
            "CAPTURE_MODE_MISMATCH",
            "manifest and observation capture modes must be identical",
            "$.capture_mode",
        )
    status = _enum(manifest["validation_status"], VALIDATION_STATUSES, "$.validation_status")
    if status != observation_document["validation_status"]:
        _fail(
            "VALIDATION_STATUS_MISMATCH",
            "manifest and observation validation statuses must be identical",
            "$.validation_status",
        )
    template = status == AWAITING_PROVENANCE
    if template and not allow_template:
        _fail(
            "TEMPLATE_NOT_IMPORT_ADMISSIBLE",
            "awaiting-source/provenance template requires allow_template=True",
            "$.validation_status",
        )
    _relative_path(manifest["observation_path"], "$.observation_path", required=not template)
    _required_string(manifest["notes"], "$.notes", allow_empty=True)

    sources_value = manifest["sources"]
    if not isinstance(sources_value, list):
        _fail("ARRAY_REQUIRED", "must be an array", "$.sources")
    if not template and not sources_value:
        _fail("REQUIRED_VALUE_MISSING", "import manifest must contain sources", "$.sources")

    cutoff: datetime | None = None
    if observation_document["information_cutoff_timestamp"] is not None:
        cutoff = _timestamp_with_zone(
            observation_document["information_cutoff_timestamp"],
            observation_document["information_cutoff_timezone"],
            "$observation.information_cutoff_timestamp",
            "$observation.information_cutoff_timezone",
            required=True,
        )

    source_by_id: dict[str, Mapping[str, Any]] = {}
    for index, raw_source in enumerate(sources_value):
        path = f"$.sources[{index}]"
        source = _mapping(raw_source, path)
        _strict_keys(source, SOURCE_ENTRY_KEYS, path)
        source_id = _identifier(source["source_id"], f"{path}.source_id")
        if source_id in source_by_id:
            _fail("DUPLICATE_SOURCE_ID", "source IDs must be unique", f"{path}.source_id")
        source_by_id[source_id] = source
        source_type = _enum(source["source_type"], SOURCE_TYPES, f"{path}.source_type")
        _required_string(source["source_name"], f"{path}.source_name")
        _required_string(source["source_title"], f"{path}.source_title")
        original_filename = _template_string(
            source["source_original_filename"],
            f"{path}.source_original_filename",
            template=template,
        )
        _template_identifier(
            source["source_identity"], f"{path}.source_identity", template=template
        )
        relative = _relative_path(source["path"], f"{path}.path", required=not template)
        if original_filename is not None and relative is not None and relative.name != original_filename:
            _fail(
                "SOURCE_FILENAME_MISMATCH",
                "source_original_filename must equal the final path component",
                f"{path}.source_original_filename",
            )

        source_mode = _enum(source["capture_mode"], CAPTURE_MODES, f"{path}.capture_mode")
        if source_mode != capture_mode:
            _fail(
                "CAPTURE_MODE_MISMATCH",
                "source capture_mode must equal batch capture_mode",
                f"{path}.capture_mode",
            )
        captured_at = _source_timestamp(source, path, template=template)
        publication_at: datetime | None = None
        if source["source_publication_timestamp"] is not None:
            publication_at = _timestamp_with_zone(
                source["source_publication_timestamp"],
                source["timezone"],
                f"{path}.source_publication_timestamp",
                f"{path}.timezone",
                required=True,
            )
        publication_date = _optional_date(
            source["source_publication_date"], f"{path}.source_publication_date"
        )
        precision = _optional_enum(
            source["timestamp_precision"], TIMESTAMP_PRECISIONS, f"{path}.timestamp_precision"
        )
        if not template and precision is None:
            _fail("PROVENANCE_REQUIRED", "timestamp_precision is required", f"{path}.timestamp_precision")
        historical = _optional_bool(
            source["historical_reconstruction"], f"{path}.historical_reconstruction"
        )
        attested = _optional_bool(
            source["contemporaneous_capture_attested"],
            f"{path}.contemporaneous_capture_attested",
        )
        if not template and (historical is None or attested is None):
            _fail("PROVENANCE_REQUIRED", "capture flags are required", path)
        if not template and capture_mode == "PROSPECTIVE":
            if historical is not False or attested is not True:
                _fail(
                    "PROSPECTIVE_PROVENANCE_INVALID",
                    "prospective sources require historical_reconstruction=false and contemporaneous attestation=true",
                    path,
                )
        if not template and capture_mode == "RETROSPECTIVE" and historical is not True:
            _fail(
                "RETROSPECTIVE_PROVENANCE_INVALID",
                "retrospective sources require historical_reconstruction=true",
                f"{path}.historical_reconstruction",
            )
        if (
            capture_mode == "PROSPECTIVE"
            and cutoff is not None
            and captured_at is not None
            and captured_at > cutoff
        ):
            _fail(
                "SOURCE_CAPTURE_AFTER_INFORMATION_CUTOFF",
                "source capture timestamp is later than the information cutoff",
                f"{path}.source_capture_timestamp",
            )
        if cutoff is not None and publication_at is not None and publication_at > cutoff:
            _fail(
                "SOURCE_PUBLICATION_AFTER_INFORMATION_CUTOFF",
                "source publication timestamp is later than the information cutoff",
                f"{path}.source_publication_timestamp",
            )
        if publication_at is not None and publication_date is not None:
            zone_name, zone = _zone(source["timezone"], f"{path}.timezone")
            del zone_name
            if publication_at.astimezone(zone).date() != publication_date:
                _fail(
                    "PUBLICATION_DATE_MISMATCH",
                    "publication date disagrees with publication timestamp in source timezone",
                    f"{path}.source_publication_date",
                )
        if cutoff is not None and publication_date is not None:
            _, source_zone = _zone(source["timezone"], f"{path}.timezone")
            if publication_date > cutoff.astimezone(source_zone).date():
                _fail(
                    "SOURCE_PUBLICATION_AFTER_INFORMATION_CUTOFF",
                    "source publication date is later than the information cutoff date",
                    f"{path}.source_publication_date",
                )
        expected_hash = source["expected_sha256"]
        if expected_hash is not None:
            rendered_hash = _required_string(expected_hash, f"{path}.expected_sha256")
            if SHA256_RE.fullmatch(rendered_hash) is None:
                _fail(
                    "INVALID_SHA256",
                    "must be a lowercase 64-character SHA-256 or null",
                    f"{path}.expected_sha256",
                )
        _optional_string(source["parser_version"], f"{path}.parser_version")
        _required_string(source["notes"], f"{path}.notes", allow_empty=True)
        if source_type == "WEB_METADATA" and not template and relative is None:
            _fail("RAW_SOURCE_REQUIRED", "web metadata must be retained as a file", f"{path}.path")

    observation_source_ids = frozenset(str(item) for item in observation_document["source_ids"])
    manifest_source_ids = frozenset(source_by_id)
    if observation_source_ids != manifest_source_ids:
        _fail(
            "SOURCE_ID_SET_MISMATCH",
            f"observation/manifest source sets differ; observation={sorted(observation_source_ids)!r}; manifest={sorted(manifest_source_ids)!r}",
            "$.sources",
        )

    for record_type in OBSERVATION_ARRAY_NAMES:
        for index, raw_record in enumerate(observation_document[record_type]):
            record = _mapping(raw_record, f"$observation.{record_type}[{index}]")
            source_id = record["source_id"]
            if source_id is None:
                continue
            source = source_by_id[str(source_id)]
            derivation = record["derivation_type"]
            if (
                record_type == "futures_snapshot"
                and record["source_type"] != source["source_type"]
            ):
                _fail(
                    "SOURCE_TYPE_MISMATCH",
                    "futures snapshot source_type must match its raw source provenance",
                    f"$observation.{record_type}[{index}].source_type",
                )
            if derivation == "USER_DERIVED" and source["source_type"] not in USER_DERIVED_SOURCE_TYPES:
                _fail(
                    "USER_DERIVED_SOURCE_REQUIRED",
                    "USER_DERIVED records require an immutable analyst-note or structured-manual source",
                    f"$observation.{record_type}[{index}].source_id",
                )
            source_identity_text = " ".join(
                str(source[key])
                for key in ("source_name", "source_title", "source_identity")
                if source[key] is not None
            ).casefold()
            if (
                "traderlion" in source_identity_text
                or "richard moglen" in source_identity_text
            ) and derivation != "SOURCE_DERIVED":
                _fail(
                    "NAMED_SOURCE_DERIVATION_MISMATCH",
                    "manual TraderLion/Richard Moglen extraction remains SOURCE_DERIVED",
                    f"$observation.{record_type}[{index}].derivation_type",
                )

    state = (
        "TEMPLATE_STRUCTURALLY_ACCEPTED_NON_AUTHORITATIVE"
        if template
        else "IMPORT_CONTRACT_VALID_NON_AUTHORITATIVE"
    )
    return ValidationReport(
        document_type="IMPORT_MANIFEST",
        state=state,
        checks=(
            "STRICT_SCHEMA",
            "OBSERVATION_BINDING",
            "SOURCE_ID_SET",
            "SOURCE_PROVENANCE",
            "TIMESTAMP_AND_TIMEZONE",
            "CAPTURE_MODE",
            "DERIVATION_LAYER",
            "OUTCOME_FIREWALL",
        ),
    )
