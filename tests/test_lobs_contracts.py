"""Focused contract and leakage-boundary tests for ``edge_lobs``."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from edge_lobs.errors import LobsError
from edge_lobs.jsonio import (
    canonical_json_bytes,
    load_json_object,
    write_canonical_json_new,
)
from edge_lobs.validation import (
    validate_import_manifest_document,
    validate_observation_document,
)


def _ready_observation() -> dict:
    return {
        "schema_version": "edge.leadership_observation_batch.v1",
        "observation_batch_id": "EDGE-LOBS-20260811-001",
        "observation_date": "2026-08-11",
        "information_cutoff_timestamp": "2026-08-11T07:10:00+02:00",
        "information_cutoff_timezone": "Europe/Rome",
        "capture_mode": "PROSPECTIVE",
        "recorded_at": "2026-08-11T07:09:00+02:00",
        "source_ids": ["EDGE-LOBS-SRC-20260811-TL"],
        "extractor": {
            "actor_type": "USER",
            "actor_id": "EDGE-USER-001",
            "method": "MANUAL_TRANSCRIPTION",
            "version": "1",
        },
        "validation_status": "READY_FOR_IMPORT",
        "supersedes_batch_id": None,
        "market": [
            {
                "observation_id": "EDGE-LOBS-OBS-20260811-MKT-001",
                "timestamp": "2026-08-11T07:00:00+02:00",
                "timezone": "Europe/Rome",
                "derivation_type": "SOURCE_DERIVED",
                "observation_subtype": None,
                "source_text": "Market is building as new leaders emerge.",
                "source_id": "EDGE-LOBS-SRC-20260811-TL",
                "source_location": "page 1",
                "confidence_of_extraction": "HIGH",
                "capture_mode": "PROSPECTIVE",
                "notes": "",
                "field": "MARKET_DESCRIPTION",
                "metric": None,
                "state": "BUILDING",
            }
        ],
        "instruments": [],
        "groups": [],
        "stocks": [],
        "futures_snapshot": [],
        "macro_context": [],
        "notes": "",
    }


def _ready_manifest() -> dict:
    return {
        "schema_version": "edge.leadership_import_manifest.v1",
        "observation_batch_id": "EDGE-LOBS-20260811-001",
        "observation_path": "observation_batch.json",
        "capture_mode": "PROSPECTIVE",
        "validation_status": "READY_FOR_IMPORT",
        "sources": [
            {
                "source_id": "EDGE-LOBS-SRC-20260811-TL",
                "source_type": "PDF",
                "source_name": "TraderLion",
                "source_title": "Richard Moglen Trade Lab report — 11 Aug 2026",
                "source_original_filename": "trade-lab-2026-08-11.pdf",
                "source_identity": "TRADERLION-TRADE-LAB-20260811",
                "path": "trade-lab-2026-08-11.pdf",
                "source_capture_timestamp": "2026-08-11T06:59:00+02:00",
                "source_publication_timestamp": "2026-08-11T06:30:00+02:00",
                "source_publication_date": "2026-08-11",
                "timestamp_precision": "EXACT_MINUTE",
                "timezone": "Europe/Rome",
                "capture_mode": "PROSPECTIVE",
                "historical_reconstruction": False,
                "contemporaneous_capture_attested": True,
                "expected_sha256": None,
                "parser_version": None,
                "notes": "",
            }
        ],
        "notes": "",
    }


def _draft_pair() -> tuple[dict, dict]:
    observation = _ready_observation()
    observation["validation_status"] = "AWAITING_RAW_SOURCES_AND_PROVENANCE"
    observation["information_cutoff_timestamp"] = None
    observation["information_cutoff_timezone"] = None
    observation["recorded_at"] = None
    observation["market"][0]["timestamp"] = None
    observation["market"][0]["timezone"] = None
    observation["market"][0]["source_location"] = None

    manifest = _ready_manifest()
    manifest["validation_status"] = "AWAITING_RAW_SOURCES_AND_PROVENANCE"
    manifest["observation_path"] = None
    source = manifest["sources"][0]
    for key in (
        "source_original_filename",
        "source_identity",
        "path",
        "source_capture_timestamp",
        "source_publication_timestamp",
        "source_publication_date",
        "timestamp_precision",
        "timezone",
        "historical_reconstruction",
        "contemporaneous_capture_attested",
    ):
        source[key] = None
    return observation, manifest


def _assert_code(expected: str, callable_, *args, **kwargs) -> LobsError:
    with pytest.raises(LobsError) as caught:
        callable_(*args, **kwargs)
    assert caught.value.code == expected
    return caught.value


def test_error_is_machine_readable() -> None:
    error = LobsError("TEST_CODE", "detail", path="$.field")
    assert error.as_dict() == {
        "code": "TEST_CODE",
        "message": "detail",
        "path": "$.field",
    }


def test_strict_json_rejects_duplicate_keys_and_nonfinite_numbers(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"a":1,"a":2}', encoding="utf-8")
    _assert_code("DUPLICATE_JSON_KEY", load_json_object, duplicate)

    for index, token in enumerate(("NaN", "Infinity", "-Infinity", "1e999")):
        invalid = tmp_path / f"nonfinite-{index}.json"
        invalid.write_text(f'{{"value":{token}}}', encoding="utf-8")
        _assert_code("NONFINITE_JSON_NUMBER", load_json_object, invalid)


def test_canonical_writer_is_sorted_newline_terminated_and_exclusive(tmp_path: Path) -> None:
    target = tmp_path / "artifact.json"
    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'
    write_canonical_json_new(target, {"b": 2, "a": 1})
    assert target.read_bytes() == b'{"a":1,"b":2}\n'
    _assert_code("IMMUTABLE_PATH_EXISTS", write_canonical_json_new, target, {})


def test_ready_observation_and_manifest_are_structurally_valid_not_authoritative() -> None:
    observation = _ready_observation()
    observation_report = validate_observation_document(observation)
    assert observation_report.passed
    assert observation_report.state == "STRUCTURALLY_VALID_IMPORT_CANDIDATE"

    manifest_report = validate_import_manifest_document(_ready_manifest(), observation)
    assert manifest_report.passed
    assert manifest_report.state == "IMPORT_CONTRACT_VALID_NON_AUTHORITATIVE"
    assert manifest_report.as_dict()["hard_blocker_count"] == 0


def test_null_provenance_is_allowed_only_for_explicit_non_authoritative_draft() -> None:
    observation, manifest = _draft_pair()
    _assert_code("DRAFT_NOT_IMPORT_ADMISSIBLE", validate_observation_document, observation)
    report = validate_observation_document(observation, allow_draft=True)
    assert report.state == "DRAFT_STRUCTURALLY_ACCEPTED_NON_AUTHORITATIVE"

    _assert_code(
        "TEMPLATE_NOT_IMPORT_ADMISSIBLE",
        validate_import_manifest_document,
        manifest,
        observation,
    )
    template_report = validate_import_manifest_document(
        manifest, observation, allow_template=True
    )
    assert template_report.state == "TEMPLATE_STRUCTURALLY_ACCEPTED_NON_AUTHORITATIVE"

    observation["validation_status"] = "READY_FOR_IMPORT"
    _assert_code(
        "TIMESTAMP_TIMEZONE_PAIR_REQUIRED",
        validate_observation_document,
        observation,
        True,
    )


def test_schema_is_exact_and_outcome_firewall_precedes_generic_key_failure() -> None:
    unexpected = _ready_observation()
    unexpected["unexpected"] = "value"
    _assert_code("SCHEMA_KEYS_MISMATCH", validate_observation_document, unexpected)

    outcome = _ready_observation()
    outcome["market"][0]["forward_return_20d"] = 0.5
    _assert_code("OUTCOME_FIELD_FORBIDDEN", validate_observation_document, outcome)

    nonfinite = _ready_observation()
    nonfinite["notes"] = float("nan")
    _assert_code("NONFINITE_JSON_NUMBER", validate_observation_document, nonfinite)


def test_timezone_offset_and_information_cutoff_fail_closed() -> None:
    mismatch = _ready_observation()
    mismatch["information_cutoff_timestamp"] = "2026-08-11T07:10:00+01:00"
    _assert_code("TIMEZONE_OFFSET_MISMATCH", validate_observation_document, mismatch)

    future_record = _ready_observation()
    future_record["market"][0]["timestamp"] = "2026-08-11T07:11:00+02:00"
    _assert_code(
        "OBSERVATION_AFTER_INFORMATION_CUTOFF",
        validate_observation_document,
        future_record,
    )

    recorded_late = _ready_observation()
    recorded_late["recorded_at"] = "2026-08-11T07:11:00+02:00"
    _assert_code(
        "RECORDED_AFTER_INFORMATION_CUTOFF",
        validate_observation_document,
        recorded_late,
    )

    future_snapshot = _ready_observation()
    future_snapshot["futures_snapshot"] = [
        {
            "observation_id": "EDGE-LOBS-OBS-20260811-FUT-001",
            "timestamp": "2026-08-11T07:00:00+02:00",
            "timezone": "Europe/Rome",
            "derivation_type": "SOURCE_DERIVED",
            "observation_subtype": None,
            "source_text": "US 500 7,763.8 +0.14%",
            "source_id": "EDGE-LOBS-SRC-20260811-TL",
            "source_location": "screenshot row 2",
            "confidence_of_extraction": "HIGH",
            "capture_mode": "PROSPECTIVE",
            "notes": "",
            "instrument": "US 500",
            "value": "7,763.8",
            "change_absolute": None,
            "change_percent": "+0.14%",
            "observation_timestamp": "2026-08-11T07:11:00+02:00",
            "timestamp_precision": "APPROXIMATE_MINUTE",
            "source_type": "SCREENSHOT",
        }
    ]
    _assert_code(
        "OBSERVATION_AFTER_INFORMATION_CUTOFF",
        validate_observation_document,
        future_snapshot,
    )

    draft, _ = _draft_pair()
    draft["information_cutoff_timezone"] = "Not/AZone"
    _assert_code(
        "INVALID_IANA_TIMEZONE",
        validate_observation_document,
        draft,
        True,
    )


def test_missing_timezone_fails_loudly_for_ready_observation_and_source() -> None:
    observation = _ready_observation()
    observation["market"][0]["timezone"] = None
    _assert_code(
        "TIMESTAMP_TIMEZONE_PAIR_REQUIRED",
        validate_observation_document,
        observation,
    )

    observation = _ready_observation()
    manifest = _ready_manifest()
    manifest["sources"][0]["timezone"] = None
    _assert_code(
        "TIMESTAMP_TIMEZONE_PAIR_REQUIRED",
        validate_import_manifest_document,
        manifest,
        observation,
    )


def test_capture_mode_and_derivation_layers_must_agree() -> None:
    mode = _ready_observation()
    mode["market"][0]["capture_mode"] = "RETROSPECTIVE"
    _assert_code("CAPTURE_MODE_MISMATCH", validate_observation_document, mode)

    mdm = _ready_observation()
    mdm["market"][0]["derivation_type"] = "MDM_DERIVED"
    _assert_code("DERIVATION_LAYER_FORBIDDEN", validate_observation_document, mdm)

    user = _ready_observation()
    user["market"][0]["derivation_type"] = "USER_DERIVED"
    _assert_code("USER_DERIVED_SUBTYPE_REQUIRED", validate_observation_document, user)


def test_outcome_derived_label_cannot_be_written_as_source_classification() -> None:
    observation = _ready_observation()
    common = {
        key: value
        for key, value in observation["market"][0].items()
        if key
        in {
            "observation_id",
            "timestamp",
            "timezone",
            "derivation_type",
            "observation_subtype",
            "source_text",
            "source_id",
            "source_location",
            "confidence_of_extraction",
            "capture_mode",
            "notes",
        }
    }
    common["observation_id"] = "EDGE-LOBS-OBS-20260811-GRP-001"
    observation["groups"] = [
        {
            **common,
            "group_id": "SOURCE-GROUP-CYBER",
            "group_name": "cyber",
            "group_type": "THEME",
            "taxonomy_origin": "SOURCE_TAXONOMY",
            "source_classification": "SUCCESSFUL_BREAKOUT",
            "classification_basis": "Assigned after observing the outcome",
        }
    ]
    _assert_code("VALUE_NOT_ALLOWED", validate_observation_document, observation)


def test_manual_traderlion_extraction_remains_source_derived() -> None:
    observation = _ready_observation()
    validate_import_manifest_document(_ready_manifest(), observation)

    observation["market"][0]["derivation_type"] = "USER_DERIVED"
    observation["market"][0]["observation_subtype"] = (
        "CONTEMPORANEOUS_HUMAN_OBSERVATION"
    )
    manifest = _ready_manifest()
    manifest["sources"][0]["source_type"] = "ANALYST_NOTE"
    _assert_code(
        "NAMED_SOURCE_DERIVATION_MISMATCH",
        validate_import_manifest_document,
        manifest,
        observation,
    )


def test_user_derived_requires_an_immutable_human_note_source() -> None:
    observation = _ready_observation()
    observation["market"][0]["derivation_type"] = "USER_DERIVED"
    observation["market"][0]["observation_subtype"] = (
        "CONTEMPORANEOUS_HUMAN_OBSERVATION"
    )
    manifest = _ready_manifest()
    manifest["sources"][0]["source_name"] = "Independent analyst note"
    manifest["sources"][0]["source_title"] = "Morning note"
    manifest["sources"][0]["source_identity"] = "ANALYST-NOTE-20260811"
    _assert_code(
        "USER_DERIVED_SOURCE_REQUIRED",
        validate_import_manifest_document,
        manifest,
        observation,
    )

    manifest["sources"][0]["source_type"] = "ANALYST_NOTE"
    assert validate_import_manifest_document(manifest, observation).passed


def test_manifest_source_set_paths_and_prospective_clocks_fail_closed() -> None:
    observation = _ready_observation()
    missing_source = _ready_manifest()
    missing_source["sources"] = []
    _assert_code(
        "REQUIRED_VALUE_MISSING",
        validate_import_manifest_document,
        missing_source,
        observation,
    )

    different_source = _ready_manifest()
    different_source["sources"][0]["source_id"] = "EDGE-LOBS-SRC-OTHER"
    _assert_code(
        "SOURCE_ID_SET_MISMATCH",
        validate_import_manifest_document,
        different_source,
        observation,
    )

    escaped = _ready_manifest()
    escaped["sources"][0]["path"] = "../trade-lab-2026-08-11.pdf"
    _assert_code(
        "PATH_ESCAPE_FORBIDDEN",
        validate_import_manifest_document,
        escaped,
        observation,
    )

    future = _ready_manifest()
    future["sources"][0]["source_publication_timestamp"] = (
        "2026-08-11T07:11:00+02:00"
    )
    _assert_code(
        "SOURCE_PUBLICATION_AFTER_INFORMATION_CUTOFF",
        validate_import_manifest_document,
        future,
        observation,
    )

    future_date = _ready_manifest()
    future_date["sources"][0]["source_publication_timestamp"] = None
    future_date["sources"][0]["source_publication_date"] = "2026-08-12"
    _assert_code(
        "SOURCE_PUBLICATION_AFTER_INFORMATION_CUTOFF",
        validate_import_manifest_document,
        future_date,
        observation,
    )

    false_prospective = _ready_manifest()
    false_prospective["sources"][0]["historical_reconstruction"] = True
    _assert_code(
        "PROSPECTIVE_PROVENANCE_INVALID",
        validate_import_manifest_document,
        false_prospective,
        observation,
    )


def test_later_article_content_cannot_be_attached_to_earlier_batch() -> None:
    observation = _ready_observation()
    manifest = _ready_manifest()
    source = manifest["sources"][0]
    source.update(
        {
            "source_type": "WEB_CAPTURE",
            "source_name": "Investing.com",
            "source_title": (
                "Asian stocks mixed as Korea gains, China slips; "
                "RBA decision in focus"
            ),
            "source_original_filename": "investing-article-capture.html",
            "path": "investing-article-capture.html",
            "source_identity": "INVESTING-ARTICLE-20260811",
            "source_publication_timestamp": "2026-08-11T07:11:00+02:00",
            "source_publication_date": "2026-08-11",
        }
    )
    _assert_code(
        "SOURCE_PUBLICATION_AFTER_INFORMATION_CUTOFF",
        validate_import_manifest_document,
        manifest,
        observation,
    )


def test_later_source_capture_is_valid_only_for_retrospective_reconstruction() -> None:
    retrospective_observation = _ready_observation()
    retrospective_observation["capture_mode"] = "RETROSPECTIVE"
    retrospective_observation["recorded_at"] = "2026-08-12T09:00:00+02:00"
    retrospective_observation["market"][0]["capture_mode"] = "RETROSPECTIVE"

    retrospective_manifest = _ready_manifest()
    retrospective_manifest["capture_mode"] = "RETROSPECTIVE"
    retrospective_manifest["sources"][0]["capture_mode"] = "RETROSPECTIVE"
    retrospective_manifest["sources"][0]["historical_reconstruction"] = True
    retrospective_manifest["sources"][0]["contemporaneous_capture_attested"] = False
    retrospective_manifest["sources"][0]["source_capture_timestamp"] = (
        "2026-08-12T08:00:00+02:00"
    )
    assert validate_import_manifest_document(
        retrospective_manifest, retrospective_observation
    ).passed

    prospective_observation = _ready_observation()
    prospective_manifest = _ready_manifest()
    prospective_manifest["sources"][0]["source_capture_timestamp"] = (
        "2026-08-12T08:00:00+02:00"
    )
    _assert_code(
        "SOURCE_CAPTURE_AFTER_INFORMATION_CUTOFF",
        validate_import_manifest_document,
        prospective_manifest,
        prospective_observation,
    )


def test_published_schema_documents_are_strict_json_objects() -> None:
    root = Path(__file__).resolve().parents[1]
    schemas = root / "observations" / "leadership_rotation" / "schemas"
    names = {
        "leadership_observation_batch.v1.schema.json",
        "leadership_import_manifest.v1.schema.json",
    }
    assert {path.name for path in schemas.glob("*.schema.json")} >= names
    for name in names:
        document = load_json_object(schemas / name)
        assert document["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert document["additionalProperties"] is False
        json.dumps(document, allow_nan=False)
