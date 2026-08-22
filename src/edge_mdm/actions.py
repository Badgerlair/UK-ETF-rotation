"""Corporate-action validation and a separate return-consistent daily view."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any, Iterable, Mapping

from .temporal import parse_timestamp


SUPPORTED_ACTIONS = frozenset(
    {"SPLIT", "CASH_DISTRIBUTION", "TERMINAL_DELISTING"}
)
COMPLEX_ACTIONS = frozenset(
    {"MERGER", "ACQUISITION", "SPINOFF", "RIGHTS", "REORGANISATION"}
)
ACTIVE_ACTION_STATES = frozenset({"ACTIVE", "CONFIRMED"})
INACTIVE_ACTION_STATES = frozenset({"CANCELLED", "REVERSED"})

RETURN_COLUMNS = (
    "session_date",
    "security_id",
    "listing_id",
    "previous_close",
    "raw_close",
    "raw_return_1d",
    "split_multiplier",
    "split_consistent_volume",
    "price_return_1d",
    "distribution_return_1d",
    "terminal_return",
    "total_return_1d",
    "action_ids",
    "action_record_ids",
    "action_state",
    "return_quality_state",
    "return_missing_reason",
    "continuity_state",
)


class CorporateActionError(ValueError):
    """Raised for an invalid corporate-action contract."""


def decimal_value(
    value: Any, *, field: str, required: bool = True
) -> Decimal | None:
    if value is None or str(value).strip() == "":
        if required:
            raise CorporateActionError(f"{field} is required")
        return None
    try:
        parsed = Decimal(str(value))
    except InvalidOperation as exc:
        raise CorporateActionError(f"{field} is not decimal: {value!r}") from exc
    if not parsed.is_finite():
        raise CorporateActionError(f"{field} must be finite")
    return parsed


def decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    with localcontext() as context:
        context.prec = 34
        quantized = value.quantize(Decimal("0.000000000001"))
    return format(quantized, "f")


def corporate_action_errors(
    rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    seen_records: set[str] = set()
    revisions: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        source_record_id = str(row.get("source_record_id", "")).strip()
        action_id = str(row.get("action_id", "")).strip()
        action_type = str(row.get("action_type", "")).strip().upper()
        if not source_record_id or source_record_id in seen_records:
            errors.append(
                {
                    "code": "DUPLICATE_OR_MISSING_ACTION_RECORD",
                    "record": source_record_id,
                }
            )
        seen_records.add(source_record_id)
        if not action_id:
            errors.append({"code": "MISSING_ACTION_ID", "record": source_record_id})
        if not str(row.get("listing_id", "")).strip():
            errors.append({"code": "MISSING_ACTION_LISTING", "record": source_record_id})
        if str(row.get("quality_state", "")).upper() != "PASSED":
            errors.append({"code": "ACTION_QUALITY_NOT_PASSED", "record": source_record_id})
        revisions[action_id].append(row)
        try:
            announcement = parse_timestamp(
                row.get("announcement_at"), field="announcement_at"
            )
            published = parse_timestamp(row.get("published_at"), field="published_at")
            available = parse_timestamp(row.get("available_at"), field="available_at")
            effective = parse_timestamp(row.get("effective_at"), field="effective_at")
            if announcement > published or published > available:
                errors.append(
                    {
                        "code": "INVALID_ACTION_INFORMATION_CLOCKS",
                        "action_id": action_id,
                    }
                )
            if effective.date().isoformat() != str(row.get("ex_date", "")):
                errors.append(
                    {"code": "ACTION_EX_DATE_MISMATCH", "action_id": action_id}
                )
            state = str(row.get("action_status", "")).upper()
            if state not in ACTIVE_ACTION_STATES | INACTIVE_ACTION_STATES:
                errors.append(
                    {"code": "UNKNOWN_ACTION_STATUS", "action_id": action_id}
                )
            if action_type == "SPLIT":
                ratio = decimal_value(row.get("split_ratio"), field="split_ratio")
                if ratio is not None and ratio <= 0:
                    errors.append(
                        {"code": "INVALID_SPLIT_RATIO", "action_id": action_id}
                    )
            elif action_type == "CASH_DISTRIBUTION":
                amount = decimal_value(row.get("cash_amount"), field="cash_amount")
                if amount is not None and (
                    amount < 0 or not str(row.get("currency", "")).strip()
                ):
                    errors.append(
                        {
                            "code": "INVALID_CASH_DISTRIBUTION",
                            "action_id": action_id,
                        }
                    )
            elif action_type == "TERMINAL_DELISTING":
                amount = decimal_value(
                    row.get("terminal_consideration"),
                    field="terminal_consideration",
                )
                if amount is not None and (
                    amount < 0 or not str(row.get("currency", "")).strip()
                ):
                    errors.append(
                        {"code": "INVALID_TERMINAL_VALUE", "action_id": action_id}
                    )
            elif action_type not in COMPLEX_ACTIONS:
                errors.append(
                    {"code": "UNKNOWN_ACTION_TYPE", "action_id": action_id}
                )
            if not str(row.get("timestamp_precision", "")).strip():
                errors.append(
                    {"code": "MISSING_TIMESTAMP_PRECISION", "action_id": action_id}
                )
        except (CorporateActionError, ValueError) as exc:
            errors.append(
                {
                    "code": "INVALID_ACTION",
                    "action_id": action_id,
                    "detail": str(exc),
                }
            )

    for action_id, history in revisions.items():
        listing_ids = {
            str(row.get("listing_id", "")).strip() for row in history
        }
        if len(listing_ids) != 1:
            errors.append(
                {
                    "code": "ACTION_REVISION_LISTING_CHANGED",
                    "action_id": action_id,
                }
            )
        ordered = sorted(
            history,
            key=lambda row: parse_timestamp(row["available_at"], field="available_at"),
        )
        times = [
            parse_timestamp(row["available_at"], field="available_at")
            for row in ordered
        ]
        if len(times) != len(set(times)):
            errors.append(
                {"code": "AMBIGUOUS_ACTION_REVISION", "action_id": action_id}
            )
    return errors


def _action_state_as_of(
    actions: Iterable[Mapping[str, Any]], cutoff: Any
) -> list[Mapping[str, Any]]:
    cutoff_time = parse_timestamp(cutoff, field="cutoff_at")
    by_action: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for action in actions:
        if parse_timestamp(action["available_at"], field="available_at") <= cutoff_time:
            by_action[str(action["action_id"])].append(action)
    selected: list[Mapping[str, Any]] = []
    for history in by_action.values():
        latest_at = max(
            parse_timestamp(row["available_at"], field="available_at")
            for row in history
        )
        finalists = [
            row
            for row in history
            if parse_timestamp(row["available_at"], field="available_at") == latest_at
        ]
        if len(finalists) != 1:
            raise CorporateActionError("AMBIGUOUS_ACTION_REVISION")
        chosen = finalists[0]
        if str(chosen["action_status"]).upper() in ACTIVE_ACTION_STATES:
            selected.append(chosen)
    return selected


def build_return_components(
    panel_rows: list[Mapping[str, Any]],
    action_rows: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build historical one-session returns outside the observable panel.

    Raw OHLCV values are preserved. Unsupported complex actions, ambiguous
    revisions, and missing terminal consideration produce typed quarantine
    rather than guessed continuity. Future action revisions are invisible.
    """

    actions_by_listing: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for action in action_rows:
        actions_by_listing[str(action["listing_id"])].append(action)

    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in panel_rows:
        grouped[str(row["listing_id"])].append(row)

    output: list[dict[str, Any]] = []
    for listing_id in sorted(grouped):
        previous_close: Decimal | None = None
        previous_row_session: str | None = None
        previous_currency: str | None = None
        for row in sorted(
            grouped[listing_id], key=lambda item: str(item["session_date"])
        ):
            security_id = str(row["security_id"])
            current_close = decimal_value(row.get("close"), field="close", required=False)
            current_volume = decimal_value(
                row.get("volume"), field="volume", required=False
            )
            current_currency = str(row.get("currency", "")).upper()
            quality = "PASSED"
            reason = ""
            try:
                known_actions = _action_state_as_of(
                    actions_by_listing.get(listing_id, []), row["cutoff_at"]
                )
            except CorporateActionError:
                known_actions = []
                quality = "QUARANTINED"
                reason = "AMBIGUOUS_ACTION_REVISION"
            relevant = [
                action
                for action in known_actions
                if str(action["ex_date"]) == str(row["session_date"])
            ]
            visible = relevant

            action_types = {str(action["action_type"]).upper() for action in visible}
            unsupported = sorted(action_types - SUPPORTED_ACTIONS)
            split_multiplier = Decimal("1")
            distribution = Decimal("0")
            terminal_value: Decimal | None = None
            continuity_state = "CONTINUOUS"

            if quality == "PASSED" and unsupported:
                quality = "QUARANTINED"
                reason = f"UNSUPPORTED_ACTION:{','.join(unsupported)}"
                continuity_state = "BREAK"
            elif quality == "PASSED":
                for action in visible:
                    action_type = str(action["action_type"]).upper()
                    if action_type in {"CASH_DISTRIBUTION", "TERMINAL_DELISTING"}:
                        action_currency = str(action.get("currency", "")).upper()
                        row_currency = str(row.get("currency", "")).upper()
                        if not action_currency or action_currency != row_currency:
                            quality = "QUARANTINED"
                            reason = "ACTION_CURRENCY_MISMATCH"
                            continuity_state = "BREAK"
                            break
                    if action_type == "SPLIT":
                        ratio = decimal_value(
                            action.get("split_ratio"), field="split_ratio"
                        )
                        if ratio is None or ratio <= 0:
                            quality = "QUARANTINED"
                            reason = "INVALID_SPLIT_RATIO"
                            continuity_state = "BREAK"
                        else:
                            split_multiplier *= ratio
                    elif action_type == "CASH_DISTRIBUTION":
                        amount = decimal_value(
                            action.get("cash_amount"), field="cash_amount"
                        )
                        distribution += amount or Decimal("0")
                    elif action_type == "TERMINAL_DELISTING":
                        if terminal_value is not None:
                            quality = "QUARANTINED"
                            reason = "MULTIPLE_TERMINAL_OUTCOMES"
                            continuity_state = "BREAK"
                        terminal_value = decimal_value(
                            action.get("terminal_consideration"),
                            field="terminal_consideration",
                        )

            lifecycle_state = str(row.get("lifecycle_state", "")).upper()
            if quality == "PASSED" and terminal_value is not None:
                if action_types - {"TERMINAL_DELISTING"}:
                    quality = "QUARANTINED"
                    reason = "TERMINAL_COMPOUND_ACTION_UNSUPPORTED"
                    continuity_state = "BREAK"
                elif lifecycle_state != "DELISTED":
                    quality = "QUARANTINED"
                    reason = "TERMINAL_LIFECYCLE_MISMATCH"
                    continuity_state = "BREAK"
                elif current_close is not None:
                    # The first frozen convention represents a terminal
                    # settlement as a DELISTED security-day with no ordinary
                    # market bar. A simultaneous traded close is ambiguous and
                    # must never fall through to the ordinary return formula.
                    quality = "QUARANTINED"
                    reason = "TERMINAL_BAR_CONFLICT"
                    continuity_state = "BREAK"

            raw_return: Decimal | None = None
            price_return: Decimal | None = None
            distribution_return: Decimal | None = None
            terminal_return: Decimal | None = None
            total_return: Decimal | None = None
            comparable_volume: Decimal | None = None

            consecutive = (
                previous_row_session is not None
                and previous_row_session
                == str(row.get("previous_session_date", ""))
            )
            same_currency = (
                previous_currency is None or previous_currency == current_currency
            )
            comparison_close = previous_close if consecutive and same_currency else None
            if consecutive and not same_currency and quality == "PASSED":
                quality = "QUARANTINED"
                reason = "CURRENCY_CONTINUITY_BREAK"
                continuity_state = "BREAK"
            if previous_row_session is not None and not consecutive and quality == "PASSED":
                reason = "NON_CONSECUTIVE_OBSERVATION"
                continuity_state = "BREAK"

            if quality == "PASSED" and comparison_close is not None and comparison_close != 0:
                if terminal_value is not None and current_close is None:
                    terminal_return = terminal_value / comparison_close - Decimal("1")
                    total_return = terminal_return
                    continuity_state = "BREAK"
                elif current_close is not None:
                    raw_return = current_close / comparison_close - Decimal("1")
                    price_return = (
                        current_close * split_multiplier / comparison_close - Decimal("1")
                    )
                    distribution_return = (
                        distribution * split_multiplier / comparison_close
                    )
                    total_return = price_return + distribution_return
                    if current_volume is not None:
                        comparable_volume = current_volume / split_multiplier
                elif str(row.get("lifecycle_state", "")).upper() == "DELISTED":
                    quality = "QUARANTINED"
                    reason = "MISSING_TERMINAL_OUTCOME"
                    continuity_state = "BREAK"
                elif str(row.get("lifecycle_state", "")).upper() in {
                    "HALTED",
                    "SUSPENDED",
                }:
                    reason = f"{str(row.get('lifecycle_state')).upper()}_NO_BAR"
                    continuity_state = "BREAK"
            elif quality == "PASSED" and comparison_close is None and not reason:
                if previous_row_session is None:
                    reason = "INSUFFICIENT_HISTORY"
                else:
                    reason = "PRIOR_SESSION_VALUE_ABSENT"
                    continuity_state = "BREAK"

            return_row = {
                    "session_date": str(row["session_date"]),
                    "security_id": security_id,
                    "listing_id": str(row.get("listing_id", "")),
                    "previous_close": decimal_text(comparison_close),
                    "raw_close": decimal_text(current_close),
                    "raw_return_1d": decimal_text(raw_return),
                    "split_multiplier": decimal_text(split_multiplier),
                    "split_consistent_volume": decimal_text(comparable_volume),
                    "price_return_1d": decimal_text(price_return),
                    "distribution_return_1d": decimal_text(distribution_return),
                    "terminal_return": decimal_text(terminal_return),
                    "total_return_1d": decimal_text(total_return),
                    "action_ids": ";".join(
                        sorted(str(action["action_id"]) for action in visible)
                    ),
                    "action_record_ids": ";".join(
                        sorted(str(action["source_record_id"]) for action in visible)
                    ),
                    "action_state": (
                        "NONE" if not visible else ";".join(sorted(action_types))
                    ),
                    "return_quality_state": quality,
                    "return_missing_reason": reason,
                    "continuity_state": continuity_state,
                }
            output.append({column: return_row[column] for column in RETURN_COLUMNS})
            previous_close = current_close
            previous_row_session = str(row["session_date"])
            previous_currency = current_currency
    return sorted(output, key=lambda row: (row["session_date"], row["security_id"]))
