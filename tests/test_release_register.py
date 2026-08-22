"""Governance-only release-register tests; no market data are used."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

import edge_mdm.release as release_module
from edge_mdm.fingerprint import canonical_json_bytes, sha256_file
from edge_mdm.pipeline import (
    DailySliceBuild,
    build_daily_slice,
    load_daily_slice_request,
)
from edge_mdm.release import (
    MaterialisedArtifact,
    ReleaseError,
    approve_production_release,
    change_production_release_state,
    materialise_candidate,
    record_failed_build_attempt,
    verify_materialised_candidate,
)
from edge_mdm.source import verify_mdm_snapshot
from tests.fixture_factory import build_canonical_parquet_fixture


def _synthetic_candidate(
    tmp_path: Path,
) -> tuple[MaterialisedArtifact, DailySliceBuild]:
    bundle = build_canonical_parquet_fixture(tmp_path / "source")
    snapshot = verify_mdm_snapshot(
        bundle.manifest_path, bundle.root, allow_test_only=True
    )
    request = load_daily_slice_request(
        Path.cwd() / "config" / "mandatory_daily_slice_policy.test.v1.json"
    )
    build = build_daily_slice(snapshot, request)
    artifact = materialise_candidate(
        build,
        repository_root=Path.cwd(),
        output_root=tmp_path / "artifacts",
        builder_id="TEST-BUILDER",
    )
    return artifact, build


def _rewrite_manifest(
    artifact: MaterialisedArtifact, manifest: dict
) -> MaterialisedArtifact:
    artifact.manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return MaterialisedArtifact(
        artifact_id=artifact.artifact_id,
        root=artifact.root,
        manifest_path=artifact.manifest_path,
        manifest_sha256=sha256_file(artifact.manifest_path),
        manifest=manifest,
    )


def _refresh_file_descriptor(manifest: dict, path: Path) -> None:
    manifest["files"][path.name] = {
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def _rewrite_observable_panel(artifact: MaterialisedArtifact, projection: str) -> Path:
    panel = artifact.root / "observable_panel.parquet"
    replacement = artifact.root / ".observable_panel.rewrite.parquet"
    with duckdb.connect(database=":memory:") as connection:
        connection.execute("SET threads = 1")
        connection.execute("SET TimeZone = 'UTC'")
        connection.read_parquet(str(panel)).create_view("source_panel")
        connection.execute(
            f"COPY (SELECT * REPLACE ({projection}) FROM source_panel) "
            "TO ? (FORMAT PARQUET, COMPRESSION ZSTD)",
            [str(replacement)],
        )
    replacement.replace(panel)
    return panel


def _governance_harness_artifact(tmp_path: Path) -> MaterialisedArtifact:
    artifact_id = "EDGE-" + "A" * 24
    root = tmp_path / artifact_id
    root.mkdir()
    payload = root / "observable_panel.parquet"
    payload.write_bytes(b"governance harness only; contains no market data\n")
    manifest = {
        "schema_version": "edge.feature_ready_artifact.v1",
        "artifact_id": artifact_id,
        "artifact_state": "READY_FOR_INDEPENDENT_REVIEW",
        "production_use_permitted": True,
        "source_kind": "MDM_PRODUCTION_SNAPSHOT",
        "source_snapshot_id": "MDM-GOVERNANCE-HARNESS-001",
        "source_manifest_sha256": "a" * 64,
        "validation_state": "ADMISSIBLE",
        "builder_id": "BUILDER-A",
        "files": {
            payload.name: {
                "sha256": sha256_file(payload),
                "bytes": payload.stat().st_size,
            }
        },
    }
    manifest_path = root / "artifact_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return MaterialisedArtifact(
        artifact_id=manifest["artifact_id"],
        root=root,
        manifest_path=manifest_path,
        manifest_sha256=sha256_file(manifest_path),
        manifest=manifest,
    )


def test_arbitrary_self_asserted_artifact_cannot_enter_release_register(
    tmp_path: Path,
) -> None:
    artifact = _governance_harness_artifact(tmp_path)
    register = tmp_path / "release-register.jsonl"

    with pytest.raises(ReleaseError) as rejected:
        approve_production_release(
            artifact,
            repository_root=Path.cwd(),
            register_path=register,
            reviewer_id="BUILDER-A",
            review_evidence_id="REVIEW-001",
        )
    assert rejected.value.code == "ARTIFACT_MANIFEST_SCHEMA_INVALID"
    assert not register.exists()


def _write_governance_release_record(register: Path, artifact_id: str) -> dict:
    body = {
        "schema_version": "edge.release_register.v1",
        "previous_record_sha256": "0" * 64,
        "artifact_id": artifact_id,
        "artifact_manifest_sha256": "b" * 64,
        "source_snapshot_id": "MDM-GOVERNANCE-HARNESS-001",
        "source_manifest_sha256": "a" * 64,
        "release_state": "RELEASED",
        "builder_id": "BUILDER-A",
        "reviewer_id": "REVIEWER-B",
        "review_evidence_id": "REVIEW-001",
        "recorded_at_utc": "2026-08-03T00:00:00Z",
    }
    from edge_mdm.fingerprint import sha256_bytes

    record = {**body, "record_sha256": sha256_bytes(canonical_json_bytes(body))}
    register.write_bytes(canonical_json_bytes(record) + b"\n")
    return record


def test_revocation_extends_the_governance_chain_without_rewriting(
    tmp_path: Path,
) -> None:
    artifact_id = "EDGE-" + "B" * 24
    register = tmp_path / "release-register.jsonl"
    released = _write_governance_release_record(register, artifact_id)

    revoked = change_production_release_state(
        repository_root=Path.cwd(),
        register_path=register,
        artifact_id=artifact_id,
        new_state="REVOKED",
        authority_id="RELEASE-AUTHORITY-C",
        reason="governance harness revocation test",
    )
    assert revoked["previous_record_sha256"] == released["record_sha256"]
    assert len(register.read_text(encoding="utf-8").splitlines()) == 2


def test_released_artifact_byte_change_is_detected(tmp_path: Path) -> None:
    bundle = build_canonical_parquet_fixture(tmp_path / "source")
    snapshot = verify_mdm_snapshot(
        bundle.manifest_path, bundle.root, allow_test_only=True
    )
    request = load_daily_slice_request(
        Path.cwd() / "config" / "mandatory_daily_slice_policy.test.v1.json"
    )
    build = build_daily_slice(snapshot, request)
    artifact = materialise_candidate(
        build,
        repository_root=Path.cwd(),
        output_root=tmp_path / "artifacts",
        builder_id="TEST-BUILDER",
    )
    (artifact.root / "observable_panel.parquet").write_bytes(b"changed\n")
    with pytest.raises(ReleaseError) as changed:
        verify_materialised_candidate(
            artifact, repository_root=Path.cwd()
        )
    assert changed.value.code in {
        "ARTIFACT_FILE_CHANGED",
        "ARTIFACT_FILE_SIZE_MISMATCH",
    }


def test_post_validation_row_mutation_cannot_be_materialised(tmp_path: Path) -> None:
    bundle = build_canonical_parquet_fixture(tmp_path / "source")
    snapshot = verify_mdm_snapshot(
        bundle.manifest_path, bundle.root, allow_test_only=True
    )
    request = load_daily_slice_request(
        Path.cwd() / "config" / "mandatory_daily_slice_policy.test.v1.json"
    )
    build = build_daily_slice(snapshot, request)
    build.panel_rows[0]["close"] = "999.000000"
    with pytest.raises(ReleaseError) as changed:
        materialise_candidate(
            build,
            repository_root=Path.cwd(),
            output_root=tmp_path / "artifacts",
            builder_id="TEST-BUILDER",
        )
    assert changed.value.code == "BUILD_CHANGED_AFTER_VALIDATION"


def test_failed_build_attempt_is_retained_without_unsafe_data(tmp_path: Path) -> None:
    error = ReleaseError("SCIENTIFIC_GATE_FAILED", "synthetic failure")
    evidence = record_failed_build_attempt(
        repository_root=Path.cwd(),
        output_root=tmp_path / "attempts",
        stage="BUILD_DAILY_SLICE",
        error=error,
        context={"request_id": "TEST-REQUEST"},
    )
    record = json.loads(evidence.read_text(encoding="utf-8"))
    assert record["error_code"] == "SCIENTIFIC_GATE_FAILED"
    assert record["context"] == {"request_id": "TEST-REQUEST"}
    assert len(record["software_source_sha256"]) == 64
    assert len(record["record_sha256"]) == 64


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_artifact_payload_file_set_mutation_is_rejected(
    tmp_path: Path, mutation: str
) -> None:
    artifact, _ = _synthetic_candidate(tmp_path)
    if mutation == "missing":
        (artifact.root / "join_audit.json").unlink()
    else:
        (artifact.root / "unexpected.txt").write_text(
            "unexpected artifact payload\n", encoding="utf-8"
        )

    with pytest.raises(ReleaseError) as rejected:
        verify_materialised_candidate(artifact, repository_root=Path.cwd())
    assert rejected.value.code == "ARTIFACT_DIRECTORY_SET_INVALID"


def test_schema_conforming_row_tampering_fails_independent_rebuild(
    tmp_path: Path,
) -> None:
    artifact, build = _synthetic_candidate(tmp_path)
    panel = _rewrite_observable_panel(
        artifact,
        "CAST(CASE WHEN close IS NULL THEN NULL ELSE close + 1 END "
        "AS DECIMAL(18,6)) AS close",
    )
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    contract = release_module._DATASET_CONTRACTS["observable_panel"]
    manifest["materialized_datasets"]["observable_panel"] = (
        release_module._parquet_profile(
            panel,
            columns=contract[1],
            types=release_module._dataset_types("observable_panel"),
            sort_keys=contract[2],
        )
    )
    _refresh_file_descriptor(manifest, panel)
    artifact = _rewrite_manifest(artifact, manifest)

    disk_manifest, _ = verify_materialised_candidate(
        artifact, repository_root=Path.cwd()
    )
    with pytest.raises(ReleaseError) as rejected:
        release_module._verify_candidate_matches_build(
            artifact,
            disk_manifest,
            build,
            repository_root=Path.cwd(),
        )
    assert rejected.value.code == "INDEPENDENT_REBUILD_MISMATCH"


def test_parquet_physical_schema_mutation_is_rejected(tmp_path: Path) -> None:
    artifact, _ = _synthetic_candidate(tmp_path)
    panel = _rewrite_observable_panel(
        artifact,
        "CAST(volume AS DOUBLE) AS volume",
    )
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    _refresh_file_descriptor(manifest, panel)
    artifact = _rewrite_manifest(artifact, manifest)

    with pytest.raises(ReleaseError) as rejected:
        verify_materialised_candidate(artifact, repository_root=Path.cwd())
    assert rejected.value.code == "ARTIFACT_PARQUET_SCHEMA_MISMATCH"


def test_supporting_evidence_mutation_is_rejected_after_hash_refresh(
    tmp_path: Path,
) -> None:
    artifact, _ = _synthetic_candidate(tmp_path)
    lineage_path = artifact.root / "lineage.json"
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    lineage["source_snapshot_id"] = "MDM-TAMPERED-SNAPSHOT"
    lineage_path.write_bytes(canonical_json_bytes(lineage) + b"\n")
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    _refresh_file_descriptor(manifest, lineage_path)
    artifact = _rewrite_manifest(artifact, manifest)

    with pytest.raises(ReleaseError) as rejected:
        verify_materialised_candidate(artifact, repository_root=Path.cwd())
    assert rejected.value.code == "ARTIFACT_LINEAGE_MISMATCH"
