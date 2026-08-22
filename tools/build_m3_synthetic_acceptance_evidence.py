"""Build the retained Milestone 3 synthetic acceptance artifact once."""

from __future__ import annotations

import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from edge_mdm.pipeline import build_daily_slice, load_daily_slice_request
from edge_mdm.release import materialise_candidate, verify_materialised_candidate
from edge_mdm.source import verify_mdm_snapshot
from tests.fixture_factory import build_canonical_parquet_fixture


def main() -> int:
    evidence_root = REPOSITORY_ROOT / "artifacts" / "milestone3" / "synthetic_acceptance"
    evidence_root.mkdir(parents=True, exist_ok=False)
    source_bundle = build_canonical_parquet_fixture(evidence_root / "source")
    snapshot = verify_mdm_snapshot(
        source_bundle.manifest_path,
        source_bundle.root,
        allow_test_only=True,
    )
    request = load_daily_slice_request(
        REPOSITORY_ROOT / "config" / "mandatory_daily_slice_policy.test.v1.json"
    )
    build = build_daily_slice(snapshot, request)
    artifact = materialise_candidate(
        build,
        repository_root=REPOSITORY_ROOT,
        output_root=evidence_root / "feature_ready",
        builder_id="EDGE-M3-AUTOMATED-ACCEPTANCE",
    )
    verified_manifest, _ = verify_materialised_candidate(
        artifact, repository_root=REPOSITORY_ROOT
    )
    summary = {
        "classification": "TEST_ONLY_NON_PRODUCTION",
        "contains_empirical_market_data": False,
        "production_use_permitted": False,
        "source_manifest": str(source_bundle.manifest_path.relative_to(REPOSITORY_ROOT)),
        "artifact_manifest": str(artifact.manifest_path.relative_to(REPOSITORY_ROOT)),
        "artifact_manifest_sha256": artifact.manifest_sha256,
        "candidate_disk_verification": "PASS",
        "materialized_datasets": verified_manifest["materialized_datasets"],
        "build": build.summary(),
        "mandatory_checks": [
            check.as_dict() for check in build.validation_report.checks
        ],
    }
    (evidence_root / "acceptance_summary.json").write_text(
        json.dumps(summary, ensure_ascii=True, allow_nan=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
