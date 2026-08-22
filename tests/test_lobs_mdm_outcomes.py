"""Leakage and immutability tests for LOBS MDM/outcome boundaries."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from edge_lobs.errors import LobsError
from edge_lobs.mdm import (
    ENRICHMENT_SCHEMA_VERSION,
    STRUCTURAL_VALIDATION_ONLY,
    TEST_ONLY_CLASSIFICATION,
    derive_last_completed_session,
    materialise_production_enrichment,
    read_mdm_status,
    reject_mdm_taxonomy_source_leakage,
    require_production_mdm_access,
    validate_test_only_enrichment,
    validate_test_only_feature_inputs,
)
from edge_lobs.outcomes import (
    ALLOWED_HORIZONS,
    OUTCOME_ARTIFACT_MANIFEST_SCHEMA_VERSION,
    OUTCOME_LAYER,
    OUTCOME_SCHEMA_VERSION,
    derive_first_permissible_outcome_session,
    derive_outcome_window,
    materialise_production_outcomes,
    materialise_test_only_outcomes,
    validate_outcome_horizon,
    validate_test_only_outcomes,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = REPOSITORY_ROOT / "observations" / "leadership_rotation" / "schemas"
OBSERVATION_BATCH_ID = "EDGE-LOBS-20260811-TEST"
INFORMATION_CUTOFF = "2026-08-11T07:02:00+02:00"
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def _session(session_date: str) -> dict[str, object]:
    return {
        "exchange_id": "XNYS",
        "session_date": session_date,
        "session_state": "REGULAR",
        "open_at": f"{session_date}T13:30:00Z",
        "close_at": f"{session_date}T20:00:00Z",
        "cutoff_at": f"{session_date}T20:05:00Z",
        "available_at": "2026-08-01T00:00:00Z",
    }


def _sessions() -> list[dict[str, object]]:
    return [
        _session(day)
        for day in (
            "2026-08-07",
            "2026-08-10",
            "2026-08-11",
            "2026-08-12",
            "2026-08-13",
            "2026-08-14",
            "2026-08-17",
        )
    ]


def _batch_manifest() -> dict[str, object]:
    return {
        "observation_batch_id": OBSERVATION_BATCH_ID,
        "information_cutoff_timestamp": INFORMATION_CUTOFF,
    }


def _enrichment_document() -> dict[str, object]:
    return {
        "schema_version": ENRICHMENT_SCHEMA_VERSION,
        "classification": TEST_ONLY_CLASSIFICATION,
        "production_use_permitted": False,
        "research_use_permitted": False,
        "admission_status": STRUCTURAL_VALIDATION_ONLY,
        "observation_batch_id": OBSERVATION_BATCH_ID,
        "information_cutoff_timestamp": INFORMATION_CUTOFF,
        "exchange_id": "XNYS",
        "last_eligible_completed_session": "2026-08-10",
        "source_snapshot_id": "MDM-SYNTHETIC-TEST",
        "source_artifact_manifest_sha256": HASH_A,
        "source_manifest_sha256": HASH_B,
        "software_source_sha256": HASH_C,
        "rows": [
            {
                "feature_id": "return_1d",
                "feature_definition_version": "TEST-V1",
                "entity_id": "LISTING-TEST-001",
                "derivation_type": "MDM_DERIVED",
                "source_snapshot_id": "MDM-SYNTHETIC-TEST",
                "max_available_at": "2026-08-10T20:05:00Z",
                "max_contributing_session": "2026-08-10",
                "value": 0.01,
                "value_state": "OBSERVED",
            }
        ],
    }


def _outcome_document(*, horizon: int = 3) -> dict[str, object]:
    window = derive_outcome_window(
        _sessions(),
        information_cutoff_timestamp=INFORMATION_CUTOFF,
        exchange_id="XNYS",
        horizon_sessions=horizon,
    )
    return {
        "schema_version": OUTCOME_SCHEMA_VERSION,
        "classification": TEST_ONLY_CLASSIFICATION,
        "production_use_permitted": False,
        "research_use_permitted": False,
        "admission_status": STRUCTURAL_VALIDATION_ONLY,
        "observation_batch_id": OBSERVATION_BATCH_ID,
        "information_cutoff_timestamp": INFORMATION_CUTOFF,
        "exchange_id": "XNYS",
        "calculation_timestamp": "2026-08-17T21:00:00Z",
        "source_snapshot_id": "MDM-SYNTHETIC-TEST",
        "source_artifact_manifest_sha256": HASH_A,
        "source_manifest_sha256": HASH_B,
        "software_source_sha256": HASH_C,
        "rows": [
            {
                "outcome_id": "EDGE-OUTCOME-TEST-001",
                "layer": OUTCOME_LAYER,
                "outcome_definition_id": "FORWARD_CLOSE_RETURN",
                "outcome_definition_version": "TEST-V1",
                "source_snapshot_id": "MDM-SYNTHETIC-TEST",
                "horizon_sessions": horizon,
                "first_contributing_at": window.first_contributing_at,
                "start_session": window.start_session,
                "end_session": window.end_session,
                "maturity_timestamp": window.maturity_timestamp,
                "max_available_at": window.maturity_timestamp,
                "value": 0.12,
                "value_state": "OBSERVED",
                "terminal_state": "COMPLETE_PATH",
            }
        ],
    }


def _assert_error(code: str, function, /, *args, **kwargs) -> LobsError:
    with pytest.raises(LobsError) as caught:
        function(*args, **kwargs)
    assert caught.value.code == code
    return caught.value


@pytest.mark.parametrize(
    ("filename", "schema_version", "row_definition"),
    (
        (
            "leadership_mdm_enrichment.v1.schema.json",
            ENRICHMENT_SCHEMA_VERSION,
            "enrichmentRow",
        ),
        (
            "leadership_forward_outcomes.v1.schema.json",
            OUTCOME_SCHEMA_VERSION,
            "outcomeRow",
        ),
    ),
)
def test_published_test_only_schemas_load_and_pin_exact_runtime_versions(
    filename: str, schema_version: str, row_definition: str
) -> None:
    schema = json.loads((SCHEMA_ROOT / filename).read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schema_version"] == {"const": schema_version}
    assert schema["properties"]["classification"] == {
        "const": TEST_ONLY_CLASSIFICATION
    }
    assert schema["properties"]["production_use_permitted"] == {"const": False}
    assert schema["properties"]["research_use_permitted"] == {"const": False}
    assert schema["properties"]["admission_status"] == {
        "const": STRUCTURAL_VALIDATION_ONLY
    }
    assert row_definition in schema["$defs"]
    assert "runtime validator is authoritative" in schema["description"]

    if schema_version == OUTCOME_SCHEMA_VERSION:
        assert schema["$defs"]["outcomeRow"]["properties"]["horizon_sessions"][
            "enum"
        ] == sorted(ALLOWED_HORIZONS)


def test_current_repository_mdm_status_and_real_materialisation_fail_closed() -> None:
    status = read_mdm_status(REPOSITORY_ROOT)
    assert status.ready is False
    assert status.production_use_permitted is False
    assert "MDM_CAPABILITY_GATE_BLOCKED" in status.blockers
    assert "POPULATION_TIME_CONTRACT_UNRATIFIED" in status.blockers
    assert "NO_APPROVED_PRODUCTION_SCOPE" in status.blockers
    assert "PRODUCTION_RELEASE_AUTHORITY_NOT_READY" in status.blockers

    production_arguments = {
        "artifact": None,
        "repository_root": REPOSITORY_ROOT,
        "register_path": REPOSITORY_ROOT / "research" / "release.jsonl",
        "source_snapshot": None,
        "production_scope": None,
    }
    for function in (
        require_production_mdm_access,
        materialise_production_enrichment,
        materialise_production_outcomes,
    ):
        _assert_error(
            "MDM_ENRICHMENT_PRODUCTION_BLOCKED", function, **production_arguments
        )


def test_last_completed_session_is_derived_from_availability_and_cutoff() -> None:
    result = derive_last_completed_session(
        _sessions(),
        information_cutoff_timestamp=INFORMATION_CUTOFF,
        exchange_id="XNYS",
    )
    assert result["session_date"] == "2026-08-10"

    unknown_until_later = _sessions()
    unknown_until_later[1]["available_at"] = "2026-08-11T06:00:00Z"
    result = derive_last_completed_session(
        unknown_until_later,
        information_cutoff_timestamp=INFORMATION_CUTOFF,
        exchange_id="XNYS",
    )
    assert result["session_date"] == "2026-08-07"


def test_feature_inputs_reject_bars_after_cutoff_and_uncompleted_session() -> None:
    valid = validate_test_only_feature_inputs(
        [
            {
                "session_date": "2026-08-10",
                "available_at": "2026-08-10T20:05:00Z",
            }
        ],
        _sessions(),
        information_cutoff_timestamp=INFORMATION_CUTOFF,
        exchange_id="XNYS",
        requested_last_completed_session="2026-08-10",
    )
    assert valid.last_completed_session == "2026-08-10"
    assert valid.as_dict()["production_use_permitted"] is False

    _assert_error(
        "MDM_INPUT_AFTER_INFORMATION_CUTOFF",
        validate_test_only_feature_inputs,
        [
            {
                "session_date": "2026-08-10",
                "available_at": "2026-08-11T06:00:00Z",
            }
        ],
        _sessions(),
        information_cutoff_timestamp=INFORMATION_CUTOFF,
        exchange_id="XNYS",
    )
    _assert_error(
        "MDM_BAR_SESSION_NOT_COMPLETED",
        validate_test_only_feature_inputs,
        [
            {
                "session_date": "2026-08-11",
                "available_at": "2026-08-11T04:00:00Z",
            }
        ],
        _sessions(),
        information_cutoff_timestamp=INFORMATION_CUTOFF,
        exchange_id="XNYS",
    )
    _assert_error(
        "LAST_COMPLETED_SESSION_MISMATCH",
        validate_test_only_feature_inputs,
        [],
        _sessions(),
        information_cutoff_timestamp=INFORMATION_CUTOFF,
        exchange_id="XNYS",
        requested_last_completed_session="2026-08-11",
    )


def test_feature_inputs_reject_current_or_ineffective_membership() -> None:
    valid_membership = {
        "membership_basis": "POINT_IN_TIME",
        "available_at": "2026-08-01T00:00:00Z",
        "effective_from": "2026-01-01T00:00:00Z",
        "effective_to": None,
    }
    result = validate_test_only_feature_inputs(
        [],
        _sessions(),
        information_cutoff_timestamp=INFORMATION_CUTOFF,
        exchange_id="XNYS",
        membership_rows=[valid_membership],
    )
    assert result.membership_count == 1

    current = deepcopy(valid_membership)
    current["membership_basis"] = "CURRENT"
    _assert_error(
        "CURRENT_MEMBERSHIP_FORBIDDEN",
        validate_test_only_feature_inputs,
        [],
        _sessions(),
        information_cutoff_timestamp=INFORMATION_CUTOFF,
        exchange_id="XNYS",
        membership_rows=[current],
    )

    current_string = deepcopy(valid_membership)
    current_string["Current_Membership"] = "true"
    _assert_error(
        "CURRENT_MEMBERSHIP_FORBIDDEN",
        validate_test_only_feature_inputs,
        [],
        _sessions(),
        information_cutoff_timestamp=INFORMATION_CUTOFF,
        exchange_id="XNYS",
        membership_rows=[current_string],
    )

    future = deepcopy(valid_membership)
    future["effective_from"] = "2026-08-11T13:30:00Z"
    _assert_error(
        "INEFFECTIVE_MEMBERSHIP_FORBIDDEN",
        validate_test_only_feature_inputs,
        [],
        _sessions(),
        information_cutoff_timestamp=INFORMATION_CUTOFF,
        exchange_id="XNYS",
        membership_rows=[future],
    )


def test_mdm_taxonomy_cannot_enter_source_observation_layer() -> None:
    reject_mdm_taxonomy_source_leakage(
        {"groups": [{"taxonomy_origin": "SOURCE_TAXONOMY"}]}
    )
    _assert_error(
        "MDM_TAXONOMY_SOURCE_LEAKAGE",
        reject_mdm_taxonomy_source_leakage,
        {"groups": [{"taxonomy_origin": "MDM_TAXONOMY"}]},
    )
    _assert_error(
        "MDM_TAXONOMY_SOURCE_LEAKAGE",
        reject_mdm_taxonomy_source_leakage,
        {"groups": [{"Taxonomy_Origin": " mdm_taxonomy "}]},
    )


def test_test_only_enrichment_validates_structure_but_never_authorises() -> None:
    report = validate_test_only_enrichment(
        _enrichment_document(),
        batch_manifest=_batch_manifest(),
        session_rows=_sessions(),
    )
    assert report.passed
    assert report.as_dict()["classification"] == TEST_ONLY_CLASSIFICATION
    assert report.as_dict()["production_use_permitted"] is False
    assert report.as_dict()["research_use_permitted"] is False

    self_authorised = _enrichment_document()
    self_authorised["production_use_permitted"] = True
    _assert_error(
        "TEST_ONLY_SELF_AUTHORISATION_FORBIDDEN",
        validate_test_only_enrichment,
        self_authorised,
        batch_manifest=_batch_manifest(),
        session_rows=_sessions(),
    )

    nested_authority = _enrichment_document()
    nested_authority["rows"][0]["Released"] = "yes"
    _assert_error(
        "TEST_ONLY_SELF_AUTHORISATION_FORBIDDEN",
        validate_test_only_enrichment,
        nested_authority,
        batch_manifest=_batch_manifest(),
        session_rows=_sessions(),
    )


def test_test_only_enrichment_rejects_late_session_and_outcome_fields() -> None:
    late = _enrichment_document()
    late["rows"][0]["max_available_at"] = "2026-08-11T06:00:00Z"
    _assert_error(
        "MDM_INPUT_AFTER_INFORMATION_CUTOFF",
        validate_test_only_enrichment,
        late,
        batch_manifest=_batch_manifest(),
        session_rows=_sessions(),
    )

    future_session = _enrichment_document()
    future_session["rows"][0]["max_contributing_session"] = "2026-08-11"
    _assert_error(
        "MDM_BAR_SESSION_NOT_COMPLETED",
        validate_test_only_enrichment,
        future_session,
        batch_manifest=_batch_manifest(),
        session_rows=_sessions(),
    )

    outcome_bearing = _enrichment_document()
    outcome_bearing["rows"][0]["forward_return"] = 0.50
    _assert_error(
        "OUTCOME_FIELD_FORBIDDEN_IN_ENRICHMENT",
        validate_test_only_enrichment,
        outcome_bearing,
        batch_manifest=_batch_manifest(),
        session_rows=_sessions(),
    )

    nested_outcome = _enrichment_document()
    nested_outcome["rows"][0]["metadata"] = {"Outcome_Label": "WINNER"}
    _assert_error(
        "OUTCOME_FIELD_FORBIDDEN_IN_ENRICHMENT",
        validate_test_only_enrichment,
        nested_outcome,
        batch_manifest=_batch_manifest(),
        session_rows=_sessions(),
    )

    outcome_feature = _enrichment_document()
    outcome_feature["rows"][0]["feature_id"] = "forward_return_20d"
    _assert_error(
        "OUTCOME_FEATURE_ID_FORBIDDEN",
        validate_test_only_enrichment,
        outcome_feature,
        batch_manifest=_batch_manifest(),
        session_rows=_sessions(),
    )


def test_first_outcome_session_is_the_first_open_strictly_after_cutoff() -> None:
    first = derive_first_permissible_outcome_session(
        _sessions(),
        information_cutoff_timestamp=INFORMATION_CUTOFF,
        exchange_id="XNYS",
    )
    assert first["session_date"] == "2026-08-11"

    during_session = derive_first_permissible_outcome_session(
        _sessions(),
        information_cutoff_timestamp="2026-08-11T15:00:00Z",
        exchange_id="XNYS",
    )
    assert during_session["session_date"] == "2026-08-12"


def test_allowed_horizons_and_mechanical_outcome_window() -> None:
    assert validate_outcome_horizon(1) == 1
    assert validate_outcome_horizon(60) == 60
    _assert_error("OUTCOME_HORIZON_NOT_ALLOWED", validate_outcome_horizon, 2)
    _assert_error("OUTCOME_HORIZON_INVALID", validate_outcome_horizon, True)

    window = derive_outcome_window(
        _sessions(),
        information_cutoff_timestamp=INFORMATION_CUTOFF,
        exchange_id="XNYS",
        horizon_sessions=3,
    )
    assert window.first_contributing_at == "2026-08-11T13:30:00Z"
    assert window.start_session == "2026-08-11"
    assert window.end_session == "2026-08-13"
    assert window.maturity_timestamp == "2026-08-13T20:05:00Z"


def test_outcome_validator_enforces_maturity_clock_and_source_separation() -> None:
    report = validate_test_only_outcomes(
        _outcome_document(),
        batch_manifest=_batch_manifest(),
        session_rows=_sessions(),
    )
    assert report.passed
    assert report.as_dict()["research_use_permitted"] is False

    early = _outcome_document()
    early["calculation_timestamp"] = "2026-08-13T20:04:59Z"
    _assert_error(
        "OUTCOME_HORIZON_NOT_MATURE",
        validate_test_only_outcomes,
        early,
        batch_manifest=_batch_manifest(),
        session_rows=_sessions(),
    )

    wrong_clock = _outcome_document()
    wrong_clock["rows"][0]["start_session"] = "2026-08-10"
    _assert_error(
        "OUTCOME_CLOCK_MISMATCH",
        validate_test_only_outcomes,
        wrong_clock,
        batch_manifest=_batch_manifest(),
        session_rows=_sessions(),
    )

    embedded_source = _outcome_document()
    embedded_source["rows"][0]["source_text"] = "Watching for a range breakout"
    _assert_error(
        "SOURCE_PAYLOAD_FORBIDDEN_IN_OUTCOME",
        validate_test_only_outcomes,
        embedded_source,
        batch_manifest=_batch_manifest(),
        session_rows=_sessions(),
    )

    future_input = _outcome_document()
    future_input["rows"][0]["max_available_at"] = "2026-08-17T21:00:01Z"
    _assert_error(
        "OUTCOME_INPUT_AFTER_CALCULATION",
        validate_test_only_outcomes,
        future_input,
        batch_manifest=_batch_manifest(),
        session_rows=_sessions(),
    )


def test_test_only_outcome_materialisation_is_separate_atomic_and_immutable(
    tmp_path: Path,
) -> None:
    document = _outcome_document()
    artifact = materialise_test_only_outcomes(
        document,
        batch_manifest=_batch_manifest(),
        session_rows=_sessions(),
        repository_root=tmp_path,
    )
    authorised_root = (
        tmp_path / "research" / "leadership_rotation" / "outcomes" / "test_only"
    ).resolve()
    assert artifact.artifact_root.parent == authorised_root
    assert artifact.artifact_id == "EDGE-LOUT-" + artifact.payload_sha256.upper()
    assert not (tmp_path / "observations").exists()
    assert artifact.payload_path.read_bytes().endswith(b"\n")
    assert hashlib.sha256(artifact.payload_path.read_bytes()).hexdigest() == artifact.payload_sha256
    assert hashlib.sha256(artifact.manifest_path.read_bytes()).hexdigest() == artifact.manifest_sha256

    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == OUTCOME_ARTIFACT_MANIFEST_SCHEMA_VERSION
    assert manifest["classification"] == TEST_ONLY_CLASSIFICATION
    assert manifest["production_use_permitted"] is False
    assert manifest["research_use_permitted"] is False
    assert manifest["admission_status"] == STRUCTURAL_VALIDATION_ONLY
    assert manifest["files"][0]["sha256"] == artifact.payload_sha256

    original_payload = artifact.payload_path.read_bytes()
    _assert_error(
        "IMMUTABLE_OUTCOME_ARTIFACT_EXISTS",
        materialise_test_only_outcomes,
        document,
        batch_manifest=_batch_manifest(),
        session_rows=_sessions(),
        repository_root=tmp_path,
    )
    assert artifact.payload_path.read_bytes() == original_payload

    _assert_error(
        "OUTCOME_ROOT_NOT_SEPARATE",
        materialise_test_only_outcomes,
        document,
        batch_manifest=_batch_manifest(),
        session_rows=_sessions(),
        repository_root=tmp_path,
        output_root=tmp_path / "observations" / "leadership_rotation",
    )
