"""Build immutable, content-addressed Milestone 3 pytest evidence.

The tool deliberately uses pytest's built-in JUnit XML support instead of an
additional reporting dependency.  A completed evidence directory is created
with an atomic rename and is never overwritten by this tool.
"""

from __future__ import annotations

import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Any, Iterable
import xml.etree.ElementTree as ET


sys.dont_write_bytecode = True

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
PACKAGE_ROOT = SOURCE_ROOT / "edge_mdm"
EVIDENCE_ROOT = REPOSITORY_ROOT / "evidence" / "milestone3"
STAGING_ROOT = EVIDENCE_ROOT / ".building"

MANIFEST_VERSION = "edge-m3-pytest-evidence-v1"
EVIDENCE_ID_PREFIX = "EDGE-M3-PYTEST-"
OUTPUT_NAMES = (
    "collection.stdout.txt",
    "collection.stderr.txt",
    "collected_node_ids.json",
    "pytest.stdout.txt",
    "pytest.stderr.txt",
    "pytest.junit.xml",
)
EVIDENCE_TOOL_PATHS = (
    REPOSITORY_ROOT / "tools" / "build_m3_synthetic_acceptance_evidence.py",
    REPOSITORY_ROOT / "tools" / "build_m3_test_evidence.py",
)
GENERATED_TEST_PARTS = frozenset({".pytest_cache", ".pytest_tmp", "__pycache__"})
SUBPROCESS_ENVIRONMENT = {
    "NO_COLOR": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
    "PYTEST_ADDOPTS": "",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    "TERM": "dumb",
}


class EvidenceBuildError(RuntimeError):
    """Raised when a complete, trustworthy evidence run cannot be built."""


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _ensure_inside(path: Path, parent: Path, label: str) -> Path:
    resolved = path.resolve()
    resolved_parent = parent.resolve()
    if resolved != resolved_parent and resolved_parent not in resolved.parents:
        raise EvidenceBuildError(f"{label} escapes repository boundary: {resolved}")
    return resolved


def _relative(path: Path) -> str:
    resolved = _ensure_inside(path, REPOSITORY_ROOT, "bound path")
    return resolved.relative_to(REPOSITORY_ROOT.resolve()).as_posix()


def _file_record(path: Path) -> dict[str, Any]:
    resolved = _ensure_inside(path, REPOSITORY_ROOT, "bound file")
    if not resolved.is_file():
        raise EvidenceBuildError(f"required bound file is missing: {resolved}")
    return {
        "path": _relative(resolved),
        "bytes": resolved.stat().st_size,
        "sha256": _sha256_file(resolved),
    }


def _binding_group(name: str, paths: Iterable[Path]) -> dict[str, Any]:
    records = sorted((_file_record(path) for path in paths), key=lambda item: item["path"])
    if not records:
        raise EvidenceBuildError(f"binding group is empty: {name}")
    aggregate = {"name": name, "files": records}
    return {
        "file_count": len(records),
        "files": records,
        "aggregate_sha256": _sha256_bytes(_canonical_json_bytes(aggregate)),
    }


def _source_python_files() -> list[Path]:
    return sorted(path for path in SOURCE_ROOT.rglob("*.py") if path.is_file())


def _test_files() -> list[Path]:
    result: list[Path] = []
    for path in (REPOSITORY_ROOT / "tests").rglob("*"):
        relative_parts = path.relative_to(REPOSITORY_ROOT / "tests").parts
        if any(part in GENERATED_TEST_PARTS for part in relative_parts):
            continue
        if path.is_file() and path.suffix.lower() != ".pyc":
            result.append(path)
    return sorted(result)


def _config_files() -> list[Path]:
    return sorted(
        path for path in (REPOSITORY_ROOT / "config").rglob("*") if path.is_file()
    )


def _package_source_fingerprint() -> dict[str, str]:
    if str(SOURCE_ROOT) not in sys.path:
        sys.path.insert(0, str(SOURCE_ROOT))
    from edge_mdm.fingerprint import (  # noqa: PLC0415
        SOFTWARE_FINGERPRINT_VERSION,
        package_source_fingerprint,
    )

    return {
        "algorithm_version": SOFTWARE_FINGERPRINT_VERSION,
        "package_root": _relative(PACKAGE_ROOT),
        "sha256": package_source_fingerprint(PACKAGE_ROOT),
    }


def _input_bindings() -> dict[str, Any]:
    groups = {
        "source_python": _binding_group("source_python", _source_python_files()),
        "tests": _binding_group("tests", _test_files()),
        "evidence_tools": _binding_group("evidence_tools", EVIDENCE_TOOL_PATHS),
        "project_contract": _binding_group(
            "project_contract",
            (REPOSITORY_ROOT / "pyproject.toml", REPOSITORY_ROOT / "requirements.lock"),
        ),
        "configs": _binding_group("configs", _config_files()),
    }
    package_fingerprint = _package_source_fingerprint()
    aggregate_preimage = {
        "groups": groups,
        "package_source_fingerprint": package_fingerprint,
    }
    return {
        **aggregate_preimage,
        "aggregate_sha256": _sha256_bytes(_canonical_json_bytes(aggregate_preimage)),
        "test_file_exclusions": sorted(GENERATED_TEST_PARTS),
    }


