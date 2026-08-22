"""Structural and production-boundary tests for EDGE_M3_PIT_001."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from edge_mdm.source import SourceValidationError, verify_mdm_snapshot
from tests.fixture_factory import (
    AUTHORISATION_STATUS,
    FIXTURE_CLASSIFICATION,
    SOURCE_AUTHORITY,
    build_fixture,
    verify_fixture,
)


def test_clean_fixture_has_exact_test_only_authority_and_integrity(tmp_path: Path) -> None:
    bundle = build_fixture(tmp_path)

    assert verify_fixture(bundle.root) == ()
    assert bundle.manifest["source_authority"] == SOURCE_AUTHORITY
    assert bundle.manifest["authorisation_status"] == AUTHORISATION_STATUS
    assert bundle.manifest["classification"] == FIXTURE_CLASSIFICATION
    assert bundle.manifest["production_use_permitted"] is False
    assert bundle.manifest["contains_empirical_market_data"] is False
    assert len(bundle.table_paths) == 8

    for table_name, entry in bundle.manifest["tables"].items():
        assert entry["classification"] == FIXTURE_CLASSIFICATION
        assert len(entry["content_sha256"]) == 64
        assert len(entry["schema_fingerprint_sha256"]) == 64
        assert len(entry["canonical_rows_sha256"]) == 64
        assert entry["required_columns"] == entry["columns"]
        assert bundle.table_path(table_name).is_file()


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("wrong_source", "SOURCE_AUTHORITY_INVALID"),
        ("row_count", "DAILY_OBSERVATIONS_ROW_COUNT_MISMATCH"),
        ("hash", "DAILY_OBSERVATIONS_CONTENT_HASH_MISMATCH"),
    ],
)
def test_integrity_mutations_fail_at_fixture_intake(
    tmp_path: Path, mutation: str, expected_error: str
) -> None:
    bundle = build_fixture(tmp_path, mutations=mutation)

    assert verify_fixture(bundle.root) == (expected_error,)


@pytest.mark.parametrize(
    "mutation",
    [
        "future_bar",
        "non_session_bar",
        "ambiguous_identity",
        "missing_terminal",
        "duplicate_sector",
        "outcome_column",
        "reversed_order",
    ],
)
def test_scientific_mutations_remain_structurally_well_formed_for_boundary_tests(
    tmp_path: Path, mutation: str
) -> None:
    bundle = build_fixture(tmp_path, mutations=mutation)

    assert verify_fixture(bundle.root) == ()


def test_test_only_csv_bundle_cannot_cross_production_parquet_boundary(
    tmp_path: Path,
) -> None:
    """The safety fixture is never an admissible substitute for an MDM bundle."""

    bundle = build_fixture(tmp_path)

    with pytest.raises(SourceValidationError) as captured:
        verify_mdm_snapshot(bundle.manifest_path, tmp_path)

    assert captured.value.code == "MANIFEST_CONTRACT_INVALID"
    assert bundle.manifest["production_use_permitted"] is False

