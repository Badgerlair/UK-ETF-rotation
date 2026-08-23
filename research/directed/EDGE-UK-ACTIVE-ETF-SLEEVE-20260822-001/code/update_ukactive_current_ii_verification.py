"""Create the dated UKACTIVE current-ii verification overlay.

This program updates current implementation metadata only.  It deliberately
does not write historical eligibility, research-return, universe-mapping,
lineage, or frozen configuration artifacts.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

from query_ukactive_rotation import build_snapshot


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROGRAMME_ROOT.parents[2]
OBSERVATION_DATE = "2026-08-23"
VERIFICATION_METHOD = "USER_ACCOUNT_MANUAL_CHECK"

CONFIRMED_TICKERS = (
    "EBIG",
    "SBIX",
    "S7XP",
    "SPGP",
    "SPOG",
    "SILG",
    "KLWD",
    "ECOG",
    "XUFB",
    "DFEU",
    "ICBM",
    "SPAG",
    "AIAA",
    "CHRG",
    "KWBP",
    "INRA",
    "ARCG",
    "CYSE",
    "INFR",
    "SMGB",
    "QANT",
    "RBTX",
    "RAYS",
    "NUCG",
    "IH2O",
)

VERIFIED_COLUMNS = [
    "economic_exposure_family_id",
    "display_name",
    "rotation_role",
    "preferred_current_implementation_ticker",
    "preferred_isin",
    "issuer",
    "lse_trading_line",
    "listing_currency",
    "alternate_ticker",
    "alternate_isin",
    "current_public_uk_eligibility_status",
    "ii_current_tradable",
    "ii_observation_date",
    "ii_verification_method",
    "notes",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def group_digest(paths: list[Path]) -> dict[str, object]:
    members = []
    aggregate = hashlib.sha256()
    for path in sorted(paths):
        relative = path.relative_to(REPOSITORY_ROOT).as_posix()
        file_hash = sha256(path)
        members.append({"path": relative, "sha256": file_hash})
        aggregate.update(f"{relative}\0{file_hash}\n".encode("utf-8"))
    return {
        "file_count": len(members),
        "aggregate_sha256": aggregate.hexdigest(),
        "members": members,
    }


def protected_groups() -> dict[str, list[Path]]:
    return {
        "historical_eligibility": [
            PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_PUBLIC_UK_ELIGIBILITY_POST_A2R.csv",
            PROGRAMME_ROOT / "UKACTIVE_A4_HISTORICAL_UK_RETAIL_EVIDENCE.csv",
            PROGRAMME_ROOT / "UKACTIVE_A4_HISTORICAL_ISA_EVIDENCE.csv",
        ],
        "research_return_outputs": sorted(
            path
            for path in PROGRAMME_ROOT.iterdir()
            if path.is_file()
            and path.name.startswith(("UKACTIVE_A3", "UKACTIVE_A4"))
            and any(token in path.name for token in ("RESULT", "EQUITY_CURVE", "RETURN_CONTRIBUTION"))
        ),
        "frozen_model_and_config": sorted((PROGRAMME_ROOT / "config").glob("*")),
        "economic_family_mappings": [
            PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_ROTATION_ROLE_MASTER_POST_A2R.csv",
            PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_PARENT_CHILD_MAP_POST_A2R.csv",
            PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_OVERLAP_CLUSTERS_POST_A2R.csv",
        ],
        "historical_implementation_lineage": [
            PROGRAMME_ROOT / "UKACTIVE_A2R_LINEAGE_CORRECTIONS.csv",
            PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_CURRENT_IMPLEMENTATION_LINES_POST_A2R.csv",
            PROGRAMME_ROOT / "UKACTIVE_A2R_CORRECTED_IMPLEMENTATION_HISTORY.parquet",
        ],
        "immutable_20260821_snapshot": [
            PROGRAMME_ROOT / "UKACTIVE_CURRENT_ROTATION_SNAPSHOT.csv",
            PROGRAMME_ROOT / "UKACTIVE_CURRENT_ROTATION_SNAPSHOT.json",
        ],
    }


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=REPOSITORY_ROOT, text=True, encoding="utf-8"
    ).strip()


def write_versioned(path: Path, payload: bytes) -> None:
    if path.exists() and path.read_bytes() != payload:
        raise RuntimeError(f"Refusing to overwrite versioned artifact with different bytes: {path}")
    if not path.exists():
        path.write_bytes(payload)


def build_verified_table() -> pd.DataFrame:
    source = pd.read_csv(
        PROGRAMME_ROOT / "UKACTIVE_CURRENT_II_MANUAL_CHECK_LIST.csv",
        dtype=str,
        keep_default_na=False,
    )
    if len(source) != 25 or source["economic_exposure_family_id"].duplicated().any():
        raise AssertionError("Authoritative manual-check scope is not exactly 25 unique families")
    if set(source["preferred_current_implementation_ticker"]) != set(CONFIRMED_TICKERS):
        raise AssertionError("User-confirmed ticker set does not match the 25-family signal-ready scope")
    if not source["rotation_role"].isin(["INDUSTRY_ROTATION", "THEME_ROTATION"]).all():
        raise AssertionError("Out-of-scope rotation role found")

    verified = source[
        [
            "economic_exposure_family_id",
            "display_name",
            "rotation_role",
            "preferred_current_implementation_ticker",
            "preferred_isin",
            "issuer",
            "lse_trading_line",
            "listing_currency",
            "alternate_ticker",
            "alternate_isin",
            "current_public_uk_eligibility_status",
        ]
    ].copy()
    verified["ii_current_tradable"] = "CONFIRMED_BY_USER"
    verified["ii_observation_date"] = OBSERVATION_DATE
    verified["ii_verification_method"] = VERIFICATION_METHOD
    verified["notes"] = verified["preferred_current_implementation_ticker"].map(
        lambda ticker: (
            f"User manually confirmed {ticker} present and tradeable in Interactive Investor "
            f"on {OBSERVATION_DATE}. Current-only evidence; do not back-project."
        )
    )
    retail = verified["economic_exposure_family_id"].eq("GLOBAL_RETAIL")
    verified.loc[retail, "notes"] = (
        verified.loc[retail, "notes"]
        + " GBP EBIG remains preferred over the alternate USD EBIZ trading line."
    )
    infrastructure = verified["economic_exposure_family_id"].eq("GLOBAL_INFRASTRUCTURE")
    verified.loc[infrastructure, "notes"] = (
        "User manually confirmed INFR present and tradeable in Interactive Investor on "
        "2026-08-23. Current-only evidence; do not back-project."
    )
    verified = verified[VERIFIED_COLUMNS]
    verified["_order"] = verified["preferred_current_implementation_ticker"].map(
        {ticker: index for index, ticker in enumerate(CONFIRMED_TICKERS)}
    )
    return verified.sort_values("_order", kind="stable").drop(columns="_order").reset_index(drop=True)


def markdown_table(frame: pd.DataFrame) -> str:
    lines = [
        "# UKACTIVE current ii implementation verification — 2026-08-23",
        "",
        "This is a current implementation metadata update only. It does not establish historical ii availability, historical ISA eligibility, historical UK-retail eligibility, or deployment readiness.",
        "",
        f"Coverage: **{len(frame)}/{len(frame)} signal-ready INDUSTRY + THEME families (100%)**.",
        "",
        "| " + " | ".join(VERIFIED_COLUMNS) + " |",
        "| " + " | ".join(["---"] * len(VERIFIED_COLUMNS)) + " |",
    ]
    for row in frame.to_dict(orient="records"):
        values = [str(row[column]).replace("|", "\\|").replace("\n", "<br>") for column in VERIFIED_COLUMNS]
        lines.append("| " + " | ".join(values) + " |")
    lines.extend(
        [
            "",
            "Controls:",
            "",
            "- Current user-account evidence is dated 2026-08-23 and is never back-projected.",
            "- Preferred GBP/GBX implementation lines are unchanged.",
            "- GLOBAL_RETAIL continues to prefer GBP EBIG over USD EBIZ.",
            "- No research return, signal, frozen model, economic-family mapping, or historical implementation-lineage artifact is changed.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    before = {name: group_digest(paths) for name, paths in protected_groups().items()}
    verified = build_verified_table()

    verified_csv = PROGRAMME_ROOT / "UKACTIVE_CURRENT_II_IMPLEMENTATION_VERIFIED_20260823.csv"
    verified_md = PROGRAMME_ROOT / "UKACTIVE_CURRENT_II_IMPLEMENTATION_VERIFIED_20260823.md"
    write_versioned(
        verified_csv,
        verified.to_csv(index=False, lineterminator="\n").encode("utf-8"),
    )
    write_versioned(verified_md, markdown_table(verified).encode("utf-8"))

    snapshot, _ = build_snapshot("latest")
    snapshot_csv = PROGRAMME_ROOT / "UKACTIVE_CURRENT_ROTATION_SNAPSHOT_II_VERIFIED_20260823.csv"
    snapshot_json = PROGRAMME_ROOT / "UKACTIVE_CURRENT_ROTATION_SNAPSHOT_II_VERIFIED_20260823.json"
    write_versioned(
        snapshot_csv,
        snapshot.to_csv(index=False, lineterminator="\n").encode("utf-8"),
    )
    snapshot_records = json.loads(snapshot.to_json(orient="records", date_format="iso"))
    write_versioned(
        snapshot_json,
        (json.dumps(snapshot_records, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )

    signal_ready = snapshot.loc[
        snapshot["rotation_pool"].isin(["INDUSTRY", "THEME"])
        & snapshot["current_universe_status"].eq("SIGNAL_ELIGIBLE_AT_ASOF")
        & snapshot["3_6_12_composite"].notna()
    ].copy()
    historical, _ = build_snapshot("2021-08-20")
    after = {name: group_digest(paths) for name, paths in protected_groups().items()}
    protected_unchanged = {
        name: before[name]["aggregate_sha256"] == after[name]["aggregate_sha256"]
        for name in before
    }

    tracked_changes = [line for line in git("diff", "--name-only").splitlines() if line]
    allowed_tracked_changes = {
        "research/directed/EDGE-UK-ACTIVE-ETF-SLEEVE-20260822-001/code/query_ukactive_rotation.py"
    }
    research_outputs_unchanged = set(tracked_changes).issubset(allowed_tracked_changes)

    checks = [
        {
            "control_id": "II-V01",
            "requirement": "Exactly 25 signal-ready INDUSTRY + THEME families",
            "status": "PASS" if len(verified) == 25 and len(signal_ready) == 25 else "FAIL",
            "detail": f"verified={len(verified)}; query_signal_ready={len(signal_ready)}",
        },
        {
            "control_id": "II-V02",
            "requirement": "25/25 are CONFIRMED_BY_USER",
            "status": "PASS" if verified["ii_current_tradable"].eq("CONFIRMED_BY_USER").all() else "FAIL",
            "detail": str(int(verified["ii_current_tradable"].eq("CONFIRMED_BY_USER").sum())),
        },
        {
            "control_id": "II-V03",
            "requirement": "Zero TO_CHECK",
            "status": "PASS" if not verified["ii_current_tradable"].eq("TO_CHECK").any() else "FAIL",
            "detail": str(int(verified["ii_current_tradable"].eq("TO_CHECK").sum())),
        },
        {
            "control_id": "II-V04",
            "requirement": "Zero unresolved preferred implementations",
            "status": "PASS" if verified["preferred_isin"].ne("").all() and verified["preferred_current_implementation_ticker"].ne("").all() else "FAIL",
            "detail": "0",
        },
        {
            "control_id": "II-V05",
            "requirement": "Historical eligibility remains unchanged and current ii status is masked historically",
            "status": "PASS" if protected_unchanged["historical_eligibility"] and historical["II_CURRENT_TRADABLE"].eq("NOT_APPLICABLE_HISTORICAL_ASOF").all() else "FAIL",
            "detail": "historical artifact digest unchanged; historical query masks current ii metadata",
        },
        {
            "control_id": "II-V06",
            "requirement": "No research-return outputs changed",
            "status": "PASS" if protected_unchanged["research_return_outputs"] and research_outputs_unchanged else "FAIL",
            "detail": f"protected_files={before['research_return_outputs']['file_count']}; tracked_changes={tracked_changes}",
        },
        {
            "control_id": "II-V07",
            "requirement": "No frozen model/config changed",
            "status": "PASS" if protected_unchanged["frozen_model_and_config"] else "FAIL",
            "detail": f"protected_files={before['frozen_model_and_config']['file_count']}",
        },
        {
            "control_id": "II-V08",
            "requirement": "No economic-family mappings changed",
            "status": "PASS" if protected_unchanged["economic_family_mappings"] else "FAIL",
            "detail": f"protected_files={before['economic_family_mappings']['file_count']}",
        },
        {
            "control_id": "II-V09",
            "requirement": "No historical implementation lineage changed and immutable 2026-08-21 snapshot preserved",
            "status": "PASS" if protected_unchanged["historical_implementation_lineage"] and protected_unchanged["immutable_20260821_snapshot"] else "FAIL",
            "detail": "lineage and immutable current-alias digests unchanged",
        },
        {
            "control_id": "II-V10",
            "requirement": "Query-engine current metadata reproduces the 25 confirmations",
            "status": "PASS" if len(signal_ready) == 25 and signal_ready["II_CURRENT_TRADABLE"].eq("CONFIRMED_BY_USER").all() and signal_ready["II_OBSERVATION_DATE"].eq(OBSERVATION_DATE).all() and signal_ready["II_VERIFICATION_METHOD"].eq(VERIFICATION_METHOD).all() else "FAIL",
            "detail": f"confirmed={int(signal_ready['II_CURRENT_TRADABLE'].eq('CONFIRMED_BY_USER').sum())}/25",
        },
    ]
    if any(check["status"] != "PASS" for check in checks):
        raise AssertionError(json.dumps(checks, indent=2))

    outputs = [verified_csv, verified_md, snapshot_csv, snapshot_json]
    summary = {
        "update_id": "UKACTIVE-CURRENT-II-VERIFICATION-20260823-001",
        "programme_root": str(PROGRAMME_ROOT),
        "metadata_scope": "CURRENT_IMPLEMENTATION_ONLY",
        "observation_date": OBSERVATION_DATE,
        "verification_method": VERIFICATION_METHOD,
        "signal_ready_industry_theme_families": 25,
        "ii_confirmed": 25,
        "to_check": 0,
        "unresolved": 0,
        "current_ii_implementation_coverage": 1.0,
        "historical_back_projection": "PROHIBITED_AND_NOT_PERFORMED",
        "deployment_readiness_inference": "NOT_AUTHORISED",
        "executed_from_commit": git("rev-parse", "HEAD"),
        "source_artifacts": [
            {
                "path": str(PROGRAMME_ROOT / "UKACTIVE_CURRENT_II_MANUAL_CHECK_LIST.csv"),
                "sha256": sha256(PROGRAMME_ROOT / "UKACTIVE_CURRENT_II_MANUAL_CHECK_LIST.csv"),
            },
            {
                "path": str(PROGRAMME_ROOT / "UKACTIVE_A4_CURRENT_II_IMPLEMENTATION.csv"),
                "sha256": sha256(PROGRAMME_ROOT / "UKACTIVE_A4_CURRENT_II_IMPLEMENTATION.csv"),
            },
            {
                "path": str(PROGRAMME_ROOT / "UKACTIVE_CURRENT_ROTATION_SNAPSHOT.csv"),
                "sha256": sha256(PROGRAMME_ROOT / "UKACTIVE_CURRENT_ROTATION_SNAPSHOT.csv"),
            },
        ],
        "outputs": [
            {"path": str(path), "sha256": sha256(path), "size_bytes": path.stat().st_size}
            for path in outputs
        ],
        "protected_artifact_groups": after,
        "quality_controls": checks,
        "limitations": [
            "Current user-account observations are not evidence of historical ii availability.",
            "Current ii confirmation is not historical ISA or UK-retail verification.",
            "Current ii confirmation does not make the frozen research candidate deployment-ready.",
        ],
    }
    summary_path = PROGRAMME_ROOT / "UKACTIVE_CURRENT_II_IMPLEMENTATION_VERIFICATION_SUMMARY.json"
    write_versioned(
        summary_path,
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )

    print(
        json.dumps(
            {
                "signal_ready": 25,
                "ii_confirmed": 25,
                "to_check": 0,
                "unresolved": 0,
                "coverage": "100%",
                "quality_controls": "10/10 PASS",
                "snapshot_rows": len(snapshot),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
