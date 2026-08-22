"""Small command-line surface for verification and the single daily build."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .pipeline import build_daily_slice, load_daily_slice_request
from .release import materialise_candidate, record_failed_build_attempt
from .scope import load_production_scope
from .source import verify_mdm_snapshot


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="edge-mdm")
    commands = parser.add_subparsers(dest="command", required=True)

    verify = commands.add_parser("verify-source")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--mdm-root", required=True)
    verify.add_argument("--allow-test-only", action="store_true")

    build = commands.add_parser("build-daily-slice")
    build.add_argument("--manifest", required=True)
    build.add_argument("--mdm-root", required=True)
    build.add_argument("--policy", required=True)
    build.add_argument("--repository-root", required=True)
    build.add_argument("--output-root", required=True)
    build.add_argument("--builder-id", required=True)
    build.add_argument("--production-scope")
    build.add_argument("--allow-test-only", action="store_true")

    audit = commands.add_parser("audit-status")
    audit.add_argument("--repository-root", required=True)
    return parser


def _emit(value: Any) -> None:
    sys.stdout.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "verify-source":
            snapshot = verify_mdm_snapshot(
                args.manifest,
                args.mdm_root,
                allow_test_only=args.allow_test_only,
            )
            _emit(
                {
                    "state": "VERIFIED",
                    "snapshot_id": snapshot.manifest.snapshot_id,
                    "source_kind": snapshot.manifest.source_kind,
                    "production_use_permitted": snapshot.production_use_permitted,
                    "manifest_sha256": snapshot.manifest_sha256,
                    "tables": {
                        table.manifest.logical_name: {
                            "rows": table.manifest.row_count,
                            "file_sha256": table.verified_sha256,
                            "logical_sha256": table.verified_logical_sha256,
                        }
                        for table in snapshot.tables
                    },
                }
            )
            return 0
        if args.command == "build-daily-slice":
            snapshot = verify_mdm_snapshot(
                args.manifest,
                args.mdm_root,
                allow_test_only=args.allow_test_only,
            )
            request = load_daily_slice_request(args.policy)
            scope = (
                load_production_scope(args.production_scope)
                if args.production_scope
                else None
            )
            build = build_daily_slice(snapshot, request, production_scope=scope)
            artifact = materialise_candidate(
                build,
                repository_root=args.repository_root,
                output_root=args.output_root,
                builder_id=args.builder_id,
            )
            _emit(
                {
                    "state": artifact.manifest["artifact_state"],
                    "artifact_id": artifact.artifact_id,
                    "artifact_root": str(artifact.root),
                    "artifact_manifest_sha256": artifact.manifest_sha256,
                    "production_use_permitted": artifact.production_use_permitted,
                    "build": build.summary(),
                }
            )
            return 0
        if args.command == "audit-status":
            repository = Path(args.repository_root).resolve(strict=True)
            capability = json.loads(
                (repository / "config" / "mdm_capability_audit.v1.json").read_text(
                    encoding="utf-8"
                )
            )
            population = json.loads(
                (repository / "config" / "population_time_contract.v1.json").read_text(
                    encoding="utf-8"
                )
            )
            scope_status = json.loads(
                (repository / "config" / "production_scope_status.v1.json").read_text(
                    encoding="utf-8"
                )
            )
            release_authority = json.loads(
                (
                    repository
                    / "config"
                    / "production_release_authority.v1.json"
                ).read_text(encoding="utf-8")
            )
            ready = (
                capability.get("production_gate") == "READY"
                and population.get("status") == "RATIFIED"
                and scope_status.get("status") == "APPROVED_SCOPES_AVAILABLE"
                and release_authority.get("status") == "READY"
                and release_authority.get("production_use_permitted") is True
            )
            _emit(
                {
                    "production_implementation_ready": ready,
                    "mdm_capability_gate": capability.get("production_gate"),
                    "population_time_contract": population.get("status"),
                    "production_scope_status": scope_status.get("status"),
                    "production_release_authority": release_authority.get("status"),
                    "mandatory_blockers": capability.get("mandatory_blockers", [])
                    + population.get("unresolved_mandatory_decisions", [])
                    + (
                        [str(scope_status.get("reason"))]
                        if scope_status.get("status") != "APPROVED_SCOPES_AVAILABLE"
                        else []
                    )
                    + (
                        [str(release_authority.get("required_control"))]
                        if release_authority.get("status") != "READY"
                        else []
                    ),
                }
            )
            return 0 if ready else 2
    except Exception as exc:  # CLI converts fail-closed exceptions to typed JSON.
        response = {
            "state": "FAILED_CLOSED",
            "error_type": type(exc).__name__,
            "error_code": getattr(exc, "code", "UNCLASSIFIED_FAILURE"),
            "message": str(exc),
        }
        if getattr(args, "command", None) == "build-daily-slice":
            try:
                failure = record_failed_build_attempt(
                    repository_root=args.repository_root,
                    output_root=args.output_root,
                    stage="BUILD_DAILY_SLICE",
                    error=exc,
                    context={
                        "source_manifest": args.manifest,
                        "mdm_root": args.mdm_root,
                        "policy": args.policy,
                        "production_scope": args.production_scope,
                    },
                )
                response["failure_evidence"] = str(failure)
            except Exception as evidence_error:
                response["failure_evidence_error"] = str(evidence_error)
        _emit(response)
        return 1
    return 1
