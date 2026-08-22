"""Deterministic assembly of the outcome-free daily observable panel."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .temporal import parse_timestamp


class AssemblyError(ValueError):
    """Raised when an output cannot be assembled without an arbitrary choice."""


@dataclass(frozen=True)
class JoinAudit:
    left_rows: int
    matched_rows: int
    unmatched_rows: int
    multiple_match_rows: int
    rejected_not_available: int
    terminal_missing_bar_rows: int

    def as_dict(self) -> dict[str, int]:
        return {
            "left_rows": self.left_rows,
            "matched_rows": self.matched_rows,
            "unmatched_rows": self.unmatched_rows,
            "multiple_match_rows": self.multiple_match_rows,
            "rejected_not_available": self.rejected_not_available,
            "terminal_missing_bar_rows": self.terminal_missing_bar_rows,
        }


PANEL_COLUMNS = (
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
    "universe_id",
    "candidate",
    "eligible",
    "exclusion_reason",
    "action_state",
    "action_record_ids",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "price_basis",
    "observation_state",
    "value_state",
    "missing_reason",
    "quality_state",
    "identity_record_id",
    "membership_record_id",
    "observation_record_id",
)


FORBIDDEN_FIELD_ROLES = {
    "OUTCOME",
    "TARGET",
    "LABEL",
    "SIGNAL",
    "STRATEGY",
    "FUTURE",
}


def enforce_outcome_firewall(
    requested_fields: Sequence[Mapping[str, str]],
    field_roles: Mapping[str, str],
) -> None:
    """Reject requested output identities governed as outcomes or unknown."""

    forbidden_tokens = (
        "forward_",
        "future_",
        "target",
        "label",
        "signal",
        "strategy",
        "outcome",
    )
    for request in requested_fields:
        field_id = str(request.get("field_id", "")).strip()
        role = str(field_roles.get(field_id, "UNKNOWN")).upper()
        lowered = field_id.lower()
        if (
            role in FORBIDDEN_FIELD_ROLES
            or role == "UNKNOWN"
            or any(token in lowered for token in forbidden_tokens)
        ):
            raise AssemblyError(f"OUTCOME_FIELD_FORBIDDEN:{field_id}")


def _actions_for_panel_row(
    action_rows: Iterable[Mapping[str, Any]],
    *,
    listing_id: str,
    session_date: str,
    cutoff_at: Any,
) -> tuple[str, str]:
    # Future revisions are not counted or exposed.  Even a typed
    # "not-yet-available" marker would reveal that a future action exists.
    known = [
        row
        for row in action_rows
        if str(row.get("listing_id", "")) == listing_id
        and parse_timestamp(row["available_at"], field="available_at")
        <= parse_timestamp(cutoff_at, field="cutoff_at")
    ]
    latest_by_action: dict[str, Mapping[str, Any]] = {}
    for row in sorted(
        known,
        key=lambda item: parse_timestamp(item["available_at"], field="available_at"),
    ):
        latest_by_action[str(row["action_id"])] = row
    visible = [
        row
        for row in latest_by_action.values()
        if str(row.get("ex_date", "")) == session_date
        if str(row.get("action_status", "")).upper() not in {"CANCELLED", "REVERSED"}
    ]
    if not visible:
        return "NONE", ""
    return (
        ";".join(sorted({str(row["action_type"]).upper() for row in visible})),
        ";".join(sorted(str(row["source_record_id"]) for row in visible)),
    )


def assemble_security_day_panel(
    universe_rows: list[Mapping[str, Any]],
    observation_rows: list[Mapping[str, Any]],
    action_rows: Iterable[Mapping[str, Any]] = (),
) -> tuple[list[dict[str, Any]], JoinAudit]:
    """Assemble candidate rows without dropping missing or terminal sessions."""

    by_key: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for observation in observation_rows:
        key = (str(observation["listing_id"]), str(observation["session_date"]))
        by_key[key].append(observation)

    panel: list[dict[str, Any]] = []
    matched = 0
    unmatched = 0
    multiple = 0
    rejected_future = 0
    terminal_missing = 0
    candidates = [row for row in universe_rows if _bool(row.get("candidate"))]
    material_actions = tuple(action_rows)
    for universe in sorted(
        candidates,
        key=lambda row: (
            str(row["session_date"]),
            str(row["exchange_id"]),
            str(row["security_id"]),
        ),
    ):
        key = (str(universe["listing_id"]), str(universe["session_date"]))
        matches = by_key.get(key, [])
        cutoff = parse_timestamp(universe["cutoff_at"], field="cutoff_at")
        known_matches = [
            observation
            for observation in matches
            if parse_timestamp(observation["available_at"], field="available_at")
            <= cutoff
        ]
        rejected_future += len(matches) - len(known_matches)
        observation: Mapping[str, Any] | None = None
        if known_matches:
            latest_available = max(
                parse_timestamp(row["available_at"], field="available_at")
                for row in known_matches
            )
            finalists = [
                row
                for row in known_matches
                if parse_timestamp(row["available_at"], field="available_at")
                == latest_available
            ]
            if len(finalists) != 1:
                multiple += 1
                raise AssemblyError(
                    f"AMBIGUOUS_DAILY_OBSERVATION_REVISION:{key[0]}:{key[1]}"
                )
            observation = finalists[0]

        row = {column: universe.get(column, "") for column in PANEL_COLUMNS}
        action_state, action_record_ids = _actions_for_panel_row(
            material_actions,
            listing_id=key[0],
            session_date=key[1],
            cutoff_at=universe["cutoff_at"],
        )
        row["action_state"] = action_state
        row["action_record_ids"] = action_record_ids
        if observation is None:
            unmatched += 1
            lifecycle = str(universe.get("lifecycle_state", "")).upper()
            terminal = lifecycle == "DELISTED"
            governed_absence = lifecycle in {"HALTED", "SUSPENDED"}
            row.update(
                {
                    "open": None,
                    "high": None,
                    "low": None,
                    "close": None,
                    "volume": None,
                    "price_basis": "RAW_UNADJUSTED",
                    "observation_state": "ABSENT",
                    "value_state": (
                        "TERMINAL_NO_BAR"
                        if terminal
                        else (
                            f"{lifecycle}_NO_BAR"
                            if governed_absence
                            else "SOURCE_VALUE_ABSENT"
                        )
                    ),
                    "missing_reason": (
                        "TERMINAL_SETTLEMENT_ONLY"
                        if terminal
                        else (
                            f"LIFECYCLE_{lifecycle}"
                            if governed_absence
                            else "NO_DAILY_OBSERVATION"
                        )
                    ),
                    "quality_state": (
                        "PASSED" if terminal or governed_absence else "SUSPECT"
                    ),
                    "observation_record_id": "",
                }
            )
            terminal_missing += int(terminal)
        else:
            matched += 1
            row.update(
                {
                    "open": observation.get("open"),
                    "high": observation.get("high"),
                    "low": observation.get("low"),
                    "close": observation.get("close"),
                    "volume": observation.get("volume"),
                    "price_basis": str(observation["price_basis"]),
                    "observation_state": str(observation["observation_state"]),
                    "value_state": str(observation["value_state"]),
                    "missing_reason": "",
                    "quality_state": str(observation["quality_state"]),
                    "observation_record_id": str(observation["source_record_id"]),
                }
            )
        panel.append({column: row.get(column) for column in PANEL_COLUMNS})

    audit = JoinAudit(
        left_rows=len(candidates),
        matched_rows=matched,
        unmatched_rows=unmatched,
        multiple_match_rows=multiple,
        rejected_not_available=rejected_future,
        terminal_missing_bar_rows=terminal_missing,
    )
    return panel, audit


def observation_key_errors(
    observations: Iterable[Mapping[str, Any]],
    sessions: Iterable[Mapping[str, Any]],
    identity_rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, str]]:
    valid_sessions = {
        (str(row["exchange_id"]), str(row["session_date"]))
        for row in sessions
        if str(row.get("session_state", "")).upper()
        in {"REGULAR", "EARLY_CLOSE"}
    }
    listing_exchanges: dict[str, set[str]] = defaultdict(set)
    for identity in identity_rows:
        listing_exchanges[str(identity["listing_id"])].add(
            str(identity["exchange_id"])
        )

    revisions: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    errors: list[dict[str, str]] = []
    for row in observations:
        listing_id = str(row.get("listing_id", ""))
        session_date = str(row.get("session_date", ""))
        key = (listing_id, session_date)
        revisions[key].append(row)
        exchanges = listing_exchanges.get(listing_id, set())
        if len(exchanges) != 1 or (next(iter(exchanges)), session_date) not in valid_sessions:
            errors.append(
                {
                    "code": "OBSERVATION_ON_NON_SESSION",
                    "listing_id": listing_id,
                    "session_date": session_date,
                }
            )
    for key, history in revisions.items():
        available_times = [
            parse_timestamp(row["available_at"], field="available_at")
            for row in history
        ]
        if len(available_times) != len(set(available_times)):
            errors.append(
                {
                    "code": "AMBIGUOUS_OBSERVATION_REVISION",
                    "listing_id": key[0],
                    "session_date": key[1],
                }
            )
    return errors


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