def _environment_record() -> dict[str, Any]:
    return {
        "cwd": str(Path.cwd().resolve()),
        "python": {
            "executable": str(Path(sys.executable).resolve()),
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "version_detail": sys.version,
        },
        "platform": {
            "machine": platform.machine(),
            "platform": platform.platform(),
            "release": platform.release(),
            "system": platform.system(),
            "version": platform.version(),
        },
        "packages": {
            "duckdb": metadata.version("duckdb"),
            "pytest": metadata.version("pytest"),
        },
        "subprocess_environment_overrides": dict(SUBPROCESS_ENVIRONMENT),
    }


def _command_record(argv: list[str], contract_argv: list[str]) -> dict[str, Any]:
    return {
        "argv": argv,
        "contract_argv": contract_argv,
        "cwd": str(REPOSITORY_ROOT.resolve()),
        "display": subprocess.list2cmdline(argv),
        "shell": False,
    }


def _run(argv: list[str]) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment.update(SUBPROCESS_ENVIRONMENT)
    return subprocess.run(
        argv,
        cwd=REPOSITORY_ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _write_new(path: Path, content: bytes) -> None:
    _ensure_inside(path, EVIDENCE_ROOT, "evidence output")
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _parse_node_ids(stdout: bytes) -> tuple[list[str], int | None]:
    text = stdout.decode("utf-8", errors="strict")
    node_ids = [
        line.strip()
        for line in text.splitlines()
        if "::" in line and line.lstrip().startswith(("tests/", "tests\\"))
    ]
    if len(node_ids) != len(set(node_ids)):
        raise EvidenceBuildError("collect-only output contains duplicate node IDs")
    summaries = re.findall(r"(?m)^\s*(\d+)\s+tests?\s+collected(?:\s|$)", text)
    reported = int(summaries[-1]) if summaries else None
    if reported is not None and reported != len(node_ids):
        raise EvidenceBuildError(
            f"collect-only reported {reported} tests but emitted {len(node_ids)} node IDs"
        )
    return node_ids, reported


def _local_tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _parse_junit(path: Path) -> dict[str, Any]:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise EvidenceBuildError(f"cannot parse pytest JUnit XML: {exc}") from exc

    if _local_tag(root) == "testsuite":
        suites = [root]
        totals_source = root
    elif _local_tag(root) == "testsuites":
        suites = [child for child in root if _local_tag(child) == "testsuite"]
        totals_source = root
    else:
        raise EvidenceBuildError(f"unexpected JUnit root element: {_local_tag(root)}")

    def total(name: str) -> int:
        raw = totals_source.attrib.get(name)
        if raw is not None:
            try:
                return int(raw)
            except ValueError as exc:
                raise EvidenceBuildError(f"invalid JUnit {name} count: {raw}") from exc
        try:
            return sum(int(suite.attrib.get(name, "0")) for suite in suites)
        except ValueError as exc:
            raise EvidenceBuildError(f"invalid JUnit suite {name} count") from exc

    counts = {name: total(name) for name in ("tests", "failures", "errors", "skipped")}
    counts["passed"] = (
        counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    )
    if any(value < 0 for value in counts.values()):
        raise EvidenceBuildError(f"internally inconsistent JUnit counts: {counts}")

    cases: list[dict[str, Any]] = []
    derived = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "passed": 0}
    for element in root.iter():
        if _local_tag(element) != "testcase":
            continue
        derived["tests"] += 1
        children = {_local_tag(child): child for child in element}
        outcome = "passed"
        detail: dict[str, Any] | None = None
        for candidate in ("failure", "error", "skipped"):
            if candidate in children:
                outcome = candidate
                child = children[candidate]
                body = (child.text or "").encode("utf-8")
                detail = {
                    "message": child.attrib.get("message"),
                    "type": child.attrib.get("type"),
                    "body_bytes": len(body),
                    "body_sha256": _sha256_bytes(body),
                }
                break
        derived_key = {"failure": "failures", "error": "errors"}.get(
            outcome, outcome
        )
        derived[derived_key] += 1
        cases.append(
            {
                "classname": element.attrib.get("classname"),
                "file": element.attrib.get("file"),
                "line": element.attrib.get("line"),
                "name": element.attrib.get("name"),
                "outcome": outcome,
                "detail": detail,
            }
        )
    if counts != derived:
        raise EvidenceBuildError(
            f"JUnit aggregate and testcase counts disagree: {counts} != {derived}"
        )
    return {
        "counts": counts,
        "cases": cases,
        "suite_count": len(suites),
    }


