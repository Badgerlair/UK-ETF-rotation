"""Positive and negative tests through the real production-shaped boundary."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import duckdb
import pytest

from edge_mdm.pipeline import DailySliceRequest, PipelineError, build_daily_slice
from edge_mdm.fingerprint import canonical_json_bytes, sha256_bytes, sha256_file
from edge_mdm.release import (
    ReleaseError,
    approve_production_release,
    materialise_candidate,
    verify_materialised_candidate,
)
from edge_mdm.source import SourceValidationError, verify_mdm_snapshot
from edge_mdm.scope import (
    ProductionScopeApproval,
    ScopeApprovalError,
    assert_repository_production_gate_open,
)
from tests.fixture_factory import build_canonical_parquet_fixture


def _request(
    *,
    use_mode: str = "TEST_ONLY_VALIDATION",
    request_id: str = "EDGE-M3-TEST-001",
) -> DailySliceRequest:
    return DailySliceRequest(
        request_id=request_id,
        universe_id="EDGE-PRIMARY-EQUITY",
        exchange_ids=("XEQ",),
        security_types=("COMMON_STOCK",),
        currencies=("USD",),
        start_session="2024-03-08",
        end_session="2024-03-18",
        population_time_contract_version="PTC-TEST-001",
        calendar_policy_version="CAL-TEST-001",
        universe_policy_version="UNIV-TEST-001",
        corporate_action_policy_version="CA-TEST-001",
        point_in_time_join_version="PIT-TEST-001",
        use_mode=use_mode,
    )


def _verified(tmp_path: Path, mutation: str | None = None):
    bundle = build_canonical_parquet_fixture(tmp_path, mutations=mutation)
    return bundle, verify_mdm_snapshot(
        bundle.manifest_path, bundle.root, allow_test_only=True
    )


def _scope_for(snapshot, request: DailySliceRequest) -> ProductionScopeApproval:
    return ProductionScopeApproval(
        approval_id="SELF-ASSERTED-SCOPE",
        status="APPROVED",
        authorisation_scope_id="EDGE-M3-SYNTHETIC-SAFETY-001",
        capability_audit_id="EDGE-MDM-AUDIT-2026-08-03-001",
        capability_gate_status="READY",
        population_time_contract_version=request.population_time_contract_version,
        population_time_contract_status="RATIFIED",
        allowed_exchange_ids=("XEQ",),
        allowed_security_types=("COMMON_STOCK",),
        allowed_currencies=("USD",),
        earliest_session="2024-03-08",
        latest_session="2024-03-18",
        approved_snapshot_ids=("MDM-FIXTURE-001",),
        source_manifest_sha256=snapshot.manifest_sha256,
        source_version=snapshot.manifest.source_version,
        consistency_token=snapshot.manifest.consistency_token,
        authorised_mdm_root=str(snapshot.authorised_mdm_root),
        request_sha256=sha256_bytes(canonical_json_bytes(request.as_dict())),
    )


def test_strict_parquet_boundary_to_feature_ready_artifact(tmp_path: Path) -> None:
    bundle, snapshot = _verified(tmp_path)
    build = build_daily_slice(snapshot, _request())

    assert build.validation_report.state == "TEST_ADMISSIBLE_NON_PRODUCTION"
    assert build.validation_report.hard_blocker_count == 0
    assert all(check.status == "PASS" for check in build.validation_report.checks)
    assert build.fingerprints == build.replay_fingerprints
    assert len(build.panel_rows) == 14
    assert len(build.return_rows) == 14
    assert build.join_audit.matched_rows == 13
    assert build.join_audit.terminal_missing_bar_rows == 1

    by_key = {
        (row["session_date"], row["security_id"]): row for row in build.return_rows
    }
    assert by_key[("2024-03-12", "S1")]["price_return_1d"] == "0.020000000000"
    assert by_key[("2024-03-12", "S1")]["split_consistent_volume"] == "1100.000000000000"
    assert by_key[("2024-03-15", "S1")]["total_return_1d"] == "0.000000000000"
    assert by_key[("2024-03-15", "S3")]["terminal_return"] == "-0.800000000000"

    artifact = materialise_candidate(
        build,
        repository_root=Path.cwd(),
        output_root=tmp_path / "artifacts",
        builder_id="TEST-BUILDER",
    )
    assert artifact.root.is_dir()
    assert artifact.production_use_permitted is False
    assert artifact.manifest["artifact_state"] == "TEST_EVIDENCE_NON_PRODUCTION"
    assert (artifact.root / "observable_panel.parquet").is_file()
    with pytest.raises(ReleaseError, match="NON_PRODUCTION_ARTIFACT"):
        approve_production_release(
            artifact,
            repository_root=Path.cwd(),
            register_path=tmp_path / "release-register.jsonl",
            reviewer_id="TEST-REVIEWER",
            review_evidence_id="TEST-REVIEW-001",
        )
    assert bundle.manifest["source_kind"] == "TEST_ONLY_NON_PRODUCTION"


def test_test_only_snapshot_is_rejected_without_explicit_opt_in(tmp_path: Path) -> None:
    bundle = build_canonical_parquet_fixture(tmp_path)
    with pytest.raises(SourceValidationError) as captured:
        verify_mdm_snapshot(bundle.manifest_path, bundle.root)
    assert captured.value.code == "SOURCE_NOT_AUTHORISED_FOR_PRODUCTION"


def test_test_only_snapshot_cannot_execute_a_production_request(tmp_path: Path) -> None:
    _, snapshot = _verified(tmp_path)
    with pytest.raises(PipelineError) as captured:
        build_daily_slice(snapshot, _request(use_mode="PRODUCTION_RESEARCH"))
    assert captured.value.code == "PRODUCTION_GATE_BLOCKED"
    assert "protected production release authority is not READY" in captured.value.message


def test_caller_created_scope_cannot_override_canonical_blocked_gate(
    tmp_path: Path,
) -> None:
    _, snapshot = _verified(tmp_path)
    production_request = _request(use_mode="PRODUCTION_RESEARCH")
    asserted_scope = _scope_for(snapshot, production_request)
    with pytest.raises(PipelineError) as captured:
        build_daily_slice(
            snapshot,
            production_request,
            production_scope=asserted_scope,
        )
    assert captured.value.code == "PRODUCTION_GATE_BLOCKED"


def test_scope_approval_binds_exact_source_root_manifest_and_request(
    tmp_path: Path,
) -> None:
    _, snapshot = _verified(tmp_path)
    request = _request()
    scope = _scope_for(snapshot, request)
    scope.assert_authorised(snapshot, request)
    assert len(scope.content_sha256) == 64

    broadened = replace(request, universe_id="DIFFERENT-UNIVERSE")
    with pytest.raises(ScopeApprovalError, match="exact request"):
        scope.assert_authorised(snapshot, broadened)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("source_manifest_sha256", "0" * 64, "manifest content"),
        ("source_version", "different-source-version", "source version"),
        ("consistency_token", "different-consistency-token", "consistency token"),
    ],
)
def test_scope_approval_rejects_each_source_binding_drift(
    tmp_path: Path,
    field: str,
    replacement: str,
    message: str,
) -> None:
    _, snapshot = _verified(tmp_path)
    request = _request()
    scope = replace(_scope_for(snapshot, request), **{field: replacement})
    with pytest.raises(ScopeApprovalError, match=message):
        scope.assert_authorised(snapshot, request)


def test_scope_approval_rejects_authorised_root_drift(tmp_path: Path) -> None:
    _, snapshot = _verified(tmp_path / "source")
    request = _request()
    different_root = tmp_path / "different-mdm-root"
    different_root.mkdir()
    scope = replace(
        _scope_for(snapshot, request), authorised_mdm_root=str(different_root)
    )
    with pytest.raises(ScopeApprovalError, match="authorised MDM root"):
        scope.assert_authorised(snapshot, request)


def test_canonical_scope_register_binds_id_to_exact_scope_hash(tmp_path: Path) -> None:
    _, snapshot = _verified(tmp_path / "source")
    request = _request()
    scope = _scope_for(snapshot, request)
    repository = tmp_path / "repository"
    config = repository / "config"
    config.mkdir(parents=True)
    records = {
        "mdm_capability_audit.v1.json": {
            "schema_version": "edge.mdm_capability_audit.v1",
            "audit_id": scope.capability_audit_id,
            "production_gate": "READY",
        },
        "population_time_contract.v1.json": {
            "schema_version": "edge.population_time_contract.v1",
            "contract_version": scope.population_time_contract_version,
            "status": "RATIFIED",
            "production_use_permitted": True,
        },
        "production_scope_status.v1.json": {
            "schema_version": "edge.production_scope_status.v1",
            "status": "APPROVED_SCOPES_AVAILABLE",
            "approved_production_scopes": [
                {
                    "approval_id": scope.approval_id,
                    "scope_sha256": scope.content_sha256,
                }
            ],
        },
        "production_release_authority.v1.json": {
            "schema_version": "edge.production_release_authority.v1",
            "status": "READY",
            "production_use_permitted": True,
        },
    }
    for filename, value in records.items():
        (config / filename).write_text(
            json.dumps(value, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    assert_repository_production_gate_open(scope, repository_root=repository)
    changed = replace(scope, latest_session="2024-03-19")
    with pytest.raises(ScopeApprovalError, match="exact content hash"):
        assert_repository_production_gate_open(changed, repository_root=repository)


def test_production_build_reverifies_paths_instead_of_trusting_forged_handle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # This ephemeral adversarial fixture contains no empirical data and is never
    # materialised or released. Production classification only exercises the
    # exact fail-closed handle re-verification branch.
    bundle = build_canonical_parquet_fixture(tmp_path / "source")
    manifest = json.loads(bundle.manifest_path.read_text(encoding="utf-8"))
    manifest["source_kind"] = "MDM_PRODUCTION_SNAPSHOT"
    manifest["authorisation_status"] = "AUTHORISED_FOR_PROJECT_EDGE_RESEARCH"
    bundle.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    genuine = verify_mdm_snapshot(bundle.manifest_path, bundle.root)
    original = genuine.table("daily_observations")
    alternate = bundle.root / "forged_daily_observations.parquet"
    with duckdb.connect(database=":memory:") as connection:
        connection.execute("SET threads = 1")
        connection.execute("SET TimeZone = 'UTC'")
        connection.read_parquet(str(original.path)).create_view("genuine_observations")
        connection.execute(
            "COPY (SELECT * REPLACE "
            "(CAST(close + 100 AS DECIMAL(18,6)) AS close) "
            "FROM genuine_observations) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)",
            [str(alternate)],
        )
    forged_table = replace(
        original,
        path=alternate,
        verified_sha256=sha256_file(alternate),
        verified_logical_sha256="f" * 64,
    )
    forged = replace(
        genuine,
        tables=tuple(
            forged_table if table.manifest.logical_name == "daily_observations" else table
            for table in genuine.tables
        ),
    )
    request = _request(use_mode="PRODUCTION_RESEARCH")
    scope = _scope_for(genuine, request)
    monkeypatch.setattr(
        "edge_mdm.pipeline.assert_repository_production_gate_open",
        lambda *args, **kwargs: None,
    )

    build = build_daily_slice(forged, request, production_scope=scope)
    assert build.snapshot.table("daily_observations").path == original.path
    row = next(
        row
        for row in build.panel_rows
        if row["session_date"] == "2024-03-11" and row["security_id"] == "S1"
    )
    assert row["close"] == "100.000000"


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("wrong_hash", "TABLE_HASH_MISMATCH"),
        ("wrong_row_count", "TABLE_ROW_COUNT_MISMATCH"),
        ("wrong_physical_type", "TABLE_COLUMN_TYPE_MISMATCH"),
        ("mixed_vintage", "TABLE_VINTAGE_MISMATCH"),
        ("outcome_column", "TABLE_SCHEMA_COLUMNS_MISMATCH"),
        ("mutable_snapshot_id", "MANIFEST_CONTRACT_INVALID"),
        ("path_escape", "MANIFEST_CONTRACT_INVALID"),
    ],
)
def test_strict_source_integrity_mutations_fail_closed(
    tmp_path: Path, mutation: str, expected_code: str
) -> None:
    bundle = build_canonical_parquet_fixture(tmp_path, mutations=mutation)
    with pytest.raises(SourceValidationError) as captured:
        verify_mdm_snapshot(bundle.manifest_path, bundle.root, allow_test_only=True)
    assert captured.value.code == expected_code


@pytest.mark.parametrize(
    ("mutation", "failure_kind", "expected_code"),
    [
        ("future_bar", "report", "TYPED_MISSINGNESS"),
        ("non_session_bar", "report", "DAILY_OBSERVATIONS"),
        ("duplicate_bar", "exception", "SCIENTIFIC_TRANSFORM_FAILED"),
        ("ambiguous_identity", "report", "STABLE_IDENTITY"),
        ("missing_terminal", "report", "CORPORATE_ACTIONS"),
        ("late_action", "report", "CORPORATE_ACTIONS"),
    ],
)
def test_scientific_mutations_cannot_become_admissible(
    tmp_path: Path, mutation: str, failure_kind: str, expected_code: str
) -> None:
    _, snapshot = _verified(tmp_path, mutation)
    if failure_kind == "exception":
        with pytest.raises(PipelineError) as captured:
            build_daily_slice(snapshot, _request())
        assert captured.value.code == expected_code
        return
    build = build_daily_slice(snapshot, _request())
    assert build.validation_report.state == "INADMISSIBLE"
    assert build.validation_report.hard_blocker_count > 0
    check = next(
        result for result in build.validation_report.checks if result.code == expected_code
    )
    assert check.status == "FAIL"


def test_source_table_change_after_verification_is_detected(tmp_path: Path) -> None:
    bundle, snapshot = _verified(tmp_path)
    table = bundle.table_path("daily_observations")
    table.write_bytes(table.read_bytes() + b"changed")
    with pytest.raises(SourceValidationError) as captured:
        snapshot.assert_unchanged()
    assert captured.value.code == "SOURCE_CHANGED_AFTER_VERIFICATION"


def test_source_manifest_change_after_verification_is_detected(tmp_path: Path) -> None:
    bundle, snapshot = _verified(tmp_path)
    bundle.manifest_path.write_text(
        bundle.manifest_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(SourceValidationError) as captured:
        snapshot.assert_unchanged()
    assert captured.value.code == "MANIFEST_CHANGED_AFTER_VERIFICATION"


def test_arbitrary_policy_identifier_is_not_executable() -> None:
    with pytest.raises(ValueError, match="unsupported policy bundle"):
        replace(_request(), calendar_policy_version="CAL-CALLER-DEFINED")


def test_reversed_physical_input_has_identical_logical_outputs(tmp_path: Path) -> None:
    _, ordered = _verified(tmp_path / "ordered")
    _, reversed_snapshot = _verified(tmp_path / "reversed", "reversed_input")
    first = build_daily_slice(ordered, _request())
    second = build_daily_slice(reversed_snapshot, _request())
    assert first.fingerprints == second.fingerprints


def test_out_of_range_action_correction_supersedes_in_range_revision(
    tmp_path: Path,
) -> None:
    _, snapshot = _verified(tmp_path, "action_revision_out_of_range")
    build = build_daily_slice(snapshot, _request())
    assert build.validation_report.state == "TEST_ADMISSIBLE_NON_PRODUCTION"
    row = next(
        row
        for row in build.return_rows
        if row["session_date"] == "2024-03-12" and row["security_id"] == "S1"
    )
    assert row["split_multiplier"] == "1.000000000000"
    assert row["price_return_1d"] == "-0.490000000000"
    panel = next(
        row
        for row in build.panel_rows
        if row["session_date"] == "2024-03-12" and row["security_id"] == "S1"
    )
    assert panel["action_state"] == "NONE"


def test_latest_bar_revision_available_by_cutoff_is_selected(tmp_path: Path) -> None:
    _, snapshot = _verified(tmp_path, "bar_revision")
    build = build_daily_slice(snapshot, _request())
    assert build.validation_report.state == "TEST_ADMISSIBLE_NON_PRODUCTION"
    row = next(
        row
        for row in build.panel_rows
        if row["session_date"] == "2024-03-11" and row["security_id"] == "S1"
    )
    assert row["close"] == "101.000000"
    assert row["observation_record_id"] == "OBS-L1-2024-03-11-REV2"


def test_future_bar_revision_is_retained_but_not_joined(tmp_path: Path) -> None:
    _, snapshot = _verified(tmp_path, "bar_future_revision")
    build = build_daily_slice(snapshot, _request())
    assert build.validation_report.state == "TEST_ADMISSIBLE_NON_PRODUCTION"
    row = next(
        row
        for row in build.panel_rows
        if row["session_date"] == "2024-03-11" and row["security_id"] == "S1"
    )
    assert row["close"] == "100.000000"
    assert row["observation_record_id"] == "OBS-L1-2024-03-11"
    assert build.join_audit.rejected_not_available == 1
    artifact = materialise_candidate(
        build,
        repository_root=Path.cwd(),
        output_root=tmp_path / "artifacts",
        builder_id="TEST-BUILDER",
    )
    verify_materialised_candidate(artifact, repository_root=Path.cwd())


def test_future_action_revision_is_retained_without_rewriting_history(
    tmp_path: Path,
) -> None:
    _, snapshot = _verified(tmp_path, "future_action_revision")
    build = build_daily_slice(snapshot, _request())
    assert build.validation_report.state == "TEST_ADMISSIBLE_NON_PRODUCTION"
    row = next(
        row
        for row in build.return_rows
        if row["session_date"] == "2024-03-15" and row["security_id"] == "S1"
    )
    assert row["action_record_ids"] == "ACT-DIV-001"
    assert row["total_return_1d"] == "0.000000000000"


def test_action_currency_mismatch_is_inadmissible(tmp_path: Path) -> None:
    _, snapshot = _verified(tmp_path, "action_currency_mismatch")
    build = build_daily_slice(snapshot, _request())
    assert build.validation_report.state == "INADMISSIBLE"
    action_check = next(
        check for check in build.validation_report.checks if check.code == "CORPORATE_ACTIONS"
    )
    assert "RETURN_ROW_QUARANTINED" in action_check.error_codes


@pytest.mark.parametrize(
    ("mutation", "expected_check", "expected_error"),
    [
        ("unsupported_complex_action", "CORPORATE_ACTIONS", "RETURN_ROW_QUARANTINED"),
        ("terminal_bar_conflict", "CORPORATE_ACTIONS", "RETURN_ROW_QUARANTINED"),
        (
            "compound_terminal_action",
            "CORPORATE_ACTIONS",
            "RETURN_ROW_QUARANTINED",
        ),
        (
            "action_listing_drift",
            "CORPORATE_ACTIONS",
            "ACTION_REVISION_LISTING_CHANGED",
        ),
        ("late_cutoff", "TRADING_CALENDAR", "CALENDAR_CUTOFF_POLICY_MISMATCH"),
        (
            "orphan_membership",
            "HISTORICAL_UNIVERSE",
            "UNIVERSE_LISTING_IDENTITY_UNRESOLVED",
        ),
        ("unknown_lifecycle", "STABLE_IDENTITY", "UNKNOWN_LIFECYCLE_STATE"),
        (
            "listing_security_drift",
            "STABLE_IDENTITY",
            "LISTING_SECURITY_ID_DRIFT",
        ),
    ],
)
def test_additional_scientific_sentinels_fail_closed(
    tmp_path: Path,
    mutation: str,
    expected_check: str,
    expected_error: str,
) -> None:
    _, snapshot = _verified(tmp_path, mutation)
    build = build_daily_slice(snapshot, _request())
    assert build.validation_report.state == "INADMISSIBLE"
    check = next(
        result for result in build.validation_report.checks if result.code == expected_check
    )
    assert expected_error in check.error_codes


def test_null_cash_amount_fails_with_typed_transform_error(tmp_path: Path) -> None:
    _, snapshot = _verified(tmp_path, "null_cash_amount")
    with pytest.raises(PipelineError) as captured:
        build_daily_slice(snapshot, _request())
    assert captured.value.code == "SCIENTIFIC_TRANSFORM_FAILED"
    assert "cash_amount is required" in captured.value.message


def test_listing_currency_drift_breaks_return_continuity(tmp_path: Path) -> None:
    _, snapshot = _verified(tmp_path, "listing_currency_drift")
    request = replace(_request(), currencies=("USD", "EUR"))
    build = build_daily_slice(snapshot, request)
    assert build.validation_report.state == "INADMISSIBLE"
    identity = next(
        check
        for check in build.validation_report.checks
        if check.code == "STABLE_IDENTITY"
    )
    actions = next(
        check
        for check in build.validation_report.checks
        if check.code == "CORPORATE_ACTIONS"
    )
    assert "LISTING_CURRENCY_DRIFT" in identity.error_codes
    assert "RETURN_ROW_QUARANTINED" in actions.error_codes
    row = next(
        row
        for row in build.return_rows
        if row["session_date"] == "2024-03-15" and row["security_id"] == "S1"
    )
    assert row["return_missing_reason"] == "CURRENCY_CONTINUITY_BREAK"
    assert row["continuity_state"] == "BREAK"


def test_halt_without_bar_is_typed_and_breaks_return_continuity(
    tmp_path: Path,
) -> None:
    _, snapshot = _verified(tmp_path, "halted_no_bar")
    build = build_daily_slice(snapshot, _request())
    assert build.validation_report.state == "TEST_ADMISSIBLE_NON_PRODUCTION"
    halted = next(
        row
        for row in build.panel_rows
        if row["session_date"] == "2024-03-14" and row["security_id"] == "S1"
    )
    assert halted["value_state"] == "HALTED_NO_BAR"
    assert halted["quality_state"] == "PASSED"
    returns = {
        (row["session_date"], row["security_id"]): row for row in build.return_rows
    }
    assert returns[("2024-03-14", "S1")]["continuity_state"] == "BREAK"
    assert returns[("2024-03-15", "S1")]["total_return_1d"] is None
    assert returns[("2024-03-15", "S1")]["continuity_state"] == "BREAK"
