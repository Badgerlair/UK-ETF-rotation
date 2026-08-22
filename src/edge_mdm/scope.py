"""Independent production-scope approval for the bounded daily path."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .fingerprint import canonical_json_bytes, sha256_bytes


class ScopeApprovalError(ValueError):
    pass


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def assert_repository_production_gate_open(
    scope: "ProductionScopeApproval | None",
    *,
    repository_root: str | Path | None = None,
) -> None:
    """Require the canonical repository gates, not a standalone assertion.

    The current Milestone 3 repository deliberately records a blocked gate and
    no approved scope.  A caller-created scope JSON therefore cannot turn on a
    production build.  Protected external approval storage remains an
    operational prerequisite before these canonical records may be advanced.
    """

    root = (
        Path(repository_root).resolve(strict=True)
        if repository_root is not None
        else Path(__file__).resolve().parents[2]
    )
    config_root = root / "config"

    def read(name: str) -> Mapping[str, Any]:
        path = config_root / name
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ScopeApprovalError(f"canonical production gate unreadable: {path}") from exc
        if not isinstance(value, Mapping):
            raise ScopeApprovalError(f"canonical production gate is not an object: {path}")
        return value

    capability = read("mdm_capability_audit.v1.json")
    population = read("population_time_contract.v1.json")
    status = read("production_scope_status.v1.json")
    release_authority = read("production_release_authority.v1.json")
    failures: list[str] = []
    if capability.get("schema_version") != "edge.mdm_capability_audit.v1":
        failures.append("capability audit schema is invalid")
    if capability.get("production_gate") != "READY":
        failures.append("MDM capability audit is not READY")
    if population.get("schema_version") != "edge.population_time_contract.v1":
        failures.append("population/time contract schema is invalid")
    if not (
        population.get("status") == "RATIFIED"
        and population.get("production_use_permitted") is True
    ):
        failures.append("population/time contract is not RATIFIED")
    if status.get("schema_version") != "edge.production_scope_status.v1":
        failures.append("production scope status schema is invalid")
    if (
        release_authority.get("schema_version")
        != "edge.production_release_authority.v1"
    ):
        failures.append("production release authority schema is invalid")
    if not (
        release_authority.get("status") == "READY"
        and release_authority.get("production_use_permitted") is True
    ):
        failures.append("protected production release authority is not READY")
    approved = status.get("approved_production_scopes")
    if scope is None:
        failures.append("an exact production scope approval is required")
    elif not isinstance(approved, list):
        failures.append("canonical approved-scope register is invalid")
    else:
        valid_entries = all(
            isinstance(entry, Mapping)
            and set(entry) == {"approval_id", "scope_sha256"}
            and isinstance(entry.get("approval_id"), str)
            and bool(str(entry.get("approval_id")).strip())
            and isinstance(entry.get("scope_sha256"), str)
            and _SHA256_RE.fullmatch(str(entry.get("scope_sha256"))) is not None
            for entry in approved
        )
        if not valid_entries:
            failures.append("canonical approved-scope register entries are invalid")
        exact_matches = [
            entry
            for entry in approved
            if isinstance(entry, Mapping)
            and entry.get("approval_id") == scope.approval_id
            and entry.get("scope_sha256") == scope.content_sha256
        ]
        if len(exact_matches) != 1:
            failures.append(
                "scope ID and exact content hash are not in the canonical approved-scope register"
            )
    if status.get("status") != "APPROVED_SCOPES_AVAILABLE":
        failures.append("canonical production scope status is not open")
    if scope is not None:
        if capability.get("audit_id") != scope.capability_audit_id:
            failures.append("scope capability audit ID differs from the canonical audit")
        if population.get("contract_version") != scope.population_time_contract_version:
            failures.append("scope population/time contract differs from the canonical contract")
    if failures:
        raise ScopeApprovalError("; ".join(failures))


@dataclass(frozen=True)
class ProductionScopeApproval:
    approval_id: str
    status: str
    authorisation_scope_id: str
    capability_audit_id: str
    capability_gate_status: str
    population_time_contract_version: str
    population_time_contract_status: str
    allowed_exchange_ids: tuple[str, ...]
    allowed_security_types: tuple[str, ...]
    allowed_currencies: tuple[str, ...]
    earliest_session: str
    latest_session: str
    approved_snapshot_ids: tuple[str, ...]
    source_manifest_sha256: str
    source_version: str
    consistency_token: str
    authorised_mdm_root: str
    request_sha256: str

    def __post_init__(self) -> None:
        if not _SHA256_RE.fullmatch(self.source_manifest_sha256):
            raise ScopeApprovalError(
                "source_manifest_sha256 must be a lowercase 64-character SHA-256"
            )
        if not _SHA256_RE.fullmatch(self.request_sha256):
            raise ScopeApprovalError(
                "request_sha256 must be a lowercase 64-character SHA-256"
            )
        if not self.authorised_mdm_root.strip():
            raise ScopeApprovalError("authorised_mdm_root must be non-empty")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ProductionScopeApproval":
        expected = {
            "approval_id",
            "status",
            "authorisation_scope_id",
            "capability_audit_id",
            "capability_gate_status",
            "population_time_contract_version",
            "population_time_contract_status",
            "allowed_exchange_ids",
            "allowed_security_types",
            "allowed_currencies",
            "earliest_session",
            "latest_session",
            "approved_snapshot_ids",
            "source_manifest_sha256",
            "source_version",
            "consistency_token",
            "authorised_mdm_root",
            "request_sha256",
        }
        if set(value) != expected:
            raise ScopeApprovalError(
                f"production scope keys mismatch: missing={sorted(expected - set(value))}, "
                f"unexpected={sorted(set(value) - expected)}"
            )
        scalar_names = expected - {
            "allowed_exchange_ids",
            "allowed_security_types",
            "allowed_currencies",
            "approved_snapshot_ids",
        }
        if any(not isinstance(value[name], str) or not value[name] for name in scalar_names):
            raise ScopeApprovalError("production scope scalar values must be non-empty strings")
        arrays: dict[str, tuple[str, ...]] = {}
        for name in (
            "allowed_exchange_ids",
            "allowed_security_types",
            "allowed_currencies",
            "approved_snapshot_ids",
        ):
            raw = value[name]
            if not isinstance(raw, list) or not raw or not all(
                isinstance(item, str) and item for item in raw
            ):
                raise ScopeApprovalError(f"{name} must be a non-empty string array")
            arrays[name] = tuple(raw)
        return cls(
            approval_id=value["approval_id"],
            status=value["status"],
            authorisation_scope_id=value["authorisation_scope_id"],
            capability_audit_id=value["capability_audit_id"],
            capability_gate_status=value["capability_gate_status"],
            population_time_contract_version=value["population_time_contract_version"],
            population_time_contract_status=value["population_time_contract_status"],
            allowed_exchange_ids=arrays["allowed_exchange_ids"],
            allowed_security_types=arrays["allowed_security_types"],
            allowed_currencies=arrays["allowed_currencies"],
            earliest_session=value["earliest_session"],
            latest_session=value["latest_session"],
            approved_snapshot_ids=arrays["approved_snapshot_ids"],
            source_manifest_sha256=value["source_manifest_sha256"],
            source_version=value["source_version"],
            consistency_token=value["consistency_token"],
            authorised_mdm_root=value["authorised_mdm_root"],
            request_sha256=value["request_sha256"],
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "status": self.status,
            "authorisation_scope_id": self.authorisation_scope_id,
            "capability_audit_id": self.capability_audit_id,
            "capability_gate_status": self.capability_gate_status,
            "population_time_contract_version": self.population_time_contract_version,
            "population_time_contract_status": self.population_time_contract_status,
            "allowed_exchange_ids": list(self.allowed_exchange_ids),
            "allowed_security_types": list(self.allowed_security_types),
            "allowed_currencies": list(self.allowed_currencies),
            "earliest_session": self.earliest_session,
            "latest_session": self.latest_session,
            "approved_snapshot_ids": list(self.approved_snapshot_ids),
            "source_manifest_sha256": self.source_manifest_sha256,
            "source_version": self.source_version,
            "consistency_token": self.consistency_token,
            "authorised_mdm_root": self.authorised_mdm_root,
            "request_sha256": self.request_sha256,
        }

    @property
    def content_sha256(self) -> str:
        return sha256_bytes(canonical_json_bytes(self.as_dict()))

    def assert_authorised(self, snapshot: Any, request: Any) -> None:
        failures: list[str] = []
        if self.status != "APPROVED":
            failures.append("scope status is not APPROVED")
        if self.capability_gate_status != "READY":
            failures.append("MDM capability gate is not READY")
        if self.population_time_contract_status != "RATIFIED":
            failures.append("population/time contract is not RATIFIED")
        if snapshot.manifest.authorisation_scope_id != self.authorisation_scope_id:
            failures.append("snapshot authorisation scope differs")
        if snapshot.manifest.snapshot_id not in self.approved_snapshot_ids:
            failures.append("snapshot ID has not been independently approved")
        if snapshot.manifest_sha256 != self.source_manifest_sha256:
            failures.append("source manifest content differs from the approval")
        if snapshot.manifest.source_version != self.source_version:
            failures.append("source version differs from the approval")
        if snapshot.manifest.consistency_token != self.consistency_token:
            failures.append("source consistency token differs from the approval")
        try:
            approved_root = Path(self.authorised_mdm_root).resolve(strict=True)
            actual_root = Path(snapshot.authorised_mdm_root).resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ScopeApprovalError("approved MDM root cannot be resolved") from exc
        if actual_root != approved_root:
            failures.append("authorised MDM root differs from the approval")
        actual_request_sha256 = sha256_bytes(canonical_json_bytes(request.as_dict()))
        if actual_request_sha256 != self.request_sha256:
            failures.append("exact request and policy tuple differs from the approval")
        if request.population_time_contract_version != self.population_time_contract_version:
            failures.append("population/time contract differs")
        if not set(request.exchange_ids) <= set(self.allowed_exchange_ids):
            failures.append("exchange scope exceeds approval")
        if not set(request.security_types) <= set(self.allowed_security_types):
            failures.append("security-type scope exceeds approval")
        if not set(request.currencies) <= set(self.allowed_currencies):
            failures.append("currency scope exceeds approval")
        if request.start_session < self.earliest_session or request.end_session > self.latest_session:
            failures.append("date scope exceeds approval")
        if failures:
            raise ScopeApprovalError("; ".join(failures))


def load_production_scope(path: str | Path) -> ProductionScopeApproval:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScopeApprovalError(f"production scope is unreadable: {source}") from exc
    if not isinstance(value, Mapping):
        raise ScopeApprovalError("production scope root must be an object")
    return ProductionScopeApproval.from_mapping(value)
