"""Point-in-time historical population reconstruction for the daily slice."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Iterable, Mapping

from .temporal import parse_timestamp, select_point_in_time


TRADING_SESSION_STATES = frozenset({"REGULAR", "EARLY_CLOSE"})
CANDIDATE_LIFECYCLE_STATES = frozenset(
    {"ACTIVE", "HALTED", "SUSPENDED", "INACTIVE"}
)
INCLUDED_MEMBERSHIP_STATES = frozenset({"INCLUDED", "MEMBER", "ELIGIBLE"})

UNIVERSE_COLUMNS = (
    "session_date",
    "calendar_id",
    "exchange_id",
    "session_state",
    "previous_session_date",
    "next_session_date",
    "open_at",
    "close_at",
    "cutoff_at",
    "security_id",
    "issuer_id",
    "listing_id",
    "ticker",
    "security_type",
    "share_class",
    "primary_listing",
    "currency",
    "lifecycle_state",
    "candidate",
    "eligible",
    "exclusion_reason",
    "identity_record_id",
    "identity_status",
    "universe_id",
    "membership_record_id",
    "membership_status",
)


def _trading_sessions(rows: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        (
            row
            for row in rows
            if str(row.get("session_state", "")).upper() in TRADING_SESSION_STATES
        ),
        key=lambda row: (str(row["exchange_id"]), str(row["session_date"])),
    )


def _known_rows(
    rows: Iterable[Mapping[str, Any]], cutoff: datetime
) -> list[Mapping[str, Any]]:
    return [
        row
        for row in rows
        if str(row.get("available_at", "")).strip()
        and parse_timestamp(row["available_at"], field="available_at") <= cutoff
    ]


def _first_effective(history: list[Mapping[str, Any]]) -> datetime:
    return min(
        parse_timestamp(row["effective_from"], field="effective_from")
        for row in history
    )


def _last_known_identity(
    history: list[Mapping[str, Any]], cutoff: datetime
) -> Mapping[str, Any] | None:
    known = _known_rows(history, cutoff)
    if not known:
        return None
    return max(
        known,
        key=lambda row: (
            parse_timestamp(row["effective_from"], field="effective_from"),
            parse_timestamp(row["available_at"], field="available_at"),
            str(row.get("source_record_id", "")),
        ),
    )


def _is_first_delisted_session(
    selected: Mapping[str, Any], session: Mapping[str, Any]
) -> bool:
    if str(selected.get("lifecycle_state", "")).upper() != "DELISTED":
        return False
    effective = parse_timestamp(selected["effective_from"], field="effective_from")
    session_open = parse_timestamp(session["open_at"], field="open_at")
    previous_raw = session.get("previous_session_date")
    if previous_raw is None or str(previous_raw).strip() == "":
        return effective <= session_open
    return str(previous_raw) < effective.date().isoformat() <= str(session["session_date"])


def build_historical_universe(
    identity_rows: list[Mapping[str, Any]],
    session_rows: list[Mapping[str, Any]],
    membership_rows: list[Mapping[str, Any]],
    *,
    universe_id: str | None = None,
    allowed_security_types: Iterable[str] | None = None,
    allowed_currencies: Iterable[str] | None = None,
    primary_listings_only: bool = True,
) -> list[dict[str, Any]]:
    """Build one explicit assessment per stable security and trading session.

    The candidate population is derived from point-in-time identity/lifecycle
    history, never from the securities that happen to have bars. Eligibility is
    then restricted by the point-in-time governed membership record. A first
    delisted session remains visible as a typed terminal-settlement row.
    """

    identities: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    memberships: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in identity_rows:
        identities[str(row["listing_id"])].append(row)
    available_universe_ids = {str(row["universe_id"]) for row in membership_rows}
    if universe_id is None:
        if len(available_universe_ids) != 1:
            raise ValueError(
                "An exact universe_id is required when source membership contains "
                f"{sorted(available_universe_ids)!r}"
            )
        universe_id = next(iter(available_universe_ids))
    for row in membership_rows:
        if str(row["universe_id"]) != universe_id:
            continue
        memberships[str(row["listing_id"])].append(row)

    permitted_types = (
        None
        if allowed_security_types is None
        else {str(value).upper() for value in allowed_security_types}
    )
    permitted_currencies = (
        None
        if allowed_currencies is None
        else {str(value).upper() for value in allowed_currencies}
    )

    assessments: list[dict[str, Any]] = []
    for session in _trading_sessions(session_rows):
        open_at = parse_timestamp(session["open_at"], field="open_at")
        cutoff_at = parse_timestamp(session["cutoff_at"], field="cutoff_at")
        exchange_id = str(session["exchange_id"])
        for listing_id in sorted(identities):
            history = identities[listing_id]
            exchange_history = [
                row for row in history if str(row["exchange_id"]) == exchange_id
            ]
            if not exchange_history:
                continue

            identity_decision = select_point_in_time(
                exchange_history,
                effective_at=open_at,
                cutoff=cutoff_at,
                revision_field=None,
            )
            selected = identity_decision.record
            lifecycle = "IDENTITY_UNKNOWN"
            candidate = False
            eligible = False
            reason = identity_decision.status
            membership_status = "NOT_EVALUATED"
            membership_record: Mapping[str, Any] | None = None

            if open_at < _first_effective(exchange_history):
                lifecycle = "PRE_LISTING"
                reason = "PRE_LISTING"
                selected = None
            elif identity_decision.status != "MATCHED":
                selected = _last_known_identity(exchange_history, cutoff_at)
                if selected is not None:
                    lifecycle = "POST_LISTING"
                    reason = "NO_EFFECTIVE_IDENTITY"
            else:
                assert selected is not None
                lifecycle = str(selected.get("lifecycle_state", "ACTIVE")).upper()
                security_type = str(selected.get("security_type", "")).upper()
                currency = str(selected.get("currency", "")).upper()
                primary_listing = _bool(selected.get("primary_listing"))
                if lifecycle == "DELISTED":
                    if (
                        _is_first_delisted_session(selected, session)
                        and (not primary_listings_only or primary_listing)
                        and (permitted_types is None or security_type in permitted_types)
                        and (
                            permitted_currencies is None
                            or currency in permitted_currencies
                        )
                    ):
                        candidate = True
                        reason = "TERMINAL_SETTLEMENT_ONLY"
                    else:
                        reason = "POST_DELISTING"
                elif lifecycle not in CANDIDATE_LIFECYCLE_STATES:
                    reason = f"LIFECYCLE_{lifecycle or 'UNKNOWN'}"
                elif primary_listings_only and not primary_listing:
                    reason = "SECONDARY_LISTING"
                elif permitted_types is not None and security_type not in permitted_types:
                    reason = "SECURITY_TYPE_EXCLUDED"
                elif permitted_currencies is not None and currency not in permitted_currencies:
                    reason = "CURRENCY_EXCLUDED"
                else:
                    candidate = True
                    membership_decision = select_point_in_time(
                        memberships.get(listing_id, []),
                        effective_at=open_at,
                        cutoff=cutoff_at,
                        revision_field=None,
                    )
                    membership_status = membership_decision.status
                    membership_record = membership_decision.record
                    if membership_decision.status != "MATCHED":
                        reason = f"MEMBERSHIP_{membership_decision.status}"
                    else:
                        membership_state = str(
                            membership_record.get("membership_state", "")
                        ).upper()
                        if membership_state not in INCLUDED_MEMBERSHIP_STATES:
                            reason = f"MEMBERSHIP_{membership_state or 'UNKNOWN'}"
                        elif lifecycle != "ACTIVE":
                            reason = lifecycle
                        else:
                            eligible = True
                            reason = ""

            selected_values = selected or {}
            master = min(
                exchange_history,
                key=lambda row: parse_timestamp(
                    row["effective_from"], field="effective_from"
                ),
            )
            assessment = {
                    "session_date": str(session["session_date"]),
                    "calendar_id": str(session["calendar_id"]),
                    "exchange_id": exchange_id,
                    "session_state": str(session["session_state"]),
                    "previous_session_date": str(
                        session.get("previous_session_date") or ""
                    ),
                    "next_session_date": str(session.get("next_session_date") or ""),
                    "open_at": str(session["open_at"]),
                    "close_at": str(session["close_at"]),
                    "cutoff_at": str(session["cutoff_at"]),
                    "security_id": str(
                        selected_values.get("security_id", master["security_id"])
                    ),
                    "issuer_id": str(
                        selected_values.get("issuer_id", master.get("issuer_id", ""))
                    ),
                    "listing_id": str(
                        selected_values.get("listing_id", listing_id)
                    ),
                    "ticker": str(selected_values.get("ticker", "")),
                    "security_type": str(
                        selected_values.get(
                            "security_type", master.get("security_type", "")
                        )
                    ),
                    "share_class": str(
                        selected_values.get("share_class", master.get("share_class", ""))
                    ),
                    "primary_listing": selected_values.get(
                        "primary_listing", master.get("primary_listing", False)
                    ),
                    "currency": str(
                        selected_values.get("currency", master.get("currency", ""))
                    ),
                    "lifecycle_state": lifecycle,
                    "candidate": candidate,
                    "eligible": eligible,
                    "exclusion_reason": reason,
                    "identity_record_id": str(
                        selected_values.get("source_record_id", "")
                    ),
                    "identity_status": identity_decision.status,
                    "universe_id": str(
                        (membership_record or {}).get("universe_id", universe_id)
                    ),
                    "membership_record_id": str(
                        (membership_record or {}).get("source_record_id", "")
                    ),
                    "membership_status": membership_status,
                }
            assessments.append(
                {column: assessment[column] for column in UNIVERSE_COLUMNS}
            )
    return sorted(
        assessments,
        key=lambda row: (
            row["session_date"],
            row["exchange_id"],
            row["security_id"],
        ),
    )


def universe_counts(rows: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    material = list(rows)
    return {
        "assessment_rows": len(material),
        "candidate_rows": sum(_bool(row.get("candidate")) for row in material),
        "eligible_rows": sum(_bool(row.get("eligible")) for row in material),
        "candidate_ineligible_rows": sum(
            _bool(row.get("candidate")) and not _bool(row.get("eligible"))
            for row in material
        ),
        "non_candidate_rows": sum(
            not _bool(row.get("candidate")) for row in material
        ),
        "distinct_securities": len(
            {str(row["security_id"]) for row in material}
        ),
        "distinct_sessions": len(
            {str(row["session_date"]) for row in material}
        ),
    }


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
