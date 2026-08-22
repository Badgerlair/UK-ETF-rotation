"""Transactional and tamper-evidence tests for the observation ledger.

The fixtures are deliberately synthetic.  They exercise storage governance and
do not contain, imitate, or make claims about empirical market evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
from typing import Any

import pytest

import edge_lobs.ledger as ledger_module
from edge_lobs.errors import LobsError
from edge_lobs.jsonio import canonical_json_bytes, load_json_object
from edge_lobs.ledger import (
    LedgerPaths,
    import_observation_batch,
    rebuild_index,
    verify_ledger,
)
from edge_mdm.fingerprint import sha256_bytes, sha256_file


@dataclass(frozen=True, slots=True)
class _PreparedImport:
    batch_id: str
    observation_id: str
    source_id: str
    source_identity: str
    manifest_path: Path
    observation_path: Path
    raw_path: Path
    raw_sha256: str


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _prepare_import(
    repository: Path,
    suffix: str,
    *,
    raw_bytes: bytes | None = None,
    raw_filename: str | None = None,
    source_identity: str | None = None,
    source_id: str | None = None,
    observation_id: str | None = None,
    folder: str | None = None,
) -> _PreparedImport:
    """Create one complete, valid synthetic inbox candidate."""

    repository.mkdir(parents=True, exist_ok=True)
    rendered = suffix.upper()
    batch_id = f"EDGE-LOBS-20260811-{rendered}"
    source_id = source_id or f"SRC-20260811-{rendered}"
    source_identity = source_identity or f"SYNTHETIC-SOURCE-20260811-{rendered}"
    observation_id = observation_id or f"EDGE-LOBS-OBS-20260811-{rendered}"
    inbox = (
        repository
        / "observations"
        / "leadership_rotation"
        / "inbox"
        / (folder or suffix.casefold())
    )
    inbox.mkdir(parents=True, exist_ok=False)
    raw_filename = raw_filename or f"source-{suffix.casefold()}.txt"
    raw_path = inbox / raw_filename
    raw_path.write_bytes(
        raw_bytes if raw_bytes is not None else f"synthetic source {suffix}\n".encode()
    )
    raw_sha256 = sha256_file(raw_path)

    observation = {
        "schema_version": "edge.leadership_observation_batch.v1",
        "observation_batch_id": batch_id,
        "observation_date": "2026-08-11",
        "information_cutoff_timestamp": "2026-08-11T07:05:00+02:00",
        "information_cutoff_timezone": "Europe/Rome",
        "capture_mode": "PROSPECTIVE",
        "recorded_at": "2026-08-11T07:04:00+02:00",
        "source_ids": [source_id],
        "extractor": {
            "actor_type": "USER",
            "actor_id": "TEST-EXTRACTOR",
            "method": "synthetic governance fixture",
            "version": "1",
        },
        "validation_status": "READY_FOR_IMPORT",
        "supersedes_batch_id": None,
        "market": [
            {
                "observation_id": observation_id,
                "timestamp": "2026-08-11T06:59:00+02:00",
                "timezone": "Europe/Rome",
                "derivation_type": "SOURCE_DERIVED",
                "observation_subtype": None,
                "source_text": "Synthetic market description.",
                "source_id": source_id,
                "source_location": "synthetic line 1",
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
        "notes": "Synthetic storage-control fixture only.",
    }
    observation_path = inbox / "observation_batch.json"
    _write_json(observation_path, observation)

    manifest = {
        "schema_version": "edge.leadership_import_manifest.v1",
        "observation_batch_id": batch_id,
        "observation_path": observation_path.name,
        "capture_mode": "PROSPECTIVE",
        "validation_status": "READY_FOR_IMPORT",
        "sources": [
            {
                "source_id": source_id,
                "source_type": "TEXT",
                "source_name": "Synthetic governance source",
                "source_title": "Synthetic source fixture",
                "source_original_filename": raw_path.name,
                "source_identity": source_identity,
                "path": raw_path.name,
                "source_capture_timestamp": "2026-08-11T06:58:00+02:00",
                "source_publication_timestamp": "2026-08-11T06:30:00+02:00",
                "source_publication_date": "2026-08-11",
                "timestamp_precision": "EXACT_MINUTE",
                "timezone": "Europe/Rome",
                "capture_mode": "PROSPECTIVE",
                "historical_reconstruction": False,
                "contemporaneous_capture_attested": True,
                "expected_sha256": raw_sha256,
                "parser_version": None,
                "notes": "Synthetic storage-control fixture only.",
            }
        ],
        "notes": "Synthetic storage-control fixture only.",
    }
    manifest_path = inbox / "import_manifest.json"
    _write_json(manifest_path, manifest)
    return _PreparedImport(
        batch_id=batch_id,
        observation_id=observation_id,
        source_id=source_id,
        source_identity=source_identity,
        manifest_path=manifest_path,
        observation_path=observation_path,
        raw_path=raw_path,
        raw_sha256=raw_sha256,
    )


def _assert_single_seal(repository: Path, expected_batch_id: str) -> None:
    paths = LedgerPaths.from_repository(repository)
    assert sorted(path.name for path in paths.batches_root.iterdir()) == [
        expected_batch_id
    ]
    assert len(paths.register_path.read_text(encoding="utf-8").splitlines()) == 1


def test_import_seals_complete_bundle_and_rebuilds_derived_index(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    prepared = _prepare_import(repository, "A")

    sealed = import_observation_batch(prepared.manifest_path, repository)

    assert sealed.observation_batch_id == prepared.batch_id
    assert sealed.root == (
        repository
        / "observations"
        / "leadership_rotation"
        / "ledger"
        / "batches"
        / prepared.batch_id
    ).resolve()
    raw_copy = sealed.root / "raw" / prepared.raw_sha256
    assert raw_copy.read_bytes() == prepared.raw_path.read_bytes()
    source_manifest = load_json_object(sealed.root / "source_manifest.json")
    assert source_manifest["sources"][0]["original_hash"] == prepared.raw_sha256
    assert source_manifest["sources"][0]["storage_location"] == (
        f"raw/{prepared.raw_sha256}"
    )
    assert source_manifest["sources"][0]["byte_length"] > 0
    validation = load_json_object(sealed.root / "validation_report.json")
    assert validation["authority_source"] == "COMPUTED"
    assert validation["state"] == "VALIDATED_FOR_SEAL"
    batch_manifest = load_json_object(sealed.batch_manifest_path)
    assert batch_manifest["observation_date"] == "2026-08-11"
    assert batch_manifest["information_cutoff_timestamp"] == (
        "2026-08-11T07:05:00+02:00"
    )
    assert batch_manifest["information_cutoff_timezone"] == "Europe/Rome"

    verified = verify_ledger(repository)
    assert verified["state"] == "VERIFIED"
    assert verified["batch_count"] == 1
    assert verified["batches"][0]["observation_batch_id"] == prepared.batch_id
    sealed.index_path.unlink()
    rebuilt = rebuild_index(repository)
    assert rebuilt["batch_count"] == 1
    assert load_json_object(sealed.index_path) == rebuilt


def test_same_raw_bytes_under_different_filename_are_rejected_globally(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    first = _prepare_import(repository, "A", raw_bytes=b"identical bytes\n")
    import_observation_batch(first.manifest_path, repository)
    second = _prepare_import(
        repository,
        "B",
        raw_bytes=b"identical bytes\n",
        raw_filename="renamed-source.bin",
    )

    with pytest.raises(LobsError) as rejected:
        import_observation_batch(second.manifest_path, repository)

    assert rejected.value.code == "DUPLICATE_RAW_SOURCE_CONTENT"
    _assert_single_seal(repository, first.batch_id)
    assert not (LedgerPaths.from_repository(repository).batches_root / second.batch_id).exists()


def test_source_identity_duplicate_is_rejected_even_when_bytes_differ(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    first = _prepare_import(repository, "A", raw_bytes=b"first bytes\n")
    import_observation_batch(first.manifest_path, repository)
    second = _prepare_import(
        repository,
        "B",
        raw_bytes=b"second bytes\n",
        source_identity=first.source_identity,
    )

    with pytest.raises(LobsError) as rejected:
        import_observation_batch(second.manifest_path, repository)

    assert rejected.value.code == "DUPLICATE_SOURCE_IDENTITY"
    _assert_single_seal(repository, first.batch_id)


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("source_id", "DUPLICATE_SOURCE_ID"),
        ("observation_id", "DUPLICATE_OBSERVATION_ID"),
    ],
)
def test_existing_record_ids_are_refused(
    tmp_path: Path, field: str, code: str
) -> None:
    repository = tmp_path / "repository"
    first = _prepare_import(repository, "A", raw_bytes=b"first bytes\n")
    import_observation_batch(first.manifest_path, repository)
    kwargs = {field: getattr(first, field)}
    second = _prepare_import(
        repository,
        "B",
        raw_bytes=b"second bytes\n",
        **kwargs,
    )

    with pytest.raises(LobsError) as rejected:
        import_observation_batch(second.manifest_path, repository)

    assert rejected.value.code == code
    _assert_single_seal(repository, first.batch_id)


def test_existing_batch_id_refuses_rewrite_and_preserves_sealed_bytes(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    first = _prepare_import(repository, "A", raw_bytes=b"first bytes\n")
    sealed = import_observation_batch(first.manifest_path, repository)
    original_manifest_hash = sha256_file(sealed.batch_manifest_path)
    replacement = _prepare_import(
        repository,
        "A",
        raw_bytes=b"replacement bytes\n",
        source_identity="SYNTHETIC-REPLACEMENT-IDENTITY",
        source_id="SRC-REPLACEMENT-A",
        observation_id="EDGE-LOBS-OBS-REPLACEMENT-A",
        folder="replacement-a",
    )

    with pytest.raises(LobsError) as rejected:
        import_observation_batch(replacement.manifest_path, repository)

    assert rejected.value.code == "IMMUTABLE_BATCH_ID_COLLISION"
    assert sha256_file(sealed.batch_manifest_path) == original_manifest_hash
    _assert_single_seal(repository, first.batch_id)


def test_import_manifest_must_resolve_inside_exact_repository_inbox(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    prepared = _prepare_import(repository, "A")
    outside = repository / "outside-import-manifest.json"
    outside.write_bytes(prepared.manifest_path.read_bytes())

    with pytest.raises(LobsError) as rejected:
        import_observation_batch(outside, repository)

    assert rejected.value.code == "IMPORT_MANIFEST_OUTSIDE_INBOX"
    assert not (
        repository / "observations" / "leadership_rotation" / "ledger"
    ).exists()


def test_empty_raw_source_fails_before_any_visible_batch(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    prepared = _prepare_import(repository, "A", raw_bytes=b"")

    with pytest.raises(LobsError) as rejected:
        import_observation_batch(prepared.manifest_path, repository)

    assert rejected.value.code == "EMPTY_RAW_SOURCE"
    assert not (
        repository
        / "observations"
        / "leadership_rotation"
        / "ledger"
        / "batches"
        / prepared.batch_id
    ).exists()


def test_validation_failure_creates_no_batch_or_register(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    prepared = _prepare_import(repository, "A")
    observation = load_json_object(prepared.observation_path)
    observation["market"][0]["forward_return"] = "0.50"
    prepared.observation_path.write_bytes(canonical_json_bytes(observation) + b"\n")

    with pytest.raises(LobsError) as rejected:
        import_observation_batch(prepared.manifest_path, repository)

    assert rejected.value.code == "OUTCOME_FIELD_FORBIDDEN"
    paths = LedgerPaths.from_repository(repository)
    assert not (paths.batches_root / prepared.batch_id).exists()
    assert not paths.register_path.exists()


def test_source_set_mismatch_creates_no_visible_batch(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    prepared = _prepare_import(repository, "A")
    observation = load_json_object(prepared.observation_path)
    observation["source_ids"] = ["SRC-UNDECLARED"]
    observation["market"][0]["source_id"] = "SRC-UNDECLARED"
    prepared.observation_path.write_bytes(canonical_json_bytes(observation) + b"\n")

    with pytest.raises(LobsError) as rejected:
        import_observation_batch(prepared.manifest_path, repository)

    assert rejected.value.code == "SOURCE_ID_SET_MISMATCH"
    paths = LedgerPaths.from_repository(repository)
    assert not (paths.batches_root / prepared.batch_id).exists()
    assert not paths.register_path.exists()


def test_source_change_during_copy_removes_only_uncommitted_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    prepared = _prepare_import(repository, "A", raw_bytes=b"stable bytes\n")
    original_copy = ledger_module._copy_file_new

    def copy_then_change(source: Path, target: Path) -> None:
        original_copy(source, target)
        source.write_bytes(b"changed after copy\n")

    monkeypatch.setattr(ledger_module, "_copy_file_new", copy_then_change)
    with pytest.raises(LobsError) as rejected:
        import_observation_batch(prepared.manifest_path, repository)

    assert rejected.value.code == "SOURCE_CHANGED_DURING_IMPORT"
    paths = LedgerPaths.from_repository(repository)
    assert not (paths.batches_root / prepared.batch_id).exists()
    assert not paths.register_path.exists()
    assert not list(paths.ledger_root.glob(".edge-lobs-stage-*"))


def test_failure_after_atomic_rename_retains_excluded_orphan_for_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    prepared = _prepare_import(repository, "A")

    def fail_register_append(*args: Any, **kwargs: Any) -> dict[str, Any]:
        del args, kwargs
        raise LobsError("SYNTHETIC_REGISTER_FAILURE", "synthetic failure")

    monkeypatch.setattr(ledger_module, "_append_register", fail_register_append)
    with pytest.raises(LobsError) as rejected:
        import_observation_batch(prepared.manifest_path, repository)
    assert rejected.value.code == "SYNTHETIC_REGISTER_FAILURE"

    paths = LedgerPaths.from_repository(repository)
    orphan = paths.batches_root / prepared.batch_id
    assert orphan.is_dir()
    assert not paths.register_path.exists()
    with pytest.raises(LobsError) as excluded:
        verify_ledger(repository)
    assert excluded.value.code == "UNREGISTERED_BATCH_PRESENT"
    assert orphan.is_dir()


def test_raw_byte_tamper_is_detected_on_every_authoritative_read(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    prepared = _prepare_import(repository, "A", raw_bytes=b"raw-a\n")
    sealed = import_observation_batch(prepared.manifest_path, repository)
    (sealed.root / "raw" / prepared.raw_sha256).write_bytes(b"tampr\n")

    with pytest.raises(LobsError) as rejected:
        verify_ledger(repository)

    assert rejected.value.code == "BATCH_FILE_HASH_MISMATCH"


def test_register_record_tamper_is_detected(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    prepared = _prepare_import(repository, "A")
    import_observation_batch(prepared.manifest_path, repository)
    register_path = LedgerPaths.from_repository(repository).register_path
    record = json.loads(register_path.read_text(encoding="utf-8"))
    record["actor"] = "TAMPERED-ACTOR"
    register_path.write_bytes(canonical_json_bytes(record) + b"\n")

    with pytest.raises(LobsError) as rejected:
        verify_ledger(repository)

    assert rejected.value.code == "LEDGER_REGISTER_HASH_MISMATCH"


def test_registered_batch_missing_is_detected_bidirectionally(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    prepared = _prepare_import(repository, "A")
    sealed = import_observation_batch(prepared.manifest_path, repository)
    shutil.rmtree(sealed.root)

    with pytest.raises(LobsError) as rejected:
        verify_ledger(repository)

    assert rejected.value.code == "REGISTERED_BATCH_MISSING"


def test_expected_source_hash_mismatch_does_not_begin_transaction(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    prepared = _prepare_import(repository, "A")
    manifest = load_json_object(prepared.manifest_path)
    manifest["sources"][0]["expected_sha256"] = sha256_bytes(b"different bytes")
    prepared.manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")

    with pytest.raises(LobsError) as rejected:
        import_observation_batch(prepared.manifest_path, repository)

    assert rejected.value.code == "SOURCE_EXPECTED_HASH_MISMATCH"
    paths = LedgerPaths.from_repository(repository)
    assert not (paths.batches_root / prepared.batch_id).exists()
    assert not paths.register_path.exists()
