"""Mandatory scientific validation and fail-closed admissibility decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping

from .actions import RETURN_COLUMNS, corporate_action_errors
from .assemble import (
    PANEL_COLUMNS,
    AssemblyError,
    enforce_outcome_firewall,
    observation_key_errors,
)
from .contracts import (
    MDM_SOURCE_AUTHORITY,
    REQUIRED_COLUMN_TYPES,
    REQUIRED_SORT_KEYS,
    REQUIRED_TABLES,
)
from .fingerprint import logical_rows_fingerprint, package_source_fingerprint
from .source import VerifiedMdmSnapshot
from .temporal import (
    identity_interval_errors,
    interval_contains,
    optional_timestamp,
    parse_timestamp,
)
from .universe import UNIVERSE_COLUMNS


HARD_FAILURE_CODES = frozenset(
    {
        "AUTHORISED_MDM_SOURCE",
        "SNAPSHOT_INTEGRITY",
        "REQUIRED_SCHEMA",
        "STABLE_IDENTITY",
        "TRADING_CALENDAR",
        "DAILY_OBSERVATIONS",
        "POINT_IN_TIME_AVAILABILITY",
        "CORPORATE_ACTIONS",
        "HISTORICAL_UNIVERSE",
        "FEATURE_READY_KEYS",
        "TYPED_MISSINGNESS",
        "OUTCOME_FIREWALL",
        "LINEAGE",
        "DETERMINISTIC_REPLAY",
    }
)


@dataclass(frozen=True)
class CheckResult:
    code: str
    status: str
    severity: str
    count: int
    detail: str
    error_codes: tuple[str, ...] = ()
    sample_errors: tuple[Mapping[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "status": self.status,
            "severity": self.severity,
            "count": self.count,
            "detail": self.detail,
            "error_codes": list(self.error_codes),
            "sample_errors": [dict(error) for error in self.sample_errors],
        }


@dataclass(frozen=True)
class ValidationReport:
    state: str
    checks: tuple[CheckResult, ...]
    hard_blocker_count: int

    @property
    def passed(self) -> bool:
        return self.hard_blocker_count == 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "edge.validation_report.v1",
            "state": self.state,
            "hard_blocker_count": self.hard_blocker_count,
            "checks": [check.as_dict() for check in self.checks],
        }


@dataclass(frozen=True)
class AdmissionEvidence:
    """Mechanically derived evidence required to issue an admission decision."""

    snapshot: VerifiedMdmSnapshot
    requested_fields: tuple[Mapping[str, str], ...]
    field_roles: Mapping[str, str]
    lineage_manifest: Mapping[str, Any]
    first_fingerprints: Mapping[str, str]
    replay_fingerprints: Mapping[str, str]


def _evidence_checks(
    evidence: AdmissionEvidence,
    computed_fingerprints: Mapping[str, str],
    computed_scoped_source_fingerprints: Mapping[str, str],
) -> tuple[bool, bool, bool, bool, bool, str]:
    snapshot = evidence.snapshot
    snapshot.assert_unchanged()
    source_verified = (
        snapshot.manifest.source_authority == MDM_SOURCE_AUTHORITY
        and {table.manifest.logical_name for table in snapshot.tables}
        == set(REQUIRED_TABLES)
    )
    schema_verified = all(
        table.columns
        == tuple(REQUIRED_COLUMN_TYPES[table.manifest.logical_name])
        and bool(table.verified_schema_sha256)
        and bool(table.verified_logical_sha256)
        for table in snapshot.tables
    )
    try:
        enforce_outcome_firewall(evidence.requested_fields, evidence.field_roles)
        outcome_firewall_passed = True
    except AssemblyError:
        outcome_firewall_passed = False
    required_lineage = {
        "source_snapshot_id",
        "source_manifest_sha256",
        "request_id",
        "policy_versions",
        "source_table_logical_sha256",
        "scoped_source_logical_sha256",
        "universe_logical_sha256",
        "panel_logical_sha256",
        "return_view_logical_sha256",
        "field_lineage_version",
        "observable_panel_field_lineage",
        "software_source_sha256",
        "production_scope_approval_id",
        "capability_audit_id",
    }
    lineage_complete = (
        required_lineage <= set(evidence.lineage_manifest)
        and evidence.lineage_manifest.get("source_snapshot_id")
        == snapshot.manifest.snapshot_id
        and evidence.lineage_manifest.get("source_manifest_sha256")
        == snapshot.manifest_sha256
        and evidence.lineage_manifest.get("source_table_logical_sha256")
        == {
            table.manifest.logical_name: table.verified_logical_sha256
            for table in snapshot.tables
        }
        and evidence.lineage_manifest.get("scoped_source_logical_sha256")
        == computed_scoped_source_fingerprints
        and evidence.lineage_manifest.get("universe_logical_sha256")
        == computed_fingerprints.get("universe")
        and evidence.lineage_manifest.get("panel_logical_sha256")
        == computed_fingerprints.get("observable_panel")
        and evidence.lineage_manifest.get("return_view_logical_sha256")
        == computed_fingerprints.get("return_consistent_view")
        and set(evidence.lineage_manifest.get("observable_panel_field_lineage", {}))
        == set(PANEL_COLUMNS)
        and evidence.lineage_manifest.get("software_source_sha256")
        == package_source_fingerprint()
    )
    deterministic_replay_passed = (
        bool(evidence.first_fingerprints)
        and evidence.first_fingerprints == computed_fingerprints
        and evidence.first_fingerprints == evidence.replay_fingerprints
        and all(evidence.first_fingerprints.values())
    )
    source_detail = (
        f"verified MDM snapshot {snapshot.manifest.snapshot_id}; "
        f"source_kind={snapshot.manifest.source_kind}; "
        f"production_use_permitted={snapshot.production_use_permitted}"
    )
    return (
        source_verified,
        schema_verified,
        lineage_complete,
        outcome_firewall_passed,
        deterministic_replay_passed,
        source_detail,
    )


def _result(code: str, errors: Iterable[Any], detail: str) -> CheckResult:
    material = list(errors)
    normalised: list[Mapping[str, Any]] = []
    for error in material:
        normalised.append(error if isinstance(error, Mapping) else {"code": str(error)})
    error_codes = tuple(
        sorted({str(error.get("code", "UNSPECIFIED")) for error in normalised})
    )
    return CheckResult(
        code=code,
        status="PASS" if not material else "FAIL",
        severity="MANDATORY",
        count=len(material),
        detail=detail,
        error_codes=error_codes,
        sample_errors=tuple(normalised[:10]),
    )


def _boolean_result(code: str, passed: bool, detail: str) -> CheckResult:
    return CheckResult(
        code=code,
        status="PASS" if passed else "FAIL",
        severity="MANDATORY",
        count=0 if passed else 1,
        detail=detail,
        error_codes=() if passed else (code,),
        sample_errors=() if passed else ({"code": code},),
    )


CALENDAR_CUTOFF_LAGS = {"CAL-TEST-001": timedelta(minutes=5)}


def calendar_errors(
    rows: list[Mapping[str, Any]], *, calendar_policy_version: str
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    expected_cutoff_lag = CALENDAR_CUTOFF_LAGS.get(calendar_policy_version)
    if expected_cutoff_lag is None:
        errors.append(
            {
                "code": "UNSUPPORTED_CALENDAR_POLICY",
                "policy": calendar_policy_version,
            }
        )
    seen: set[tuple[str, str]] = set()
    trading_by_exchange: dict[str, list[Mapping[str, Any]]] = {}
    for row in sorted(
        rows,
        key=lambda item: (
            str(item.get("exchange_id", "")),
            str(item.get("session_date", "")),
        ),
    ):
        exchange_id = str(row.get("exchange_id", "")).strip()
        session_date = str(row.get("session_date", "")).strip()
        key = (exchange_id, session_date)
        if not exchange_id or not session_date or key in seen:
            errors.append({"code": "DUPLICATE_OR_MISSING_SESSION", "key": str(key)})
        seen.add(key)
        if not str(row.get("source_record_id", "")).strip():
            errors.append({"code": "MISSING_CALENDAR_LINEAGE", "key": str(key)})
        if str(row.get("quality_state", "")).upper() != "PASSED":
            errors.append({"code": "CALENDAR_QUALITY_NOT_PASSED", "key": str(key)})
        state = str(row.get("session_state", "")).upper()
        if state in {"REGULAR", "EARLY_CLOSE"}:
            try:
                open_at = parse_timestamp(row.get("open_at"), field="open_at")
                close_at = parse_timestamp(row.get("close_at"), field="close_at")
                cutoff_at = parse_timestamp(row.get("cutoff_at"), field="cutoff_at")
                if not open_at < close_at <= cutoff_at:
                    errors.append({"code": "INVALID_SESSION_ORDER", "key": str(key)})
                if (
                    expected_cutoff_lag is not None
                    and cutoff_at - close_at != expected_cutoff_lag
                ):
                    errors.append(
                        {
                            "code": "CALENDAR_CUTOFF_POLICY_MISMATCH",
                            "key": str(key),
                        }
                    )
                early_close = _bool(row.get("early_close"))
                if early_close != (state == "EARLY_CLOSE"):
                    errors.append({"code": "EARLY_CLOSE_STATE_MISMATCH", "key": str(key)})
                if parse_timestamp(row.get("available_at"), field="available_at") > open_at:
                    errors.append({"code": "CALENDAR_NOT_KNOWN_BY_SESSION_OPEN", "key": str(key)})
                trading_by_exchange.setdefault(exchange_id, []).append(row)
            except ValueError as exc:
                errors.append(
                    {
                        "code": "INVALID_SESSION_TIME",
                        "key": str(key),
                        "detail": str(exc),
                    }
                )
        elif state not in {"HOLIDAY", "CLOSED"}:
            errors.append({"code": "UNKNOWN_SESSION_STATE", "key": str(key)})
        else:
            try:
                available = parse_timestamp(row.get("available_at"), field="available_at")
                if available.date().isoformat() > session_date:
                    errors.append({"code": "CLOSURE_NOT_KNOWN_BY_SESSION_DATE", "key": str(key)})
            except ValueError as exc:
                errors.append({"code": "INVALID_CALENDAR_AVAILABILITY", "key": str(key), "detail": str(exc)})
        if not str(row.get("timezone", "")).strip():
            errors.append({"code": "MISSING_SESSION_TIMEZONE", "key": str(key)})

    for exchange_id, trading_rows in trading_by_exchange.items():
        ordered = sorted(trading_rows, key=lambda row: str(row["session_date"]))
        previous_cutoff = None
        for index, row in enumerate(ordered):
            key = f"{exchange_id}:{row['session_date']}"
            open_at = parse_timestamp(row["open_at"], field="open_at")
            cutoff_at = parse_timestamp(row["cutoff_at"], field="cutoff_at")
            if previous_cutoff is not None and open_at <= previous_cutoff:
                errors.append({"code": "OVERLAPPING_SESSIONS", "key": key})
            previous_cutoff = cutoff_at
            expected_previous = "" if index == 0 else str(ordered[index - 1]["session_date"])
            expected_next = "" if index + 1 == len(ordered) else str(ordered[index + 1]["session_date"])
            actual_previous = _optional_text(row.get("previous_session_date"))
            actual_next = _optional_text(row.get("next_session_date"))
            # A bounded extract may legitimately point just outside its first
            # and last retained dates. Internal links must be exact.
            if index > 0 and actual_previous != expected_previous:
                errors.append({"code": "PREVIOUS_SESSION_MISMATCH", "key": key})
            if index + 1 < len(ordered) and actual_next != expected_next:
                errors.append({"code": "NEXT_SESSION_MISMATCH", "key": key})
    return errors


def observation_value_errors(rows: list[Mapping[str, Any]]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for row in rows:
        record_id = str(row.get("source_record_id", ""))
        try:
            values = {
                name: Decimal(str(row[name]))
                for name in ("open", "high", "low", "close", "volume")
            }
            if any(not value.is_finite() for value in values.values()):
                raise InvalidOperation
            if min(values[name] for name in ("open", "high", "low", "close")) <= 0:
                errors.append({"code": "NON_POSITIVE_PRICE", "record": record_id})
            if values["volume"] < 0 or values["volume"] != values["volume"].to_integral():
                errors.append({"code": "INVALID_VOLUME", "record": record_id})
            if values["low"] > min(
                values["open"], values["close"], values["high"]
            ):
                errors.append({"code": "INVALID_OHLC_LOW", "record": record_id})
            if values["high"] < max(
                values["open"], values["close"], values["low"]
            ):
                errors.append({"code": "INVALID_OHLC_HIGH", "record": record_id})
            if str(row.get("price_basis", "")).upper() != "RAW_UNADJUSTED":
                errors.append({"code": "UNKNOWN_PRICE_BASIS", "record": record_id})
            if str(row.get("value_state", "")).upper() != "PRESENT":
                errors.append({"code": "OBSERVED_VALUE_NOT_PRESENT", "record": record_id})
            if str(row.get("quality_state", "")).upper() != "PASSED":
                errors.append({"code": "OBSERVATION_NOT_PASSED", "record": record_id})
            parse_timestamp(row.get("available_at"), field="available_at")
        except (KeyError, InvalidOperation, ValueError) as exc:
            errors.append(
                {
                    "code": "INVALID_OBSERVATION_VALUE",
                    "record": record_id,
                    "detail": str(exc),
                }
            )
    return errors


def universe_errors(
    rows: list[Mapping[str, Any]],
    identity_rows: list[Mapping[str, Any]],
    session_rows: list[Mapping[str, Any]],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (
            str(row.get("exchange_id", "")),
            str(row.get("session_date", "")),
            str(row.get("security_id", "")),
        )
        if key in seen:
            errors.append({"code": "DUPLICATE_UNIVERSE_KEY", "key": str(key)})
        seen.add(key)
        candidate = _bool(row.get("candidate"))
        eligible = _bool(row.get("eligible"))
        if eligible and not candidate:
            errors.append({"code": "ELIGIBLE_NON_CANDIDATE", "key": str(key)})
        if not eligible and not str(row.get("exclusion_reason", "")).strip():
            errors.append({"code": "MISSING_EXCLUSION_REASON", "key": str(key)})
        if str(row.get("lifecycle_state", "")).upper() == "DELISTED" and candidate:
            if str(row.get("exclusion_reason", "")) != "TERMINAL_SETTLEMENT_ONLY":
                errors.append(
                    {"code": "INVALID_TERMINAL_UNIVERSE_STATE", "key": str(key)}
                )

    expected: set[tuple[str, str, str]] = set()
    exchanges_by_security: dict[str, set[str]] = {}
    for identity in identity_rows:
        exchanges_by_security.setdefault(str(identity["security_id"]), set()).add(
            str(identity["exchange_id"])
        )
    for session in session_rows:
        if str(session.get("session_state", "")).upper() not in {
            "REGULAR",
            "EARLY_CLOSE",
        }:
            continue
        exchange_id = str(session["exchange_id"])
        for security_id, exchanges in exchanges_by_security.items():
            if exchange_id in exchanges:
                expected.add((exchange_id, str(session["session_date"]), security_id))
    for missing in sorted(expected - seen):
        errors.append({"code": "MISSING_UNIVERSE_ASSESSMENT", "key": str(missing)})
    return errors


def membership_errors(rows: list[Mapping[str, Any]]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    seen_records: set[str] = set()
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for row in rows:
        record_id = str(row.get("source_record_id", "")).strip()
        if not record_id or record_id in seen_records:
            errors.append(
                {"code": "DUPLICATE_OR_MISSING_MEMBERSHIP_RECORD", "record": record_id}
            )
        seen_records.add(record_id)
        key = (str(row.get("universe_id", "")), str(row.get("listing_id", "")))
        grouped.setdefault(key, []).append(row)
        try:
            start = parse_timestamp(row.get("effective_from"), field="effective_from")
            end = optional_timestamp(row.get("effective_to"), field="effective_to")
            published = parse_timestamp(row.get("published_at"), field="published_at")
            available = parse_timestamp(row.get("available_at"), field="available_at")
            if end is not None and end <= start:
                errors.append({"code": "INVALID_MEMBERSHIP_INTERVAL", "record": record_id})
            if published > available:
                errors.append(
                    {"code": "MEMBERSHIP_PUBLISHED_AFTER_AVAILABLE", "record": record_id}
                )
        except ValueError as exc:
            errors.append(
                {"code": "INVALID_MEMBERSHIP_TIME", "record": record_id, "detail": str(exc)}
            )
        if str(row.get("membership_state", "")).upper() not in {
            "INCLUDED",
            "EXCLUDED",
            "MEMBER",
            "ELIGIBLE",
        }:
            errors.append({"code": "UNKNOWN_MEMBERSHIP_STATE", "record": record_id})
        if str(row.get("quality_state", "")).upper() != "PASSED":
            errors.append({"code": "MEMBERSHIP_QUALITY_NOT_PASSED", "record": record_id})

    for key, history in grouped.items():
        ordered = sorted(
            history,
            key=lambda row: parse_timestamp(row["effective_from"], field="effective_from"),
        )
        for left, right in zip(ordered, ordered[1:]):
            left_end = optional_timestamp(left.get("effective_to"), field="effective_to")
            right_start = parse_timestamp(right["effective_from"], field="effective_from")
            if left_end is None or left_end > right_start:
                left_start = parse_timestamp(
                    left["effective_from"], field="effective_from"
                )
                right_end = optional_timestamp(
                    right.get("effective_to"), field="effective_to"
                )
                exact_revision_interval = (
                    left_start == right_start and left_end == right_end
                )
                if exact_revision_interval:
                    left_available = parse_timestamp(
                        left["available_at"], field="available_at"
                    )
                    right_available = parse_timestamp(
                        right["available_at"], field="available_at"
                    )
                    if left_available == right_available:
                        errors.append(
                            {
                                "code": "AMBIGUOUS_MEMBERSHIP_REVISION",
                                "key": str(key),
                            }
                        )
                    continue
                errors.append(
                    {"code": "OVERLAPPING_MEMBERSHIP_INTERVAL", "key": str(key)}
                )
    return errors


def listing_reference_errors(
    rows: list[Mapping[str, Any]],
    identity_rows: list[Mapping[str, Any]],
    *,
    code: str,
) -> list[dict[str, str]]:
    """Reject relevant source rows whose permanent listing identity is unresolved."""

    known_listing_ids = {
        str(row.get("listing_id", "")).strip() for row in identity_rows
    }
    return [
        {
            "code": code,
            "record": str(row.get("source_record_id", "")),
            "listing_id": str(row.get("listing_id", "")),
        }
        for row in rows
        if str(row.get("listing_id", "")).strip() not in known_listing_ids
    ]


def point_in_time_errors(
    panel_rows: list[Mapping[str, Any]],
    observations: list[Mapping[str, Any]],
    identities: list[Mapping[str, Any]],
    memberships: list[Mapping[str, Any]],
    actions: list[Mapping[str, Any]],
    sessions: list[Mapping[str, Any]],
) -> list[dict[str, str]]:
    observations_by_id = {
        str(row.get("source_record_id", "")): row for row in observations
    }
    identities_by_id = {
        str(row.get("source_record_id", "")): row for row in identities
    }
    memberships_by_id = {
        str(row.get("source_record_id", "")): row for row in memberships
    }
    actions_by_id = {str(row.get("source_record_id", "")): row for row in actions}
    errors: list[dict[str, str]] = []
    # Later corrections may legitimately exist in the retained snapshot.  Only
    # the selected row lineage below must have been available by the historical
    # cutoff; retaining a future revision is not itself leakage.
    for panel in panel_rows:
        cutoff = parse_timestamp(panel["cutoff_at"], field="cutoff_at")
        effective = parse_timestamp(panel["open_at"], field="open_at")
        for lineage_field, records, requires_effective in (
            ("identity_record_id", identities_by_id, True),
            ("membership_record_id", memberships_by_id, True),
            ("observation_record_id", observations_by_id, False),
        ):
            record_id = str(panel.get(lineage_field, ""))
            if not record_id:
                continue
            record = records.get(record_id)
            if record is None:
                errors.append(
                    {"code": "BROKEN_POINT_IN_TIME_LINEAGE", "record": record_id}
                )
                continue
            if parse_timestamp(record["available_at"], field="available_at") > cutoff:
                errors.append({"code": "FUTURE_RECORD_JOINED", "record": record_id})
            if requires_effective and not interval_contains(record, effective):
                errors.append({"code": "INEFFECTIVE_RECORD_JOINED", "record": record_id})
            if lineage_field == "observation_record_id" and str(
                record.get("currency", "")
            ) != str(panel.get("currency", "")):
                errors.append({"code": "OBSERVATION_CURRENCY_MISMATCH", "record": record_id})
        for action_record_id in filter(
            None, str(panel.get("action_record_ids", "")).split(";")
        ):
            action = actions_by_id.get(action_record_id)
            if action is None:
                errors.append(
                    {"code": "BROKEN_ACTION_LINEAGE", "record": action_record_id}
                )
            elif parse_timestamp(action["available_at"], field="available_at") > cutoff:
                errors.append(
                    {"code": "FUTURE_ACTION_JOINED", "record": action_record_id}
                )
    return errors


def action_release_errors(
    action_rows: list[Mapping[str, Any]],
    identity_rows: list[Mapping[str, Any]],
    session_rows: list[Mapping[str, Any]],
    universe_rows: list[Mapping[str, Any]],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    exchange_by_listing = {
        str(row["listing_id"]): str(row["exchange_id"]) for row in identity_rows
    }
    cutoff_by_exchange_date = {
        (str(row["exchange_id"]), str(row["session_date"])): row.get("cutoff_at")
        for row in session_rows
        if str(row.get("session_state", "")).upper() in {"REGULAR", "EARLY_CLOSE"}
    }
    session_range_by_exchange: dict[str, tuple[str, str]] = {}
    for session in session_rows:
        if str(session.get("session_state", "")).upper() not in {
            "REGULAR",
            "EARLY_CLOSE",
        }:
            continue
        exchange_id = str(session["exchange_id"])
        session_date = str(session["session_date"])
        prior = session_range_by_exchange.get(exchange_id)
        session_range_by_exchange[exchange_id] = (
            min(prior[0], session_date) if prior else session_date,
            max(prior[1], session_date) if prior else session_date,
        )
    actions_by_listing: dict[str, list[Mapping[str, Any]]] = {}
    actions_by_id: dict[str, list[Mapping[str, Any]]] = {}
    for action in action_rows:
        actions_by_listing.setdefault(str(action["listing_id"]), []).append(action)
        actions_by_id.setdefault(str(action["action_id"]), []).append(action)
    for action_id, history in actions_by_id.items():
        for action in history:
            if str(action.get("action_status", "")).upper() not in {
                "ACTIVE",
                "CONFIRMED",
            }:
                continue
            listing_id = str(action["listing_id"])
            ex_date = str(action["ex_date"])
            exchange_id = exchange_by_listing.get(listing_id, "")
            cutoff = cutoff_by_exchange_date.get((exchange_id, ex_date))
            if cutoff is None:
                date_range = session_range_by_exchange.get(exchange_id)
                if date_range is not None and (
                    ex_date < date_range[0] or ex_date > date_range[1]
                ):
                    # Complete revision histories are retained. Revisions whose
                    # effective date is outside this bounded request are valid
                    # source history, not missing-session errors.
                    continue
                errors.append(
                    {
                        "code": "ACTION_WITHOUT_EFFECTIVE_SESSION",
                        "action_id": action_id,
                    }
                )
                continue
            cutoff_time = parse_timestamp(cutoff, field="cutoff_at")
            available = parse_timestamp(action["available_at"], field="available_at")
            if available <= cutoff_time:
                continue
            # A later retained correction must not invalidate the state that
            # was actually knowable at the historical cutoff. It is an error
            # only when the action had no earlier revision available then.
            earlier_known = any(
                parse_timestamp(revision["available_at"], field="available_at")
                <= cutoff_time
                for revision in history
            )
            if not earlier_known:
                errors.append(
                    {
                        "code": "ACTION_NOT_AVAILABLE_BY_EFFECTIVE_CUTOFF",
                        "action_id": action_id,
                    }
                )
    for row in universe_rows:
        if not (
            _bool(row.get("candidate"))
            and str(row.get("lifecycle_state", "")).upper() == "DELISTED"
        ):
            continue
        listing_id = str(row.get("listing_id", ""))
        session_date = str(row.get("session_date", ""))
        cutoff = parse_timestamp(row["cutoff_at"], field="cutoff_at")
        known_by_id: dict[str, list[Mapping[str, Any]]] = {}
        for action in actions_by_listing.get(listing_id, []):
            if parse_timestamp(action["available_at"], field="available_at") <= cutoff:
                known_by_id.setdefault(str(action["action_id"]), []).append(action)
        selected: list[Mapping[str, Any]] = []
        for history in known_by_id.values():
            latest_at = max(
                parse_timestamp(action["available_at"], field="available_at")
                for action in history
            )
            finalists = [
                action
                for action in history
                if parse_timestamp(action["available_at"], field="available_at")
                == latest_at
            ]
            if len(finalists) == 1:
                selected.append(finalists[0])
        terminals = [
            action
            for action in selected
            if str(action.get("action_status", "")).upper() in {"ACTIVE", "CONFIRMED"}
            and str(action.get("action_type", "")).upper() == "TERMINAL_DELISTING"
            and str(action.get("ex_date", "")) == session_date
            and _optional_decimal(action.get("terminal_consideration")) is not None
        ]
        if len(terminals) != 1:
            errors.append(
                {
                    "code": (
                        "MISSING_TERMINAL_OUTCOME"
                        if not terminals
                        else "MULTIPLE_TERMINAL_OUTCOMES"
                    ),
                    "key": f"{listing_id}:{session_date}",
                }
            )
    return errors


def panel_errors(
    rows: list[Mapping[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    keys: set[tuple[str, str]] = set()
    key_errors: list[dict[str, str]] = []
    missing_errors: list[dict[str, str]] = []
    lineage_errors: list[dict[str, str]] = []
    for row in rows:
        key = (str(row.get("session_date", "")), str(row.get("security_id", "")))
        if key in keys:
            key_errors.append({"code": "DUPLICATE_PANEL_KEY", "key": str(key)})
        keys.add(key)
        if tuple(row) != PANEL_COLUMNS:
            key_errors.append({"code": "PANEL_SCHEMA_OR_ORDER_MISMATCH", "key": str(key)})
        missing_ohlcv = any(
            row.get(field) is None or str(row.get(field, "")).strip() == ""
            for field in ("open", "high", "low", "close", "volume")
        )
        if missing_ohlcv and (
            not str(row.get("value_state", "")).strip()
            or not str(row.get("missing_reason", "")).strip()
        ):
            missing_errors.append({"code": "UNTYPED_MISSING_VALUE", "key": str(key)})
        permitted_absence_states = {
            "TERMINAL_NO_BAR",
            "HALTED_NO_BAR",
            "SUSPENDED_NO_BAR",
        }
        if missing_ohlcv and str(row.get("value_state", "")) not in permitted_absence_states:
            missing_errors.append(
                {"code": "NONTERMINAL_OBSERVATION_MISSING", "key": str(key)}
            )
        if not missing_ohlcv and str(row.get("value_state", "")) != "PRESENT":
            missing_errors.append({"code": "PRESENT_VALUES_TYPED_ABSENT", "key": str(key)})
        if str(row.get("quality_state", "")).upper() != "PASSED":
            missing_errors.append({"code": "PANEL_QUALITY_NOT_PASSED", "key": str(key)})
        if not str(row.get("identity_record_id", "")).strip():
            lineage_errors.append({"code": "MISSING_IDENTITY_LINEAGE", "key": str(key)})
        if _bool(row.get("eligible")) and not str(
            row.get("membership_record_id", "")
        ).strip():
            lineage_errors.append(
                {"code": "MISSING_MEMBERSHIP_LINEAGE", "key": str(key)}
            )
        if not missing_ohlcv and not str(
            row.get("observation_record_id", "")
        ).strip():
            lineage_errors.append(
                {"code": "MISSING_OBSERVATION_LINEAGE", "key": str(key)}
            )
    return key_errors, missing_errors, lineage_errors


def return_component_errors(
    rows: list[Mapping[str, Any]],
    panel_rows: list[Mapping[str, Any]] | None = None,
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    tolerance = Decimal("0.000000000001")
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = f"{row.get('session_date')}:{row.get('security_id')}"
        tuple_key = (str(row.get("session_date", "")), str(row.get("security_id", "")))
        if tuple_key in seen:
            errors.append({"code": "DUPLICATE_RETURN_KEY", "key": key})
        seen.add(tuple_key)
        if str(row.get("return_quality_state", "")).upper() != "PASSED":
            errors.append({"code": "RETURN_ROW_QUARANTINED", "key": key})
            continue
        price = _optional_decimal(row.get("price_return_1d"))
        distribution = _optional_decimal(row.get("distribution_return_1d"))
        terminal = _optional_decimal(row.get("terminal_return"))
        total = _optional_decimal(row.get("total_return_1d"))
        expected = (
            terminal
            if terminal is not None
            else (
                price + distribution
                if price is not None and distribution is not None
                else None
            )
        )
        if expected is not None and (
            total is None or abs(total - expected) > tolerance
        ):
            errors.append({"code": "RETURN_COMPONENT_MISMATCH", "key": key})
        if total is None and not str(row.get("return_missing_reason", "")).strip():
            errors.append({"code": "UNTYPED_RETURN_MISSINGNESS", "key": key})
        if terminal is not None and str(row.get("continuity_state", "")) != "BREAK":
            errors.append({"code": "TERMINAL_CONTINUITY_NOT_BROKEN", "key": key})
    if panel_rows is not None:
        panel_keys = {
            (str(row.get("session_date", "")), str(row.get("security_id", "")))
            for row in panel_rows
        }
        for missing in sorted(panel_keys - seen):
            errors.append({"code": "MISSING_RETURN_ROW", "key": str(missing)})
        for extra in sorted(seen - panel_keys):
            errors.append({"code": "ORPHAN_RETURN_ROW", "key": str(extra)})
    return errors


def _bound_rows_fingerprint(
    columns: tuple[str, ...],
    rows: list[Mapping[str, Any]],
    sort_keys: tuple[str, ...],
) -> str:
    """Fingerprint the exact rows supplied to admission under a frozen schema."""

    expected = set(columns)
    for row_number, row in enumerate(rows, 1):
        if set(row) != expected:
            missing = sorted(expected - set(row))
            unexpected = sorted(set(row) - expected)
            raise ValueError(
                f"row {row_number} schema mismatch; missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )
    ordered = sorted(
        rows,
        key=lambda row: tuple(str(row.get(key, "")) for key in sort_keys),
    )
    return logical_rows_fingerprint(
        columns,
        (tuple(row[column] for column in columns) for row in ordered),
    ).sha256


def validate_daily_release(
    *,
    evidence: AdmissionEvidence,
    identity_rows: list[Mapping[str, Any]],
    session_rows: list[Mapping[str, Any]],
    observation_rows: list[Mapping[str, Any]],
    action_rows: list[Mapping[str, Any]],
    membership_rows: list[Mapping[str, Any]],
    universe_rows: list[Mapping[str, Any]],
    panel_rows: list[Mapping[str, Any]],
    return_rows: list[Mapping[str, Any]],
) -> ValidationReport:
    binding_errors: list[dict[str, str]] = []
    computed_fingerprints: dict[str, str] = {}
    computed_scoped_source_fingerprints: dict[str, str] = {}
    try:
        computed_fingerprints = {
            "universe": _bound_rows_fingerprint(
                UNIVERSE_COLUMNS,
                universe_rows,
                ("session_date", "exchange_id", "security_id"),
            ),
            "observable_panel": _bound_rows_fingerprint(
                PANEL_COLUMNS,
                panel_rows,
                ("session_date", "security_id"),
            ),
            "return_consistent_view": _bound_rows_fingerprint(
                RETURN_COLUMNS,
                return_rows,
                ("session_date", "security_id"),
            ),
        }
        source_rows = {
            "identity_lifecycle": identity_rows,
            "exchange_sessions": session_rows,
            "daily_observations": observation_rows,
            "corporate_actions": action_rows,
            "universe_membership": membership_rows,
        }
        computed_scoped_source_fingerprints = {
            logical_name: _bound_rows_fingerprint(
                tuple(REQUIRED_COLUMN_TYPES[logical_name]),
                source_rows[logical_name],
                REQUIRED_SORT_KEYS[logical_name],
            )
            for logical_name in sorted(source_rows)
        }
    except (KeyError, TypeError, ValueError) as exc:
        binding_errors.append(
            {"code": "ADMISSION_ROW_BINDING_FAILED", "detail": str(exc)}
        )
    (
        source_verified,
        required_schema_verified,
        lineage_complete,
        outcome_firewall_passed,
        deterministic_replay_passed,
        source_detail,
    ) = _evidence_checks(
        evidence, computed_fingerprints, computed_scoped_source_fingerprints
    )
    panel_key_errors, missing_errors, lineage_row_errors = panel_errors(panel_rows)
    checks = [
        _boolean_result("AUTHORISED_MDM_SOURCE", source_verified, source_detail),
        _boolean_result(
            "SNAPSHOT_INTEGRITY",
            source_verified,
            "Manifest, hashes, row counts, schemas, and logical rows verified",
        ),
        _boolean_result(
            "REQUIRED_SCHEMA",
            required_schema_verified,
            "Every exact Mandatory source field and physical type resolved",
        ),
        _result(
            "STABLE_IDENTITY",
            identity_interval_errors(identity_rows),
            "Stable identity, ticker history, and non-overlap",
        ),
        _result(
            "TRADING_CALENDAR",
            calendar_errors(
                session_rows,
                calendar_policy_version=str(
                    evidence.lineage_manifest.get("policy_versions", {}).get(
                        "calendar", ""
                    )
                ),
            ),
            "Session, timezone, DST, early-close, and cutoff integrity",
        ),
        _result(
            "DAILY_OBSERVATIONS",
            observation_value_errors(observation_rows)
            + observation_key_errors(observation_rows, session_rows, identity_rows)
            + listing_reference_errors(
                observation_rows,
                identity_rows,
                code="OBSERVATION_LISTING_IDENTITY_UNRESOLVED",
            ),
            "Raw unadjusted OHLCV and exact trading-session keys",
        ),
        _result(
            "POINT_IN_TIME_AVAILABILITY",
            point_in_time_errors(
                panel_rows,
                observation_rows,
                identity_rows,
                membership_rows,
                action_rows,
                session_rows,
            ),
            "Only effective records available by the row cutoff",
        ),
        _result(
            "CORPORATE_ACTIONS",
            corporate_action_errors(action_rows)
            + listing_reference_errors(
                action_rows,
                identity_rows,
                code="ACTION_LISTING_IDENTITY_UNRESOLVED",
            )
            + action_release_errors(
                action_rows, identity_rows, session_rows, universe_rows
            )
            + return_component_errors(return_rows, panel_rows),
            "Action clocks, revisions, distributions, splits, and terminal returns",
        ),
        _result(
            "HISTORICAL_UNIVERSE",
            membership_errors(membership_rows)
            + listing_reference_errors(
                membership_rows,
                identity_rows,
                code="UNIVERSE_LISTING_IDENTITY_UNRESOLVED",
            )
            + universe_errors(universe_rows, identity_rows, session_rows),
            "Survivor-complete population and explicit eligibility exclusions",
        ),
        _result(
            "FEATURE_READY_KEYS",
            panel_key_errors,
            "Unique allowlisted security-session observable rows",
        ),
        _result(
            "TYPED_MISSINGNESS",
            missing_errors,
            "Every absent value is typed and nonterminal gaps fail closed",
        ),
        _boolean_result(
            "OUTCOME_FIREWALL",
            outcome_firewall_passed,
            "No outcome, target, signal, strategy, or future field",
        ),
        _result(
            "LINEAGE",
            ([] if lineage_complete else [{"code": "LINEAGE_MANIFEST_INCOMPLETE"}])
            + lineage_row_errors
            + binding_errors,
            "Source-to-view dataset, field, and row references are complete",
        ),
        _boolean_result(
            "DETERMINISTIC_REPLAY",
            deterministic_replay_passed,
            "Canonical output replay equality",
        ),
    ]
    blockers = sum(
        1
        for check in checks
        if check.code in HARD_FAILURE_CODES and check.status != "PASS"
    )
    if blockers:
        state = "INADMISSIBLE"
    elif evidence.snapshot.production_use_permitted:
        state = "ADMISSIBLE"
    else:
        state = "TEST_ADMISSIBLE_NON_PRODUCTION"
    return ValidationReport(
        state=state,
        checks=tuple(checks),
        hard_blocker_count=blockers,
    )


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    return Decimal(str(value))


def _optional_text(value: Any) -> str:
    return "" if value is None or str(value).strip() == "" else str(value)
