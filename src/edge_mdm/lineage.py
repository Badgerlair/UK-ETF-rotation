"""Frozen field-level lineage for the first feature-ready daily slice."""

from __future__ import annotations

from typing import Mapping


FIELD_LINEAGE_VERSION = "edge.daily_field_lineage.v1"


def _source(table: str, field: str) -> dict[str, str]:
    return {
        "role": "OBSERVABLE",
        "origin": "MDM_SOURCE_FIELD",
        "source_table": table,
        "source_field": field,
    }


def _derived(rule: str, *tables: str) -> dict[str, str]:
    return {
        "role": "OBSERVABLE",
        "origin": "DETERMINISTIC_DERIVATION",
        "source_table": ";".join(tables),
        "source_field": "",
        "rule": rule,
    }


PANEL_FIELD_LINEAGE: Mapping[str, Mapping[str, str]] = {
    "session_date": _source("exchange_sessions", "session_date"),
    "calendar_id": _source("exchange_sessions", "calendar_id"),
    "exchange_id": _source("exchange_sessions", "exchange_id"),
    "session_state": _source("exchange_sessions", "session_state"),
    "previous_session_date": _source("exchange_sessions", "previous_session_date"),
    "next_session_date": _source("exchange_sessions", "next_session_date"),
    "open_at": _source("exchange_sessions", "open_at"),
    "close_at": _source("exchange_sessions", "close_at"),
    "cutoff_at": _source("exchange_sessions", "cutoff_at"),
    "security_id": _source("identity_lifecycle", "security_id"),
    "issuer_id": _source("identity_lifecycle", "issuer_id"),
    "listing_id": _source("identity_lifecycle", "listing_id"),
    "ticker": _source("identity_lifecycle", "ticker"),
    "security_type": _source("identity_lifecycle", "security_type"),
    "share_class": _source("identity_lifecycle", "share_class"),
    "primary_listing": _source("identity_lifecycle", "primary_listing"),
    "currency": _source("identity_lifecycle", "currency"),
    "lifecycle_state": _source("identity_lifecycle", "lifecycle_state"),
    "universe_id": _source("universe_membership", "universe_id"),
    "candidate": _derived(
        "PIT lifecycle and frozen population policy", "identity_lifecycle"
    ),
    "eligible": _derived(
        "candidate plus PIT membership and lifecycle", "identity_lifecycle", "universe_membership"
    ),
    "exclusion_reason": _derived(
        "first deterministic failed population rule", "identity_lifecycle", "universe_membership"
    ),
    "action_state": _derived(
        "latest action revision available by cutoff", "corporate_actions"
    ),
    "action_record_ids": _derived(
        "sorted source records supporting action_state", "corporate_actions"
    ),
    "open": _source("daily_observations", "open"),
    "high": _source("daily_observations", "high"),
    "low": _source("daily_observations", "low"),
    "close": _source("daily_observations", "close"),
    "volume": _source("daily_observations", "volume"),
    "price_basis": _source("daily_observations", "price_basis"),
    "observation_state": _source("daily_observations", "observation_state"),
    "value_state": _derived(
        "source state or typed absence", "daily_observations", "identity_lifecycle"
    ),
    "missing_reason": _derived(
        "typed deterministic reason for absent values", "daily_observations", "identity_lifecycle"
    ),
    "quality_state": _derived(
        "source quality or governed terminal state", "daily_observations", "identity_lifecycle"
    ),
    "identity_record_id": _derived(
        "selected PIT identity source record", "identity_lifecycle"
    ),
    "membership_record_id": _derived(
        "selected PIT membership source record", "universe_membership"
    ),
    "observation_record_id": _derived(
        "exact daily observation source record", "daily_observations"
    ),
}