def _output_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for name in OUTPUT_NAMES:
        path = _ensure_inside(STAGING_ROOT / name, STAGING_ROOT, "evidence payload")
        if not path.is_file():
            raise EvidenceBuildError(f"required evidence payload is missing: {path}")
        records.append(
            {
                "path": name,
                "path_scope": "evidence_run_root",
                "bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
    return records


def main() -> int:
    if Path.cwd().resolve() != REPOSITORY_ROOT.resolve():
        raise EvidenceBuildError(
            f"run from repository root {REPOSITORY_ROOT}; current cwd is {Path.cwd().resolve()}"
        )
    _ensure_inside(EVIDENCE_ROOT, REPOSITORY_ROOT, "evidence root")
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    STAGING_ROOT.mkdir(exist_ok=False)

    initial_bindings = _input_bindings()
    environment = _environment_record()
    python_executable = str(Path(sys.executable).resolve())

    collection_argv = [python_executable, "-B", "-m", "pytest", "--collect-only", "-q"]
    collection_contract = ["python", "-B", "-m", "pytest", "--collect-only", "-q"]
    collection = _run(collection_argv)
    _write_new(STAGING_ROOT / "collection.stdout.txt", collection.stdout)
    _write_new(STAGING_ROOT / "collection.stderr.txt", collection.stderr)
    node_ids, reported_collection_count = _parse_node_ids(collection.stdout)
    node_payload = {"count": len(node_ids), "node_ids": node_ids}
    _write_new(
        STAGING_ROOT / "collected_node_ids.json",
        _canonical_json_bytes(node_payload) + b"\n",
    )

    junit_path = STAGING_ROOT / "pytest.junit.xml"
    pytest_argv = [
        python_executable,
        "-B",
        "-m",
        "pytest",
        "-q",
        f"--junitxml={junit_path}",
    ]
    pytest_contract = [
        "python",
        "-B",
        "-m",
        "pytest",
        "-q",
        "--junitxml=<repo>/evidence/milestone3/.building/pytest.junit.xml",
    ]
    execution = _run(pytest_argv)
    _write_new(STAGING_ROOT / "pytest.stdout.txt", execution.stdout)
    _write_new(STAGING_ROOT / "pytest.stderr.txt", execution.stderr)
    if not junit_path.is_file():
        raise EvidenceBuildError("pytest did not produce its required JUnit XML output")
    junit = _parse_junit(junit_path)

    final_bindings = _input_bindings()
    if final_bindings != initial_bindings:
        raise EvidenceBuildError("bound source, test, tool, contract, or config files changed")

    outputs = _output_records()
    collection_execution_count_match = junit["counts"]["tests"] == len(node_ids)
    overall_status = (
        "PASS"
        if collection.returncode == 0
        and execution.returncode == 0
        and collection_execution_count_match
        else "FAIL"
    )
    commands = {
        "collection": _command_record(collection_argv, collection_contract),
        "execution": _command_record(pytest_argv, pytest_contract),
    }
    manifest_body = {
        "manifest_version": MANIFEST_VERSION,
        "classification": "MILESTONE_3_TEST_EVIDENCE",
        "overall_status": overall_status,
        "commands": commands,
        "environment": environment,
        "input_bindings": initial_bindings,
        "collection": {
            "return_code": collection.returncode,
            "reported_count": reported_collection_count,
            **node_payload,
        },
        "execution": {
            "return_code": execution.returncode,
            "junit": junit,
        },
        "consistency": {
            "collection_execution_count_match": collection_execution_count_match,
        },
        "outputs": outputs,
        "immutability": {
            "completed_run_creation": "exclusive atomic directory rename",
            "existing_run_policy": "refuse overwrite",
            "payload_integrity": "SHA-256 per output file",
        },
        "evidence_id_derivation": {
            "algorithm": "SHA-256",
            "canonicalisation": "UTF-8 JSON, sorted keys, no insignificant whitespace",
            "prefix": EVIDENCE_ID_PREFIX,
            "preimage": "the complete manifest object excluding evidence_id",
        },
    }
    manifest_digest = _sha256_bytes(_canonical_json_bytes(manifest_body))
    evidence_id = f"{EVIDENCE_ID_PREFIX}{manifest_digest.upper()}"
    manifest = {"evidence_id": evidence_id, **manifest_body}
    _write_new(
        STAGING_ROOT / "manifest.json",
        _canonical_json_bytes(manifest) + b"\n",
    )

    final_root = EVIDENCE_ROOT / evidence_id
    _ensure_inside(final_root, EVIDENCE_ROOT, "final evidence run")
    if final_root.exists():
        raise EvidenceBuildError(f"refusing to overwrite existing evidence run: {final_root}")
    STAGING_ROOT.rename(final_root)

    print(f"evidence_id={evidence_id}")
    print(f"evidence_directory={final_root}")
    print(
        "tests={tests} failures={failures} errors={errors} skipped={skipped}".format(
            **junit["counts"]
        )
    )
    return 0 if overall_status == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvidenceBuildError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
