#!/usr/bin/env python3
"""Read-only schema and provenance audit for canonical UKACTIVE paper inputs.

This helper never modifies a canonical research artefact.  It is retained with
the paper so that the source audit can be repeated from the frozen commit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd


REPO_ROOT = Path(r"D:\codex\equity_quant_research_platform")
RESEARCH_ROOT = REPO_ROOT / "research" / "directed" / "EDGE-UK-ACTIVE-ETF-SLEEVE-20260822-001"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_commit(path: Path) -> str:
    rel = path.relative_to(REPO_ROOT).as_posix()
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", rel],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def load_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, low_memory=False)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported table type: {path}")


def normalise(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def inspect(paths: list[Path], head: int) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in paths:
        entry: dict[str, Any] = {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "source_commit": source_commit(path),
        }
        if path.suffix.lower() in {".csv", ".parquet"}:
            frame = load_table(path)
            entry.update(
                {
                    "rows": int(len(frame)),
                    "columns": [str(column) for column in frame.columns],
                    "dtypes": {str(column): str(dtype) for column, dtype in frame.dtypes.items()},
                    "head": [
                        {str(key): normalise(value) for key, value in row.items()}
                        for row in frame.head(head).to_dict(orient="records")
                    ],
                }
            )
        elif path.suffix.lower() == ".json":
            entry["json"] = json.loads(path.read_text(encoding="utf-8"))
        files.append(entry)
    return {"research_root": str(RESEARCH_ROOT), "files": files}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="Paths relative to the research root")
    parser.add_argument("--head", type=int, default=3)
    args = parser.parse_args()
    resolved = [(RESEARCH_ROOT / item).resolve() for item in args.paths]
    for path in resolved:
        if not path.is_file() or RESEARCH_ROOT.resolve() not in path.parents:
            raise FileNotFoundError(path)
    print(json.dumps(inspect(resolved, args.head), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
