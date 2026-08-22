"""Exact replay proof in two independent Python interpreter processes."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


_CHILD = r"""
import json
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()
from tests.fixture_factory import build_canonical_parquet_fixture
from edge_mdm.pipeline import build_daily_slice, load_daily_slice_request
from edge_mdm.release import materialise_candidate
from edge_mdm.source import verify_mdm_snapshot

bundle = build_canonical_parquet_fixture(destination / "source")
snapshot = verify_mdm_snapshot(bundle.manifest_path, bundle.root, allow_test_only=True)
request = load_daily_slice_request(root / "config" / "mandatory_daily_slice_policy.test.v1.json")
build = build_daily_slice(snapshot, request)
artifact = materialise_candidate(
    build,
    repository_root=root,
    output_root=destination / "output",
    builder_id="REPRO-BUILDER",
)
print(json.dumps({
    "artifact_id": artifact.artifact_id,
    "logical_fingerprints": dict(build.fingerprints),
    "replay_fingerprints": dict(build.replay_fingerprints),
    "file_hashes": {
        name: descriptor["sha256"]
        for name, descriptor in artifact.manifest["files"].items()
    },
}, sort_keys=True))
"""


def _run(destination: Path) -> dict[str, object]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(REPOSITORY_ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-c", _CHILD, str(REPOSITORY_ROOT), str(destination)],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return json.loads(completed.stdout)


def test_two_fresh_processes_produce_identical_logical_and_physical_results(
    tmp_path: Path,
) -> None:
    first = _run(tmp_path / "first")
    second = _run(tmp_path / "second")
    assert first == second
    assert first["logical_fingerprints"] == first["replay_fingerprints"]
