"""Point-in-time primitives for the Project EDGE daily data slice.

The functions in this module are deliberately small and deterministic.  They
operate on ordinary mappings so the same rules can be exercised without a
database-specific temporal engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping, Sequence


SUPPORTED_LIFECYCLE_STATES = frozenset(
    {"ACTIVE", "HALTED", "SUSPENDED", "DELISTED"}
)


UTC = timezone.utc


class TemporalIntegrityError(ValueError):
    """Raised when a point-in-time decision is ambiguous or unsafe."""


@dataclass(frozen=True)
class AsOfDecision:
    status: str
    record: Mapping[str, Any] | None
    eligible_count: int
    rejected_not_available: int
    rejected_not_effective: int
    detail: str = ""


def parse_timestamp(value: Any, *, field: str = "timestamp") -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            raise TemporalIntegrityError(f"{field} is required")
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise TemporalIntegrityError(f"{field} is not ISO-8601: {value!r}") from exc
    if parsed.tzinfo is None:
        raise TemporalIntegrityError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


def parse_date(value: Any, *, field: str = "date") -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        raise TemporalIntegrityError(f"{field} is required")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise TemporalIntegrityError(f"{field} is not ISO yyyy-mm-dd: {value!r}") from exc


def optional_timestamp(value: Any, *, field: str) -> datetime | None:
    if value is None or str(value).strip() == "":
        return None
    return parse_timestamp(value, field=field)


def interval_contains(
    record: Mapping[str, Any],
    moment: datetime,
    *,
    start_field: str = "effective_from",
    end_field: str = "effective_to",
) -> bool:
    start = parse_timestamp(record[start_field], field=start_field)
    end = optional_timestamp(record.get(end_field), field=end_field)
    return start <= moment and (end is None or moment < end)


def select_point_in_time(
    records: Iterable[Mapping[str, Any]],
    *,
    effective_at: datetime,
    cutoff: datetime,
    start_field: str = "effective_from",
    end_field: str = "effective_to",
    available_field: str = "available_at",
    revision_field: str | None = "revision_sequence",
) -> AsOfDecision:
    """Select the latest eligible record and fail on an unresolved tie.

    A record must be effective at ``effective_at`` and available no later than
    ``cutoff``.  The latest availability wins.  A numeric revision sequence is
    used only to resolve revisions sharing that availability timestamp.  Any
    remaining tie is a scientific ambiguity, not an arbitrary sort choice.
    """

    effective: list[Mapping[str, Any]] = []
    not_effective = 0
    not_available = 0
    for record in records:
        if not interval_contains(record, effective_at, start_field=start_field, end_field=end_field):
            not_effective += 1
            continue
        raw_available = record.get(available_field)
        if raw_available is None or str(raw_available).strip() == "":
            return AsOfDecision(
                status="UNKNOWN_AVAILABILITY",
                record=None,
                eligible_count=0,
                rejected_not_available=not_available,
                rejected_not_effective=not_effective,
                detail=f"{available_field} is missing",
            )
        available = parse_timestamp(raw_available, field=available_field)
        if available > cutoff:
            not_available += 1
            continue
        effective.append(record)

    if not effective:
        status = "NOT_YET_AVAILABLE" if not_available else "NO_EFFECTIVE_RECORD"
        return AsOfDecision(status, None, 0, not_available, not_effective)

    latest_available = max(parse_timestamp(row[available_field], field=available_field) for row in effective)
    finalists = [
        row
        for row in effective
        if parse_timestamp(row[available_field], field=available_field) == latest_available
    ]
    if revision_field and len(finalists) > 1 and any(str(row.get(revision_field, "")).strip() for row in finalists):
        try:
            latest_revision = max(int(str(row.get(revision_field, "0") or "0")) for row in finalists)
        except ValueError as exc:
            raise TemporalIntegrityError(f"{revision_field} must be an integer") from exc
        finalists = [
            row
            for row in finalists
            if int(str(row.get(revision_field, "0") or "0")) == latest_revision
        ]

    if len(finalists) != 1:
        return AsOfDecision(
            status="MULTIPLE_ELIGIBLE_MATCHES",
            record=None,
            eligible_count=len(finalists),
            rejected_not_available=not_available,
            rejected_not_effective=not_effective,
            detail="No deterministic scientific precedence rule resolves the eligible records",
        )
    return AsOfDecision("MATCHED", finalists[0], 1, not_available, not_effective)


def resolve_ticker(
    identity_rows: Iterable[Mapping[str, Any]],
    *,
    ticker: str,
    exchange_id: str,
    effective_at: datetime,
    cutoff: datetime,
) -> AsOfDecision:
    wanted_ticker = ticker.strip().upper()
    wanted_exchange = exchange_id.strip().upper()
    candidates = [
        row
        for row in identity_rows
        if str(row.get("ticker", "")).strip().upper() == wanted_ticker
        and str(row.get("exchange_id", "")).strip().upper() == wanted_exchange
    ]
    return select_point_in_time(candidates, effective_at=effective_at, cutoff=cutoff)


def identity_interval_errors(identity_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    seen_records: set[str] = set()
    identities_by_listing: dict[str, list[Mapping[str, Any]]] = {}

    def overlapping(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
        a_start = parse_timestamp(a["effective_from"], field="effective_from")
        b_start = parse_timestamp(b["effective_from"], field="effective_from")
        a_end = optional_timestamp(a.get("effective_to"), field="effective_to") or datetime.max.replace(tzinfo=UTC)
        b_end = optional_timestamp(b.get("effective_to"), field="effective_to") or datetime.max.replace(tzinfo=UTC)
        return a_start < b_end and b_start < a_end

    for index, left in enumerate(identity_rows):
        identities_by_listing.setdefault(str(left.get("listing_id", "")), []).append(
            left
        )
        record_id = str(left.get("source_record_id", "")).strip()
        if not record_id or record_id in seen_records:
            errors.append({"code": "DUPLICATE_OR_MISSING_IDENTITY_RECORD", "record": record_id})
        seen_records.add(record_id)
        for required in (
            "security_id",
            "issuer_id",
            "listing_id",
            "exchange_id",
            "security_type",
            "currency",
        ):
            if not str(left.get(required, "")).strip():
                errors.append(
                    {"code": "MISSING_IDENTITY_FIELD", "record": record_id, "field": required}
                )
        if str(left.get("quality_state", "PASSED")).upper() != "PASSED":
            errors.append({"code": "IDENTITY_QUALITY_NOT_PASSED", "record": record_id})
        lifecycle_state = str(left.get("lifecycle_state", "")).strip().upper()
        if lifecycle_state not in SUPPORTED_LIFECYCLE_STATES:
            errors.append(
                {
                    "code": "UNKNOWN_LIFECYCLE_STATE",
                    "record": record_id,
                    "state": lifecycle_state,
                }
            )
        try:
            left_start = parse_timestamp(left.get("effective_from"), field="effective_from")
            left_end = optional_timestamp(left.get("effective_to"), field="effective_to")
            parse_timestamp(left.get("available_at"), field="available_at")
            published_raw = left.get("published_at")
            if published_raw is not None and str(published_raw).strip():
                published = parse_timestamp(published_raw, field="published_at")
                available = parse_timestamp(left.get("available_at"), field="available_at")
                if published > available:
                    errors.append(
                        {"code": "IDENTITY_PUBLISHED_AFTER_AVAILABLE", "record": record_id}
                    )
            if left_end is not None and left_end <= left_start:
                errors.append({"code": "INVALID_IDENTITY_INTERVAL", "record": str(left.get("source_record_id", ""))})
        except TemporalIntegrityError as exc:
            errors.append({"code": "INVALID_IDENTITY_TIME", "record": str(left.get("source_record_id", "")), "detail": str(exc)})
            continue
        for right in identity_rows[index + 1 :]:
            same_listing = str(left.get("listing_id")) == str(right.get("listing_id"))
            same_symbol = (
                str(left.get("ticker", "")).upper() == str(right.get("ticker", "")).upper()
                and str(left.get("exchange_id", "")).upper()
                == str(right.get("exchange_id", "")).upper()
            )
            if not (same_listing or same_symbol):
                continue
            try:
                is_overlap = overlapping(left, right)
            except TemporalIntegrityError:
                continue
            if not is_overlap:
                continue
            same_revision_interval = (
                same_listing
                and str(left.get("security_id")) == str(right.get("security_id"))
                and str(left.get("exchange_id")) == str(right.get("exchange_id"))
                and parse_timestamp(left["effective_from"], field="effective_from")
                == parse_timestamp(right["effective_from"], field="effective_from")
                and optional_timestamp(left.get("effective_to"), field="effective_to")
                == optional_timestamp(right.get("effective_to"), field="effective_to")
            )
            if same_revision_interval:
                left_available = parse_timestamp(
                    left["available_at"], field="available_at"
                )
                right_available = parse_timestamp(
                    right["available_at"], field="available_at"
                )
                if left_available == right_available:
                    errors.append(
                        {
                            "code": "AMBIGUOUS_IDENTITY_REVISION",
                            "left": str(left.get("source_record_id", "")),
                            "right": str(right.get("source_record_id", "")),
                        }
                    )
                continue
            if same_listing:
                code = "OVERLAPPING_LISTING_IDENTITY"
            elif str(left.get("security_id")) != str(right.get("security_id")):
                code = "AMBIGUOUS_TICKER_IDENTITY"
            else:
                code = "OVERLAPPING_TICKER_INTERVAL"
            errors.append(
                {
                    "code": code,
                    "left": str(left.get("source_record_id", "")),
                    "right": str(right.get("source_record_id", "")),
                }
            )
    for listing_id, history in identities_by_listing.items():
        security_ids = {
            str(row.get("security_id", "")).strip() for row in history
        }
        currencies = {str(row.get("currency", "")).strip() for row in history}
        if len(security_ids) != 1:
            errors.append(
                {
                    "code": "LISTING_SECURITY_ID_DRIFT",
                    "listing_id": listing_id,
                }
            )
        if len(currencies) != 1:
            errors.append(
                {
                    "code": "LISTING_CURRENCY_DRIFT",
                    "listing_id": listing_id,
                }
            )
    return errors


def _one_exchange_sessions(
    sessions: Sequence[Mapping[str, Any]], exchange_id: str | None
) -> list[Mapping[str, Any]]:
    exchanges = {str(row.get("exchange_id", row.get("exchange", ""))) for row in sessions}
    exchanges.discard("")
    if exchange_id is None:
        if len(exchanges) != 1:
            raise TemporalIntegrityError(
                "exchange_id is required when more than one calendar is present"
            )
        exchange_id = next(iter(exchanges))
    return [
        row
        for row in sessions
        if str(row.get("exchange_id", row.get("exchange", ""))) == exchange_id
    ]


def session_shift(
    sessions: Sequence[Mapping[str, Any]],
    session_date: str,
    offset: int,
    *,
    exchange_id: str | None = None,
) -> str:
    scoped = _one_exchange_sessions(sessions, exchange_id)
    ordered = sorted(
        str(row["session_date"])
        for row in scoped
        if str(row.get("session_state", "")).upper() in {"REGULAR", "EARLY_CLOSE"}
    )
    try:
        position = ordered.index(session_date)
    except ValueError as exc:
        raise TemporalIntegrityError(f"Unknown trading session: {session_date}") from exc
    target = position + offset
    if target < 0 or target >= len(ordered):
        raise TemporalIntegrityError(f"Session shift leaves available calendar: {session_date} {offset:+d}")
    return ordered[target]


def session_for_timestamp(
    sessions: Sequence[Mapping[str, Any]],
    value: Any,
    *,
    exchange_id: str | None = None,
) -> str | None:
    timestamp = parse_timestamp(value, field="timestamp")
    scoped = _one_exchange_sessions(sessions, exchange_id)
    tradable = sorted(
        (
            row
            for row in scoped
            if str(row.get("session_state", "")).upper() in {"REGULAR", "EARLY_CLOSE"}
        ),
        key=lambda row: str(row["session_date"]),
    )
    if not tradable:
        return None
    first_open = parse_timestamp(tradable[0]["open_at"], field="open_at")
    if timestamp < first_open:
        return None
    for row in tradable:
        open_at = parse_timestamp(row["open_at"], field="open_at")
        cutoff_at = parse_timestamp(row["cutoff_at"], field="cutoff_at")
        if open_at <= timestamp <= cutoff_at:
            return str(row["session_date"])
        if timestamp < open_at:
            return str(row["session_date"])
    return None
