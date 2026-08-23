"""Build the Git-excluded local-data inventory for the UKACTIVE programme.

The inventory is deliberately generated from bytes on disk.  It records every
large/reproducible binary research artifact and every retained source capture,
so Git can carry the code, policies and audit controls without redistributing
large or potentially licensed data.
"""

from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path


PROGRAMME = Path(__file__).resolve().parents[1]
OUTPUT = PROGRAMME / "UKACTIVE_GIT_EXCLUDED_DATA_INVENTORY.csv"
LARGE_FILE_BYTES = 5 * 1024 * 1024
EXCLUDED_SUFFIXES = {
    ".parquet",
    ".feather",
    ".arrow",
    ".h5",
    ".hdf5",
    ".pkl",
    ".pickle",
    ".joblib",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".bin",
    ".gz",
    ".zip",
    ".7z",
    ".tar",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def policy_for(relative_path: str) -> str:
    name = relative_path.upper()
    for stage in ("A4C", "A4B", "A4", "A3R2", "A3R1R1", "A2R2", "A3R1", "A2R", "A3R0", "A3", "A2", "A0A1"):
        if f"UKACTIVE_{stage}" in name:
            return f"UKACTIVE_{stage}_POLICY_OR_MANIFEST"
    if relative_path.lower().startswith("evidence/sources/"):
        return "SOURCE_CAPTURE; SEE COMMITTED EVIDENCE LEDGER"
    return "PLATFORM_REPRODUCIBILITY_POLICY"


def exclusion_reason(path: Path, relative_path: str) -> str | None:
    normalized = relative_path.replace("\\", "/").lower()
    if normalized.startswith("evidence/sources/"):
        return "SOURCE_CAPTURE_NOT_REDISTRIBUTED"
    if path.suffix.lower() in EXCLUDED_SUFFIXES or path.name.lower().endswith(".bin.gz"):
        return "LARGE_OR_REPRODUCIBLE_BINARY_DATA"
    name = path.name.upper()
    if name.endswith("_SUBPERIOD_RESULTS.CSV") and name != "UKACTIVE_A3R1_SUBPERIOD_RESULTS.CSV":
        return "REPRODUCIBLE_GENERATED_TABLE_EXCLUDED_BY_POLICY"
    if name.endswith("_QUANTILE_FORWARD_RETURNS.CSV") or name.endswith("_TIME_SERIES.CSV"):
        return "REPRODUCIBLE_GENERATED_TABLE_EXCLUDED_BY_POLICY"
    if name in {
        "UKACTIVE_A3R1_DYNAMIC_COHORT_COUNTS.CSV",
        "UKACTIVE_A3R1_OVERLAP_DIAGNOSTICS.CSV",
        "UKACTIVE_A3R1R1_DYNAMIC_COHORT_COUNTS.CSV",
        "UKACTIVE_A3R1R1_OVERLAP_DIAGNOSTICS.CSV",
        "UKACTIVE_A3R1R1_TOP_TAIL_RESULTS.CSV",
        "UKACTIVE_A2R2_HORIZON_COVERAGE_HEATMAP.CSV",
    }:
        return "REPRODUCIBLE_GENERATED_TABLE_EXCLUDED_BY_POLICY"
    if path.stat().st_size > LARGE_FILE_BYTES:
        return "GENERATED_OUTPUT_OVER_5_MIB"
    return None


def main() -> None:
    records: list[dict[str, object]] = []
    for path in sorted(PROGRAMME.rglob("*")):
        if not path.is_file() or path == OUTPUT:
            continue
        relative = path.relative_to(PROGRAMME).as_posix()
        reason = exclusion_reason(path, relative)
        if reason is None:
            continue
        stat = path.stat()
        modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        records.append(
            {
                "local_path": str(path),
                "relative_path": relative,
                "sha256": sha256_file(path),
                "size_bytes": stat.st_size,
                "source_identity": relative,
                "retrieval_or_generation_date": modified.date().isoformat(),
                "date_basis": "LOCAL_LAST_WRITE_UTC; AUTHORITATIVE RETRIEVAL IN EVIDENCE LEDGER/MANIFEST",
                "generating_policy_version": policy_for(relative),
                "git_exclusion_reason": reason,
            }
        )

    fields = [
        "local_path",
        "relative_path",
        "sha256",
        "size_bytes",
        "source_identity",
        "retrieval_or_generation_date",
        "date_basis",
        "generating_policy_version",
        "git_exclusion_reason",
    ]
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    print(f"wrote {len(records)} records to {OUTPUT}")


if __name__ == "__main__":
    main()
