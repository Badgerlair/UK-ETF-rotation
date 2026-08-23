"""Validate the completed UKACTIVE-A3R1 artifact set and manifest lineage."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "UKACTIVE_A3R1_SCOPE_AND_PREREGISTRATION.md",
    "UKACTIVE_A3R1_SIGNAL_REGISTRY.csv",
    "UKACTIVE_A3R1_ROTATION_POOL_MEMBERSHIP.csv",
    "UKACTIVE_A3R1_DYNAMIC_COHORT_COUNTS.csv",
    "UKACTIVE_A3R1_MULTI_HORIZON_RS.parquet",
    "UKACTIVE_A3R1_DISCRETE_RELATIVE_SEGMENTS.parquet",
    "UKACTIVE_A3R1_RS_ACCELERATION.parquet",
    "UKACTIVE_A3R1_PAIRWISE_RS_RESULTS.parquet",
    "UKACTIVE_A3R1_ROTATION_STATES.parquet",
    "UKACTIVE_A3R1_RELATIVE_LINE_FEATURES.parquet",
    "UKACTIVE_A3R1_TOP_TAIL_RESULTS.csv",
    "UKACTIVE_A3R1_FORWARD_HORIZON_DECAY.csv",
    "UKACTIVE_A3R1_GROUP_RESULTS.csv",
    "UKACTIVE_A3R1_LEADERSHIP_PERSISTENCE.csv",
    "UKACTIVE_A3R1_STATE_TRANSITIONS.csv",
    "UKACTIVE_A3R1_PARENT_RS_RESULTS.csv",
    "UKACTIVE_A3R1_TREND_QUALITY_DIAGNOSTICS.csv",
    "UKACTIVE_A3R1_OVERLAP_DIAGNOSTICS.csv",
    "UKACTIVE_A3R1_BREADTH_DIAGNOSTICS.csv",
    "UKACTIVE_A3R1_SUBPERIOD_RESULTS.csv",
    "UKACTIVE_A3R1_DEPENDENCY_TESTS.csv",
    "UKACTIVE_A3R1_PARAMETER_ROBUSTNESS.csv",
    "UKACTIVE_A3R1_STATISTICAL_INFERENCE.md",
    "UKACTIVE_A3R1_MULTIPLE_TESTING_LEDGER.csv",
    "UKACTIVE_A3R1_CORRECTNESS_TEST_RESULTS.csv",
    "UKACTIVE_A3R1_RESEARCH_CANDIDATES.md",
    "UKACTIVE_A3R1_DECISION.json",
    "UKACTIVE_A3R1_MANIFEST.json",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    assert not missing, f"Missing required outputs: {missing}"

    decision = json.loads((ROOT / "UKACTIVE_A3R1_DECISION.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "UKACTIVE_A3R1_MANIFEST.json").read_text(encoding="utf-8"))
    assert decision["decision"] == "UKACTIVE_A3R1_FAIL_DATA_OR_METHOD"
    assert decision["scientific_coverage_gate"] == "FAIL"
    assert decision["a3r2_executed"] is False
    assert decision["a3r2_scientifically_supported"] is False

    tests = pd.read_csv(ROOT / "UKACTIVE_A3R1_CORRECTNESS_TEST_RESULTS.csv")
    assert len(tests) == 21 and tests["status"].eq("PASS").all()

    registry = pd.read_csv(ROOT / "UKACTIVE_A3R1_SIGNAL_REGISTRY.csv")
    ledger = pd.read_csv(ROOT / "UKACTIVE_A3R1_MULTIPLE_TESTING_LEDGER.csv")
    assert set(registry["signal_id"]).issubset(set(ledger["signal_id"]))
    assert len(ledger) == int(decision["specifications_tested"])

    coverage = pd.read_csv(ROOT / "UKACTIVE_A3R1_HORIZON_COVERAGE_AUDIT.csv")
    blocked = coverage.loc[
        coverage["record_type"].eq("PRIMARY_SIGNAL_COVERAGE")
        & coverage["scientific_coverage_gate"].eq("FAIL")
    ]
    assert len(blocked) == 6
    rs252 = coverage.loc[coverage["feature_or_signal_id"].eq("RS_252")].iloc[0]
    assert rs252["covers_2020_onward"] == "NO"

    manifest_outputs = {
        Path(record["path"]).name: record
        for record in manifest["output_artifacts_excluding_self"]
    }
    for name in REQUIRED:
        if name == "UKACTIVE_A3R1_MANIFEST.json":
            continue
        path = ROOT / name
        record = manifest_outputs[name]
        assert path.stat().st_size == int(record["size_bytes"]), name
        assert sha256_file(path).upper() == str(record["sha256"]).upper(), name

    for name, record in manifest["input_hashes"].items():
        path = Path(record["path"])
        assert path.is_file(), name
        assert path.stat().st_size == int(record["size_bytes"]), name
        assert sha256_file(path).upper() == str(record["sha256"]).upper(), name

    parquet_names = [name for name in REQUIRED if name.endswith(".parquet")]
    parquet_audit: dict[str, dict[str, object]] = {}
    with tempfile.TemporaryDirectory(prefix="ukactive_a3r1_validate_") as temp_dir:
        temp_root = Path(temp_dir)
        for name in parquet_names:
            original = pd.read_parquet(ROOT / name)
            mirror = temp_root / name
            original.to_parquet(mirror, index=False)
            reread = pd.read_parquet(mirror)
            assert len(original) == len(reread), name
            assert list(original.columns) == list(reread.columns), name
            parquet_audit[name] = {"rows": len(original), "columns": len(original.columns)}

    inventory = manifest["local_excluded_data_inventory"]
    inventory_path = Path(inventory["path"])
    assert inventory_path.is_file()
    assert sha256_file(inventory_path).upper() == str(inventory["sha256"]).upper()
    assert len(pd.read_csv(inventory_path)) == int(inventory["record_count"])

    print(
        json.dumps(
            {
                "required_outputs": len(REQUIRED),
                "manifest_output_hashes_verified": len(REQUIRED) - 1,
                "input_hashes_verified": len(manifest["input_hashes"]),
                "correctness_tests": f"{tests['status'].eq('PASS').sum()}/{len(tests)}",
                "specification_ledger_rows": len(ledger),
                "parquet_round_trip": parquet_audit,
                "excluded_data_inventory_records": int(inventory["record_count"]),
                "decision": decision["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
