"""Scientific safety tests for the first deterministic daily implementation slice.

The production source boundary consumes strict Parquet contracts.  The Milestone
3 safety fixture is deliberately CSV and TEST_ONLY_NON_PRODUCTION, so these tests
adapt its rows explicitly into the lower-level scientific APIs.  No adapter here
is a production ingestion path.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any, Mapping

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from edge_mdm.actions import build_return_components
from edge_mdm.assemble import (
    PANEL_COLUMNS,
    AssemblyError,
    assemble_security_day_panel,
    enforce_outcome_firewall,
    observation_key_errors,
)
from edge_mdm.fingerprint import logical_rows_fingerprint
from edge_mdm.temporal import (
    identity_interval_errors,
    parse_timestamp,
    resolve_ticker,
    select_point_in_time,
    session_for_timestamp,
    session_shift,
)
from edge_mdm.universe import build_historical_universe, universe_counts
from edge_mdm.validation import (
    calendar_errors,
    membership_errors,
    observation_value_errors,
    panel_errors,
    return_component_errors,
    universe_errors,
)
from tests.fixture_factory import build_fixture


REQUESTED_DATES = (
    "2024-03-08",
    "2024-03-11",
    "2024-03-12",
    "2024-03-14",
    "2024-03-15",
    "2024-03-18",
)


def _csv_rows(bundle: Any, table_name: str) -> list[dict[str, str]]:
    with bundle.table_path(table_name).open("r", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def _sessions(bundle: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in _csv_rows(bundle, "exchange_sessions"):
        if row["session_date"] < "2024-03-08" or row["session_date"] > "2024-03-18":
            continue
        result.append(
            {
                **row,
                "exchange": row["exchange_id"],
                "calendar_id": row["calendar_id"],
                "source_record_id": f"SESSION-{row['exchange_id']}-{row['session_date']}",
                "quality_state": "PASSED",
            }
        )
    return result


def _identity(bundle: Any) -> list[dict[str, Any]]:
    """Create the current bounded canonical identity shape from fixture vintages."""

    source = {row["record_id"]: row for row in _csv_rows(bundle, "identity_lifecycle")}
    record_ids = [
        "SYM-S1-ARC-V2",
        "SYM-S1-NOVA",
        "SYM-S2-ARC",
        "SYM-S3-FALL",
    ]
    if "SYM-S4-ARC" in source:
        record_ids.append("SYM-S4-ARC")

    list_dates = {
        "S1": "2024-01-01",
        "S2": "2024-03-14",
        "S3": "2024-01-01",
        "S4": "2024-03-14",
    }
    results: list[dict[str, Any]] = []
    for record_id in record_ids:
        row = source[record_id]
        available_at = row["available_at"]
        source_record_id = record_id
        # This is the deterministic canonical consolidation of the ARC V1/V2
        # chain, not a direct production-source adapter.
        if record_id == "SYM-S1-ARC-V2":
            available_at = source["SYM-S1-ARC-V1"]["available_at"]
            source_record_id = "SYM-S1-ARC"
        results.append(
            {
                "source_record_id": source_record_id,
                "security_id": row["security_id"],
                "issuer_id": row["issuer_id"],
                "listing_id": row["listing_id"],
                "ticker": row["ticker"],
                "exchange": row["exchange_id"],
                "exchange_id": row["exchange_id"],
                "currency": row["currency"],
                "security_type": row["security_type"],
                "share_class": row["share_class"],
                "primary_listing": True,
                "lifecycle_state": "ACTIVE",
                "effective_from": row["effective_from"],
                "effective_to": row["effective_to"],
                "available_at": available_at,
                "revision_sequence": "1",
                "list_date": list_dates[row["security_id"]],
                "delist_date": "2024-03-15" if row["security_id"] == "S3" else "",
            }
        )
    delisted = source["LIFE-S3-DELISTED"]
    results.append(
        {
            "source_record_id": delisted["record_id"],
            "security_id": "S3",
            "issuer_id": "I3",
            "listing_id": "L3",
            "ticker": "FALL",
            "exchange": "XEQ",
            "exchange_id": "XEQ",
            "currency": "USD",
            "security_type": "COMMON_STOCK",
            "share_class": "A",
            "primary_listing": True,
            "lifecycle_state": "DELISTED",
            "effective_from": delisted["effective_from"],
            "effective_to": "",
            "available_at": delisted["available_at"],
            "revision_sequence": "1",
            "list_date": "2024-01-01",
            "delist_date": "2024-03-15",
        }
    )
    return results


def _memberships(bundle: Any, sessions: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_date = {
        str(row["session_date"]): row
        for row in sessions
        if str(row["session_state"]).upper() in {"REGULAR", "EARLY_CLOSE"}
    }
    ordered = [date for date in REQUESTED_DATES]
    next_open = {
        date: by_date[ordered[index + 1]]["open_at"] if index + 1 < len(ordered) else ""
        for index, date in enumerate(ordered)
    }
    return [
        {
            "source_record_id": f"UNIV-{row['security_id']}-{row['session_date']}",
            "security_id": row["security_id"],
            "listing_id": row["listing_id"],
            "universe_id": "EDGE-PRIMARY-EQUITY",
            "effective_from": by_date[row["session_date"]]["open_at"],
            "effective_to": next_open[row["session_date"]],
            "available_at": row["research_cutoff"],
            "published_at": row["research_cutoff"],
            "revision_sequence": "1",
            "eligible": row["eligible"],
            "membership_state": "INCLUDED" if row["eligible"] == "true" else "EXCLUDED",
            "reason": row["reason_code"],
            "quality_state": "PASSED",
        }
        for row in _csv_rows(bundle, "universe_membership")
    ]


def _observations(bundle: Any) -> list[dict[str, Any]]:
    return [
        {
            **row,
            "source_record_id": f"OBS-{row['security_id']}-{row['session_date']}",
            "exchange": row["exchange_id"],
            "price_basis": "RAW_UNADJUSTED",
            "observation_state": row["trade_state"],
            "value_state": "PRESENT",
            "quality_state": "PASSED",
        }
        for row in _csv_rows(bundle, "daily_observations")
    ]


def _actions(bundle: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in _csv_rows(bundle, "corporate_actions"):
        results.append(
            {
                **row,
                "source_record_id": f"ACTION-{row['action_id']}",
                "announcement_at": row["published_at"],
                "announced_at": row["published_at"],
                "split_ratio": row["new_shares_per_old_share"],
                "split_from": "1" if row["action_type"] == "SPLIT" else "",
                "split_to": row["new_shares_per_old_share"],
                "cash_amount": row["cash_per_share"],
                "terminal_consideration": row["terminal_cash_per_share"],
                "terminal_value": row["terminal_cash_per_share"],
                "status": "ACTIVE",
                "ex_date": row["effective_at"][:10],
                "timestamp_precision": "EXACT",
            }
        )
    return results


def _sector_rows(bundle: Any) -> list[dict[str, Any]]:
    return [
        {**row, "revision_sequence": "1"}
        for row in _csv_rows(bundle, "sector_history")
    ]


def _fundamental_rows(bundle: Any) -> list[dict[str, Any]]:
    return [
        {
            **row,
            "effective_from": f"{row['fiscal_period_end']}T00:00:00Z",
            "effective_to": "",
            "revision_sequence": row["revision_number"],
        }
        for row in _csv_rows(bundle, "fundamentals")
    ]


def _build_slice(bundle: Any) -> dict[str, Any]:
    sessions = _sessions(bundle)
    identities = _identity(bundle)
    memberships = _memberships(bundle, sessions)
    universe = build_historical_universe(identities, sessions, memberships)
    observations = _observations(bundle)
    actions = _actions(bundle)
    panel, audit = assemble_security_day_panel(universe, observations, actions)
    returns = build_return_components(panel, actions)
    return {
        "sessions": sessions,
        "identities": identities,
        "memberships": memberships,
        "universe": universe,
        "observations": observations,
        "panel": panel,
        "audit": audit,
        "actions": actions,
        "returns": returns,
    }


def _by_key(rows: list[Mapping[str, Any]]) -> dict[tuple[str, str], Mapping[str, Any]]:
    return {(str(row["session_date"]), str(row["security_id"])): row for row in rows}


def test_clean_lower_level_slice_is_point_in_time_complete_and_admissible(
    tmp_path: Path,
) -> None:
    bundle = build_fixture(tmp_path)
    built = _build_slice(bundle)
    expectations = bundle.manifest["scientific_expectations"]

    assert universe_counts(built["universe"]) == {
        "assessment_rows": 18,
        "candidate_rows": 14,
        "eligible_rows": 13,
        "candidate_ineligible_rows": 1,
        "non_candidate_rows": 4,
        "distinct_securities": 3,
        "distinct_sessions": 6,
    }
    assert [
        [row["session_date"], row["security_id"]] for row in built["panel"]
    ] == expectations["feature_ready_keys"]
    assert built["audit"].as_dict() == {
        "left_rows": 14,
        "matched_rows": 13,
        "unmatched_rows": 1,
        "multiple_match_rows": 0,
        "rejected_not_available": 0,
        "terminal_missing_bar_rows": 1,
    }

    terminal = _by_key(built["panel"])[("2024-03-15", "S3")]
    assert terminal["close"] is None
    assert terminal["value_state"] == "TERMINAL_NO_BAR"
    assert terminal["missing_reason"] == "TERMINAL_SETTLEMENT_ONLY"
    assert terminal["quality_state"] == "PASSED"

    assert identity_interval_errors(built["identities"]) == []
    assert calendar_errors(
        built["sessions"], calendar_policy_version="CAL-TEST-001"
    ) == []
    assert observation_value_errors(built["observations"]) == []
    assert membership_errors(built["memberships"]) == []
    assert universe_errors(
        built["universe"], built["identities"], built["sessions"]
    ) == []
    assert all(not errors for errors in panel_errors(built["panel"]))
    assert return_component_errors(built["returns"]) == []


def test_calendar_dst_holiday_and_early_close_are_deterministic(tmp_path: Path) -> None:
    bundle = build_fixture(tmp_path)
    sessions = _sessions(bundle)

    assert session_shift(sessions, "2024-03-08", 1) == "2024-03-11"
    assert session_shift(sessions, "2024-03-12", 1) == "2024-03-14"
    assert session_shift(sessions, "2024-03-15", 1) == "2024-03-18"
    by_date = {row["session_date"]: row for row in sessions}
    assert by_date["2024-03-08"]["close_at"] == "2024-03-08T21:00:00Z"
    assert by_date["2024-03-11"]["close_at"] == "2024-03-11T20:00:00Z"
    assert by_date["2024-03-13"]["session_state"] == "HOLIDAY"
    assert by_date["2024-03-14"]["early_close"] == "true"
    assert by_date["2024-03-14"]["close_at"] == "2024-03-14T17:00:00Z"
    assert session_for_timestamp(sessions, "2024-03-08T21:30:00Z") == "2024-03-11"
    assert session_for_timestamp(sessions, "2024-03-14T17:04:00Z") == "2024-03-14"
    assert session_for_timestamp(sessions, "2024-03-14T17:06:00Z") == "2024-03-15"


def test_ticker_change_and_reuse_resolve_only_by_stable_identity_and_time(
    tmp_path: Path,
) -> None:
    bundle = build_fixture(tmp_path)
    identities = _identity(bundle)

    at_0311 = resolve_ticker(
        identities,
        ticker="ARC",
        exchange_id="XEQ",
        effective_at=parse_timestamp("2024-03-11T20:00:00Z"),
        cutoff=parse_timestamp("2024-03-11T20:05:00Z"),
    )
    at_0315 = resolve_ticker(
        identities,
        ticker="ARC",
        exchange_id="XEQ",
        effective_at=parse_timestamp("2024-03-15T20:00:00Z"),
        cutoff=parse_timestamp("2024-03-15T20:05:00Z"),
    )
    s1_at_0312 = select_point_in_time(
        [row for row in identities if row["security_id"] == "S1"],
        effective_at=parse_timestamp("2024-03-12T20:00:00Z"),
        cutoff=parse_timestamp("2024-03-12T20:05:00Z"),
    )

    assert at_0311.status == "MATCHED"
    assert at_0311.record["security_id"] == "S1"
    assert at_0315.status == "MATCHED"
    assert at_0315.record["security_id"] == "S2"
    assert s1_at_0312.status == "MATCHED"
    assert s1_at_0312.record["ticker"] == "NOVA"
    assert identity_interval_errors(identities) == []


def test_future_sector_index_and_fundamental_vintages_do_not_leak(
    tmp_path: Path,
) -> None:
    bundle = build_fixture(tmp_path)
    sectors = _sector_rows(bundle)
    fundamentals = _fundamental_rows(bundle)
    index_rows = _csv_rows(bundle, "index_membership")

    sector_0312 = select_point_in_time(
        sectors,
        effective_at=parse_timestamp("2024-03-12T20:00:00Z"),
        cutoff=parse_timestamp("2024-03-12T20:05:00Z"),
    )
    sector_0314 = select_point_in_time(
        sectors,
        effective_at=parse_timestamp("2024-03-14T17:00:00Z"),
        cutoff=parse_timestamp("2024-03-14T17:05:00Z"),
    )
    index_0314 = select_point_in_time(
        index_rows,
        effective_at=parse_timestamp("2024-03-14T17:00:00Z"),
        cutoff=parse_timestamp("2024-03-14T17:05:00Z"),
    )
    index_0315 = select_point_in_time(
        index_rows,
        effective_at=parse_timestamp("2024-03-15T20:00:00Z"),
        cutoff=parse_timestamp("2024-03-15T20:05:00Z"),
    )

    assert sector_0312.record["sector"] == "TECH"
    assert sector_0314.record["sector"] == "HEALTH"
    assert index_0314.status == "NO_EFFECTIVE_RECORD"
    assert index_0315.status == "MATCHED"

    expected = {
        "2024-03-11T20:05:00Z": ("NOT_YET_AVAILABLE", None),
        "2024-03-12T20:05:00Z": ("MATCHED", "1.00"),
        "2024-03-14T17:05:00Z": ("MATCHED", "1.00"),
        "2024-03-18T20:05:00Z": ("MATCHED", "0.80"),
    }
    for cutoff_text, (status, value) in expected.items():
        decision = select_point_in_time(
            fundamentals,
            effective_at=parse_timestamp(cutoff_text),
            cutoff=parse_timestamp(cutoff_text),
        )
        assert decision.status == status
        assert (decision.record["value"] if decision.record else None) == value


def test_split_distribution_and_terminal_returns_reconcile_without_rewriting_raw_prices(
    tmp_path: Path,
) -> None:
    bundle = build_fixture(tmp_path)
    built = _build_slice(bundle)
    returns = _by_key(built["returns"])
    panel = _by_key(built["panel"])

    split = returns[("2024-03-12", "S1")]
    assert panel[("2024-03-11", "S1")]["close"] == "100"
    assert panel[("2024-03-12", "S1")]["close"] == "51"
    assert split["raw_return_1d"] == "-0.490000000000"
    assert split["price_return_1d"] == "0.020000000000"
    assert split["split_consistent_volume"] == "1100.000000000000"

    distribution = returns[("2024-03-15", "S1")]
    assert distribution["price_return_1d"] == "-0.019230769231"
    assert distribution["distribution_return_1d"] == "0.019230769231"
    assert distribution["total_return_1d"] == "0.000000000000"

    terminal = returns[("2024-03-15", "S3")]
    assert terminal["terminal_return"] == "-0.800000000000"
    assert terminal["total_return_1d"] == "-0.800000000000"
    assert "A-DEL" not in returns[("2024-03-14", "S3")]["action_ids"]


@pytest.mark.parametrize(
    ("mutation", "bad_date"),
    [("future_bar", "2024-03-19"), ("non_session_bar", "2024-03-13")],
)
def test_future_and_non_session_bar_mutations_fail_the_scoped_calendar_boundary(
    tmp_path: Path, mutation: str, bad_date: str
) -> None:
    bundle = build_fixture(tmp_path, mutations=mutation)
    built = _build_slice(bundle)
    errors = observation_key_errors(
        built["observations"], built["sessions"], built["identities"]
    )

    assert any(
        error["code"] == "OBSERVATION_ON_NON_SESSION"
        and error["session_date"] == bad_date
        for error in errors
    )
    assert len(built["panel"]) == 14
    assert all(row["session_date"] != bad_date for row in built["panel"])


def test_ambiguous_identity_mutation_fails_without_guessing(tmp_path: Path) -> None:
    bundle = build_fixture(tmp_path, mutations="ambiguous_identity")
    identities = _identity(bundle)
    errors = identity_interval_errors(identities)
    decision = resolve_ticker(
        identities,
        ticker="ARC",
        exchange_id="XEQ",
        effective_at=parse_timestamp("2024-03-15T20:00:00Z"),
        cutoff=parse_timestamp("2024-03-15T20:05:00Z"),
    )

    assert any(error["code"] == "AMBIGUOUS_TICKER_IDENTITY" for error in errors)
    assert decision.status == "MULTIPLE_ELIGIBLE_MATCHES"
    assert decision.record is None
    assert decision.eligible_count == 2


def test_missing_terminal_mutation_quarantines_return_interval(tmp_path: Path) -> None:
    bundle = build_fixture(tmp_path, mutations="missing_terminal")
    built = _build_slice(bundle)
    terminal = _by_key(built["returns"])[("2024-03-15", "S3")]

    assert terminal["return_quality_state"] == "QUARANTINED"
    assert terminal["return_missing_reason"] == "MISSING_TERMINAL_OUTCOME"
    assert terminal["total_return_1d"] is None


def test_duplicate_sector_mutation_fails_as_of_join_without_precedence(
    tmp_path: Path,
) -> None:
    bundle = build_fixture(tmp_path, mutations="duplicate_sector")
    decision = select_point_in_time(
        _sector_rows(bundle),
        effective_at=parse_timestamp("2024-03-14T17:00:00Z"),
        cutoff=parse_timestamp("2024-03-14T17:05:00Z"),
    )

    assert decision.status == "MULTIPLE_ELIGIBLE_MATCHES"
    assert decision.record is None
    assert decision.eligible_count == 2


def test_outcome_column_mutation_is_rejected_by_identity_even_when_aliased(
    tmp_path: Path,
) -> None:
    bundle = build_fixture(tmp_path, mutations="outcome_column")
    schema = bundle.manifest["tables"]["daily_observations"]["schema"]
    roles = {column["name"]: column["semantic_role"] for column in schema}
    request = {
        "field_id": "forward_total_return_1_session",
        "alias": "r1",
    }

    with pytest.raises(AssemblyError, match="OUTCOME_FIELD_FORBIDDEN"):
        enforce_outcome_firewall([request], roles)

    # An already completed historical return is governed by role, not a crude
    # rejection of every field whose name contains "return".
    enforce_outcome_firewall(
        [{"field_id": "historical_total_return_1d"}],
        {"historical_total_return_1d": "OBSERVABLE"},
    )


def test_reversed_source_order_produces_identical_scientific_output(
    tmp_path: Path,
) -> None:
    clean_bundle = build_fixture(tmp_path)
    reversed_bundle = build_fixture(tmp_path, mutations="reversed_order")
    clean = _build_slice(clean_bundle)
    reversed_slice = _build_slice(reversed_bundle)

    assert clean["panel"] == reversed_slice["panel"]
    assert clean["returns"] == reversed_slice["returns"]
    assert clean["audit"] == reversed_slice["audit"]

    clean_canonical = {
        table: entry["canonical_rows_sha256"]
        for table, entry in clean_bundle.manifest["tables"].items()
    }
    reversed_canonical = {
        table: entry["canonical_rows_sha256"]
        for table, entry in reversed_bundle.manifest["tables"].items()
    }
    assert clean_canonical == reversed_canonical
    assert any(
        clean_bundle.manifest["tables"][table]["content_sha256"]
        != reversed_bundle.manifest["tables"][table]["content_sha256"]
        for table in clean_bundle.manifest["tables"]
    )

    clean_fingerprint = logical_rows_fingerprint(
        PANEL_COLUMNS,
        ([row[column] for column in PANEL_COLUMNS] for row in clean["panel"]),
    )
    reversed_fingerprint = logical_rows_fingerprint(
        PANEL_COLUMNS,
        ([row[column] for column in PANEL_COLUMNS] for row in reversed_slice["panel"]),
    )
    assert clean_fingerprint == reversed_fingerprint
