"""Guarded UKACTIVE-A5 prospective shadow-decision runner.

No broker connection, order path, or scheduler exists in this module.  It reads
an externally refreshed frozen-feature panel and can append one prospective
decision row only when every lineage/date guard passes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_ROOT = PROGRAMME_ROOT.parents[2]
DEFAULT_CONFIG = PROGRAMME_ROOT / "config" / "ukactive_a5_frozen_candidate.json"
DEFAULT_FEATURES = PROGRAMME_ROOT / "UKACTIVE_A3R2_FEATURE_PANEL.parquet"
DEFAULT_IMPLEMENTATIONS = PROGRAMME_ROOT / "UKACTIVE_A4_CURRENT_II_IMPLEMENTATION.csv"
DEFAULT_REGIMES = PROGRAMME_ROOT / "UKACTIVE_A3R2_REGIME_STATE_HISTORY.parquet"
DEFAULT_LEDGER = PROGRAMME_ROOT / "UKACTIVE_A5_PROSPECTIVE_DECISION_LEDGER.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=PLATFORM_ROOT, text=True).strip()


def resolve_freeze(config: dict[str, Any]) -> str:
    tag = config["model_freeze_git_tag"]
    return git("rev-parse", f"{tag}^{{commit}}")


def implementation_state(value: str) -> str:
    if value == "CURRENT_II_CONFIRMED":
        return "SHADOW_EXECUTABLE_CURRENT_II_CONFIRMED"
    if value == "CURRENT_PUBLIC_UK_ELIGIBLE_II_UNCHECKED":
        return "SHADOW_NOT_EXECUTABLE_II_UNCHECKED"
    return "SHADOW_NOT_EXECUTABLE_IMPLEMENTATION_UNRESOLVED"


def load_regime(regime_path: Path, asof: pd.Timestamp) -> dict[str, Any]:
    frame = pd.read_parquet(regime_path)
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.loc[frame["date"].eq(asof) & frame["pool_id"].eq("INDUSTRY_PLUS_THEME")]
    if frame.empty:
        return {key: "NOT_AVAILABLE_REQUIRES_REFRESH" for key in [
            "global_trend_regime", "volatility_regime", "dispersion_regime", "breadth_regime",
            "rotation_intensity_regime", "us_technology_dominance",
        ]}
    row = frame.iloc[0]
    return {key: row.get(key, "NOT_AVAILABLE") for key in [
        "global_trend_regime", "volatility_regime", "dispersion_regime", "breadth_regime",
        "rotation_intensity_regime", "us_technology_dominance",
    ]}


def build_decision(
    *,
    asof: pd.Timestamp,
    config_path: Path,
    feature_path: Path,
    implementation_path: Path,
    regime_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["status"] != "FROZEN_NOT_STARTED":
        raise RuntimeError("A5 configuration is not in the frozen pre-start state")
    cutoff = pd.Timestamp(config["historical_development_cutoff"])
    earliest = pd.Timestamp(config["prospective_signal_not_before"])
    if asof <= cutoff or asof < earliest:
        raise RuntimeError(f"Prospective guard failed: {asof.date()} is not after cutoff and tagged boundary")
    freeze_commit = resolve_freeze(config)

    features = pd.read_parquet(feature_path)
    features["date"] = pd.to_datetime(features["date"])
    if features["date"].max() < asof:
        raise RuntimeError("Feature panel has not been refreshed through requested as-of date")
    frame = features.loc[
        features["date"].eq(asof)
        & features["cadence"].eq("MONTHLY")
        & features["analysis_context_id"].eq(config["candidate"]["economic_pool"])
        & features["MH_LEVEL_3_6_12_REFERENCE"].notna()
    ].copy()
    if frame.empty:
        raise RuntimeError("Requested date is not a valid frozen monthly decision date or has no eligible families")
    rebuilt = frame[["RANK_RS_63", "RANK_RS_126", "RANK_RS_252"]].mean(axis=1)
    difference = (frame["MH_LEVEL_3_6_12_REFERENCE"] - rebuilt).abs()
    if not np.allclose(difference, 0.0, atol=1e-12, rtol=0.0):
        raise RuntimeError("Frozen score reconstruction failed")
    frame = frame.sort_values(
        ["MH_LEVEL_3_6_12_REFERENCE", "economic_exposure_family_id"], ascending=[False, True]
    ).reset_index(drop=True)
    top = frame.iloc[0]
    implementations = pd.read_csv(implementation_path, dtype=str)
    match = implementations.loc[
        implementations["economic_exposure_family_id"].eq(top["economic_exposure_family_id"])
    ]
    if match.empty:
        raise RuntimeError("Economic rank 1 lacks a row in the versioned current implementation table")
    impl = match.iloc[0]
    regimes = load_regime(regime_path, asof)
    decision = {
        "specification_id": config["specification_id"],
        "model_freeze_git_tag": config["model_freeze_git_tag"],
        "model_freeze_git_commit": freeze_commit,
        "signal_date": asof.date().isoformat(),
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_feature_panel_path": str(feature_path.resolve()),
        "input_feature_panel_sha256": sha256(feature_path),
        "current_implementation_path": str(implementation_path.resolve()),
        "current_implementation_sha256": sha256(implementation_path),
        "eligible_family_count": int(len(frame)),
        "rank_1_family": str(top["economic_exposure_family_id"]),
        "rank_1_score": float(top["MH_LEVEL_3_6_12_REFERENCE"]),
        "rank_rs_63": float(top["RANK_RS_63"]),
        "rank_rs_126": float(top["RANK_RS_126"]),
        "rank_rs_252": float(top["RANK_RS_252"]),
        "score_reconstruction_difference": float(difference.loc[top.name]),
        "rank_2_family": str(frame.iloc[1]["economic_exposure_family_id"]) if len(frame) > 1 else "NOT_APPLICABLE",
        "rank_3_family": str(frame.iloc[2]["economic_exposure_family_id"]) if len(frame) > 2 else "NOT_APPLICABLE",
        "preferred_ticker": str(impl["preferred_ticker"]),
        "preferred_isin": str(impl["preferred_isin"]),
        "ii_current_status": str(impl["ii_current_tradable"]),
        "ii_observation_date": str(impl["ii_observation_date"]),
        "shadow_execution_state": implementation_state(str(impl["current_implementation_state"])),
        "benchmark_family_id": config["candidate"]["global_benchmark_family_id"],
        **regimes,
        "backfill": "NO",
        "orders_or_scheduler": "NONE",
        "warning": config["warning"],
    }
    return decision


def append_ledger(path: Path, row: dict[str, Any]) -> None:
    if path.exists():
        existing = pd.read_csv(path, dtype=str)
        if existing["signal_date"].eq(row["signal_date"]).any():
            raise RuntimeError("A5 ledger already contains this signal date")
        if not existing.empty and pd.Timestamp(row["signal_date"]) <= pd.to_datetime(existing["signal_date"]).max():
            raise RuntimeError("A5 ledger dates must be strictly increasing")
        columns = list(existing.columns)
        if columns != list(row):
            raise RuntimeError("A5 ledger schema does not match frozen runner output")
        frame = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
    else:
        frame = pd.DataFrame([row])
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate one guarded prospective UKACTIVE-A5 shadow decision")
    parser.add_argument("--asof", required=True, help="Prospective monthly XLON review date (YYYY-MM-DD)")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--feature-panel", type=Path, default=DEFAULT_FEATURES)
    parser.add_argument("--current-implementation", type=Path, default=DEFAULT_IMPLEMENTATIONS)
    parser.add_argument("--regime-panel", type=Path, default=DEFAULT_REGIMES)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--record", action="store_true", help="Append the decision to the immutable CSV ledger")
    args = parser.parse_args()
    decision = build_decision(
        asof=pd.Timestamp(args.asof),
        config_path=args.config,
        feature_path=args.feature_panel,
        implementation_path=args.current_implementation,
        regime_path=args.regime_panel,
    )
    if args.record:
        append_ledger(args.ledger, decision)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
