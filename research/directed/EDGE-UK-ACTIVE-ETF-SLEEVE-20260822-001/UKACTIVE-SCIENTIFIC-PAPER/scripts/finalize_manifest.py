"""Write the final UKACTIVE paper package manifest.

The manifest excludes itself from the hash inventory to avoid a recursive
self-hash. It also excludes temporary page renders used only for visual QA.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader


SCRIPT = Path(__file__).resolve()
PAPER_ROOT = SCRIPT.parents[1]
REPO_ROOT = PAPER_ROOT.parents[3]
MANIFEST = PAPER_ROOT / "UKACTIVE_PAPER_MANIFEST.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def words(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return len(text.split())


def command_output(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return (completed.stdout or completed.stderr).strip()


def runtime_versions() -> dict[str, Any]:
    system_python = r"C:\Python312\python.exe"
    bundled_python = r"C:\Users\paulh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    node = r"C:\Users\paulh\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
    system = json.loads(
        command_output(
            [
                system_python,
                "-c",
                (
                    "import json,platform,numpy,pandas,matplotlib,pyarrow;"
                    "print(json.dumps({'python':platform.python_version(),'numpy':numpy.__version__,"
                    "'pandas':pandas.__version__,'matplotlib':matplotlib.__version__,"
                    "'pyarrow':pyarrow.__version__}))"
                ),
            ]
        )
    )
    bundled = json.loads(
        command_output(
            [
                bundled_python,
                "-c",
                (
                    "import json,platform,pypdf,docx,PIL;"
                    "print(json.dumps({'python':platform.python_version(),'pypdf':pypdf.__version__,"
                    "'python_docx':docx.__version__,'pillow':PIL.__version__}))"
                ),
            ]
        )
    )
    artifact_package = Path(
        r"C:\Users\paulh\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\@oai\artifact-tool\package.json"
    )
    artifact = json.loads(artifact_package.read_text(encoding="utf-8"))
    return {
        "host": {
            "platform": platform.platform(),
            "timezone": "Europe/London",
        },
        "asset_runtime": system,
        "document_runtime": bundled,
        "node": command_output([node, "--version"]),
        "artifact_tool": artifact["version"],
        "word_renderer": "Microsoft Word for Microsoft 365",
        "pdf_rasterizer": command_output(["pdftoppm.exe", "-v"]).splitlines()[0],
    }


def file_category(relative: Path) -> str:
    if relative.parts[0] == "figures":
        return "figure"
    if relative.parts[0] == "tables":
        return "derived_table"
    if relative.parts[0] == "scripts":
        return "reproduction_script"
    if relative.parts[0] == "qa":
        return "quality_assurance"
    if relative.suffix.lower() in {".docx", ".pdf"}:
        return "rendered_paper"
    if relative.suffix.lower() == ".md":
        return "narrative_or_documentation"
    if relative.suffix.lower() == ".bib":
        return "bibliography"
    if relative.suffix.lower() == ".csv":
        return "evidence_or_figure_manifest"
    if relative.suffix.lower() == ".json":
        return "reproducibility_or_manifest_support"
    return "other"


def package_files() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(item for item in PAPER_ROOT.rglob("*") if item.is_file()):
        relative = path.relative_to(PAPER_ROOT)
        if (
            relative == Path(MANIFEST.name)
            or relative.parts[0] == "rendered"
            or "__pycache__" in relative.parts
            or relative.suffix.lower() == ".pyc"
        ):
            continue
        records.append(
            {
                "path": relative.as_posix(),
                "category": file_category(relative),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "raw_byte_reproducibility": (
                    "DOCUMENTED_WORD_PDF_EXCEPTION"
                    if relative.name == "UKACTIVE_ETF_ROTATION_SCIENTIFIC_PAPER.pdf"
                    else "DETERMINISTIC_OR_AUTHORED_INPUT"
                ),
            }
        )
    return records


def source_inventory() -> list[dict[str, str]]:
    evidence = PAPER_ROOT / "UKACTIVE_PAPER_SOURCE_EVIDENCE_MATRIX.csv"
    with evidence.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    unique: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["source_stage"], row["source_file"], row["source_commit"])
        unique[key] = {
            "source_stage": row["source_stage"],
            "source_file": row["source_file"],
            "source_commit": row["source_commit"],
        }
    return [unique[key] for key in sorted(unique)]


def git(*args: str) -> str:
    return command_output(["git", *args])


def main() -> None:
    markdown = PAPER_ROOT / "UKACTIVE_ETF_ROTATION_SCIENTIFIC_PAPER.md"
    supplement = PAPER_ROOT / "UKACTIVE_ETF_ROTATION_SUPPLEMENT.md"
    summary = PAPER_ROOT / "UKACTIVE_ETF_ROTATION_EXECUTIVE_SUMMARY.md"
    glossary = PAPER_ROOT / "UKACTIVE_PAPER_METRIC_GLOSSARY.md"
    pdf = PAPER_ROOT / "UKACTIVE_ETF_ROTATION_SCIENTIFIC_PAPER.pdf"
    evidence_rows = sum(1 for _ in (PAPER_ROOT / "UKACTIVE_PAPER_SOURCE_EVIDENCE_MATRIX.csv").open(encoding="utf-8")) - 1

    manifest = {
        "schema": "UKACTIVE_PAPER_MANIFEST.v1",
        "paper_version": "1.0.0",
        "generation_timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generation_date": "2026-08-27",
        "historical_cutoff": "2026-08-21",
        "documentation_branch": git("branch", "--show-current"),
        "documentation_parent_commit": git("rev-parse", "HEAD"),
        "authoritative_source": {
            "branch": "research/ukactive-a5c-sipp-frozen-prospective",
            "freeze_commit": "a8008f7709af3000a889bb234a86f8c520c4ed73",
            "results_commit": "beb8d49828b9819aa167d2e07ffdc2b92581b36b",
            "final_manifest_commit": "df30c9be430c4a746a6e3ec0d97690612badd4fa",
        },
        "frozen_strategy": "INDUSTRY_PLUS_THEME | M2_BASE | TOP7 | MONTHLY | CASH0_ALWAYS_INVESTED | EQUAL",
        "scientific_classification": "E2_DEVELOPMENTAL",
        "model_status": "FROZEN",
        "historical_model_development": "CLOSED / M2_HISTORICAL_MODEL_DEVELOPMENT_CLOSED",
        "live_implementation_status": {
            "status": "AWAITING_CURRENT_HOLDINGS_INPUT",
            "pilot_operationally_ready": False,
            "permitted_use": "Controlled 10% pilot after operational readiness and explicit user approval",
        },
        "counts": {
            "main_paper_words": words(markdown),
            "supplement_words": words(supplement),
            "executive_summary_words": words(summary),
            "metric_glossary_words": words(glossary),
            "numbered_main_tables": len(re.findall(r"^\*\*Table \d+\.", markdown.read_text(encoding="utf-8"), flags=re.MULTILINE)),
            "figures": len(list((PAPER_ROOT / "figures").glob("*.png"))),
            "derived_table_csvs": len(list((PAPER_ROOT / "tables").glob("*.csv"))),
            "evidence_claims": evidence_rows,
            "pdf_pages": len(PdfReader(pdf).pages),
        },
        "quality_assurance": {
            "scientific_qa": "PASS_WITH_DISCLOSED_SOURCE_CONFLICT",
            "asset_build": "PASS",
            "tabular_validation": "PASS",
            "render_validation": "PASS",
            "two_pass_reproduction": "PASS",
            "unresolved_source_conflicts": ["LONG-CORE-CONFLICT"],
            "pdf_reproduction_exception": "Raw Word PDF bytes differ between builds; all 56 independently rasterised page hashes are identical.",
        },
        "runtime_versions": runtime_versions(),
        "source_files": source_inventory(),
        "generated_files": package_files(),
        "manifest_self_hash_policy": "UKACTIVE_PAPER_MANIFEST.json is excluded from its own generated_files hash inventory.",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "manifest": str(MANIFEST), "files": len(manifest["generated_files"])}, indent=2))


if __name__ == "__main__":
    main()
