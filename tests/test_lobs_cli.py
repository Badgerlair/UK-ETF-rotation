"""Focused command-boundary tests for ``python -m edge_lobs``.

These tests use provenance-free schema templates or an empty ledger.  They do
not create raw source evidence or claim that a template is import-admissible.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

from edge_lobs.cli import main
from edge_lobs.jsonio import canonical_json_bytes, load_json_object
from edge_lobs.ledger import LedgerPaths
from edge_mdm.fingerprint import sha256_bytes


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _draft_observation() -> dict[str, Any]:
    return {
        "schema_version": "edge.leadership_observation_batch.v1",
        "observation_batch_id": "EDGE-LOBS-20260811-CLI-TEMPLATE",
        "observation_date": "2026-08-11",
        "information_cutoff_timestamp": None,
        "information_cutoff_timezone": None,
        "capture_mode": "PROSPECTIVE",
        "recorded_at": None,
        "source_ids": [],
        "extractor": {
            "actor_type": "USER",
            "actor_id": "CLI-TEST-USER",
            "method": "SCHEMA_TEMPLATE",
            "version": "1",
        },
        "validation_status": "AWAITING_RAW_SOURCES_AND_PROVENANCE",
        "supersedes_batch_id": None,
        "market": [],
        "instruments": [],
        "groups": [],
        "stocks": [],
        "futures_snapshot": [],
        "macro_context": [],
        "notes": "Provenance-free schema template; not import-admissible.",
    }


def _template_manifest() -> dict[str, Any]:
    return {
        "schema_version": "edge.leadership_import_manifest.v1",
        "observation_batch_id": "EDGE-LOBS-20260811-CLI-TEMPLATE",
        "observation_path": None,
        "capture_mode": "PROSPECTIVE",
        "validation_status": "AWAITING_RAW_SOURCES_AND_PROVENANCE",
        "sources": [],
        "notes": "Provenance-free schema template; not import-admissible.",
    }


def _invoke(capsys: pytest.CaptureFixture[str], argv: list[str]) -> tuple[int, dict]:
    code = main(argv)
    captured = capsys.readouterr()
    assert captured.err == ""
    return code, json.loads(captured.out)


def test_validate_draft_requires_explicit_flag_and_stays_non_authoritative(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    observation_path = tmp_path / "observation_batch.json"
    _write_json(observation_path, _draft_observation())

    blocked_code, blocked = _invoke(
        capsys, ["validate", str(observation_path)]
    )
    assert blocked_code == 1
    assert blocked["state"] == "FAILED_CLOSED"
    assert blocked["error_code"] == "DRAFT_NOT_IMPORT_ADMISSIBLE"

    accepted_code, accepted = _invoke(
        capsys, ["validate", str(observation_path), "--allow-draft"]
    )
    assert accepted_code == 0
    assert accepted["document_type"] == "OBSERVATION_BATCH"
    assert accepted["state"] == "DRAFT_STRUCTURALLY_ACCEPTED_NON_AUTHORITATIVE"
    assert accepted["passed"] is True
    assert accepted["hard_blocker_count"] == 0


def test_validate_null_path_manifest_template_uses_explicit_observation_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository = tmp_path / "repository"
    template_root = repository / "observations" / "leadership_rotation" / "inbox"
    observation_path = template_root / "observation_batch.json"
    manifest_path = template_root / "import_manifest.json"
    _write_json(observation_path, _draft_observation())
    _write_json(manifest_path, _template_manifest())

    forbidden_code, forbidden = _invoke(
        capsys,
        [
            "validate-manifest",
            str(manifest_path),
            "--repository-root",
            str(repository),
            "--observation",
            str(observation_path),
        ],
    )
    assert forbidden_code == 1
    assert forbidden["error_code"] == "OBSERVATION_OVERRIDE_FORBIDDEN"

    accepted_code, accepted = _invoke(
        capsys,
        [
            "validate-manifest",
            str(manifest_path),
            "--repository-root",
            str(repository),
            "--allow-template",
            "--observation",
            str(observation_path),
        ],
    )
    assert accepted_code == 0
    assert accepted["document_type"] == "IMPORT_MANIFEST"
    assert accepted["state"] == (
        "TEMPLATE_STRUCTURALLY_ACCEPTED_NON_AUTHORITATIVE"
    )
    assert accepted["passed"] is True


def test_mdm_status_reports_repository_governance_blockers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = Path(__file__).resolve().parents[1]

    code, status = _invoke(
        capsys, ["mdm-status", "--repository-root", str(repository)]
    )

    assert code == 2
    assert status["production_implementation_ready"] is False
    assert status["production_use_permitted"] is False
    assert status["mdm_capability_gate"] == "BLOCKED"
    assert status["population_time_contract"] == "UNRATIFIED"
    assert status["production_scope_status"] == "NO_APPROVED_SCOPE"
    assert status["production_release_authority"] == "NOT_CONFIGURED"
    assert set(status["blockers"]) >= {
        "MDM_CAPABILITY_GATE_BLOCKED",
        "POPULATION_TIME_CONTRACT_UNRATIFIED",
        "NO_APPROVED_PRODUCTION_SCOPE",
        "PRODUCTION_RELEASE_AUTHORITY_NOT_READY",
    }


def test_empty_ledger_verifies_and_rebuilds_non_authoritative_index(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()

    verify_code, verified = _invoke(
        capsys, ["verify-ledger", "--repository-root", str(repository)]
    )
    assert verify_code == 0
    assert verified == {
        "batch_count": 0,
        "batches": [],
        "register_sha256": sha256_bytes(b""),
        "schema_version": "edge.leadership_ledger.v1",
        "state": "VERIFIED",
    }
    paths = LedgerPaths.from_repository(repository)
    assert not paths.ledger_root.exists()

    rebuild_code, index = _invoke(
        capsys, ["rebuild-index", "--repository-root", str(repository)]
    )
    assert rebuild_code == 0
    assert index["schema_version"] == "edge.leadership_ledger_index.v1"
    assert index["batch_count"] == 0
    assert index["batches"] == []
    assert index["register_sha256"] == sha256_bytes(b"")
    assert load_json_object(paths.index_path) == index


def test_module_entrypoint_routes_to_fail_closed_empty_ledger_verifier(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    project_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    source_root = str(project_root / "src")
    prior_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_root
        if not prior_pythonpath
        else source_root + os.pathsep + prior_pythonpath
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "edge_lobs",
            "verify-ledger",
            "--repository-root",
            str(repository),
        ],
        cwd=project_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    result = json.loads(completed.stdout)
    assert result["state"] == "VERIFIED"
    assert result["batch_count"] == 0
