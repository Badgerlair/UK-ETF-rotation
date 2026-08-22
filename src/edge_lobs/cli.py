"""Small fail-closed command surface for leadership observation capture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping

from .errors import LobsError
from .jsonio import load_json_object
from .ledger import import_observation_batch, rebuild_index, verify_ledger
from .mdm import read_mdm_status, validate_test_only_enrichment
from .outcomes import materialise_test_only_outcomes, validate_test_only_outcomes
from .validation import (
    validate_import_manifest_document,
    validate_observation_document,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="edge-lobs")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="validate an observation JSON")
    validate.add_argument("observation")
    validate.add_argument("--allow-draft", action="store_true")

    manifest = commands.add_parser(
        "validate-manifest", help="validate an import manifest and observation"
    )
    manifest.add_argument("manifest")
    manifest.add_argument("--repository-root", required=True)
    manifest.add_argument("--allow-template", action="store_true")
    manifest.add_argument(
        "--observation",
        help=(
            "repository-contained observation JSON used only when an explicitly "
            "allowed template has a null observation_path"
        ),
    )

    import_command = commands.add_parser(
        "import", help="validate and immutably seal one complete batch"
    )
    import_command.add_argument("manifest")
    import_command.add_argument("--repository-root", required=True)

    verify = commands.add_parser("verify-ledger")
    verify.add_argument("--repository-root", required=True)

    index = commands.add_parser("rebuild-index")
    index.add_argument("--repository-root", required=True)

    status = commands.add_parser("mdm-status")
    status.add_argument("--repository-root", required=True)

    enrichment = commands.add_parser(
        "validate-enrichment",
        help="structurally validate an explicitly test-only enrichment document",
    )
    enrichment.add_argument("document")
    enrichment.add_argument("--batch-manifest", required=True)
    enrichment.add_argument("--sessions", required=True)

    outcomes = commands.add_parser(
        "validate-outcomes",
        help="structurally validate explicitly test-only forward outcomes",
    )
    outcomes.add_argument("document")
    outcomes.add_argument("--batch-manifest", required=True)
    outcomes.add_argument("--sessions", required=True)

    materialise = commands.add_parser(
        "materialise-test-outcomes",
        help="write an immutable TEST_ONLY_NON_PRODUCTION outcome artifact",
    )
    materialise.add_argument("document")
    materialise.add_argument("--batch-manifest", required=True)
    materialise.add_argument("--sessions", required=True)
    materialise.add_argument("--repository-root", required=True)
    materialise.add_argument("--output-root")
    return parser


def _emit(value: Any) -> None:
    sys.stdout.write(
        json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True)
        + "\n"
    )


def _resolved_repo_file(path: str | Path, repository_root: str | Path) -> Path:
    try:
        root = Path(repository_root).resolve(strict=True)
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = root / resolved
        resolved = resolved.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise LobsError("PATH_INVALID", "path does not resolve", path=str(path)) from exc
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise LobsError(
            "PATH_OUTSIDE_REPOSITORY",
            "required file must stay inside the Project EDGE repository",
            path=str(resolved),
        )
    return resolved


def _manifest_observation_path(
    manifest_path: Path, manifest: Mapping[str, Any], repository_root: str | Path
) -> Path:
    raw = manifest.get("observation_path")
    if not isinstance(raw, str) or not raw:
        raise LobsError(
            "OBSERVATION_PATH_REQUIRED",
            "manifest observation_path must name a file",
            path=str(manifest_path),
        )
    try:
        root = Path(repository_root).resolve(strict=True)
        candidate = (manifest_path.parent / raw).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise LobsError(
            "OBSERVATION_PATH_INVALID", "observation path does not resolve", path=raw
        ) from exc
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise LobsError(
            "OBSERVATION_PATH_OUTSIDE_REPOSITORY",
            "observation must be a repository-contained file",
            path=str(candidate),
        )
    return candidate


def _session_rows(path: str | Path) -> list[Mapping[str, Any]]:
    document = load_json_object(path)
    rows = document.get("sessions")
    if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
        raise LobsError(
            "SESSION_DOCUMENT_INVALID",
            "session document must be an object containing a sessions array",
            path=str(path),
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            report = validate_observation_document(
                load_json_object(args.observation), allow_draft=args.allow_draft
            )
            _emit(report.as_dict())
            return 0

        if args.command == "validate-manifest":
            manifest_path = _resolved_repo_file(args.manifest, args.repository_root)
            manifest = load_json_object(manifest_path)
            if args.observation is not None:
                if not args.allow_template or manifest.get("observation_path") is not None:
                    raise LobsError(
                        "OBSERVATION_OVERRIDE_FORBIDDEN",
                        "--observation is permitted only for an explicitly allowed "
                        "template whose observation_path is null",
                        path=str(manifest_path),
                    )
                observation_path = _resolved_repo_file(
                    args.observation, args.repository_root
                )
            else:
                observation_path = _manifest_observation_path(
                    manifest_path, manifest, args.repository_root
                )
            observation = load_json_object(observation_path)
            report = validate_import_manifest_document(
                manifest, observation, allow_template=args.allow_template
            )
            _emit(report.as_dict())
            return 0

        if args.command == "import":
            sealed = import_observation_batch(args.manifest, args.repository_root)
            _emit({"state": "SEALED_CAPTURE_RECORD", **sealed.as_dict()})
            return 0

        if args.command == "verify-ledger":
            _emit(verify_ledger(args.repository_root))
            return 0

        if args.command == "rebuild-index":
            _emit(rebuild_index(args.repository_root))
            return 0

        if args.command == "mdm-status":
            status = read_mdm_status(args.repository_root)
            _emit(status.as_dict())
            return 0 if status.ready else 2

        if args.command in {
            "validate-enrichment",
            "validate-outcomes",
            "materialise-test-outcomes",
        }:
            document = load_json_object(args.document)
            batch_manifest = load_json_object(args.batch_manifest)
            sessions = _session_rows(args.sessions)
            if args.command == "validate-enrichment":
                report = validate_test_only_enrichment(
                    document, batch_manifest=batch_manifest, session_rows=sessions
                )
                _emit(report.as_dict())
                return 0
            if args.command == "validate-outcomes":
                report = validate_test_only_outcomes(
                    document, batch_manifest=batch_manifest, session_rows=sessions
                )
                _emit(report.as_dict())
                return 0
            artifact = materialise_test_only_outcomes(
                document,
                batch_manifest=batch_manifest,
                session_rows=sessions,
                repository_root=args.repository_root,
                output_root=args.output_root,
            )
            _emit(artifact.as_dict())
            return 0
    except LobsError as exc:
        _emit(
            {
                "state": "FAILED_CLOSED",
                "error_type": type(exc).__name__,
                "error_code": exc.code,
                "message": exc.message,
                "path": exc.path,
            }
        )
        return 1
    except Exception as exc:  # defensive command boundary; no traceback leakage.
        _emit(
            {
                "state": "FAILED_CLOSED",
                "error_type": type(exc).__name__,
                "error_code": "UNCLASSIFIED_FAILURE",
                "message": str(exc),
                "path": None,
            }
        )
        return 1
    return 1


__all__ = ["main"]
